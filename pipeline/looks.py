"""Picks the look of each Viksit Bharat Short so no two look alike.

A look is a palette, a background motion and a hook style. The picker keeps
three rules:
- no palette repeats within 8 Shorts, and two Shorts in a row never share a
  background colour family (relaxed one step at a time only if no pick fits);
- no motion repeats within 8 Shorts;
- the full palette + motion + hook combination never repeats within 21 days.
Picks are stored in state/looks.json, which the daily run commits.
"""
import json
import random
from pathlib import Path

from render.painters.viksit_bharat import HOOKS_FOR, MOTIONS, PALETTES

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "looks.json"


def _load():
    return json.loads(STATE.read_text()) if STATE.exists() else []


def pick(stem, first_scene_type):
    history = [h for h in _load() if h["stem"] != stem]
    history.sort(key=lambda h: h["stem"])
    earlier = [h for h in history if h["stem"] < stem]
    last21 = earlier[-21:]
    prev_family = PALETTES[earlier[-1]["palette"]]["family"] if earlier else None
    hooks = HOOKS_FOR.get(first_scene_type, HOOKS_FOR["headline"])
    rng = random.Random(stem)
    seen_combo = {(h["palette"], h["motion"], h["hook"]) for h in last21}

    def options(window, family_rule):
        recent = earlier[-window:] if window else []
        used_p, used_m = {h["palette"] for h in recent}, {h["motion"] for h in recent}
        return [(p, m, k) for p in PALETTES for m in MOTIONS for k in hooks
                if p not in used_p and m not in used_m and (p, m, k) not in seen_combo
                and not (family_rule and PALETTES[p]["family"] == prev_family)]

    # strictest first; each fallback relaxes one rule, the combination rule always holds
    for window, family_rule in ((7, True), (7, False), (5, True), (3, True), (0, True), (0, False)):
        opts = options(window, family_rule)
        if opts:
            break
    p, m, k = rng.choice(opts)
    look = {"stem": stem, "palette": p, "motion": m, "hook": k}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(sorted(history + [look], key=lambda h: h["stem"])[-120:], indent=1))
    return {"palette": p, "motion": m, "hook": k}
