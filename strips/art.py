"""Vector art for Pim (a timid ghost) and Soot (a deadpan black cat).

Everything is drawn here as SVG, so every comic is original artwork. A panel is
512 x 647 units. Characters are placed by position (left, center, right) and
size (small, medium, large); rooms define the floor line and prop spots.
"""
INK = "#1d1a22"
PW, PH = 512, 647
X = {"left": 140, "center": 256, "right": 372, "far_left": 100, "far_right": 412}
SIZE = {"small": 0.72, "medium": 0.95, "large": 1.28}

# ---------------------------------------------------------------- characters

GHOST_MOODS = ["happy", "excited", "nervous", "sad", "surprised", "proud", "sleepy", "love", "peek", "determined"]
CAT_MOODS = ["flat", "annoyed", "smug", "surprised", "sleeping", "eating", "pleased"]


def ghost(x, y, s=1.0, mood="happy", flip=False, talking=False, prop=None):
    sx = -s if flip else s
    E = lambda cx: f'<ellipse cx="{cx}" cy="-48" rx="10" ry="15" fill="{INK}"/><circle cx="{cx + 3}" cy="-53" r="4" fill="#fff"/>'
    eyes = {
        "happy": E(-26) + E(26),
        "proud": f'<path d="M-38,-46 Q-26,-38 -14,-46" stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round"/>'
                 f'<path d="M14,-46 Q26,-38 38,-46" stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round"/>',
        "excited": f'<path d="M-38,-44 Q-26,-62 -14,-44" stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round"/>'
                   f'<path d="M14,-44 Q26,-62 38,-44" stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round"/>',
        "nervous": f'<ellipse cx="-26" cy="-48" rx="12" ry="16" fill="#fff" stroke="{INK}" stroke-width="5"/><circle cx="-24" cy="-46" r="5" fill="{INK}"/>'
                   f'<ellipse cx="26" cy="-48" rx="12" ry="16" fill="#fff" stroke="{INK}" stroke-width="5"/><circle cx="28" cy="-46" r="5" fill="{INK}"/>'
                   f'<path d="M58,-86 Q70,-66 58,-58 Q46,-66 58,-86 Z" fill="#9fd3ff" stroke="{INK}" stroke-width="3"/>',
        "sad": E(-26) + E(26) + f'<path d="M-40,-70 L-14,-62 M40,-70 L14,-62" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
               f'<path d="M-30,-30 Q-34,-16 -30,-10 Q-26,-16 -30,-30 Z" fill="#9fd3ff" stroke="{INK}" stroke-width="2.5"/>',
        "surprised": f'<circle cx="-26" cy="-50" r="14" fill="#fff" stroke="{INK}" stroke-width="5"/><circle cx="-26" cy="-50" r="5" fill="{INK}"/>'
                     f'<circle cx="26" cy="-50" r="14" fill="#fff" stroke="{INK}" stroke-width="5"/><circle cx="26" cy="-50" r="5" fill="{INK}"/>',
        "sleepy": f'<path d="M-38,-46 L-14,-46 M14,-46 L38,-46" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>',
        "love": ''.join(f'<path transform="translate({cx},-50) scale(0.9)" d="M0,10 C-18,-4 -14,-20 -4,-18 C0,-17 0,-14 0,-12 C0,-14 0,-17 4,-18 C14,-20 18,-4 0,10 Z" fill="#ff5a7a" stroke="{INK}" stroke-width="3"/>' for cx in (-26, 26)),
        "peek": f'<ellipse cx="-26" cy="-48" rx="12" ry="17" fill="{INK}"/><ellipse cx="26" cy="-48" rx="12" ry="17" fill="{INK}"/>'
                f'<circle cx="-22" cy="-54" r="5" fill="#fff"/><circle cx="30" cy="-54" r="5" fill="#fff"/>',
        "determined": E(-26) + E(26) + f'<path d="M-42,-72 L-12,-64 M42,-72 L12,-64" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>',
    }[mood]
    closed = {
        "happy": f'<path d="M-14,-14 Q0,0 14,-14" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>',
        "proud": f'<path d="M-16,-16 Q0,2 16,-16" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>',
        "excited": f'<path d="M-20,-18 Q0,18 20,-18 Z" fill="{INK}"/><path d="M-10,-2 Q0,8 10,-2 Z" fill="#ff8a9a"/>',
        "nervous": f'<path d="M-16,-12 Q-8,-18 0,-12 Q8,-6 16,-12" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
        "sad": f'<path d="M-12,-6 Q0,-18 12,-6" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>',
        "surprised": f'<ellipse cx="0" cy="-10" rx="9" ry="12" fill="{INK}"/>',
        "sleepy": f'<path d="M-8,-12 L8,-12" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>',
        "love": f'<path d="M-14,-14 Q0,0 14,-14" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>',
        "peek": f'<ellipse cx="0" cy="-10" rx="7" ry="9" fill="{INK}"/>',
        "determined": f'<path d="M-14,-10 L14,-10" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>',
    }[mood]
    mouth = (f'<ellipse cx="0" cy="-10" rx="13" ry="12" fill="{INK}"/><ellipse cx="0" cy="-4" rx="7" ry="4" fill="#ff8a9a"/>'
             if talking and mood not in ("excited",) else closed)
    arms = ('<path d="M-80,10 Q-112,2 -116,-24" /><path d="M80,10 Q110,0 118,-26" />' if mood in ("excited", "proud", "happy", "love", "determined")
            else '<path d="M-80,6 Q-104,24 -100,44" /><path d="M80,6 Q104,24 100,44" />' if mood in ("sad", "sleepy")
            else '<path d="M-78,-4 Q-96,-30 -70,-46" /><path d="M78,-4 Q96,-30 70,-46" />' if mood in ("nervous", "surprised")
            else '<path d="M-80,10 Q-108,14 -112,-6" /><path d="M80,10 Q108,14 112,-6" />')
    held = prop_svg(prop, 118, 10, 0.42) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="150" rx="70" ry="12" fill="#000" opacity="0.10"/>
  <path d="M-82,40 C-86,-70 -48,-122 0,-122 C48,-122 86,-70 82,40 L82,104 Q70,128 54,108 Q40,90 26,110 Q12,130 -2,110 Q-16,90 -30,110
           Q-44,130 -58,110 Q-70,96 -82,108 Z" fill="#fbfbff" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>
  <g stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round">{arms}</g>
  <path d="M-60,-80 Q-40,-108 -6,-112" stroke="#e7e9f5" stroke-width="10" fill="none" stroke-linecap="round"/>
  <ellipse cx="-46" cy="-22" rx="13" ry="7" fill="#ffb3c1"/><ellipse cx="46" cy="-22" rx="13" ry="7" fill="#ffb3c1"/>
  {eyes}{mouth}{held}
