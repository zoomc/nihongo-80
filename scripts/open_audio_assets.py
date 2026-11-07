#!/usr/bin/env python3
"""Generate public original-material audio with locally installed Kokoro, no audio playback."""
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/audio'
VOICE = 'jf_alpha'
MODEL = 'hexgrad/Kokoro-82M'
MODEL_REVISION = 'f3ff3571791e39611d31c381e3a41a3af07b4987'
_pipeline = None


def notice_text():
    """Attributions that travel with publicly generated audio."""
    header = "Nihongo 150 audio M0096–M0140: attribution and license notice\n\nThese recordings are machine-synthesized from original project AI-draft texts;\nthey are not recordings of a human speaker. Pronunciation has not been\nverified by a human reviewer.\n\nSynthesis model: Kokoro-82M v1.0 by hexgrad; voice: {voice}.\nModel repository and card: https://huggingface.co/hexgrad/Kokoro-82M\nRepository revision: {revision}\nModel weights license: Apache License 2.0, https://www.apache.org/licenses/LICENSE-2.0\nVoice list and attribution data: https://huggingface.co/hexgrad/Kokoro-82M/blob/{revision}/VOICES.md\nThe jf_alpha row lists no additional voice-specific CC BY attribution; other\nJapanese voices have separate credited sources and are not used here.\n\nThe Kokoro v1.0 model card identifies these CC BY datasets in its training data:\n- Koniwa tnc, voice recordings by Television Nishinippon (TNC), collected by\n  Koniwa: https://github.com/koniwa/koniwa ; CC BY 3.0:\n  https://creativecommons.org/licenses/by/3.0/\n- The SIWIS French Speech Synthesis Database, Junichi Yamagishi, Pierre-Edouard\n  Honnet, Philip Garner and Alexandros Lazaridis (2017):\n  https://doi.org/10.7488/ds/1705 ; CC BY 4.0:\n  https://creativecommons.org/licenses/by/4.0/\nThese datasets were used by the model's authors to train the model; they are\nnot the project source texts or recordings. The model card does not establish\nwhich training samples contributed to any particular generated audio.\n\nJapanese text analysis: The UniDic Consortium, UniDic for Contemporary Written\nJapanese 3.1.0, https://clrd.ninjal.ac.jp/unidic/en/ . The BSD option of its\nGPL v2 / LGPL v2.1 / modified BSD triple license applies here. Authors file:\nThe UniDic Consortium. The dictionary itself is not distributed in these audio\nfiles. Its BSD license text follows.\n\n"
    bsd = 'Copyright (c) 2011-2021, The UniDic Consortium\nAll rights reserved.\n\nRedistribution and use in source and binary forms, with or without\nmodification, are permitted provided that the following conditions are\nmet:\n\n * Redistributions of source code must retain the above copyright\n   notice, this list of conditions and the following disclaimer.\n\n * Redistributions in binary form must reproduce the above copyright\n   notice, this list of conditions and the following disclaimer in the\n   documentation and/or other materials provided with the\n   distribution.\n\n * Neither the name of the UniDic Consortium nor the names of its\n   contributors may be used to endorse or promote products derived\n   from this software without specific prior written permission.\n\nTHIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS\n"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT\nLIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR\nA PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT\nOWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,\nSPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT\nLIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,\nDATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY\nTHEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT\n(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE\nOF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.\n'
    return header.format(voice=VOICE, revision=MODEL_REVISION) + bsd


def init_worker():
    global _pipeline
    import torch
    from kokoro import KPipeline, KModel
    torch.set_num_threads(2)
    snapshot = Path(os.environ['NIHONGO_KOKORO_SNAPSHOT'])
    model = KModel(repo_id=MODEL, config=str(snapshot / 'config.json'), model=str(snapshot / 'kokoro-v1_0.pth')).to('cpu').eval()
    _pipeline = KPipeline(lang_code='j', repo_id=MODEL, model=model, device='cpu')


def render(item):
    import numpy as np
    import soundfile as sf
    mid, source, target = item
    pieces = []
    sentences = re.findall(r'.+?[。！？]|.+$', source)
    for sentence in sentences:
        segments = [result.audio.numpy() for result in _pipeline(sentence, voice=str(Path(os.environ['NIHONGO_KOKORO_SNAPSHOT'])/'voices'/f'{VOICE}.pt'), speed=1) if result.audio is not None]
        if not segments:
            raise RuntimeError(f'{mid}: no audio for sentence {sentence!r}')
        pieces.extend(segments)
        pieces.append(np.zeros(2400, dtype=np.float32))
    samples = np.concatenate(pieces)
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) < 0.001:
        raise RuntimeError(f'{mid}: invalid or silent waveform')
    wav = Path(target) / (mid + '.wav')
    output = Path(target) / (mid + '.m4a')
    sf.write(wav, samples, 24000)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-c:a','aac','-b:a','64k','-movflags','+faststart',str(output)],check=True)
    wav.unlink()
    return mid, {'url': f'/audio/{mid}.m4a', 'text_sha256': hashlib.sha256(source.encode()).hexdigest(), 'duration_sec': round(len(samples)/24000,3), 'bytes': output.stat().st_size}


def main():
    materials = [json.loads(line) for line in (ROOT/'knowledge/seeds/materials.jsonl').read_text().splitlines() if line.strip()]
    wanted = {f'M{i:04d}' for i in range(96,141)}
    selected = [m for m in materials if m.get('id') in wanted]
    if len(selected)!=45 or any(m.get('license')!='original' or m.get('review_status')!='ai_draft' or not m.get('audio_text') for m in selected):
        raise SystemExit('Expected 45 original ai_draft materials')
    # Pin the exact downloaded model revision for repeatable provenance; this does not call a hosted inference service.
    os.environ.setdefault('HF_HUB_OFFLINE','1')
    from huggingface_hub import snapshot_download
    os.environ['NIHONGO_KOKORO_SNAPSHOT'] = snapshot_download(MODEL, revision=MODEL_REVISION, local_files_only=True, allow_patterns=['config.json','kokoro-v1_0.pth','voices/jf_alpha.pt'])
    snapshot = Path(os.environ['NIHONGO_KOKORO_SNAPSHOT'])
    expected = {'kokoro-v1_0.pth': '496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4', 'voices/jf_alpha.pt': '1bf4c9dc69e45ee46183b071f4db766349aac5592acbcfeaf051018048a5d787'}
    for name, digest in expected.items():
        if hashlib.sha256((snapshot/name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f'model checksum mismatch: {name}')
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nihongo-open-audio-') as tmp:
        jobs = [(m['id'], m['audio_text'], tmp) for m in selected]
        items = {}
        with concurrent.futures.ProcessPoolExecutor(max_workers=3, initializer=init_worker) as pool:
            for mid, info in pool.map(render, jobs):
                items[mid] = info
                print(f"{mid}: {info['duration_sec']}s", flush=True)
        for mid in items:
            (Path(tmp)/(mid+'.m4a')).replace(OUT/(mid+'.m4a'))
        manifest = {'version':1, 'kind':'synthetic', 'generator':'Kokoro-82M v1.0 + UniDic', 'voice':VOICE, 'model_revision':MODEL_REVISION, 'items':items}
        (Path(tmp)/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        (Path(tmp)/'manifest.json').replace(OUT/'manifest.json')
        (Path(tmp)/'NOTICE.txt').write_text(notice_text(), encoding='utf-8')
        (Path(tmp)/'NOTICE.txt').replace(OUT/'NOTICE.txt')


if __name__ == '__main__':
    main()
