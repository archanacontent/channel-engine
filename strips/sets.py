"""More places, props and panel effects for Comicsofy. Panels are 512 x 647 units."""
INK = "#1d1a22"
PW, PH = 512, 647
K = f'stroke="{INK}" stroke-width="6" stroke-linejoin="round"'


def _g(id_, a, b):
    return f'<defs><linearGradient id="{id_}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'


def _wall(id_, a, b):
    return _g(id_, a, b) + f'<rect width="{PW}" height="{PH}" fill="url(#{id_})"/>'


def _floor(y, c, line):
    return (f'<rect x="-10" y="{y}" width="{PW + 20}" height="{PH - y + 10}" fill="{c}" {K}/>'
            + "".join(f'<line x1="{i}" y1="{y + 3}" x2="{i - 50}" y2="{PH}" stroke="{line}" stroke-width="3"/>' for i in range(40, PW + 80, 80)))


def _tiles(y, a, b):
    out = f'<rect x="-10" y="{y}" width="{PW + 20}" height="{PH - y + 10}" fill="{a}" {K}/>'
    for r, yy in enumerate(range(y, PH, 36)):
        for i, xx in enumerate(range(-20, PW, 56)):
            if (r + i) % 2:
                out += f'<rect x="{xx + (r % 2) * 28}" y="{yy}" width="56" height="36" fill="{b}"/>'
    return out + f'<line x1="-10" y1="{y}" x2="{PW + 10}" y2="{y}" stroke="{INK}" stroke-width="6"/>'


def _desk(y=500, top="#c99a6b", face="#b3855a"):
    return (f'<rect x="-10" y="{y}" width="{PW + 20}" height="26" fill="{top}" {K}/>'
            f'<rect x="-10" y="{y + 26}" width="{PW + 20}" height="{PH - y}" fill="{face}" {K}/>'
            f'<path d="M180,{y + 60} L180,{PH} M340,{y + 60} L340,{PH}" stroke="{INK}" stroke-width="4" opacity="0.5"/>')


def _buildings(y, colors, lit="#fff1a8", dark=False):
    out, x = "", -20
    for i, c in enumerate(colors):
        w, h = 90 + (i * 37) % 60, 180 + (i * 71) % 200
        out += f'<rect x="{x}" y="{y - h}" width="{w}" height="{h + 10}" fill="{c}" {K}/>'
        for wy in range(y - h + 22, y - 20, 34):
            for wx in range(x + 14, x + w - 20, 26):
                on = (wx * 7 + wy * 3) % 5 < (3 if dark else 2)
                out += f'<rect x="{wx}" y="{wy}" width="14" height="18" fill="{lit if on else "#00000022"}"/>'
        x += w - 4
    return out


