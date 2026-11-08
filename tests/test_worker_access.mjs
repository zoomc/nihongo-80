// Regression: untrusted POSTs must be rejected before parsing or touching D1.
import { createRequire } from 'node:module';
import { strict as assert } from 'node:assert';
const require = createRequire(new URL('../deploy/package.json', import.meta.url));
const { build } = require('esbuild');
const result = await build({entryPoints:[new URL('../deploy/worker/src/index.ts',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'browser'});
const worker = (await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'))).default;
const env = {NH80_SYNC_KEY:'test-only-key',DB:{prepare(){throw new Error('must not touch DB')}}};
const response = await worker.fetch(new Request('https://example.test/api/events',{method:'POST',body:'{}',headers:{'content-type':'application/json'}}),env);
assert.equal(response.status,401);
console.log('PASS: unauthenticated writes denied before database access');

// Smoke-check path must reach D1 and never store learning events.
let prepared = 0;
const env2 = {NH80_SYNC_KEY:'test-only-key',DB:{prepare(sql){prepared++;return{first:async()=>({id:'total'})}}}};
const res2 = await worker.fetch(new Request('https://example.test/api/events',{method:'POST',
  body:JSON.stringify({v:1,day:1,check:true}),headers:{'content-type':'application/json','X-NH80-Key':'test-only-key'}}),env2);
const body2 = await res2.json();
assert.equal(res2.status,200);
assert.equal(body2.ok,true);
assert.equal(body2.stored,0);
assert.equal(prepared,1);
console.log('PASS: authenticated check probes D1 without writing');

// A session's metadata is immutable: changed drafts must not be silently lost.
const { DatabaseSync } = await import('node:sqlite');
const { readFileSync } = await import('node:fs');
const { createHash } = await import('node:crypto');
const sqlite = new DatabaseSync(':memory:');
for (const name of ['0001_events.sql','0002_session_payload.sql','0003_personal_budget.sql','0004_study.sql']) {
  sqlite.exec(readFileSync(new URL('../deploy/migrations/' + name, import.meta.url), 'utf8'));
}
class Statement {
  constructor(sql, args=[]) { this.sql=sql; this.args=args; }
  bind(...args) { return new Statement(this.sql,args); }
  async first() { return sqlite.prepare(this.sql).get(...this.args) ?? null; }
  async run() { const result=sqlite.prepare(this.sql).run(...this.args); return {meta:{changes:Number(result.changes)}}; }
}
const db = {
  prepare: sql => new Statement(sql),
  async batch(statements) {
    sqlite.exec('BEGIN');
    try { const results=[]; for (const stmt of statements) results.push(await stmt.run()); sqlite.exec('COMMIT'); return results; }
    catch (err) { sqlite.exec('ROLLBACK'); throw err; }
  },
};
const hash = createHash('sha256').update('はい').digest('hex');
const env3 = {NH80_SYNC_KEY:'test-only-key',DB:db,ASSETS:{async fetch(){return Response.json({answers:{Q1:{day:1,type:'mcq',answer_hash:hash,knowledge_ids:[]},Q2:{day:1,type:'mcq',answer_hash:hash,knowledge_ids:[]}}})}}};
const submit = body => worker.fetch(new Request('https://example.test/api/events',{method:'POST',headers:{'X-NH80-Key':'test-only-key','content-type':'application/json'},body:JSON.stringify(body)}),env3);
const first = {day:1,session:'session-metadata',practice_mode:'choice',review_ratings:[],sentences:[],results:[{qid:'Q1',answer:'はい'}]};
assert.equal((await submit(first)).status,200);
const conflict = await submit({...first,sentences:[{text:'new draft'}],results:[{qid:'Q2',answer:'はい'}]});
assert.equal(conflict.status,409, 'changed session metadata must be rejected');
const conflictBody=await conflict.json();
assert.equal(conflictBody.reason,'session_metadata_conflict');
assert.equal(conflictBody.local_export,true);
assert.equal(sqlite.prepare('SELECT count(*) AS n FROM events').get().n,1);
const append = await submit({...first,results:[{qid:'Q2',answer:'はい'}]});
assert.equal(append.status,200);
assert.equal((await append.json()).stored,1);
const duplicate = await submit({...first,results:[{qid:'Q2',answer:'別の回答'}]});
assert.equal((await duplicate.json()).duplicates,1);
assert.equal(sqlite.prepare('SELECT answer FROM events WHERE qid=?').get('Q2').answer,'はい');
// Simulate an out-of-date preflight read: the transactional upsert must still reject.
env3.DB={...db,prepare(sql){if(sql.startsWith('SELECT day,payload')) return {bind(){return {first:async()=>null}}}; return db.prepare(sql)}};
const raced=await submit({...first,sentences:[{text:'concurrent draft'}],results:[{qid:'Q1',answer:'はい'}]});
assert.equal(raced.status,409);
assert.equal((await raced.json()).reason,'session_metadata_conflict');
assert.equal(sqlite.prepare('SELECT payload FROM study_sessions WHERE session=?').get(first.session).payload,JSON.stringify({review_ratings:[],sentences:[],practice_mode:'choice'}));
console.log('PASS: session metadata conflict is rejected; append and duplicate remain idempotent');
