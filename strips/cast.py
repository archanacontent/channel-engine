"""The Comicsofy ensemble: people, a dog and a pigeon, all drawn as SVG.

Every character shares one mood list (MOODS), so the writer never has to know
which body it is drawing. Origin is the body centre; feet rest on y = 124.
"""
from functools import partial

INK = "#1d1a22"

MOODS = ["neutral", "happy", "laughing", "angry", "shocked", "smug", "sad", "tired", "panic", "deadpan",
         "scheming", "love", "proud", "sleeping", "crying"]

STROKE = f'stroke="{INK}" stroke-width="6" stroke-linejoin="round"'


# ---------------------------------------------------------------- faces

def face(mood, talking, ex=21, ey=-96, my=-64, white="#fff", iris=INK, lid=None, blink=False):
    """Eyes, brows and mouth for any front-facing head. ex = half the eye spacing."""
    L, R = -ex, ex
    dot = lambda cx, r=6.5: f'<ellipse cx="{cx}" cy="{ey}" rx="{r}" ry="{r * 1.25}" fill="{iris}"/><circle cx="{cx + 2}" cy="{ey - 3}" r="2.2" fill="#fff"/>'
    arc_up = lambda cx: f'<path d="M{cx - 11},{ey + 3} Q{cx},{ey - 11} {cx + 11},{ey + 3}" stroke="{INK}" stroke-width="5.5" fill="none" stroke-linecap="round"/>'
    arc_dn = lambda cx: f'<path d="M{cx - 11},{ey - 3} Q{cx},{ey + 8} {cx + 11},{ey - 3}" stroke="{INK}" stroke-width="5.5" fill="none" stroke-linecap="round"/>'
    big = lambda cx, p=4.5: (f'<circle cx="{cx}" cy="{ey}" r="14" fill="{white}" stroke="{INK}" stroke-width="4.5"/>'
                             f'<circle cx="{cx}" cy="{ey}" r="{p}" fill="{iris}"/>')
    half = lambda cx: (f'<ellipse cx="{cx}" cy="{ey + 2}" rx="11" ry="9" fill="{white}" stroke="{INK}" stroke-width="4"/>'
                       f'<circle cx="{cx}" cy="{ey + 4}" r="4.5" fill="{iris}"/>'
                       f'<path d="M{cx - 13},{ey} L{cx + 13},{ey}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
                       + (f'<path d="M{cx - 12},{ey - 1} L{cx + 12},{ey - 1} L{cx + 12},{ey - 10} L{cx - 12},{ey - 10} Z" fill="{lid}"/>' if lid else ""))
    line = lambda cx: f'<path d="M{cx - 11},{ey} L{cx + 11},{ey}" stroke="{INK}" stroke-width="5.5" stroke-linecap="round"/>'
    heart = lambda cx: f'<path transform="translate({cx},{ey}) scale(0.75)" d="M0,10 C-18,-4 -14,-20 -4,-18 C0,-17 0,-14 0,-12 C0,-14 0,-17 4,-18 C14,-20 18,-4 0,10 Z" fill="#ff5a7a" stroke="{INK}" stroke-width="3"/>'
    by = ey - 20
    brow = lambda d: f'<path d="{d}" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>'
    brows = {
        "angry": brow(f"M{L - 13},{by - 6} L{L + 10},{by + 4} M{R + 13},{by - 6} L{R - 10},{by + 4}"),
        "sad": brow(f"M{L - 12},{by + 3} L{L + 9},{by - 5} M{R + 12},{by + 3} L{R - 9},{by - 5}"),
        "crying": brow(f"M{L - 12},{by + 3} L{L + 9},{by - 5} M{R + 12},{by + 3} L{R - 9},{by - 5}"),
        "shocked": brow(f"M{L - 11},{by - 10} Q{L},{by - 16} {L + 11},{by - 10} M{R - 11},{by - 10} Q{R},{by - 16} {R + 11},{by - 10}"),
        "panic": brow(f"M{L - 12},{by - 2} L{L + 9},{by - 9} M{R + 12},{by - 2} L{R - 9},{by - 9}"),
        "smug": brow(f"M{L - 11},{by + 2} L{L + 11},{by + 2} M{R - 11},{by - 4} Q{R},{by - 12} {R + 12},{by - 6}"),
        "scheming": brow(f"M{L - 13},{by - 4} L{L + 10},{by + 6} M{R + 13},{by - 4} L{R - 10},{by + 6}"),
        "deadpan": brow(f"M{L - 11},{by + 4} L{L + 11},{by + 4} M{R - 11},{by + 4} L{R + 11},{by + 4}"),
        "tired": brow(f"M{L - 11},{by + 2} L{L + 11},{by + 5} M{R - 11},{by + 5} L{R + 11},{by + 2}"),
    }.get(mood, "")
    eyes = {
        "neutral": dot(L) + dot(R), "happy": arc_up(L) + arc_up(R), "laughing": arc_up(L) + arc_up(R),
        "angry": dot(L) + dot(R), "shocked": big(L, 3.5) + big(R, 3.5), "smug": half(L) + half(R),
        "sad": dot(L) + dot(R), "tired": half(L) + half(R), "panic": big(L, 5) + big(R, 5),
        "deadpan": line(L) + line(R), "scheming": half(L) + half(R), "love": heart(L) + heart(R),
        "proud": arc_dn(L) + arc_dn(R), "sleeping": arc_dn(L) + arc_dn(R), "crying": arc_dn(L) + arc_dn(R),
    }[mood]
    m = lambda d, w=5: f'<path d="{d}" stroke="{INK}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    open_mouth = f'<path d="M-12,{my - 5} Q0,{my - 9} 12,{my - 5} Q14,{my + 12} 0,{my + 14} Q-14,{my + 12} -12,{my - 5} Z" fill="#7a2232" stroke="{INK}" stroke-width="4"/><ellipse cx="0" cy="{my + 8}" rx="6" ry="3.5" fill="#ff8a9a"/>'
    mouths = {
        "neutral": m(f"M-9,{my} L9,{my}"), "happy": m(f"M-14,{my - 4} Q0,{my + 10} 14,{my - 4}"),
        "laughing": f'<path d="M-18,{my - 6} L18,{my - 6} Q16,{my + 18} 0,{my + 20} Q-16,{my + 18} -18,{my - 6} Z" fill="#7a2232" stroke="{INK}" stroke-width="4"/><path d="M-14,{my - 6} L14,{my - 6} L12,{my} L-12,{my} Z" fill="#fff"/>',
        "angry": f'<rect x="-15" y="{my - 7}" width="30" height="14" rx="4" fill="#fff" stroke="{INK}" stroke-width="4"/><path d="M-15,{my} L15,{my} M-5,{my - 7} L-5,{my + 7} M5,{my - 7} L5,{my + 7}" stroke="{INK}" stroke-width="2.5"/>',
        "shocked": f'<ellipse cx="0" cy="{my + 2}" rx="9" ry="13" fill="#7a2232" stroke="{INK}" stroke-width="4"/>',
        "smug": m(f"M-12,{my} Q4,{my + 4} 15,{my - 8}"), "sad": m(f"M-12,{my + 6} Q0,{my - 6} 12,{my + 6}"),
        "tired": m(f"M-10,{my + 2} Q0,{my - 1} 10,{my + 2}"),
        "panic": m(f"M-15,{my + 2} Q-10,{my - 5} -5,{my + 2} Q0,{my + 8} 5,{my + 2} Q10,{my - 5} 15,{my + 2}", 4.5),
        "deadpan": m(f"M-11,{my} L11,{my}"),
        "scheming": f'<path d="M-18,{my - 6} Q0,{my + 4} 18,{my - 6} Q14,{my + 12} 0,{my + 12} Q-14,{my + 12} -18,{my - 6} Z" fill="#fff" stroke="{INK}" stroke-width="4"/>',
        "love": m(f"M-12,{my - 4} Q0,{my + 8} 12,{my - 4}"), "proud": m(f"M-14,{my - 4} Q0,{my + 10} 14,{my - 4}"),
        "sleeping": f'<ellipse cx="0" cy="{my}" rx="5" ry="6" fill="#7a2232" stroke="{INK}" stroke-width="3"/>',
        "crying": f'<path d="M-16,{my + 10} Q0,{my - 12} 16,{my + 10} Z" fill="#7a2232" stroke="{INK}" stroke-width="4"/>',
    }
    mouth = open_mouth if talking and mood not in ("laughing", "shocked", "crying") else mouths[mood]
    if talking == 1 and mouth is open_mouth:   # half-open, for quiet syllables in the Reels
        mouth = f'<g transform="translate(0,{my + 3}) scale(0.8,0.5) translate(0,{-my - 3})">{open_mouth}</g>'
    if blink and mood not in ("happy", "laughing", "love", "proud", "sleeping", "crying", "deadpan"):
        eyes = arc_dn(L) + arc_dn(R)
    extra = ""
    if mood in ("panic", "shocked"):
        extra += f'<path d="M{R + 30},{ey - 26} Q{R + 40},{ey - 8} {R + 30},{ey} Q{R + 20},{ey - 8} {R + 30},{ey - 26} Z" fill="#9fd3ff" stroke="{INK}" stroke-width="3"/>'
    if mood == "crying":
        extra += "".join(f'<path d="M{cx},{ey + 8} Q{cx - 6},{ey + 40} {cx},{ey + 52} Q{cx + 6},{ey + 40} {cx},{ey + 8} Z" fill="#9fd3ff" stroke="{INK}" stroke-width="2.5"/>' for cx in (L, R))
    if mood == "sad":
        extra += f'<path d="M{L},{ey + 10} Q{L - 5},{ey + 24} {L},{ey + 30} Q{L + 5},{ey + 24} {L},{ey + 10} Z" fill="#9fd3ff" stroke="{INK}" stroke-width="2.5"/>'
    if mood == "angry":
        extra += f'<path d="M{R + 26},{ey - 44} l10,0 l-5,9 z M{R + 34},{ey - 52} l0,10 l9,-5 z" fill="#e84a5f" stroke="{INK}" stroke-width="2"/>'
    if mood == "sleeping":
        extra += f'<text x="{R + 24}" y="{ey - 30}" font-family="Hand" font-size="34" fill="{INK}">z</text><text x="{R + 44}" y="{ey - 56}" font-family="Hand" font-size="44" fill="{INK}">Z</text>'
    return brows + eyes + mouth + extra


