#!/usr/bin/env python3
"""Fail closed before publishing the personal free-tier build."""
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
    for p in (ROOT/'web/data').glob('day-*.json'):
        d=json.loads(p.read_text())
        if any('answer' in q or 'rationale' in q for q in d['quiz']) or any(any(k.startswith('answer') for k in s) for s in d['sentences']):
            raise ValueError('public reference answer: '+p.name)
        core=d['core_vocab_ids'];extra=d['extension_vocab_ids']
        if len(core)>(11 if d['listening'] else 16) or set(core)&set(extra) or len(core)+len(extra)!=len(d['vocab']):
            raise ValueError('daily workload split broken')
    print(json.dumps({'ok':True,'files':len(files),'asset_bytes':sum(p.stat().st_size for p in files),'public_audio':45,'cloud_bindings':['existing D1'],'paid_features':False}))

if __name__=='__main__':check()
