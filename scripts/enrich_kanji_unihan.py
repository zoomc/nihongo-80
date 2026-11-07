#!/usr/bin/env python3
"""Regenerate character-level Korean references from official Unicode Unihan."""
import argparse
import collections
import json
import re
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'knowledge/seeds/kanji.jsonl'
FALLBACK = {'飲': '음', '歳': '세', '説': '설', '働': '동', '込': '未确认（和制字）'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--unihan-zip', type=Path, required=True)
    args = parser.parse_args()
    data = collections.defaultdict(dict)
    with zipfile.ZipFile(args.unihan_zip) as archive:
        for name in ('Unihan_Readings.txt', 'Unihan_Variants.txt'):
            for line in archive.read(name).decode('utf-8').splitlines():
                if not line or line.startswith('#'):
                    continue
                code, key, value = line.split('\t', 2)
                if key in ('kHangul', 'kJapaneseOldVariant', 'kTraditionalVariant'):
                    data[chr(int(code[2:], 16))][key] = value
    entries = [json.loads(line) for line in FILE.read_text().splitlines()]
    counts = collections.Counter()
    for entry in entries:
        char = entry['char']
        values = data[char]
        old = [chr(int(m, 16)) for m in re.findall(r'U\+([0-9A-F]+)', values.get('kJapaneseOldVariant', ''))]
        old = [c for c in old if data[c].get('kHangul')]
        trad = [chr(int(m, 16)) for m in re.findall(r'U\+([0-9A-F]+)', values.get('kTraditionalVariant', ''))]
        trad = [c for c in trad if c != char and data[c].get('kHangul')]
        direct = values.get('kHangul', '')
        # E indicates the basic Korean-education set; avoid picking a rare
        # spelling reading when the Japanese old form is the standard one.
        direct_has_education = any('E' in t.partition(':')[2] for t in direct.split())
        if len(old) == 1 and (not direct or not direct_has_education):
            target = old[0]
        elif direct:
            target = char
        elif len(trad) == 1:
            target = trad[0]
        else:
            target = None
        if target:
            readings = [unicodedata.normalize('NFC', t.partition(':')[0]) for t in data[target]['kHangul'].split()]
            entry['ko_hanja'] = ' / '.join(dict.fromkeys(readings))
            entry['ko_status'] = 'dictionary'
            entry['ko_source'] = 'Unicode Unihan 18.0.0 kHangul' + (f'（{char}→{target}，Unicode 字形对应）' if target != char else '')
            entry['ko_license'] = 'Unicode-3.0'
            counts['unihan'] += 1
        else:
            if char not in FALLBACK:
                raise ValueError(f'No unambiguous Unicode reading or AI fallback for {char}')
            entry['ko_hanja'] = FALLBACK[char]
            entry['ko_status'] = 'ai_gloss'
            entry['ko_source'] = 'AI 常识参考；Unicode kHangul 未找到可靠对应'
            entry['ko_license'] = 'project AI draft'
            counts['ai'] += 1
        if char == '円':
            entry['ko_note'] = '日语货币单位在韩语通常称 엔；圓 的汉字音是 원。'
        elif char == '働':
            entry['ko_note'] = '和制字，동 为未人工审校的 AI 字音参考，不代表通行韩语词。'
        elif char == '込':
            entry['ko_note'] = '和制字；未确认可靠的韩语汉字音，不推断韩语词。'
        elif char == '畑':
            entry['ko_note'] = '和制字；Unicode 列出的字音仅供字符参考，不推断韩语词。'
        elif char == '娘':
            entry.pop('ko_note', None)
    FILE.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in entries))
    print(dict(counts))

if __name__ == '__main__':
    main()
