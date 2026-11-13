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
  first<T = Record<string, unknown>>(): Promise<T | null>;
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
  day: number;
  type: string;
  answer_hash: string;
  knowledge_ids: string[];
  capability?: string;
}
type AnswerKey = Map<string, KeyEntry>;

async function loadAnswerKey(env: Env, url: URL, day: number): Promise<AnswerKey | null> {
  try {
    const path = `/data/grade/day-${String(day).padStart(3, "0")}.json`;
    const response = await env.ASSETS.fetch(new Request(new URL(path, url.origin)));
    if (!response.ok) return null;
    const data = await response.json() as { answers?: Record<string, KeyEntry> };
    if (!data.answers || typeof data.answers !== "object" || Array.isArray(data.answers)) return null;
    return new Map(Object.entries(data.answers));
  } catch { return null; }
}

async function regrade(entry: KeyEntry | undefined, answer: unknown): Promise<boolean | null> {
  if (!entry || entry.type !== "mcq" || !/^[a-f0-9]{64}$/.test(entry.answer_hash ?? "")) return null;
  return constantTimeEqual(await sha256Hex(norm(answer)), entry.answer_hash);
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
  if (value === null || value === undefined || value === "") return fallback;
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
  if (!env.NH80_SYNC_KEY) return jsonResponse({ok:false,reason:"no_key"},503,origin);
  if (!constantTimeEqual(request.headers.get("X-NH80-Key") ?? "",env.NH80_SYNC_KEY))
    return jsonResponse({ok:false,reason:"unauthorized"},401,origin);
  const rawBody = await request.text();
  if (new TextEncoder().encode(rawBody).length > MAX_BODY_BYTES) {
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

  const dbHandle = env.DB;
  if (body.check === true) {
    // Owner-only deployment smoke check: exercise the D1 binding without storing events.
    if (!dbHandle) return jsonResponse({ ok: false, reason: "no_db" }, 503, origin);
    try {
      await dbHandle.prepare("SELECT id FROM sync_budget WHERE id='total'").first();
      return jsonResponse({ ok: true, check: true, stored: 0, day }, 200, origin);
    } catch { return jsonResponse({ ok: false, reason: "db_error" }, 503, origin); }
  }

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

  const answerKey = await loadAnswerKey(env, url, day);
  if (!answerKey) return jsonResponse({ok:false,reason:"grade_unavailable",local_export:true},503,origin);
  const wrong = results.find(r => {
    const entry = answerKey.get(r.qid);
    return !entry || entry.day !== day || entry.type !== "mcq" ||
      !/^[a-f0-9]{64}$/.test(entry.answer_hash ?? "") || !Array.isArray(entry.knowledge_ids) ||
      entry.knowledge_ids.some(k => typeof k !== "string" || !/^[VGK]\d{4}$/.test(k));
  });
  if (wrong) return jsonResponse({ok:false,reason:"unknown_or_wrong_day_question",local_export:true},400,origin);
  const serverTs = new Date().toISOString();
  const metadata = JSON.stringify({review_ratings:body.review_ratings ?? [],sentences:body.sentences ?? [],practice_mode:body.practice_mode === "choice" ? "choice" : "teacher"});
  if (new TextEncoder().encode(metadata).length > 16384) return jsonResponse({ok:false,reason:"drafts_too_large",local_export:true},413,origin);
  try {
    const existing = await db.prepare("SELECT day,payload FROM study_sessions WHERE session=?").bind(session).first<{day:number,payload:string}>();
    if (existing && existing.day !== day) return jsonResponse({ok:false,reason:"session_day_conflict",local_export:true},409,origin);
    if (existing && existing.payload !== metadata) return jsonResponse({ok:false,reason:"session_metadata_conflict",local_export:true},409,origin);
    // The guarded upsert also detects concurrent conflicting first submissions;
    // a NOT NULL violation aborts the entire D1 batch before any event is committed.
    const statements: D1PreparedStatement[] = [db.prepare(`INSERT INTO study_sessions(session,day,payload) VALUES(?,?,?)
      ON CONFLICT(session) DO UPDATE SET payload=CASE
        WHEN study_sessions.day=excluded.day AND study_sessions.payload=excluded.payload
        THEN study_sessions.payload ELSE NULL END`).bind(session,day,metadata)];
    for (const r of results) {
      const entry = answerKey.get(r.qid)!;
      const correct = await regrade(entry, r.answer);
      const hinted = r.hinted || r.revealed;
      const payloadHash = await sha256Hex(JSON.stringify([day,session,r.qid,r.answer,hinted,r.revealed,r.seconds,clientTs ?? ""]));
      statements.push(db.prepare(`INSERT OR IGNORE INTO events
        (client_ts,server_ts,day,session,qid,answer,hinted,revealed,seconds,capability,regraded_correct,payload_hash,session_payload,knowledge_ids)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,?)`)
        .bind(clientTs,serverTs,day,session,r.qid,r.answer,hinted?1:0,r.revealed?1:0,r.seconds,
          entry.capability ?? null,correct === null ? null : correct ? 1 : 0,payloadHash,JSON.stringify(entry.knowledge_ids)));
    }
    if (!db.batch) throw new Error("batch_unavailable");
    const batch = await db.batch(statements);
    const stored = batch.slice(1).filter(x => (x.meta?.changes ?? 0) > 0).length;
    return jsonResponse({ok:true,stored,duplicates:results.length-stored,regraded:results.length},200,origin);
  } catch (err) {
    if (String((err as Error)?.message ?? err).includes("NOT NULL constraint failed: study_sessions.payload"))
      return jsonResponse({ok:false,reason:"session_metadata_conflict",local_export:true},409,origin);
    return databaseError(err,origin);
  }
}

// ---------------------------------------------------------------------------
// GET /api/events
// ---------------------------------------------------------------------------

const EVENT_COLUMNS = `e.id, e.client_ts, e.server_ts, e.day, e.session, e.qid, e.answer,
 e.hinted, e.revealed, e.seconds, e.capability, e.regraded_correct, e.payload_hash,
 COALESCE(e.session_payload, s.payload) AS session_payload, e.knowledge_ids`;

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
      .prepare(`SELECT ${EVENT_COLUMNS} FROM events e LEFT JOIN study_sessions s ON s.session=e.session WHERE e.id > ? ORDER BY e.id ASC LIMIT ?`)
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

function databaseError(err: unknown, origin: string | null): Response {
  const message = String((err as Error)?.message ?? err);
  const reason = message.includes("daily_budget") ? "daily_budget" : message.includes("storage_budget") ? "storage_budget" : "db_error";
  return jsonResponse({ok:false,reason,local_export:true},reason === "db_error" ? 503 : 429,origin);
}

function authenticate(request: Request, env: Env, origin: string | null): Response | null {
  if (!env.NH80_SYNC_KEY) return jsonResponse({ok:false,reason:"no_key"},503,origin);
  if (!constantTimeEqual(request.headers.get("X-NH80-Key") ?? "",env.NH80_SYNC_KEY))
    return jsonResponse({ok:false,reason:"unauthorized"},401,origin);
  if (!env.DB) return jsonResponse({ok:false,reason:"no_db",local_export:true},503,origin);
  return null;
}

async function readJson(request: Request, maxBytes: number): Promise<Record<string, unknown> | string> {
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > maxBytes) return "body_too_large";
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return "bad_json";
    return parsed;
  } catch { return "bad_json"; }
}

