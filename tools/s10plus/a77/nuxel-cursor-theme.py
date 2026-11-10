#!/usr/bin/env python3
"""Generate the Nuxel cyan Xcursor theme.

The S10+ phoc session reads org.gnome.desktop.interface cursor-theme.  A
Nuxel-branded theme lives in /usr/share/icons/nuxel and is generated here with
no external dependencies (the phone image has no xcursorgen).  Xcursor files
contain one ARGB image per nominal size; 64 is required for the 32 logical-px
cursor at phoc's scale=2 output.
"""

import argparse
import math
import os
import struct

MAGIC = 0x72756358  # 'Xcur'
IMAGE_TYPE = 0xFFFD0002
SIZES = (24, 32, 48, 64, 96)

# Nuxel palette (matches the launcher's cyan accent).
FILL_TOP = (0x8B, 0xF7, 0xFF)
FILL_BOTTOM = (0x00, 0xB8, 0xDD)
OUTLINE = (0x02, 0x18, 0x22)
GLOW = (0x29, 0xD8, 0xF4)


class Shape:
    def __init__(self, polys=(), lines=(), rings=(), hotspot=(0.5, 0.5),
                 line_width=0.10, glow=0.10, outline=0.055):
        self.polys = [list(p) for p in polys]
        self.lines = list(lines)
        self.rings = list(rings)
        self.hotspot = hotspot
        self.line_width = line_width
        self.glow = glow
        self.outline = outline


def _dist_seg(px, py, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    wx, wy = px - x1, py - y1
    d = vx * vx + vy * vy
    if d <= 1e-12:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / d))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


