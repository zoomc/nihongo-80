"""curriculum.py — 由真实知识种子生成 80 天完整课程 + 先修校验 + 分级兑现报告。

理论依据：research/nh80_framework.md（NH80 高频压缩习得法）。
不照抄任何一套教材的课序；按「多套教材综合提炼的原则」做确定性重排：
高频优先、场景 Can-do 驱动、变形先行拓扑、中日韩迁移但强制验证、N3 能力锚定。

诚实声明：课程由程序从已审核种子组装（review_status=generated），不是 80 篇人工精修教材。
骨架（知识目标）稳定；动态任务（实际复习/练习）由 state.db 的 plan_adjustments/review_tasks 决定。
"""
from __future__ import annotations

import json
from collections import defaultdict
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

# Can-do 任务池：按阶段给出真实可执行任务，不是「学习某某语法」式空标题。
# 占位符 {g}=当天句型 {v}=当天新词 {topic}=当天素材主题。
CANDO_BANK = {
    "P1": [
        ("初次见面", "用「{g}」向对方介绍自己并确认对方姓名，全程不靠中文汉字猜读音"),
        ("语音辨识", "分辨 {v} 的长音、促音与浊音，听写后自行对照订正"),
        ("教室点名", "听准并读出 {v}，把每个词的假名与实际发音对上，再各造一句"),
        ("时令寒暄", "按早/午/晚选对问候语，完成一次得体的开场"),
        ("一日复盘", "不看笔记说出今天 3 个新词与 1 个句型的用法"),
        ("家庭介绍", "用「{g}」说出自己与同伴的身份关系，不给对方名字误加 さん"),
        ("便利店", "听懂价格与数字，用当天句型问清「这是什么／多少钱」并道谢"),
        ("问路起点", "听懂场所词与方位表达，用自己的话复述目的地"),
        ("购物结算", "在收银台完成一轮问价—确认—付款的简短对话"),
        ("时间安排", "用已学时间词说出今天的两项安排，让对方复述确认"),
    ],
    "P2": [
        ("咖啡店点单", "用「{g}」点单、确认数量与价格，并处理一次听不懂时的追问"),
        ("电车问路", "听懂站台广播里的 {v}，用已学句型复述换乘方案"),
        ("预约登记", "用礼貌体报出姓名、时间与人数，并核对对方复述是否正确"),
        ("工作打卡", "说明自己今天做了什么、几点结束，动词变形不靠中文语序直译"),
        ("购物退换", "用「{g}」说明商品问题并提出一个具体请求"),
        ("天气闲聊", "听懂 {topic} 相关的简短闲谈，接着说出自己的一天"),
        ("餐厅评价", "用形容词过去式与「{g}」说清两道菜的差别"),
        ("朋友邀约", "发出一次邀请并回应对方的婉拒，注意时态与否定"),
        ("日程协调", "用「{g}」把两件事排进同一天并说明先后顺序"),
        ("电话留言", "听懂一段短留言，复述谁、何时、要做什么"),
    ],
    "P3": [
        ("搬家准备", "用「{g}」说明哪些事已经做完、哪些留到之后，区分 てある/ておく"),
        ("故障报修", "用「{g}」描述设备状态与发生经过，自动词/他动词不混用"),
        ("旅行复盘", "用「{g}」讲一段过去经历，并说明当时的条件与结果"),
        ("同事协作", "用授受表达说清谁帮谁做了什么，中文「给」不直译"),
        ("医院问诊", "用「{g}」说明症状持续时间与变化，听懂医嘱要点"),
        ("邮件回复", "用「{g}」写出 3 句得体的回信，简体和敬体不混用"),
        ("规则说明", "用「{g}」解释一条手续或规则，并回答一个追问"),
        ("意愿协商", "用条件表达提出方案，比较两种做法后给出结论"),
        ("传闻转述", "用「{g}」转述听到的信息，明确标注信息来源与不确定度"),
        ("经验对比", "用「{g}」区分「做过」与「经常做」，并各给一个真实例子"),
    ],
    "P4": [
        ("市政通知", "读一段 {topic} 通知，30 秒说出主旨与一条支撑细节，不逐字翻译"),
        ("新闻标题", "从 {topic} 标题与导语抓住概要，说明哪句话支撑你的判断"),
        ("部门联络", "听一段近自然语速的 {topic} 对话，复述人物关系与下一步动作"),
        ("会议转达", "用「{g}」把听到的安排转述给第三方，敬体层级保持一致"),
        ("意见陈述", "用「{g}」说明原因与推测的区别，避免把猜测说成事实"),
        ("服务投诉", "用「{g}」得体地说明问题、提出要求并确认对方承诺"),
        ("略难短文", "读一篇含替换表达的 {topic} 短文，借上下文推出主旨后自检依据"),
        ("计划变更", "用「{g}」说明原定安排、变更原因与替代方案"),
        ("数据说明", "用 {v} 描述趋势与例外，并回答「为什么」的追问"),
        ("立场表达", "用「{g}」表示部分同意与保留，不用非黑即白的中文式直译"),
        ("路边采访", "听 {topic} 相关的两段短发言，指出说话人关系的差异"),
        ("书面申请", "用「{g}」写一段 4 句以上的申请说明，检查接续与前后逻辑"),
    ],
    "P5": [
        ("弱项重做", "把最近错得最多的 {g} 重新用于两个不同场景，并说出为什么上次错"),
        ("混合听读", "连续处理 {topic} 的听解与读解各一段，比较两者的信息缺口"),
        ("限时表达", "不查资料，用至少 3 个 {v} 说满 60 秒并自评语病"),
        ("角色互换", "与教师交换角色完成 {topic} 对话，负责追问与澄清"),
        ("错题讲评", "挑一道自己错过的题，把解题依据讲给「新手」听"),
        ("语体切换", "把同一段 {topic} 内容分别用简体与敬体各说一遍"),
        ("信息整合", "把两条互相矛盾的 {topic} 信息合并成一段准确说明"),
        ("复述压缩", "听一段 {topic} 长对话，用 3 句概括人物关系与结论"),
        ("即兴应对", "对 {topic} 的突发状况给出两个方案并说明取舍"),
        ("迁移输出", "把「{g}」用在一个从未练过的新场景里，检验是否真迁移"),
    ],
    "P6": [
        ("分项盘点", "在模拟卷中分别报出词汇/语法/阅读/听力/表达的自我判断依据"),
        ("错因归档", "把本轮高频错误归入遗忘/混淆/助词/变形/听辨/理解六类"),
        ("限时读解", "在限定时间内完成 {topic} 读解并说明取舍策略"),
        ("综合复述", "听读结合复述 {topic} 信息，标出哪部分来自听、哪部分来自读"),
        ("下一轮规划", "基于真实数据说出下一周期最该补的两项能力，不写空泛决心"),
    ],
}