ROOMS = {
    "office": lambda: (_wall("of", "#e6ebf2", "#d4dbe6") +
                       f'<rect x="300" y="60" width="180" height="200" fill="#bfe3ff" {K}/>' +
                       "".join(f'<line x1="300" y1="{yy}" x2="480" y2="{yy}" stroke="#9fb2c8" stroke-width="5"/>' for yy in range(76, 260, 16)) +
                       f'<rect x="-10" y="300" width="200" height="210" fill="#8e9bb0" {K}/><rect x="-10" y="300" width="200" height="16" fill="#6f7c92"/>'
                       f'<path d="M40,330 l60,0 l0,40 l-60,0 z" fill="#fff4a8" stroke="{INK}" stroke-width="3" transform="rotate(-6 70 350)"/>'
                       f'<path d="M110,350 l50,0 l0,36 l-50,0 z" fill="#ffc9d9" stroke="{INK}" stroke-width="3" transform="rotate(5 135 368)"/>'),
    "meeting_room": lambda: (_wall("mr", "#eef1f6", "#dde3ec") +
                             f'<rect x="40" y="60" width="300" height="200" fill="#fff" {K}/>'
                             f'<path d="M70,110 L130,130 L180,120 L230,180 L300,230" stroke="#e84a5f" stroke-width="8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                             f'<path d="M286,214 L304,234 L278,236 Z" fill="#e84a5f"/><path d="M70,90 L70,240 L320,240" stroke="{INK}" stroke-width="4" fill="none"/>'
                             f'<rect x="390" y="90" width="80" height="80" rx="40" fill="#fff" {K}/><path d="M430,104 L430,130 L448,140" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>'),
    "cafe": lambda: (f'<rect width="{PW}" height="{PH}" fill="#b8623f"/>' +
                     "".join(f'<rect x="{(c * 64) + (r % 2) * 32 - 32}" y="{r * 30}" width="60" height="26" fill="#c9744f" rx="2"/>' for r in range(18) for c in range(10)) +
                     f'<rect x="60" y="90" width="230" height="170" fill="#2e3a33" stroke="#7a5a3a" stroke-width="12"/>' +
                     "".join(f'<path d="M84,{yy} q40,-8 80,0 q30,6 60,0" stroke="#f2efe6" stroke-width="4" fill="none" opacity="0.85"/>' for yy in (130, 170, 210, 240)) +
                     "".join(f'<path d="M{lx},0 L{lx},70" stroke="{INK}" stroke-width="4"/><path d="M{lx - 30},100 Q{lx},50 {lx + 30},100 Z" fill="#f4d03f" {K}/>' for lx in (360, 450))),
    "city_street": lambda: (_wall("cs", "#9fd3ff", "#e9f6ff") +
                            _buildings(470, ["#e8a87c", "#c38d9e", "#41b3a3", "#e27d60", "#8e9bb0", "#f4d03f"]) +
                            f'<rect x="-10" y="470" width="{PW + 20}" height="200" fill="#c9cdd8" {K}/>' +
                            "".join(f'<line x1="{i}" y1="470" x2="{i - 30}" y2="{PH}" stroke="#aab0bf" stroke-width="4"/>' for i in range(30, PW + 60, 110)) +
                            f'<rect x="440" y="200" width="14" height="280" fill="#3b4158" {K}/><path d="M430,200 Q447,170 480,186 L476,200 Z" fill="#3b4158" {K}/>'),
    "park": lambda: (_wall("pk", "#8fd0ff", "#dff3ff") +
                     '<circle cx="420" cy="90" r="44" fill="#ffe28a"/>'
                     f'<path d="M-10,430 Q120,370 260,420 Q400,460 522,400 L522,660 L-10,660 Z" fill="#7cc576" {K}/>' +
                     f'<rect x="60" y="250" width="34" height="200" fill="#7a4e2d" {K}/><circle cx="77" cy="220" r="90" fill="#4caf50" {K}/>'
                     f'<circle cx="30" cy="260" r="50" fill="#5fc068" {K}/>' +
                     f'<rect x="300" y="430" width="200" height="16" rx="6" fill="#a8693f" {K}/><rect x="300" y="400" width="200" height="14" rx="6" fill="#a8693f" {K}/>'
                     f'<path d="M320,446 L320,490 M480,446 L480,490" stroke="{INK}" stroke-width="7"/>'),
    "supermarket": lambda: (f'<rect width="{PW}" height="{PH}" fill="#f2f4f8"/>' +
                            "".join(f'<rect x="-10" y="{sy}" width="{PW + 20}" height="12" fill="#c9cdd8" {K}/>' +
                                    "".join(f'<rect x="{bx}" y="{sy - 70}" width="40" height="70" rx="4" fill="{c}" stroke="{INK}" stroke-width="3.5"/>'
                                            for bx, c in zip(range(6, PW, 46), ["#e84a5f", "#f4d03f", "#41b3a3", "#7b6cf6", "#f28c28", "#4caf50", "#e27d60", "#9fd3ff", "#ff9f43", "#c38d9e", "#e84a5f"][sy % 3:]))
                                    for sy in (140, 260, 380)) +
                            _tiles(500, "#e6e9ef", "#d5d9e2")),
    "bus": lambda: (f'<rect width="{PW}" height="{PH}" fill="#e9e1cf"/>' +
                    "".join(f'<rect x="{wx}" y="80" width="150" height="190" rx="18" fill="#9fd3ff" {K}/>'
                            f'<path d="M{wx + 10},200 L{wx + 60},150 L{wx + 100},180 L{wx + 140},130" stroke="#7fb6e0" stroke-width="16" fill="none"/>' for wx in (20, 190, 360)) +
                    f'<rect x="250" y="0" width="14" height="520" fill="#f4d03f" {K}/><rect x="-10" y="40" width="{PW + 20}" height="12" fill="#f4d03f" {K}/>' +
                    f'<rect x="-10" y="330" width="220" height="110" rx="20" fill="#41b3a3" {K}/><rect x="320" y="330" width="210" height="110" rx="20" fill="#41b3a3" {K}/>' +
                    _floor(520, "#6f7c92", "#5f6b80")),
    "gym": lambda: (_wall("gy", "#3b4158", "#2a2f40") +
                    f'<rect x="40" y="70" width="260" height="330" fill="#cfe6f5" {K}/><path d="M70,100 L150,90 M80,140 L120,135" stroke="#fff" stroke-width="8" stroke-linecap="round"/>' +
                    f'<rect x="340" y="230" width="160" height="12" fill="#9aa3b5" {K}/><rect x="340" y="330" width="160" height="12" fill="#9aa3b5" {K}/>' +
                    "".join(f'<rect x="{dx}" y="{dy}" width="34" height="26" rx="6" fill="#e84a5f" stroke="{INK}" stroke-width="4"/>' for dx in (350, 410, 460) for dy in (204, 304)) +
                    _floor(520, "#2f3542", "#252a35")),
    "rooftop_night": lambda: (_wall("rn", "#141a38", "#3a2f6b") +
                              "".join(f'<circle cx="{(i * 89) % PW}" cy="{(i * 53) % 220}" r="2.5" fill="#fff6c9"/>' for i in range(1, 30)) +
                              '<circle cx="420" cy="80" r="34" fill="#fff6c9"/>' +
                              _buildings(460, ["#252a4a", "#2f3561", "#1f2547", "#353b6e", "#262c52", "#2f3561"], dark=True) +
                              f'<path d="M-10,150 Q130,210 260,160 Q390,210 522,150" stroke="{INK}" stroke-width="3" fill="none"/>' +
                              "".join(f'<circle cx="{lx}" cy="{150 + 40 * (1 - ((lx % 260) / 130 - 1) ** 2)}" r="8" fill="#ffd166"/>' for lx in range(20, PW, 46)) +
                              f'<rect x="-10" y="460" width="{PW + 20}" height="200" fill="#4b4f5c" {K}/><rect x="-10" y="440" width="{PW + 20}" height="26" fill="#6b7080" {K}/>'),
    "elevator": lambda: (_wall("el", "#c9cdd8", "#aab0bf") +
                         f'<rect x="60" y="40" width="392" height="540" fill="#d5d9e2" {K}/><path d="M256,40 L256,580" stroke="{INK}" stroke-width="6"/>' +
                         "".join(f'<line x1="{lx}" y1="44" x2="{lx}" y2="576" stroke="#bfc4cf" stroke-width="2"/>' for lx in range(70, 452, 14)) +
                         f'<rect x="200" y="0" width="112" height="34" rx="6" fill="#2a2730" {K}/><text x="256" y="27" font-family="Hand" font-size="26" fill="#ff6b5a" text-anchor="middle">13</text>' +
                         _tiles(560, "#8a8f9c", "#7a7f8c")),
    "party": lambda: (_wall("pa", "#4b2d6b", "#2b1a40") +
                      "".join(f'<path d="M{sx},0 Q{sx + 40},60 {sx + 80},0" stroke="{c}" stroke-width="8" fill="none"/>' for sx, c in ((0, "#ffd166"), (90, "#ff5a7a"), (180, "#5fb8a5"), (270, "#ffd166"), (360, "#ff5a7a"), (450, "#5fb8a5"))) +
                      "".join(f'<path d="M{bx},{by + 70} q-4,40 6,90" stroke="#ddd" stroke-width="2" fill="none"/><ellipse cx="{bx}" cy="{by}" rx="34" ry="42" fill="{c}" {K}/>'
                              for bx, by, c in ((60, 140, "#ff5a7a"), (110, 200, "#ffd166"), (440, 150, "#5fb8a5"), (480, 230, "#7b6cf6"))) +
                      f'<circle cx="256" cy="70" r="42" fill="#cfd3dd" {K}/>' +
                      "".join(f'<path d="M256,70 L{256 + 260 * dx},{70 + 400 * dy}" stroke="#ffffff22" stroke-width="18"/>' for dx, dy in ((-0.8, 1), (-0.3, 1), (0.3, 1), (0.8, 1))) +
                      _floor(520, "#3a2652", "#2f1f44")),
    "doctor_office": lambda: (_wall("do", "#e3f4ee", "#cfe9e0") +
                              f'<rect x="300" y="70" width="150" height="200" fill="#fff" {K}/>' +
                              "".join(f'<rect x="{375 - w / 2}" y="{yy}" width="{w}" height="{h}" fill="{INK}" rx="2"/>' for yy, w, h in ((92, 44, 40), (148, 70, 24), (188, 90, 16), (220, 106, 10), (242, 116, 7))) +
                              f'<rect x="-10" y="380" width="220" height="40" rx="10" fill="#9fd3ff" {K}/><rect x="-10" y="420" width="200" height="100" fill="#c9cdd8" {K}/>' +
                              _tiles(520, "#f2f4f8", "#e1e5ec")),
}
FRONT = {
    "office": lambda: _desk(500, "#d8dde6", "#aab3c2") + f'<rect x="440" y="420" width="120" height="80" rx="8" fill="#2f3542" {K}/><rect x="452" y="432" width="100" height="58" fill="#8ec5ff"/>',
    "meeting_room": lambda: _desk(500, "#8a5a3b", "#6b4428"),
    "cafe": lambda: (_desk(500, "#e9d8b8", "#7a5a3a") + f'<path d="M470,440 L506,440 L502,500 L474,500 Z" fill="#dff3ff" {K}/><rect x="478" y="470" width="20" height="14" fill="#7cc576"/>'),
}
FLOOR = {"office": 545, "meeting_room": 545, "cafe": 545, "city_street": 540, "park": 545, "supermarket": 545, "bus": 545,
         "gym": 545, "rooftop_night": 520, "elevator": 580, "party": 545, "doctor_office": 545}
