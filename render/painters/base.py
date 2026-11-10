from PIL import Image, ImageDraw

from render.lib import H, ROOT, W, ease, font, rgb, text_c, tw, wrap


class Painter:
    """One channel's look. Subclasses draw the background, logo and each beat."""

    caption_style = {}
    tag_text_color = "#FFFFFF"
    tag_font = ("Inter[opsz,wght].ttf", 600)
    bare = False

    def __init__(self, brand, episode, timing):
        self.brand, self.ep, self.timing = brand, episode, timing
        self.p = {k: rgb(v) for k, v in brand["palette"].items()}
        self.bg = self.make_bg()
        self.logo_file = ROOT / "channels" / brand["slug"] / "art" / "logo.png"
        self.logo_small = self.logo_any(72)
        self.logo_big = self.logo_any(520)

    def logo_any(self, size):
        """The channel's own logo file when there is one, otherwise the drawn mark."""
        if not self.logo_file.exists():
            return self.logo(size)
        im = Image.open(self.logo_file).convert("RGBA").resize((size, size), Image.LANCZOS)
        big = size * 3
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.18), fill=255)
        im.putalpha(mask.resize((size, size), Image.LANCZOS))
        return im

    # Subclasses override these.
    def make_bg(self):
        return Image.new("RGB", (W, H), self.p["background"])

    def background(self, t):
        return self.bg.copy()

    def logo(self, size):
        raise NotImplementedError

    def beat(self, img, d, i, t, dur):
        pass

    # Shared pieces.
    def tag(self, img, d):
        img.paste(self.logo_small, (56, 104), self.logo_small)
        f = font(self.tag_font[0], 34, self.tag_font[1])
        d.text((144, 122), self.brand["name"], font=f, fill=rgb(self.tag_text_color))

    def end(self, img, d, k):
        """Branded end frame, the same on every Short of the channel."""
        a = ease(k / 0.5)
        f2 = font(self.tag_font[0], 38, 500)
        col = self.p.get("muted_text", self.p.get("secondary"))
        if self.logo_file.exists():
            size = int(470 + 50 * a)
            lg = self.logo_big.resize((size, size))
            img.paste(lg, ((W - size) // 2, 700 - size // 2), lg)
            y = 1010
        else:
            size = int(260 + 40 * a)
            lg = self.logo_big.resize((size, size))
            img.paste(lg, ((W - size) // 2, 640 - size // 2), lg)
            text_c(d, W / 2, 840, self.brand["name"], font(self.tag_font[0], 72, 700), rgb(self.tag_text_color))
            y = 950
        for j, line in enumerate(wrap(self.brand["positioning"], f2, 860)):
            text_c(d, W / 2, y + j * 52, line, f2, col)
