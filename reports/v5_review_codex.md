# v5 Codex 独立审查

> 历史审查：本报告记录v5.1时点，当前v6已处理后续范围，见v6_completion.md。不要把下文历史“未解决”当作当前待办。

基线：0fba24e；2026-11-07；先复现，再修改。

## 基线结果

- PASS：`nh80.py validate` 返回 ok:true、150 天、2700/276/620、45 个听力日。
- PASS：19 项既有测试通过；该结果不证明真实学习闭环。
- FAIL P0：45 个听力日仅用 32 个素材；未带理解题。
- FAIL P0：主题轮转只有 15 种；Day 46 问候主题与授受语法不符。
- FAIL P0：页面分钟硬编码，与课程、文档不一致（scripts/build_v5_site.py:304、317、326、332）。
- FAIL P0（新发现）：网页 Q-001-V0 等题号不在本地 questions；scripts/nh80.py:435 拒绝未知题目，pull-cloud 无法导入。
- FAIL P0（新发现）：sync 吞掉错误并直接显示已记录；作答丢失不可见（scripts/build_v5_site.py:258）。
- FAIL P1：brief 存在则直接返回，不按课程更新（scripts/session_v5.py:71）。日报有人工记录，不能用刷新缓存方式覆盖。
- FAIL P1：每日词量与 16/11 设计冲突；且 150 天最多容纳 2175 词，须明确取舍。
- FAIL P1：1839 词缺 ko_hanja、38 词缺例句。缺韩语不能自动认定是和语，也不能编造对应。
- FAIL P1：phase_name 是阶段代码，STATE 显示 P0 P0。
- FAIL P1（新发现）：句子对象携带 answer，题目 rationale 也直接透露答案；检查 answer 字段一个名字不足以证明不泄题。
- FAIL P1（新发现）：汉字 Day 150 一次安排 24 个；复习自评未从 reviewState 传入同步载荷。

## 内容抽样（固定等距，便于复核）

这是 AI 静态复审，未请人工教师审校；不能升级为 verified。

### 词汇 30 条

V0001, V0094, V0187, V0280, V0373, V0466, V0559, V0652, V0746, V0839, V0932, V1025, V1118, V1211, V1304, V1397, V1490, V1583, V1676, V1769, V1862, V1955, V2049, V2142, V2235, V2328, V2421, V2514, V2607, V2700

### 语法 15 条

G0001, G0021, G0040, G0060, G0080, G0099, G0119, G0139, G0158, G0178, G0197, G0217, G0237, G0256, G0276

### 汉字 10 条

K0001, K0070, K0139, K0207, K0276, K0345, K0414, K0482, K0551, K0620

- 词汇：V2514 例句生硬；V2697 将「バン」兼作面包，需区分「パン」。38 条缺例句另列为确定缺项。
- 语法：G0040 的「見て行きます」可在别的语境成立；G0080 的 なら、G0178 的口语省略、G0197 的 をてある不宜一概判非法；先标明语境，不用这些例子判学生语法错误。
- 汉字：10 条抽样未见确定硬错误；K0207 等数据含低频读音，不能把任意读音题设为唯一合法读音。

## 页面抽查

Day 1 / 46 / 47 / 100 / 150：静态结构均有复习、新词、语法、句子、练习；47/100 等听力日额外听力置后。交互与响应式须修复后浏览器实测。

## 修复后验收

以下为修复后实测；未完成项另列。

