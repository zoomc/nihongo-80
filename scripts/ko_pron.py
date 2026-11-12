#!/usr/bin/env python3
"""ko_pron.py — 假名→한글 读音转写 + 日语句子读音解析（v12）。

给朝鲜族/韩语母语学习者用的「韩语读音标注」：页面上的日语单词、语法句型、例句，
除日语原文与中文外，再给一行韩语读音（한글 표음）。

两层能力
--------
1. ``to_hangul(kana)``：把**假名**逐拍转写成韩文。
   - 清音/浊音/半浊音、拗音、外来音（ファ/ティ/ウィ…）按国立国语院《外来语表记法》
     「日本語の表記」的口径取音；
   - 拨音 ん → ㄴ，后接 ㅁ/ㅂ/ㅍ 起头的音节时同化为 ㅁ（しんぶん → 심분）；
   - 促音 っ → 紧音（된소리）ㄲ/ㄸ/ㅃ/ㅆ/ㅉ（がっこう → 갓코우）；
   - 长音**按拍转写、不压缩**：とう → 토우、コーヒー → 코오히이。理由是压缩后
     思う（おもう）会变成「오모」、追う 会变成「오우」，词尾信息丢失；逐拍转写
     不会给出错的读音，只是不如韩语借词写法「도쿄」那么本土化。
   - 汉字直接原样保留（本函数只认假名）；要整句读音用 ``ReadingIndex``。

2. ``ReadingIndex``：用词汇种子里的 ``(surface, kana)`` 做最长匹配，把例句转成整句
   假名读音，再交给 ``to_hangul``。
   - **宁可不标，也不给错读音**：句子里只要有一个汉字解析不出来，``reading()`` 就返回
     ``None``，页面直接不显示韩语读音行；
   - 词形只切到词干（食べる → 食べ）来兼容 ます/た/て 形，且只在词尾是假名时切；
   - 匹配不允许停在汉字串中间（「東京」若不在词表里，不会退化成 東(ひがし)+京 的错误读音）。

两份表都是纯代码推导，不写进 seeds：读音由假名唯一确定，放进种子只会制造同步负担。
"""
from __future__ import annotations

import re

# 汉字 / 假名判定
KANJI_RE = re.compile(r"[\u3005\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")  # 々 也算汉字
HIRA_RE = re.compile(r"[\u3041-\u3096]")
KATA_RE = re.compile(r"[\u30a1-\u30f6]")
KANA_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30f6]")


def _is_kanji(ch: str) -> bool:
    return bool(KANJI_RE.match(ch))


def _is_kana(ch: str) -> bool:
    return bool(KANA_RE.match(ch))


# ---------------------------------------------------------------------------
# 五十音（平假名 → 한글）。片假名按 0x60 偏移自动生成。
# ---------------------------------------------------------------------------
_HIRA = {
    "あ": "아", "い": "이", "う": "우", "え": "에", "お": "오",
    "か": "카", "き": "키", "く": "쿠", "け": "케", "こ": "코",
    "が": "가", "ぎ": "기", "ぐ": "구", "げ": "게", "ご": "고",
    "さ": "사", "し": "시", "す": "스", "せ": "세", "そ": "소",
    "ざ": "자", "じ": "지", "ず": "즈", "ぜ": "제", "ぞ": "조",
    "た": "타", "ち": "치", "つ": "쓰", "て": "테", "と": "토",
    "だ": "다", "ぢ": "지", "づ": "즈", "で": "데", "ど": "도",
    "な": "나", "に": "니", "ぬ": "누", "ね": "네", "の": "노",
    "は": "하", "ひ": "히", "ふ": "후", "へ": "헤", "ほ": "호",
    "ば": "바", "び": "비", "ぶ": "부", "べ": "베", "ぼ": "보",
    "ぱ": "파", "ぴ": "피", "ぷ": "푸", "ぺ": "페", "ぽ": "포",
    "ま": "마", "み": "미", "む": "무", "め": "메", "も": "모",
    "や": "야", "ゆ": "유", "よ": "요",
    "ら": "라", "り": "리", "る": "루", "れ": "레", "ろ": "로",
    "わ": "와", "ゐ": "위", "ゑ": "웨", "を": "오", "ん": "ㄴ", "ゔ": "부",
    "ぁ": "아", "ぃ": "이", "ぅ": "우", "ぇ": "에", "ぉ": "오",
    "ゎ": "와", "ゕ": "카", "ゖ": "케",
}

