"""Regression: late cloud self-ratings must not backdate an FSRS card."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import core
import learning
import study_sync


class LateRatingTest(unittest.TestCase):
    def test_late_rating_uses_import_time_and_keeps_server_time_in_audit(self):
        now = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
        server_time = '2026-11-05T12:00:00Z'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            core.init_db(root)
            conn = core.connect(root)
            with conn:
                conn.execute("INSERT INTO vocabulary(id,raw) VALUES('V0001','{}')")
                learning.apply_review_rating(conn, kid='V0001', label='good', day=1,
                                             session_id='first', at=now - timedelta(days=5))
                learning.apply_review_rating(conn, kid='V0001', label='good', day=1,
                                             session_id='newer', at=now - timedelta(days=1))
            before = conn.execute("SELECT last_review FROM fsrs_cards WHERE knowledge_id='V0001|meaning'").fetchone()[0]
            conn.close()

            def response(base, key, path, body=None):
                if path.startswith('/api/reviews?'):
                    return [{'id': 1, 'event_id': 'late-rating', 'kid': 'V0001',
                             'day': 1, 'rating': 'again', 'created_at': server_time}]
                if path.startswith('/api/events?'):
                    return []
                return {'ok': True}

            with patch.object(study_sync, '_request', side_effect=response), patch.object(learning, 'now_utc', return_value=now):
                study_sync.run(root, 'https://example.test', 'not-a-real-key')
            conn = core.connect(root)
            try:
                after = conn.execute("SELECT last_review FROM fsrs_cards WHERE knowledge_id='V0001|meaning'").fetchone()[0]
                self.assertGreaterEqual(after, before)
                self.assertEqual(datetime.fromisoformat(after), now)
                records = [json.loads(row[0]) for row in conn.execute("SELECT detail FROM audit_log WHERE action='study_sync_rating'")]
                self.assertEqual(records[0]['server_created_at'], server_time)
            finally:
                conn.close()


if __name__ == '__main__':
    unittest.main()
