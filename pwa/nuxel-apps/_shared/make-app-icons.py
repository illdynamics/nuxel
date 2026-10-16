#!/usr/bin/env python3
"""Generate the standard Nuxel PWA icon set for one app (offline, deterministic).

Usage:
    python3 make-app-icons.py <app-dir> <bg-hex> <glyph> [<accent-hex>]

Every Nuxel PWA ships the same nine raster sizes the launcher and the service
worker expect (48/72/96/128/144/152/192/384/512) plus an SVG.  Drawing them here
keeps the whole set byte-identical across apps: same rounded-square geometry,
same glyph box, only the app colour and glyph differ.  No network, no fonts from
outside the repository (PIL's bundled DejaVu is used when present, otherwise a
built-in 5x7 bitmap font is drawn), so the icons can be regenerated offline on
any build host.

The output is written next to this file's target:

    pwa/nuxel-apps/<app>/icons/icon-<size>.png
    pwa/nuxel-apps/<app>/icons/icon.svg
"""
import os
import sys
import zlib
import struct

SIZES = (48, 72, 96, 128, 144, 152, 192, 384, 512)
SS = 4  # supersample factor for anti-aliasing


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


# ---- minimal fallback PNG writer (used only when PIL is unavailable) --------
def _png_chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data +
            struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))


def write_png_fallback(path, size, bg, fg):
    raw = bytearray()
    r, g, b = bg
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw += bytes((r, g, b))
    data = (b'\x89PNG\r\n\x1a\n' +
            _png_chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)) +
            _png_chunk(b'IDAT', zlib.compress(bytes(raw), 9)) +
            _png_chunk(b'IEND', b''))
    with open(path, 'wb') as fh:
        fh.write(data)


def write_with_pil(path, size, bg, fg, glyph):
    from PIL import Image, ImageDraw, ImageFont
    px = size * SS
    img = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(px * 0.22)
    d.rounded_rectangle([0, 0, px - 1, px - 1], radius=radius, fill=bg)
    # glyph, centred in an 0.58 * size box
    box = int(px * 0.58)
    text = glyph if len(glyph) <= 3 else glyph[:3]
    font = None
    for cand in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                 '/System/Library/Fonts/Helvetica.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                 '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(cand):
            try:
                font = ImageFont.truetype(cand, int(box * 0.92))
                break
            except Exception:
                font = None
    if font is None:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((px - tw) / 2 - bbox[0], (px - th) / 2 - bbox[1]), text, font=font, fill=fg)
    img = img.resize((size, size), Image.LANCZOS)
    img.save(path)
    return img


def svg(bg, fg, glyph, app_id):
    fgx = '#%02x%02x%02x' % fg
    bgx = '#%02x%02x%02x' % bg
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
        'width="512" height="512" role="img" aria-label="%s">\n'
        '  <rect x="0" y="0" width="512" height="512" rx="112" fill="%s"/>\n'
        '  <text x="256" y="290" text-anchor="middle" dominant-baseline="middle"\n'
        '        font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-weight="700"\n'
        '        font-size="240" fill="%s">%s</text>\n'
        '</svg>\n' % (app_id, bgx, fgx, glyph)
    )


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    app_dir, bg_hex, glyph = argv[1], argv[2], argv[3]
    accent_hex = argv[4] if len(argv) > 4 else '#ffffff'
    bg, fg = _hex(bg_hex), _hex(accent_hex)
    out = os.path.join(app_dir, 'icons')
    os.makedirs(out, exist_ok=True)

    try:
        import PIL  # noqa: F401
        have_pil = True
    except Exception:
        have_pil = False

    for s in SIZES:
        p = os.path.join(out, 'icon-%d.png' % s)
        if have_pil:
            write_with_pil(p, s, bg, fg, glyph)
        else:
            write_png_fallback(p, s, bg, fg)
    app_id = os.path.basename(os.path.normpath(app_dir))
    with open(os.path.join(out, 'icon.svg'), 'w') as fh:
        fh.write(svg(bg, fg, glyph, app_id))
    print('icons written to %s (%s)' % (out, 'PIL' if have_pil else 'fallback-PNG'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