</g>'''


def cat(x, y, s=1.0, mood="flat", flip=False, talking=False, prop=None):
    sx = -s if flip else s
    fur = "#2c2a36"
    eye_y = -58
    if mood == "sleeping":
        eyes = f'<path d="M-36,-56 Q-24,-48 -12,-56 M12,-56 Q24,-48 36,-56" stroke="#e8e6f0" stroke-width="4" fill="none" stroke-linecap="round"/>'
    elif mood == "surprised":
        eyes = (f'<circle cx="-24" cy="{eye_y}" r="17" fill="#f4d03f" stroke="{INK}" stroke-width="3"/><circle cx="24" cy="{eye_y}" r="17" fill="#f4d03f" stroke="{INK}" stroke-width="3"/>'
                f'<circle cx="-24" cy="{eye_y}" r="7" fill="{INK}"/><circle cx="24" cy="{eye_y}" r="7" fill="{INK}"/>')
    else:
        eyes = (f'<ellipse cx="-24" cy="{eye_y}" rx="15" ry="14" fill="#f4d03f" stroke="{INK}" stroke-width="3"/>'
                f'<ellipse cx="24" cy="{eye_y}" rx="15" ry="14" fill="#f4d03f" stroke="{INK}" stroke-width="3"/>'
                f'<ellipse cx="-24" cy="-56" rx="3.5" ry="10" fill="{INK}"/><ellipse cx="24" cy="-56" rx="3.5" ry="10" fill="{INK}"/>')
        lid_h = {"flat": 15, "annoyed": 17, "smug": 17, "eating": 15, "pleased": 0}[mood]
        if lid_h:
            eyes += f'<rect x="-44" y="-74" width="88" height="{lid_h}" fill="{fur}"/>'
            eyes += f'<path d="M-42,{-74 + lid_h} L-8,{-74 + lid_h} M8,{-74 + lid_h} L42,{-74 + lid_h}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
        if mood == "annoyed":
            eyes += f'<path d="M-44,-86 L-12,-78 M44,-86 L12,-78" stroke="#e8e6f0" stroke-width="4" stroke-linecap="round"/>'
        if mood == "pleased":
            eyes = (f'<path d="M-38,-56 Q-24,-70 -10,-56 M10,-56 Q24,-70 38,-56" stroke="#f4d03f" stroke-width="6" fill="none" stroke-linecap="round"/>')
    if talking:
        mouth = f'<ellipse cx="0" cy="-19" rx="9" ry="8" fill="#e98a9c" stroke="{INK}" stroke-width="3"/>'
    else:
        mouth = {"smug": '<path d="M-10,-22 Q4,-14 12,-26" stroke="#e8e6f0" stroke-width="4" fill="none" stroke-linecap="round"/>',
                 "eating": f'<ellipse cx="0" cy="-18" rx="11" ry="8" fill="#e98a9c" stroke="{INK}" stroke-width="3"/>',
                 "surprised": f'<ellipse cx="0" cy="-18" rx="7" ry="8" fill="#e98a9c" stroke="{INK}" stroke-width="3"/>',
                 "pleased": '<path d="M-10,-22 Q-5,-16 0,-22 Q5,-16 10,-22" stroke="#e8e6f0" stroke-width="4" fill="none" stroke-linecap="round"/>',
                 }.get(mood, '<path d="M-9,-20 L9,-20" stroke="#e8e6f0" stroke-width="4" fill="none" stroke-linecap="round"/>')
    zzz = (f'<text x="56" y="-120" font-family="Hand" font-size="34" fill="{INK}">z</text>'
           f'<text x="78" y="-146" font-family="Hand" font-size="44" fill="{INK}">Z</text>' if mood == "sleeping" else "")
    held = prop_svg(prop, 96, 70, 0.4) if prop else ""
    return f'''<g transform="translate({x},{y}) scale({sx},{s})">
  <ellipse cx="0" cy="128" rx="78" ry="12" fill="#000" opacity="0.10"/>
  <path d="M58,110 C120,108 124,40 96,20 C84,12 76,26 88,34 C104,48 98,88 56,92" fill="{fur}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
  <path d="M-60,124 C-74,40 -44,-6 0,-6 C44,-6 74,40 60,124 Z" fill="{fur}" stroke="{INK}" stroke-width="6"/>
  <path d="M-28,124 C-30,104 -18,96 -10,104 M28,124 C30,104 18,96 10,104" stroke="#45424f" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path d="M-50,-78 L-58,-136 L-14,-100 Z" fill="{fur}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
  <path d="M50,-78 L58,-136 L14,-100 Z" fill="{fur}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
  <path d="M-46,-90 L-50,-120 L-26,-100 Z M46,-90 L50,-120 L26,-100 Z" fill="#e98a9c"/>
  <circle cx="0" cy="-54" r="60" fill="{fur}" stroke="{INK}" stroke-width="6"/>
  {eyes}
  <path d="M-5,-36 L5,-36 L0,-30 Z" fill="#e98a9c"/>
  {mouth}
  <path d="M-34,-34 L-74,-40 M-34,-28 L-72,-24 M34,-34 L74,-40 M34,-28 L72,-24" stroke="#cfcbe0" stroke-width="2.5" stroke-linecap="round"/>
  {zzz}{held}