# 拗音（平假名 → 한글）；片假名同名拗音自动生成
_HIRA_DIGRAPH = {
    "きゃ": "캬", "きゅ": "큐", "きょ": "쿄", "きぇ": "케",
    "ぎゃ": "갸", "ぎゅ": "규", "ぎょ": "교", "ぎぇ": "게",
    "しゃ": "샤", "しゅ": "슈", "しょ": "쇼", "しぇ": "셰",
    "じゃ": "자", "じゅ": "주", "じょ": "조", "じぇ": "제",
    "ちゃ": "차", "ちゅ": "추", "ちょ": "초", "ちぇ": "체",
    "ぢゃ": "자", "ぢゅ": "주", "ぢょ": "조",
    "にゃ": "냐", "にゅ": "뉴", "にょ": "뇨",
    "ひゃ": "햐", "ひゅ": "휴", "ひょ": "효",
    "びゃ": "뱌", "びゅ": "뷰", "びょ": "뵤",
    "ぴゃ": "퍄", "ぴゅ": "퓨", "ぴょ": "표",
    "みゃ": "먀", "みゅ": "뮤", "みょ": "묘",
    "りゃ": "랴", "りゅ": "류", "りょ": "료",
    # 外来音
    "ふぁ": "파", "ふぃ": "피", "ふぇ": "페", "ふぉ": "포", "ふゅ": "퓨",
    "てぃ": "티", "でぃ": "디", "とぅ": "투", "どぅ": "두",
    "つぁ": "차", "つぃ": "치", "つぇ": "체", "つぉ": "초",
    "うぃ": "위", "うぇ": "웨", "うぉ": "워",
    "ゔぁ": "바", "ゔぃ": "비", "ゔぇ": "베", "ゔぉ": "보",
    "くぁ": "콰", "くぃ": "퀴", "くぇ": "퀘", "くぉ": "쿼",
    "ぐぁ": "과", "ぐぃ": "귀", "ぐぇ": "궤", "ぐぉ": "고",
    "すぃ": "시", "ずぃ": "지", "いぇ": "예", "きぇ": "케", "ぎぇ": "게",
}

SINGLE = dict(_HIRA)
DIGRAPH = dict(_HIRA_DIGRAPH)
SOKUON = {"っ", "ッ"}
CHOON = {"ー", "ｰ"}
# 韩语输出用韩语标点（日语 。、 直接留给人看会觉得别扭）
KO_PUNCT = {"。": ".", "、": ",", "？": "?", "！": "!", "　": " ", "・": "·"}

for _k, _v in list(_HIRA.items()):
    _code = ord(_k)
    if 0x3041 <= _code <= 0x3096:  # ぁ-ゖ → ァ-ヶ
        SINGLE[chr(_code + 0x60)] = _v
for _k, _v in list(_HIRA_DIGRAPH.items()):
    _kata = "".join(chr(ord(c) + 0x60) if 0x3041 <= ord(c) <= 0x3096 else c for c in _k)
    DIGRAPH[_kata] = _v  # きゃ→キャ, ゔぁ→ヴァ

# 促音：紧音化
TENSE = {"ㄱ": "ㄲ", "ㄷ": "ㄸ", "ㅂ": "ㅃ", "ㅅ": "ㅆ", "ㅈ": "ㅉ",
         "ㅋ": "ㄲ", "ㅌ": "ㄸ", "ㅍ": "ㅃ", "ㅊ": "ㅉ"}

# 谚文分解表（长音 ー 要把前一元音重复出来）
_VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ",
         "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ",
         "ㅌ", "ㅍ", "ㅎ"]

# 长音 ー 重复的是「基础元音」：쇼→쇼오（不是 쇼요）、뉴→뉴우（不是 뉴유）
BASE_VOWEL = {"ㅑ": "ㅏ", "ㅒ": "ㅐ", "ㅕ": "ㅓ", "ㅖ": "ㅔ", "ㅛ": "ㅗ", "ㅠ": "ㅜ",
              "ㅘ": "ㅏ", "ㅙ": "ㅐ", "ㅚ": "ㅔ", "ㅝ": "ㅓ", "ㅞ": "ㅔ", "ㅟ": "ㅣ",
              "ㅢ": "ㅣ"}


