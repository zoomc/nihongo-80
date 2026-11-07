import generatedKey from "./generated-key.json";
// Nihongo 80 Worker
//
// 职责（docs/REVISION_CONTRACT.md 第 10 节）：
//   GET  /api/health  -> {"status":"ok","features":{db,sync}}
//   POST /api/events  -> 接收网页原始作答事件，服务端重判客观题后写入 D1
//   GET  /api/events  -> 需要 X-NH80-Key（env.NH80_SYNC_KEY），供本地 cloud_sync.py 增量拉取
//   其余路径          -> 交给 ASSETS 静态资源
//
// 硬约束：
//   - 前端只提交 answer/hinted/seconds，**不提交 correct**；判分只认服务端标准答案。
//   - 未绑定 D1 时不报 500，统一返回 503 {"ok":false,"reason":"no_db"}（优雅降级）。
//   - 未配置 NH80_SYNC_KEY 时 GET /api/events 返回 503，绝不裸奔。
//   - CORS 只允许同源，不使用 "*"。

interface Fetcher {
  fetch(input: Request | string | URL, init?: RequestInit): Promise<Response>;
}

interface D1Result<T = unknown> {
  success: boolean;
  results?: T[];
  meta?: { changes?: number; last_row_id?: number };
}

interface D1PreparedStatement {
  bind(...values: unknown[]): D1PreparedStatement;
  run(): Promise<D1Result>;
  all<T = Record<string, unknown>>(): Promise<D1Result<T>>;
}

interface D1Database {
  prepare(query: string): D1PreparedStatement;
  batch?(statements: D1PreparedStatement[]): Promise<D1Result[]>;
}

interface Env {
  ASSETS: Fetcher;
  /** 可选：未绑定时整套接口自动降级，静态站行为完全不变。 */
  DB?: D1Database;
  /** 可选：未配置时 GET /api/events 返回 503（用 `wrangler secret put` 设置）。 */
  NH80_SYNC_KEY?: string;
}

const MAX_RESULTS = 40;
const MAX_BODY_BYTES = 64 * 1024;
const MAX_ANSWER_CHARS = 2000;
const OPEN_TYPES = new Set(["free_production", "dialogue", "translate"]);

// ---------------------------------------------------------------------------
// 通用响应 / CORS（同源，绝不使用 "*"）
// ---------------------------------------------------------------------------

function jsonResponse(body: unknown, status: number, origin: string | null): Response {
  const headers = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  if (origin) {
    headers.set("access-control-allow-origin", origin);
    headers.set("vary", "Origin");
  }
  return new Response(JSON.stringify(body), { status, headers });
}

/** 返回非空 Response 表示应直接拒绝（跨源）。 */
function rejectCrossOrigin(request: Request, url: URL): Response | null {
  const origin = request.headers.get("Origin");
  if (origin && origin !== url.origin) {
    // 不回 CORS 头，浏览器侧同样会拒绝读取；这里再给一个明确状态码。
    return jsonResponse({ ok: false, reason: "cross_origin" }, 403, null);
  }
  return null;
}

function okOrigin(request: Request, url: URL): string | null {
  const origin = request.headers.get("Origin");
  return origin === url.origin ? origin : null;
}

function preflight(request: Request, url: URL): Response | null {
  if (request.method !== "OPTIONS") return null;
  const denied = rejectCrossOrigin(request, url);
  if (denied) return denied;
  const headers = new Headers({
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "content-type, x-nh80-key",
    "access-control-max-age": "86400",
    "vary": "Origin",
  });
  const origin = okOrigin(request, url);
  if (origin) headers.set("access-control-allow-origin", origin);
  return new Response(null, { status: 204, headers });
}

// ---------------------------------------------------------------------------
// 答案标准化 / 重判（与 web/assets/app.js 的 norm()、learning.norm_answer() 同构）
// NFKC → 去所有空白（含全角空格）→ 去句末标点 → 全角逗号转半角
// ---------------------------------------------------------------------------

