#!/usr/bin/env python3
"""Fail closed before publishing the personal free-tier build."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def check():
    config = (ROOT / 'deploy/wrangler.jsonc').read_text()
    for forbidden in ('r2_buckets', 'kv_namespaces', 'ai', 'vectorize', 'queues', 'durable_objects', 'logpush', 'triggers'):
        if re.search(r'"'+forbidden+r'"\s*:', config):
            raise ValueError('unexpected cloud binding: '+forbidden)
    if '"enabled": true' in config:
        raise ValueError('logs must stay off to avoid paid usage')
    if '"/*"' in config:
        raise ValueError('every static request must not be forced through the Worker')
    files = [p for p in (ROOT/'web').rglob('*') if p.is_file()]
    if len(files) >= 20000 or any(p.stat().st_size > 25*1024*1024 for p in files):
        raise ValueError('static free tier file limits exceeded')
    if any(p.suffix in ('.db','.sqlite','.key','.wav','.aiff','.pt','.pth') or p.name.startswith('.sync') for p in files):
        raise ValueError('private/runtime/model asset in public output')
    if config.count('"run_worker_first": ["/", "/api/*", "/health"]') != 2:
        raise ValueError('root must be forwarded for html_handling=none (prod+preview)')
    db_ids = re.findall(r'"database_id"\s*:\s*"([0-9a-f-]+)"', config)
    if len(db_ids) != 2 or len(set(db_ids)) != 2:
        raise ValueError('prod and preview must use two separate free-tier D1 databases')
    if '"database_name": "nihongo80-preview"' not in config:
        raise ValueError('preview must not share the production D1')
    if not (ROOT/'web/audio/NOTICE.txt').is_file():
        raise ValueError('audio attribution notice missing')
    manifest = json.loads((ROOT/'web/audio/manifest.json').read_text())
    if manifest.get('generator') != 'Kokoro-82M v1.0 + UniDic' or len(manifest['items']) != 45:
        raise ValueError('unapproved or incomplete synthetic audio')
    materials = {x['id']: x for x in map(json.loads,(ROOT/'knowledge/seeds/materials.jsonl').read_text().splitlines())}
    for mid,item in manifest['items'].items():
        path=ROOT/'web'/item['url'].lstrip('/')
        if item['text_sha256'] != hashlib.sha256(materials[mid]['audio_text'].encode()).hexdigest() or not path.is_file() or path.stat().st_size!=item['bytes'] or not 60 <= item['duration_sec'] <= 90:
            raise ValueError('invalid audio or changed script: '+mid)
    for name in ('vocabulary','grammar','kanji'):
        rows=list(map(json.loads,(ROOT/'knowledge/seeds'/(name+'.jsonl')).read_text().splitlines()))
        if name=='vocabulary' and any(not x.get('ko_hint') for x in rows):
            raise ValueError('incomplete Korean hints')
    from curriculum_v5 import DAYS, DAILY_VOCAB
    from daily_questions import compact
    from quiz_v5 import fnv
    for day in range(1, DAYS + 1):
        p = ROOT / f"web/data/day-{day:03d}.json"
        d = json.loads(p.read_text())
        daily = d['questions']
        public_questions = (d['quiz'] + d['sentences'] + d.get('practice', [])
                            + d.get('unit_questions', [])
                            + (d.get('listening_material') or {}).get('questions', []) + daily)
        if any('answer' in q or 'rationale' in q for q in public_questions):
            raise ValueError('public reference answer: ' + p.name)
        expected = {**{v['id']: 2 for v in d['vocab']}, **{g['id']: 3 for g in d['grammar']}}
        if Counter(k for q in daily for k in q['knowledge_ids']) != expected:
            raise ValueError('daily question quotas: ' + p.name)
        if len({q['qid'] for q in daily}) != len(daily) or len(daily) > 62:
            raise ValueError('invalid question count or duplicate ID: ' + p.name)
        for q in daily:
            hashes = [fnv(o) for o in q['options']]
            if len(q['knowledge_ids']) != 1 or len(hashes) != 4 or len(set(hashes)) != 4 or hashes != q['oh'] or q['h'] not in hashes:
                raise ValueError('invalid daily question: ' + q['qid'])
            answer = q['options'][hashes.index(q['h'])]
            if not answer or compact(answer) in compact(q['prompt'] + q.get('passage', '')):
                raise ValueError('answer visible in prompt: ' + q['qid'])
        core=d['core_vocab_ids'];extra=d['extension_vocab_ids']
        if len(core) != (14 if day == 1 else DAILY_VOCAB) or extra or len(core) != len(d['vocab']) or d['listening']:
            raise ValueError('daily workload split broken')
    shards=list((ROOT/'web/data/grade').glob('day-*.json'))
    if len(shards)!=DAYS or any('answer' in q or not re.fullmatch('[a-f0-9]{64}',q.get('answer_hash','')) for p in shards for q in json.loads(p.read_text())['answers'].values()):
        raise ValueError('grading shards incomplete or contain plaintext answers')
    if 'generated-key.json' in (ROOT/'deploy/worker/src/index.ts').read_text():
        raise ValueError('private full bank must not be bundled into Worker')
    print(json.dumps({'ok':True,'files':len(files),'asset_bytes':sum(p.stat().st_size for p in files),'public_audio':45,'cloud_bindings':['D1 prod','D1 preview (isolated)'],'paid_features':False}))

if __name__=='__main__':check()
