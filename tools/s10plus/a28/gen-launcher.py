#!/usr/bin/env python3
"""gen-launcher.py — generate the S10+ launcher tables from the LAUNCHER'S OWN
sources.  Nothing in this file invents an app, a colour or a geometry token.

AUTHORITATIVE INPUTS (the same files the UTM VM serves and renders):

  pwa/nuxel-home/js/apps.js          the launcher's app registry (NUXEL_APPS)
  pwa/nuxel-home/css/style.css       :root design tokens (colours, sizes)
  shell/nuxel-home-native/nuxel_home/app_registry.json
                                     the native front-end's registry (used here
                                     ONLY to cross-check ids/names/native paths)

EMITTED:

  tools/s10plus/a28/generated/nuxel-launcher.h   C tables for tools/s10plus/nuxel-ui.c
  tools/s10plus/a28/generated/nuxel-launcher.json  machine-readable report

ORDERING IS NOT INVENTED EITHER.  The PWA computes what it shows from two
methods in js/apps.js:

    getAllApps()   -> [...this.apps.values()].sort((a,b)=>a.name.localeCompare(b.name))
    getDockedApps()-> getAllApps().filter(app => app.docked)

so the grid is (all apps, sorted by name) minus the docked ones and the dock is
the docked ones IN SORTED ORDER.  vm/vm-verify-pwa.sh observed exactly that on
the live VM display: "app grid has 6 item(s), dock has 3 item(s)".

Usage: gen-launcher.py [--check]
  --check  fail (nonzero) if the generated header differs from the one on disk
Exit: 0 ok, 1 mismatch in --check mode, 2 a required input is missing/ambiguous
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
APPS_JS = os.path.join(ROOT, "pwa", "nuxel-home", "js", "apps.js")
STYLE_CSS = os.path.join(ROOT, "pwa", "nuxel-home", "css", "style.css")
NATIVE_JSON = os.path.join(ROOT, "shell", "nuxel-home-native", "nuxel_home",
                           "app_registry.json")
OUT_H = os.path.join(HERE, "generated", "nuxel-launcher.h")
OUT_JSON = os.path.join(HERE, "generated", "nuxel-launcher.json")

# The launcher serves its PWAs from the nuxel-web static server (see
# services/nuxel-web.service: "nuxel-home launcher on :8000").  apps.js stores
# the PWA urls as paths relative to that server's root.
PWA_ORIGIN = "http://127.0.0.1:8000"

# Browser preference order, from shell/nuxel-kiosk/nuxel-home-kiosk (unchanged).
PWA_BROWSERS = ("chromium-browser", "chromium", "firefox", "epiphany")

# Design tokens that the port's C code must agree with (parsed, then asserted).
REQUIRED_TOKENS = ["--bg-primary", "--bg-secondary", "--bg-card", "--bg-card-hover",
                   "--text-primary", "--text-secondary", "--text-accent",
                   "--accent", "--accent-light", "--success", "--warning",
                   "--error", "--info", "--status-bar-height", "--dock-height",
                   "--grid-padding", "--app-icon-size", "--app-icon-radius",
                   "--card-radius", "--button-radius"]
# the base :root block (before any responsive override)
EXPECTED_NUMERIC = {"--status-bar-height": 36, "--dock-height": 80,
                    "--grid-padding": 16, "--app-icon-size": 64,
                    "--app-icon-radius": 16, "--card-radius": 16,
                    "--button-radius": 12}
# ... and what is EFFECTIVE at the phone's CSS width (see parse_root_tokens)
EXPECTED_NUMERIC_EFFECTIVE = {"--status-bar-height": 36, "--dock-height": 80,
                              "--grid-padding": 12, "--app-icon-size": 56,
                              "--app-icon-radius": 16, "--card-radius": 16,
                              "--button-radius": 12}
# the phone panel is 1440x3040 = 4 x (360x760) design units; one design unit is
# one PWA CSS pixel, so this is the width every media query is evaluated at.
VIEWPORT_CSS_W = int(os.environ.get("NUXEL_VIEWPORT_CSS_W", "360"))


def sha256_of(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def parse_nuxel_apps(text):
    """Return the NUXEL_APPS entries in source order, with fields decoded."""
    start = text.find("const NUXEL_APPS = {")
    if start < 0:
        sys.exit("apps.js: 'const NUXEL_APPS = {' not found")
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        sys.exit("apps.js: unbalanced NUXEL_APPS literal")
    body = text[start:end + 1]

    apps = []
    for m in re.finditer(r"\n\s*'([A-Za-z0-9_.\-]+)':\s*\{", body):
        key = m.group(1)
        b0 = m.end() - 1
        d, j = 0, b0
        while j < len(body):
            if body[j] == "{":
                d += 1
            elif body[j] == "}":
                d -= 1
                if d == 0:
                    break
            j += 1
        entry = body[b0:j + 1]
        app = {"key": key}
        for f in re.finditer(r"(\w+)\s*:\s*('([^']*)'|\"([^\"]*)\"|(\d+)|(true|false)|\[([^\]]*)\])",
                             entry):
            name = f.group(1)
            if f.group(3) is not None:
                val = f.group(3)
            elif f.group(4) is not None:
                val = f.group(4)
            elif f.group(5) is not None:
                val = int(f.group(5))
            elif f.group(6) is not None:
                val = f.group(6) == "true"
            else:
                val = [s.strip().strip("'\"") for s in f.group(7).split(",") if s.strip()]
            app[name] = val
        for req in ("id", "name", "icon", "color", "category", "type", "url", "docked"):
            if req not in app:
                sys.exit("apps.js: entry %r is missing %r" % (key, req))
        apps.append(app)
    if not apps:
        sys.exit("apps.js: no entries parsed from NUXEL_APPS")
    return apps


def parse_root_block(block):
    toks = {}
    for m in re.finditer(r"(--[a-z0-9\-]+)\s*:\s*([^;]+);", block):
        toks[m.group(1)] = m.group(2).strip()
    return toks


def parse_root_tokens(css):
    """:root tokens, then the responsive overrides that apply at the phone width.

    style.css carries a breakpoint the launcher really uses:

        @media (max-width: 480px) { :root { --app-icon-size:56px; --grid-padding:12px } }
        @media (min-width: 768px) { :root { --app-icon-size:72px } }

    The VM renders the launcher at 720x1440 physical = 360 CSS px, i.e. INSIDE
    the <=480px breakpoint (measured live with the WebKitGTK geometry harness:
    grid icons 56x56, grid padding 12px).  The S10+ panel is 1440x3040 = 4 x
    (360x760), so the phone is in the same band and must use the same values.
    Returns (base, effective, applied_media).
    """
    start = css.find(":root")
    if start < 0:
        sys.exit("style.css: no :root block")
    end = css.find("}", start)
    base = parse_root_block(css[start:end])
    for t in REQUIRED_TOKENS:
        if t not in base:
            sys.exit("style.css: :root is missing %s" % t)
    effective = dict(base)
    applied = []
    for m in re.finditer(r"@media\s*\(([^)]*)\)\s*\{", css):
        cond = m.group(1).strip()
        # find the matching closing brace of this media block
        depth, i = 1, m.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        body = css[m.end():i - 1]
        mm = re.search(r":root\s*\{([^}]*)\}", body)
        if not mm:
            continue
        over = parse_root_block(mm.group(1))
        if applies(cond, VIEWPORT_CSS_W):
            effective.update(over)
            applied.append(dict(condition=cond, tokens=over))
    return base, effective, applied


def applies(cond, width):
    """Evaluate the width media conditions this file uses."""
    for part in cond.split(" and "):
        part = part.strip()
        m = re.match(r"(min|max)-width\s*:\s*(\d+)px$", part)
        if not m:
            return False            # an unknown feature is never assumed to match
        kind, px = m.group(1), int(m.group(2))
        if kind == "max" and not width <= px:
            return False
        if kind == "min" and not width >= px:
            return False
    return True


def hex_to_rgb(v):
    m = re.match(r"^#([0-9a-fA-F]{6})$", v.strip())
    if not m:
        sys.exit("not a #rrggbb token: %r" % v)
    return int(m.group(1), 16)


def px_to_int(v):
    m = re.match(r"^(-?\d+)px$", v.strip())
    if not m:
        sys.exit("not a px token: %r" % v)
    return int(m.group(1))


def body_background(css):
    """The PWA's own fallback background (body { background-color: ... })."""
    m = re.search(r"html,\s*body\s*\{([^}]*)\}", css)
    if not m:
        sys.exit("style.css: html,body rule not found")
    m2 = re.search(r"background-color\s*:\s*(#[0-9a-fA-F]{6})", m.group(1))
    if not m2:
        sys.exit("style.css: body background-color not found")
    return m2.group(1)


