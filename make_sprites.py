"""Cut the plush out of the studio shots and emit transparent sprites.

    python make_sprites.py
"""
from collections import deque
import os
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "sprites")

# Studio backdrop is pure white; the plush's own white fur is cream-tinted,
# so hue neutrality separates them better than brightness does.
def tight(p):
    return min(p) >= 249 and (max(p) - min(p)) <= 7

def loose(p):
    return min(p) >= 226 and (max(p) - min(p)) <= 16


def pool(p):
    # Contact shadow under the feet goes grey rather than staying pure white,
    # so the bottom band needs a wider net than the cream-fur test above.
    return min(p) >= 198 and (max(p) - min(p)) <= 26


def is_yellow(p):
    r, g, b = p
    return r - b > 55 and r > 150


def cutout(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    dq = deque()

    def seed(x, y, rule):
        i = y * w + x
        if not seen[i] and rule(px[x, y]):
            seen[i] = 1
            dq.append((x, y, rule))

    for x in range(w):
        seed(x, 0, tight)
        seed(x, h - 1, tight)
    for y in range(h):
        seed(0, y, tight)
        seed(w - 1, y, tight)
    while dq:
        x, y, rule = dq.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                i = ny * w + nx
                if not seen[i] and rule(px[nx, ny]):
                    seen[i] = 1
                    dq.append((nx, ny, rule))

    feet = max((y for y in range(h) for x in range(0, w, 2) if is_yellow(px[x, y])), default=h - 1)
    band = max(0, feet - int(h * 0.07))
    for y in range(band, h):
        for x in range(w):
            i = y * w + x
            if not seen[i] and (loose(px[x, y]) or (y >= feet - 6 and pool(px[x, y]))):
                seen[i] = 1

    alpha = Image.new("L", (w, h), 255)
    ad = alpha.load()
    for i in range(w * h):
        if seen[i]:
            ad[i % w, i // w] = 0
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))

    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(alpha.getbbox())


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [("hero_src.png", "idle", 420), ("web_a1.png", "turn_a", 420),
            ("web_a2.png", "turn_b", 420), ("web_a3.png", "turn_c", 420)]
    for name, stem, height in jobs:
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            print("skip", name)
            continue
        sprite = cutout(src)
        ratio = height / sprite.height
        sprite = sprite.resize((max(1, round(sprite.width * ratio)), height), Image.LANCZOS)
        sprite.save(os.path.join(OUT, stem + ".png"))
        probe = Image.new("RGBA", sprite.size, (210, 40, 150, 255))
        probe.alpha_composite(sprite)
        probe.convert("RGB").save(os.path.join(OUT, stem + "_probe.jpg"), quality=88)
        print(stem, sprite.size)


if __name__ == "__main__":
    main()