def _split_syllable(ch: str):
    """返回 (初声, 中声, 终声)；不是谚文音节时返回 None。"""
    code = ord(ch) - 0xAC00
    if not 0 <= code < 11172:
        return None
    cho = code // 588
    jung = (code % 588) // 28
    jong = code % 28
    return _CHO[cho], _VOWELS[jung], _JONG[jong]


def _syllable(text: str, i: int):
    """从 i 取一个音节，返回 (한글, 消耗长度)；取不到返回 (None, 0)。"""
    two = text[i:i + 2]
    if len(two) == 2 and two in DIGRAPH:
        return DIGRAPH[two], 2
    ch = text[i:i + 1]
    if ch in SINGLE:
        return SINGLE[ch], 1
    return None, 0


def _compose(cho: str, jung: str, jong: str = "") -> str:
    return chr(0xAC00 + _CHO.index(cho) * 588 + _VOWELS.index(jung) * 28
               + (_JONG.index(jong) if jong else 0))


def _add_final(out: list, jong: str) -> None:
    """把 ㄴ/ㅁ 挂到前一个音节的终声；前字已有终声时退化成独立字母（罕见）。"""
    if out:
        sp = _split_syllable(out[-1][-1])
        if sp and not sp[2]:
            out[-1] = out[-1][:-1] + _compose(sp[0], sp[1], jong)
            return
    out.append(jong)


def _tense(syl: str) -> str:
    sp = _split_syllable(syl[-1]) if syl else None
    if not sp:
        return syl
    cho, jung, jong = sp
    return syl[:-1] + _compose(TENSE.get(cho, cho), jung, jong)


def _tense_tsu(syl: str) -> str:
    """っ＋つ：쓰 → 쯔（초성 ㅆ → ㅉ）。"""
    sp = _split_syllable(syl[-1]) if syl else None
    if not sp:
        return syl
    cho, jung, jong = sp
    return syl[:-1] + _compose("ㅉ" if cho == "ㅆ" else TENSE.get(cho, cho), jung, jong)


def to_hangul(text: str) -> str:
    """假名串 → 한글。汉字/拉丁/标点原样保留（只认假名）。"""
    out: list[str] = []
    i, n = 0, len(text)
    tense = False
    while i < n:
        ch = text[i]
        if ch in SOKUON:
            tense = True
            i += 1
            continue
        if ch in CHOON:
            # 长音：重复前一元音的**基础元音**（とー→토오、ショー→쇼오、ニュー→뉴우）。
            # 直接重复介音会写出 쇼요/뉴유 这种错音，所以先把 ㅑㅕㅛㅠ 等还原成单元音。
            prev = out[-1] if out else ""
            sp = _split_syllable(prev[-1]) if prev else None
            if sp and sp[1] not in ("ㅡ", "ㅔ", "ㅐ"):  # ㅡ 无长音；ㅔ/ㅐ＋ー 读 이（ケーキ→케이키）
                vowel = BASE_VOWEL.get(sp[1], sp[1])
                out.append(chr(0xAC00 + _CHO.index("ㅇ") * 588 + _VOWELS.index(vowel) * 28))
            elif sp and sp[1] in ("ㅔ", "ㅐ"):
                out.append("이")
            i += 1
            tense = False
            continue
        if ch == "ん" or ch == "ン":
            nxt, _ = _syllable(text, i + 1)
            nsp = _split_syllable(nxt[-1]) if nxt else None
            bilabial = bool(nsp) and nsp[0] in "ㅁㅂㅍ"
            _add_final(out, "ㅁ" if bilabial else "ㄴ")
            i += 1
            tense = False
            continue
        syl, width = _syllable(text, i)
        if syl:
            if tense:
                # っ＋つ 用 ㅉ（四つ→요쯔）；っ＋す 保持 ㅆ（まっすぐ→마쓰구）
                syl = _tense_tsu(syl) if ch in ("つ", "ツ") else _tense(syl)
            out.append(syl)
            tense = False
            i += width
            continue
        out.append(KO_PUNCT.get(ch, ch))
        tense = False
        i += 1
    return "".join(out)


def kana_only(text: str) -> bool:
    """整串是否只由假名/标点/数字/拉丁组成（即不含汉字），可以安全转写。"""
    return not any(_is_kanji(ch) for ch in str(text or ""))


