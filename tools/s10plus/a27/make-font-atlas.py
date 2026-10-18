#!/usr/bin/env python3
"""make-font-atlas.py — rasterise the Nuxel UI font into an embedded bitmap atlas.

WHY: the framebuffer UI used a scaled 5x7 bitmap font.  At this panel's 4x
phone scale that renders as block letters and cannot be sized to fit a measured
box.  The VM/PWA interface uses a system sans (Segoe UI / Roboto / Cantarell);
the free stand-in used here is **DejaVu Sans**, which is redistributable
(Bitstream Vera licence, DejaVu changes public domain) — see
tools/s10plus/a27/assets/fonts/LICENSE-DejaVu.txt.  No proprietary system font
is copied or rasterised.

WHAT IT EMITS (deterministic, no timestamps):
  tools/s10plus/a27/generated/nuxel-font-atlas.c
    * one tight-bbox 8-bit coverage bitmap per glyph, per size;
    * per-size metrics (ascent, descent, line height);
    * per-glyph advance + offsets, so the C renderer can measure text exactly
      before it draws it (that is what makes "fits in the box" a measurement and
      not a guess).

Sizes are rendered at 4x the design size because this panel is exactly
1440x3040 = 4 x (360x760) design units; the C renderer blits 1:1 there and
box-filters for other scales.

Usage: make-font-atlas.py [--out FILE] [--font TTF] [--report FILE]
"""
import argparse
import hashlib
import json
import os
import struct
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required (pip install pillow)")

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DEFAULT_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "fonts", "DejaVuSans.ttf")
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "generated", "nuxel-font-atlas.c")
ATLAS_SCALE = 4                      # the panel is 4x the 360x760 design space
SIZES = [11, 13, 14, 16, 22, 28]     # design (logical) px, VM/PWA token range
FIRST, LAST = 32, 126                # printable ASCII


def build_glyphs(font_path):
    sizes = []
    for design_px in SIZES:
        px = design_px * ATLAS_SCALE
        f = ImageFont.truetype(font_path, px)
        ascent, descent = f.getmetrics()
        glyphs = []
        for cp in range(FIRST, LAST + 1):
            ch = chr(cp)
            # Half-up rounding, not Python's banker's rounding.  FreeType
            # returns exact halves for some glyphs (measured: 22px 't' =
            # 34.5), so round() produced 34 while an older Pillow produced 35
            # and the "reproducible" atlas gate drifted by one advance.  The
            # conversion is explicit and version-independent now.
            advance = int(f.getlength(ch) + 0.5)
            bbox = f.getbbox(ch)            # (l, t, r, b) with origin at (0, ascent-offset)
            if bbox is None:
                glyphs.append(dict(w=0, h=0, xoff=0, yoff=0, adv=max(advance, 0), bits=b""))
                continue
            l, t, r, b = bbox
            w, h = max(r - l, 0), max(b - t, 0)
            if w == 0 or h == 0:
                glyphs.append(dict(w=0, h=0, xoff=0, yoff=0, adv=max(advance, 0), bits=b""))
                continue
            img = Image.new("L", (w, h), 0)
            ImageDraw.Draw(img).text((-l, -t), ch, font=f, fill=255)
            # 4-bit coverage (16 levels of antialiasing) packed two pixels per
            # byte: half the size of an 8-bit atlas for no visible difference at
            # these sizes, and the renderer expands nibble*17 -> 0..255.
            cov = bytes((v >> 4) & 0xF for v in img.tobytes())
            packed = bytearray()
            for i in range(0, len(cov), 2):
                hi = cov[i]
                lo = cov[i + 1] if i + 1 < len(cov) else 0
                packed.append((hi << 4) | lo)
            glyphs.append(dict(w=w, h=h, xoff=l, yoff=t - ascent, adv=max(advance, 1),
                               bits=bytes(packed)))
        sizes.append(dict(design=design_px, px=px, ascent=ascent, descent=descent,
                          glyphs=glyphs))
    return sizes