| 项目 | 当前结论 | 代码或实测证据 |
|---|---|---|
| 听力内容与顺序 | PASS（TTS替代方案） | materials M0096–M0140；45唯一ID、每篇3题、328–363字；build_v5_site.py 的 listen_json 与 HTML 顺序；估算66–73秒，非实测 |
| 主题与当天内容 | PASS | curriculum_v5.py 从当天 grammar pattern/meaning 生成 can_do，不再轮转场景 |
| 时间口径 | PASS（预算一致） | curriculum blocks：网页42+会话18；build_v5_site.py 读取budget；新增复现测试遍历150页求和 |
| brief 刷新 / report保留 | PASS | session_v5.py:57；临时目录先写 stale，再普通 brief 生成；report人工内容保持 |
| 题目判分闭环 | PASS（隔离实测） | quiz_v5.py统一生成；nh80 build登记1035道当天题（900普通+135听力）；Worker打包答案，本地重判 |
| 提交失败冒充成功 | PASS | HTTP503→失败可重试；之后200→确认保存；作答不带correct |
| Day81–150接口被拒（新发现） | PASS | Worker范围从80改150；本地Day150 POST返回 stored9/regraded9 |
| 同天重做被误去重（新发现） | PASS | cmd_import_web保留原始session；新增第25测试先失败，再修复后通过 |
| 复习与草稿丢失（新发现） | PASS（隔离实测） | migration0002保存session_payload；cloud_sync恢复元数据；CLI复习排期、草稿落盘；不自动评分句子 |
| 明文参考答案 | PASS（不等于防作弊） | public_question只投影五字段；句子删除answer*；旧公开answer-key.json移除，Worker答案只打包；哈希可枚举 |
| 38条缺例句 | PASS（字段补齐） | vocabulary seeds已有例句；V1508按いだく写心理例句、V1574按うわ写上の空，未升级verified |
| P0 P0 / 汉字最后一天堆积 | PASS | phase_name输出真实名称；汉字均衡为每天4–5个（旧Day150为24个） |
| 个人状态入库 | PASS（当前版本不再跟踪） | student/*.json移出版本索引，保留本机，init自动生成；DB/密钥/运行时目录均ignore；不清除Git历史 |
| 词量16/11 | 未解决 | 105×16+45×11=2175，与2700差525；保留全覆盖，等用户选择减量/延期/较高负载 |
| 韩语汉字音 | 部分处理 | 仍缺1839条，未知显示待核对；不猜填，不把未知归为和语 |
| 全库人工审校 | 未解决 | 仅AI抽样与确定缺项修补，不声称人工验证 |

## 具体专项验证

1. 修复前：19既有测试PASS；新增5个复现均FAIL（分钟、听力、明文解析、brief、题号登记）。实施后转绿。之后独立会话重做复现再增加1个测试，修复前FAIL、修复后PASS。没有在实现后补镜像测试或改旧断言。
2. 最终：`nh80 init`成功；`validate` ok:true/error_count0、150天、2700/276/620、45听力日；25项测试OK。测试运行存在SQLite连接ResourceWarning（测试连接释放提示），未出现用例失败。
3. 浏览器：Day1/46/47/100/150 × 375/1280，10组均通过。Day100按实际排期不是听力日；Day47/150验证听力六块，普通日五块。全局/单卡四态、6/6判分、无横向滚动、无pageerror、HTTP失败后重试成功、提交无correct。证据：`evidence/v5.1-browser.json`，`evidence/v5.1-listening-375.png`、`evidence/v5.1-listening-1280.png`。
4. 本地真实Worker+D1：Day150首次POST `stored:9,duplicates:0,regraded:9`；重复POST `stored:0,duplicates:9,regraded:9`；SQL确认9条元数据保存。没有往生产库写测试作答。
5. 隔离数据库：保留真实库的只读快照，在临时目录调用nh80；9题本地重判为对（即使客户端谎报correct:false）、再次导入9题去重、错误day拒绝、不同session9题可重做；cloud_sync从真实本地D1事件恢复复习/草稿，CLI生成web-drafts.json。测试未给真实学生增加attempts。
6. 发布：远程0001/0002迁移成功。preview版本`2ad7e6d7-6fae-4f26-bf81-469ebefa8816`；最终production版本`0237b65b-0623-4062-b404-02d9cf6a548f`。后者为最终版，preview不是逐字同版。
7. 线上：curl验证Day1/47/150均200且与本地构建逐字一致；app.js同样一致；health为ok/db:true/sync:true。完整SHA见`evidence/v5.1-production.json`。Python urllib访问曾403，换curl验证成功，未据urllib失败宣称生产故障。
8. Git历史中的个人状态没有重写清除，当前版本移出跟踪；本机内容保持。未操作Surge或家庭网络引擎。

## 教材审查依据与限制

G0040不能将「見て行きます」绝对判错：东京外国语大学的[Vていきます／Vてきます说明](https://www.coelang.tufs.ac.jp/mt/ja/gmod/contents/explanation/087.html)明确给出看新闻后去上课的用例。本次将其改为目的表达与动作先后的语义辨析。G0080/G0178/G0197留为needs_review，不以未经人工复核的对比例句判学生语法错误。

本次没有接入外部教材音频，也没有复制受限教材正文。新增TTS是九类场景的五组事实变体，不冒充45篇独立人工审校录音。实际时长、发音自然度、难度与已知词率均待验收。42分钟只是预算，不代表真人学习完成用时已证实。

其他仍未修的P2：旧脚本/历史文档仍保留，已用当前入口隔离；首页仍平铺150天。生产真实学生作答→本地权威状态的完整流程未以真实学习记录验收，本次证明范围限于本地Worker+D1及隔离SQLite。