# ---------------------------------------------------------------- people

HAIR = {
    # style: (behind the head, over the head)
    "short": ("", "M-57,-100 C-64,-168 64,-168 57,-100 Q44,-130 6,-134 Q-34,-128 -57,-100 Z"),
    "messy": ("", "M-58,-96 L-66,-120 L-50,-122 C-56,-170 46,-178 56,-130 L70,-126 L58,-98 Q46,-124 20,-128 L10,-112 L0,-130 "
                  "Q-30,-128 -44,-112 Z"),
    "bun": ("M-22,-150 a24,24 0 1,1 44,0 a24,24 0 1,1 -44,0 Z", "M-57,-96 C-62,-166 62,-166 57,-96 Q50,-130 0,-136 Q-50,-130 -57,-96 Z"),
    "ponytail": ("M40,-140 C96,-150 104,-80 86,-30 C80,-60 70,-100 40,-118 Z",
                 "M-57,-98 C-62,-168 62,-168 57,-98 Q30,-136 -10,-128 Q-40,-126 -57,-98 Z"),
    "big": ("M-82,-60 C-110,-150 -40,-196 0,-190 C40,-196 110,-150 82,-60 C84,-30 60,-20 52,-40 L-52,-40 C-60,-20 -84,-30 -82,-60 Z",
            "M-58,-94 C-64,-170 64,-170 58,-94 Q40,-140 -6,-130 Q-40,-130 -58,-94 Z"),
    "long": ("M-62,-100 C-70,-40 -64,0 -48,10 L48,10 C64,0 70,-40 62,-100 Z",
             "M-58,-96 C-64,-170 64,-170 58,-96 Q20,-140 -20,-122 Q-44,-112 -58,-96 Z"),
    "curly": ("", "".join(f"M{x},{y} a{r},{r} 0 1,1 0.1,0 Z " for x, y, r in
                          ((-48, -116, 18), (-30, -140, 20), (-4, -152, 21), (24, -146, 20), (46, -124, 18), (-56, -94, 12), (56, -96, 12)))),
    "bald": ("", ""),
    "cap": ("", "M-60,-104 C-62,-170 62,-170 60,-104 Z M50,-108 Q96,-110 102,-96 L48,-96 Z"),
}