def pron(text: str) -> str:
    """安全转写：含汉字就返回空串（不猜读音）；固定说法先按 FIXED_READING 修正。"""
    text = str(text or "")
    if not text or not kana_only(text):
        return ""
    return to_hangul(FIXED_READING.get(text, text))


# ---------------------------------------------------------------------------
# 数词 + 量词读音（時/分/月/日/人/歳/円/回/年/週間/か月/階/枚/本/冊/台/杯/匹/軒/個/番/つ）
# 例句里「七時」「２０歳」「三十分」这类极多，靠词表匹配不到，单独给规则。
# ---------------------------------------------------------------------------
_NUM_KANA = {0: "ぜろ", 1: "いち", 2: "に", 3: "さん", 4: "よん", 5: "ご",
             6: "ろく", 7: "なな", 8: "はち", 9: "きゅう"}
_KANJI_NUM = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
_FW_DIGIT = {chr(0xFF10 + i): str(i) for i in range(10)}

_COUNTER_RE = re.compile(
    r"(?P<num>[0-9０-９]+|[〇零一二三四五六七八九十百千万]+|何)"
    r"(?P<unit>時間|週間|か月|ヶ月|ヵ月|時|分|月|日|年|回|度|人|歳|階|枚|本|冊|台|杯|匹|軒|個|番|円|つ)")

_TSU = {"いち": "いっ", "ろく": "ろっ", "はち": "はっ", "じゅう": "じゅっ",
        "ひゃく": "ひゃっ", "びゃく": "びゃっ", "ぴゃく": "ぴゃっ"}

# 每个量词一张小表：suffix 普通后缀；tsu=(后缀, {哪些数走促音便})；ren=(数, 浊化后缀)；
# exact=整体例外；zero=0 的读法。促音便后缀**不再自带「っ」**（否则一本会变成 いっっぽん）。
_COUNTERS = {
    "時": dict(suffix="じ", zero="れいじ",
              exact={4: "よじ", 7: "しちじ", 9: "くじ", 14: "じゅうよじ", 24: "にじゅうよじ"}),
    "分": dict(suffix="ふん", tsu=("ぷん", (1, 6, 8, 10)), ren=(3, "ぷん")),
    "時間": dict(suffix="じかん"),
    "月": dict(suffix="がつ", exact={4: "しがつ", 7: "しちがつ", 9: "くがつ"}),
    "日": dict(suffix="にち", exact={2: "ふつか", 3: "みっか", 4: "よっか",
                                    5: "いつか", 6: "むいか", 7: "なのか", 8: "ようか",
                                    9: "ここのか", 10: "とおか", 14: "じゅうよっか",
                                    20: "はつか", 24: "にじゅうよっか",
                                    17: "じゅうしちにち", 19: "じゅうくにち",
                                    27: "にじゅうしちにち"}),
    "年": dict(suffix="ねん", exact={4: "よねん"}),
    "回": dict(suffix="かい", tsu=("かい", (1, 6, 8, 10))),
    "度": dict(suffix="ど", zero="れいど"),
    "人": dict(suffix="にん", exact={1: "ひとり", 2: "ふたり", 4: "よにん", 7: "しちにん"}),
    "歳": dict(suffix="さい", tsu=("さい", (1, 8, 10)),
              exact={20: "はたち", 100: "ひゃくさい"}),
    "階": dict(zero=None, exact={1000: "せんがい"}, suffix="かい", tsu=("かい", (1, 6, 8, 10)), ren=(3, "がい")),
    "枚": dict(suffix="まい"),
    "本": dict(zero=None, exact={1000: "せんぼん"}, suffix="ほん", tsu=("ぽん", (1, 6, 8, 10)), ren=(3, "ぼん")),
    "冊": dict(suffix="さつ", tsu=("さつ", (1, 8, 10)), exact={100: "ひゃくさつ"}),
    "台": dict(suffix="だい"),
    "杯": dict(zero=None, exact={1000: "せんばい"}, suffix="はい", tsu=("ぱい", (1, 6, 8, 10)), ren=(3, "ばい")),
    "匹": dict(zero=None, exact={1000: "せんびき"}, suffix="ひき", tsu=("ぴき", (1, 6, 8, 10)), ren=(3, "びき")),
    "軒": dict(zero=None, exact={1000: "せんげん"}, suffix="けん", tsu=("けん", (1, 6, 8, 10)), ren=(3, "げん")),
    "個": dict(suffix="こ", tsu=("こ", (1, 6, 8, 10))),
    "番": dict(suffix="ばん"),
    "円": dict(suffix="えん", exact={4: "よえん"}),
    "週間": dict(suffix="しゅうかん", tsu=("しゅうかん", (1, 8, 10))),
    "か月": dict(suffix="かげつ", tsu=("かげつ", (1, 6, 8, 10))),
    "ヶ月": dict(suffix="かげつ", tsu=("かげつ", (1, 6, 8, 10))),
    "ヵ月": dict(suffix="かげつ", tsu=("かげつ", (1, 6, 8, 10))),
    "つ": dict(exact={1: "ひとつ", 2: "ふたつ", 3: "みっつ", 4: "よっつ", 5: "いつつ",
                     6: "むっつ", 7: "ななつ", 8: "やっつ", 9: "ここのつ", 10: "とお"}),
}

