#!/usr/bin/env python3
"""Contract test for the external bridge's DECON pixel-format selection.

The bridge does not program the DPP directly.  It passes a caller-side
DECON format to S3CFB_WIN_CONFIG; the vendor kernel then translates it with
dpu_translate_fmt_to_dpp() before writing the IDMA format register.

The normal bridge word is 0xAARRGGBB (memory B,G,R,A).  That word must reach
IDMA ARGB_8888, which requires caller BGRA_8888 (3):
    caller BGRA_8888 (3) -> IDMA ARGB_8888 (0)

The diagnostic --color-order abgr word is 0xAABBGGRR (memory R,G,B,A) and
must reach IDMA ABGR_8888 (1), which requires caller RGBA_8888 (2):
    caller RGBA_8888 (2) -> IDMA ABGR_8888 (1)

Passing caller ARGB_8888 was the blue-overlay regression: it translated to
IDMA BGRA_8888, whose 0xAABBGGRR/bytes A,R,G,B interpretation reads the opaque
0xff alpha byte as blue for every pixel.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(BASE, "..", ".."))
SRC = os.path.join(BASE, "bin", "nuxel-wl-fb-ext.c")
HELPER = os.path.join(
    REPO, "kernel", "s10plus", ".build", "src", "drivers", "video",
    "fbdev", "exynos", "dpu20", "helper.c")


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


def source_checks():
    text = open(SRC, encoding="utf-8").read()
    m = re.search(r"#define\s+DEXT_FMT_BGRA8888\s+(\d+)", text)
    check(bool(m), "DEXT_FMT_BGRA8888 is defined")
    check(int(m.group(1)) == 3, "caller BGRA_8888 is DECON enum value 3")
    m = re.search(r"#define\s+DEXT_FMT_RGBA8888\s+(\d+)", text)
    check(bool(m), "DEXT_FMT_RGBA8888 is defined")
    check(int(m.group(1)) == 2, "caller RGBA_8888 is DECON enum value 2")

    normal = re.search(
        r"if\s*\(color_order_argb\)\s*\{[^}]*"
        r"fb\.decon_format\s*=\s*DEXT_FMT_(\w+);", text, re.S)
    check(bool(normal), "normal packing selects a DECON format")
    check(normal.group(1) == "BGRA8888",
          "normal 0xAARRGGBB packing selects caller BGRA_8888")
    diag = re.search(
        r"else\s*\{[^}]*fb\.decon_format\s*=\s*DEXT_FMT_(\w+);", text, re.S)
    check(bool(diag), "diagnostic packing selects a DECON format")
    check(diag.group(1) == "RGBA8888",
          "diagnostic 0xAABBGGRR packing selects caller RGBA_8888")


def kernel_translation_checks():
    if not os.path.exists(HELPER):
        print("  SKIP kernel helper.c not present in this checkout")
        return
    text = open(HELPER, encoding="utf-8").read()
    body = text[text.find("u32 dpu_translate_fmt_to_dpp"):]
    body = body[:body.find("u32 dpu_get_bpp")]
    check("case DECON_PIXEL_FORMAT_BGRA_8888:\n\t\treturn DECON_PIXEL_FORMAT_ARGB_8888;"
          in body, "kernel translates caller BGRA -> IDMA ARGB")
    check("case DECON_PIXEL_FORMAT_RGBA_8888:\n\t\treturn DECON_PIXEL_FORMAT_ABGR_8888;"
          in body, "kernel translates caller RGBA -> IDMA ABGR")


def main():
    print("test-colour-format")
    source_checks()
    kernel_translation_checks()
    print("PASS colour-format contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