async function handleReviews(request: Request, env: Env, url: URL): Promise<Response> {
  const origin = okOrigin(request,url);
  const denied = authenticate(request,env,origin); if (denied) return denied;
  const db = env.DB!;
  try {
    if (request.method === "GET") {
      const since = asInt(url.searchParams.get("since"),0,0,Number.MAX_SAFE_INTEGER) ?? 0;
      const limit = asInt(url.searchParams.get("limit"),200,1,500) ?? 200;
      const rows = await db.prepare("SELECT id,event_id,kid,day,rating,created_at FROM rating_events WHERE id>? ORDER BY id ASC LIMIT ?").bind(since,limit).all();
      return jsonResponse(rows.results ?? [],200,origin);
    }
    if (request.method !== "POST") return jsonResponse({ok:false,reason:"method_not_allowed"},405,origin);
    const body = await readJson(request,MAX_BODY_BYTES);
    if (typeof body === "string") return jsonResponse({ok:false,reason:body,local_export:true},body === "body_too_large" ? 413 : 400,origin);
    if (!Array.isArray(body.reviews) || body.reviews.length < 1 || body.reviews.length > 40)
      return jsonResponse({ok:false,reason:"bad_reviews",local_export:true},400,origin);
    const now = new Date().toISOString();
    const statements: D1PreparedStatement[] = [];
    for (const raw of body.reviews) {
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) return jsonResponse({ok:false,reason:"bad_review",local_export:true},400,origin);
      const r = raw as Record<string,unknown>;
      if (typeof r.event_id !== "string" || !/^[A-Za-z0-9_.:-]{3,96}$/.test(r.event_id) ||
          typeof r.kid !== "string" || !/^[VGK]\d{4}$/.test(r.kid) || strictInt(r.day,1,150) === null ||
          !["again","hard","good"].includes(String(r.rating)))
        return jsonResponse({ok:false,reason:"bad_review",local_export:true},400,origin);
      statements.push(db.prepare("INSERT OR IGNORE INTO rating_events(event_id,kid,day,rating,created_at) VALUES(?,?,?,?,?)").bind(r.event_id,r.kid,r.day,r.rating,now));
    }
    if (!db.batch) throw new Error("batch_unavailable");
    const out = await db.batch(statements);
    const stored = out.filter(x => (x.meta?.changes ?? 0)>0).length;
    return jsonResponse({ok:true,stored,duplicates:statements.length-stored},200,origin);
  } catch (err) { return databaseError(err,origin); }
}

