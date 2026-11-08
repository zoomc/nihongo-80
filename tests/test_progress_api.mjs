// Contract + regression tests for POST /api/progress and GET /api/progress.
// Runs the real Worker bundle via esbuild + a node:sqlite in-memory D1 mock,
// mirroring tests/test_worker_access.mjs. No network, no secrets, no files written.
import { createRequire } from 'node:module';
import { strict as assert } from 'node:assert';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';

const require = createRequire(new URL('../deploy/package.json', import.meta.url));
const { build } = require('esbuild');
const result = await build({
  entryPoints: [new URL('../deploy/worker/src/index.ts', import.meta.url).pathname],
  bundle: true, write: false, format: 'esm', platform: 'browser',
});
const worker = (await import('data:text/javascript;base64,' +
  Buffer.from(result.outputFiles[0].text).toString('base64'))).default;

const BASE = 'https://example.test';
const KEY = 'test-only-key';
const MIGRATIONS = ['0003_personal_budget.sql', '0005_progress.sql'];

function makeDb() {
  const sqlite = new DatabaseSync(':memory:');
  for (const name of MIGRATIONS) {
    sqlite.exec(readFileSync(new URL('../deploy/migrations/' + name, import.meta.url), 'utf8'));
  }
  class Statement {
    constructor(sql, args = []) { this.sql = sql; this.args = args; }
    bind(...args) { return new Statement(this.sql, args); }
    async first() { return sqlite.prepare(this.sql).get(...this.args) ?? null; }
    async run() { const r = sqlite.prepare(this.sql).run(...this.args); return { meta: { changes: Number(r.changes) } }; }
    async all() { return { success: true, results: sqlite.prepare(this.sql).all(...this.args) }; }
  }
  return { sqlite, db: { prepare: (sql) => new Statement(sql) } };
}

const { sqlite, db } = makeDb();
const env = {
  NH80_SYNC_KEY: KEY,
  DB: db,
  ASSETS: { async fetch() { return new Response('', { status: 404 }); } },
};

const payload = {
  v: 1,
  day: 47,
  completed_at: '2026-11-08T23:50:00+08:00',
  required_ids: ['V0001'],
  extra_ids: ['V0002'],
  grammar_ids: ['G0001'],
  questions: [{ qid: 'Q-001-K0-xxx', answer: 'ニチ', correct: true, hinted: false, revealed: false, seconds: 8 }],
  accuracy: 0.83,
  self_rating: { V0001: 'good', G0001: 'hard' },
  wrong_summary: [{ qid: 'Q-001-K0-xxx', knowledge_ids: ['V0001'] }],
  review_summary: ['V0001', 'G0001'],
  note: '',
};

const post = (body, headers = {}) => worker.fetch(new Request(BASE + '/api/progress', {
  method: 'POST',
  headers: { 'content-type': 'application/json', ...headers },
  body: typeof body === 'string' ? body : JSON.stringify(body),
}), env);
const get = (qs, headers = {}) => worker.fetch(new Request(BASE + '/api/progress' + qs, {
  method: 'GET',
  headers: { ...headers },
}), env);
const readDay = async (day) => (await (await get('?day=' + day, { 'X-NH80-Key': KEY })).json()).items;

// 1) 无 Origin 也能 POST（页面/CLI 冒烟路径），响应严格按契约三字段。
const r1 = await post(payload);
assert.equal(r1.status, 200, 'no-Origin POST should be accepted');
assert.deepEqual(await r1.json(), { ok: true, day: 47, saved: true });
console.log('PASS: POST without Origin accepted (content-type guard + strong limits)');

// 2) 错误 day -> 400。
for (const bad of [0, 151, '47x', null, 3.5]) {
  const r = await post({ ...payload, day: bad });
  assert.equal(r.status, 400, 'bad day: ' + String(bad));
}
console.log('PASS: invalid day rejected with 400');

// 3) 超大体 -> 413（content-length 与实际文本长度双检）。
const r3a = await post({ ...payload, junk: 'x'.repeat(70 * 1024) });
assert.equal(r3a.status, 413, 'actual text length > 64KB');
const r3b = await worker.fetch(new Request(BASE + '/api/progress', {
  method: 'POST',
  headers: { 'content-type': 'application/json', 'content-length': '999999' },
  body: JSON.stringify(payload),
}), env);
assert.equal(r3b.status, 413, 'declared content-length > 64KB');
console.log('PASS: oversized body rejected with 413 (both content-length and actual length)');

