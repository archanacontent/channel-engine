from PIL import Image, ImageDraw

from render.lib import H, W, ease, font, rgb, text_c, tw, wrap


class Painter:
    """One channel's look. Subclasses draw the background, logo and each beat."""

    caption_style = {}
    tag_text_color = "#FFFFFF"
    tag_font = ("Inter[opsz,wght].ttf", 600)

    def __init__(self, brand, episode, timing):
        self.brand, self.ep, self.timing = brand, episode, timing
        self.p = {k: rgb(v) for k, v in brand["palette"].items()}
        self.bg = self.make_bg()
        self.logo_small = self.logo(72)
        self.logo_big = self.logo(300)

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
        size = int(260 + 40 * a)
        lg = self.logo_big.resize((size, size))
        img.paste(lg, ((W - size) // 2, 640 - size // 2), lg)
        f = font(self.tag_font[0], 72, 700)
        text_c(d, W / 2, 840, self.brand["name"], f, rgb(self.tag_text_color))
        f2 = font(self.tag_font[0], 36, 400)
        col = self.p.get("muted_text", self.p.get("secondary"))
        for j, line in enumerate(wrap(self.brand["positioning"], f2, 820)):
            text_c(d, W / 2, 950 + j * 50, line, f2, col)