async function handleStudyPlan(request: Request, env: Env, url: URL): Promise<Response> {
  const origin = okOrigin(request,url);
  const denied = authenticate(request,env,origin); if (denied) return denied;
  if (request.method !== "POST") return jsonResponse({ok:false,reason:"method_not_allowed"},405,origin);
  const body = await readJson(request,128*1024);
  if (typeof body === "string") return jsonResponse({ok:false,reason:body,local_export:true},body === "body_too_large" ? 413 : 400,origin);
  const plan = body.plan;
  if (!plan || typeof plan !== "object" || Array.isArray(plan) || typeof (plan as any).updated_at !== "string" ||
      !Array.isArray((plan as any).due) || (plan as any).due.length > 1000 ||
      (plan as any).due.some((d: any) => !d || typeof d !== "object" || typeof d.kid !== "string" || !/^[VGK]\d{4}$/.test(d.kid) ||
       typeof d.due !== "string" || typeof d.stage !== "string" || !["string","number"].includes(typeof d.priority)))
    return jsonResponse({ok:false,reason:"bad_plan",local_export:true},400,origin);
  try {
    await env.DB!.prepare("INSERT INTO study_projection(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload").bind(JSON.stringify(plan)).run();
    return jsonResponse({ok:true},200,origin);
  } catch (err) { return databaseError(err,origin); }
}