function norm(value: unknown): string {
  return String(value ?? "")
    .normalize("NFKC")
    .replace(/[\s\u3000]+/g, "")
    .replace(/[。．.！!？?]+$/g, "")
    .replace(/，/g, ",");
}

interface KeyEntry {
  day?: number;
  type?: string;
  answer?: string;
  accepted?: string[];
  capability?: string;
}

type AnswerKey = Map<string, KeyEntry>;

/**
 * answer-key.json 由 scripts/build_site.py 生成，这里做容错解析，避免形状差异导致整站失效。
 * 支持：{answers:{qid:{type,answer,accepted,capability}}}、{key:{...}}、
 *       {questions:[{id|qid,...}]}、以及顶层直接是 qid -> 答案 的映射。
 */
function indexAnswerKey(raw: unknown): AnswerKey {
  const key: AnswerKey = new Map();
  const put = (qid: unknown, value: unknown) => {
    if (typeof qid !== "string" || !qid) return;
    if (typeof value === "string") {
      key.set(qid, { answer: value });
    } else if (value && typeof value === "object") {
      key.set(qid, value as KeyEntry);
    }
  };

  const root = raw as Record<string, unknown> | null;
  let table: unknown = root;
  if (root && !Array.isArray(root) && typeof root === "object") {
    table = root.answers ?? root.key ?? root.questions ?? root;
  }
  if (Array.isArray(table)) {
    for (const item of table) {
      if (!item || typeof item !== "object") continue;
      const obj = item as Record<string, unknown>;
      put(obj.qid ?? obj.id, obj);
    }
  } else if (table && typeof table === "object") {
    for (const [qid, value] of Object.entries(table as Record<string, unknown>)) put(qid, value);
  }
  return key;
}

async function loadAnswerKey(env: Env, url: URL): Promise<AnswerKey | null> {
  return indexAnswerKey(generatedKey);
}

/** 客观题重判；开放题 / 缺标准答案 / 缺条目 → null（无法重判）。 */
function regrade(entry: KeyEntry | undefined, answer: unknown): boolean | null {
  if (!entry) return null;
  const type = typeof entry.type === "string" ? entry.type : "";
  if (OPEN_TYPES.has(type)) return null;

  const candidates: string[] = [];
  if (Array.isArray(entry.accepted)) {
    for (const item of entry.accepted) candidates.push(String(item));
  }
  if (typeof entry.answer === "string") candidates.push(entry.answer);
  if (candidates.length === 0) return null;

  const strip = (s: string) => (type === "reorder" ? norm(s).replace(/,/g, "") : norm(s));
  const actual = strip(String(answer ?? ""));
  return candidates.some((c) => strip(c) === actual);
}

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function asInt(value: unknown, fallback: number | null, min: number, max: number): number | null {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, Math.trunc(n)));
}

/** 严格整数区间校验：越界返回 null（用于 day 这类不允许 clamp 的字段）。 */
function strictInt(value: unknown, min: number, max: number): number | null {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(n) || n < min || n > max) return null;
  return n;
}

// ---------------------------------------------------------------------------
// POST /api/events
// ---------------------------------------------------------------------------

interface IncomingResult {
  qid: string;
  answer: string;
  hinted: boolean;
  revealed: boolean;
  seconds: number | null;
}

function parseResults(raw: unknown): IncomingResult[] | string {
  if (!Array.isArray(raw)) return "results_must_be_array";
  if (raw.length > MAX_RESULTS) return "too_many_results";
  const out: IncomingResult[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") return "bad_result_item";
    const obj = item as Record<string, unknown>;
    const qid = typeof obj.qid === "string" ? obj.qid.trim() : "";
    if (!qid || !/^[A-Za-z0-9_.:-]{1,48}$/.test(qid)) return "bad_qid";
    const answer = obj.answer === undefined || obj.answer === null ? "" : String(obj.answer);
    if (answer.length > MAX_ANSWER_CHARS) return "answer_too_long";
    const seconds = obj.seconds === undefined || obj.seconds === null
      ? null
      : asInt(obj.seconds, null, 0, 86400);
    out.push({
      qid,
      answer,
      hinted: obj.hinted === true,
      revealed: obj.revealed_before_submit === true || obj.revealed === true,
      seconds,
    });
  }
  return out;
}