# 能力目标池：每天按确定性轮换抽取，避免 80 天 objectives 完全相同
OBJECTIVE_POOL = [
    "能听懂 {topic} 场景的关键词并复述要点",
    "能在无提示条件下独立产出至少 1 句完整日语（口头或书面）",
    "能说明「{g}」的接续条件与适用场合，并给出一个反例",
    "能辨析 {v} 与已学近义表达的差别，不按中文词义套用",
    "能读准当天汉字的音读/训读，不按中文读音类推",
    "能在近自然语速的短对话中抓住人物关系与后续动作",
    "能从通知或短文中提取主旨并指出一条支撑细节",
    "能把当天表达迁移到一个新场景，而不是复述例句",
    "能区分事实陈述与推测表达，避免把猜测说成定论",
    "能对自己的错误归因到具体类型（遗忘/混淆/助词/变形/听辨/理解）",
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

# 素材 topic 原为英文标签，转成中文场景词后再进课程文案，避免「读一段 discussion 通知」这类生硬句子
TOPIC_ZH = {
    "restaurant": "餐厅点餐", "weather": "天气", "work": "工作沟通", "travel": "旅行",
    "email": "邮件往来", "notice": "通知告示", "health": "健康问诊", "transport": "交通出行",
    "school": "校园", "family": "家庭", "asking_directions": "问路", "tech": "科技产品",
    "appointment": "预约", "news_summary": "新闻概要", "procedure": "手续办理",
    "reservation": "预订", "technology": "科技", "greeting": "寒暄", "self_intro": "自我介绍",
    "shopping": "购物", "daily_routine": "日常作息", "entertainment": "休闲娱乐",
    "request": "请求委托", "discussion": "意见讨论", "explanation": "说明解释",
    "announcement": "公告",
}


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


def _pick_materials(day, learned, materials, used_m):
    """主素材必须是有正文的原创/开放许可文本；外部版权教材只作每周延伸索引。"""
    # 素材按 level 分级选材，不要求所有引用词都已学：可理解输入本来允许 5-10% 生词
    # （CONTRACTS 第 7 节 known_ratio）。题目才做严格超纲检查。
    allowed = {"N5": 1, "N4": 26, "N3": 46}
    def ok(m):
        return day >= allowed.get(m.get("level", "N5"), 1)
    want = "N5" if day <= 25 else "N4" if day <= 45 else "N3"
    def order(m):
        return (m["id"] in used_m, 0 if m.get("level") == want else 1, m["id"])
    originals = [m for m in materials if m.get("review_status") != "index_only" and ok(m)]
    reading = sorted([m for m in originals if m.get("kind") == "reading"], key=order)
    listening = sorted([m for m in originals if m.get("kind") == "listening"], key=order)
    def choose(pool):
        if not pool:
            return None
        m = pool[0]
        used_m.add(m["id"])
        return m["id"]
    out = [x for x in (choose(reading), choose(listening)) if x]
    if day % 7 == 0:      # 外部资源只作延伸阅读，不占听力/阅读正文位
        ext = [m for m in materials if m.get("review_status") == "index_only"]
        if ext:
            out.append(ext[(day // 7 - 1) % len(ext)]["id"])
    return out


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

    # 知识引入窗口（框架 §3.1/§3.2）：级别集中在对应阶段，窗口内高频优先；P5/P6 不新增。
    # 旧算法把 N3 均匀铺到 Day 51–72，因缺 N3 种子导致 P4 阶段空转，已废弃。
    vwin = _windows_by_level(vocab, LEVEL_WINDOWS)
    kwin = _windows_by_level(kanji, LEVEL_WINDOWS)
    gwin, gday = _topo_days_by_level(grammar, GRAMMAR_WINDOWS)

    qidx = _question_index(questions)
    used_q, used_m = set(), set()
    learned = set()
    new_by_day = {}
    days = []
    for day in range(1, 81):
        ph = phase_of(day)
        nv, ng, nk = vwin.get(day, []), gwin.get(day, []), kwin.get(day, [])
        learned |= set(nv + ng + nk)
        new_by_day[day] = nv + ng + nk
        # 复习候选池：1/2/3/7/14/30 天前引入的知识（实际到期由 FSRS 决定）
        rev = []
        for back in (1, 2, 3, 7, 14, 30):
            rev += new_by_day.get(day - back, [])
        rev = list(dict.fromkeys([x for x in rev if x in learned]))[:12]
        level_hint = 1 if day <= 10 else 2 if day <= 25 else 3 if day <= 45 else 4 if day <= 65 else 5
        nq = 8 if assessment_of(day) in ("diagnostic", "final", "midterm", "n3_readiness") else 6
        qids = _pick_questions(day, learned, questions, nq, level_hint, used_q)
        mids = _pick_materials(day, learned, materials, used_m)
        ass = assessment_of(day)
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
        # ---- 差异化教学设计：Can-do 任务驱动，不是 80 天共用一套模板（框架 §3.2）----
        topic = ""
        for mid in mids:
            m = mmap_all.get(mid)
            if m and m.get("topic"):
                topic = m["topic"]; break
        vs = [vmap[i]["surface"] for i in nv[:3] if i in vmap]
        gs = [gmap_all[i]["pattern"] for i in ng[:2] if i in gmap_all]
        ks = [kmap[i]["char"] for i in nk[:4] if i in kmap]
        scene_title = next((mmap_all[mid]["title"] for mid in mids
                            if mmap_all.get(mid, {}).get("title")), "日常对话")
        gtxt = "、".join(gs) or "已学句型"
        vtxt = "、".join(vs) or "当天新词"
        ttext = TOPIC_ZH.get(topic, topic) or "日常生活"
        pool = CANDO_BANK[ph]
        phase_start = next(a for code, a, _b, _ in PHASES if code == ph)
        # 按阶段内顺序取任务，保证 P1 从「自我介绍」起步，不把后期任务轮到零基础的第一天
        scene_tag, task_tpl = pool[(day - phase_start) % len(pool)]
        can_do = task_tpl.format(g=gtxt, v=vtxt, topic=ttext)
        if ass not in ("none", "diagnostic"):
            can_do = "在 %s（%s）中分项展示五维能力，并用「%s」完成 1 次独立输出" % (
                ass, scene_tag, gtxt)
        theme = "%s｜%s" % (scene_tag, "・".join((gs + vs)[:3]) or (topic or "综合应用"))
        scene = "【%s】%s：%s（素材：%s）" % (scene_tag, ttext, can_do, scene_title)
        obj_idx = (day * 2 + day // 5) % len(OBJECTIVE_POOL)
        objectives = [OBJECTIVE_POOL[(obj_idx + j) % len(OBJECTIVE_POOL)].format(
            g=gtxt, v=vtxt, topic=ttext) for j in range(3)]
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
                    b["desc"] = "【%s】%s：听读素材 + 至少 1 次无提示独立输出" % (scene_tag, ttext)
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
        days.append({
            "day": day, "phase": ph, "theme": theme, "scene": scene,
            "scene_tag": scene_tag, "can_do": can_do, "focus": focus,
            "objectives": objectives, "new_vocab_ids": nv, "new_grammar_ids": ng,
            "new_kanji_ids": nk, "review_knowledge_ids": rev,
            "material_ids": mids,
            "blocks": blocks, "question_ids": qids,
            "rubric": rubric,
            "minutes": 60, "completion": completion, "assessment": ass,
            "source_ids": sorted(set(sources)),
            "review_status": "generated",
            "dynamic_note": "复习项与练习以 state.db 的 FSRS 到期队列和 plan_adjustments 为准；本文件只给固定骨架。",
        })
    data = {"meta": {"version": "2", "days": 80, "minutes_per_day": 60,
                     "total_hours": 80, "framework": "research/nh80_framework.md",
                     "generated_at": iso(), "generator": "scripts/curriculum.py",
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
    valid = {x["id"] for k in ("vocabulary", "grammar", "kanji") for x in seeds[k]}
    qmap = {q["id"]: q for q in seeds["questions"]}
    mmap = {m["id"]: m for m in seeds["materials"]}
    gday, learned = {}, set()
    required = ("day phase theme scene scene_tag can_do focus objectives "
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
    return {"ok": not errs, "errors": errs[:40], "error_count": len(errs),
            "warnings": warns, "coverage": coverage,
            "level_delivery": delivery, "teaching_design": design,
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
        "- **Can-do（本日真实任务）**：%s" % d.get("can_do", ""),
        "- 能力侧重：%s｜方法依据：`research/nh80_framework.md`" % "、".join(d.get("focus", [])),
        "- 预计时长：%d 分钟｜测试：%s｜审核状态：`%s`（程序化组装，非人工精修教材）" %
        (d["minutes"], d["assessment"], d["review_status"]),
        "", "## 1. 能力目标", *["- " + x for x in d["objectives"]],
        "", "## 2. 新词汇（ID）", V(d["new_vocab_ids"]),
        "", "## 3. 新语法（含先修）", G(d["new_grammar_ids"]),
        "", "## 4. 新汉字（中日差异）", K(d["new_kanji_ids"]),
        "", "## 5. 需复习的旧知识（候选池，实际以 FSRS 到期队列为准）",
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
           "", "## 教学设计差异化（防止 80 天共用一套模板）", ""]
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
