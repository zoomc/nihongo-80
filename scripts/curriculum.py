"""curriculum.py — 由真实知识种子生成 80 天完整课程 + 先修校验 + 分级兑现报告。

理论依据：research/nh80_framework.md（NH80 高频压缩习得法）。
不照抄任何一套教材的课序；按「多套教材综合提炼的原则」做确定性重排：
高频优先、场景 Can-do 驱动、变形先行拓扑、中日韩迁移但强制验证、N3 能力锚定。

诚实声明：课程由程序从已审核种子组装（review_status=generated），不是 80 篇人工精修教材。
骨架（知识目标）稳定；动态任务（实际复习/练习）由 state.db 的 plan_adjustments/review_tasks 决定。
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from core import iso, jdump, read_jsonl, root_of

PHASES = [("P1", 1, 10, "音形底座与判断句：假名、发音、は/が、です/ます"),
          ("P2", 11, 25, "高频日常 Can-do：N5 核心词、基础变形与场景输出"),
          ("P3", 26, 45, "动词系统总攻：N4 词/汉字、てたない形复合与授受"),
          ("P4", 46, 65, "N3 高频冲刺：N3 词/汉字/句型 + 官方能力锚定的听读进阶"),
          ("P5", 66, 75, "整合迁移：跨阶段交错、弱项补救、近自然语速输出"),
          ("P6", 76, 80, "模拟评估：分项能力盘点与下一阶段规划")]
ASSESSMENT_PRIORITY = ["final", "midterm", "n3_readiness", "stage", "weekly", "diagnostic"]

# 高频压缩路径的分级窗口：级别不铺满全程，而是集中在对应阶段兑现（框架 §3.2）
LEVEL_WINDOWS = {"N5": (1, 25), "N4": (26, 45), "N3": (46, 65)}
GRAMMAR_WINDOWS = {"N5": (1, 25), "N4": (26, 45), "N3": (46, 65)}

# Can-do 不再按阶段/按天轮换：由当天素材 topic 驱动的 SCENE_TASKS 生成（见下）。
# 能力目标池：每天按确定性轮换抽取，避免 80 天 objectives 完全相同。
# 写成零基础学员一眼能懂的中文短句，不出现「接续条件/适用场合/近义表达/类推/近自然语速/
# 主旨/支撑细节/迁移/事实陈述/推测表达/归因/听辨」这类教研或系统黑话（v3 改造）。
OBJECTIVE_POOL = [
    "能听懂 {topic} 里常出现的词，并说出大概意思",
    "能不看提示，自己说出至少 1 句完整的日语",
    "能说清「{g}」用在什么场合、前面该怎么接",
    "能分清 {v} 和意思相近的词，别按中文硬套",
    "能读准今天汉字的日语读音，不照中文读音猜",
    "能听懂一段正常语速的短对话，说清谁和谁、接下来要做什么",
    "能从一小段通知或短文里找出主要意思，并说出一句依据",
    "能把今天学的说法用到一个新场景，而不是只背原句",
    "能分清「这是事实」和「这是我猜的」，不把猜测说成肯定",
    "能说出自己错在哪一类（忘了 / 记混 / 助词 / 变形 / 听错 / 没读懂）",
]

RUBRIC_POOL = [
    "客观题按答案精确判分；开放题按 rubric 分点评分（内容/语法/得体性），AI 判定后经 grade-open 回写；错误必须标注 error_type。",
    "听解题以 audio_text 为准、允许假名作答；读解题须引用原文依据；开放题分点给分，意思大致相近但语法/语体错误照样扣分。",
    "词汇题按词形与读音双判；语法题须说明接续理由；开放题按内容完整度、语法准确度、语体得体性三点评分，不设安慰分。",
    "改错与翻译按「错因定位 + 修正 + 依据」三点给分；自由产出必须达到 rubric 每一项才计满分；错误按 error_type 归档。",
    "选择题精确判分；重组题按编号序列判分；情景对话按任务完成度与得体性评分，只写单词不算完成交际任务。",
]

FOCUS_CYCLE = [("listening", "reading"), ("grammar", "production"), ("vocabulary", "kanji"),
               ("reading", "listening"), ("production", "grammar")]

# 素材 topic 原为英文标签，转成中文场景词后再进课程文案，避免「读一段 discussion 通知」这类生硬句子。
# health / notice 的标签与 docs/REVISION_CONTRACT.md 第 7 节的示例日（Day 30 / Day 46）保持一致。
TOPIC_ZH = {
    "restaurant": "餐厅点餐", "weather": "天气", "work": "工作沟通", "travel": "旅行",
    "email": "邮件往来", "notice": "市政通知", "health": "医院问诊", "transport": "交通出行",
    "school": "校园", "family": "家庭", "asking_directions": "问路", "tech": "科技产品",
    "appointment": "预约", "news_summary": "新闻概要", "procedure": "手续办理",
    "reservation": "预订", "technology": "科技", "greeting": "寒暄", "self_intro": "自我介绍",
    "shopping": "购物", "daily_routine": "日常作息", "entertainment": "休闲娱乐",
    "request": "请求委托", "discussion": "意见讨论", "explanation": "说明解释",
    "announcement": "公告",
}

# 主题词表（日文关键词）：既用于「新知识对当天场景的亲和度」排序，也用于素材补位时
# 选择语义最近的同级别文本。新增 topic 时同步补这里；缺项按 0 亲和度处理，不报错。
TOPIC_LEXICON = {
    "restaurant": ["料理", "食べ", "飲み", "メニュー", "店", "注文", "味", "おいし", "昼ご飯", "食券", "食堂"],
    "weather": ["天気", "雨", "晴れ", "曇り", "雪", "気温", "予報", "空", "暑", "寒", "涼", "台風"],
    "work": ["仕事", "会社", "会議", "資料", "打ち合わせ", "就職", "職場", "同僚", "部長", "残業", "面接"],
    "travel": ["旅行", "観光", "ハイキング", "延期", "温泉", "出発", "荷物", "宿", "旅", "景色"],
    "email": ["メール", "返事", "件名", "宛先", "添付", "連絡", "先生", "変更", "返信", "文面"],
    "notice": ["お知らせ", "掲示", "案内", "遅れ", "遅延", "ごみ", "資源", "改装", "営業", "注意",
               "変更", "受付", "手続き", "窓口", "放送", "ご不便", "申し訳"],
    "health": ["病院", "医者", "症状", "具合", "薬", "熱", "痛", "眠", "健康", "体", "患者",
               "入院", "診察", "治療", "検査", "風邪", "看護", "安心", "無理", "休む", "顔色"],
    "transport": ["電車", "駅", "切符", "乗", "路線", "バス", "交通", "運転", "遅延", "乗り換え", "改札"],
    "school": ["学校", "図書館", "授業", "勉強", "学生", "先生", "教室", "宿題", "試験", "借りる", "カード"],
    "family": ["家族", "母", "父", "弟", "妹", "兄", "姉", "親", "子ども", "家", "泊まる"],
    "asking_directions": ["どこ", "道", "地図", "駅の前", "曲が", "信号", "交差点", "近く", "場所", "方向"],
    "tech": ["パソコン", "アプリ", "設定", "故障", "サポート", "画面", "ネット", "機械", "便利", "壊れ"],
    "technology": ["パソコン", "アプリ", "設定", "故障", "サポート", "画面", "ネット", "機械", "便利", "機能"],
    "appointment": ["予約", "約束", "誘い", "映画", "時間", "変更", "忘れ", "希望", "都合"],
    "news_summary": ["ニュース", "台風", "調査", "就職意識", "発表", "影響", "交通", "増加", "結果", "報告"],
    "procedure": ["手続き", "申請", "窓口", "カード", "更新", "受付", "書類", "住所", "提出", "発行"],
    "reservation": ["予約", "ホテル", "人数", "変更", "返信", "泊", "部屋", "空室", "宿泊"],
    "greeting": ["おはよう", "こんにちは", "こんばんは", "元気", "あいさつ", "私", "学生", "名前", "です", "はじめまして"],
    "self_intro": ["自己紹介", "名前", "私", "学生", "出身", "趣味", "です", "よろしく", "専攻"],
    "shopping": ["店", "買", "値段", "円", "商品", "売り", "レジ", "店員", "安い", "高い", "サイズ"],
    "daily_routine": ["毎朝", "起き", "寝", "支度", "朝", "夜", "習慣", "時間", "会社", "帰る"],
    "entertainment": ["映画", "音楽", "趣味", "日曜日", "見", "遊び", "楽しい", "コンサート", "チケット"],
    "request": ["ください", "待って", "お願い", "頼", "手伝", "ちょっと", "貸して", "教えて"],
    "discussion": ["意見", "考え", "話", "人によって", "違", "議論", "自分", "賛成", "反対"],
    "explanation": ["説明", "違い", "気持ち", "気分", "意味", "たとえ", "使い分け", "例"],
    "announcement": ["お知らせ", "放送", "駅", "遅延", "事故", "ご協力", "ご利用", "運転", "再開"],
}

# 场景任务模板：topic -> (场景标签, can_do 模板)。
# 模板必须含 {topic}（当天中文场景标签）和 {g}（当天语法），{v} 可选用。
# 不再按阶段/按天从大池子里轮换——同一天的主题、素材、语法、Can-do 必须自洽。
SCENE_TASKS = {
    "restaurant": ("餐厅点餐", "在{topic}场景用「{g}」点单、确认数量和口味，并处理一次没听清"),
    "weather": ("天气闲聊", "听一段{topic}预报，用「{g}」说出明天天气和出门建议"),
    "work": ("工作沟通", "在{topic}里用「{g}」确认会议时间、资料和负责人，并复述一遍"),
    "travel": ("旅行安排", "用「{g}」说明{topic}的行程变化、原因和替代方案"),
    "email": ("邮件往来", "读一封{topic}邮件，用「{g}」回信说明收到、问题和下一步"),
    "notice": ("市政通知", "读一份{topic}，用「{g}」在 30 秒内说出要办的事、截止时间和一条原文依据"),
    "health": ("医院问诊", "在{topic}中用「{g}」说明症状从何时开始、如何变化，并复述医嘱"),
    "transport": ("交通出行", "在{topic}场景用「{g}」问清路线、换乘和所需时间"),
    "school": ("校园学习", "在{topic}场景用「{g}」说明课程安排、借阅规则或学习计划"),
    "family": ("家庭交谈", "用「{g}」向家人说明{topic}里的安排和每个人的分工"),
    "asking_directions": ("问路", "用「{g}」在{topic}场景问清目的地、方向和步行时间"),
    "tech": ("科技产品", "在{topic}场景用「{g}」说明故障现象、已试过的办法和请求"),
    "technology": ("科技说明", "读一段{topic}说明，用「{g}」讲清设置步骤和注意事项"),
    "appointment": ("预约改期", "用「{g}」完成一次{topic}：报时间、人数并处理改期"),
    "news_summary": ("新闻概要", "读一则{topic}，用「{g}」概括主旨、影响和一条数据依据"),
    "procedure": ("手续办理", "在{topic}窗口用「{g}」问清所需材料、办理顺序和领取时间"),
    "reservation": ("预订确认", "用「{g}」确认{topic}的人数、时间和变更条件"),
    "greeting": ("初次见面", "用「{g}」完成一次{topic}：自我介绍、确认姓名并寒暄"),
    "self_intro": ("自我介绍", "用「{g}」介绍自己的{topic}：姓名、身份和一个兴趣"),
    "shopping": ("购物结算", "在{topic}场景用「{g}」问价、确认数量和付款方式"),
    "daily_routine": ("日常作息", "用「{g}」说出{topic}里的起床、出门和回家时间"),
    "entertainment": ("休闲娱乐", "用「{g}」聊一次{topic}安排：看什么、和谁去、几点碰面"),
    "request": ("请求委托", "在{topic}场景用「{g}」提出请求、说明理由并确认对方能否帮忙"),
    "discussion": ("意见讨论", "读一段{topic}，用「{g}」说明两种看法的差异和自己的立场"),
    "explanation": ("说明解释", "用「{g}」解释{topic}里两个近义词的区别，并各造一句"),
    "announcement": ("公共广播", "听一段{topic}，用「{g}」复述发生了什么、影响和下一步"),
}

# 锚定日：Day 1 是诊断日，预先保证 G0001/V0001/V0078/K0036/K0045/K0047 同天出现，
# 让诊断题 Q0181 等有合法题目可选；Day 30 / Day 46 是契约点名的场景（医院问诊 / 市政通知）。
# 锚点只决定该窗口的轮转起点，不改变「同 topic 分组 + 确定性轮转」的选材方式。
TOPIC_ANCHORS = {1: "greeting", 30: "health", 46: "notice"}

# 诊断日必须同天出现的基础知识（否则 Day 1 的 8 道诊断题会因超纲筛不到题）。
FOUNDATION_DAY1 = {"vocabulary": ["V0001", "V0078"],
                   "kanji": ["K0036", "K0045", "K0047"],
                   "grammar": ["G0001"]}



# ---- v3：把「今天学哪几句话 / 复习哪几个词 / 中文难点是什么」写进课程骨架 ----
# 复习是基于课程的确定性间隔计划（1/2/3/7/14/30 天），与本地 FSRS 到期队列是两回事。
REVIEW_INTERVALS = [1, 2, 3, 7, 14, 30]
_SENT_END = re.compile(r"(?<=[。！？!?])")          # 句末标点后断句（保留标点）
_INTERNAL_ID = re.compile(r"[GVKQ]\d{4}")          # 内部主键，不进学员可见文案
_PAREN_ID = re.compile(r"[（(][^（）()]*[GVKQ]\d{4}[^（）()]*[）)]")
_TEACH_CUES = ["记住：", "注意：", "容易错：", "小提醒："]
_GENERIC_NOTE = "点「听」跟读一遍，再对照中文记住这句话。"


def _split_sentences(text):
    """把一段文本按句末标点切成句子（保留标点），供素材 text_ja / text_zh 对齐。"""
    return [p.strip() for p in _SENT_END.split(text or "") if p and p.strip()]


def _short_zh(text, limit=80):
    """把种子的中文讲解截成一句短提示：去掉内部编号 G0001 等，不追加任何编造内容。"""
    if not isinstance(text, str) or not text.strip():
        return ""
    s = _PAREN_ID.sub("", text)
    s = _INTERNAL_ID.sub("", s)
    s = s.replace("（）", "").replace("()", "").strip("，、； ")
    if not s:
        return ""
    if len(s) <= limit:
        return s
    cut = max(s.rfind(m, 0, limit) for m in "。！？；，、")
    return s[:cut + 1] if cut > 0 else s[:limit]


# ---- v4：主题驱动选材 / 亲和度分配 ----

def _norm_ja(text):
    """去掉空白与全角空格，供「语法模式是否出现在素材正文」的确定性比对。"""
    return re.sub(r"[\s\u3000]+", "", text or "")


def _topic_affinity(topic, item, kind="vocab"):
    """亲和度 = TOPIC_LEXICON[topic] 在知识点可见文本中的命中次数。

    词：surface / meaning_zh / notes_for_zh / examples；
    语法：pattern / meaning_zh / examples；汉字：char / meaning_zh / zh_trap；
    素材：title / text_ja / text_zh / focus_zh。
    只做计数，不引入随机权重，保证同输入同输出。
    """
    kws = TOPIC_LEXICON.get(topic) or []
    if not kws or not isinstance(item, dict):
        return 0
    parts = [item.get("surface"), item.get("meaning_zh"), item.get("notes_for_zh"),
             item.get("pattern"), item.get("char"), item.get("zh_trap"),
             item.get("title"), item.get("text_ja"), item.get("text_zh"),
             item.get("focus_zh")]
    for e in item.get("examples") or []:
        if isinstance(e, dict):
            parts.extend([e.get("ja"), e.get("zh")])
    blob = "".join(str(p) for p in parts if p)
    return sum(blob.count(k) for k in kws)


_JARGON = {"名詞", "動詞", "形容詞", "副詞", "連体", "普通形", "辞書形", "ない形", "ます形",
           "意志形", "た形", "て形", "ば形", "い形", "な形", "可能形", "条件形", "受身形",
           "使役形", "授受", "比較", "同一", "同一動詞", "前", "後", "词干", "詞干",
           "丁寧体", "简体", "敬体", "普通体", "名", "動", "辞书形"}


def _clean_token(token):
    """把语法模式里的一段拆成可用于正文比对的日文片段；纯占位/术语返回空串。"""
    t = _norm_ja(token)
    t = re.sub(r"^[NVA]\d*", "", t)
    t = t.strip("。、；：・，,（）()「」[]")
    if not t or t in _JARGON:
        return ""
    if re.fullmatch(r"[A-Za-z0-9]+", t):
        return ""
    if not re.search(r"[ぁ-んァ-ヶ一-龥]", t):
        return ""
    return t


def _grammar_signatures(pattern):
    """从 pattern 抽 1..n 组「必须同时出现」的日文片段。

    `A / B + C` 表示任一组成立即可；组内片段需全部出现在正文。
    例：`～て ください` -> [["て", "ください"]]；`～たい / ～たがる` -> [["たい"], ["たがる"]]。
    """
    p = re.sub(r"[（(][^）)]*[）)]", "", pattern or "")
    out = []
    for alt in re.split(r"[/／]", p):
        toks = [_clean_token(x) for x in re.split(r"[\s+・、]+", alt.replace("～", ""))]
        toks = [x for x in toks if x]
        if toks:
            out.append(toks)
    return out


def _signature_hit(signatures, text):
    blob = _norm_ja(text)
    if not blob or not signatures:
        return False
    return any(all(t in blob for t in group) for group in signatures)


def _grammar_evidence(gid, mats, vocab_ids, gmap, vmap, strict=False):
    """返回语法当天的证据来源：material / vocab / grammar_example / ""。

    - material：当天素材的 grammar_ids 命中，或正文出现 pattern 的日文片段；
    - vocab：当天新词例句的 grammar_ids 命中，或例句正文出现片段；
    - grammar_example：该语法自己的种子例句（仍属「当天新知识例句」）。
    """
    g = gmap.get(gid) or {}
    sigs = _grammar_signatures(g.get("pattern"))
    for m in mats or []:
        if gid in (m.get("grammar_ids") or []):
            return "material"
        if _signature_hit(sigs, m.get("text_ja") or ""):
            return "material"
    for vid in vocab_ids or []:
        for e in (vmap.get(vid) or {}).get("examples") or []:
            if not isinstance(e, dict):
                continue
            if gid in (e.get("grammar_ids") or []):
                return "vocab"
            if _signature_hit(sigs, e.get("ja") or ""):
                return "vocab"
    for e in g.get("examples") or []:
        if not isinstance(e, dict):
            continue
        if not sigs:
            return "grammar_example"
        if _signature_hit(sigs, e.get("ja") or ""):
            return "grammar_example"
    # 语法自己的例句本身就是「当天新知识例句」：pattern 是辞书形/术语时，
    # 例句常以ます形/过去形出现，签名匹配会漏；有例句即视为有语境证据。
    # strict=True 时不接受这个兜底，只认「当天素材/当天新词」的硬证据，
    # 用于分配排序与对齐统计，避免用自家例句把「没对齐」粉饰成「对齐」。
    if g.get("examples") and not strict:
        return "grammar_example"
    return ""


def _grammar_supported(gid, mats, vocab_ids, gmap, vmap):
    return bool(_grammar_evidence(gid, mats, vocab_ids, gmap, vmap))


def _material_groups(materials):
    """原创素材按 level -> topic -> kind 分组；index_only / 无正文一律不参与选材。"""
    by = {}
    for m in materials:
        if m.get("review_status") == "index_only" or not m.get("text_ja"):
            continue
        topic = m.get("topic")
        if not topic:
            continue
        lvl = m.get("level") or "N5"
        kind = m.get("kind")
        if kind not in ("reading", "listening"):
            continue
        by.setdefault(lvl, {}).setdefault(topic, {"reading": [], "listening": []})[kind].append(m)
    for lvl in by:
        for topic in by[lvl]:
            for kind in ("reading", "listening"):
                by[lvl][topic][kind].sort(key=lambda x: x["id"])
    return by


def _rotation_order(topics, start, end):
    """确定性轮转顺序：按 topic 名排序，再按锚定日旋转到锚点位置。"""
    order = sorted(topics)
    if not order:
        return []
    n = len(order)
    for day, topic in sorted(TOPIC_ANCHORS.items()):
        if start <= day <= end and topic in order:
            shift = (order.index(topic) - (day - start)) % n
            return order[shift:] + order[:shift]
    return order


def _assign_topics(materials):
    """给 Day 1..80 定 topic：级别窗口内轮转；P5/P6 沿用 N3 轮转（综合复习）。"""
    groups = _material_groups(materials)
    topics_by_day, orders = {}, {}
    for lvl, (a, b) in LEVEL_WINDOWS.items():
        order = _rotation_order((groups.get(lvl) or {}).keys(), a, b)
        orders[lvl] = order
        for day in range(a, b + 1):
            topics_by_day[day] = order[(day - a) % len(order)] if order else ""
    order_n3 = orders.get("N3") or []
    for day in range(66, 81):
        topics_by_day[day] = order_n3[(day - 46) % len(order_n3)] if order_n3 else ""
    return topics_by_day, groups, orders


def _pick_materials(day, topic, groups, order, use_count, force_review=False):
    """按 topic 取「阅读 + 听力」各一篇；同 topic 缺一种时用同级别最近的 topic 补位。

    返回 (material_ids, topic_used, topic_match, material_topics)。
    topic_match:
      exact   —— 至少一篇素材与 scene_topic_key 同 topic，且该篇排在第一；
      partial —— 该 topic 在本级别完全没有素材，只能用最近 topic 补位（scene key 改为实际 topic）；
      review  —— P5/P6 综合复习，不承诺素材与场景主题一致。
    """
    grp = groups or {}
    if not grp:
        return [], topic, "review", []
    order = list(order) or sorted(grp)
    n = len(order)

    def take(kind, wanted):
        same = (grp.get(wanted) or {}).get(kind) or []
        if same:
            m = min(same, key=lambda x: (use_count.get(x["id"], 0), x["id"]))
            return m, True
        cands = [(t, m) for t, g in grp.items() for m in (g.get(kind) or [])]
        if not cands:
            return None, False
        wi = order.index(wanted) if wanted in order else 0

        def rank(tm):
            t, m = tm
            d = n
            if t in order:
                ti = order.index(t)
                d = min((ti - wi) % n, (wi - ti) % n)
            return (-_topic_affinity(wanted, m), d, use_count.get(m["id"], 0), m["id"])

        t, m = min(cands, key=rank)
        return m, False

    same_grp = grp.get(topic) or {}
    if same_grp.get("reading"):
        primary, secondary = "reading", "listening"
    elif same_grp.get("listening"):
        primary, secondary = "listening", "reading"
    else:
        primary, secondary = "reading", "listening"

    chosen = []
    first, first_match = take(primary, topic)
    if first:
        chosen.append(first)
    second, _ = take(secondary, topic)
    if second and second["id"] not in {m["id"] for m in chosen}:
        chosen.append(second)
    if not chosen:
        return [], topic, "review", []

    matched = [m for m in chosen if m.get("topic") == topic]
    if matched:
        # 保证 lesson_core 第一句优先来自与场景同 topic 的素材
        chosen.sort(key=lambda m: (m.get("topic") != topic, 0 if m.get("kind") == "reading" else 1, m["id"]))
        used = topic
    else:
        used = chosen[0].get("topic") or topic
    for m in chosen:
        use_count[m["id"]] = use_count.get(m["id"], 0) + 1
    match = "review" if force_review else ("exact" if matched else "partial")
    return [m["id"] for m in chosen], used, match, [m.get("topic") for m in chosen]


def _allocate_topic_pool(items, start, end, topics_by_day, level, kind):
    """级别窗口内按「亲和度降序, frequency 降序, id」分配；每天取 ceil(剩余池/剩余天)。"""
    if level == "N5":
        pool = [x for x in items if x.get("jlpt") == "N5" or x.get("jlpt") not in LEVEL_WINDOWS]
    else:
        pool = [x for x in items if x.get("jlpt") == level]
    pool = sorted(pool, key=lambda x: x["id"])
    out = defaultdict(list)
    for day in range(start, end + 1):
        rem_days = end - day + 1
        n = max(1, math.ceil(len(pool) / rem_days)) if pool else 0
        topic = topics_by_day.get(day, "")
        ranked = sorted(pool, key=lambda x: (-_topic_affinity(topic, x, kind),
                                             -(int(x.get("frequency") or 3)), x["id"]))
        take = ranked[:n]
        out[day] = [x["id"] for x in take]
        taken = {x["id"] for x in take}
        pool = [x for x in pool if x["id"] not in taken]
    return out


def _pin_foundation(alloc, kind):
    """把诊断日必须同天出现的基础知识钉到 Day 1 最前面（从其它天移走，不复制）。"""
    fixed = list(FOUNDATION_DAY1.get(kind) or [])
    if not fixed:
        return
    cur = [x for x in (alloc.get(1) or []) if x not in fixed]
    for d, ids in list(alloc.items()):
        if d != 1:
            alloc[d] = [x for x in ids if x not in fixed]
    alloc[1] = fixed + cur


def _improve_grammar_alignment(out, materials_by_day, vocab_by_day, gmap, vmap, mmap):
    """把「只有自家例句」的语法与别的天做等价交换，换到素材真能支撑的那一天。

    只做同级别窗口内、且交换后先修顺序仍成立的交换；确定性遍历，最多 40 轮。
    换不动就保留，并如实计入 alignment.grammar_backed_by_material，不粉饰。
    """
    gday = {gid: d for d, ids in out.items() for gid in ids}
    def evidence_on(gid, day):
        mats = [mmap[m] for m in materials_by_day.get(day, []) if m in mmap]
        return _grammar_evidence(gid, mats, vocab_by_day.get(day, []), gmap, vmap, strict=True)

    def day_ok(day):
        ids = out.get(day) or []
        return (not ids) or any(evidence_on(g, day) for g in ids)

    def topology_ok(gday_map):
        for gid, d in gday_map.items():
            for p in (gmap.get(gid, {}).get("prerequisites") or []):
                if p in gday_map and gday_map[p] >= d:
                    return False
        return True

    for _ in range(40):
        changed = False
        for day in sorted(out):
            if day_ok(day):
                continue
            weak = [g for g in out.get(day, []) if not evidence_on(g, day)]
            if not weak:
                continue
            for other in sorted(out):
                if other == day:
                    continue
                if phase_of(other) != phase_of(day):
                    continue
                for cand in out.get(other, []):
                    if not evidence_on(cand, day):
                        continue
                    if evidence_on(cand, other):
                        continue          # 别把别人已经对齐的语法抢走
                    for bad in weak:
                        trial = dict(gday)
                        trial[cand], trial[bad] = day, other
                        if not topology_ok(trial):
                            continue
                        out[day] = [cand if x == bad else x for x in out[day]]
                        out[other] = [bad if x == cand else x for x in out[other]]
                        gday = trial
                        changed = True
                        break
                    if changed:
                        break
                if changed:
                    break
            if changed:
                break
        if not changed:
            break
    return out


def _allocate_grammar(grammar, topics_by_day, materials_by_day, vocab_by_day, gmap, vmap, mmap):
    """语法仍受先修拓扑约束，但同一天内优先选当天素材/新词例句能支撑的语法。"""
    out = defaultdict(list)
    evidence = {}
    introduced = set()
    remaining = sorted(grammar, key=lambda x: x["id"])
    for lvl, (a, b) in sorted(LEVEL_WINDOWS.items(), key=lambda kv: kv[1][0]):
        pool = [g for g in remaining
                if g.get("jlpt") == lvl or (lvl == "N5" and g.get("jlpt") not in LEVEL_WINDOWS)]
        pool_ids = {g["id"] for g in pool}
        remaining = [g for g in remaining if g["id"] not in pool_ids]
        for day in range(a, b + 1):
            if not pool:
                break
            rem_days = b - day + 1
            n = max(1, math.ceil(len(pool) / rem_days))
            eligible = [g for g in pool
                        if all(p in introduced for p in (g.get("prerequisites") or []))]
            topic = topics_by_day.get(day, "")
            mats = [mmap[mid] for mid in materials_by_day.get(day, []) if mid in mmap]
            nv = vocab_by_day.get(day, [])

            def rank(g):
                ev = _grammar_evidence(g["id"], mats, nv, gmap, vmap, strict=True)
                strong = 0 if ev else 1
                return (strong, -_topic_affinity(topic, g, "grammar"),
                        -(int(g.get("frequency") or 3)), g["id"])

            take = sorted(eligible, key=rank)[:n]
            out[day] = [g["id"] for g in take]
            for g in take:
                evidence[g["id"]] = _grammar_evidence(g["id"], mats, nv, gmap, vmap)
                introduced.add(g["id"])
            taken = {g["id"] for g in take}
            pool = [g for g in pool if g["id"] not in taken]
            if day == b and pool:
                # 窗口最后一天仍有剩余：全部排入（先修在同一批内不满足时，validate 会如实报错，
                # 这里不悄悄放宽拓扑约束）。
                out[day].extend(g["id"] for g in pool)
                for g in pool:
                    evidence[g["id"]] = _grammar_evidence(g["id"], mats, nv, gmap, vmap)
                    introduced.add(g["id"])
                pool = []
    return out, evidence



def _zh_candidates(item, kind):
    """从一个知识点抽出「可给零基础学员看的中文难点」候选 (rank, 文本)。
    rank 越小越优先：0=中文母语者易错点，1=中日差异/同形，2=助词/变形/敬简。"""
    out = []
    if kind == "vocab":
        if item.get("notes_for_zh"):
            out.append((0, item["notes_for_zh"]))
    elif kind == "grammar":
        for e in item.get("common_errors") or []:
            if isinstance(e, dict) and e.get("why"):
                rank = 0 if e.get("learner") in (None, "zh") else 1
                out.append((rank, e["why"]))
        if item.get("usage"):
            out.append((2, item["usage"]))
        for c in item.get("compare") or []:
            diff = c.get("diff") if isinstance(c, dict) else (c if isinstance(c, str) else None)
            if diff:
                out.append((2, diff))
    elif kind == "kanji":
        if item.get("zh_trap"):
            out.append((1, item["zh_trap"]))
    cleaned = []
    for rank, text in out:
        s = _short_zh(text)
        if s:
            cleaned.append((rank, s))
    return cleaned


def _seed_note(item, kind):
    """取一条最适合挂在句子旁的中文提示（真实种子内容），兜底为通用的中文学习提示。"""
    for _rank, text in _zh_candidates(item, kind):
        return text
    for key in ("meaning_zh", "usage", "notes_for_zh", "zh_trap"):
        s = _short_zh(item.get(key, ""))
        if s:
            return s
    return _GENERIC_NOTE


def _material_pairs(mids, mmap, gmap, vmap):
    """把素材按句拆成 (日文, 假名, 中文, 中文提示)。只有日中句数一致才成对，
    避免把错位的中文硬配到日文上（等于编造翻译）。

    v3 修复两处：
    1) 资料层已为部分 N5 素材补了真实 `text_kana`，逐句对齐后填入假名；
       没有 / 句数不符 / 与原文相同（旧的「读音=原文」bug）一律留空，不伪造。
    2) 中文提示优先用素材自己的 `focus_zh`，不再把某条语法的易错点循环塞给
       不相关的句子（旧版「早上好」配「だ 是简体」的错配）。"""
    pairs = []
    for mid in mids:
        m = mmap.get(mid)
        if not m:
            continue
        ja, zh = m.get("text_ja"), m.get("text_zh")
        if not ja or not zh:
            continue
        ja_s, zh_s = _split_sentences(ja), _split_sentences(zh)
        if not ja_s or len(ja_s) != len(zh_s):
            continue
        ka_s = _split_sentences(m.get("text_kana") or "")
        if len(ka_s) != len(ja_s):
            ka_s = []   # 句数对不上就不猜，绝不把 text_ja 当读音
        focus = _short_zh(m.get("focus_zh") or "")
        notes = [focus] if focus else []
        if not notes:
            for gid in m.get("grammar_ids") or []:
                if gid in gmap:
                    n = _seed_note(gmap[gid], "grammar")
                    if n:
                        notes.append(n)
            for vid in m.get("vocab_ids") or []:
                if vid in vmap:
                    n = _seed_note(vmap[vid], "vocab")
                    if n:
                        notes.append(n)
        if not notes:
            notes = [_GENERIC_NOTE]
        for i, (j, z) in enumerate(zip(ja_s, zh_s)):
            # 邮件标题 / 通知抬头不是「一句话」，不塞进「今天要会的 3 句话」
            if "／" in j or j.startswith(("件名：", "【", "※")):
                continue
            # 该句本来就是全假名时无需再显示读音行，其余句子照常给假名
            kana = ka_s[i] if ka_s and ka_s[i] != j else ""
            pairs.append((j, kana, z, notes[i % len(notes)], mid))
    return pairs


def _example_pairs(kids, imap, kind):
    """把知识点的 examples 拆成 (日文, 假名, 中文, 中文提示)。
    种子例句没有整句假名，一律留空，由页面用 TTS + 中文兜底，不伪造读音。"""
    pairs = []
    for kid in kids:
        it = imap.get(kid)
        if not it:
            continue
        note = _seed_note(it, kind)
        for e in it.get("examples") or []:
            ja, zh = e.get("ja"), e.get("zh")
            if ja and zh:
                pairs.append((ja, "", zh, note))
    return pairs


def _build_lesson_core(mids, nv, ng, rev, learned, mmap, gmap, vmap):
    """凑满且仅 3 句「今天要会的话」，全部来自真实种子，绝不编造日语。

    v4 对齐规则（契约第 7 节）：
    1) 第一句必须来自当天素材（`_material_pairs` 命中），素材句优先填满 3 句；
    2) 不足 3 句才用当天新语法 / 新词例句补齐，最后才用复习/已学例句兜底；
    3) 每句写 `origin`：material | grammar | vocab | fallback，供 validate 与对齐报告审计。
    kana 只取资料层已核实的素材 text_kana 逐句对齐结果；没有就留空，绝不伪造。"""
    mat_pairs = _material_pairs(mids, mmap, gmap, vmap)
    g_pairs = _example_pairs(ng, gmap, "grammar")
    v_pairs = _example_pairs(nv, vmap, "vocab")
    core, seen = [], set()

    def add(rows, origin):
        for row in rows:
            if len(row) == 5:
                ja, kana, zh, note, src = row
            else:
                ja, kana, zh, note = row
                src = ""
            if ja in seen:
                continue
            seen.add(ja)
            item = {"ja": ja, "kana": kana, "zh": zh,
                    "note_zh": note or _GENERIC_NOTE, "audio_text": ja,
                    "origin": origin}
            if src:
                item["source_id"] = src
            core.append(item)
            if len(core) == 3:
                return True
        return False

    for rows, origin in ((mat_pairs, "material"), (g_pairs, "grammar"), (v_pairs, "vocab")):
        if add(rows, origin):
            return core
    # 极端兜底：用「已学知识」的真实例句补齐到 3 句（排序保证确定性）
    fallback = (_example_pairs(sorted(k for k in learned if k in gmap), gmap, "grammar") +
                _example_pairs(sorted(k for k in learned if k in vmap), vmap, "vocab"))
    add(fallback, "fallback")
    return core


def _review_reason(gap):
    return "这是预习建议（非 FSRS 到期项）：%d 天前学过，可按 1/2/3/7/14/30 天间隔预看" % gap


def _next_hint(gap, learned_day):
    idx = REVIEW_INTERVALS.index(gap) if gap in REVIEW_INTERVALS else 0
    nxt = REVIEW_INTERVALS[idx + 1] if idx + 1 < len(REVIEW_INTERVALS) else gap * 2
    return "按课程间隔，大约 Day %d 再预习" % (learned_day + nxt)


def _build_review_plan(rev, day, introduced_day, vmap, gmap, kmap):
    """把 review_knowledge_ids 展开成具体词条，最多 8 条，首日为空数组。
    契约第 4 节：字段名保留，但语义是「预习建议」，每项标 planned_only=True。"""
    out = []
    for kid in rev[:8]:
        learned_day = introduced_day.get(kid, day - 1)
        gap = day - learned_day
        if kid in vmap:
            x = vmap[kid]
            surface, kana, zh = x.get("surface", ""), x.get("kana", ""), x.get("meaning_zh", "")
        elif kid in gmap:
            x = gmap[kid]
            surface, kana, zh = x.get("pattern", ""), "", x.get("meaning_zh", "")
        elif kid in kmap:
            x = kmap[kid]
            surface, kana, zh = x.get("char", ""), "", x.get("meaning_zh", "")
        else:
            continue
        out.append({"kid": kid, "surface": surface, "kana": kana, "zh": zh,
                    "reason_zh": _review_reason(gap),
                    "learned_day": learned_day,
                    "next_hint_zh": _next_hint(gap, learned_day),
                    "planned_only": True})
    return out


def _build_teaching_notes(nv, ng, nk, rev, vmap, gmap, kmap, maxn=4):
    """2–4 条中文难点讲解，取自当天新知识点；新知识点不足 2 条时，
    才用「今天要复习的真实知识点」补（仍 100% 来自种子）。无可取字段就少于 2 条甚至空数组。"""
    cand = []

    def add(kids, imap, kind, rank_offset=0):
        for kid in kids:
            if kid in imap:
                for rank, t in _zh_candidates(imap[kid], kind):
                    cand.append((rank + rank_offset, kid, t))

    add(nv, vmap, "vocab")
    add(ng, gmap, "grammar")
    add(nk, kmap, "kanji")
    if len(cand) < 2:
        add(rev, vmap, "vocab", 3)
        add(rev, gmap, "grammar", 3)
        add(rev, kmap, "kanji", 3)
    cand.sort(key=lambda x: (x[0], x[1]))
    notes, seen = [], set()
    for _rank, _kid, t in cand:
        if t in seen:
            continue
        seen.add(t)
        notes.append(_TEACH_CUES[len(notes) % len(_TEACH_CUES)] + t)
        if len(notes) >= maxn:
            break
    return notes


def phase_of(day: int) -> str:
    for code, a, b, _ in PHASES:
        if a <= day <= b:
            return code
    raise ValueError("day 越界: %s" % day)


def assessment_of(day: int) -> str:
    c = []
    if day == 1: c.append("diagnostic")
    if day % 7 == 0: c.append("weekly")
    if day % 20 == 0: c.append("stage")
    if day == 40: c.append("midterm")
    if day == 60: c.append("n3_readiness")
    if day == 80: c.append("final")
    for x in ASSESSMENT_PRIORITY:
        if x in c:
            return x      # 同一天只保留优先级最高的一个，绝不叠加
    return "none"


def _windows(items, start, end):
    """把一组条目均匀铺到 [start,end] 天，返回 day -> [id]。"""
    out = defaultdict(list)
    n = len(items)
    if not n:
        return out
    for i, x in enumerate(items):
        d = start + (i * (end - start + 1)) // n
        out[min(d, end)].append(x["id"])
    return out


def _windows_by_level(items, windows):
    """高频压缩路径的核心：按 JLPT 级别把知识集中铺到对应阶段窗口，
    同一窗口内 frequency 高的先出现（Zipf 覆盖率优先，框架 §3.1）。
    返回 day -> [id]。"""
    out = defaultdict(list)
    known = set(windows)
    for lvl, (a, b) in windows.items():
        pool = [x for x in items if x.get("jlpt") == lvl]
        pool.sort(key=lambda x: (-(int(x.get("frequency") or 3)), x["id"]))
        n = len(pool)
        if not n:
            continue
        for i, x in enumerate(pool):
            d = a + (i * (b - a + 1)) // n
            out[min(d, b)].append(x["id"])
    # 未标级别的条目不静默丢弃：并入最早窗口，保证覆盖率 100%
    other = [x for x in items if x.get("jlpt") not in known]
    a, b = windows["N5"]
    for i, x in enumerate(sorted(other, key=lambda y: y["id"])):
        out[a + (i * (b - a + 1)) // max(len(other), 1)].append(x["id"])
    return out


def _topo_days_by_level(grammar, windows):
    """语法按级别窗口铺开 + 先修拓扑修正：变形规则必须先于依赖它的复合句型（框架 §3.3）。"""
    day_of = {}
    for lvl, (a, b) in windows.items():
        pool = sorted([g for g in grammar if g.get("jlpt") == lvl], key=lambda x: x["id"])
        if not pool:
            continue
        for i, g in enumerate(pool):
            day_of[g["id"]] = a + (i * (b - a + 1)) // len(pool)
    a, b = windows["N5"]
    for g in grammar:
        if g["id"] not in day_of:
            day_of[g["id"]] = a
    for _ in range(400):
        changed = False
        for g in sorted(grammar, key=lambda x: x["id"]):
            for p in g.get("prerequisites") or []:
                if p not in day_of:
                    raise ValueError("先修缺失 %s -> %s" % (g["id"], p))
                if day_of[p] >= day_of[g["id"]]:
                    day_of[g["id"]] = day_of[p] + 1
                    changed = True
        if not changed:
            break
    if max(day_of.values()) > 78:
        raise ValueError("先修链导致课程超出 Day 78（无法给终期评估留空）")
    out = defaultdict(list)
    for gid, d in day_of.items():
        out[d].append(gid)
    return out, day_of


def _topo_days(grammar, start=1, end=70):
    """语法按 id 顺序铺开后，迭代修正使每个先修都出现在更早的天。"""
    by_id = {g["id"]: g for g in grammar}
    day_of = {}
    for i, g in enumerate(sorted(grammar, key=lambda x: x["id"])):
        day_of[g["id"]] = start + (i * (end - start + 1)) // len(grammar)
    for _ in range(200):
        changed = False
        for g in sorted(grammar, key=lambda x: x["id"]):
            for p in g.get("prerequisites") or []:
                if p not in day_of:
                    raise ValueError("先修缺失 %s -> %s" % (g["id"], p))
                if day_of[p] >= day_of[g["id"]]:
                    day_of[g["id"]] = day_of[p] + 1
                    changed = True
        if not changed:
            break
    if max(day_of.values()) > 80:
        raise ValueError("先修链导致课程超出 80 天")
    out = defaultdict(list)
    for gid, d in day_of.items():
        out[d].append(gid)
    return out, day_of


def _question_index(questions):
    idx = defaultdict(list)
    for q in questions:
        for kid in q.get("knowledge_ids") or []:
            idx[kid].append(q)
    return idx


def _pick_questions(day, learned, questions, n, level_hint, used):
    """只选引用已学知识的题（超纲检查）；优先未做过的，难度接近当阶段；
    题库小于 80*题量 时允许跨天复用 —— 这是刻意的间隔重复，不是凑数。"""
    eligible = [q for q in questions
                if q.get("knowledge_ids")
                and all(k in learned for k in q["knowledge_ids"])
                and (q.get("difficulty") or 1) <= level_hint + 1]
    eligible.sort(key=lambda q: (q["id"] in used,
                                 abs((q.get("difficulty") or 1) - level_hint),
                                 q["id"]))
    picked = eligible[:n]
    for q in picked:
        used.add(q["id"])
    return [q["id"] for q in picked]


def _build_stamp(r):
    """用种子文件的最后修改时间作为构建时间：内容不变则构建产物稳定（可复现）。"""
    paths = sorted((r / "knowledge" / "seeds").glob("*.jsonl"))
    ts = max((p.stat().st_mtime for p in paths), default=0)
    return iso(datetime.fromtimestamp(ts, timezone.utc))


def build(root=None) -> dict:
    r = root_of(root)
    seeds = {k: read_jsonl(r / "knowledge" / "seeds" / f) for k, f in {
        "vocabulary": "vocabulary.jsonl", "grammar": "grammar.jsonl",
        "kanji": "kanji.jsonl", "questions": "questions.jsonl",
        "materials": "materials.jsonl"}.items()}
    vocab, grammar, kanji = seeds["vocabulary"], seeds["grammar"], seeds["kanji"]
    questions, materials = seeds["questions"], seeds["materials"]
    valid_ids = {x["id"] for k in ("vocabulary", "grammar", "kanji") for x in seeds[k]}
    vmap = {x["id"]: x for x in vocab}
    gmap_all = {x["id"]: x for x in grammar}
    kmap = {x["id"]: x for x in kanji}
    mmap_all = {x["id"]: x for x in materials}
    qmap_all = {x["id"]: x for x in questions}

    # 主题驱动选材 + 亲和度分配（契约第 7 节）。
    # 1) 每个级别窗口把原创素材按 topic 分组，确定性轮转，保证每天读到同一主题的文本；
    # 2) 新词/汉字/语法在级别窗口内按当天 topic 亲和度排序，仍保先修拓扑与分级下限。
    topics_by_day, mat_groups, mat_orders = _assign_topics(materials)
    material_by_day, material_meta = {}, {}
    use_count = {}
    for day in range(1, 81):
        level = "N5" if day <= 25 else "N4" if day <= 45 else "N3"
        topic = topics_by_day.get(day, "")
        ids, used_topic, match, mtops = _pick_materials(
            day, topic, mat_groups.get(level) or {}, mat_orders.get(level) or [],
            use_count, force_review=(day >= 66))
        material_by_day[day] = ids
        material_meta[day] = {"topic": used_topic, "match": match, "topics": mtops}
        if day % 7 == 0:      # 外部资源只作延伸阅读，不占听力/阅读正文位
            ext = [m for m in materials if m.get("review_status") == "index_only"]
            if ext:
                material_by_day[day].append(ext[(day // 7 - 1) % len(ext)]["id"])

    vby_day, kby_day = {}, {}
    for lvl, (a, b) in LEVEL_WINDOWS.items():
        vby_day.update(_allocate_topic_pool(vocab, a, b, topics_by_day, lvl, "vocab"))
        kby_day.update(_allocate_topic_pool(kanji, a, b, topics_by_day, lvl, "kanji"))
    _pin_foundation(vby_day, "vocabulary")
    _pin_foundation(kby_day, "kanji")
    gby_day, grammar_evidence = _allocate_grammar(
        grammar, topics_by_day, material_by_day, vby_day, gmap_all, vmap, mmap_all)
    _pin_foundation(gby_day, "grammar")
    gby_day = _improve_grammar_alignment(gby_day, material_by_day, vby_day,
                                         gmap_all, vmap, mmap_all)
    gday = {gid: d for d, ids in gby_day.items() for gid in ids}

    qidx = _question_index(questions)
    used_q = set()
    learned = set()
    new_by_day = {}
    introduced_day = {}          # kid -> 真实引入那天，供 review_plan 回溯
    days = []
    for day in range(1, 81):
        ph = phase_of(day)
        ass = assessment_of(day)
        nv, ng, nk = vby_day.get(day, []), gby_day.get(day, []), kby_day.get(day, [])
        learned |= set(nv + ng + nk)
        new_by_day[day] = nv + ng + nk
        for kid in nv + ng + nk:
            introduced_day[kid] = day
        # 复习候选池：1/2/3/7/14/30 天前引入的知识（实际到期由 FSRS 决定）
        rev = []
        for back in REVIEW_INTERVALS:
            rev += new_by_day.get(day - back, [])
        rev = list(dict.fromkeys([x for x in rev if x in learned]))[:12]
        level_hint = 1 if day <= 10 else 2 if day <= 25 else 3 if day <= 45 else 4 if day <= 65 else 5
        nq = 8 if ass in ("diagnostic", "final", "midterm", "n3_readiness") else 6
        qids = _pick_questions(day, learned, questions, nq, level_hint, used_q)
        mids = material_by_day.get(day, [])
        if ass != "none":
            blocks = [{"min": 10, "type": "review", "desc": "FSRS 到期项主动回忆，无提示优先"},
                      {"min": 10, "type": "new", "desc": "当天新知识快速回顾（不新增超纲内容）"},
                      {"min": 5, "type": "interaction", "desc": "短场景口头输出，保持表达能力训练"},
                      {"min": 30, "type": "assessment", "desc": "合并执行当天唯一的 %s，不叠加多套试卷" % ass},
                      {"min": 5, "type": "feedback", "desc": "归因、写档、生成下一日任务"}]
        elif ph == "P5":
            blocks = [{"min": 20, "type": "review", "desc": "跨阶段混合复习与延迟回忆"},
                      {"min": 10, "type": "remedy", "desc": "按错误类型做针对性补救"},
                      {"min": 15, "type": "interaction", "desc": "综合场景表达与角色扮演"},
                      {"min": 10, "type": "quiz", "desc": "交错练习：易混语法/助词/变形"},
                      {"min": 5, "type": "feedback", "desc": "记录与明日调整"}]
        else:
            blocks = [{"min": 10, "type": "review", "desc": "FSRS 到期复习 + 上一日错题重做"},
                      {"min": 20, "type": "new", "desc": "新知识：先给场景让学生推测，再揭示规则"},
                      {"min": 15, "type": "interaction", "desc": "听力/阅读素材 + 情景对话与独立输出"},
                      {"min": 10, "type": "quiz", "desc": "当天测验，先作答后讲解"},
                      {"min": 5, "type": "feedback", "desc": "错误归因、写档、明日任务"}]
        # ---- 主题驱动：当天素材 topic 决定场景标签、Can-do 与主题句 ----
        meta = material_meta.get(day, {})
        topic = meta.get("topic") or topics_by_day.get(day, "")
        topic_match = meta.get("match") or ("review" if day >= 66 else "partial")
        scene_topic = TOPIC_ZH.get(topic, topic) or "日常场景"
        vs = [vmap[i]["surface"] for i in nv[:3] if i in vmap]
        gs = [gmap_all[i]["pattern"] for i in ng[:2] if i in gmap_all]
        ks = [kmap[i]["char"] for i in nk[:4] if i in kmap]
        scene_title = next((mmap_all[mid]["title"] for mid in mids
                            if mmap_all.get(mid, {}).get("title")), "日常对话")
        scene_tag, task_tpl = SCENE_TASKS.get(
            topic, ("综合场景", "在{topic}场景用「{g}」完成一次听读与口头输出"))
        # Can-do 至少含一个当天语法：优先新语法，P5/P6 无新语法时用当天预习语法
        g_cando = next((gmap_all[i]["pattern"] for i in ng if i in gmap_all), "")
        if not g_cando:
            g_cando = next((gmap_all[i]["pattern"] for i in rev if i in gmap_all), "已学句型")
        gtxt = "、".join(gs) or g_cando
        vtxt = "、".join(vs) or "当天新词"
        can_do = task_tpl.format(g=g_cando, v=vtxt, topic=scene_topic)
        if ass not in ("none", "diagnostic"):
            can_do = "在 %s（%s｜%s）中分项展示五维能力，并用「%s」完成 1 次独立输出" % (
                ass, scene_tag, scene_topic, g_cando)
        theme = "%s｜%s" % (scene_tag, "・".join((gs + vs)[:3]) or scene_topic)
        scene = "【%s】%s：%s（素材：%s｜主题键：%s｜对齐：%s）" % (
            scene_tag, scene_topic, can_do, scene_title, topic, topic_match)
        obj_idx = (day * 2 + day // 5) % len(OBJECTIVE_POOL)
        objectives = [OBJECTIVE_POOL[(obj_idx + j) % len(OBJECTIVE_POOL)].format(
            g=gtxt, v=vtxt, topic=scene_topic) for j in range(3)]
        if vs: objectives.append("当天新词：%s（读音与用法都要验证，不靠汉字猜义）" % "、".join(vs))
        if gs: objectives.append("当天句型：%s，须说出接续条件" % "、".join(gs))
        if ks: objectives.append("当天汉字：%s，音读/训读各给一例" % "、".join(ks))
        objectives.append("Can-do：%s" % can_do)
        if ass != "none":
            objectives.append("本日评估 %s：分项记录词汇/语法/阅读/听力/表达得分" % ass)
        focus = list(FOCUS_CYCLE[(day - 1) % len(FOCUS_CYCLE)])
        rubric = RUBRIC_POOL[(day + len(ass)) % len(RUBRIC_POOL)]
        qtypes = sorted({qmap_all[q]["type"] for q in qids if q in qmap_all})
        if qtypes:
            rubric += " 本日题型：%s（按对应 rubric 判分，不因题型变化降低标准）。" % "、".join(qtypes)
        if ass == "none" and ph not in ("P5",):
            for b in blocks:
                if b["type"] == "interaction":
                    b["desc"] = "【%s】%s：听读素材 + 至少 1 次无提示独立输出" % (scene_tag, scene_topic)
        if ass == "diagnostic":
            completion = ("完成 Day 1 摸底诊断 %d 题（诊断不设及格线，结果用于调整起点），"
                          "并留下 1 次独立输出样本。" % len(qids))
        elif ass != "none":
            completion = ("在 60 分钟内合并完成当日唯一的 %s（不叠加多套试卷）：全部 %d 题作答 + "
                          "至少 1 次独立输出；分项记录五维得分。未达标不得标记完成，"
                          "由 adjust 生成补救任务，禁止降低测试难度。" % (ass, len(qids)))
        elif ph == "P4":
            completion = ("完成全部 %d 题作答 + Can-do「%s」的独立输出；N3 读解/听解至少各练 1 段；"
                          "客观正确率 >= 0.70；到期复习处理完毕。未达标不得标记完成，"
                          "由 adjust 生成补救任务而非降低难度。" % (len(qids), scene_tag))
        else:
            completion = ("完成全部 %d 题作答 + Can-do「%s」的独立输出；客观正确率 >= 0.70；"
                          "到期复习项处理完毕。未达标不得标记完成，"
                          "由 adjust 生成补救任务而非降低难度。" % (len(qids), scene_tag))
        sources = ["S000"]   # 课程主体是项目原创整理；外部来源从素材的 source_ids 合并
        if ph == "P4": sources.append("S007")   # N3 题型结构参照 JLPT 官方（仅标准参照，不复制原题）
        if ass != "none": sources.append("S008")  # 评估按 JLPT 官方 N3 能力描述锚定
        for mid in mids:
            m = next((x for x in materials if x["id"] == mid), None)
            if m: sources += [s for s in (m.get("source_ids") or []) if s not in sources]
        # ---- v3：把「今天具体学的 3 句 / 复习哪几个词 / 中文难点」写进骨架 ----
        lesson_core = _build_lesson_core(mids, nv, ng, rev, learned,
                                        mmap_all, gmap_all, vmap)
        review_plan = _build_review_plan(rev, day, introduced_day, vmap, gmap_all, kmap)
        teaching_notes = _build_teaching_notes(nv, ng, nk, rev, vmap, gmap_all, kmap)
        days.append({
            "day": day, "phase": ph, "theme": theme, "scene": scene,
            "scene_tag": scene_tag, "can_do": can_do, "focus": focus,
            "scene_topic_key": topic, "scene_topic": scene_topic,
            "topic_match": topic_match,
            "material_topic_keys": list(meta.get("topics") or []),
            "material_pair": ("same_topic" if meta.get("topics")
                              and all(t == topic for t in meta["topics"] if t) else "mixed_topic"),
            "grammar_evidence": {gid: grammar_evidence.get(gid, "") for gid in ng},
            "objectives": objectives, "new_vocab_ids": nv, "new_grammar_ids": ng,
            "new_kanji_ids": nk, "review_knowledge_ids": rev,
            "material_ids": mids,
            "lesson_core": lesson_core,
            "review_plan": review_plan,
            "teaching_notes": teaching_notes,
            "blocks": blocks, "question_ids": qids,
            "rubric": rubric,
            "minutes": 60, "completion": completion, "assessment": ass,
            "source_ids": sorted(set(sources)),
            "review_status": "generated",
            "dynamic_note": "复习项与练习以 state.db 的 FSRS 到期队列和 plan_adjustments 为准；本文件只给固定骨架。",
        })
    # ---- 素材全覆盖：选材按 topic 走，难免有素材永远排不上。
    # 未使用的素材按级别窗口补进「同 topic 且当天素材最少」的那一天，
    # 保证 coverage 报告里的 unused 不是被静默隐藏，而是真正进入课程。
    used_mids = {mid for d in days for mid in d.get("material_ids") or []}
    for m in sorted(materials, key=lambda x: x["id"]):
        if m["id"] in used_mids:
            continue
        lvl = m.get("level", "N5")
        a, b = LEVEL_WINDOWS.get(lvl, (66, 75))
        pool = [d for d in days if a <= d["day"] <= b] or days
        pool.sort(key=lambda d: (d.get("scene_topic_key") != m.get("topic"),
                                 len(d.get("material_ids") or []), d["day"]))
        tgt = pool[0]
        tgt.setdefault("material_ids", []).append(m["id"])
        used_mids.add(m["id"])
    data = {"meta": {"version": "4", "days": 80, "minutes_per_day": 60,
                     "total_hours": 80, "framework": "research/nh80_framework.md",
                     "generated_at": _build_stamp(r), "generator": "scripts/curriculum.py",
                     "level_windows": {k: list(v) for k, v in LEVEL_WINDOWS.items()},
                     "honesty": "由真实知识种子按 NH80 高频压缩习得法程序化组装，非 80 篇人工精修教材；"
                                "80 学时是压缩冲刺路径，不等于 JLPT 官方学时标准，也不承诺合格分数；"
                                "Day 1-3 经端到端演练验证。"},
            "days": days}
    return {"data": data, "seeds": seeds, "gday": gday, "valid_ids": valid_ids,
            "learned_final": learned}


def validate(data: dict, seeds: dict) -> dict:
    """强校验：10 要素、60 分钟、先修、超纲、覆盖率、评估唯一。"""
    errs, warns = [], []
    days = data["days"]
    if len(days) != 80 or [d["day"] for d in days] != list(range(1, 81)):
        errs.append("天数不是 1..80 连续")
    gmap = {g["id"]: g for g in seeds["grammar"]}
    vmap = {v["id"]: v for v in seeds["vocabulary"]}
    valid = {x["id"] for k in ("vocabulary", "grammar", "kanji") for x in seeds[k]}
    qmap = {q["id"]: q for q in seeds["questions"]}
    mmap = {m["id"]: m for m in seeds["materials"]}
    gday, learned = {}, set()
    required = ("day phase theme scene scene_tag can_do focus objectives "
                "scene_topic_key scene_topic topic_match "
                "new_vocab_ids new_grammar_ids new_kanji_ids "
                "review_knowledge_ids material_ids blocks question_ids rubric minutes completion "
                "assessment source_ids review_status").split()
    introduced = set()
    used_q, used_m = set(), set()
    for d in days:
        for k in required:
            if k not in d: errs.append("Day %d 缺字段 %s" % (d["day"], k))
        if sum(b["min"] for b in d["blocks"]) != 60:
            errs.append("Day %d 时间块合计 != 60" % d["day"])
        if d["minutes"] != 60: errs.append("Day %d minutes != 60" % d["day"])
        new = d["new_vocab_ids"] + d["new_grammar_ids"] + d["new_kanji_ids"]
        for kid in new:
            if kid not in valid: errs.append("Day %d 引用不存在知识 %s" % (d["day"], kid))
        introduced |= set(new)
        learned |= set(new)
        for gid in d["new_grammar_ids"]:
            gday[gid] = d["day"]
            for p in (gmap.get(gid, {}).get("prerequisites") or []):
                if p not in gday:
                    errs.append("Day %d 语法 %s 的先修 %s 尚未出现" % (d["day"], gid, p))
                elif gday[p] >= d["day"]:
                    errs.append("Day %d 语法 %s 的先修 %s 同日或更晚" % (d["day"], gid, p))
        for qid in d["question_ids"]:
            if qid not in qmap: errs.append("Day %d 题目不存在 %s" % (d["day"], qid))
            else:
                used_q.add(qid)
                for kid in qmap[qid].get("knowledge_ids") or []:
                    if kid not in learned:
                        errs.append("Day %d 题目 %s 超纲引用 %s" % (d["day"], qid, kid))
        for mid in d["material_ids"]:
            if mid not in mmap: errs.append("Day %d 素材不存在 %s" % (d["day"], mid))
            else:
                used_m.add(mid)
                gate = {"N5": 1, "N4": 26, "N3": 46}.get(mmap[mid].get("level", "N5"), 1)
                if d["day"] < gate:
                    errs.append("Day %d 素材 %s 等级 %s 超前" % (d["day"], mid, mmap[mid].get("level")))
                if mmap[mid].get("review_status") == "index_only" and mmap[mid].get("text_ja"):
                    errs.append("Day %d 外部索引素材 %s 含正文，违反许可" % (d["day"], mid))
        if len(d["question_ids"]) < 5:
            errs.append("Day %d 测验题不足 5 道（实际 %d）" % (d["day"], len(d["question_ids"])))
        if not d["objectives"] or not d["scene"] or not d["completion"]:
            errs.append("Day %d 存在空要素" % d["day"])

    # ---- v3 新增检查（既有强校验保持不变）----
    for d in days:
        day = d["day"]
        lc = d.get("lesson_core")
        if not isinstance(lc, list) or len(lc) != 3:
            errs.append("Day %d lesson_core 不是恰好 3 句" % day)
        rp = d.get("review_plan")
        if not isinstance(rp, list):
            errs.append("Day %d review_plan 非数组" % day)
        else:
            rev_ids = set(d.get("review_knowledge_ids") or [])
            for it in rp:
                if not isinstance(it, dict) or it.get("kid") not in rev_ids:
                    errs.append("Day %d review_plan 项不属于当天 review_knowledge_ids" % day)
                    break
                if it.get("planned_only") is not True:
                    errs.append("Day %d review_plan 项未标 planned_only=true" % day)
                    break
        if not isinstance(d.get("teaching_notes"), list):
            errs.append("Day %d teaching_notes 非数组" % day)

    # ---- v4 课程对齐硬校验（契约第 7 节）----
    for d in days:
        day = d["day"]
        tmatch = d.get("topic_match")
        if tmatch not in ("exact", "partial", "review"):
            errs.append("Day %d topic_match 非法：%r" % (day, tmatch))
        scene_topic = d.get("scene_topic") or ""
        if not scene_topic:
            errs.append("Day %d 缺 scene_topic" % day)
        elif scene_topic not in (d.get("can_do") or ""):
            errs.append("Day %d can_do 未包含场景中文标签「%s」" % (day, scene_topic))
        mats = [mmap[mid] for mid in (d.get("material_ids") or []) if mid in mmap]
        if tmatch != "review":
            if not any(m.get("topic") == d.get("scene_topic_key") for m in mats):
                errs.append("Day %d 没有与 scene_topic_key=%s 同 topic 的素材" %
                            (day, d.get("scene_topic_key")))
        lc = d.get("lesson_core")
        if isinstance(lc, list) and lc:
            if lc[0].get("origin") != "material":
                errs.append("Day %d lesson_core 第一句不是素材句（origin=%r）" %
                            (day, lc[0].get("origin")))
            if not any(s.get("origin") == "material" for s in lc):
                errs.append("Day %d lesson_core 没有任何 origin=material 的句子" % day)
        new_g = list(d.get("new_grammar_ids") or [])
        for gid in new_g:
            if not _grammar_supported(gid, mats, d.get("new_vocab_ids") or [], gmap, vmap):
                errs.append("Day %d 新语法 %s 未出现在当天素材正文/grammar_ids/新词例句" % (day, gid))
        if new_g and not any(_grammar_evidence(gid, mats, d.get("new_vocab_ids") or [],
                                                gmap, vmap, strict=True) for gid in new_g):
            # 不把它升级成 err：现有素材库不足以让 96 条语法都落在同一天的素材里。
            # 但必须显式披露，不能像旧版那样用「语法自家例句」把未对齐粉饰成已对齐。
            warns.append("Day %d 的新语法（%s）只有自家例句，当天素材没有硬证据"
                         % (day, "、".join(new_g)))

    seen_ass = {}
    for d in days:
        if d["assessment"] != "none":
            seen_ass.setdefault(d["day"], []).append(d["assessment"])
    for day, a in seen_ass.items():
        if len(a) != 1: errs.append("Day %d 叠加多个测试 %s" % (day, a))

    # ---- 分级兑现检查（修 curriculum_provenance.md 的硬伤：100% 覆盖率曾掩盖阶段偏科）----
    level_of = {}
    for k in ("vocabulary", "grammar", "kanji"):
        for x in seeds[k]:
            level_of[x["id"]] = x.get("jlpt", "N5")
    phase_level = defaultdict(lambda: defaultdict(int))
    p4_thin = []
    for d in days:
        new = d["new_vocab_ids"] + d["new_grammar_ids"] + d["new_kanji_ids"]
        for kid in new:
            phase_level[d["phase"]][level_of.get(kid, "N5")] += 1
        if d["phase"] == "P4" and len(new) < 2:
            p4_thin.append(d["day"])
    delivery = {p: dict(c) for p, c in sorted(phase_level.items())}
    for ph, floors in {"P3": {"N4": 20}, "P4": {"N3": 40}}.items():
        for lvl, floor in floors.items():
            got = phase_level[ph].get(lvl, 0)
            if got < floor:
                errs.append("%s 阶段 %s 级新知仅 %d 项，低于下限 %d（分级目标未兑现）" % (ph, lvl, got, floor))
    if p4_thin:
        errs.append("P4（N3 冲刺）存在几乎无新知的天：%s" % p4_thin[:10])

    # ---- 教学设计差异化检查：不允许 80 天共用一套文案（框架 §3.2）----
    design = {
        "distinct_scene": len({d["scene"] for d in days}),
        "distinct_can_do": len({d.get("can_do", "") for d in days}),
        "distinct_objectives": len({tuple(d["objectives"]) for d in days}),
        "distinct_rubric": len({d["rubric"] for d in days}),
        "distinct_theme": len({d["theme"] for d in days}),
    }
    if design["distinct_objectives"] < 70:
        errs.append("能力目标模板化：80 天仅 %d 种不同 objectives" % design["distinct_objectives"])
    for key, floor in (("distinct_scene", 70), ("distinct_can_do", 55), ("distinct_theme", 60)):
        if design[key] < floor:
            warns.append("%s 仅 %d 种（下限 %d），需补充场景/任务池" % (key, design[key], floor))

    coverage = {
        "vocabulary": {"total": len(seeds["vocabulary"]),
                       "introduced": sum(1 for x in seeds["vocabulary"] if x["id"] in introduced),
                       "unused": [x["id"] for x in seeds["vocabulary"] if x["id"] not in introduced]},
        "grammar": {"total": len(seeds["grammar"]),
                    "introduced": sum(1 for x in seeds["grammar"] if x["id"] in introduced),
                    "unused": [x["id"] for x in seeds["grammar"] if x["id"] not in introduced]},
        "kanji": {"total": len(seeds["kanji"]),
                  "introduced": sum(1 for x in seeds["kanji"] if x["id"] in introduced),
                  "unused": [x["id"] for x in seeds["kanji"] if x["id"] not in introduced]},
        "questions": {"total": len(seeds["questions"]), "used": len(used_q),
                      "unused": [q["id"] for q in seeds["questions"] if q["id"] not in used_q]},
        "materials": {"total": len(seeds["materials"]), "used": len(used_m),
                      "unused": [m["id"] for m in seeds["materials"] if m["id"] not in used_m]},
    }
    for k, v in coverage.items():
        if v.get("unused"): warns.append("%s 未覆盖 %d 项（见报告）" % (k, len(v["unused"])))
    grammar_total = sum(len(d.get("new_grammar_ids") or []) for d in days)
    grammar_backed = 0
    for d in days:
        mats = [mmap[mid] for mid in (d.get("material_ids") or []) if mid in mmap]
        for gid in d.get("new_grammar_ids") or []:
            if _grammar_evidence(gid, mats, d.get("new_vocab_ids") or [],
                                 gmap, vmap, strict=True):
                grammar_backed += 1
    alignment = {
        # exact 的口径是「主素材与场景同 topic」，不等于读写两篇都同主题；
        # 真正两篇同主题另记 paired_same_topic，避免用一个数字夸大对齐度。
        "primary_match": sum(1 for d in days if d.get("topic_match") == "exact"),
        "paired_same_topic": sum(1 for d in days
                                 if d.get("topic_match") == "exact"
                                 and d.get("material_pair") == "same_topic"),
        "partial": sum(1 for d in days if d.get("topic_match") == "partial"),
        "review": sum(1 for d in days if d.get("topic_match") == "review"),
        "material_lines": sum(1 for d in days for s in (d.get("lesson_core") or [])
                              if isinstance(s, dict) and s.get("origin") == "material"),
        "grammar_backed_by_material": grammar_backed,
        "grammar_new_total": grammar_total,
    }
    alignment["exact"] = alignment["primary_match"]   # 兼容旧调用方
    return {"ok": not errs, "errors": errs[:40], "error_count": len(errs),
            "warnings": warns, "coverage": coverage,
            "level_delivery": delivery, "teaching_design": design,
            "alignment": alignment,
            "assessments": {str(k): v[0] for k, v in sorted(seen_ass.items())},
            "generated_days": sum(1 for d in days if d["review_status"] == "generated")}


def render_day_md(d: dict, seeds: dict, out: Path):
    def V(ids):
        m = {x["id"]: x for x in seeds["vocabulary"]}
        return "\n".join("- `%s` **%s**（%s）— %s" % (i, m[i]["surface"], m[i]["kana"], m[i]["meaning_zh"])
                         for i in ids if i in m) or "- 本日无新增词汇"
    def G(ids):
        m = {x["id"]: x for x in seeds["grammar"]}
        return "\n".join("- `%s` **%s** — %s｜接续：%s" %
                         (i, m[i]["pattern"], m[i]["meaning_zh"], m[i]["connection"])
                         for i in ids if i in m) or "- 本日无新增语法"
    def K(ids):
        m = {x["id"]: x for x in seeds["kanji"]}
        return "\n".join("- `%s` **%s** 音:%s 训:%s｜%s" %
                         (i, m[i]["char"], "/".join(m[i]["onyomi"]), "/".join(m[i]["kunyomi"]), m[i]["zh_trap"])
                         for i in ids if i in m) or "- 本日无新增汉字"
    qm = {q["id"]: q for q in seeds["questions"]}
    mm = {m["id"]: m for m in seeds["materials"]}
    lines = [
        "# Day %03d · %s" % (d["day"], d["theme"]),
        "",
        "- 阶段：%s｜场景：%s" % (d["phase"], d["scene"]),
        "- 场景主题：%s（`%s` / 对齐：`%s`）" % (
            d.get("scene_topic", ""), d.get("scene_topic_key", ""), d.get("topic_match", "")),
        "- **Can-do（本日真实任务）**：%s" % d.get("can_do", ""),
        "- 能力侧重：%s｜方法依据：`research/nh80_framework.md`" % "、".join(d.get("focus", [])),
        "- 预计时长：%d 分钟｜测试：%s｜审核状态：`%s`（程序化组装，非人工精修教材）" %
        (d["minutes"], d["assessment"], d["review_status"]),
        "", "## 1. 能力目标", *["- " + x for x in d["objectives"]],
        "", "## 1.1 今天要会的 3 句（来源：%s）" %
        "、".join(sorted({s.get("origin", "") for s in d.get("lesson_core") or []})),
    ]
    for s in d.get("lesson_core") or []:
        lines.append("- [%s] %s（%s）" % (s.get("origin", ""), s.get("ja", ""), s.get("zh", "")))
    lines += [
        "", "## 2. 新词汇（ID）", V(d["new_vocab_ids"]),
        "", "## 3. 新语法（含先修）", G(d["new_grammar_ids"]),
        "", "## 4. 新汉字（中日差异）", K(d["new_kanji_ids"]),
        "", "## 5. 预习建议（planned_only，非 FSRS 到期项）",
        "- " + ("、".join("`%s`" % x for x in d["review_knowledge_ids"]) or "无（首日或纯新课）"),
        "", "## 6. 听力与阅读素材",
    ]
    for mid in d["material_ids"]:
        m = mm.get(mid)
        if not m: continue
        if m.get("review_status") == "index_only":
            lines.append("- `%s` **%s**｜外部索引 [%s](%s)｜%s（不复制正文）" %
                         (mid, m["title"], m.get("license", ""), m.get("url", ""), m.get("level", "")))
        else:
            lines.append("- `%s` **%s**（%s / %s / %ds）｜正文：%s" %
                         (mid, m["title"], m["kind"], m.get("level", ""), m.get("duration_sec", 0),
                          (m.get("text_ja") or "")[:80]))
    lines += ["", "## 7. 互动练习与时间块"]
    for b in d["blocks"]:
        lines.append("- **%d 分钟 · %s** — %s" % (b["min"], b["type"], b["desc"]))
    lines += ["", "## 8. 测验题与评分标准"]
    for qid in d["question_ids"]:
        q = qm.get(qid)
        if q:
            lines.append("- `%s` [%s/难度%s] %s" % (qid, q["type"], q["difficulty"],
                                                    (q.get("prompt_ja") or q.get("prompt_zh") or "")[:60]))
    lines += ["- 评分：%s" % d["rubric"],
              "", "## 9. 完成条件", "- " + d["completion"],
              "", "## 10. 关联资料来源", "- " + "、".join("`%s`" % s for s in d["source_ids"]),
              "", "> 动态任务说明：%s" % d["dynamic_note"],
              "> 在线/本地每日页面：`web/day-%03d.html`（可视化、TTS、交互练习、回传码）" % d["day"], ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def write_all(root=None, data=None, validation=None, seeds=None) -> dict:
    r = root_of(root)
    b = build(r) if data is None else {"data": data, "seeds": seeds}
    data = b["data"]; seeds = b["seeds"]
    validation = validation or validate(data, seeds)
    if not validation["ok"]:
        raise ValueError("课程校验未通过，拒绝写入：%s" % validation["errors"][:5])
    cd = r / "curriculum"; cd.mkdir(parents=True, exist_ok=True)
    (cd / "curriculum.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for d in data["days"]:
        render_day_md(d, seeds, cd / ("day-%03d.md" % d["day"]))
    # roadmap
    rm = ["# 80 天课程地图", "",
          "**方法论**：`research/nh80_framework.md`（NH80 高频压缩习得法）。",
          "不照抄 Irodori / Marugoto 任何一套教材的课序；综合多套教材与二语习得研究后自研一套",
          "面向 80 学时压缩冲刺 N3 的编排原则：高频优先、Can-do 驱动、变形先行、迁移加速但强制验证、",
          "N3 官方能力锚定、检索与输出占比最大化。",
          "",
          "**学时口径（诚实）**：80 天 × 60 分钟 = 80 学时。Irodori 官方自述全四册需 360–500 学时，",
          "且 Starter–Elementary 2 才到 N4。因此本路线是「用高强度换时长」的压缩冲刺，",
          "目标是尽可能接近 N3 的高频能力与真实交流，**不等于官方学时标准，也不承诺 JLPT 合格分数**。",
          "80 天是首轮周期，不是硬性成绩承诺。", "",
          "每天原则上 60 分钟；同一天的多种测试已合并为一项，不叠加。", "",
          "| 阶段 | 天数 | 主线 |", "|---|---|---|"]
    for code, a, bb, desc in PHASES:
        rm.append("| %s | %d–%d | %s |" % (code, a, bb, desc))
    rm += ["", "## 评估日历（每天最多一项）", "",
           "| Day | 类型 |", "|---|---|"]
    for d in data["days"]:
        if d["assessment"] != "none":
            rm.append("| %d | %s |" % (d["day"], d["assessment"]))
    rm += ["", "## 运行方式", "",
           "1. `python3 scripts/nh80.py start-day N` 生成当天 briefing（含 FSRS 到期队列）。",
           "2. `python3 scripts/new_session_prompt.py N` 复制提示词，在 WorkBuddy **新建独立会话**粘贴。",
           "3. 可选打开 `web/day-NNN.html` 做可视化/听力/练习，结束后复制回传码。",
           "4. `python3 scripts/nh80.py import-web-result '<码>'` 写回本地 SQLite。",
           "5. `python3 scripts/nh80.py finish-day N` 落盘、导出镜像、生成下一日任务。", "",
           "详见 `docs/DAILY_SESSION.md` 与 `AGENTS.md`。", ""]
    (cd / "roadmap.md").write_text("\n".join(rm), encoding="utf-8")
    # coverage report
    cov = validation["coverage"]
    cr = ["# 课程覆盖率与完整性检查", "", "生成时间：%s" % data["meta"]["generated_at"],
          "校验结果：**%s**（errors=%d）" % ("PASS" if validation["ok"] else "FAIL", validation["error_count"]), "",
          "## 知识点覆盖", "", "| 类别 | 总数 | 引入/使用 | 覆盖率 |", "|---|---|---|---|"]
    for k, v in cov.items():
        n = v.get("introduced", v.get("used", 0))
        cr.append("| %s | %d | %d | %.1f%% |" % (k, v["total"], n, 100.0 * n / v["total"] if v["total"] else 0))
    cr += ["", "## 未覆盖项（如实列出，不隐藏）", ""]
    for k, v in cov.items():
        cr.append("- **%s**：%s" % (k, "、".join(v["unused"][:30]) + ("…" if len(v["unused"]) > 30 else "")
                                    if v["unused"] else "全部覆盖"))
    cr += ["", "## 分级兑现（防止 100% 覆盖率掩盖阶段偏科）", "",
           "按 `research/nh80_framework.md` 的压缩路径，级别必须集中在对应阶段真实引入：",
           "", "| 阶段 | N5 新知 | N4 新知 | N3 新知 |", "|---|---|---|---|"]
    for p, c in sorted(validation.get("level_delivery", {}).items()):
        cr.append("| %s | %d | %d | %d |" % (p, c.get("N5", 0), c.get("N4", 0), c.get("N3", 0)))
    cr += ["", "- 强校验下限：P3 的 N4 ≥ 20 项、P4 的 N3 ≥ 40 项；P4 不得出现几乎无新知的天。",
           "- 旧版曾出现 P4 20 天仅 1 个新词、0 个汉字，本表即为防止该问题复发。",
           "", "## 场景-素材-语法对齐（契约第 7 节）", ""]
    al = validation.get("alignment") or {}
    cr.append("统计：主素材同主题 %d 天｜读写两篇都同主题 %d 天｜纯复习 %d 天｜"
              "lesson_core 中 origin=material 的句子 %d 行。"
              % (al.get("primary_match", 0), al.get("paired_same_topic", 0),
                 al.get("review", 0), al.get("material_lines", 0)))
    cr.append("语法硬证据：%d / %d 条新语法能在当天素材正文、素材 grammar_ids 或当天新词例句中找到证据；"
              "其余只靠语法自身例句，已逐天列入下方告警，不计入「已对齐」。"
              % (al.get("grammar_backed_by_material", 0), al.get("grammar_new_total", 0)))
    cr += ["", "> 「主素材同主题」只说明当天**第一主角素材**与场景一致；若该 topic 在本级别只有",
           "> 一种体裁，另一篇会按「同级别最近 topic」补位（`material_pair=mixed_topic`）。",
           "> 真正读写同主题的天数单独统计，不用一个「exact」夸大对齐度。", ""]
    cr += ["", "| Day | topic | 素材 id | lesson_core 来源 | 是否 exact |", "|---|---|---|---|---|"]
    for d in data["days"]:
        origins = "/".join(sorted({s.get("origin", "") for s in (d.get("lesson_core") or [])
                                   if isinstance(s, dict)}))
        cr.append("| %d | %s（%s） | %s | %s | %s |" % (
            d["day"], d.get("scene_topic", ""), d.get("scene_topic_key", ""),
            "、".join(d.get("material_ids") or []), origins,
            "是" if d.get("topic_match") == "exact" else ("部分" if d.get("topic_match") == "partial" else "复习")))
    cr += ["", "## 教学设计差异化（防止 80 天共用一套模板）", ""]
    for k, v in sorted(validation.get("teaching_design", {}).items()):
        cr.append("- %s：**%d / 80** 种" % (k, v))
    cr += ["", "## 先修与超纲检查", "",
           "- 语法 prerequisites 必须出现在更早的天：%s" % ("通过" if not any("先修" in e for e in validation["errors"]) else "失败"),
           "- 题目/素材不得引用尚未教授的知识：%s" % ("通过" if not any("超纲" in e for e in validation["errors"]) else "失败"),
           "- 每天时间块合计 60 分钟：%s" % ("通过" if not any("时间块" in e for e in validation["errors"]) else "失败"),
           "- 同一天多测试合并（不叠加）：%s" % ("通过" if not any("叠加" in e for e in validation["errors"]) else "失败"),
           "", "## 诚实披露", "",
           "- 80 天课程全部由 `scripts/curriculum.py` 从真实、已校验的知识种子程序化组装，",
           "  `review_status=generated`，**不是 80 篇人工逐课精修的教材**。Day 1–3 已做端到端演练验证。",
           "- 课程内容引用的是结构化知识点 ID 与题库 ID，讲解措辞由每日教师 Agent 现场生成，",
           "  不在此重复堆砌静态课文，也不假装已经教过。",
           "- 固定骨架（知识目标）稳定；实际复习与练习由 `state.db` 的 FSRS 到期队列与",
           "  `plan_adjustments` 动态决定。",
           "- 未覆盖项与 `%s` 条 needs_review 种子见 `knowledge/seeds/`。"
           % sum(1 for k in ("vocabulary", "grammar", "kanji") for x in seeds[k]
                 if x.get("review_status") == "needs_review"), ""]
    (cd / "coverage_report.md").write_text("\n".join(cr), encoding="utf-8")
    return {"ok": True, "days": 80, "files": 82, "validation": validation}