async function handleStudy(request: Request, env: Env, url: URL): Promise<Response> {
  const origin = okOrigin(request,url);
  const denied = authenticate(request,env,origin); if (denied) return denied;
  if (request.method !== "GET") return jsonResponse({ok:false,reason:"method_not_allowed"},405,origin);
  try {
    const db = env.DB!;
    const ratings = await db.prepare(`SELECT r.kid,r.rating,r.day,r.created_at,
      EXISTS(SELECT 1 FROM rating_events b WHERE b.kid=r.kid AND b.rating IN ('again','hard')) AS ever_bad
      FROM rating_events r WHERE r.id=(SELECT MAX(x.id) FROM rating_events x WHERE x.kid=r.kid)
      ORDER BY r.id DESC LIMIT 4000`).all();
    const questions = await db.prepare(`SELECT e.qid,e.day,e.knowledge_ids,e.regraded_correct AS last_correct,
      (SELECT COUNT(*) FROM events w WHERE w.qid=e.qid AND w.day=e.day AND w.regraded_correct=0) AS wrong_count
      FROM events e WHERE e.id=(SELECT MAX(x.id) FROM events x WHERE x.qid=e.qid AND x.day=e.day)
      AND EXISTS(SELECT 1 FROM events w WHERE w.qid=e.qid AND w.day=e.day AND w.regraded_correct=0)
      ORDER BY e.id DESC LIMIT 10000`).all();
    const projection = await db.prepare("SELECT payload FROM study_projection WHERE id=1").first<{payload:string}>();
    const rows = (questions.results ?? []).map((row: any) => {
      let ids: unknown = []; try { ids = JSON.parse(row.knowledge_ids ?? "[]"); } catch { /* legacy */ }
      return {...row,knowledge_ids:Array.isArray(ids) ? ids : []};
    });
    return jsonResponse({ratings:ratings.results ?? [],questions:rows,plan:projection ? JSON.parse(projection.payload) : null},200,origin);
  } catch (err) { return databaseError(err,origin); }
}

// ---------------------------------------------------------------------------
// /api/progress — 当天完成快照（公开写、鉴权读；自报，非掌握权威）
// ---------------------------------------------------------------------------
// 与 /api/events 完全解耦：独立表 study_progress（day 主键覆盖，≤150 行）。
// POST 无用户口令，靠 Origin 白名单 + content-type + 64KB 双检 + 字段白名单
// + 每 IP/每日与全局每日限流（复用 sync_budget）保护 D1 写额度。
// GET 必须 X-NH80-Key（复用 authenticate / constantTimeEqual）。
// 服务端不重判 questions[].correct：整份快照以 self_reported=1 标注，
// 权威完成/FSRS 只由本机 SQLite（nh80.py finish-day）负责。

const PROGRESS_SITE_ORIGINS = new Set([
  "https://nihongo80.cmjfire.workers.dev",
  "https://nihongo80-preview.cmjfire.workers.dev",
]);
const PROGRESS_MAX_QUESTIONS = 65;
const PROGRESS_MAX_IDS = 200;
const PROGRESS_MAX_NOTE = 2000;
const PROGRESS_MAX_ANSWER = 2000;
const PROGRESS_MAX_QID = 48;
const PROGRESS_IP_DAILY_LIMIT = 50;
const PROGRESS_GLOBAL_DAILY_LIMIT = 500;
const PROGRESS_LIMIT_DEFAULT = 7;

type ProgressObject = Record<string, unknown>;

/** 无 Origin：允许但强制 content-type 与全套强限制；有 Origin：须在白名单。 */
function progressOrigin(request: Request, url: URL): { allowed: boolean; corsOrigin: string | null } {
  const origin = request.headers.get("Origin");
  if (!origin) return { allowed: true, corsOrigin: null };
  let parsed: URL;
  try { parsed = new URL(origin); } catch { return { allowed: false, corsOrigin: null }; }
  const isLoopback = parsed.protocol === "http:" &&
    (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost");
  const isSite = parsed.origin === url.origin || PROGRESS_SITE_ORIGINS.has(parsed.origin);
  if (!isLoopback && !isSite) return { allowed: false, corsOrigin: null };
  return { allowed: true, corsOrigin: origin };
}

function progressPreflight(corsOrigin: string | null): Response {
  const headers = new Headers({
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "content-type, x-nh80-key",
    "access-control-max-age": "86400",
    "vary": "Origin",
  });
  if (corsOrigin) headers.set("access-control-allow-origin", corsOrigin);
  return new Response(null, { status: 204, headers });
}

function progressId(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= 24 &&
    /^[A-Za-z0-9_-]+$/.test(value);
}

function progressQid(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= PROGRESS_MAX_QID &&
    /^[A-Za-z0-9_.:-]+$/.test(value);
}

function progressIdList(value: unknown, max: number): string[] | null {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.length > max) return null;
  const out: string[] = [];
  for (const item of value) {
    if (!progressId(item)) return null;
    out.push(item);
  }
  return out;
}

