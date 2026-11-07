"""Regression: legitimate Japanese forms must not be taught as errors."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class GrammarErrorExamples(unittest.TestCase):
    def test_context_dependent_forms_not_labeled_wrong(self):
        entries = {x['id']: x for x in map(json.loads, (ROOT / 'knowledge/seeds/grammar.jsonl').read_text().splitlines())}
        allowed = {'G0080': 'これさえあるなら', 'G0178': '何時からっけ', 'G0197': '地図をはってあります'}
        for gid, expression in allowed.items():
            with self.subTest(grammar=gid):
                self.assertFalse(any(expression in x['wrong'] for x in entries[gid]['common_errors']))

if __name__ == '__main__':
    unittest.main()
