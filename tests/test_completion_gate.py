"""Regression: six MCQs alone must not finish a speaking/output lesson."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import nh80
import cloud_sync


class CompletionGate(unittest.TestCase):
    def test_objective_answers_without_output_stay_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'data').mkdir(); (root / 'curriculum').mkdir()
            (root / 'knowledge').symlink_to(ROOT / 'knowledge')
            shutil.copy(ROOT / 'curriculum/curriculum.json', root / 'curriculum/curriculum.json')
            src = sqlite3.connect(ROOT / 'data/state.db'); dst = sqlite3.connect(root / 'data/state.db')
            src.backup(dst); src.close(); dst.close()
            key = json.loads((ROOT / 'deploy/worker/src/generated-key.json').read_text())['answers']
            payload = {'v': 1, 'day': 149, 'session': 'objective-only-gate', 'ts': '2026-11-07T00:00:00Z',
                       'results': [{'qid': q, 'answer': x['answer']} for q, x in key.items() if x['day'] == 149],
                       'minutes': None, 'source': 'test'}
            with contextlib.redirect_stdout(io.StringIO()):
                nh80.cmd_import_web(argparse.Namespace(root=str(root), code=cloud_sync.encode_payload(payload)))
            with contextlib.redirect_stdout(io.StringIO()) as result:
                nh80.cmd_finish_day(argparse.Namespace(root=str(root), day=149, minutes=60))
            self.assertFalse(json.loads(result.getvalue())['passed'])