/** 字段白名单 + 逐项校验；返回规范化对象（未知字段一律丢弃）或错误 reason。 */
function parseProgressBody(body: ProgressObject): ProgressObject | string {
  if (body.v !== 4) return "bad_version";
  const day = strictInt(body.day, 1, 150);
  if (day === null) return "bad_day";

  const requiredIds = progressIdList(body.required_ids, PROGRESS_MAX_IDS);
  const extraIds = progressIdList(body.extra_ids, PROGRESS_MAX_IDS);
  const grammarIds = progressIdList(body.grammar_ids, PROGRESS_MAX_IDS);
  if (requiredIds === null || extraIds === null || grammarIds === null) return "bad_ids";

  const reviewSummary = progressIdList(body.review_summary, PROGRESS_MAX_IDS);
  if (reviewSummary === null) return "bad_review_summary";

  const questions: ProgressObject[] = [];
  if (body.questions !== undefined && body.questions !== null) {
    if (!Array.isArray(body.questions) || body.questions.length > PROGRESS_MAX_QUESTIONS) return "bad_questions";
    for (const raw of body.questions) {
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) return "bad_questions";
      const q = raw as ProgressObject;
      if (!progressQid(q.qid)) return "bad_questions";
      const answer = typeof q.answer === "string" ? q.answer : "";
      if (answer.length > PROGRESS_MAX_ANSWER) return "answer_too_long";
      const seconds = q.seconds === undefined || q.seconds === null
        ? null : asInt(q.seconds, null, 0, 86400);
      // correct/hinted/revealed 原样保留，但服务端不采信 correct 为权威（整体 self_reported=1）。
      questions.push({
        qid: q.qid,
        answer,
        correct: q.correct === true,
        hinted: q.hinted === true,
        revealed: q.revealed === true,
        seconds,
      });
    }
  }

  const selfRating: Record<string, string> = {};
  if (body.self_rating !== undefined && body.self_rating !== null) {
    const sr = body.self_rating;
    if (typeof sr !== "object" || Array.isArray(sr)) return "bad_self_rating";
    const entries = Object.entries(sr as ProgressObject);
    if (entries.length > PROGRESS_MAX_IDS) return "bad_self_rating";
    for (const [kid, rating] of entries) {
      if (!progressId(kid) || !["again", "hard", "good"].includes(String(rating))) return "bad_self_rating";
      selfRating[kid] = String(rating);
    }
  }

  const wrongSummary: ProgressObject[] = [];
  if (body.wrong_summary !== undefined && body.wrong_summary !== null) {
    if (!Array.isArray(body.wrong_summary) || body.wrong_summary.length > PROGRESS_MAX_QUESTIONS) return "bad_wrong_summary";
    for (const raw of body.wrong_summary) {
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) return "bad_wrong_summary";
      const w = raw as ProgressObject;
      if (!progressQid(w.qid)) return "bad_wrong_summary";
      const kids = progressIdList(w.knowledge_ids, 20);
      if (kids === null) return "bad_wrong_summary";
      wrongSummary.push({ qid: w.qid, knowledge_ids: kids });
    }
  }

  const accuracy = typeof body.accuracy === "number" && Number.isFinite(body.accuracy) &&
    body.accuracy >= 0 && body.accuracy <= 1 ? body.accuracy : null;
  if (typeof body.note === "string" && body.note.length > PROGRESS_MAX_NOTE) return "note_too_large";

  return {
    v: 4,
    day,
    completed_at: typeof body.completed_at === "string" ? body.completed_at.slice(0, 40) : "",
    required_ids: requiredIds,
    extra_ids: extraIds,
    grammar_ids: grammarIds,
    questions,
    accuracy,
    self_rating: selfRating,
    wrong_summary: wrongSummary,
    review_summary: reviewSummary,
    note: typeof body.note === "string" ? body.note.slice(0, PROGRESS_MAX_NOTE) : "",
    self_reported: 1,
  };
}