SURFACE = {"office": 500, "meeting_room": 500, "cafe": 500}


# ---------------------------------------------------------------- props

PROPS = {
    "coffee": (f'<path d="M-36,-60 L36,-60 L28,60 L-28,60 Z" fill="#fffdf2" {K}/><rect x="-40" y="-76" width="80" height="18" rx="5" fill="#f4f6fb" {K}/>'
               f'<rect x="-33" y="-20" width="64" height="32" fill="#a8693f"/>', 70, 0.6),
    "bread": (f'<path d="M-90,30 C-110,-50 -40,-70 0,-60 C40,-70 110,-50 90,30 Z" fill="#e3a65a" {K}/>'
              f'<path d="M-50,-40 Q-40,-10 -50,10 M0,-50 Q10,-20 0,10 M50,-40 Q60,-10 50,10" stroke="#b9772e" stroke-width="6" fill="none" stroke-linecap="round"/>', 30, 0.6),
    "cake": (f'<rect x="-90" y="-40" width="180" height="90" rx="10" fill="#ffc9d9" {K}/><path d="M-90,-30 Q-60,0 -30,-30 Q0,0 30,-30 Q60,0 90,-30" stroke="#fff" stroke-width="10" fill="none"/>'
             + "".join(f'<rect x="{cx - 6}" y="-80" width="12" height="40" fill="#9fd3ff" stroke="{INK}" stroke-width="3"/><path d="M{cx},-84 q-8,-14 0,-24 q8,10 0,24 Z" fill="#ffb703"/>' for cx in (-50, 0, 50)), 50, 0.7),
    "dumbbell": (f'<rect x="-70" y="-10" width="140" height="20" fill="#9aa3b5" {K}/><rect x="-100" y="-40" width="36" height="80" rx="8" fill="#e84a5f" {K}/><rect x="64" y="-40" width="36" height="80" rx="8" fill="#e84a5f" {K}/>', 40, 0.6),
    "flowers": (f'<path d="M-30,20 L30,20 L10,100 L-10,100 Z" fill="#9fd3ff" {K}/>' +
                "".join(f'<path d="M0,20 Q{fx * 0.5},-20 {fx},{fy}" stroke="#4caf50" stroke-width="6" fill="none"/><circle cx="{fx}" cy="{fy}" r="22" fill="{c}" {K}/><circle cx="{fx}" cy="{fy}" r="7" fill="#ffd166"/>'
                        for fx, fy, c in ((-40, -60, "#ff5a7a"), (0, -90, "#ffd166"), (40, -60, "#7b6cf6"))), 100, 0.65),
    "envelope": (f'<rect x="-80" y="-50" width="160" height="100" fill="#fffdf2" {K}/><path d="M-80,-50 L0,14 L80,-50" fill="none" {K}/><circle cx="0" cy="14" r="14" fill="#d64545" stroke="{INK}" stroke-width="3"/>', 50, 0.55),
    "clipboard": (f'<rect x="-60" y="-80" width="120" height="160" rx="8" fill="#c99a6b" {K}/><rect x="-46" y="-60" width="92" height="124" fill="#fff"/>'
                  f'<rect x="-24" y="-92" width="48" height="24" rx="6" fill="#9aa3b5" {K}/>' +
                  "".join(f'<path d="M-36,{yy} L36,{yy}" stroke="#b8b4c8" stroke-width="5"/>' for yy in (-40, -20, 0, 20, 40)), 80, 0.6),
    "balloon": (f'<path d="M0,60 Q-10,110 6,170" stroke="#888" stroke-width="3" fill="none"/><ellipse cx="0" cy="0" rx="50" ry="62" fill="#ff5a7a" {K}/><path d="M-6,60 L6,60 L0,68 Z" fill="#ff5a7a" {K}/>', 170, 0.6),
    "briefcase": (f'<rect x="-80" y="-40" width="160" height="100" rx="10" fill="#7a4e2d" {K}/><path d="M-30,-40 L-30,-64 L30,-64 L30,-40" fill="none" {K}/><rect x="-14" y="-10" width="28" height="16" fill="#ffd166" stroke="{INK}" stroke-width="3"/>', 60, 0.6),
    "trophy": (f'<path d="M-50,-80 L50,-80 L40,-10 Q0,20 -40,-10 Z" fill="#ffd166" {K}/><path d="M-50,-66 Q-90,-60 -70,-30 Q-60,-20 -42,-26 M50,-66 Q90,-60 70,-30 Q60,-20 42,-26" fill="none" {K}/>'
               f'<rect x="-10" y="10" width="20" height="40" fill="#ffd166" {K}/><rect x="-46" y="50" width="92" height="26" fill="#7a4e2d" {K}/>', 76, 0.65),
}


