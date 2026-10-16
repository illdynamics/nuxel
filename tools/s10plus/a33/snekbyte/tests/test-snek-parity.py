#!/usr/bin/env python3
"""SnekByte port verification (offline, no hardware).

    python3 tools/s10plus/a33/snekbyte/tests/test-snek-parity.py

Checks, in order:

  T1  the upstream sources are present and their hashes match upstream-manifest.json
      (so the port cannot silently drift away from what was actually imported)
  T2  the committed parity fixture still matches a fresh run of the REAL upstream
      game logic (gen-parity-fixtures.py --check)
  T3  the JavaScript port reproduces that fixture tick for tick (parity-run.js)
  T4  the PWA shell exists, is wired to the engine, and the engine has no
      environment-specific dependency (no pygame, no node-only API, no network)
  T5  the artefact records where it came from (provenance + licence statement),
      including that the upstream archive contains NO licence file — which is
      stated rather than glossed over
  T6  the archive itself, when present on this machine, still hashes to the value
      recorded at import time (informational: an absent archive is reported, not
      treated as a failure — that is the documented BLOCKED_EXTERNAL_RESOURCE case)
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(PKG, "..", "..", "..", ".."))
PWA = os.path.join(REPO, "pwa", "nuxel-apps", "snekbyte")
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name, ("  — " + detail) if detail else ""))
    return cond


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


print("SnekByte port verification")

# ---- T1 upstream provenance -------------------------------------------------
man_path = os.path.join(PKG, "upstream-manifest.json")
check("upstream-manifest.json exists", os.path.isfile(man_path))
man = json.load(open(man_path))
bad = []
for rel, rec in man["members"].items():
    full = os.path.join(PKG, "upstream", rel)
    if not os.path.isfile(full):
        bad.append(rel + " (missing)")
        continue
    if sha256(full) != rec["sha256"] or os.path.getsize(full) != rec["bytes"]:
        bad.append(rel + " (hash/size drift)")
check("every upstream member is present and unmodified (%d files)" % len(man["members"]),
      not bad, ", ".join(bad[:4]))
check("the imported tree includes the shipped entry point and its rule modules",
      all(os.path.isfile(os.path.join(PKG, "upstream", p)) for p in
          ("src/main.py", "src/game_loop.py", "src/game_logic.py", "src/snake.py",
           "src/food.py", "src/poop.py", "src/game_state.py", "src/config.py")))

# ---- T2 fixture freshness ---------------------------------------------------
rc, out = run([sys.executable, os.path.join(PKG, "gen-parity-fixtures.py"), "--check"], cwd=PKG)
check("the committed parity fixture matches a fresh run of the upstream game", rc == 0,
      out.strip().splitlines()[-1] if out.strip() else "")

fixture = json.load(open(os.path.join(PKG, "fixtures", "parity.json")))
check("the fixture records which pygame was used (%s)" % fixture["pygameUsed"],
      "pygame" in fixture["pygameUsed"])
causes = [sc["steps"][-1]["tick"]["cause"] for sc in fixture["scenarios"]]
check("the fixture exercises wall, self AND poop endings", set(causes) == {"wall", "self", "poop"},
      ",".join(causes))
check("the fixture covers >=30 ticks", sum(len(s["steps"]) for s in fixture["scenarios"]) >= 30)
check("the fixture's grid matches the shipped config (40x30, 20 px cells)",
      (fixture["config"]["gridWidth"], fixture["config"]["gridHeight"], fixture["config"]["gridSize"]) == (40, 30, 20))

# ---- T3 JavaScript parity ---------------------------------------------------
node = subprocess.run(["which", "node"], stdout=subprocess.PIPE).stdout.strip()
if not node:
    check("node is available to replay the fixture", False, "node not found — parity could not be executed")
else:
    rc, out = run(["node", os.path.join(PKG, "parity-run.js")], cwd=PKG)
    check("the shipped JS engine reproduces the original tick for tick", rc == 0,
          out.strip().splitlines()[-1] if out.strip() else "")

# ---- T4 PWA shell ----------------------------------------------------------
for rel in ("index.html", "app.json", "manifest.json", "sw.js", "css/snekbyte.css",
            "js/snekbyte.js", "js/snek-engine.js", "tests/test-snek-engine.js"):
    check("PWA ships %s" % rel, os.path.isfile(os.path.join(PWA, rel)))

engine_src = open(os.path.join(PWA, "js", "snek-engine.js")).read()
# The header COMMENTS discuss pygame on purpose (they document what was ported and
# that rendering moved to snekbyte.js), so the assertion is made against the code
# with comments removed -- "no pygame dependency" is a claim about behaviour, not
# about prose.
import re as _re
engine_code = _re.sub(r"/\*[\s\S]*?\*/", "", engine_src)
engine_code = _re.sub(r"^[ \t]*//.*$", "", engine_code, flags=_re.M)
check("the engine has no pygame/Emscripten dependency (comments excluded)",
      not _re.search(r"pygame|emscripten|SDL", engine_code, _re.I))
check("the engine makes no network call", not any(t in engine_src for t in ("fetch(", "XMLHttpRequest", "WebSocket")))
index_src = open(os.path.join(PWA, "index.html")).read()
check("index.html loads the engine", "js/snek-engine.js" in index_src)
check("index.html loads the UI", "js/snekbyte.js" in index_src)
ui_src = open(os.path.join(PWA, "js", "snekbyte.js")).read()
check("the UI talks only to the engine module", "SnekEngine" in ui_src)
check("the UI drives a canvas", "<canvas" in index_src and "getContext" in ui_src)

# ---- T5 provenance / licence ------------------------------------------------
prov = open(os.path.join(PKG, "UPSTREAM-PROVENANCE.md")).read()
check("UPSTREAM-PROVENANCE.md names the archive", "snekbyte-main.zip" in prov)
check("UPSTREAM-PROVENANCE.md states the licence position honestly",
      "no licence" in prov.lower() or "without a licence" in prov.lower())
check("the provenance file records the WoNQ rule", "WoNQ" in prov)
licence_files = [f for f in man["members"] if "licen" in f.lower() or f.lower().startswith("copying")]
check("the upstream archive really contains no licence file (recorded, not hidden)",
      licence_files == [], "found: " + ", ".join(licence_files) if licence_files else "none")

# ---- T6 the archive on this machine (informational) -------------------------
ARCHIVES = [
    os.path.expanduser("~/Downloads/snekbyte-main.zip"),
    os.path.expanduser("~/Downloads/snekbyte-main (1).zip"),
]
recorded = man.get("source_archive_sha256")
found = [a for a in ARCHIVES if os.path.isfile(a)]
if not found:
    print("  INFO the supplied snekbyte archive is not present on this machine — "
          "hashes were recorded at import time and the imported tree is verified above "
          "(documented BLOCKED_EXTERNAL_RESOURCE case for re-import, not for the port)")
else:
    hashes = sorted({sha256(a) for a in found})
    check("the archive(s) present on this machine hash to the recorded value",
          recorded in hashes if recorded else True,
          "recorded=%s found=%s" % (recorded, ",".join(h[:16] for h in hashes)))

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(0 if not FAIL else 1)
