import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.dirname(os.path.abspath(__file__))
S = 2048
NAVY_TOP = (30, 38, 66)
NAVY_BOT = (11, 14, 26)
GOLD_L = (255, 226, 130)
GOLD_D = (205, 150, 40)


def vgrad(size, c1, c2):
    k = np.linspace(0, 1, size, dtype=np.float32)[:, None, None]
    a = np.array(c1, np.float32)
    b = np.array(c2, np.float32)
    arr = (a * (1 - k) + b * k) * np.ones((size, size, 1), np.float32)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def gold_fill(size):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    k = np.clip((xx * 0.4 + yy * 0.8) / (size * 1.2), 0, 1)[..., None]
    a = np.array(GOLD_L, np.float32)
    b = np.array(GOLD_D, np.float32)
    arr = a * (1 - k) + b * k
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def mark_mask():
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    cx = S // 2
    top = 400
    d.rounded_rectangle((cx - 26, top + 60, cx + 26, 1180), radius=22, fill=255)
    d.ellipse((cx - 70, top - 10, cx + 70, top + 130), fill=255)
    d.rounded_rectangle((cx - 560, top + 100, cx + 560, top + 150),
                        radius=25, fill=255)
    for sx in (-1, 1):
        px = cx + sx * 520
        d.line((px, top + 140, px - 170, 880), fill=255, width=22)
        d.line((px, top + 140, px + 170, 880), fill=255, width=22)
        d.pieslice((px - 215, 700, px + 215, 1060), 0, 180, fill=255)
        d.rounded_rectangle((px - 225, 862, px + 225, 892), radius=15,
                            fill=255)
    by = 1250
    for sx in (-1, 1):
        pts = [(cx + sx * 20, by - 60),
               (cx + sx * 330, by - 190),
               (cx + sx * 700, by - 130),
               (cx + sx * 700, by + 330),
               (cx + sx * 330, by + 270),
               (cx + sx * 20, by + 400)]
        d.polygon(pts, fill=255)
    d.line((cx, by - 40, cx, by + 405), fill=0, width=26)
    for sx in (-1, 1):
        for j in range(4):
            y0 = by + 10 + j * 70
            d.line((cx + sx * 80, y0 + 40 - j * 8, cx + sx * 560,
                    y0 - 60 - j * 6 + 40), fill=0, width=18)
    return m


def build(size_out, rounded=True):
    bg = vgrad(S, NAVY_TOP, NAVY_BOT).convert("RGBA")
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    dist = np.sqrt((xx - S / 2) ** 2 + (yy - S * 0.52) ** 2) / (S * 0.5)
    glow = np.clip(1 - dist, 0, 1) ** 2.2 * 70
    arr = np.zeros((S, S, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = 255, 200, 70
    arr[..., 3] = glow.astype(np.uint8)
    bg = Image.alpha_composite(bg, Image.fromarray(arr, "RGBA"))

    ring = Image.new("L", (S, S), 0)
    ImageDraw.Draw(ring).ellipse((150, 150, S - 150, S - 150),
                                 outline=255, width=14)
    bg.paste(gold_fill(S), (0, 0), ring.point(lambda v: int(v * 0.55)))

    m = mark_mask()
    shadow = m.filter(ImageFilter.GaussianBlur(26)).point(
        lambda v: int(v * 0.5))
    bg.paste(Image.new("RGB", (S, S), (0, 0, 0)), (0, 40), shadow)
    bg.paste(gold_fill(S), (0, 0), m)

    if rounded:
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=255)
        out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        out.paste(bg, (0, 0), mask)
        bg = out
    return bg.resize((size_out, size_out), Image.LANCZOS)


if __name__ == "__main__":
    build(1024, rounded=False).convert("RGB").save(
        os.path.join(OUT, "icon.png"))
    build(1024, rounded=True).save(os.path.join(OUT, "logo.png"))
    print("logo files created")
