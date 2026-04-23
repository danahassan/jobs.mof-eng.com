"""Generate dark-themed PWA icons from static/icons/mof-logo.png.

Run:  python scripts/gen_pwa_icons.py
"""
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / 'static' / 'icons' / 'mof-logo.png'
OUT  = ROOT / 'static' / 'icons'

BG_DARK = (15, 25, 35)        # #0f1923 — matches theme_color
ACCENT  = (34, 197, 94)       # subtle green tint for vignette


def round_corners(im, radius):
    mask = Image.new('L', im.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, im.size[0], im.size[1]), radius=radius, fill=255)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def make_icon(size, *, logo_ratio=0.72, rounded=False, square=True, bg=BG_DARK):
    canvas = Image.new('RGBA', (size, size), bg + (255,))

    # Soft radial vignette in brand green
    vignette = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    cx = cy = size // 2
    rad = int(size * 0.55)
    vd.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=ACCENT + (38,))
    vignette = vignette.filter(ImageFilter.GaussianBlur(size * 0.18))
    canvas.alpha_composite(vignette)

    # Place the logo centered
    src = Image.open(SRC).convert('RGBA')
    target_w = int(size * logo_ratio)
    ratio    = target_w / src.width
    target_h = int(src.height * ratio)
    if target_h > size * logo_ratio:
        target_h = int(size * logo_ratio)
        target_w = int(src.width * (target_h / src.height))
    logo = src.resize((target_w, target_h), Image.LANCZOS)
    canvas.alpha_composite(logo, ((size - target_w) // 2, (size - target_h) // 2))

    if rounded and not square:
        canvas = round_corners(canvas, int(size * 0.22))
    return canvas


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Standard "any" icons — full-bleed dark background with logo
    for sz in (192, 512, 1024):
        ic = make_icon(sz, logo_ratio=0.68)
        ic.save(OUT / f'icon-{sz}.png', optimize=True)

    # Maskable icons — logo smaller (40%) to stay inside safe zone
    for sz in (192, 512):
        ic = make_icon(sz, logo_ratio=0.46)
        ic.save(OUT / f'icon-maskable-{sz}.png', optimize=True)

    # Apple touch icon (iOS adds rounded mask itself)
    make_icon(180, logo_ratio=0.7).save(OUT / 'apple-touch-icon.png', optimize=True)
    make_icon(167, logo_ratio=0.7).save(OUT / 'apple-touch-icon-167.png', optimize=True)
    make_icon(152, logo_ratio=0.7).save(OUT / 'apple-touch-icon-152.png', optimize=True)
    make_icon(120, logo_ratio=0.7).save(OUT / 'apple-touch-icon-120.png', optimize=True)

    # Favicons
    make_icon(32, logo_ratio=0.78).save(OUT / 'favicon-32.png', optimize=True)
    make_icon(16, logo_ratio=0.85).save(OUT / 'favicon-16.png', optimize=True)

    # Notification badge — monochrome silhouette would be ideal, use small icon
    make_icon(96, logo_ratio=0.78).save(OUT / 'badge-96.png', optimize=True)

    print('Generated icons in', OUT)


if __name__ == '__main__':
    main()