async function handlePostEvents(request: Request, env: Env, url: URL): Promise<Response> {
  const origin = okOrigin(request, url);
  const rawBody = await request.text();
  if (rawBody.length > MAX_BODY_BYTES) {
    return jsonResponse({ ok: false, reason: "body_too_large" }, 413, origin);
  }
  let body: Record<string, unknown>;
  try {
    const parsed = JSON.parse(rawBody);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("not object");
    body = parsed as Record<string, unknown>;
  } catch {
    return jsonResponse({ ok: false, reason: "bad_json" }, 400, origin);
  }

  if (body.v !== undefined && body.v !== 1) {
    return jsonResponse({ ok: false, reason: "bad_version" }, 400, origin);
  }
  const day = strictInt(body.day, 1, 150);
  if (day === null) return jsonResponse({ ok: false, reason: "bad_day" }, 400, origin);

  const session = typeof body.session === "string" ? body.session.trim() : "";
  if (session.length < 3 || session.length > 96 || !/^[A-Za-z0-9_.:-]+$/.test(session)) {
    return jsonResponse({ ok: false, reason: "bad_session" }, 400, origin);
  }

  const results = parseResults(body.results);
  if (typeof results === "string") return jsonResponse({ ok: false, reason: results }, 400, origin);
  if (results.length === 0) return jsonResponse({ ok: false, reason: "empty_results" }, 400, origin);

  const clientTs = typeof body.client_ts === "string" ? body.client_ts.slice(0, 40) : null;
  const minutes = body.minutes === undefined ? null : asInt(body.minutes, null, 0, 1440);

  // 无 D1：优雅降级，明确 503，绝不 500。静态页与回传码路径完全不受影响。
  const db = env.DB;
  if (!db) {
    return jsonResponse({ ok: false, reason: "no_db" }, 503, origin);
  }

  const answerKey = await loadAnswerKey(env, url);
  const wrong = results.find(r => !answerKey?.has(r.qid) || answerKey.get(r.qid)?.day !== day);
  if (wrong) return jsonResponse({ok:false, reason:"unknown_or_wrong_day_question"}, 400, origin);
  const serverTs = new Date().toISOString();

  const graded = results.map((r) => {
    const entry = answerKey ? answerKey.get(r.qid) : undefined;
    const correct = answerKey ? regrade(entry, r.answer) : null;
    return { r, entry, correct };
  });

  const statements: D1PreparedStatement[] = [];
  for (const item of graded) {
    const { r, entry, correct } = item;
    const hinted = r.hinted || r.revealed;
    const payloadHash = await sha256Hex(
      JSON.stringify([day, session, r.qid, r.answer, hinted, r.revealed, r.seconds, clientTs ?? ""]),
    );
    statements.push(
      db
        .prepare(
          `INSERT OR IGNORE INTO events
             (client_ts, server_ts, day, session, qid, answer, hinted, revealed, seconds,
              capability, regraded_correct, payload_hash, session_payload)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .bind(
          clientTs,
          serverTs,
          day,
          session,
          r.qid,
          r.answer,
          hinted ? 1 : 0,
          r.revealed ? 1 : 0,
          r.seconds,
          entry && typeof entry.capability === "string" ? entry.capability : null,
          correct === null ? null : correct ? 1 : 0,
          payloadHash,
          JSON.stringify({review_ratings:body.review_ratings ?? [], sentences:body.sentences ?? []}),
        ),
    );
  }

  let changes: number[] = [];
  try {
    if (typeof db.batch === "function") {
      const batchResults = await db.batch(statements);
      changes = batchResults.map((x) => x?.meta?.changes ?? 0);
    } else {
      for (const stmt of statements) {
        const res = await stmt.run();
        changes.push(res?.meta?.changes ?? 0);
      }
    }
  } catch (err) {
    // 表不存在 / D1 异常：明确报错，但不吞成 500 让前端以为成功了。
    return jsonResponse(
      { ok: false, reason: "db_error", detail: String((err as Error)?.message ?? err).slice(0, 200) },
      503,
      origin,
    );
  }

  const stored = changes.filter((n) => n > 0).length;
  const duplicates = changes.length - stored;
  const regraded = answerKey ? graded.filter((x) => x.correct !== null).length : "unavailable";

  return jsonResponse({ ok: true, stored, duplicates, regraded }, 200, origin);
}

// ---------------------------------------------------------------------------
// GET /api/events
// ---------------------------------------------------------------------------

const EVENT_COLUMNS =
  "id, client_ts, server_ts, day, session, qid, answer, hinted, revealed, seconds, capability, regraded_correct, payload_hash, session_payload";

async function handleGetEvents(request: Request, env: Env, url: URL): Promise<Response> {
  const origin = okOrigin(request, url);
  const expected = env.NH80_SYNC_KEY;
  if (!expected) {
    return jsonResponse({ ok: false, reason: "no_key" }, 503, origin);
  }
  const provided = request.headers.get("X-NH80-Key") ?? "";
  if (!constantTimeEqual(provided, expected)) {
    return jsonResponse({ ok: false, reason: "unauthorized" }, 401, origin);
  }
  if (!env.DB) {
    return jsonResponse({ ok: false, reason: "no_db" }, 503, origin);
  }

  const since = asInt(url.searchParams.get("since"), 0, 0, Number.MAX_SAFE_INTEGER) ?? 0;
  const limit = asInt(url.searchParams.get("limit"), 200, 1, 500) ?? 200;

  try {
    const res = await env.DB
      .prepare(`SELECT ${EVENT_COLUMNS} FROM events WHERE id > ? ORDER BY id ASC LIMIT ?`)
      .bind(since, limit)
      .all<Record<string, unknown>>();
    const events = res.results ?? [];
    // 契约要求「返回事件数组」：直接返回数组，按 id 升序；游标由调用方取最后一条的 id。
    return jsonResponse(events, 200, origin);
  } catch (err) {
    return jsonResponse(
      { ok: false, reason: "db_error", detail: String((err as Error)?.message ?? err).slice(0, 200) },
      503,
      origin,
    );
  }
}

// ---------------------------------------------------------------------------
// 入口
// ---------------------------------------------------------------------------

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/api/health" || url.pathname === "/health") {
      return jsonResponse(
        { status: "ok", features: { db: Boolean(env.DB), sync: Boolean(env.NH80_SYNC_KEY) } },
        200,
        okOrigin(request, url),
      );
    }

    if (url.pathname === "/api/events") {
      const denied = rejectCrossOrigin(request, url);
      if (denied) return denied;
      const opt = preflight(request, url);
      if (opt) return opt;

      if (request.method === "POST") return handlePostEvents(request, env, url);
      if (request.method === "GET") return handleGetEvents(request, env, url);
      return jsonResponse({ ok: false, reason: "method_not_allowed" }, 405, okOrigin(request, url));
    }

    // html_handling: "none" 下 assets 不会把 / 映射到 index.html，
    // 这里显式转发，保证首页与 /day-NNN.html 都能用同一套真实路径。
    if (url.pathname === "/") {
      const indexUrl = new URL("/index.html", url.origin).toString();
      return env.ASSETS.fetch(new Request(indexUrl, request));
    }
    return env.ASSETS.fetch(request);
  },
};
