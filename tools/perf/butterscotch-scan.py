#!/usr/bin/env python3
"""Butterscotch performance scanner — repeatable static metrics for the home UI.

Measures the expensive software-rendered surface of pwa/nuxel-home without a
physical device: backdrop/box blur, persistent compositing hints, animation
timers, gradient stacks, and decoded-asset cost for the navigation artwork.

Exit code 0 always (this is a measuring instrument, not a gate). JSON on stdout.
"""
from __future__ import annotations
import json, os, re, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "pwa" / "nuxel-home"
CSS = sorted((HOME / "css").glob("*.css"))
JS = sorted((HOME / "js").glob("*.js"))

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def png_dim(p: Path):
    try:
        d = p.read_bytes()[:26]
        if d[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        w, h = struct.unpack(">II", d[16:24])
        return {"w": w, "h": h, "bytes": p.stat().st_size, "rgba_est_bytes": w * h * 4}
    except OSError:
        return None

def count(regex, text):
    return len(re.findall(regex, text))

metrics = {"files": {"css": len(CSS), "js": len(JS)}}

css_text = {p.name: read(p) for p in CSS}
js_text = {p.name: read(p) for p in JS}

# Expensive raster effects
metrics["backdrop_filter_css"] = sum(count(r"backdrop-filter", t) for t in css_text.values())
metrics["backdrop_filter_js"] = sum(count(r"backdrop-filter", t) for t in js_text.values())
metrics["blur_px_css"] = sum(count(r"blur\(\s*\d+px", t) for t in css_text.values())
metrics["blur_px_js"] = sum(count(r"blur\(\s*\d+px", t) for t in js_text.values())
metrics["filter_css"] = sum(count(r"filter\s*:", t) for t in css_text.values())
metrics["will_change_css"] = sum(count(r"will-change\s*:", t) for t in css_text.values())
metrics["box_shadow_css"] = sum(count(r"box-shadow\s*:", t) for t in css_text.values())
metrics["text_shadow_css"] = sum(count(r"text-shadow\s*:", t) for t in css_text.values())
metrics["gradients_css"] = sum(count(r"(?:linear|radial)-gradient\(", t) for t in css_text.values())
metrics["infinite_animations_css"] = sum(count(r"animation\s*:[^;]*\binfinite\b", t) for t in css_text.values())
metrics["console_log_js"] = sum(count(r"console\.log\(", t) for t in js_text.values())
metrics["set_interval_js"] = sum(count(r"setInterval\(", t) for t in js_text.values())
metrics["request_animation_frame_js"] = sum(count(r"requestAnimationFrame\(", t) for t in js_text.values())

# Largest box-shadow blur radii (CSS + inline JS). Inline JS styles are the
# transient OSD/bootlog/notification panels, which are still software rasterised.
blurs = []
for name, src in list(css_text.items()) + list(js_text.items()):
    for m in re.findall(r"box-shadow:\s*([^;{}]+)", src):
        for px in re.findall(r"\b(\d+)px\b", m):
            blurs.append(int(px))
metrics["box_shadow_blur_px_max"] = max(blurs) if blurs else 0
metrics["box_shadow_blur_px_gt8"] = sum(1 for b in blurs if b > 8)
metrics["box_shadow_blur_px_gt8_css"] = 0
for name, src in css_text.items():
    for m in re.findall(r"box-shadow:\s*([^;{}]+)", src):
        for px in re.findall(r"\b(\d+)px\b", m):
            if int(px) > 8:
                metrics["box_shadow_blur_px_gt8_css"] += 1

# Navigation artwork decoded cost (canonical root + the local copies the
# DOM nav actually loads after the pwnage-37000 asset pass).
nav_art = {}
for rel in ["assets/button-left.png", "assets/button-middle.png", "assets/button-right.png"]:
    nav_art[rel] = png_dim(ROOT / rel)
for rel in ["assets/button-left.png", "assets/button-middle.png", "assets/button-right.png"]:
    nav_art["pwa/nuxel-home/" + rel] = png_dim(HOME / rel)
metrics["nav_art"] = nav_art
metrics["nav_art_total_bytes_root"] = sum(v["bytes"] for v in nav_art.values() if v)

# What the DOM nav actually references in index.html right now.
index = read(HOME / "index.html")
used = {}
for src in re.findall(r'<button[^>]+data-nav[^>]+><img\s+src="([^"]+)"', index):
    qs = src.split("?")[0]
    fs = (HOME / qs) if not qs.startswith("/") else (ROOT / qs.lstrip("/"))
    dim = png_dim(fs)
    used[src] = {"file": str(fs.relative_to(ROOT)), **dim} if dim else {"file": str(fs.relative_to(ROOT)), "missing": True}
metrics["nav_art_used_by_index"] = used
metrics["nav_art_used_total_bytes"] = sum(v.get("bytes", 0) for v in used.values())
metrics["nav_art_used_rgba_est_bytes"] = sum(v.get("rgba_est_bytes", 0) for v in used.values())

print(json.dumps(metrics, indent=2, sort_keys=True))