_NAN = {"時": "なんじ", "分": "なんぷん", "時間": "なんじかん", "月": "なんがつ", "日": "なんにち",
        "年": "なんねん", "回": "なんかい", "度": "なんど", "人": "なんにん", "歳": "なんさい",
        "階": "なんがい", "枚": "なんまい", "本": "なんぼん", "冊": "なんさつ", "台": "なんだい",
        "杯": "なんばい", "匹": "なんびき", "軒": "なんげん", "個": "なんこ", "番": "なんばん",
        "円": "なんえん", "週間": "なんしゅうかん", "か月": "なんかげつ", "ヶ月": "なんかげつ",
        "ヵ月": "なんかげつ", "つ": None}


def _int_to_kana(n: int) -> str:
    if n == 0:
        return "ぜろ"
    if not 0 < n <= 9999:
        raise ValueError(n)
    out = []
    for unit in (1000, 100, 10):
        digit = n // unit
        if not digit:
            continue
        n %= unit
        if unit == 1000:
            out.append({1: "せん", 3: "さんぜん", 8: "はっせん"}.get(digit, _NUM_KANA[digit] + "せん"))
        elif unit == 100:
            out.append({1: "ひゃく", 3: "さんびゃく", 6: "ろっぴゃく",
                        8: "はっぴゃく"}.get(digit, _NUM_KANA[digit] + "ひゃく"))
        else:
            out.append(("じゅう" if digit == 1 else _NUM_KANA[digit] + "じゅう"))
    if n:
        out.append(_NUM_KANA[n])
    return "".join(out)


def _parse_num(raw: str):
    """アラビア数字 / 全角 / 漢数字 → int；解析不了返回 None。"""
    raw = "".join(_FW_DIGIT.get(c, c) for c in raw)
    if raw.isdigit():
        return int(raw)
    total, section, digit = 0, 0, 0
    for ch in raw:
        if ch in _KANJI_NUM:
            # 连续个位数字按十进制累加：二〇二四 → 2024
            digit = digit * 10 + _KANJI_NUM[ch] if digit else _KANJI_NUM[ch]
        elif ch == "十":
            section += (digit or 1) * 10
            digit = 0
        elif ch == "百":
            section += (digit or 1) * 100
            digit = 0
        elif ch == "千":
            section += (digit or 1) * 1000
            digit = 0
        elif ch == "万":
            total += (section + digit or 1) * 10000
            section, digit = 0, 0
        else:
            return None
    return total + section + digit


def _tsu(base: str):
    """把读末尾的一拍换成促音便：いち→いっ、さんじゅう→さんじゅっ。"""
    for tail, tense in _TSU.items():
        if base.endswith(tail):
            return base[:-len(tail)] + tense
    return None