async function progressIpKey(request: Request, env: Env, utcDay: string): Promise<string> {
  const ip = request.headers.get("CF-Connecting-IP") ?? "local";
  const digest = await sha256Hex(ip + "|" + (env.NH80_SYNC_KEY ?? "nh80-progress"));
  return "progress_ip:" + utcDay + ":" + digest.slice(0, 12);
}

/** 复用 sync_budget 的 UPSERT 计数行（不追加行数）；返回是否仍在额度内。 */
async function progressBudget(db: D1Database, key: string, limit: number): Promise<boolean> {
  await db.prepare("INSERT INTO sync_budget(id,used) VALUES(?,1) ON CONFLICT(id) DO UPDATE SET used=used+1")
    .bind(key).run();
  const row = await db.prepare("SELECT used FROM sync_budget WHERE id=?").bind(key).first<{ used: number }>();
  return (row?.used ?? 1) <= limit;
}

async function handleGetProgress(env: Env, url: URL, origin: string | null): Promise<Response> {
  const db = env.DB!;
  const dayParam = url.searchParams.get("day");
  const latestParam = url.searchParams.get("latest");
  try {
    let res: D1Result<Record<string, unknown>>;
    if (dayParam !== null) {
      const day = strictInt(dayParam, 1, 150);
      if (day === null) return jsonResponse({ ok: false, reason: "bad_query" }, 400, origin);
      res = await db.prepare("SELECT day,server_ts,completed_at,payload,accuracy,self_reported FROM study_progress_120 WHERE day=?")
        .bind(day).all<Record<string, unknown>>();
    } else if (latestParam !== null && latestParam !== "0") {
      const limit = asInt(url.searchParams.get("limit"), PROGRESS_LIMIT_DEFAULT, 1, 150) ?? PROGRESS_LIMIT_DEFAULT;
      res = await db.prepare("SELECT day,server_ts,completed_at,payload,accuracy,self_reported FROM study_progress_120 ORDER BY server_ts DESC, day DESC LIMIT ?")
        .bind(limit).all<Record<string, unknown>>();
    } else {
      return jsonResponse({ ok: false, reason: "bad_query" }, 400, origin);
    }
    const items = (res.results ?? []).map((row) => {
      let payload: ProgressObject = {};
      try { payload = JSON.parse(String(row.payload ?? "{}")) as ProgressObject; } catch { /* corrupt row */ }
      return { ...payload, day: row.day, server_ts: row.server_ts, self_reported: row.self_reported ?? 1 };
    });
    return jsonResponse({ ok: true, items }, 200, origin);
  } catch (err) {
    return jsonResponse(
      { ok: false, reason: "db_error", detail: String((err as Error)?.message ?? err).slice(0, 200) },
      503, origin,
    );
  }
}