def person(x, y, s=1.0, mood="neutral", flip=False, talking=False, prop=None, look=None, blink=False):
    from strips.art import prop_svg
    lk = {"skin": "#e9b48c", "hair": "short", "hair_color": "#3a2a20", "top": "#6b8fd6", "legs": "#3b4158",
          "body": "slim", "glasses": False, "eyebags": False, "tie": None, "lipstick": None, "beard": None,
          "outfit": None, **(look or {})}
    sx = -s if flip else s
    hw = 58 if lk["body"] == "round" else 46
    skin, top, hc = lk["skin"], lk["top"], lk["hair_color"]
    back, front = HAIR[lk["hair"]]
    pose = ("up" if mood in ("happy", "laughing", "proud", "love") else "hips" if mood in ("angry", "smug") else
            "face" if mood in ("panic", "shocked", "crying") else "down")
    arms = {
        "down": ((-hw, -24, -hw - 26, 10, -hw - 14, 46), (hw, -24, hw + 26, 10, hw + 14, 46)),
        "up": ((-hw, -24, -hw - 34, -46, -hw - 22, -88), (hw, -24, hw + 34, -46, hw + 22, -88)),
        "hips": ((-hw, -24, -hw - 40, 6, -hw + 6, 34), (hw, -24, hw + 40, 6, hw - 6, 34)),
        "face": ((-hw, -24, -hw - 30, -30, -40, -72), (hw, -24, hw + 30, -30, 40, -72)),
    }[pose]
    if prop:
        arms = (arms[0], (hw, -24, hw + 36, 0, hw + 40, 8))
    arm_svg = "".join(f'<path d="M{a},{b} Q{c},{d} {e},{f}" stroke="{INK}" stroke-width="24" fill="none" stroke-linecap="round"/>'
                      f'<path d="M{a},{b} Q{c},{d} {e},{f}" stroke="{top}" stroke-width="13" fill="none" stroke-linecap="round"/>'
                      f'<circle cx="{e}" cy="{f}" r="11" fill="{skin}" stroke="{INK}" stroke-width="4.5"/>' for a, b, c, d, e, f in arms)
    torso = (f'M{-hw},-18 Q{-hw},-38 {-hw + 18},-40 L{hw - 18},-40 Q{hw},-38 {hw},-18 L{hw + 6},72 Q0,82 {-hw - 6},72 Z')
    o = lk["outfit"]
    outfit = ""
    if o == "cardigan":
        outfit = (f'<path d="M-8,-38 L-14,74 M8,-38 L14,74" stroke="{INK}" stroke-width="4"/>'
                  + "".join(f'<circle cx="-18" cy="{cy}" r="4" fill="#fff4dc" stroke="{INK}" stroke-width="2"/>' for cy in (0, 24, 48)))
    elif o == "blazer":
        outfit = (f'<path d="M-30,-40 L0,20 L30,-40 Z" fill="#fff" stroke="{INK}" stroke-width="4"/>'
                  f'<path d="M-30,-40 L-6,8 L-20,-4 Z M30,-40 L6,8 L20,-4 Z" fill="{top}" stroke="{INK}" stroke-width="4"/>')
    elif o == "apron":
        outfit = f'<path d="M-30,-14 L30,-14 L36,72 Q0,78 -36,72 Z" fill="#7a5a3a" stroke="{INK}" stroke-width="4"/><path d="M-30,-14 L-40,-40 M30,-14 L40,-40" stroke="{INK}" stroke-width="4"/>'
    elif o == "labcoat":
        outfit = f'<path d="{torso}" fill="#f7f9ff" stroke="{INK}" stroke-width="5"/><path d="M0,-40 L0,76 M-16,-40 L0,4 L16,-40" stroke="{INK}" stroke-width="4" fill="none"/>'
    elif o == "hoodie":
        outfit = f'<path d="M-30,-40 Q0,-10 30,-40" stroke="{INK}" stroke-width="4" fill="none"/><path d="M-26,30 L26,30 L22,56 L-22,56 Z" fill="none" stroke="{INK}" stroke-width="4"/>'
    elif o == "tank":
        outfit = f'<path d="M{-hw},-18 Q{-hw},-38 {-hw + 18},-40 L-20,-40 L-20,-18 Z M{hw},-18 Q{hw},-38 {hw - 18},-40 L20,-40 L20,-18 Z" fill="{skin}" stroke="{INK}" stroke-width="4"/>'
    tie = (f'<path d="M-8,-38 L8,-38 L5,-28 L11,36 L0,48 L-11,36 L-5,-28 Z" fill="{lk["tie"]}" stroke="{INK}" stroke-width="3.5"/>'
           f'<path d="M-6,-30 L6,-22" stroke="#00000033" stroke-width="3"/>' if lk["tie"] else "")
    legs = (f'<rect x="-34" y="58" width="26" height="60" rx="8" fill="{lk["legs"]}" {STROKE}/>'
            f'<rect x="8" y="58" width="26" height="60" rx="8" fill="{lk["legs"]}" {STROKE}/>'
            f'<ellipse cx="-24" cy="120" rx="20" ry="9" fill="#2a2730" {STROKE}/><ellipse cx="24" cy="120" rx="20" ry="9" fill="#2a2730" {STROKE}/>')
    glasses = (f'<circle cx="-21" cy="-96" r="17" fill="#ffffff22" stroke="{INK}" stroke-width="4.5"/>'
               f'<circle cx="21" cy="-96" r="17" fill="#ffffff22" stroke="{INK}" stroke-width="4.5"/><path d="M-4,-98 Q0,-102 4,-98" stroke="{INK}" stroke-width="4" fill="none"/>'
               if lk["glasses"] else "")
    bags = ('<path d="M-31,-82 Q-21,-74 -11,-82 M11,-82 Q21,-74 31,-82" stroke="#8a6a8f" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
            '<path d="M-30,-77 Q-21,-71 -12,-77 M12,-77 Q21,-71 30,-77" stroke="#8a6a8f" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            if lk["eyebags"] else "")
    beard = (f'<path d="M-50,-90 Q-52,-40 0,-34 Q52,-40 50,-90 Q40,-56 0,-54 Q-40,-56 -50,-90 Z" fill="{lk["beard"]}" stroke="{INK}" stroke-width="4"/>'
             if lk["beard"] else "")
    lips = (f'<path d="M-12,-66 Q0,-58 12,-66 Q0,-70 -12,-66 Z" fill="{lk["lipstick"]}"/>' if lk["lipstick"] and not talking and mood in ("neutral", "smug", "deadpan", "tired", "scheming") else "")
    head_pre = f'<path d="{back}" fill="{hc}" {STROKE}/>' if back else ""
    hair_front = f'<path d="{front}" fill="{hc if lk["hair"] != "cap" else lk.get("cap_color", "#e84a5f")}" {STROKE}/>' if front else ""
    if lk["hair"] == "bald":
        hair_front = '<path d="M-30,-140 Q-10,-152 14,-148" stroke="#ffffff88" stroke-width="7" fill="none" stroke-linecap="round"/>'
    held = prop_svg(prop, hw + 46, -6, 0.42) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="126" rx="70" ry="11" fill="#000" opacity="0.12"/>
  {legs}
  <path d="{torso}" fill="{top}" {STROKE}/>{outfit}{tie}
  <rect x="-11" y="-52" width="22" height="16" fill="{skin}" stroke="{INK}" stroke-width="4"/>
  {head_pre}
  <circle cx="-54" cy="-92" r="11" fill="{skin}" {STROKE}/><circle cx="54" cy="-92" r="11" fill="{skin}" {STROKE}/>
  <circle cx="0" cy="-98" r="56" fill="{skin}" {STROKE}/>
  <ellipse cx="-36" cy="-72" rx="10" ry="6" fill="#ff8a9a" opacity="0.45"/><ellipse cx="36" cy="-72" rx="10" ry="6" fill="#ff8a9a" opacity="0.45"/>
  {beard}{hair_front}{bags}
  {face(mood, talking, blink=blink)}{lips}{glasses}
  {arm_svg}{held}
</g>'''


# ---------------------------------------------------------------- animals

def dog(x, y, s=1.0, mood="happy", flip=False, talking=False, prop=None, blink=False):
    from strips.art import prop_svg
    sx = -s if flip else s
    fur, dark, snout = "#e8b04a", "#c98a2e", "#f6d9a0"
    tail = ("M50,96 C110,90 120,30 104,4" if mood in ("happy", "laughing", "love", "proud", "scheming")
            else "M50,110 C90,120 120,120 128,104")
    tongue = (f'<path d="M-9,-24 Q-10,-6 0,-4 Q10,-6 9,-24 Z" fill="#ff7a8a" stroke="{INK}" stroke-width="3.5"/>'
              if mood in ("happy", "laughing", "love", "proud") and not talking else "")
    ears_dn = mood in ("sad", "crying", "tired", "sleeping", "deadpan")
    ear = lambda side: (f'<path d="M{side * 40},-104 C{side * 80},-110 {side * 92},{-40 if ears_dn else -60} {side * 70},{-14 if ears_dn else -36} '
                        f'C{side * 56},{-24 if ears_dn else -50} {side * 50},-70 {side * 34},-86 Z" fill="{dark}" {STROKE}/>')
    held = prop_svg(prop, 0, 30, 0.38) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="126" rx="76" ry="11" fill="#000" opacity="0.12"/>
  <path d="{tail}" stroke="{INK}" stroke-width="24" fill="none" stroke-linecap="round"/><path d="{tail}" stroke="{fur}" stroke-width="14" fill="none" stroke-linecap="round"/>
  <path d="M-62,124 C-72,40 -40,-10 0,-10 C40,-10 72,40 62,124 Z" fill="{fur}" {STROKE}/>
  <path d="M-26,40 C-30,0 30,0 26,40 L22,120 L-22,120 Z" fill="{snout}"/>
  <ellipse cx="-30" cy="118" rx="22" ry="12" fill="{fur}" {STROKE}/><ellipse cx="30" cy="118" rx="22" ry="12" fill="{fur}" {STROKE}/>
  <path d="M-46,-6 Q0,14 46,-6" stroke="#d64545" stroke-width="12" fill="none" stroke-linecap="round"/>
  <circle cx="0" cy="10" r="9" fill="#ffd166" stroke="{INK}" stroke-width="3"/>
  <circle cx="0" cy="-62" r="58" fill="{fur}" {STROKE}/>
  {ear(-1)}{ear(1)}
  <ellipse cx="0" cy="-38" rx="32" ry="24" fill="{snout}" stroke="{INK}" stroke-width="4"/>
  <ellipse cx="0" cy="-52" rx="11" ry="8" fill="{INK}"/>
  {tongue}
  {face(mood, talking, ex=24, ey=-78, my=-30, blink=blink)}
  {held}
</g>'''


def pigeon(x, y, s=1.0, mood="neutral", flip=False, talking=False, prop=None, blink=False):
    from strips.art import prop_svg
    sx = -s if flip else s
    body, head, wing = "#a3abbd", "#8b93a8", "#7c8499"
    beak = (f'<path d="M-9,-44 L9,-44 L0,-30 Z M-8,-28 L8,-28 L0,-18 Z" fill="#e8a33d" stroke="{INK}" stroke-width="3"/>' if talking
            else f'<path d="M-10,-44 L10,-44 L0,-24 Z" fill="#e8a33d" stroke="{INK}" stroke-width="3"/>')
    wings = ("M-58,10 C-110,-20 -120,-60 -100,-80 C-90,-40 -70,-20 -50,-14" if mood in ("happy", "laughing", "proud", "shocked", "panic")
             else "M-58,0 C-80,30 -78,80 -46,100 C-60,60 -56,30 -40,10")
    held = prop_svg(prop, 70, 40, 0.36) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="126" rx="56" ry="10" fill="#000" opacity="0.12"/>
  <path d="M-14,96 L-18,122 M-18,122 L-30,124 M-18,122 L-8,124 M14,96 L18,122 M18,122 L30,124 M18,122 L8,124" stroke="#e98a9c" stroke-width="6" stroke-linecap="round"/>
  <ellipse cx="0" cy="40" rx="62" ry="68" fill="{body}" {STROKE}/>
  <path d="M-40,40 Q0,56 40,40 M-36,58 Q0,74 36,58" stroke="{wing}" stroke-width="6" fill="none"/>
  <path d="{wings}" fill="{wing}" {STROKE}/><path transform="scale(-1,1)" d="{wings}" fill="{wing}" {STROKE}/>
  <path d="M-38,-22 Q0,4 38,-22 L34,-2 Q0,18 -34,-2 Z" fill="#5fb8a5" stroke="{INK}" stroke-width="4"/>
  <path d="M-30,-10 Q0,8 30,-10" stroke="#8e6bbf" stroke-width="5" fill="none"/>
  <circle cx="0" cy="-58" r="44" fill="{head}" {STROKE}/>
  <path d="M-46,-74 C-46,-118 46,-118 46,-74 Q0,-90 -46,-74 Z" fill="#4b4f5c" {STROKE}/><path d="M36,-80 Q66,-80 70,-70 L34,-72 Z" fill="#4b4f5c" stroke="{INK}" stroke-width="4"/>
  {face(mood, talking, ex=18, ey=-62, my=-14, white="#f2a33a", blink=blink)}
  {beak}{held}
</g>'''


def reaper(x, y, s=1.0, mood="neutral", flip=False, talking=False, prop=None, blink=False):
    """Mort: a small, polite grim reaper on a temp contract. Robe, hood, staff badge, a scythe a size too big."""
    from strips.art import prop_svg
    sx = -s if flip else s
    robe, shade, bone = "#3a3350", "#2a2540", "#f4f1e8"
    up = mood in ("happy", "laughing", "proud", "love", "panic", "shocked")
    arm = "M38,-20 Q70,-40 74,-70" if up else "M38,-20 Q66,-6 70,22"
    hx, hy = (74, -70) if up else (70, 22)
    held = prop_svg(prop, 80, 10, 0.4) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="126" rx="72" ry="11" fill="#000" opacity="0.12"/>
  <path d="M-78,118 L-78,-150" stroke="{INK}" stroke-width="13" stroke-linecap="round"/><path d="M-78,118 L-78,-150" stroke="#8a6a4a" stroke-width="6" stroke-linecap="round"/>
  <path d="M-80,-150 C-40,-176 10,-166 34,-128 C4,-150 -40,-150 -78,-134 Z" fill="#dfe6f2" {STROKE}/>
  <path d="M-50,-30 Q-56,60 -70,122 Q-36,112 -18,124 Q0,112 18,124 Q36,112 70,122 Q56,60 50,-30 Z" fill="{robe}" {STROKE}/>
  <path d="M-12,-20 Q-16,60 -18,118 M14,-20 Q20,60 22,116" stroke="{shade}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path d="M-38,-20 Q-70,-6 -74,24" stroke="{INK}" stroke-width="26" fill="none" stroke-linecap="round"/><path d="M-38,-20 Q-70,-6 -74,24" stroke="{robe}" stroke-width="15" fill="none" stroke-linecap="round"/>
  <circle cx="-76" cy="26" r="10" fill="{bone}" stroke="{INK}" stroke-width="4.5"/>
  <path d="{arm}" stroke="{INK}" stroke-width="26" fill="none" stroke-linecap="round"/><path d="{arm}" stroke="{robe}" stroke-width="15" fill="none" stroke-linecap="round"/>
  <circle cx="{hx}" cy="{hy}" r="10" fill="{bone}" stroke="{INK}" stroke-width="4.5"/>
  <path d="M-6,-34 L10,20" stroke="#e84a5f" stroke-width="4"/><rect x="0" y="16" width="30" height="38" rx="4" fill="#fffdf2" stroke="{INK}" stroke-width="3.5"/>
  <circle cx="15" cy="29" r="6" fill="{robe}"/><path d="M6,42 L24,42 M6,48 L20,48" stroke="{INK}" stroke-width="2.5"/>
  <path d="M-66,-76 C-74,-150 -30,-178 4,-176 C44,-174 76,-140 64,-74 C56,-34 -56,-34 -66,-76 Z" fill="{robe}" {STROKE}/>
  <path d="M4,-176 Q30,-196 40,-170" fill="{robe}" {STROKE}/>
  <ellipse cx="0" cy="-92" rx="46" ry="48" fill="{shade}"/>
  <ellipse cx="0" cy="-88" rx="40" ry="42" fill="{bone}" stroke="{INK}" stroke-width="4.5"/>
  <ellipse cx="-26" cy="-70" rx="8" ry="5" fill="#b9a7d6" opacity="0.6"/><ellipse cx="26" cy="-70" rx="8" ry="5" fill="#b9a7d6" opacity="0.6"/>
  {face(mood, talking, ex=16, ey=-94, my=-66, blink=blink)}
  {held}
</g>'''


def plant(x, y, s=1.0, mood="neutral", flip=False, talking=False, prop=None, blink=False):
    """Fern: a houseplant with a face on its pot. Leaves stand up when things go well and droop when they do not."""
    from strips.art import prop_svg
    sx = -s if flip else s
    droop = mood in ("sad", "crying", "tired", "sleeping", "deadpan", "panic")
    green, dark = ("#7fae5a", "#5d8a3f") if droop else ("#5fc26b", "#3f9a52")
    if droop:
        leaves = ("M0,26 C-20,-20 -70,-30 -96,10 C-70,0 -40,6 0,26 Z", "M0,26 C20,-20 70,-30 96,10 C70,0 40,6 0,26 Z",
                  "M0,26 C-30,-50 -70,-70 -100,-50 C-70,-44 -34,-20 0,26 Z", "M0,26 C30,-50 70,-70 100,-50 C70,-44 34,-20 0,26 Z",
                  "M0,26 C-12,-30 -10,-70 14,-84 C16,-50 12,-10 0,26 Z")
    else:
        leaves = ("M0,26 C-50,0 -90,-40 -92,-88 C-56,-70 -18,-30 0,26 Z", "M0,26 C50,0 90,-40 92,-88 C56,-70 18,-30 0,26 Z",
                  "M0,26 C-40,-40 -50,-100 -34,-138 C-10,-100 -2,-40 0,26 Z", "M0,26 C40,-40 50,-100 34,-138 C10,-100 2,-40 0,26 Z",
                  "M0,26 C-16,-50 -12,-120 0,-156 C12,-120 16,-50 0,26 Z")
    lv = "".join(f'<path d="{d}" fill="{dark if i < 2 else green}" {STROKE}/>' for i, d in enumerate(leaves))
    held = prop_svg(prop, 86, 80, 0.36) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="126" rx="70" ry="11" fill="#000" opacity="0.12"/>
  {lv}
  <path d="M-56,36 L56,36 L42,118 Q0,128 -42,118 Z" fill="#d9825b" {STROKE}/>
  <rect x="-64" y="18" width="128" height="24" rx="8" fill="#e89a72" {STROKE}/>
  <ellipse cx="-32" cy="88" rx="9" ry="5" fill="#ff8a9a" opacity="0.5"/><ellipse cx="32" cy="88" rx="9" ry="5" fill="#ff8a9a" opacity="0.5"/>
  {face(mood, talking, ex=18, ey=70, my=96, blink=blink)}
  {held}
</g>'''


# ---------------------------------------------------------------- the roster

LOOKS = {
    "Dev": {"skin": "#c68a5e", "hair": "messy", "hair_color": "#2a1f1a", "top": "#7fa4e0", "tie": "#d64545", "eyebags": True},
    "Mira": {"skin": "#f1c7a5", "hair": "ponytail", "hair_color": "#c0582b", "top": "#f5c542", "glasses": True, "legs": "#2f3542"},
    "Nana June": {"skin": "#f3d2b8", "hair": "bun", "hair_color": "#e6e6ee", "top": "#b56fa8", "glasses": True, "body": "round",
                  "outfit": "cardigan", "legs": "#6b5a7a", "scale": 0.92},
    "Brenda": {"skin": "#e0a77e", "hair": "big", "hair_color": "#8a4b2a", "top": "#2f3e66", "outfit": "blazer", "body": "round",
               "lipstick": "#c43a5a"},
    "Ravi": {"skin": "#b97a56", "hair": "curly", "hair_color": "#1f1a17", "top": "#2f2f38", "outfit": "hoodie", "glasses": True,
             "legs": "#5a6078"},
    "Lottie": {"skin": "#e2b08a", "hair": "ponytail", "hair_color": "#5a3825", "top": "#ff7aa8", "legs": "#6b8fd6", "scale": 0.7},
    "Mr. Okafor": {"skin": "#7a4a2e", "hair": "bald", "hair_color": "#ddd", "top": "#8a6d3b", "outfit": "blazer", "tie": "#2e8b57",
                   "body": "round", "beard": "#8f8f96", "legs": "#3a3226"},
}
EXTRA_LOOKS = {
    "young_man": {"skin": "#d9a27a", "hair": "short", "hair_color": "#1f1a17", "top": "#4caf7d", "outfit": "hoodie"},
    "young_woman": {"skin": "#8d5a3b", "hair": "curly", "hair_color": "#1f1a17", "top": "#e84a5f"},
    "teen": {"skin": "#f0c9a4", "hair": "long", "hair_color": "#e3c06b", "top": "#8e7cc3", "outfit": "hoodie", "scale": 0.88},
    "kid": {"skin": "#c98d64", "hair": "curly", "hair_color": "#2a1f1a", "top": "#ff9f43", "scale": 0.72},
    "old_man": {"skin": "#efc8a8", "hair": "bald", "hair_color": "#ddd", "top": "#8a9a5b", "beard": "#e6e6ee", "body": "round", "outfit": "cardigan"},
    "doctor": {"skin": "#b8774f", "hair": "short", "hair_color": "#1f1a17", "top": "#9fd3ff", "outfit": "labcoat", "glasses": True},
    "barista": {"skin": "#f0c9a4", "hair": "cap", "hair_color": "#3a2a20", "cap_color": "#4caf7d", "top": "#e9eef7", "outfit": "apron"},
    "businessman": {"skin": "#e9b48c", "hair": "short", "hair_color": "#6b6b6b", "top": "#3b4158", "outfit": "blazer", "tie": "#7b6cf6", "body": "round"},
    "delivery": {"skin": "#a8693f", "hair": "cap", "cap_color": "#f28c28", "top": "#f28c28", "beard": "#2a1f1a"},
    "fitness": {"skin": "#d9a27a", "hair": "short", "hair_color": "#e3c06b", "top": "#e84a5f", "outfit": "tank", "body": "round"},
}

ENSEMBLE = {
    "Dev": "Dev: 31, works in an open-plan office, permanently exhausted, runs on coffee and spite. Quietly losing it, "
           "replies to chaos with flat, devastating honesty. Says what everyone thinks in meetings, but only in his head, "
           "until he doesn't.",
    "Mira": "Mira: Dev's roommate and coworker. A relentless self-improver with a 5am routine, a vision board, a "
            "productivity app for everything. Confidently wrong, unstoppable, weaponises positivity.",
    "Nana June": "Nana June: Mira's 84-year-old grandmother. Sweet face, cardigan, savage. Jokes casually about her own "
                 "mortality, the will, and outliving everyone. Treats modern life with total, cheerful contempt.",
    "Brenda": "Brenda: Dev and Mira's manager. Lives in corporate speak (circle back, per my last email, we're a "
              "family here). Means every word. Oblivious to how bleak she sounds.",
    "Biscuit": "Biscuit: a golden retriever. Pure heart, zero brain. Loves everyone, misunderstands everything, takes "
               "every word literally. The wholesome punchline, or the accidental savage one.",
    "Gus": "Gus: a city pigeon in a flat cap. A small-time hustler running schemes on the sidewalk and in the park. "
           "Talks like a con artist, sells things that are clearly bread.",
    "Ravi": "Ravi: a startup founder in a hoodie. Has pivoted nine times, calls every setback a learning, and is "
            "always one funding round from changing the world. Pitches at funerals. Believes his own deck.",
    "Lottie": "Lottie: Dev's 7-year-old niece. Asks the question no adult wants asked, then waits. Brutally honest, "
              "completely sincere, and unbeatable at negotiating bedtime.",
    "Mr. Okafor": "Mr. Okafor: the landlord. Warm, fatherly, delighted to see you. Delivers rent increases, new fees "
                  "and 'improvements' as if handing out gifts. Never raises his voice. Never fixes the boiler.",
    "Mort": "Mort: a small grim reaper on a temp contract, staff badge and all. Polite, overworked, behind on his "
            "quota, hates the paperwork. Treats death as a customer service job and makes awkward small talk.",
    "Fern": "Fern: the office houseplant, a face on a terracotta pot. Has watched everything. Passive-aggressive "
            "about being watered. Dry one-liners, long memory. Cannot move, so it sits wherever the scene is.",
    "Pim": "Pim: a small, timid, endlessly optimistic ghost, bad at being scary. Best on warm days.",
    "Soot": "Soot: Pim's deadpan black cat. Says two words, wins. Best on warm days.",
}
GUESTS = {"Pim", "Soot"}


def drawers():
    """name -> (draw function, head top offset, base offset used when standing behind a counter)."""
    d = {n: (partial(person, look=lk), -158, 34, lk.get("scale", 1.0)) for n, lk in LOOKS.items()}
    d["Biscuit"] = (dog, -124, 60, 0.9)
    d["Gus"] = (pigeon, -112, 124, 0.8)
    d["Mort"] = (reaper, -178, 40, 0.86)
    d["Fern"] = (plant, -150, 124, 0.82)
    return d


def extra_drawer(look):
    return partial(person, look=EXTRA_LOOKS.get(look, EXTRA_LOOKS["young_man"]))