def _inside_poly(px, py, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _poly_sdf(px, py, poly):
    d = min(_dist_seg(px, py, *poly[i], *poly[(i + 1) % len(poly)])
            for i in range(len(poly)))
    return -d if _inside_poly(px, py, poly) else d


def _rect_sdf(px, py, x0, y0, x1, y1):
    return _poly_sdf(px, py, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _rounded_rect_sdf(px, py, x0, y0, x1, y1, r):
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    hx, hy = (x1 - x0) / 2.0 - r, (y1 - y0) / 2.0 - r
    qx, qy = abs(px - cx) - hx, abs(py - cy) - hy
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    inside = min(max(qx, qy), 0.0)
    return outside + inside - r


def _ring_sdf(px, py, cx, cy, radius, width):
    return abs(math.hypot(px - cx, py - cy) - radius) - width / 2.0


def _shape_sdf(shape, px, py):
    ds = []
    for poly in shape.polys:
        ds.append(_poly_sdf(px, py, poly))
    for x1, y1, x2, y2 in shape.lines:
        ds.append(_dist_seg(px, py, x1, y1, x2, y2) - shape.line_width / 2.0)
    for cx, cy, radius, width in shape.rings:
        ds.append(_ring_sdf(px, py, cx, cy, radius, width))
    return min(ds) if ds else 1.0


def _mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _over(dst, src):
    """dst/src are (r,g,b,a) floats with premultiplied rgb."""
    sr, sg, sb, sa = src
    dr, dg, db, da = dst
    oa = sa + da * (1.0 - sa)
    if oa <= 1e-12:
        return (0.0, 0.0, 0.0, 0.0)
    return ((sr + dr * (1.0 - sa)) / oa,
            (sg + dg * (1.0 - sa)) / oa,
            (sb + db * (1.0 - sa)) / oa,
            oa)


def _sample(shape, x, y, size):
    """Return premultiplied RGBA for one subpixel in normalized coordinates."""
    d = _shape_sdf(shape, x, y)
    fill_t = max(0.0, min(1.0, (y - 0.05) / 0.90))
    fill = _mix(FILL_TOP, FILL_BOTTOM, fill_t)
    rgba = (0.0, 0.0, 0.0, 0.0)

    if d < shape.outline + shape.glow:
        t = max(0.0, min(1.0, (shape.outline + shape.glow - d) / max(shape.glow, 1e-6)))
        a = 0.28 * t * t
        rgba = _over(rgba, (GLOW[0] / 255.0 * a, GLOW[1] / 255.0 * a,
                            GLOW[2] / 255.0 * a, a))
    if d < shape.outline:
        rgba = _over(rgba, (OUTLINE[0] / 255.0, OUTLINE[1] / 255.0,
                            OUTLINE[2] / 255.0, 1.0))
    if d <= 0.0:
        rgba = _over(rgba, (fill[0] / 255.0, fill[1] / 255.0, fill[2] / 255.0, 1.0))
    return rgba


def render(shape, size):
    """Rasterise with 4x4 supersampling; returns (w, h, xhot, yhot, argb pixels)."""
    ss = 4 if size <= 32 else (3 if size <= 64 else 2)
    w = h = size
    acc = [0.0, 0.0, 0.0, 0.0]
    data = bytearray()
    for py in range(h):
        for px in range(w):
            r = g = b = a = 0.0
            for sy in range(ss):
                for sx in range(ss):
                    nx = (px + (sx + 0.5) / ss) / w
                    ny = (py + (sy + 0.5) / ss) / h
                    sr, sg, sb, sa = _sample(shape, nx, ny, size)
                    r += sr * sa
                    g += sg * sa
                    b += sb * sa
                    a += sa
            n = ss * ss
            r, g, b, a = r / n, g / n, b / n, a / n
            if a > 1e-6:
                # un-premultiply, then re-premultiply to 8-bit values
                rr = max(0, min(255, int(round(r / a * 255.0))))
                gg = max(0, min(255, int(round(g / a * 255.0))))
                bb = max(0, min(255, int(round(b / a * 255.0))))
                aa = max(0, min(255, int(round(a * 255.0))))
                pr = (rr * aa + 127) // 255
                pg = (gg * aa + 127) // 255
                pb = (bb * aa + 127) // 255
            else:
                pr = pg = pb = aa = 0
            data += struct.pack('<I', (aa << 24) | (pr << 16) | (pg << 8) | pb)
    xhot = int(round(shape.hotspot[0] * size))
    yhot = int(round(shape.hotspot[1] * size))
    return size, size, xhot, yhot, bytes(data)


def make_xcursor(shape):
    images = [render(shape, s) for s in SIZES]
    ntoc = len(images)
    pos = 16 + 12 * ntoc
    toc = bytearray()
    chunks = bytearray()
    for w, h, xhot, yhot, pixels in images:
        toc += struct.pack('<III', IMAGE_TYPE, w, pos)
        chunk = struct.pack('<IIIIIIIII', 36, IMAGE_TYPE, w, 1, w, h,
                            xhot, yhot, 50) + pixels
        chunks += chunk
        pos += len(chunk)
    return (struct.pack('<IIII', MAGIC, 16, 1, ntoc) + bytes(toc) +
            bytes(chunks))


def write_xcursor(path, shape):
    with open(path, 'wb') as f:
        f.write(make_xcursor(shape))


def arrow(hotspot=(0.11, 0.05)):
    return Shape(
        polys=[[(0.12, 0.06), (0.12, 0.83), (0.30, 0.64), (0.43, 0.96),
                (0.56, 0.90), (0.43, 0.60), (0.70, 0.59)]],
        hotspot=hotspot, glow=0.12, outline=0.060, line_width=0.08)


def ibeam():
    return Shape(
        polys=[[(0.34, 0.14), (0.66, 0.14), (0.66, 0.22), (0.58, 0.22),
                (0.58, 0.78), (0.66, 0.78), (0.66, 0.86), (0.34, 0.86),
                (0.34, 0.78), (0.42, 0.78), (0.42, 0.22), (0.34, 0.22)]],
        hotspot=(0.5, 0.5), glow=0.10, outline=0.055)


def crosshair():
    return Shape(
        polys=[[(0.16, 0.46), (0.84, 0.46), (0.84, 0.54), (0.16, 0.54)],
               [(0.46, 0.16), (0.54, 0.16), (0.54, 0.84), (0.46, 0.84)]],
        hotspot=(0.5, 0.5), glow=0.10, outline=0.055)


def move():
    return Shape(
        polys=[[(0.50, 0.09), (0.40, 0.28), (0.46, 0.28), (0.46, 0.46),
                (0.54, 0.46), (0.54, 0.28), (0.60, 0.28)],
               [(0.50, 0.91), (0.40, 0.72), (0.46, 0.72), (0.46, 0.54),
                (0.54, 0.54), (0.54, 0.72), (0.60, 0.72)],
               [(0.09, 0.50), (0.28, 0.40), (0.28, 0.46), (0.46, 0.46),
                (0.46, 0.54), (0.28, 0.54), (0.28, 0.60)],
               [(0.91, 0.50), (0.72, 0.40), (0.72, 0.46), (0.54, 0.46),
                (0.54, 0.54), (0.72, 0.54), (0.72, 0.60)]],
        hotspot=(0.5, 0.5), glow=0.10, outline=0.050)


def ew_resize():
    return Shape(
        polys=[[(0.10, 0.50), (0.32, 0.33), (0.32, 0.44), (0.50, 0.44),
                (0.50, 0.56), (0.32, 0.56), (0.32, 0.67)],
               [(0.90, 0.50), (0.68, 0.33), (0.68, 0.44), (0.50, 0.44),
                (0.50, 0.56), (0.68, 0.56), (0.68, 0.67)]],
        hotspot=(0.5, 0.5), glow=0.10, outline=0.050)


def ns_resize():
    return Shape(
        polys=[[(0.50, 0.10), (0.33, 0.32), (0.44, 0.32), (0.44, 0.50),
                (0.56, 0.50), (0.56, 0.32), (0.67, 0.32)],
               [(0.50, 0.90), (0.33, 0.68), (0.44, 0.68), (0.44, 0.50),
                (0.56, 0.50), (0.56, 0.68), (0.67, 0.68)]],
        hotspot=(0.5, 0.5), glow=0.10, outline=0.050)


def diag_resize(nwse=True):
    if nwse:
        return Shape(
            lines=[(0.22, 0.22, 0.78, 0.78)],
            polys=[[(0.12, 0.12), (0.45, 0.21), (0.21, 0.45)],
                   [(0.88, 0.88), (0.55, 0.79), (0.79, 0.55)]],
            hotspot=(0.5, 0.5), line_width=0.11, glow=0.10, outline=0.050)
    return Shape(
        lines=[(0.78, 0.22, 0.22, 0.78)],
        polys=[[(0.88, 0.12), (0.55, 0.21), (0.79, 0.45)],
               [(0.12, 0.88), (0.45, 0.79), (0.21, 0.55)]],
        hotspot=(0.5, 0.5), line_width=0.11, glow=0.10, outline=0.050)


def wait():
    return Shape(
        rings=[(0.5, 0.5, 0.30, 0.11)],
        polys=[[(0.46, 0.19), (0.54, 0.19), (0.54, 0.30), (0.46, 0.30)],
               [(0.46, 0.70), (0.54, 0.70), (0.54, 0.81), (0.46, 0.81)]],
        hotspot=(0.5, 0.5), glow=0.10, outline=0.050)


def not_allowed():
    return Shape(
        rings=[(0.5, 0.5, 0.32, 0.10)],
        lines=[(0.27, 0.73, 0.73, 0.27)],
        hotspot=(0.5, 0.5), line_width=0.10, glow=0.10, outline=0.050)


def hand():
    return Shape(
        polys=[[(0.42, 0.18), (0.56, 0.18), (0.56, 0.48), (0.68, 0.44),
                (0.75, 0.50), (0.75, 0.68), (0.66, 0.86), (0.36, 0.86),
                (0.27, 0.67), (0.32, 0.49), (0.42, 0.53)]],
        hotspot=(0.50, 0.18), glow=0.11, outline=0.055)


SHAPES = {
    'arrow': arrow(),
    'ibeam': ibeam(),
    'cross': crosshair(),
    'move': move(),
    'ew': ew_resize(),
    'ns': ns_resize(),
    'nwse': diag_resize(True),
    'nesw': diag_resize(False),
    'wait': wait(),
    'notallowed': not_allowed(),
    'hand': hand(),
}

# Wayland cursor-shape names and legacy Xcursor names.
CURSORS = {
    'left_ptr': 'arrow', 'default': 'arrow', 'arrow': 'arrow',
    'top_left_arrow': 'arrow', 'draft': 'arrow', 'top_left_corner': 'arrow',
    'bottom_left_corner': 'arrow', 'bottom_right_corner': 'arrow',
    'top_right_corner': 'arrow', 'left_side': 'arrow', 'right_side': 'arrow',
    'top_side': 'arrow', 'bottom_side': 'arrow', 'sb_left_arrow': 'arrow',
    'sb_right_arrow': 'arrow', 'sb_up_arrow': 'arrow', 'sb_down_arrow': 'arrow',
    'text': 'ibeam', 'xterm': 'ibeam', 'vertical-text': 'ibeam',
    'crosshair': 'cross', 'cross': 'cross', 'X_cursor': 'cross', 'cell': 'cross',
    'cross_reverse': 'cross', 'diamond_cross': 'cross', 'tcross': 'cross',
    'move': 'move', 'fleur': 'move', 'all-scroll': 'move', 'size_all': 'move',
    'ew-resize': 'ew', 'e-resize': 'ew', 'w-resize': 'ew',
    'col-resize': 'ew', 'sb_h_double_arrow': 'ew', 'h_double_arrow': 'ew',
    'ns-resize': 'ns', 'n-resize': 'ns', 's-resize': 'ns',
    'row-resize': 'ns', 'sb_v_double_arrow': 'ns', 'v_double_arrow': 'ns',
    'nwse-resize': 'nwse', 'nw-resize': 'nwse', 'se-resize': 'nwse',
    'size_fdiag': 'nwse', 'bd_double_arrow': 'nwse',
    'nesw-resize': 'nesw', 'ne-resize': 'nesw', 'sw-resize': 'nesw',
    'size_bdiag': 'nesw', 'fd_double_arrow': 'nesw',
    'wait': 'wait', 'watch': 'wait', 'progress': 'wait', 'left_ptr_watch': 'wait',
    'not-allowed': 'notallowed', 'no-drop': 'notallowed',
    'crossed_circle': 'notallowed', 'forbidden': 'notallowed',
    'pointer': 'hand', 'hand1': 'hand', 'hand2': 'hand',
    'grab': 'hand', 'grabbing': 'hand', 'openhand': 'hand', 'closedhand': 'hand',
    'help': 'arrow', 'question_arrow': 'arrow', 'context-menu': 'arrow',
    'copy': 'arrow', 'alias': 'arrow', 'dnd-ask': 'arrow', 'dnd-move': 'arrow',
    'zoom-in': 'arrow', 'zoom-out': 'arrow', 'plus': 'cross', 'minus': 'cross',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', default='/usr/share/icons/nuxel')
    ap.add_argument('--preview', help='write a PPM preview for one cursor')
    args = ap.parse_args()

    cursors_dir = os.path.join(args.dest, 'cursors')
    os.makedirs(cursors_dir, exist_ok=True)
    theme = os.path.join(args.dest, 'index.theme')
    with open(theme, 'w') as f:
        f.write('[Icon Theme]\nName=Nuxel\nComment=Nuxel cyan cursors\n'
                'Inherits=Adwaita\n')

    # Many legacy names share a shape: render each shape (and each size) once.
    cache = {}
    for name, shape_name in sorted(CURSORS.items()):
        if shape_name not in cache:
            print('rendering %s...' % shape_name, flush=True)
            cache[shape_name] = make_xcursor(SHAPES[shape_name])
        path = os.path.join(cursors_dir, name)
        tmp = path + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(cache[shape_name])
        os.replace(tmp, path)

    if args.preview:
        name = args.preview
        shape = SHAPES[CURSORS.get(name, name)]
        w, h, xh, yh, data = render(shape, 64)
        with open(args.preview + '.ppm', 'wb') as f:
            f.write(b'P6\n%d %d\n255\n' % (w, h))
            for i in range(0, len(data), 4):
                px = struct.unpack('<I', data[i:i + 4])[0]
                a = (px >> 24) & 0xff
                r = ((px >> 16) & 0xff) * a // 255
                g = ((px >> 8) & 0xff) * a // 255
                b = (px & 0xff) * a // 255
                # put cursor over a dark checker so the preview is readable
                bg = 20 if ((i // 4 // w) // 8 + (i // 4) % w // 8) % 2 else 35
                f.write(bytes((r + bg * (255 - a) // 255,
                               g + bg * (255 - a) // 255,
                               b + bg * (255 - a) // 255)))

    count = len(CURSORS) * len(SIZES)
    print('NUXEL_CURSOR_THEME_OK dest=%s cursors=%d images=%d' %
          (args.dest, len(CURSORS), count))


if __name__ == '__main__':
    main()
