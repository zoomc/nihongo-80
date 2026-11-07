"""原创周测/阶段练习；返回私有题目，调用方负责公开投影。"""
import hashlib
import json
import random
from pathlib import Path

from quiz_v5 import fnv

SEED_PATH = Path(__file__).resolve().parent.parent / "knowledge/seeds/assessments.jsonl"


def build_for_day(day):
    """Return deterministic private MCQs for a day number or curriculum day dict.

    Empty knowledge_ids deliberately records comprehension evidence without updating
    knowledge-card mastery. This short practice is not a JLPT score or mock exam.
    """
    number = day["day"] if isinstance(day, dict) else day
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 150:
        raise ValueError("day must be an integer from 1 to 150")
    questions = []
    with SEED_PATH.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if item["day"] != number:
                continue
            # Include all answer-relevant content in the id so changed material
            # cannot be silently mistaken for an old registered question.
            payload = [item["passage"], item["prompt"], item["options"],
                       item["answer"], item["targets"], item["assessment"]]
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False,
                                               separators=(",", ":")).encode()).hexdigest()[:12]
            qid = f'{item["id"]}-{digest}'
            options = item["options"][:]
            random.Random(qid).shuffle(options)
            questions.append({
                "qid": qid, "id": qid, "type": "mcq", "passage": item["passage"],
                "prompt": item["prompt"], "options": options, "answer": item["answer"],
                "knowledge_ids": [], "targets": item["targets"][:],
                "assessment": item["assessment"], "review_status": "ai_draft",
                "rationale": "参考答案：" + item["answer"],
                "h": fnv(item["answer"]), "oh": [fnv(o) for o in options],
            })
    return questions