# ---------------------------------------------------------------- panel effects

def fx_back(name):
    """Drawn over the room, behind the characters."""
    if name == "speed_lines":
        import math
        return ('<g opacity="0.9">' + f'<rect width="{PW}" height="{PH}" fill="#fffdf2"/>' +
                "".join(f'<path d="M256,330 L{256 + 700 * math.cos(a + 0.03)},{330 + 700 * math.sin(a + 0.03)} L{256 + 700 * math.cos(a - 0.03)},{330 + 700 * math.sin(a - 0.03)} Z" fill="{INK}" opacity="0.85"/>'
                        for a in [i * 2 * math.pi / 44 for i in range(44)]) +
                f'<ellipse cx="256" cy="330" rx="170" ry="210" fill="#fffdf2"/></g>')
    if name == "spotlight":
        return (f'<defs><radialGradient id="spot" cx="0.5" cy="0.62" r="0.55"><stop offset="0.35" stop-color="#000" stop-opacity="0"/>'
                f'<stop offset="1" stop-color="#000" stop-opacity="0.88"/></radialGradient></defs><rect width="{PW}" height="{PH}" fill="url(#spot)"/>')
    if name == "gloom":
        return (f'<rect width="{PW}" height="{PH}" fill="#2a3350" opacity="0.55"/>' +
                "".join(f'<line x1="{(i * 53) % PW}" y1="{(i * 97) % PH}" x2="{(i * 53) % PW - 10}" y2="{(i * 97) % PH + 34}" stroke="#9fb6d8" stroke-width="3" opacity="0.7"/>' for i in range(60)))
    if name == "impact":
        import math
        pts = " ".join(f"{256 + (300 if i % 2 else 200) * math.cos(i * math.pi / 12)},{330 + (340 if i % 2 else 230) * math.sin(i * math.pi / 12)}" for i in range(24))
        return f'<rect width="{PW}" height="{PH}" fill="#ff6b5a"/><polygon points="{pts}" fill="#ffd166" stroke="{INK}" stroke-width="6"/>'
    if name == "flashback":
        return f'<rect width="{PW}" height="{PH}" fill="#f2e3c2" opacity="0.6"/>'
    return ""


