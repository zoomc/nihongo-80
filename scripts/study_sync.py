#!/usr/bin/env python3
"""Private, CLI-invoked study synchronization; SQLite remains authoritative."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import cloud_sync
import core
import learning

PAGE = 500
MAX_EVENTS = 20000
MAX_PLAN = 128 * 1024


def _request(base, key, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
    request = Request(base.rstrip('/') + path, data=data, method='GET' if data is None else 'POST',
                      headers={'Accept': 'application/json', 'Content-Type': 'application/json', 'X-NH80-Key': key, 'User-Agent': 'nh80-study-sync/1'})
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('response too large')
        obj = json.loads(raw)
    except Exception as exc:
        # No server response body, URL, exception text, or credentials in messages.
        raise RuntimeError('study sync HTTP request failed (%s)' % type(exc).__name__) from None
    if isinstance(obj, dict) and obj.get('ok') is False:
        raise RuntimeError('study sync server rejected request')
    return obj


def _page_all(base, key, endpoint, since):
    result, cursor = [], since
    while True:
        obj = _request(base, key, '/api/%s?%s' % (endpoint, urlencode({'since': cursor, 'limit': PAGE})))
        rows = obj if isinstance(obj, list) else obj.get(endpoint) if isinstance(obj, dict) else None
        if not isinstance(rows, list) or len(rows) > PAGE:
            raise ValueError('invalid %s page' % endpoint)
        for row in rows:
            if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] <= cursor:
                raise ValueError('invalid or unordered %s id' % endpoint)
            cursor = row['id']
            result.append(row)
        if len(result) > MAX_EVENTS:
            raise ValueError('%s exceeds sync limit' % endpoint)
        if len(rows) < PAGE:
            break
        # At the limit query one more page to distinguish exactly 20k from truncation.
    return result, cursor


def _validate_event(row):
    if type(row.get('day')) is not int or not 1 <= row['day'] <= 150:
        raise ValueError('invalid event day')
    for field in ('session', 'qid', 'answer'):
        if not isinstance(row.get(field), str) or (field != 'answer' and not row[field]):
            raise ValueError('invalid event %s' % field)
    raw = row.get('session_payload')
    if raw:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(parsed, dict):
            raise ValueError('invalid session payload')
    ids = row.get('knowledge_ids')
    if ids is not None:
        parsed = json.loads(ids) if isinstance(ids, str) else ids
        if not isinstance(parsed, list) or any(not isinstance(x, str) for x in parsed):
            raise ValueError('invalid event knowledge_ids')


def _validate_rating(row):
    if not isinstance(row.get('event_id'), str) or not row['event_id'] or not isinstance(row.get('kid'), str) or not row['kid']:
        raise ValueError('invalid rating identity')
    if type(row.get('day')) is not int or not 1 <= row['day'] <= 150 or row.get('rating') not in ('again', 'hard', 'good'):
        raise ValueError('invalid rating')
    stamp = row.get('created_at')
    if not isinstance(stamp, str):
        raise ValueError('invalid rating timestamp')
    dt = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('rating timestamp requires timezone')
    return dt.astimezone(timezone.utc)


def _atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.study-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _context(conn):
    updated = core.iso()
    due = learning.due_queue(conn, limit=20000)
    recommendations = {}
    for item in due:
        key = item['card_key']
        recommendations[key] = {'kid': key, 'due': item['due'], 'stage': item['stage'],
                                'priority': 1, 'reasons': ['FSRS 已到期']}
    for row in conn.execute('SELECT knowledge_ids,error_type,remedy FROM mistakes ORDER BY id DESC LIMIT 500'):
        try:
            kids = json.loads(row['knowledge_ids'] or '[]')
        except (ValueError, TypeError):
            continue
        if not isinstance(kids, list):
            continue
        for kid in kids:
            if not isinstance(kid, str):
                continue
            item = recommendations.setdefault(kid, {'kid': kid, 'due': None, 'stage': None, 'priority': 2, 'reasons': []})
            reason = '曾答错：' + str(row['error_type'] or 'other')
            if reason not in item['reasons']:
                item['reasons'].append(reason)
    # Self-ratings are stored in the existing audit record; review_tasks alone does not contain the label.
    for row in conn.execute("SELECT detail FROM audit_log WHERE action='web_review_rating' ORDER BY id DESC LIMIT 1000"):
        try:
            obj = json.loads(row['detail'])
        except (TypeError, ValueError):
            continue
        if obj.get('label') not in ('again', 'hard') or not obj.get('kid'):
            continue
        kid = obj.get('card_key') or obj['kid']
        item = recommendations.setdefault(kid, {'kid': kid, 'due': obj.get('due'), 'stage': None, 'priority': 2, 'reasons': []})
        reason = '自评' + ('遗忘' if obj['label'] == 'again' else '不熟')
        if reason not in item['reasons']:
            item['reasons'].append(reason)
    for row in conn.execute("SELECT knowledge_id,reason,remedy,due FROM review_tasks WHERE status='pending' ORDER BY id DESC LIMIT 500"):
        kid = row['knowledge_id']
        item = recommendations.setdefault(kid, {'kid': kid, 'due': row['due'], 'stage': None, 'priority': 3, 'reasons': []})
        reason = '待处理复习任务：' + str(row['remedy'] or row['reason'] or '复习')
        if reason not in item['reasons']:
            item['reasons'].append(reason)
    items = sorted(recommendations.values(), key=lambda x: (x['priority'], x['due'] or '9999', x['kid']))[:500]
    return {'updated_at': updated, 'recommendations': items,
            'note': '自评只调整复习排期，不代表掌握；优先处理真实 FSRS 到期卡。'}


def _publish_plan(context):
    # Browser projection is keyed by base knowledge ID, while FSRS may have several capabilities.
    due, seen = [], set()
    for x in context['recommendations']:
        kid = x['kid'].split('|', 1)[0]
        if x['priority'] == 1 and kid not in seen and isinstance(x['stage'], str):
            due.append({'kid': kid, 'due': x['due'], 'stage': x['stage'], 'priority': x['priority']})
            seen.add(kid)
    focus = []
    for item in context['recommendations']:
        reasons=[r for r in item['reasons'] if '曾答错' in r or '自评' in r]
        if reasons:
            focus.append({'kid': item['kid'].split('|',1)[0], 'reasons': reasons, 'priority': item['priority']})
    plan = {'updated_at': context['updated_at'], 'due': due, 'focus':focus}
    while len(json.dumps({'plan': plan}, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_PLAN:
        if plan['focus']:
            plan['focus'].pop()
        elif due:
            due.pop()
        else:
            raise ValueError('study plan exceeds size limit')
    return plan


def run(root, base, key, push_only=False):
    """Run through nh80 CLI only. Publish errors are reported without rolling back local state."""
    import nh80
    root = Path(root).resolve()
    parts = urlsplit(base)
    if parts.scheme not in ('http', 'https') or not parts.netloc or parts.query or parts.fragment or parts.username or parts.password or not key:
        raise ValueError('invalid base or missing key')
    base = base.rstrip('/')
    digest = hashlib.sha256(base.encode()).hexdigest()
    keys = ['study_sync:%s:%s' % (digest, kind) for kind in ('events', 'reviews')]
    conn = core.connect(root)
    try:
        cursors = []
        for k in keys:
            row = conn.execute('SELECT value FROM meta WHERE key=?', (k,)).fetchone()
            cursor = int(row['value']) if row else 0
            if cursor < 0:
                raise ValueError('invalid stored cursor')
            cursors.append(cursor)
        events, ratings = [], []
        next_events, next_ratings = cursors
        if not push_only:
            events, next_events = _page_all(base, key, 'events', cursors[0])
            ratings, next_ratings = _page_all(base, key, 'reviews', cursors[1])
            for row in events:
                _validate_event(row)
            for row in ratings:
                _validate_rating(row)
            for (_, _), group in cloud_sync.group_events(events).items():
                for offset in range(0, len(group), 40):
                    payload = cloud_sync.build_payload(group[offset:offset + 40])
                    result = cloud_sync.import_session(root, payload, nh80)
                    if result.get('ok') is not True or result.get('review_ratings_rejected'):
                        raise ValueError('session import rejected')
            with conn:
                for row in ratings:
                    at = learning.now_utc()
                    kid, capability = learning.split_card_key(row['kid'])
                    card = conn.execute('SELECT last_review FROM fsrs_cards WHERE knowledge_id=?',
                                        (learning.card_key(kid, capability),)).fetchone()
                    if card and card['last_review']:
                        last = datetime.fromisoformat(card['last_review'].replace('Z', '+00:00'))
                        if last.tzinfo is None or last > at:
                            raise ValueError('FSRS last_review is later than import time or lacks timezone')
                    learning.apply_review_rating(conn, kid=row['kid'], label=row['rating'], day=row['day'],
                                                 session_id='rating-' + row['event_id'], at=at)
                    core.audit(conn, 'study_sync_rating', {'event_id': row['event_id'], 'kid': row['kid'],
                               'server_created_at': row['created_at'], 'imported_at': core.iso(at)})
                for k, value in zip(keys, (next_events, next_ratings)):
                    conn.execute('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)', (k, str(value)))
                core.audit(conn, 'study_sync_cursor', {'base_hash': digest, 'events': next_events, 'reviews': next_ratings})
        context = _context(conn)
    finally:
        conn.close()
    directory = root / 'data' / 'review'
    context_path, md_path = directory / 'context.json', directory / 'CONTEXT.md'
    _atomic(context_path, json.dumps(context, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 私人复习建议', '', '同步时间：' + context['updated_at'], '', context['note'], '']
    for item in context['recommendations']:
        lines.append('- %s：%s%s' % (item['kid'], '；'.join(item['reasons']), ('；到期 ' + item['due']) if item['due'] else ''))
    if not context['recommendations']:
        lines.append('- 当前没有本地复习建议。')
    _atomic(md_path, '\n'.join(lines) + '\n')
    plan = _publish_plan(context)
    published, error = False, None
    try:
        response = _request(base, key, '/api/study-plan', {'plan': plan})
        if not isinstance(response, dict) or response.get('ok') is not True:
            raise ValueError('invalid publish response')
        published = True
    except Exception as exc:
        error = type(exc).__name__ + ': publish failed'
    result = {'ok': True, 'events_pulled': len(events), 'ratings_pulled': len(ratings),
              'events_cursor': next_events, 'ratings_cursor': next_ratings, 'published': published,
              'context_path': str(context_path), 'context_md_path': str(md_path)}
    if error:
        result['publish_error'] = error
    return result