async function handleProgress(request: Request, env: Env, url: URL): Promise<Response> {
  const { allowed, corsOrigin } = progressOrigin(request, url);
  if (!allowed) return jsonResponse({ ok: false, reason: "cross_origin" }, 403, null);
  if (request.method === "OPTIONS") return progressPreflight(corsOrigin);

  if (request.method === "GET") {
    const denied = authenticate(request, env, corsOrigin);
    if (denied) return denied;
    return handleGetProgress(env, url, corsOrigin);
  }
  if (request.method !== "POST") {
    return jsonResponse({ ok: false, reason: "method_not_allowed" }, 405, corsOrigin);
  }

  // 无 Origin 时也强制 JSON content-type；curl/CLI 冒烟需显式带 -H content-type。
  const contentType = (request.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
  if (contentType !== "application/json") {
    return jsonResponse({ ok: false, reason: "bad_content_type" }, 400, corsOrigin);
  }
  const declared = request.headers.get("content-length");
  if (declared !== null) {
    const n = Number(declared);
    if (!Number.isFinite(n) || n > MAX_BODY_BYTES) {
      return jsonResponse({ ok: false, reason: "body_too_large" }, 413, corsOrigin);
    }
  }
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > MAX_BODY_BYTES) {
    return jsonResponse({ ok: false, reason: "body_too_large" }, 413, corsOrigin);
  }
  let body: ProgressObject;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("bad");
    body = parsed as ProgressObject;
  } catch {
    return jsonResponse({ ok: false, reason: "bad_json" }, 400, corsOrigin);
  }
  const normalized = parseProgressBody(body);
  if (typeof normalized === "string") {
    return jsonResponse({ ok: false, reason: normalized }, 400, corsOrigin);
  }
  const db = env.DB;
  if (!db) return jsonResponse({ ok: false, reason: "no_db" }, 503, corsOrigin);

  const utcDay = new Date().toISOString().slice(0, 10);
  const serverTs = new Date().toISOString();
  try {
    if (!(await progressBudget(db, "progress_day:" + utcDay, PROGRESS_GLOBAL_DAILY_LIMIT))) {
      return jsonResponse({ ok: false, reason: "daily_write_budget" }, 429, corsOrigin);
    }
    if (!(await progressBudget(db, await progressIpKey(request, env, utcDay), PROGRESS_IP_DAILY_LIMIT))) {
      return jsonResponse({ ok: false, reason: "ip_write_budget" }, 429, corsOrigin);
    }
    const day = normalized.day as number;
    const payload = JSON.stringify(normalized);
    await db.prepare(`INSERT INTO study_progress_120(day,server_ts,completed_at,payload,accuracy,self_reported)
      VALUES(?,?,?,?,?,1)
      ON CONFLICT(day) DO UPDATE SET server_ts=excluded.server_ts,
        completed_at=excluded.completed_at, payload=excluded.payload,
        accuracy=excluded.accuracy, self_reported=1`)
      .bind(day, serverTs, String(normalized.completed_at ?? ""), payload, normalized.accuracy as number | null)
      .run();
    return jsonResponse({ ok: true, day, saved: true }, 200, corsOrigin);
  } catch (err) {
    return databaseError(err, corsOrigin);
  }
}

// ---------------------------------------------------------------------------
// 入口
// ---------------------------------------------------------------------------

const SESSION = "__Host-nh80_account";
const LOGIN_CODE = /^[0-9a-f]{64}$/;

function sessionResponse(account: string, code: string, maxAge = 31536000): Response {
  const response = jsonResponse({ ok: true, account }, 200, null);
  response.headers.set("set-cookie",
    `${SESSION}=${code}; Path=/; Max-Age=${maxAge}; Secure; HttpOnly; SameSite=Strict`);
  return response;
}