</g>'''


CHARACTERS = {
    "Pim": {"draw": ghost, "moods": GHOST_MOODS, "head": -125, "float": 46, "base": 0, "behind": 80},
    "Soot": {"draw": cat, "moods": CAT_MOODS, "head": -140, "float": 0, "base": 124, "behind": 94},
}
# Shared moods map onto Pim's and Soot's own faces, so one mood list fits the whole cast.
TO_GHOST = {"neutral": "happy", "laughing": "excited", "angry": "determined", "shocked": "surprised", "smug": "proud",
            "tired": "sleepy", "panic": "nervous", "deadpan": "happy", "scheming": "determined", "sleeping": "sleepy",
            "crying": "sad"}
TO_CAT = {"neutral": "flat", "happy": "pleased", "laughing": "pleased", "angry": "annoyed", "shocked": "surprised",
          "sad": "flat", "tired": "flat", "panic": "surprised", "deadpan": "flat", "scheming": "smug", "love": "pleased",
          "proud": "smug", "crying": "flat"}
_ghost, _cat = ghost, cat
ghost = lambda x, y, s=1.0, mood="happy", *a, **k: _ghost(x, y, s, mood if mood in GHOST_MOODS else TO_GHOST.get(mood, "happy"), *a, **k)
cat = lambda x, y, s=1.0, mood="flat", *a, **k: _cat(x, y, s, mood if mood in CAT_MOODS else TO_CAT.get(mood, "flat"), *a, **k)
CHARACTERS["Pim"]["draw"], CHARACTERS["Soot"]["draw"] = ghost, cat

# ---------------------------------------------------------------- props

def prop_svg(name, x, y, s=1.0):
    k = f'stroke="{INK}" stroke-width="6" stroke-linejoin="round"'
    body = {
        "turkey": f'''<ellipse cx="0" cy="22" rx="150" ry="30" fill="#f7f7fb" {k}/>
  <path d="M-70,-10 C-130,-30 -150,-70 -122,-86 C-104,-96 -90,-80 -96,-62" fill="#a85a26" {k}/>
  <path d="M70,-10 C130,-30 150,-70 122,-86 C104,-96 90,-80 96,-62" fill="#a85a26" {k}/>
  <circle cx="-124" cy="-92" r="11" fill="#fff" {k}/><circle cx="124" cy="-92" r="11" fill="#fff" {k}/>
  <path d="M-110,14 C-120,-70 -60,-112 0,-112 C60,-112 120,-70 110,14 Z" fill="#c06a2b" {k}/>
  <path d="M-62,-78 C-30,-98 20,-98 46,-84" stroke="#e39a52" stroke-width="12" fill="none" stroke-linecap="round"/>''',
        "pie": f'''<ellipse cx="0" cy="10" rx="120" ry="32" fill="#f2c27b" {k}/><path d="M-120,10 L-108,40 Q0,70 108,40 L120,10" fill="#d99a4e" {k}/>
  <ellipse cx="0" cy="4" rx="96" ry="22" fill="#e07b39"/><path d="M-70,0 Q-40,-10 -10,0 M10,4 Q40,-6 70,4" stroke="#f6d39a" stroke-width="6" fill="none"/>''',
        "mug": f'''<path d="M-50,-60 L50,-60 L42,40 Q0,52 -42,40 Z" fill="#f08a5d" {k}/><path d="M50,-40 Q90,-36 84,0 Q78,24 44,20" fill="none" {k}/>
  <path d="M-20,-80 Q-30,-100 -16,-118 M10,-80 Q0,-100 14,-118" stroke="#b8b4c8" stroke-width="5" fill="none" stroke-linecap="round"/>''',
        "laptop": f'''<path d="M-100,-110 L100,-110 L100,10 L-100,10 Z" fill="#4b5263" {k}/><rect x="-86" y="-96" width="172" height="92" fill="#9fd3ff"/>
  <path d="M-130,10 L130,10 L150,34 L-150,34 Z" fill="#c9cdd8" {k}/>''',
        "phone": f'''<rect x="-34" y="-64" width="68" height="128" rx="12" fill="#2f3542" {k}/><rect x="-26" y="-50" width="52" height="96" rx="4" fill="#9fd3ff"/>''',
        "book": f'''<path d="M-90,-40 Q-45,-60 0,-40 Q45,-60 90,-40 L90,40 Q45,20 0,40 Q-45,20 -90,40 Z" fill="#fffdf2" {k}/>
  <path d="M0,-40 L0,40" {k}/><path d="M-70,-20 L-20,-24 M-70,-4 L-20,-8 M20,-24 L70,-20 M20,-8 L70,-4" stroke="#b8b4c8" stroke-width="4"/>''',
        "pumpkin": f'''<ellipse cx="0" cy="0" rx="90" ry="70" fill="#f28c28" {k}/><path d="M-30,-66 Q-50,0 -30,66 M30,-66 Q50,0 30,66" stroke="{INK}" stroke-width="4" fill="none"/>
  <path d="M-6,-68 Q-4,-96 16,-104" stroke="#5a7d2b" stroke-width="12" fill="none" stroke-linecap="round"/>''',
        "gift": f'''<rect x="-70" y="-60" width="140" height="110" fill="#e84a5f" {k}/><rect x="-14" y="-60" width="28" height="110" fill="#ffd166"/>
  <path d="M0,-60 Q-50,-110 -40,-70 Q-30,-56 0,-60 Q30,-56 40,-70 Q50,-110 0,-60" fill="#ffd166" {k}/>''',
        "plant": f'''<path d="M-50,0 L50,0 L38,90 L-38,90 Z" fill="#d97c4a" {k}/>
  <path d="M0,0 Q-60,-60 -40,-130 Q0,-80 0,0 Q20,-110 60,-120 Q50,-50 0,0" fill="#6fbf73" {k}/>''',
        "pizza": f'''<path d="M-100,-20 L100,-20 L0,120 Z" fill="#f6c453" {k}/><path d="M-100,-20 Q0,-50 100,-20 L94,-8 Q0,-36 -94,-8 Z" fill="#c8813a" {k}/>
  <circle cx="-24" cy="10" r="13" fill="#d64545"/><circle cx="24" cy="18" r="13" fill="#d64545"/><circle cx="0" cy="56" r="11" fill="#d64545"/>''',
        "candle": f'''<rect x="-18" y="-60" width="36" height="110" fill="#fff4dc" {k}/><path d="M0,-66 Q-16,-96 0,-118 Q16,-96 0,-66 Z" fill="#ffb703" {k}/>''',
        "umbrella": f'''<path d="M-110,0 Q-100,-100 0,-104 Q100,-100 110,0 Q92,-16 74,0 Q56,-16 36,0 Q18,-16 0,0 Q-18,-16 -36,0 Q-56,-16 -74,0 Q-92,-16 -110,0 Z" fill="#7b6cf6" {k}/>
  <path d="M0,0 L0,110 Q0,130 -20,124" fill="none" {k}/>''',
        "snowman": f'''<circle cx="0" cy="40" r="70" fill="#fdfdff" {k}/><circle cx="0" cy="-60" r="48" fill="#fdfdff" {k}/>
  <circle cx="-16" cy="-68" r="6" fill="{INK}"/><circle cx="16" cy="-68" r="6" fill="{INK}"/><path d="M0,-58 L34,-50 L0,-46 Z" fill="#f28c28"/>''',
        "tv": f'''<rect x="-120" y="-90" width="240" height="150" rx="10" fill="#2f3542" {k}/><rect x="-104" y="-76" width="208" height="122" fill="#8ec5ff"/>
  <path d="M-40,60 L-60,90 M40,60 L60,90" {k}/>''',
        "sheet": f'''<path d="M-90,-60 Q0,-80 90,-60 L100,70 Q50,56 0,70 Q-50,56 -100,70 Z" fill="#fbfbff" {k}/>''',
        "sock": f'''<path d="M-30,-70 L30,-70 L30,20 Q30,60 -10,60 L-60,60 Q-80,40 -60,20 L-30,20 Z" fill="#e84a5f" {k}/>''',
    }.get(name) or _sets.PROPS[name][0]
    return f'<g transform="translate({x},{y}) scale({s})">{body}</g>'


from strips import sets as _sets  # noqa: E402

PROPS = ["turkey", "pie", "mug", "laptop", "phone", "book", "pumpkin", "gift", "plant", "pizza", "candle",
         "umbrella", "snowman", "tv", "sheet", "sock"] + list(_sets.PROPS)

# ---------------------------------------------------------------- rooms

def _stripes(c):
    return f'<g opacity="0.18" stroke="{c}" stroke-width="3">' + "".join(
        f'<line x1="{i}" y1="0" x2="{i}" y2="{PH}"/>' for i in range(30, PW, 64)) + "</g>"


def _grad(id_, a, b):
    return f'<defs><linearGradient id="{id_}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'


def _table(y):
    return (f'<rect x="-10" y="{y}" width="{PW + 20}" height="{PH - y + 10}" fill="#e9eef7" stroke="{INK}" stroke-width="6"/>'
            f'<path d="M-10,{y + 40} ' + " ".join(f"Q{i + 16},{y + 58} {i + 32},{y + 40}" for i in range(-10, PW + 20, 32)) +
            f'" fill="none" stroke="#c7d2e6" stroke-width="5"/>')


def _floor(y, color, line):
    return (f'<rect x="-10" y="{y}" width="{PW + 20}" height="{PH - y + 10}" fill="{color}" stroke="{INK}" stroke-width="6"/>'
            + "".join(f'<line x1="{i}" y1="{y + 3}" x2="{i - 40}" y2="{PH}" stroke="{line}" stroke-width="3"/>' for i in range(60, PW + 60, 90)))


def _window(x, y, w, h, sky_a, sky_b, extra=""):
    return (_grad(f"win{x}{y}", sky_a, sky_b) +
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#win{x}{y})" stroke="{INK}" stroke-width="6"/>{extra}'
            f'<path d="M{x + w / 2},{y} L{x + w / 2},{y + h} M{x},{y + h / 2} L{x + w},{y + h / 2}" stroke="{INK}" stroke-width="5"/>')


ROOMS = {
    # name: (svg builder, floor_y for characters, {prop spot: (x, y, scale)})
    "dining_room": lambda: (_grad("dr", "#f6dca8", "#efc98a") + f'<rect width="{PW}" height="{PH}" fill="url(#dr)"/>' + _stripes("#b07a3a")),
    "living_room": lambda: (_grad("lr", "#d9e6f5", "#c4d6ee") + f'<rect width="{PW}" height="{PH}" fill="url(#lr)"/>' +
                            _window(330, 70, 140, 150, "#bfe3ff", "#e9f6ff") +
                            _floor(500, "#c99a6b", "#b3855a") +
                            f'<path d="M-10,430 L200,430 Q216,430 216,446 L216,510 L-10,510 Z" fill="#7b6cf6" stroke="{INK}" stroke-width="6"/>'
                            f'<rect x="-10" y="400" width="190" height="44" rx="14" fill="#9387ff" stroke="{INK}" stroke-width="6"/>'),
    "kitchen": lambda: (f'<rect width="{PW}" height="{PH}" fill="#dff3e6"/>' +
                        '<g stroke="#b9dcc6" stroke-width="3">' + "".join(f'<line x1="0" y1="{j}" x2="{PW}" y2="{j}"/>' for j in range(40, 470, 48)) +
                        "".join(f'<line x1="{i}" y1="0" x2="{i}" y2="470"/>' for i in range(0, PW, 48)) + "</g>" +
                        f'<rect x="400" y="160" width="130" height="312" rx="12" fill="#f4f6fb" stroke="{INK}" stroke-width="6"/>'
                        f'<path d="M400,270 L530,270 M418,200 L418,248 M418,290 L418,340" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'),
    "bedroom_night": lambda: (_grad("bn", "#2d3561", "#1f2547") + f'<rect width="{PW}" height="{PH}" fill="url(#bn)"/>' +
                              _window(60, 70, 170, 170, "#141a38", "#2a3366",
                                      f'<circle cx="185" cy="115" r="24" fill="#fff6c9"/>'
                                      + "".join(f'<circle cx="{cx}" cy="{cy}" r="3" fill="#fff6c9"/>' for cx, cy in ((90, 100), (120, 190), (210, 200), (150, 90)))) +
                              _floor(510, "#3d4470", "#343b63") +
                              f'<rect x="250" y="400" width="280" height="120" rx="14" fill="#f0e6ff" stroke="{INK}" stroke-width="6"/>'
                              f'<rect x="250" y="440" width="280" height="80" fill="#8e7cc3" stroke="{INK}" stroke-width="6"/>'
                              f'<rect x="440" y="300" width="22" height="220" fill="#6b5aa8" stroke="{INK}" stroke-width="6"/>'),
    "outdoors_autumn": lambda: (_grad("oa", "#ffd9a8", "#ffefd6") + f'<rect width="{PW}" height="{PH}" fill="url(#oa)"/>' +
                                f'<rect x="-10" y="500" width="{PW + 20}" height="160" fill="#c98d4b" stroke="{INK}" stroke-width="6"/>' +
                                f'<rect x="20" y="220" width="40" height="290" fill="#7a4e2d" stroke="{INK}" stroke-width="6"/>'
                                f'<circle cx="40" cy="190" r="110" fill="#e8743b" stroke="{INK}" stroke-width="6"/>' +
                                "".join(f'<ellipse cx="{cx}" cy="{cy}" rx="10" ry="6" fill="{c}" transform="rotate({r} {cx} {cy})"/>'
                                        for cx, cy, c, r in ((180, 140, "#e8743b", 20), (300, 260, "#f2b134", -30), (420, 120, "#d9542b", 45),
                                                             (240, 560, "#f2b134", 10), (380, 590, "#e8743b", -20), (120, 600, "#d9542b", 30)))),
    "outdoors_snow": lambda: (_grad("os", "#cfe3f7", "#f1f7fd") + f'<rect width="{PW}" height="{PH}" fill="url(#os)"/>' +
                              f'<path d="M-10,500 Q130,470 260,500 Q390,530 522,496 L522,660 L-10,660 Z" fill="#fdfdff" stroke="{INK}" stroke-width="6"/>' +
                              "".join(f'<circle cx="{(i * 97) % PW}" cy="{(i * 61) % 470}" r="{3 + i % 3}" fill="#fff" stroke="#c9d6e6" stroke-width="1.5"/>' for i in range(1, 40))),
    "plain_warm": lambda: (_grad("pw", "#f6dca8", "#efc98a") + f'<rect width="{PW}" height="{PH}" fill="url(#pw)"/>' + _stripes("#b07a3a")),
    "plain_cool": lambda: (_grad("pc", "#d9e6f5", "#c4d6ee") + f'<rect width="{PW}" height="{PH}" fill="url(#pc)"/>' + _stripes("#7f98bd")),
    "plain_pink": lambda: (_grad("pp", "#ffe0ea", "#ffc9d9") + f'<rect width="{PW}" height="{PH}" fill="url(#pp)"/>' + _stripes("#d98aa5")),
}
FRONT = {  # drawn in front of the characters, so they sit behind the table or counter
    "dining_room": lambda: _table(500),
    "kitchen": lambda: (f'<rect x="-10" y="500" width="{PW + 20}" height="160" fill="#f7f1e3" stroke="{INK}" stroke-width="6"/>'
                        f'<rect x="-10" y="500" width="{PW + 20}" height="28" fill="#d4c6a6" stroke="{INK}" stroke-width="6"/>'),
}
FLOOR = {"dining_room": 545, "living_room": 520, "kitchen": 545, "bedroom_night": 530, "outdoors_autumn": 520,
         "outdoors_snow": 520, "plain_warm": 600, "plain_cool": 600, "plain_pink": 600}
SURFACE = {"dining_room": 500, "kitchen": 500}     # props sit on this line in rooms with a table or counter

ROOMS.update(_sets.ROOMS)
FRONT.update(_sets.FRONT)
FLOOR.update(_sets.FLOOR)
SURFACE.update(_sets.SURFACE)

from strips.cast import MOODS, drawers  # noqa: E402

for _n, (_d, _head, _behind, _scale) in drawers().items():
    CHARACTERS[_n] = {"draw": _d, "moods": MOODS, "head": _head, "float": 0, "base": 124, "behind": _behind, "scale": _scale}
