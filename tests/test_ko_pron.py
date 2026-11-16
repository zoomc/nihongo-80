"""v12 回归：韩语读音标注（한글 표음）+ 新词区去重复 + 逐项临时全显。

锁住 2026-11-12 的改动：
- 假名→한글 逐拍转写：促音紧音（っ＋つ 用 ㅉ）、拨音同化、长音按基础元音；
- 数词＋量词（時/分/時間/月/日/年/人/歳/円/回/週間/階/本/冊/軒/個/つ…）单独走规则；
- 整句读音只在能完整解析时输出；助词 は/へ 按词边界改读 わ/え；
- 页面版式：平假 → 单词 → 韩语发音 → 中文 → 例句韩语读音 → 例句 → 朗读；
- 所有韩语元素 data-role="zh"；每项一个「显示」按钮（10 秒临时全显）。
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))

import ko_pron  # noqa: E402


def seeds(name):
    return [json.loads(x) for x in (ROOT / "knowledge/seeds" / name).read_text(encoding="utf-8").splitlines()
            if x.strip()]


def page(day):
    return (ROOT / ("web/day-%03d.html" % day)).read_text(encoding="utf-8")


def data(day):
    return json.loads((ROOT / ("web/data/day-%03d.json" % day)).read_text(encoding="utf-8"))


def supplement():
    return json.loads((ROOT / "knowledge/ko_reading_supplement.json")
                      .read_text(encoding="utf-8"))["entries"]


def index():
    return ko_pron.ReadingIndex(seeds("vocabulary.jsonl"), supplement())


class TestTransliteration(unittest.TestCase):
    def test_kana_to_hangul_basics(self):
        cases = {
            "わたし": "와타시",
            "ありがとうございます": "아리가토우고자이마스",
            "がくせい": "가쿠세이",
            "ともだち": "토모다치",
            "パン": "판",
            "テレビ": "테레비",
        }
        for kana, hangul in cases.items():
            self.assertEqual(ko_pron.to_hangul(kana), hangul, kana)

    def test_sokuon_and_hatsuon(self):
        self.assertEqual(ko_pron.to_hangul("がっこう"), "가꼬우")   # っ → 된소리
        self.assertEqual(ko_pron.to_hangul("きって"), "키떼")
        self.assertEqual(ko_pron.to_hangul("よっつ"), "요쯔")       # っ＋つ → ㅉ
        self.assertEqual(ko_pron.to_hangul("まっすぐ"), "마쓰구")   # っ＋す 保持 ㅆ
        self.assertEqual(ko_pron.to_hangul("しんぶん"), "심분")     # ん＋ば行 → ㅁ
        self.assertEqual(ko_pron.to_hangul("でんしゃ"), "덴샤")

    def test_long_vowel_uses_base_vowel(self):
        self.assertEqual(ko_pron.to_hangul("コーヒー"), "코오히이")
        self.assertEqual(ko_pron.to_hangul("ニュース"), "뉴우스")     # 不是 뉴유스
        self.assertEqual(ko_pron.to_hangul("ショー"), "쇼오")         # 不是 쇼요
        self.assertEqual(ko_pron.to_hangul("スープ"), "스푸")         # ㅡ 不长音
        self.assertEqual(ko_pron.to_hangul("ケーキ"), "케이키")       # ㅔ＋ー → 이
        self.assertEqual(ko_pron.to_hangul("さぁ"), "사아")           # 小写元音假名

    def test_korean_punctuation(self):
        self.assertEqual(ko_pron.to_hangul("はい。そう、です。"), "하이.소우,데스.")

    def test_kanji_is_not_guessed(self):
        self.assertEqual(ko_pron.pron("学生"), "")
        self.assertTrue(ko_pron.kana_only("がくせい。"))


class TestCounters(unittest.TestCase):
    def test_time_and_minutes(self):
        self.assertEqual(ko_pron.counter_kana("三", "時"), "さんじ")
        self.assertEqual(ko_pron.counter_kana("七", "時"), "しちじ")
        self.assertEqual(ko_pron.counter_kana("九", "時"), "くじ")
        self.assertEqual(ko_pron.counter_kana("四", "時"), "よじ")
        self.assertEqual(ko_pron.counter_kana("零", "時"), "れいじ")
        self.assertEqual(ko_pron.counter_kana("何", "時"), "なんじ")
        self.assertEqual(ko_pron.counter_kana("二", "分"), "にふん")
        self.assertEqual(ko_pron.counter_kana("五", "分"), "ごふん")
        self.assertEqual(ko_pron.counter_kana("十", "分"), "じゅっぷん")
        self.assertEqual(ko_pron.counter_kana("三", "分"), "さんぷん")
        self.assertEqual(ko_pron.counter_kana("十五", "分"), "じゅうごふん")
        self.assertEqual(ko_pron.counter_kana("三十", "分"), "さんじゅっぷん")
        self.assertEqual(ko_pron.counter_kana("一", "時間"), "いちじかん")   # 時間 不促音便
        self.assertEqual(ko_pron.counter_kana("八", "時間"), "はちじかん")
        self.assertEqual(ko_pron.counter_kana("十", "時間"), "じゅうじかん")
        self.assertEqual(ko_pron.counter_kana("何", "時間"), "なんじかん")
        self.assertEqual(ko_pron.counter_kana("十四", "時"), "じゅうよじ")

    def test_dates_people_money(self):
        self.assertEqual(ko_pron.counter_kana("一", "月"), "いちがつ")
        self.assertEqual(ko_pron.counter_kana("二", "月"), "にがつ")
        self.assertEqual(ko_pron.counter_kana("九", "月"), "くがつ")
        self.assertEqual(ko_pron.counter_kana("二十", "日"), "はつか")
        self.assertEqual(ko_pron.counter_kana("十一", "日"), "じゅういちにち")
        self.assertEqual(ko_pron.counter_kana("一", "人"), "ひとり")
        self.assertEqual(ko_pron.counter_kana("十", "人"), "じゅうにん")
        self.assertEqual(ko_pron.counter_kana("二十", "歳"), "はたち")
        self.assertEqual(ko_pron.counter_kana("六", "歳"), "ろくさい")
        self.assertEqual(ko_pron.counter_kana("百", "円"), "ひゃくえん")
        self.assertEqual(ko_pron.counter_kana("四", "年"), "よねん")
        self.assertEqual(ko_pron.counter_kana("四", "円"), "よえん")
        self.assertEqual(ko_pron.counter_kana("七", "人"), "しちにん")
        self.assertEqual(ko_pron.counter_kana("十七", "日"), "じゅうしちにち")
        self.assertEqual(ko_pron.counter_kana("百", "冊"), "ひゃくさつ")

    def test_counters_with_sokuon_and_rendaku(self):
        self.assertEqual(ko_pron.counter_kana("一", "本"), "いっぽん")   # 不是 いっっぽん
        self.assertEqual(ko_pron.counter_kana("六", "本"), "ろっぽん")
        self.assertEqual(ko_pron.counter_kana("十", "本"), "じゅっぽん")
        self.assertEqual(ko_pron.counter_kana("三", "本"), "さんぼん")
        self.assertEqual(ko_pron.counter_kana("一", "杯"), "いっぱい")
        self.assertEqual(ko_pron.counter_kana("一", "個"), "いっこ")
        self.assertEqual(ko_pron.counter_kana("一", "冊"), "いっさつ")
        self.assertEqual(ko_pron.counter_kana("三", "軒"), "さんげん")
        self.assertEqual(ko_pron.counter_kana("三", "階"), "さんがい")
        self.assertEqual(ko_pron.counter_kana("何", "階"), "なんがい")
        self.assertEqual(ko_pron.counter_kana("一", "週間"), "いっしゅうかん")
        self.assertEqual(ko_pron.counter_kana("六", "週間"), "ろくしゅうかん")
        self.assertEqual(ko_pron.counter_kana("四", "つ"), "よっつ")
        self.assertEqual(ko_pron.counter_kana("千", "本"), "せんぼん")

    def test_out_of_range_is_not_guessed(self):
        self.assertIsNone(ko_pron.counter_kana("一万", "円"))
        self.assertEqual(ko_pron.number_reading("十分あります。", 0), ("十分", "じゅっぷん"))
        # 裸「1日」是时长（いちにち），「1月1日」才是日期（ついたち）
        self.assertEqual(ko_pron.number_reading("1日おきに", 0), ("1日", "いちにち"))
        self.assertEqual(ko_pron.number_reading("1月1日", 2), ("1日", "ついたち"))
        # 数词命中但停在汉字串中间 → 不让调用方从汉字中间继续啃
        self.assertEqual(ko_pron.number_reading("一日中", 0), ("", ""))


class TestSentenceReading(unittest.TestCase):
    def test_particle_reading(self):
        idx = index()
        self.assertEqual(idx.reading("私は学生です。"), "わたしわがくせいです。")
        self.assertEqual(idx.reading("これはいくらですか。"), "これわいくらですか。")
        self.assertEqual(idx.reading("こんにちは、元気ですか。"), "こんにちわ、げんきですか。")
        self.assertEqual(idx.reading("学校へ行きます。"), "がっこうえいきます。")
        self.assertEqual(idx.reading("今日はいい天気です。"), "きょうわいいてんきです。")

    def test_particle_inside_word_not_touched(self):
        idx = index()
        for ja, want in (("おはようございます。", "おはようございます。"),
                         ("来るはずです。", "くるはずです。"),
                         ("はさみを使います。", "はさみおつかいます。"),
                         ("はっきり言ってください。", "はっきりいってください。"),
                         ("もはや間に合わない。", "もはやまにあわない。")):
            self.assertEqual(idx.reading(ja), want, ja)

    def test_fixed_readings_and_compound_words(self):
        idx = index()
        cases = {
            "実はそうではありません。": "じつわそうでわありません。",
            "三時に会います。": "さんじにあいます。",
            "日本語を話します。": "にほんごおはなします。",
            "人々でいっぱいです。": "ひとびとでいっぱいです。",
            "お話し中です。": "おはなしちゅうです。",
            "１日中テニスをしました。": "いちにちじゅうテニスおしました。",
        }
        for ja, want in cases.items():
            self.assertEqual(idx.reading(ja), want, ja)

    def test_unknown_kanji_returns_none(self):
        idx = index()
        self.assertIsNone(idx.reading("薔薇が咲いた。"))
        self.assertEqual(idx.hangul("薔薇が咲いた。"), "")

    def test_ambiguous_stem_is_dropped_not_guessed(self):
        """着(き)/着(つ)、出(で)/出(だ) 这类同形异读不给单字词干（否则 着いた→きいた）。"""
        idx = index()
        surfaces = {p[0] for p in idx.pairs}
        self.assertNotIn("着", surfaces)
        self.assertNotIn("出", surfaces)
        self.assertEqual(idx.reading("シカゴに着いたら電話します。"), "シカゴについたらでんわします。")

    def test_sample_sentences_resolve(self):
        idx = index()
        for ja in ("田中さんは先生です。", "七時に起きます。", "百円です。", "東京へ行きます。",
                   "何をしますか。", "教えて下さい。", "二時間かかります。", "一日中ひまです。"):
            self.assertIsNotNone(idx.reading(ja), ja)

    def test_rendered_example_coverage_floor(self):
        """例句韩语读音的解析率地板（解析不了就整句不标，不猜）。"""
        idx = index()
        cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
        vocab = {x["id"]: x for x in seeds("vocabulary.jsonl")}
        grammar = {x["id"]: x for x in seeds("grammar.jsonl")}
        stat = {"n5": [0, 0], "all": [0, 0]}
        for d in cur["days"]:
            examples = []
            for vid in d["new_vocab_ids"]:
                ex = (vocab[vid].get("examples") or [{}])[0]
                if ex.get("ja"):
                    examples.append(ex["ja"])
            for gid in d["new_grammar_ids"]:
                for ex in (grammar[gid].get("examples") or [])[:3]:
                    if ex.get("ja"):
                        examples.append(ex["ja"])
            for ja in examples:
                ok = idx.reading(ja) is not None
                stat["all"][0] += ok
                stat["all"][1] += 1
                if d["day"] <= 24:
                    stat["n5"][0] += ok
                    stat["n5"][1] += 1
        self.assertGreaterEqual(stat["n5"][0] / stat["n5"][1], 0.92, stat["n5"])
        self.assertGreaterEqual(stat["all"][0] / stat["all"][1], 0.76, stat["all"])


class TestPageLayout(unittest.TestCase):
    def test_vocab_section_is_gone(self):
        """日课页不再有独立的新词区。"""
        h = page(47)
        self.assertNotIn('id="vocab"', h)
        self.assertNotIn("今日新词", h)
        self.assertNotIn("vocab-pair", h)

    def test_word_cards_are_gone(self):
        h = page(1)
        self.assertNotIn('<div class="item">', h)
        self.assertNotIn("あなた", h)

    def test_vocabulary_pages_are_gone(self):
        for day in (1, 47, 99, 100):
            self.assertNotIn("选学", page(day))
        self.assertFalse((ROOT / "web/optional-vocab.html").exists())
        self.assertFalse((ROOT / "web/flashcards.html").exists())

    def test_korean_readings_are_masked_with_japanese(self):
        """韩语发音是日语侧的读音提示：遮日语时必须一起遮，否则等于泄题。"""
        for day in (1, 47, 99, 100):
            h = page(day)
            seen = 0
            for cls in ('class="ko-read"', 'class="ex-ko"', 'class="small ko-read"'):
                for m in re.finditer(re.escape(cls), h):
                    seen += 1
                    tail = h[m.start():m.start() + 120]
                    self.assertIn('data-role="ja"', tail, "Day %d %s 未随日语遮蔽" % (day, cls))
            self.assertGreater(seen, 0, "Day %d 完全没有韩语读音行" % day)

    def test_korean_grammar_equivalence_stays_with_chinese(self):
        """语法区的「韩语对应」是中文侧解释，遮日语时仍保留。"""
        h = page(1)
        found = 0
        for m in re.finditer(re.escape('class="grammar-transfer ko-box"'), h):
            found += 1
            tail = h[m.start():m.start() + 120]
            self.assertIn('data-role="zh"', tail)
        self.assertGreater(found, 0, "Day 1 缺少韩语对应框")

    def test_grammar_korean_reading_stays_on_日语_side(self):
        for day in (1, 47):
            h = page(day)
            grammar = h[h.index('id="grammar"'):h.index('id="questions"')]
            self.assertIn('class="ko-read" data-role="ja"', grammar)
            self.assertNotIn('class="ko-read" data-role="zh"', grammar)

    def test_daily_examples_have_korean_reading_and_speak_button(self):
        h = page(47)
        self.assertGreater(h.count('class="ex-ko"'), 3)
        self.assertIn('data-speak=', h, "例句缺设备朗读按钮")
        self.assertNotIn('<audio', h, "不应打包音频文件")

    def test_grammar_cards_get_korean_reading(self):
        grammar_html = []
        for day in range(1, 151):
            h = page(day)
            grammar_html.append(h[h.index('id="grammar"'):h.index('id="questions"')])
        grammar = "".join(grammar_html)
        for reading in ("〜카타", "〜추우／주우", "〜와", "〜에"):
            self.assertIn(reading, grammar)

    def test_data_export_carries_korean_reading(self):
        d = data(1)
        self.assertTrue(all(g.get("ko_pron") for g in d["grammar"]), "语法卡缺 ko_pron")
        self.assertNotIn("vocab", d, "导出不该再带词卡")
        self.assertNotIn("sentences", d)

    def test_no_japanese_punctuation_in_korean_lines(self):
        for day in (1, 47, 100):
            h = page(day)
            for m in re.finditer(r'<div class="ex-ko"[^>]*>([^<]*)</div>', h):
                self.assertNotRegex(m.group(1), "[。、？！]", "Day %d 韩语行带日文标点" % day)


class TestShowAll(unittest.TestCase):
    def test_every_item_has_one_show_all_button(self):
        for day in (1, 47, 100):
            h = page(day)
            grammar = h[h.index('id="grammar"'):h.index('id="questions"')]
            self.assertEqual(grammar.count("data-show-all"), grammar.count('<div class="gcard">'),
                             "Day %d 语法卡按钮数量不对" % day)

    def test_button_is_not_inside_masked_block(self):
        h = page(47)
        for m in re.finditer(r'<div class="(?:item|gcard)">(.*?)</div></div>', h, re.S):
            block = m.group(0)
            if "data-show-all" in block:
                # 按钮不能放进会被遮住的元素里
                self.assertTrue(block.split("data-show-all")[0].count("<div class=\"mask") == 0)

    def test_script_implements_ten_second_peek(self):
        js = (ROOT / "web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn("co-show", js)
        self.assertIn("data-show-all", js)
        self.assertIn("left=10", js.replace(" ", ""))
        self.assertIn("clearInterval", js)
        css = (ROOT / "web/assets/app.css").read_text(encoding="utf-8")
        self.assertIn(".item.co-show .mask", css)


class TestSupplement(unittest.TestCase):
    def test_supplement_entries_are_sane(self):
        payload = json.loads((ROOT / "knowledge/ko_reading_supplement.json").read_text(encoding="utf-8"))
        self.assertIn("review_status", payload["meta"])
        self.assertEqual(payload["meta"]["count"], len(payload["entries"]))
        seen = set()
        for row in payload["entries"]:
            self.assertTrue(row["surface"] and row["kana"], row)
            self.assertTrue(ko_pron.kana_only(row["kana"]), row)   # 读音必须是假名
            self.assertGreaterEqual(len(row["surface"]), 2, "单字词不进补充表：%s" % row)
            self.assertNotIn(row["surface"], seen, "补充表重复：%s" % row)
            seen.add(row["surface"])

    def test_supplement_does_not_conflict_with_seed_readings(self):
        vocab = {x["surface"]: x["kana"] for x in seeds("vocabulary.jsonl")}
        for row in supplement():
            if row["surface"] in vocab:
                self.assertEqual(vocab[row["surface"]], row["kana"],
                                 "补充表与词表读音冲突：%s" % row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