async function handleCourseAccount(request: Request, env: Env, url: URL): Promise<Response> {
  const fail = (reason: string, status: number) => jsonResponse({ ok: false, reason }, status, null);
  const origin = request.headers.get("origin");
  if ((origin && origin !== url.origin) || (request.method !== "GET" && origin !== url.origin)) {
    return fail("cross_origin", 403);
  }
  const db = env.DB;
  if (!db) return fail("no_db", 503);
  const credential = request.headers.get("cookie")?.match(/(?:^|;\s*)__Host-nh80_account=([0-9a-f]{64})(?:;|$)/)?.[1];
  const account = credential ? await sha256Hex("nh80-account:" + credential) : "";
  const action = url.pathname.split("/").pop();
  try {
    if (request.method === "POST" && action === "logout") return sessionResponse("", "", 0);
    if (request.method === "POST" && action === "login") {
      if (!request.headers.get("content-type")?.startsWith("application/json")) return fail("bad_json", 400);
      const body = await readJson(request, 2048);
      if (typeof body === "string") return fail(body, 400);
      if (typeof body.code !== "string" || !LOGIN_CODE.test(body.code)) return fail("bad_code", 400);
      const id = await sha256Hex("nh80-account:" + body.code);
      if (body.create === true) {
        const ip = await progressIpKey(request, env, new Date().toISOString().slice(0, 10));
        if (!(await progressBudget(db, "account:" + ip, 12))) return fail("rate_limit", 429);
        const result = await db.prepare("INSERT OR IGNORE INTO course_accounts(id) VALUES(?)").bind(id).run();
        if (!result.meta?.changes) return fail("account_exists", 409);
      } else if (!await db.prepare("SELECT 1 FROM course_accounts WHERE id=?").bind(id).first()) {
        return fail("invalid_code", 401);
      }
      return sessionResponse(id, body.code);
    }
    if (action !== "state" || !["GET", "POST"].includes(request.method)) return fail("method_not_allowed", 405);
    if (!account) return fail("not_logged_in", 401);
    if (request.method === "POST") {
      if (!request.headers.get("content-type")?.startsWith("application/json")) return fail("bad_json", 400);
      const body = await readJson(request, 4096);
      if (typeof body === "string") return fail(body, 400);
      const { days, last, opened } = body;
      if (body.account !== account) return fail("different_account", 409);
      if (!Array.isArray(days) || days.length > 150 || days.some(day => typeof day !== "number" || strictInt(day, 1, 150) === null) ||
          typeof last !== "number" || strictInt(last, 0, 150) === null ||
          typeof opened !== "number" || strictInt(opened, 0, Date.now() + 300000) === null || (last === 0 && opened !== 0)) {
        return fail("bad_state", 400);
      }
      await db.prepare(`UPDATE course_accounts SET
        days=(SELECT json_group_array(day) FROM (
          SELECT value AS day FROM json_each(course_accounts.days)
          UNION SELECT value FROM json_each(?1) ORDER BY day)),
        last_day=CASE WHEN ?3 > opened_at THEN ?2 ELSE last_day END,
        opened_at=max(opened_at, ?3) WHERE id=?4`).bind(JSON.stringify(days), last, opened, account).run();
    }
    const row = await db.prepare("SELECT days,last_day,opened_at FROM course_accounts WHERE id=?")
      .bind(account).first<{days: string; last_day: number; opened_at: number}>();
    return row ? jsonResponse({ ok: true, account, days: JSON.parse(row.days), last: row.last_day, opened: row.opened_at }, 200, null)
      : fail("not_logged_in", 401);
  } catch {
    return fail("sync_unavailable", 503);
  }
}

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

    if (url.pathname.startsWith("/api/account/")) return handleCourseAccount(request, env, url);
    if (url.pathname === "/api/app-version" && request.method === "GET") {
      const version = await env.ASSETS.fetch(new Request(new URL("/version.json", url.origin)));
      return new Response(version.body, {
        status: version.status, headers: { "cache-control": "no-store", "content-type": "application/json" },
      });
    }

    // 独立分支：/api/progress 需允许 production/preview/本地回环三类 Origin，
    // 不能套用只认同源的 rejectCrossOrigin，也不改动既有路由数组的任何行为。
    if (url.pathname === "/api/progress") {
      return handleProgress(request, env, url);
    }

    if (["/api/events", "/api/reviews", "/api/study", "/api/study-plan"].includes(url.pathname)) {
      const denied = rejectCrossOrigin(request, url);
      if (denied) return denied;
      const opt = preflight(request, url);
      if (opt) return opt;

      if (url.pathname === "/api/reviews") return handleReviews(request,env,url);
      if (url.pathname === "/api/study") return handleStudy(request,env,url);
      if (url.pathname === "/api/study-plan") return handleStudyPlan(request,env,url);
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
