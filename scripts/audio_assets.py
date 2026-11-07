#!/usr/bin/env python3
"""Generate original Japanese listening assets using macOS say; never plays audio."""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / 'knowledge/seeds/materials.jsonl'
OUT = ROOT / 'data/audio'
VOICE = 'Kyoko'


def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def main():
    for command in ('say', 'afconvert', 'ffprobe'):
        if not shutil.which(command):
            raise SystemExit(f'missing required command: {command}')
    materials = [json.loads(line) for line in SEEDS.read_text(encoding='utf-8').splitlines() if line.strip()]
    selected = [m for m in materials if m.get('id') in {f'M{i:04d}' for i in range(96, 141)}]
    if len(selected) != 45 or any(m.get('license') != 'original' or m.get('review_status') != 'ai_draft' or not m.get('audio_text') for m in selected):
        raise SystemExit('Expected 45 original ai_draft materials with audio_text; refusing generation')
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {'version': 1, 'generator': 'macOS say + afconvert', 'voice': VOICE, 'kind': 'synthetic', 'items': {}}
    with tempfile.TemporaryDirectory() as tmp:
        for m in selected:
            mid = m['id']
            source = m['audio_text']
            aiff = Path(tmp) / f'{mid}.aiff'
            encoded = Path(tmp) / f'{mid}.m4a'
            run('say', '-v', VOICE, '-o', str(aiff), source)
            run('afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(aiff), str(encoded))
            raw = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(encoded)], text=True)
            duration = float(raw.strip())
            if duration <= 0 or not encoded.stat().st_size:
                raise SystemExit(f'invalid audio: {mid}')
            encoded.replace(OUT / f'{mid}.m4a')
            manifest['items'][mid] = {'file': f'{mid}.m4a', 'text_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest(), 'duration_sec': round(duration, 3), 'bytes': (OUT / f'{mid}.m4a').stat().st_size}
            print(f'{mid}: {duration:.2f}s', flush=True)
    tmp_manifest = OUT / '.manifest.tmp'
    tmp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp_manifest.replace(OUT / 'manifest.json')


if __name__ == '__main__':
    main()
