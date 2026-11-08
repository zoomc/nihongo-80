"""Regression: inflected forms in today's examples must remain highlightable."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lesson_emphasis import terms_for_day, emphasize

class ExampleEmphasis(unittest.TestCase):
    def test_te_kureru_polite_past_is_highlighted(self):
        day={'new_vocab_ids':[], 'new_grammar_ids':['G'], 'new_kanji_ids':[]}
        terms=terms_for_day(day,{}, {'G':{'pattern':'〜てくれる'}}, {})
        self.assertIn('<strong class="today-focus">てくれました</strong>', emphasize('友達が手伝ってくれました。', terms))
