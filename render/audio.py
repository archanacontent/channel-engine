"""Voice with Kokoro-82M (Apache 2.0, runs locally) and the music bed under it."""
import os
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
GAP = 0.32          # silence after each beat
LEAD_IN = 0.25      # silence before the first word
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", Path.home() / ".cache" / "kokoro"))

_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    return _kokoro


def trim(x, thr=0.004):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - 240): idx[-1] + 480]


def speak_beats(beats, voice_cfg):
    """Return (voice track, [(beat_start, speech_dur, beat_dur)])."""
    k = kokoro()
    parts, timing, t = [np.zeros(int(SR * LEAD_IN), np.float32)], [], LEAD_IN
    for b in beats:
        s, sr = k.create(b["say"], voice=voice_cfg["voice"], speed=voice_cfg["speed"],
                         lang=voice_cfg.get("lang", "en-us"))
        assert sr == SR
        s = trim(np.asarray(s, np.float32))
        speech = len(s) / SR
        parts += [s, np.zeros(int(SR * GAP), np.float32)]
        timing.append((t, speech, speech + GAP))
        t += speech + GAP
    v = np.concatenate(parts)
    v = v / (np.max(np.abs(v)) + 1e-9) * 0.89
    return v, timing


# ---------- music bed ----------
# Samples use a bed synthesised here, so it carries no licence terms at all.
# A channel's music/ folder of Pixabay tracks replaces it once tracks are added.

BEDS = {
    "asked-and-answered": dict(chords=[[220.0, 277.18, 329.63], [196.0, 246.94, 293.66],
                                       [174.61, 220.0, 261.63], [196.0, 246.94, 329.63]],
                               bar=3.2, pulse=0.4, bright=0.5),
    "automation-shelf": dict(chords=[[261.63, 329.63, 392.0], [293.66, 369.99, 440.0],
                                     [246.94, 311.13, 369.99], [220.0, 277.18, 329.63]],
                             bar=2.4, pulse=0.3, bright=0.7),
    "breach-brief": dict(chords=[[110.0, 130.81, 164.81], [103.83, 123.47, 155.56]],
                         bar=4.8, pulse=0.6, bright=0.2),
    "plain-docs": dict(chords=[[261.63, 329.63, 392.0], [220.0, 261.63, 329.63],
                               [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]],
                       bar=3.6, pulse=0.0, bright=0.35),
    "deep-field": dict(chords=[[130.81, 196.0, 246.94], [116.54, 174.61, 233.08],
                               [103.83, 155.56, 207.65], [116.54, 174.61, 220.0]],
                       bar=5.0, pulse=0.0, bright=0.3),
}


def synth_bed(slug, dur):
    p = BEDS[slug]
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    bar_n = int(p["bar"] * SR)
    rng = np.random.default_rng(7)
    for bi in range(n // bar_n + 1):
        chord = p["chords"][bi % len(p["chords"])]
        s, e = bi * bar_n, min(n, (bi + 1) * bar_n + int(0.8 * SR))
        if s >= n:
            break
        tt = t[s:e] - t[s]
        env = np.minimum(1, tt / 0.9) * np.exp(-np.maximum(0, tt - p["bar"]) / 0.3)
        for f in chord:
            det = 1 + rng.uniform(-0.002, 0.002)
            tone = np.sin(2 * np.pi * f * det * tt) + p["bright"] * 0.3 * np.sin(4 * np.pi * f * tt)
            out[s:e] += (tone * env * 0.18).astype(np.float32)
        if p["pulse"]:
            step = p["bar"] / 8
            for j in range(8):
                ps = s + int(j * step * SR)
                if ps >= n:
                    break
                pe = min(n, ps + int(0.35 * SR))
                pt = t[ps:pe] - t[ps]
                f = chord[j % len(chord)] * 2
                out[ps:pe] += (np.sin(2 * np.pi * f * pt) * np.exp(-pt / 0.08) * 0.09 * p["pulse"]).astype(np.float32)
    fade = np.minimum(1, np.minimum(t / 1.0, (dur - t) / 1.2))
    out *= np.clip(fade, 0, 1)
    return out / (np.max(np.abs(out)) + 1e-9)


def load_bed(slug, music_dir, dur):
    tracks = sorted(Path(music_dir).glob("*.mp3")) + sorted(Path(music_dir).glob("*.wav"))
    if not tracks:
        return synth_bed(slug, dur), "synthesised bed"
    import subprocess
    pick = tracks[hash(slug + str(int(dur))) % len(tracks)]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pick), "-t", str(dur), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.float32).copy()
    m = np.pad(m, (0, max(0, int(dur * SR) - len(m))))
    return m / (np.max(np.abs(m)) + 1e-9), pick.name


def mixdown(voice, bed, gain_db, out_wav):
    n = max(len(voice), len(bed))
    v = np.pad(voice, (0, n - len(voice)))
    b = np.pad(bed, (0, n - len(bed))) * (10 ** (gain_db / 20))
    # Duck the bed a further 4 dB while the voice is speaking.
    env = np.convolve(np.abs(v), np.ones(2400) / 2400, mode="same")
    duck = np.where(env > 0.01, 10 ** (-4 / 20), 1.0)
    duck = np.convolve(duck, np.ones(4800) / 4800, mode="same")
    m = v + b * duck
    m = m / (np.max(np.abs(m)) + 1e-9) * 0.93
    sf.write(out_wav, m, SR)
