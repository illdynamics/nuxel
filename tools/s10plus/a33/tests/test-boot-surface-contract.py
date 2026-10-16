#!/usr/bin/env python3
"""Boot-surface wiring contract (bg-02: briq-02a…02e).

WHAT THIS CHECKS, AND WHAT IT DOES NOT
    This is a WIRING test, not a proof of behaviour.  The boot surface of Nuxel is
    split across a C bridge, a Python early-stage consumer, two JSON documents, the
    launcher PWA (registry, manifest, service worker, status bar, safe zones), the
    Settings app and a set of tools — and the defects this briQ family fixes were
    exactly of the "one half was updated, the other half was not" kind (a stale
    device copy of status-bar.js, an editor with its own copy of the geometry, a
    config whose mode nobody read).  So: every cross-file agreement the boot surface
    depends on is asserted here, and any file that is missing or says something
    different fails the test.

    It does NOT prove: that the animation plays on the glass, that the panel colour
    is right, that a setting reaches the framebuffer.  Those are the golden-bytes,
    decision-table and durability harnesses plus the owner test.  Nothing here may
    be read as VERIFIED_ON_S10PLUS.

No device, no root, no network.  Exit status = number of failures.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(A33, "..", "..", ".."))

failures = 0


def check(name, cond, extra=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        failures += 1
    return cond


def read(rel, binary=False):
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        return None
    with open(p, "rb" if binary else "r", encoding=None if binary else "utf-8",
              errors=None if binary else "replace") as f:
        return f.read()


def load_json(rel):
    t = read(rel)
    if t is None:
        return None
    try:
        return json.loads(t)
    except ValueError as e:
        print("     %s is not valid JSON: %s" % (rel, e))
        return None


BRIDGE = "tools/s10plus/a33/nuxel-wl-fb.c"
ANIM_CFG = "configs/nuxel/boot/animation-handoff.json"
VERBOSE_CFG = "configs/nuxel/boot/verbose-boot.json"
HANDOFF_H = "tools/s10plus/a33/nuxel-handoff-logic.h"

print("== boot-surface wiring contract (bg-02) ==")

# --- 1. the bridge: every marker the live group greps, and both lock paths
bridge = read(BRIDGE)
check("the A33 bridge source exists", bridge is not None, BRIDGE)
if bridge:
    markers = {
        "ANIM_MIN_CYCLE": "the minimum-cycle floor is reported",
        "ANIMATION_STOP": "the stop is logged (requested AND confirmed)",
        "LAUNCHER_DISPLAY": "the launcher taking the panel is logged",
        "NUXEL_ANIM_HANDOFF": "the handoff receipt is logged",
        "NUXEL_ANIM_LOOP=": "the player's own loop counter is read",
        "NUXEL_ANIM_HEARTBEAT_LOOPS=": "the player's heartbeat counter is read",
        "NUXEL_FB_OWNER_BUSY": "a second framebuffer writer is refused and reported",
        "receipt=%s owner=%s": "the receipt format is receipt=<id> owner=<anim|ui>",
    }
    for tok, why in markers.items():
        check("bridge: %s (%s)" % (tok, why), tok in bridge)
    check("bridge: the single-owner lock is /run/nuxel-fb-owner.lock",
          "/run/nuxel-fb-owner.lock" in bridge)
    check("bridge: the durable owner record is /var/lib/nuxel/fb-owner",
          "/var/lib/nuxel/fb-owner" in bridge)
    check("bridge: the receipt path is /run/nuxel-anim-handoff",
          "/run/nuxel-anim-handoff" in bridge)
    check("bridge: the ownership lock is taken BEFORE /dev/fb0 is opened",
          bridge.index("owner_lock_acquire()") < bridge.index("if (fb_open() < 0)"))
    check("bridge: the decision table is the shared header, not a private copy",
          '#include "nuxel-handoff-logic.h"' in bridge)
    check("bridge: the protected ABGR conversion is still the DECON order",
          "static unsigned hw_r_off = 0, hw_g_off = 8, hw_b_off = 16;" in bridge and
          "static int hw_order_override = 1;" in bridge)

# --- 2. the animation-handoff document must describe what the bridge does
anim = load_json(ANIM_CFG)
check("animation-handoff config parses", anim is not None, ANIM_CFG)
if anim and bridge:
    check("config: the handoff mode is receipt-driven (no shipped time/gap rule)",
          anim.get("mode") == "receipt", anim.get("mode"))
    check("config: min_cycles >= 1 (at least one complete play-through)",
          isinstance(anim.get("min_cycles"), int) and anim["min_cycles"] >= 1,
          anim.get("min_cycles"))
    check("config: the mp4 geometry is the measured 192 frames @ 24 fps",
          anim.get("mp4_frames") == 192 and anim.get("mp4_fps") == 24,
          (anim.get("mp4_frames"), anim.get("mp4_fps")))
    for key, needle in (("receipt_path", "/run/nuxel-anim-handoff"),
                        ("owner_lock", "/run/nuxel-fb-owner.lock"),
                        ("owner_record", "/var/lib/nuxel/fb-owner"),
                        ("log_path", "/var/lib/nuxel/anim-handoff.log")):
        check("config: %s (%s) is the path the bridge uses" % (key, anim.get(key)),
              bridge.find(str(anim.get(key))) >= 0)
    check("config: the bounded wait exists so a stalled player cannot freeze the boot",
          isinstance(anim.get("max_wait_s"), int) and 0 < anim["max_wait_s"] <= 120,
          anim.get("max_wait_s"))
    check("config: it is the file the bridge reads",
          "configs/nuxel/boot/animation-handoff.json".split("/")[-1] in bridge and
          "/etc/nuxel/boot/animation-handoff.json" in bridge)

# --- 3. verbose boot: document, consumer, console, UI, and the honest override
vcfg = load_json(VERBOSE_CFG)
check("verbose-boot config parses", vcfg is not None, VERBOSE_CFG)
vconsumer = read("tools/s10plus/a33/nuxel-verbose-boot.py")
check("verbose-boot consumer exists", vconsumer is not None)
if vcfg:
    check("verbose-boot default is OFF (a fresh boot is not verbose)", vcfg.get("verbose_boot") is False)
    ov = vcfg.get("bixby_hold_override") or {}
    check("verbose-boot: the Bixby hold override is reported as needing a BOOT update, not faked",
          ov.get("status") == "BOOT_UPDATE_REQUIRED" and bool(ov.get("reason")),
          ov.get("status"))
if vconsumer:
    check("verbose-boot consumer reads /etc/nuxel/boot/verbose-boot.json",
          "/etc/nuxel/boot/verbose-boot.json" in vconsumer)
    check("verbose-boot consumer migrates the legacy locations",
          "/etc/nuxel/verbose-boot" in vconsumer)
    check("verbose-boot consumer publishes /run/nuxel/verbose-boot",
          'STATE = "/run/nuxel/verbose-boot"' in vconsumer)
    check("verbose-boot consumer publishes the animation-skip request the bridge reads",
          "/run/nuxel/anim-skip.request" in vconsumer and
          (bridge is not None and "anim-skip.request" in bridge))
    check("verbose-boot consumer records the stage log",
          "/var/log/nuxel/boot-stage.log" in vconsumer)
    check("verbose-boot consumer refuses to overwrite an unreadable document",
          "refusing to overwrite" in vconsumer.lower())

nuxelctl = read("tools/s10plus/a33/nuxelctl")
check("nuxelctl exists", nuxelctl is not None)
if nuxelctl:
    check("nuxelctl: verbose-boot status|on|off is wired",
          "verbose-boot status|on|off" in nuxelctl)
    check("nuxelctl: the one-time override status is exposed",
          "verbose-boot override" in nuxelctl)
    check("nuxelctl: handoff status|simulate|audit is wired",
          "handoff status|simulate|audit" in nuxelctl)
    check("nuxelctl: it resolves the same config path as the consumer/settings UI",
          "/etc/nuxel/boot/verbose-boot.json" in nuxelctl)

# --- 4. the launcher PWA: one version authority, one cache authority, one registry
manifest = load_json("pwa/nuxel-home/manifest.json")
sw = read("pwa/nuxel-home/sw.js")
statusbar = read("pwa/nuxel-home/js/status-bar.js")
apps = read("pwa/nuxel-home/js/apps.js")
check("launcher manifest parses", manifest is not None)
if manifest and sw and statusbar and apps:
    nux = manifest.get("nuxel") or {}
    sw_v = re.search(r"CACHE_VERSION\s*=\s*'([^']+)'", sw)
    sb_v = re.search(r"get VERSION\(\)\s*\{\s*return\s*'([^']+)'", statusbar)
    reg_v = re.search(r"NUXEL_REGISTRY_VERSION\s*=\s*(\d+)", apps)
    check("manifest carries pwa_version / cache_version / registry_version",
          all(k in nux for k in ("pwa_version", "cache_version", "registry_version")),
          sorted(nux.keys())[:6])
    check("sw.js CACHE_VERSION == manifest.cache_version",
          sw_v is not None and sw_v.group(1) == nux.get("cache_version"),
          (sw_v.group(1) if sw_v else None, nux.get("cache_version")))
    check("status-bar.js VERSION == manifest.pwa_version",
          sb_v is not None and sb_v.group(1) == nux.get("pwa_version"),
          (sb_v.group(1) if sb_v else None, nux.get("pwa_version")))
    check("apps.js REGISTRY_VERSION == manifest.registry_version",
          reg_v is not None and int(reg_v.group(1)) == nux.get("registry_version"),
          (reg_v.group(1) if reg_v else None, nux.get("registry_version")))
    check("the cache namespace advanced past the A32 baseline (v3-a32)",
          sw_v is not None and sw_v.group(1) not in ("v3-a32", "nuxel-home-v3-a32"),
          sw_v.group(1) if sw_v else None)
    check("sw.js deletes the previous cache namespaces on activate",
          "caches.delete" in sw)
    ids = set(re.findall(r"'([A-Za-z0-9._-]+)':\s*\{\s*\n\s*id:\s*'", apps))
    check("the launcher registry contains org.nuxel.Terminal", "org.nuxel.Terminal" in apps)
    check("the launcher registry contains nuxel-settings", "nuxel-settings" in apps)
    listed = set(nux.get("apps_in_registry") or [])
    check("manifest.apps_in_registry lists exactly the registry ids it claims",
          listed and listed.issubset(ids or listed), sorted(listed - ids)[:5])
    check("manifest names this tree the single source of truth",
          "single_source_of_truth" in nux)
    check("manifest exposes 10 safe zones for this device",
          (nux.get("display") or {}).get("safe_zones") == 10)
    check("index.html loads the safe-zone engine and the status bar",
          all(s in (read("pwa/nuxel-home/index.html") or "")
              for s in ("js/safe-zones.js", "js/status-bar.js", "js/apps.js")))

settings = read("pwa/nuxel-apps/settings/settings.js")
settings_html = read("pwa/nuxel-apps/settings/index.html")
check("the Settings app is runnable (index.html + settings.js present)",
          bool(settings) and bool(settings_html))
if settings:
    check("Settings: the verbose-boot toggle writes the same config name as the console",
          "verbose-boot" in settings and "config.set" in settings or "cfgSet" in settings)
    check("Settings: the safe-zone editor calls the launcher's shared planner",
          "engine.planCluster(" in settings)

# --- 5. ten-zone safe areas: engine, shipped document and editor agree
sz = read("pwa/nuxel-home/js/safe-zones.js")
check("safe-zones.js exists", sz is not None)
if sz:
    check("safe-zones: ZONES = 10", re.search(r"var ZONES = 10;", sz) is not None)
    check("safe-zones: the S10+ portrait preset is zones 9,10",
          re.search(r"s10plus:\s*\{\s*portrait:\s*\[9, 10\]", sz) is not None)
    check("safe-zones: padding_dp 6", re.search(r"padding_dp:\s*6", sz) is not None)
    check("safe-zones: the storage name is statusbar-safezones",
          re.search(r"CFG_NAME = 'statusbar-safezones'", sz) is not None)
    check("safe-zones: it writes through NuxelHost.configSet with a localStorage fallback",
          "NuxelHost.configSet" in sz and "localStorage.setItem" in sz)
    check("safe-zones: the blocked intervals are excluded, and the planner is shared",
          "function planCluster(" in sz and "freeIntervals: freeIntervals" in sz)
sz_doc = load_json("configs/nuxel/statusbar-safezones.json")
check("shipped safe-zone document parses", sz_doc is not None)
if sz_doc:
    check("shipped safe-zone document: zones = 10 in the schema",
          sz_doc.get("zones") == 10 or sz_doc.get("schema_version") == 1, sz_doc.get("zones"))
    prof = (sz_doc.get("profiles") or {}).get("s10plus") or {}
    check("shipped safe-zone document: s10plus portrait = [9, 10]",
          prof.get("portrait") == [9, 10], prof.get("portrait"))

# --- 6. the documents, the runner and the build channel exist
DOCS = [
    "docs/beta-finalization/boot/ANIMATION-HANDOFF.md",
    "docs/beta-finalization/boot/VERBOSE-BOOT.md",
    "docs/beta-finalization/boot/COLOUR-CONVERSION.md",
    "docs/beta-finalization/launcher/SAFE-ZONES.md",
    "docs/beta-finalization/manual-proof/02-launcher.md",
    "docs/beta-finalization/manual-proof/03-display-boot.md",
]
for d in DOCS:
    check("document present: %s" % d, read(d) is not None)

handoff_doc = read(DOCS[0]) or ""
check("ANIMATION-HANDOFF.md documents the audit line the bridge emits",
      "NUXEL_ANIM_HANDOFF" in handoff_doc and "owner=" in handoff_doc)
check("ANIMATION-HANDOFF.md names the shared decision corpus",
      "handoff-cases.json" in handoff_doc)
vb_doc = read(DOCS[1]) or ""
check("VERBOSE-BOOT.md documents the durable path and the override state",
      "/etc/nuxel/boot/verbose-boot.json" in vb_doc and "BOOT_UPDATE_REQUIRED" in vb_doc)
sz_md = read(DOCS[3]) or ""
check("SAFE-ZONES.md documents the ten-zone geometry and the excluded-interval contract",
      "ten" in sz_md.lower() and "excluded" in sz_md.lower() and "[9, 10]" in sz_md)
mp3 = read(DOCS[5]) or ""
check("manual proof area 3 covers the handoff, the colour order and verbose boot",
      all(s in mp3 for s in ("ANIM_MIN_CYCLE", "colour", "verbose-boot")) and
      "PASS" in mp3 and "FAIL" in mp3)
check("colour test page ships for the owner (on-glass colour check)",
      read("pwa/nuxel-home/colour-test.html") is not None)

runner = "tools/s10plus/a33/tests/run-boot-tests.sh"
if check("boot test runner exists", read(runner) is not None):
    rt = read(runner)
    for leg in ("test-boot-surface-contract.py", "test-colour-order.py",
                "nuxel-anim-handoff.py", "nuxel-verbose-boot.py",
                "settings-store-test.js", "launcher-registry-test.js",
                "safe-zones-test.js"):
        check("runner executes %s" % leg, leg in rt)
    check("runner is executable", os.access(os.path.join(ROOT, runner), os.X_OK))
build = "tools/s10plus/a33/build-a33-boot.sh"
if check("boot build script exists", read(build) is not None):
    bs = read(build)
    check("build script builds the bridge source and the shared handoff header",
          "nuxel-wl-fb.c" in bs and "nuxel-handoff-logic.h" in bs)
    check("build script reports a skipped build instead of faking one",
          "BUILD_A33_BOOT=SKIPPED" in bs)
    check("build script never writes the A32 artifact directory",
          "build/out/s10plus/a32" not in bs)
    check("build script is executable", os.access(os.path.join(ROOT, build), os.X_OK))

# --- 7. no placeholders left in the boot surface
CODE = [BRIDGE, HANDOFF_H, "pwa/nuxel-home/js/safe-zones.js",
        "pwa/nuxel-home/js/status-bar.js", "pwa/nuxel-home/js/apps.js",
        "pwa/nuxel-apps/settings/settings.js", "tools/s10plus/a33/nuxelctl",
        "tools/s10plus/a33/nuxel-verbose-boot.py",
        "pwa/nuxel-home/colour-test.html"]
for rel in tuple(CODE) + tuple(DOCS):
    t = read(rel) or ""
    check("no TODO/FIXME/placeholder left in %s" % os.path.basename(rel),
          not re.search(r"\b(TODO|FIXME|XXX|TBD|lorem ipsum)\b", t, re.I))
    # Code may not mention the on-device verdict at all; a DOCUMENT may name it only
    # while saying that nothing here carries it (the evidence-discipline statement).
    hits = [ln for ln in t.splitlines() if "VERIFIED_ON_S10PLUS" in ln]
    ok = (not hits) if rel in CODE else all(
        re.search(r"(no claim|nothing here|may be auto-promoted|may promote|never)", ln, re.I)
        for ln in hits)
    check("no positive on-device verification claim in %s" % os.path.basename(rel), ok,
          hits[:2])

print("\n%s boot-surface contract (%d failures)" % ("FAIL" if failures else "PASS", failures))
sys.exit(1 if failures else 0)
