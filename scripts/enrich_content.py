#!/usr/bin/env python3
"""Match Korean Basic Dictionary bilingual senses to vocabulary.

Download krdict/001.xml .. 011.xml from the repository and pass --dictionary-dir.
See reports/content_completion.md for licensing, provenance and limitations.
The script does not change review_status, ko_hanja, or learning state.
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'knowledge/seeds/vocabulary.jsonl'


def feat(element, name):
    return next((x.get('val', '') for x in element.findall('feat') if x.get('att') == name), '')


def terms(s):
    s = re.sub(r'[（(][^）)]*[）)]', '', s)
    return [x.strip() for x in re.split('[；;，,、/／]', s) if x.strip()]


def load_index(directory):
    index = defaultdict(list)
    paths = sorted(directory.glob('*.xml'))
    if len(paths) != 11:
        raise SystemExit('Expected all 11 Korean Basic Dictionary XML files')
    for path in paths:
        # The upstream XML contains a handful of invalid control characters.
        content = re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]', b'', path.read_bytes())
        from io import BytesIO
        for _, entry in ET.iterparse(BytesIO(content), events=('end',)):
            if entry.tag != 'LexicalEntry':
                continue
            lemma = entry.find('Lemma')
            ko = feat(lemma, 'writtenForm') if lemma is not None else ''
            for sense in entry.findall('Sense'):
                eqs = {feat(q, 'language'): feat(q, 'lemma') for q in sense.findall('Equivalent')}
                ja, zh = eqs.get('일본어', ''), eqs.get('중국어', '')
                for form in re.split(r'[。；;]', ja):
                    form = form.strip()
                    match = re.fullmatch(r'([ぁ-ゖァ-ヺー]+)【([^】]+)】', form)
                    if match:
                        kana, spellings = match.groups()
                        keys = [(s.strip(), kana) for s in re.split('[・･、，,]', spellings)]
                    elif re.fullmatch(r'[ぁ-ゖァ-ヺー]+', form):
                        keys = [(form, form)]
                    else:
                        keys = []
                    if ko and zh and not zh.startswith('(无对应'):
                        for key in keys:
                            index[key].append((ko, zh, entry.get('val', '')))
            entry.clear()
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dictionary-dir', required=True, type=Path)
    args = parser.parse_args()
    index = load_index(args.dictionary_dir)
    words = [json.loads(line) for line in FILE.read_text().splitlines()]
    count = 0
    for word in words:
        # Curated AI glosses take precedence over approximate dictionary matches.
        if word.get('ko_status') == 'ai_gloss':
            continue
        matches = []
        for ko, zh, source_id in index.get((word['surface'], word['kana']), []):
            target = terms(word['meaning_zh'])
            if not any(t == z or (len(t) >= 2 and len(z) >= 2 and (t in z or z in t)) for t in target for z in terms(zh)):
                continue
            if ko not in [m[0] for m in matches]:
                matches.append((ko, zh, source_id))
        if matches:
            # Include the original Chinese sense for transparent disambiguation.
            # Existing Korean hint gets preference only if independently matched.
            matches.sort(key=lambda x: (x[0] != word.get('ko_hanja'), len(x[0])))
            word['ko_hint'] = ' / '.join(f'{ko}（{zh}）' for ko, zh, _ in matches[:3])
            word['ko_status'] = 'dictionary'
            word['ko_source_ids'] = [m[2] for m in matches[:3]]
            count += 1
    FILE.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in words))
    print(f'{count}/{len(words)} matched by spelling, reading and Chinese sense')

if __name__ == '__main__':
    main()
