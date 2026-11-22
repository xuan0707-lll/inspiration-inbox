"""Transcribe local 16 kHz mono WAV segments with the cached Whisper model."""
import json
import re
import sys
import wave

import mlx_whisper
import numpy as np


def transcript_quality(result):
    text = result['text'].strip()
    return bool(text), -text.count('\ufffd'), len(re.findall(r'[。！？；，,.!?;]', text))


def transcript_cues(result):
    full = result['text'].strip()
    segments = [segment['text'].strip() for segment in result['segments'] if segment['text'].strip()]
    return [full] if ''.join(segments).count('\ufffd') > full.count('\ufffd') else segments


def main():
    model, context, *files = sys.argv[1:]
    cues = []
    prompt = '以下是简体中文口播，请保留标点。'
    for path in files:
        with wave.open(path) as audio:
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2')
        waveform = samples.astype(np.float32) / 32768
        result = mlx_whisper.transcribe(waveform, path_or_hf_repo=model, language='zh',
                                        initial_prompt=prompt + context, verbose=None)
        text = result['text'].strip()
        quality = transcript_quality(result)
        if context and (quality[1] < 0 or (len(text) >= 300 and quality[2] * 100 < len(text))):
            fallback = mlx_whisper.transcribe(waveform, path_or_hf_repo=model, language='zh',
                                              initial_prompt=prompt, verbose=None)
            if len(fallback['text'].strip()) >= len(text) * 0.7 and transcript_quality(fallback) > quality:
                result = fallback
        cues.extend(transcript_cues(result))
    print(json.dumps(cues, ensure_ascii=False))


if __name__ == '__main__':
    main()
