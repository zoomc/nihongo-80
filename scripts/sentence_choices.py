"""Turn the existing bilingual sentence seeds into deterministic comprehension MCQs."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
import re
from quiz_v5 import fnv
from curriculum_v5 import source_day

ROOT = Path(__file__).resolve().parents[1]

@lru_cache(maxsize=4096)
def chinese_key(text):
    text = re.sub(r'[\s，。！？、,.!?「」“”\"：:；;（）()]', '', text)
    for a,b in [('早餐','早饭'),('晚餐','晚饭'),('午餐','午饭'),('您','你'),('一名','一个')]:
        text = text.replace(a,b)
    return text

def build_for_day(day, rows=None):
    number = day['day'] if isinstance(day,dict) else day
    if rows is None:
        rows = [json.loads(l) for l in (ROOT/'knowledge/seeds/sentences.jsonl').read_text().splitlines() if l.strip()]
    result=[]
    for index,s in enumerate(x for x in rows if source_day(x['day']) == number):
        zh = s['prompt'] if s['direction']=='zh-ja' else s['answer']
        candidates=[]
        for other in rows:
            if other['direction']!=s['direction'] or other['answer']==s['answer']:
                continue
            other_zh=other['prompt'] if other['direction']=='zh-ja' else other['answer']
            if chinese_key(other_zh)==chinese_key(zh):
                continue
            candidates.append(other['answer'])
        # Similar length keeps the correct answer from standing out; all alternatives
        # are complete sentences from the course, not deliberately broken Japanese.
        candidates=sorted(set(candidates),key=lambda a:(abs(len(a)-len(s['answer'])),a))[:80]
        rng=random.Random('sentence-'+s['id']);rng.shuffle(candidates)
        wrong=[]
        for a in candidates:
            if fnv(a)!=fnv(s['answer']) and fnv(a) not in {fnv(x) for x in wrong}:
                wrong.append(a)
            if len(wrong)==3:break
        if len(wrong)!=3:raise ValueError('not enough sentence alternatives: '+s['id'])
        options=[s['answer']]+wrong;rng.shuffle(options)
        digest=hashlib.sha256(json.dumps([s['prompt'],options,s['answer']],ensure_ascii=False).encode()).hexdigest()[:12]
        qid='P-%03d-%02d-%s'%(number,index,digest)
        result.append({'qid':qid,'id':qid,'source_id':s['id'],'type':'mcq','prompt':s['prompt'],
                       'direction':s['direction'],'options':options,'answer':s['answer'],
                       'knowledge_ids':[],'evidence_only':True,'optional':index>=3,
                       'h':fnv(s['answer']),'oh':[fnv(x) for x in options]})
    return result