def emit(sizes, out_path, font_path):
    bits = bytearray()
    glyph_records = []          # (size_index, (w,h,xoff,yoff,adv,off))
    for si, s in enumerate(sizes):
        recs = []
        for g in s["glyphs"]:
            off = len(bits)
            bits += g["bits"]
            while len(bits) % 4:            # keep bitmaps word-aligned
                bits.append(0)
            recs.append((g["w"], g["h"], g["xoff"], g["yoff"], g["adv"], off))
        glyph_records.append(recs)

    body = bytearray()
    table_offsets = []
    for recs in glyph_records:
        table_offsets.append(len(body)//16)   # record index, not a byte offset
        for (w, h, xoff, yoff, adv, off) in recs:
            # <HHhh B xxx I : exactly the 16 bytes struct nuxel_glyph occupies
            # (w,h,xoff,yoff,adv,3 pad,off) so the C side can use the real type.
            body += struct.pack("<HHhhB3xI", w, h, xoff, yoff, adv, off)

    def carr(name, data, per=16):
        out = ["static const unsigned char %s[%d] = {" % (name, len(data))]
        for i in range(0, len(data), per):
            out.append("  " + ",".join("0x%02x" % b for b in data[i:i + per]) + ",")
        out.append("};")
        return "\n".join(out)

    L = []
    L.append("/* GENERATED by tools/s10plus/a27/make-font-atlas.py — do not edit by hand.")
    L.append(" * Font: %s" % os.path.relpath(font_path, ROOT))
    L.append(" * sha256 %s" % hashlib.sha256(open(font_path, "rb").read()).hexdigest())
    L.append(" * Licence: Bitstream Vera (redistributable) + DejaVu public-domain"
             " changes.")
    L.append(" * Sizes are rendered at %dx the design size (this panel is exactly"
             " 4 x 360x760). */" % ATLAS_SCALE)
    L.append("#define NUXEL_FONT_COVERAGE_BITS 4   /* nibble per pixel, x17 -> 0..255 */")
    L.append("#define NUXEL_FONT_ATLAS_SCALE %d" % ATLAS_SCALE)
    L.append("#define NUXEL_FONT_FIRST %d" % FIRST)
    L.append("#define NUXEL_FONT_COUNT %d" % (LAST - FIRST + 1))
    L.append("#define NUXEL_FONT_NSIZES %d" % len(sizes))
    L.append("struct nuxel_glyph { unsigned short w,h; signed short xoff,yoff;"
             " unsigned char adv; unsigned int off; };")
    L.append("struct nuxel_font { unsigned short design,px; signed short ascent,descent;"
             " unsigned int goff, glen; };")
    L.append("/* glyph coverage bitmaps: 4 bits per pixel, two pixels per byte, "
             "little-nibble-first */")
    L.append(carr("NUXEL_FONT_BITS", bytes(bits)))
    L.append("static const struct nuxel_glyph NUXEL_FONT_GLYPHS[%d] = {"
             % (len(body) // 16))
    for i in range(0, len(body), 16):
        w, h, xo, yo, adv, off = struct.unpack_from("<HHhhB3xI", body, i)
        L.append("  {%d,%d,%d,%d,%d,%du}," % (w, h, xo, yo, adv, off))
    L.append("};")
    L.append("static const struct nuxel_font NUXEL_FONTS[NUXEL_FONT_NSIZES] = {")
    for si, s in enumerate(sizes):
        L.append("  {%d,%d,%d,%d,%du,%du},   /* design %dpx, line %dpx */"
                 % (s["design"], s["px"], s["ascent"], s["descent"], table_offsets[si],
                    (LAST - FIRST + 1), s["design"], s["ascent"] + s["descent"]))
    L.append("};")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w").write("\n".join(L) + "\n")
    return len(bits), len(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    if not os.path.exists(a.font):
        sys.exit("font not found: %s" % a.font)
    sizes = build_glyphs(a.font)
    nbits, nglyphs = emit(sizes, a.out, a.font)
    total = nbits + nglyphs
    rep = dict(font=os.path.relpath(a.font, ROOT),
               font_sha256=hashlib.sha256(open(a.font, "rb").read()).hexdigest(),
               out=os.path.relpath(a.out, ROOT),
               out_sha256=hashlib.sha256(open(a.out, "rb").read()).hexdigest(),
               atlas_scale=ATLAS_SCALE, charset="ASCII %d..%d" % (FIRST, LAST),
               sizes=[dict(design=s["design"], px=s["px"], ascent=s["ascent"],
                           descent=s["descent"]) for s in sizes],
               bitmap_bytes=nbits, glyph_table_bytes=nglyphs, total_bytes=total)
    print(json.dumps(rep, indent=2))
    if a.report:
        open(a.report, "w").write(json.dumps(rep, indent=2) + "\n")
    print("FONT_ATLAS_OK %d bytes" % total)


if __name__ == "__main__":
    main()