def counter_kana(num_raw: str, unit: str):
    """「七時」「２０歳」「三十分」「四つ」→ 假名；0-9999 以外的数不猜，返回 None。"""
    if num_raw == "何":
        return _NAN.get(unit)
    cfg = _COUNTERS.get(unit)
    if not cfg:
        return None
    n = _parse_num(num_raw)
    if n is None or not 0 <= n <= 9999:
        return None
    if n in cfg.get("exact", {}):
        return cfg["exact"][n]
    if n == 0:
        return cfg.get("zero", "ぜろ" + cfg.get("suffix", ""))
    if cfg.get("suffix") is None:
        return None
    base = _int_to_kana(n)
    tsu = cfg.get("tsu")
    # 促音便看**末位**：1/6/8 以及整十（じゅう→じゅっ，さんじゅっぷん）
    if tsu and ((n % 10 in tsu[1]) or (n % 10 == 0 and base.endswith("じゅう"))):
        head = _tsu(base)
        if head is not None:
            return head + tsu[0]
    if tsu and unit == "分" and base.endswith("ん"):
        return base + "ぷん"
    ren = cfg.get("ren")
    if ren and base.endswith(_NUM_KANA[ren[0]]):
        return base[:-len(_NUM_KANA[ren[0]])] + _NUM_KANA[ren[0]] + ren[1]
    return base + cfg["suffix"]


def number_reading(text: str, i: int):
    """从 text[i] 起匹配「数词+量词」，返回 (surface, kana)；匹配不到返回 None。

    命中但停在汉字串中间（一日中 的 一日）时返回 ``("", "")``，调用方据此判定「这一段读不出来」，
    不能从下一个字符继续匹配 —— 否则会从汉字串中间啃出 日中＝にっちゅう 这种错读音。
    """
    m = _COUNTER_RE.match(text, i)
    if not m:
        return None
    num, unit = m.group("num"), m.group("unit")
    kana = counter_kana(num, unit)
    if not kana:
        return None
    end = m.end()
    if end < len(text) and _is_kanji(text[end - 1]) and _is_kanji(text[end]):
        return "", ""
    # 1日 只有在「X月1日」这种日期里读 ついたち，其余（1日おき/1日で）读 いちにち
    if unit == "日" and num in ("1", "１", "一"):
        kana = "ついたち" if i > 0 and text[i - 1] == "月" else "いちにち"
    return text[i:end], kana


# ---------------------------------------------------------------------------
# 整句读音解析
# ---------------------------------------------------------------------------
# 助词读音：独立成拍的 は/へ/を 才换读音（は→わ、へ→え、を→お）
PARTICLE_READING = {"は": "わ", "へ": "え", "を": "お"}
# 前面是这些假名时，后面的「は/へ」按助词读（ては/では/には/とは/のは/へ 后）
PARTICLE_PREV = set("てでにとへの")
# 固定说法：词表里是整体词，但末拍 は 实际读 わ（键是**假名**，按段精确替换，不做全局 replace）
FIXED_READING = {"こんにちは": "こんにちわ", "こんばんは": "こんばんわ",
                 "では": "でわ", "それでは": "それでわ", "または": "またわ",
                 "あるいは": "あるいわ", "じつは": "じつわ", "はじめて": "はじめて"}
# 不规则动词不给词干（来る→来(き) 不是 来(く)，する→し）
STEM_BLOCK = {"来る", "來る", "する", "為る"}
_PUNCT = "、。！？，．「」『』（）()!?,. 　"


