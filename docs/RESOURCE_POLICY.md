# 外部资源、本地音频和免费额度

核验日期：2026-11-07。资源目录见 `knowledge/resources.json`；官方资源可改版、撤下或调整条款，使用前应重新确认。免费阅读不等于允许再发布，资源只提供官方链接，不复制第三方教材、题目、翻译或音频。

- [JLPT 官方练习集](https://www.jlpt.jp/e/samples/sampleindex.html) 有 N3 阅读题、五类听力音频、答案和脚本。官方指出所有听力音频含第三方作品；按页面许可使用，仅链接。它包含 2012、2018 两册公开资源，不是无限题库，也不代表当前真题完整程度。
- [JLPT 在线样题](https://www.jlpt.jp/e/samples/forlearners.html) 可先体验各题型；模拟练习以官方练习集为主。
- [Irodori 初中級](https://www.irodori.jpf.go.jp/en/pre-intermediate/pdf.html) 提供 A2/B1 生活日语和音频，也有 A1/A2 内容；级别不等同 JLPT；[条款](https://www.irodori.jpf.go.jp/en/privacy.html)有特定使用限制，本项目仅链接。
- [NPO 多言語多読的免费读物](https://tadoku.org/japanese/en/free-books-en/)适合循序阅读、部分带音频；[指南](https://tadoku.org/japanese/en/free-books-en/note-en/)要求署名 NPO 多言語多読，CC BY-NC-ND 4.0，禁止改编后发布。项目只链接。
- [NHK やさしいことばニュース](https://www3.nhk.or.jp/news/easy/)供阅读时事；只指向官网，新闻难度未按 N3 校准。

## 本机语音（备选，不用于线上）

线上 `web/audio/` 由下一节的 Kokoro 流程生成；`python3 scripts/audio_assets.py` 在 macOS 以系统 `say` 的 Kyoko 日语声音生成原创 AI 草稿 M0096–M0140，再用 `afconvert` 编码，`ffprobe` 测量实际文件时长；依赖这些本机工具和可用的日语声音。只写文件，不向扬声器播放，也不调用收费 API。生成 `data/audio/manifest.json` 和同目录 m4a，仅供本机个人使用，禁止上传公开网站或提交仓库；manifest 的 `text_sha256` 用于防止音频与原文不一致。文本变化后须重跑。音频合成非真人、未经人工试听，读音与语调可能错误；实测音频时长不等于学习所需时间，且不证明 N3 难度。请使用者试听；公开网页使用浏览器设备端 TTS。[Apple macOS 软件许可](https://www.apple.com/legal/sla/docs/macOSSequoia.pdf)将系统声音用于原创项目限于个人非商业用途，公开部署权限不明确。

## Cloudflare 免费方案与限制

[Workers 免费限额](https://developers.cloudflare.com/workers/platform/limits/)：每账户每日 100,000 次 Worker 请求，CPU 每请求 10ms；每版本最多 20,000 个静态文件，单文件 25 MiB。[静态资源计费](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/)说明直接命中资源的请求免费且不限次数，但 `run_worker_first` 命中的请求会调用 Worker，并受其限额制约；资源不支持 Range 时返回完整文件，播放需在实际设备验证。

[D1 免费额度](https://developers.cloudflare.com/d1/platform/pricing/)为每日 500 万行读取、10 万行写入、账户总存储 5 GB；[单数据库上限](https://developers.cloudflare.com/d1/platform/limits/)免费版 500 MB。[超限行为](https://developers.cloudflare.com/d1/reference/faq/)是请求失败而不是自动转成免费额外用量，日限额 UTC 零点重置；存储满后无法继续写入。离线暂存与明确的失败重试应保留，不能把失败显示为已保存。

防付费：保持 Workers Free，不主动升级付费计划、不新增需付费服务；在 Cloudflare 控制台核对账户当前计划、账单与使用量，定期查看 Workers 请求和 D1 读写/存储。免费额度是账户级共享，具体用量及其他账户服务可能另有费用；不能仅凭代码或上述额度保证账单为零。所有阈值和政策以部署时官方文档及实际账户设置为准。

2026-11-07，主代理在 Cloudflare Dashboard 只读核验：Workers Free 显示 Current plan；当时账户当天 Workers 6,639/100,000 次请求，logs 6,673/200,000；生产 Worker 28 次、preview 4 次。计量会变化，此快照不是零账单保证，未更改计费。

## 公开机器合成音频的来源与重建

`web/audio/` 内的 M0096–M0140 使用原创 AI 草稿、本机 CPU 推理生成。声线 `jf_alpha` 来自 [hexgrad/Kokoro-82M v1.0](https://huggingface.co/hexgrad/Kokoro-82M)，模型卡标明 Apache-2.0；固定模型仓库 revision `f3ff3571791e39611d31c381e3a41a3af07b4987`。模型作者列明 [日语音色](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)及[训练数据致谢](https://huggingface.co/hexgrad/Kokoro-82M#creative-commons-attribution)；音频不是人声录音，也不暗示已人工审核。

日语分词使用 The UniDic Consortium 的现代书面语 UniDic 3.1.0，采用其 [BSD 选项](https://clrd.ninjal.ac.jp/unidic/en/)（原作者 The UniDic Consortium，亦见[许可说明](https://clrd.ninjal.ac.jp/unidic/faq.html)）；另使用 [Misaki](https://github.com/hexgrad/misaki)、[pyopenjtalk / Open JTalk](https://github.com/r9y9/pyopenjtalk) 等组件，前者以项目许可为准，后者分别 MIT / Modified BSD。词典及模型只在生成环境中使用，不包含在网页静态文件中。

在 macOS 本机具备 Python 3.12、ffmpeg 时，可在隔离环境安装 `kokoro==0.9.4`、`misaki[ja]==0.9.4`、`soundfile`，运行 `python -m unidic download` 下载字典；按脚本内模型 revision 预先下载 `config.json`、`kokoro-v1_0.pth`、`voices/jf_alpha.pt`，再执行 `python scripts/open_audio_assets.py`。工具要求模型本地缓存完整，并离线推理；安装包/模型/词典下载需联网，不调用付费推理 API。每句独立合成并拼接，以免长文本被模型截断，生成时检查每句有音频、波形有限且非静音，并在完成全部素材后更新文件与 manifest。时长以合成波形长度测得，播放器实际支持、发音、自然度和 N3 难度仍须试听核验。

公开音频随附 `web/audio/NOTICE.txt`：包括模型 revision、音色、训练数据致谢以及 UniDic 作者和 BSD 许可全文；生成器会同步生成该文件。官方音色表中 jf_alpha 的 CC BY 一栏为空，其他列有署名来源的日语音色未用于本批；Kokoro 模型卡另列 Koniwa tnc 和 SIWIS 两项 CC BY 训练数据，声明中保留其名称、作者、来源和许可，不声称具体训练样本与某个输出的对应关系。
