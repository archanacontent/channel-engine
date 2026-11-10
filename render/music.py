"""Original music, composed fresh for every Short.

Each episode gets its own key, chord progression, tempo, groove and melody,
picked from a seed made of the channel and the episode name. A per-channel
registry (channels/<slug>/music/used.json) records every track's signature,
and a repeat is rerolled, so no two Shorts on a channel share a track.
Everything is synthesised here, so there is no licence to track and nothing
for Content ID to match.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve, lfilter

SR = 24000
NOTE = lambda midi: 440.0 * 2 ** ((midi - 69) / 12)

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11], "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

# Progressions as scale degrees (0 = I). Several per channel, so the harmony varies too.
STYLES = {
    "asked-and-answered": dict(modes=["major", "dorian", "mixolydian"], bpm=(78, 92), lead="epiano", pad=0.5,
                               drums="lofi", bass=True, swing=0.12, reverb=1.2,
                               progs=[[0, 5, 3, 4], [0, 3, 5, 4], [5, 3, 0, 4], [0, 4, 5, 3], [1, 4, 0, 5],
                                      [0, 2, 3, 4], [3, 4, 2, 5], [0, 5, 1, 4]]),
    "automation-shelf": dict(modes=["major", "mixolydian", "lydian"], bpm=(108, 122), lead="pluck", pad=0.35,
                             drums="pop", bass=True, swing=0.0, reverb=0.9,
                             progs=[[0, 4, 5, 3], [0, 5, 3, 4], [3, 0, 4, 5], [0, 3, 4, 4], [5, 3, 0, 4],
                                    [0, 1, 3, 4], [3, 4, 0, 0], [0, 4, 1, 3]]),
    "breach-brief": dict(modes=["minor", "phrygian", "dorian"], bpm=(84, 98), lead="pulse", pad=0.8,
                         drums="tension", bass=True, swing=0.0, reverb=1.8,
                         progs=[[0, 0, 5, 6], [0, 5, 3, 6], [0, 1, 0, 6], [0, 3, 5, 4], [0, 6, 5, 6],
                                [0, 0, 3, 1], [5, 6, 0, 0], [0, 2, 5, 6]]),
    "plain-docs": dict(modes=["major", "lydian"], bpm=(68, 80), lead="piano", pad=0.25, drums=None, bass=False,
                       swing=0.0, reverb=1.6,
                       progs=[[0, 4, 5, 3], [0, 3, 0, 4], [5, 3, 0, 4], [0, 5, 3, 4], [3, 0, 4, 5],
                              [0, 2, 3, 4], [0, 3, 1, 4], [3, 4, 5, 0]]),
    "deep-field": dict(modes=["lydian", "minor", "dorian"], bpm=(56, 66), lead="bell", pad=1.0, drums=None,
                       bass=True, swing=0.0, reverb=2.6,
                       progs=[[0, 1, 0, 5], [0, 5, 3, 0], [0, 3, 0, 4], [5, 3, 0, 0], [0, 6, 5, 3],
                              [0, 1, 5, 3], [3, 0, 5, 1], [0, 0, 3, 3]]),
}


# ---------- instruments ----------

def env_adsr(n, a, d, s, r):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    e = np.full(n, s, np.float32)
    e[:min(a, n)] = np.linspace(0, 1, a)[:min(a, n)]
    if a < n:
        seg = np.linspace(1, s, d)[: max(0, min(d, n - a))]
        e[a:a + len(seg)] = seg
    if r and n > r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x).astype(np.float32)


def pad_voice(freqs, dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for f in freqs:
        for det in (-0.006, 0.0, 0.007):
            ph = rng.uniform(0, 2 * np.pi)
            ff = f * (1 + det)
            out += (np.sin(2 * np.pi * ff * t + ph) + 0.35 * np.sin(4 * np.pi * ff * t + ph)
                    + 0.15 * np.sin(6 * np.pi * ff * t + ph)).astype(np.float32)
    out = lowpass(out, 1800)
    return out * env_adsr(n, min(0.9, dur * 0.3), 0.4, 0.8, min(0.8, dur * 0.3)) / (3 * len(freqs))


def epiano(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    idx = 2.2 * np.exp(-t * 5)
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.exp(-t * 2.2)
    return (s * env_adsr(n, 0.004, 0.1, 1, 0.05)).astype(np.float32)


def piano(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2.5 + k)) for k, a in ((1, 1), (2, 0.4), (3, 0.18), (4, 0.08)))
    return (s * env_adsr(n, 0.003, 0.1, 1, 0.08)).astype(np.float32)


def bell(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t + 1.4 * np.exp(-t * 1.2) * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t * 1.1)
    return (s * env_adsr(n, 0.01, 0.1, 1, 0.3)).astype(np.float32)


def pluck(f, dur, rng):
    n = int(dur * SR)
    period = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, period).astype(np.float32)
    out = np.zeros(n, np.float32)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return lowpass(out, 3500) * env_adsr(n, 0.002, 0.05, 1, 0.05)


def pulse(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * t) * 0.5
    return lowpass(s.astype(np.float32), 900) * env_adsr(n, 0.01, 0.15, 0.3, 0.1)


def bass_note(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.tanh(1.6 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)))
    return (s * env_adsr(n, 0.01, 0.2, 0.7, 0.08)).astype(np.float32)


def kick(soft=1.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t * 30)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * soft).astype(np.float32)


def hat(rng, length=0.06):
    n = int(length * SR)
    s = rng.uniform(-1, 1, n).astype(np.float32)
    s = s - lowpass(s, 6000)
    return s * np.exp(-np.arange(n) / SR * 60).astype(np.float32) * 0.5


def snare(rng):
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    s = rng.uniform(-1, 1, n) * np.exp(-t * 22) * 0.5 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return lowpass(s.astype(np.float32), 5000)


def reverb(x, seconds, rng, wet=0.28):
    n = int(seconds * SR)
    ir = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir = lowpass(ir.astype(np.float32), 5000)
    y = fftconvolve(x, ir)[: len(x)]
    y /= np.max(np.abs(y)) + 1e-9
    return (1 - wet) * x / (np.max(np.abs(x)) + 1e-9) + wet * y


def add(out, x, at):
    s = int(at * SR)
    if s >= len(out):
        return
    e = min(len(out), s + len(x))
    out[s:e] += x[: e - s]


# ---------- composition ----------

def plan(slug, episode, used, attempt=0):
    st = STYLES[slug]
    seed = int(hashlib.sha256(f"{slug}|{episode}|{attempt}".encode()).hexdigest()[:12], 16)
    rng = np.random.default_rng(seed)
    root = int(rng.integers(0, 12))
    mode = st["modes"][int(rng.integers(len(st["modes"])))]
    prog = int(rng.integers(len(st["progs"])))
    bpm = int(rng.integers(st["bpm"][0], st["bpm"][1] + 1))
    motif = [int(x) for x in rng.integers(0, 8, 6)]
    rhythm = [int(x) for x in rng.integers(0, 2, 8)]
    sig = f"{root}-{mode}-{prog}-{bpm}-{''.join(map(str, motif))}"
    # The harmonic core (key, mode, progression, tempo) must also be new on this channel.
    core = sig.rsplit("-", 1)[0]
    if core in {u.rsplit("-", 1)[0] for u in used} and attempt < 50:
        return plan(slug, episode, used, attempt + 1)
    return dict(seed=seed, root=root, mode=mode, prog=prog, bpm=bpm, motif=motif, rhythm=rhythm, sig=sig)


def compose(slug, p, dur):
    st = STYLES[slug]
    rng = np.random.default_rng(p["seed"])
    scale = SCALES[p["mode"]]
    base = 48 + p["root"]
    beat = 60.0 / p["bpm"]
    bar = beat * 4
    prog = st["progs"][p["prog"]]
    n = int(dur * SR)
    pad_l, lead_l, bass_l, drum_l = (np.zeros(n + SR * 3, np.float32) for _ in range(4))

    def deg(d, octave=0):
        return base + scale[d % 7] + 12 * (d // 7 + octave)

    bars = int(dur / bar) + 2
    for b in range(bars):
        t0 = b * bar
        d = prog[b % len(prog)]
        chord = [deg(d), deg(d + 2), deg(d + 4)]
        if st["pad"]:
            add(pad_l, pad_voice([NOTE(m) for m in chord], bar + 0.6, rng) * st["pad"], t0)
        if st["bass"]:
            if st["drums"] in ("pop", "lofi"):
                for k in (0, 2.5):
                    add(bass_l, bass_note(NOTE(chord[0] - 12), beat * 1.2), t0 + k * beat)
            else:
                add(bass_l, bass_note(NOTE(chord[0] - 12), bar * 0.95), t0)
        # Lead: the motif, shifted onto each chord, playing on the bar's own rhythm.
        steps = 8 if st["lead"] in ("pluck", "pulse") else 4
        for s in range(steps):
            on = p["rhythm"][s % 8] or s == 0
            if st["lead"] in ("bell", "piano") and s % 2 and not p["rhythm"][s]:
                on = False
            if not on:
                continue
            m = deg(d + p["motif"][(s + b) % len(p["motif"])], 1)
            at = t0 + s * bar / steps + (st["swing"] * bar / steps if s % 2 else 0)
            ln = bar / steps * 1.6
            f = NOTE(m)
            voice = {"epiano": lambda: epiano(f, ln * 1.5), "piano": lambda: piano(f, ln * 2.5),
                     "bell": lambda: bell(f, ln * 3), "pluck": lambda: pluck(f, ln, rng),
                     "pulse": lambda: pulse(f, ln)}[st["lead"]]()
            add(lead_l, voice * (0.55 if st["lead"] != "pulse" else 0.35), at)
        if st["drums"] == "lofi":
            for k in (0, 2.5):
                add(drum_l, kick(0.8), t0 + k * beat)
            for k in (1, 3):
                add(drum_l, snare(rng) * 0.6, t0 + k * beat)
            for k in range(8):
                add(drum_l, hat(rng) * (0.5 if k % 2 else 0.3), t0 + k * beat / 2 + (st["swing"] * beat / 2 if k % 2 else 0))
        elif st["drums"] == "pop":
            for k in range(4):
                add(drum_l, kick(0.9), t0 + k * beat)
            for k in (1, 3):
                add(drum_l, snare(rng) * 0.5, t0 + k * beat)
            for k in range(8):
                add(drum_l, hat(rng) * 0.35, t0 + k * beat / 2 + beat / 4)
        elif st["drums"] == "tension":
            add(drum_l, kick(0.9), t0)
            add(drum_l, kick(0.6), t0 + 2.75 * beat)
            for k in range(16):
                if p["rhythm"][k % 8]:
                    add(drum_l, hat(rng, 0.03) * 0.25, t0 + k * beat / 4)

    mixl = 0.9 * pad_l + 0.7 * lead_l + 0.6 * bass_l + 0.55 * drum_l
    mixl = reverb(mixl, st["reverb"], rng)
    mixl = mixl[:n]
    t = np.arange(n) / SR
    fade = np.clip(np.minimum(t / 1.0, (dur - t) / 1.5), 0, 1)
    out = (mixl * fade).astype(np.float32)
    return out / (np.max(np.abs(out)) + 1e-9)


def bed_for(slug, episode, dur, music_dir):
    reg_path = Path(music_dir) / "used.json"
    reg = json.loads(reg_path.read_text()) if reg_path.exists() else {}
    if episode in reg:
        p = reg[episode]
    else:
        p = plan(slug, episode, [v["sig"] for v in reg.values()])
        reg[episode] = p
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        reg_path.write_text(json.dumps(reg, indent=1, sort_keys=True))
    return compose(slug, p, dur), f"original: {p['sig']} @ {p['bpm']} bpm"
