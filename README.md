# Nihongo 150 · 个人 N3 学习系统

150 天的日语资源与会话教学。适合中文母语、韩语母语级的学习者：借助语法迁移，把时间用在词汇、听读和独立造句。

**线上入口：https://nihongo80.cmjfire.workers.dev**

每天网页 42 分钟＋会话 18 分钟。常规日最多 16 个必学词，听力日最多 11 个；完整 2700 词中的其余内容按天提供选学拓展。复习与新词支持卡片/列表及双向遮盖；练习全部为选择题，三道选句必做、七道拓展。必做题答齐且正确率≥70%才计完成，不靠刷完页面。

包含 2700 词、276 语法、620 汉字、1500 句、45 篇可播放的原创合成听力，以及周阅读、阶段检测、假名诊断。韩语提示覆盖全部词汇：2050 条开放词典匹配、650 条 AI 释义。

听力分两层：**每日精听**是 45 篇原创文本的合成音频 + 3 道理解题；**真人听力页**提供 4 条开放许可音频（mp3 / Ogg 双格式，Safari 也可播）可在本页播放，以及 JLPT 官方样题、Irodori、Erin、NHK、免费播客等按阶段分组的免费入口（跳转官方原站，不托管第三方音频）。课程内容与题目经过三路独立复审并修复，详见 [v7 完成报告](reports/v7_completion.md)。

- [怎么学](docs/STUDY_GUIDE.md) · [真人听力页](web/listening.html)
- [接手与构建](HANDOFF.md)
- [v7 完成验收](reports/v7_completion.md)（[v6 验收](reports/v6_completion.md)）
- [三路复审报告](reports/v7_content_review.md) · [课程与题目复审](reports/v7_curriculum_quiz_review.md) · [听力资源调研](reports/v7_listening_sources.md)
- [数据来源与许可](DATA_LICENSES.md) · [外部资源、模型署名与免费额度](docs/RESOURCE_POLICY.md)

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate
python3 -m unittest discover -s tests -p 'test*.py'   # 44 项
node tests/test_worker_access.mjs
```

内容含 AI 释义与 AI 审校，合成音频不是人声录音。系统不调用付费云端 AI，不自动订阅或升级云服务；当前部署使用已核验的 Cloudflare Free。学习能力以实际输出和官方题目自测检验，不将本站短测换算成 JLPT 官方成绩。

词汇等基础数据：OpenJLPT，CC BY-SA 4.0。韩语词典字段：韩国国立国语院 한국어기초사전，CC BY-SA 2.0 KR；整理数据来自 spellcheck-ko/korean-dict-nikl。原创文本合成语音：Kokoro-82M（Apache 2.0）、jf_alpha、UniDic 3.1.0（BSD 选项），完整署名见 [音频 NOTICE](web/audio/NOTICE.txt)。各组件遵守各自许可，外部教材和音频只链接到官方来源。
