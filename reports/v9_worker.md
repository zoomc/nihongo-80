# v9 Worker 私有复习 API

- `0004_study.sql` 增加事件知识点、按 session 去重的元数据、独立自评事件和一行计划投影。事件与自评在实际插入后由 SQLite 触发器统一计入 UTC 日预算 1000 / 累计 20000；重复行不计，超额回滚整个 D1 batch。既有预算计数保留。
- 判分按天从静态 `/data/grade/day-NNN.json` 读取规范答案 SHA-256，计算相同规范化答案的摘要。分片加载失败返回 503 并要求保留本地数据；明文答案仍仅由本地完整答案表保存。摘要可以通过枚举选项推测，不构成防作弊。
- 个人口令保护 `GET/POST /api/events`、`GET/POST /api/reviews`、`GET /api/study` 和 `POST /api/study-plan`。events 拉取兼容旧事件 `session_payload`；新事件通过 session 表返回。reviews 增量拉取按数字 id 升序，限制 500 条；study 返回最多4000个知识点评分和10000个曾错题（覆盖当前3596个知识点与8007题）以及 CLI 发布的计划。历史自评 again/hard 标记、题目曾错次数与最新判分分开保存。
- 本地验证：`node tests/test_worker_access.mjs` 三项通过；使用临时 Node SQLite 适配器执行全部四个迁移与 Worker，验证重判、元数据、事件/自评幂等、游标、曾错及自评历史、计划、超额回滚和超额时重复重试，全部通过。校验未触碰线上 D1，临时验证脚本未提交。
- 部署前必须对 production 和 preview 各自应用迁移，再部署 Worker 与包含答案分片的静态资源。FSRS 及能力状态仍以本地 SQLite 为准。真实预览D1/Worker联调、浏览器同步和生产只读验收已由主代理完成，见 reports/v9_completion.md。

每请求作答／自评最多40项，低于 [D1 Free 每次调用50条查询限制](https://developers.cloudflare.com/d1/platform/limits/)。同会话元数据冲突返回409并保留导出，不会默默丢失；测试先红后绿，含并发保护。