// 4) GET 无 key -> 401。
const r4 = await get('?day=47');
assert.equal(r4.status, 401);
console.log('PASS: GET without X-NH80-Key denied with 401');

// 5) GET 有 key -> 200；item 含全部字段 + server_ts + self_reported。
const r5 = await get('?day=47', { 'X-NH80-Key': KEY });
assert.equal(r5.status, 200);
const b5 = await r5.json();
assert.equal(b5.ok, true);
assert.equal(b5.items.length, 1);
const it = b5.items[0];
assert.equal(it.day, 47);
assert.equal(it.accuracy, 0.83);
assert.equal(it.self_reported, 1);
assert.equal(typeof it.server_ts, 'string');
assert.deepEqual(it.required_ids, ['V0001']);
assert.deepEqual(it.grammar_ids, ['G0001']);
assert.deepEqual(it.self_rating, { V0001: 'good', G0001: 'hard' });
assert.equal(it.questions[0].correct, true, 'client correct preserved but NOT authoritative');
assert.equal(it.questions[0].answer, 'ニチ');
assert.equal(it.note, '');
console.log('PASS: GET with key reads back full item (server_ts + self_reported)');

// 6) POST 后 GET 能读回（latest 路径）。
const r6 = await get('?latest=1&limit=7', { 'X-NH80-Key': KEY });
assert.equal(r6.status, 200);
assert.equal((await r6.json()).items[0].day, 47);
console.log('PASS: ?latest=1&limit=7 reads back the saved snapshot');

// 7) 同 day 再 POST 覆盖不追加。
const r7 = await post({ ...payload, accuracy: 0.5, note: '第二次覆盖' });
assert.equal(r7.status, 200);
assert.equal(sqlite.prepare('SELECT COUNT(*) AS n FROM study_progress').get().n, 1,
  'same-day overwrite must not append rows');
const it7 = (await readDay(47))[0];
assert.equal(it7.accuracy, 0.5);
assert.equal(it7.note, '第二次覆盖');
console.log('PASS: same-day POST overwrites (row count stays 1, no append)');

// 8) 未知字段被丢弃（字段白名单）。
await post({ ...payload, evil_field: 'DROP TABLE', correct: 'server-authority-claim' });
const it8 = (await readDay(47))[0];
assert.equal('evil_field' in it8, false);
assert.equal('correct' in it8, false);
console.log('PASS: unknown fields dropped (whitelist enforced)');

// 9) Origin 白名单：production / 本地回环放行，跨站 403。
const badOrigin = await post(payload, { Origin: 'https://evil.example' });
assert.equal(badOrigin.status, 403);
const okProd = await post({ ...payload, day: 48 }, { Origin: 'https://nihongo80.cmjfire.workers.dev' });
assert.equal(okProd.status, 200);
const okLocal = await post({ ...payload, day: 49 }, { Origin: 'http://127.0.0.1:8788' });
assert.equal(okLocal.status, 200);
console.log('PASS: Origin allowlist (production / loopback accepted, cross-site 403)');

// 10) 缺 content-type -> 400。
const noCt = await worker.fetch(new Request(BASE + '/api/progress', {
  method: 'POST', body: JSON.stringify(payload),
}), env);
assert.equal(noCt.status, 400);
console.log('PASS: POST without content-type rejected');

// 11) 现有 /api/events 鉴权未被破坏（无 key 仍 401，且不触碰 D1）。
const ev = await worker.fetch(new Request(BASE + '/api/events', {
  method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}',
}), env);
assert.equal(ev.status, 401);
console.log('PASS: existing /api/events auth unchanged (still 401 before DB)');

// 12) 限流：独立库，第 51 次同 IP 写入 -> 429（每 IP 每日 50 次）。
const db2 = makeDb();
const env2 = { NH80_SYNC_KEY: KEY, DB: db2.db, ASSETS: env.ASSETS };
let lastStatus = 0;
for (let i = 0; i < 51; i += 1) {
  lastStatus = (await worker.fetch(new Request(BASE + '/api/progress', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ...payload, day: 100 }),
  }), env2)).status;
}
assert.equal(lastStatus, 429);
console.log('PASS: per-IP daily write budget (50) enforced with 429');

console.log('\nALL PASS: /api/progress contract');