def codepoints(icon):
    cps = [ord(c) for c in icon if ord(c) > 0x7F]
    cps = [c for c in cps if c != 0xFE0F]          # drop VS16: the glyph is the base char
    if not cps:
        sys.exit("icon %r has no non-ASCII codepoint" % icon)
    if len(cps) > 3:
        sys.exit("icon %r has too many codepoints" % icon)
    return cps


def c_escape(s):
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ord(ch) < 0x20:
            out.append("\\x%02x" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


def c_utf8(s):
    """Encode a python str to the exact C byte string (UTF-8, \\xNN for >0x7f)."""
    raw = s.encode("utf-8")
    out = []
    for b in raw:
        if b == 0x5C:
            out.append("\\\\")
        elif b == 0x22:
            out.append('\\"')
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
        else:
            out.append("\\x%02x" % b)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    for p in (APPS_JS, STYLE_CSS, NATIVE_JSON):
        if not os.path.exists(p):
            sys.exit("missing required input: %s" % os.path.relpath(p, ROOT))

    apps_js = open(APPS_JS, encoding="utf-8").read()
    style_css = open(STYLE_CSS, encoding="utf-8").read()
    native = json.load(open(NATIVE_JSON, encoding="utf-8"))

    apps = parse_nuxel_apps(apps_js)
    base_tokens, tokens, applied_media = parse_root_tokens(style_css)
    body_bg = body_background(style_css)

    for tok, want in EXPECTED_NUMERIC.items():
        got = px_to_int(base_tokens[tok])
        if got != want:
            sys.exit("style.css %s is %dpx, the launcher port expects %dpx (base)"
                     % (tok, got, want))
    for tok, want in EXPECTED_NUMERIC_EFFECTIVE.items():
        got = px_to_int(tokens[tok])
        if got != want:
            sys.exit("style.css %s is %dpx at %dpx CSS width, the launcher port "
                     "expects %dpx" % (tok, got, VIEWPORT_CSS_W, want))

    # Reproduce apps.js getAllApps()/getDockedApps(): name sort, then the dock.
    ordered = sorted(apps, key=lambda x: x["name"])
    dock = [x for x in ordered if x["docked"]]
    grid = [x for x in ordered if not x["docked"]]

    # Cross-check the two registries (the PWA's and the native front-end's).
    n_by_id = {x["id"]: x for x in native["apps"]}
    n_by_name = {x["name"]: x for x in native["apps"]}
    for app in ordered:
        match = n_by_id.get(app["key"]) or n_by_name.get(app["name"])
        if match is None:
            sys.exit("app %r exists in apps.js but not in app_registry.json"
                     % app["name"])
        if match["name"] != app["name"]:
            sys.exit("registry disagreement for %s: %r vs %r"
                     % (app["key"], app["name"], match["name"]))
        if match["category"] != app["category"]:
            sys.exit("registry disagreement for category of %s" % app["name"])

    # Registries can disagree about an app's runtime (measured: apps.js calls
    # Camera a native app "nuxel-camera", app_registry.json lists org.nuxel.Camera
    # as the camera-gallery PWA).  Record it; the LAUNCHER (apps.js) is the
    # authority for what is displayed, exactly as the mission requires.
    divergences = []
    for app in ordered:
        nm = n_by_id.get(app["key"]) or n_by_name.get(app["name"])
        nk = nm.get("kind")
        if nk == "native-placeholder":
            nk = "native"
        if nk != app["type"]:
            divergences.append(dict(app=app["name"], apps_js=app["type"] + " " + app["url"],
                                    app_registry_json=nk + " " + (nm.get("url") or
                                                                  nm.get("native_binary") or "")))

    rows = []
    for app in ordered:
        cps = codepoints(app["icon"])
        key = app["key"]
        nmatch = n_by_id.get(key) or n_by_name.get(app["name"])
        native_binary = nmatch.get("native_binary") or ""
        if app["type"] == "pwa":
            url = app["url"]
            if not url.startswith("http"):
                url = PWA_ORIGIN + (url if url.startswith("/") else "/" + url)
            launch_kind = "pwa"
        else:
            url = app["url"]
            launch_kind = "native"
        rows.append(dict(id=key, name=app["name"], desc=app.get("description", ""),
                         icon=app["icon"], icon_cp=cps, color=app["color"],
                         color_rgb=hex_to_rgb(app["color"]), category=app["category"],
                         type=app["type"], kind=launch_kind, url=url,
                         native_binary=native_binary,
                         capabilities=app.get("capabilities", []),
                         docked=bool(app["docked"])))

    L = []
    L.append("/* GENERATED by tools/s10plus/a28/gen-launcher.py — do not edit by hand.")
    L.append(" *")
    L.append(" * Sources (the launcher's OWN files, hashed below):")
    L.append(" *   pwa/nuxel-home/js/apps.js      sha256 %s" % sha256_of(APPS_JS))
    L.append(" *   pwa/nuxel-home/css/style.css  sha256 %s" % sha256_of(STYLE_CSS))
    L.append(" *   shell/nuxel-home-native/nuxel_home/app_registry.json sha256 %s"
             % sha256_of(NATIVE_JSON))
    L.append(" *")
    L.append(" * The app list, order and docking reproduce js/apps.js getAllApps()")
    L.append(" * (sort by name) + getDockedApps() (filter docked):")
    L.append(" *   grid (%d): %s" % (len(grid), ", ".join(x["name"] for x in grid)))
    L.append(" *   dock (%d): %s" % (len(dock), ", ".join(x["name"] for x in dock)))
    L.append(" */")
    L.append("#define NUXEL_LAUNCHER_REV \"A28-utm-launcher-port-1\"")
    L.append("#define NUXEL_LAUNCHER_APP_COUNT %d" % len(rows))
    L.append("#define NUXEL_LAUNCHER_GRID_COUNT %d" % len(grid))
    L.append("#define NUXEL_LAUNCHER_DOCK_COUNT %d" % len(dock))
    L.append("#define NUXEL_LAUNCHER_APPS_JS_SHA256 \"%s\"" % sha256_of(APPS_JS))
    L.append("#define NUXEL_LAUNCHER_STYLE_CSS_SHA256 \"%s\"" % sha256_of(STYLE_CSS))
    L.append("#define NUXEL_LAUNCHER_ORDER \"%s\""
             % ",".join(x["name"] for x in ordered))
    L.append("")
    L.append("/* Design tokens parsed from pwa/nuxel-home/css/style.css :root,")
    L.append(" * EVALUATED AT THE PHONE'S CSS WIDTH (%dpx = 1440/4).  L_* is what")
    L.append(" * the renderer uses; LB_* is the un-overridden :root value, kept so")
    L.append(" * the difference is visible in the header itself. */")
    for m in applied_media:
        L.append("/* media (%s) applies: %s */"
                 % (m["condition"], " ".join("%s:%s" % (k, v) for k, v in m["tokens"].items())))
    for tok in REQUIRED_TOKENS:
        name = "L_" + tok[2:].upper().replace("-", "_")
        base_name = "LB_" + tok[2:].upper().replace("-", "_")
        v = tokens[tok]
        bv = base_tokens[tok]
        if v.startswith("#"):
            L.append("#define %-18s 0x%06x   /* %s: %s */"
                     % (name, hex_to_rgb(v), tok, v))
        elif v.endswith("px"):
            L.append("#define %-18s %-8d /* %s: %s%s */"
                     % (name, px_to_int(v), tok, v,
                        "" if bv == v else "   (base %s overridden at <=480px)" % bv))
            if bv != v:
                L.append("#define %-18s %-8d /* un-overridden :root value */"
                         % (base_name, px_to_int(bv)))
        else:
            L.append("/* %s: %s (non-hex, not emitted) */" % (tok, v))
    L.append("/* status-bar.css: .status-bar { padding: 0 16px } (a literal, not a token) */")
    L.append("#define L_STATUSBAR_PAD 16")
    L.append("/* dock: .dock { padding: 0 20px } - the items are centred, so the port")
    L.append(" * only needs the 20px item gap (launcher.css .dock-items{gap:20px}) */")
    L.append("#define L_DOCK_GAP 20")
    L.append("#define L_BODY_BG          0x%s   /* style.css html,body background-color */"
             % body_bg[1:])
    L.append("")
    L.append("/* One registry row.  icon_cp holds the emoji codepoints from apps.js;")
    L.append(" * color_rgb is apps.js `color`, used exactly as launcher.js does:")
    L.append(" * the tile background is color@0x33 and the glyph is drawn in color. */")
    L.append("struct nuxel_app { const char *id, *name, *desc, *icon, *url, *native_binary;")
    L.append("                    unsigned int color_rgb; unsigned int icon_cp[3];")
    L.append("                    unsigned char docked, kind, category; };")
    L.append("#define NUXEL_APP_KIND_PWA 0")
    L.append("#define NUXEL_APP_KIND_NATIVE 1")
    L.append("#define NUXEL_CAT_SYSTEM 0")
    L.append("#define NUXEL_CAT_COMMUNICATION 1")
    L.append("#define NUXEL_CAT_PRODUCTIVITY 2")
    L.append("#define NUXEL_CAT_MEDIA 3")
    L.append("#define NUXEL_CAT_TOOLS 4")
    cats = {"system": "NUXEL_CAT_SYSTEM", "communication": "NUXEL_CAT_COMMUNICATION",
            "productivity": "NUXEL_CAT_PRODUCTIVITY", "media": "NUXEL_CAT_MEDIA",
            "tools": "NUXEL_CAT_TOOLS"}
    L.append("static const struct nuxel_app NUXEL_APP_LIST[NUXEL_LAUNCHER_APP_COUNT] = {")
    for r in rows:
        cps = ", ".join("%d" % c for c in r["icon_cp"]) + (", 0" * (3 - len(r["icon_cp"])))
        L.append("  { \"%s\", \"%s\", \"%s\", \"%s\"," % (
            c_escape(r["id"]), c_utf8(r["name"]), c_utf8(r["desc"]), c_utf8(r["icon"])))
        L.append("    \"%s\", \"%s\"," % (c_escape(r["url"]), c_escape(r["native_binary"])))
        L.append("    0x%06xu, { %s }, %d, %s, %s }," % (
            r["color_rgb"], cps, 1 if r["docked"] else 0,
            "NUXEL_APP_KIND_PWA" if r["kind"] == "pwa" else "NUXEL_APP_KIND_NATIVE",
            cats[r["category"]]))
    L.append("};")
    row_of = {r["id"]: i for i, r in enumerate(rows)}
    L.append("/* grid index -> NUXEL_APP_LIST index, in apps.js order */")
    L.append("#define NUXEL_LAUNCHER_GRID { %s }"
             % ", ".join(str(row_of[x["key"]]) for x in grid))
    L.append("#define NUXEL_LAUNCHER_DOCK { %s }"
             % ", ".join(str(row_of[x["key"]]) for x in dock))
    L.append("")

    text = "\n".join(L)

    report = dict(
        generator="tools/s10plus/a28/gen-launcher.py",
        inputs={os.path.relpath(p, ROOT): sha256_of(p)
                for p in (APPS_JS, STYLE_CSS, NATIVE_JSON)},
        apps=[dict(id=r["id"], name=r["name"], kind=r["kind"], docked=r["docked"],
                   color=r["color"], icon=r["icon"], icon_cp=r["icon_cp"], url=r["url"],
                   native_binary=r["native_binary"],
                   capabilities=r["capabilities"]) for r in rows],
        grid=[r["name"] for r in grid],
        dock=[r["name"] for r in dock],
        tokens={k: tokens[k] for k in REQUIRED_TOKENS},
        base_tokens={k: base_tokens[k] for k in REQUIRED_TOKENS},
        applied_media=applied_media,
        viewport_css_width=VIEWPORT_CSS_W,
        body_bg=body_bg,
        registry_divergences=divergences,
        out=os.path.relpath(OUT_H, ROOT),
    )

    if a.check:
        cur = open(OUT_H, encoding="utf-8").read() if os.path.exists(OUT_H) else ""
        if cur != text + "\n":
            print("LAUNCHER_REGISTRY_CHECK_FAILED: %s is stale"
                  % os.path.relpath(OUT_H, ROOT), file=sys.stderr)
            return 1
        print("LAUNCHER_REGISTRY_CHECK_OK %s" % os.path.relpath(OUT_H, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT_H), exist_ok=True)
    open(OUT_H, "w", encoding="utf-8").write(text + "\n")
    open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(report, indent=2) + "\n")
    print("LAUNCHER_REGISTRY_OK apps=%d grid=%d dock=%d header=%d bytes"
          % (len(rows), len(grid), len(dock), len(text) + 1))
    if applied_media:
        for m in applied_media:
            print("  media (%s) applied: %s"
                  % (m["condition"], " ".join("%s:%s" % (k, v) for k, v in m["tokens"].items())))
    print("  grid: %s" % ", ".join(r["name"] for r in grid))
    print("  dock: %s" % ", ".join(r["name"] for r in dock))
    if divergences:
        print("  WARNING registry divergence (launcher apps.js is the authority):")
        for d in divergences:
            print("    %s: apps.js=%s | app_registry.json=%s"
                  % (d["app"], d["apps_js"], d["app_registry_json"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