class ReadingIndex:
    """用词汇种子 (surface, kana) + 数词规则 + 补充词表，把日语句子还原成假名读音。

    解析不出来（有汉字没被任何一层覆盖）就返回 None —— 页面宁可不显示韩语读音，
    也不显示一条可能错的读音。
    """

    def __init__(self, vocab_rows, extra_rows=()):
        pairs: dict[str, str] = {}
        explicit: set[str] = set()
        # 补充词表优先：它只收人工核对过的专名/复合词/活用形
        for row in extra_rows:
            surface = (row.get("surface") or "").strip()
            kana = (row.get("kana") or "").strip()
            if surface and kana:
                pairs.setdefault(surface, kana)
                explicit.add(surface)
        # 词干先收集再过滤：同一个词干有多种读音就整个不用（着(き)/着(つ)、出(で)/出(だ)），
        # 取第一条会读出 着いた→きいた 这种错音。
        stems: dict[str, set] = {}
        for row in vocab_rows:
            surface = (row.get("surface") or "").strip()
            kana = (row.get("kana") or "").strip()
            if not surface or not kana:
                continue
            pairs.setdefault(surface, kana)
            if (surface in STEM_BLOCK or len(surface) < 2 or len(kana) < 2
                    or not _is_kana(surface[-1])
                    or not any(_is_kanji(c) for c in surface[:-1])):
                continue
            stems.setdefault(surface[:-1], set()).add(kana[:-1])
        for stem, readings in stems.items():
            if len(readings) == 1 and stem not in pairs:
                pairs[stem] = next(iter(readings))
        self.pairs = sorted(pairs.items(), key=lambda kv: (-len(kv[0]), kv[0]))
        self.explicit = explicit
        self._by_first: dict[str, list] = {}
        for surface, kana in self.pairs:
            self._by_first.setdefault(surface[0], []).append((surface, kana))

    def _candidates(self, text: str, i: int):
        return self._by_first.get(text[i], ())

    def _any_word_at(self, text: str, j: int) -> bool:
        """text[j] 起是否能起一个词（含汉字边界检查），用于判断「は」是不是助词。"""
        if j >= len(text):
            return False
        for surface, _ in self._candidates(text, j):
            if not text.startswith(surface, j):
                continue
            end = j + len(surface)
            if (_is_kanji(surface[-1]) and end < len(text) and _is_kanji(text[end])
                    and surface not in self.explicit):
                continue
            return True
        return False

    def _match(self, text: str, i: int):
        for surface, kana in self._candidates(text, i):
            if not text.startswith(surface, i):
                continue
            # 「は」开头的词（はい/はあ）在句中会让位给助词，但只在「は」后面还能起一个词时成立：
            # これはいくら → これ+は+いくら；はず/はさみ/はっきり 后面起不了词，照常匹配。
            if (i > 0 and surface[0] == "は" and text[i - 1] not in _PUNCT
                    and self._any_word_at(text, i + 1)):
                continue
            end = i + len(surface)
            # 不许停在汉字串中间：東京 未入词表时不能退化成 東(ひがし)+京
            # （补充词表里人工核对过的条目不受这条限制，例如 一日中/二日間）
            if (_is_kanji(surface[-1]) and end < len(text) and _is_kanji(text[end])
                    and surface not in self.explicit):
                continue
            return surface, kana
        hit = number_reading(text, i)
        if hit is not None:
            return hit
        return None

    def reading(self, text: str):
        """整句假名读音；有汉字解析不出来时返回 None。

        顺带按词边界修正助词读音：独立成拍的「は/へ」读 わ/え（わたしは→わたしわ、
        がっこうへ→がっこうえ）。词内部的 は/へ 不受影响（おはよう 的 は 前面是「お」，
        不在 PARTICLE_PREV 里，不会被误改）。
        """
        text = str(text or "")
        segments: list[list] = []
        i, n = 0, len(text)
        while i < n:
            hit = self._match(text, i)
            if hit == ("", ""):      # 数词命中但停在汉字串中间 → 整句判失败
                return None
            if hit:
                segments.append([hit[1], True])
                i += len(hit[0])
                continue
            ch = text[i]
            if _is_kanji(ch):
                return None
            segments.append([ch, False])
            i += 1
        for idx, seg in enumerate(segments):
            if seg[1] or len(seg[0]) != 1 or seg[0] not in PARTICLE_READING:
                continue
            prev, back = None, idx - 1
            while back >= 0:  # 跳过空格，看真正的上一个音节
                if segments[back][0].strip():
                    prev = segments[back]
                    break
                back -= 1
            if not prev:
                continue
            kana_run = False
            if not prev[1] and len(prev[0]) == 1 and KANA_RE.match(prev[0]):
                # 前面是连着的散假名（例：へや 这种用假名写的词）也算词，才敢把 は 改读 わ
                kana_run = back > 0 and bool(KANA_RE.match(segments[back - 1][0][-1:]))
            if seg[0] == "は":
                ok = (prev[1] or kana_run
                      or (len(prev[0]) == 1 and (prev[0] in PARTICLE_PREV
                                                 or (prev[0].isascii() and prev[0].isalnum()))))
            else:  # へ/を：只在前一个词已识别时才改读，避免 へや→えや
                ok = prev[1]
            if ok:
                seg[0] = PARTICLE_READING[seg[0]]
        # 固定说法按段精确替换，不做整串 replace（否则「ので＋話す」会被改成「のでわなし」）
        kana = "".join(FIXED_READING.get(seg[0], seg[0]) for seg in segments)
        return kana

    def hangul(self, text: str) -> str:
        """整句韩语读音；解析失败返回空串。"""
        kana = self.reading(text)
        return to_hangul(kana) if kana else ""