def fx_front(name):
    """Drawn in front of everyone."""
    if name == "sparkles":
        star = lambda x, y, r: f'<path transform="translate({x},{y}) scale({r})" d="M0,-20 Q3,-3 20,0 Q3,3 0,20 Q-3,3 -20,0 Q-3,-3 0,-20 Z" fill="#ffd166" stroke="{INK}" stroke-width="2"/>'
        return "".join(star(x, y, r) for x, y, r in ((60, 300, 1.2), (450, 260, 1.4), (90, 480, 0.9), (420, 470, 1.0), (256, 230, 0.8)))
    if name == "hearts":
        h = lambda x, y, r: f'<path transform="translate({x},{y}) scale({r})" d="M0,10 C-18,-4 -14,-20 -4,-18 C0,-17 0,-14 0,-12 C0,-14 0,-17 4,-18 C14,-20 18,-4 0,10 Z" fill="#ff5a7a" stroke="{INK}" stroke-width="2.5"/>'
        return "".join(h(x, y, r) for x, y, r in ((70, 320, 2.0), (440, 300, 2.4), (110, 470, 1.5), (400, 470, 1.7)))
    if name == "flashback":
        return f'<rect x="8" y="8" width="{PW - 16}" height="{PH - 16}" fill="none" stroke="#c9a96b" stroke-width="10" stroke-dasharray="4 14" stroke-linecap="round"/>'
    if name == "gloom":
        return (f'<g transform="translate(256,70)"><path d="M-110,30 Q-120,-20 -70,-24 Q-60,-70 -10,-60 Q30,-90 70,-50 Q120,-50 110,0 Q120,40 70,40 L-80,40 Q-120,40 -110,30 Z" fill="#6f7c92" {K}/></g>')
    return ""


def sfx(text, spot="right", at=None):
    x = {"left": 120, "center": 256, "right": 380}.get(spot, 380)
    y = 560
    if at:
        x, y = at
    t = text.upper()[:12]
    fs = 92 if len(t) <= 5 else 70 if len(t) <= 8 else 54
    return (f'<g transform="translate({x},{y}) rotate(-8)"><text text-anchor="middle" font-family="Hand" font-size="{fs}" '
            f'fill="#ffd166" stroke="{INK}" stroke-width="14" paint-order="stroke" stroke-linejoin="round" letter-spacing="2">{t}</text></g>')


FX = ["speed_lines", "spotlight", "gloom", "impact", "sparkles", "hearts", "flashback"]
SHOTS = {"wide": 1.0, "medium": 1.32, "close": 1.75, "extreme_close": 2.45}
