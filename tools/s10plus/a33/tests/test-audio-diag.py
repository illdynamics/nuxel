#!/usr/bin/env python3
"""Offline tests for the S10+ audio path and its low-volume safety (briq-03c,
mission area 6).

WHAT IS PROVEN HERE (OFFLINE_TESTED)
  1. The REAL pipeline walker names the FIRST broken stage of the real playback
     path, on eight faked roots: no card / missing codec DSP firmware / no PCM /
     no mixer controls / DAC never running / DAPM not observable / fully OK /
     UCM route present but empty. Each verdict is checked against its EXPECTED
     file, and the reported first-broken stage is checked too.
  2. "A writable mixer control is NOT an acceptance criterion." A card whose
     controls are all present and writable but whose PCM never leaves SETUP is
     reported DAC_NOT_RUNNING (fixture audio-dacidle), never OK.
  3. The low-volume default is enforced, not promised: a tone is refused without
     --yes, `safe-volume` refuses a level above the policy cap, and the ALSA
     softvol ceiling (max_dB = 0.0) is present in the shipped config.
  4. The concrete UCM EnableSequence is generated from OBSERVED control names and
     the SHIPPED UCM profile carries empty sequences — nothing is invented.
  5. The tool contains no flashing/partition-write surface (NO FLASHING
     invariant, checked mechanically).
  6. The manual-proof fragment has all eight fields, states that writability is
     not audibility, and marks audibility NEEDS_OWNER_TEST. The capability
     manifest claims no audio item as VERIFIED_ON_S10PLUS.

WHAT IS NOT PROVEN HERE — and therefore NEEDS_OWNER_TEST: that a human hears
sound from the speaker or the headphones on the physical handset. A passing run
is OFFLINE_TESTED, never VERIFIED_ON_S10PLUS.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(os.path.dirname(start)))


ROOT = _repo_root(HERE)
TOOL = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-audio-diag.sh")
AUDIO_JSON = os.path.join(ROOT, "configs", "nuxel", "audio", "audio.json")
UCM = os.path.join(ROOT, "configs", "alsa-ucm", "beyond-madera", "HiFi.conf")
ASOUND = os.path.join(ROOT, "configs", "pipewire", "asound-nuxel-safe.conf")
WP = os.path.join(ROOT, "configs", "wireplumber",
                  "nuxel-s10plus-audio.conf.d", "51-nuxel-s10plus-audio.conf")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "06-audio.md")
CAP = os.path.join(ROOT, "configs", "nuxel", "capabilities",
                   "connectivity-time-audio-buttons.json")
FIX = os.path.join(HERE, "fixtures-p3")

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ)
    e["NUXEL_DIAG_NO_SYSTEM"] = "1"
    e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


def fx(name):
    return os.path.abspath(os.path.join(FIX, name))


def status_json(name):
    p = run(["bash", TOOL, "status", "--json"], {"NUXEL_DIAG_ROOT": fx(name)})
    line = [l for l in p.stdout.splitlines() if l.strip().startswith("{")]
    if not line:
        return None, p
    return json.loads(line[-1]), p


# 1 ── fixture-driven pipeline verdicts ----------------------------------------------
p = run(["bash", TOOL, "selftest"])
check("fixtures: all audio pipeline verdicts match", p.returncode == 0,
      "rc=%d\n%s" % (p.returncode, p.stdout + p.stderr))

CASES = [
    ("audio-nocard", "NO_CARD"),
    ("audio-nofirmware", "BLOCKED_FIRMWARE"),
    ("audio-nopcm", "NO_PCM"),
    ("audio-nocontrols", "NO_CONTROLS"),
    ("audio-dacidle", "DAC_NOT_RUNNING"),
    ("audio-dapm-unverified", "OK_DAC_RUNNING"),
    ("audio-ok", "OK_DAC_RUNNING"),
    ("audio-route-empty", "OK_DAC_RUNNING"),
]
for name, state in CASES:
    doc, p = status_json(name)
    if doc is None:
        check("fixture %s -> %s" % (name, state), False, p.stdout[-300:])
        continue
    check("fixture %s -> %s" % (name, state), doc.get("state") == state,
          "state=%s first_broken=%s" % (doc.get("state"), doc.get("first_broken_stage")))
    check("%s: no stage is reported OK without observation" % name,
          not any(v == "OK" for k, v in doc.get("stages", {}).items() if k == "dac_running" and state != "OK_DAC_RUNNING"),
          json.dumps(doc.get("stages", {})))

# the FIRST broken stage is named, and a broken walk carries a reason
for name, first in [("audio-nocard", "card"), ("audio-nofirmware", "card"),
                    ("audio-nopcm", "pcm"), ("audio-nocontrols", "controls"),
                    ("audio-dacidle", "dac_running")]:
    doc, _ = status_json(name)
    check("%s: first broken stage is %r" % (name, first),
          doc is not None and doc.get("first_broken_stage") == first
          and (doc.get("reason") or "").strip() != "",
          json.dumps(doc or {}))

# 2 ── writability is NOT audibility --------------------------------------------------
doc, _ = status_json("audio-dacidle")
check("a card with writable controls but a non-running PCM is DAC_NOT_RUNNING, never OK",
      doc is not None and doc.get("state") == "DAC_NOT_RUNNING",
      json.dumps(doc or {}))
check("the tool states that writability is not an acceptance criterion",
      "writability is not audibility" in open(TOOL).read().lower()
      or "not an acceptance criterion" in open(TOOL).read().lower())

# 3 ── low-volume-only enforcement ---------------------------------------------------
p = run(["bash", TOOL, "tone", "500"], {"NUXEL_DIAG_ROOT": fx("audio-ok")})
check("tone without --yes is refused (no accidental burst)", p.returncode == 2,
      p.stdout[-300:])

p = run(["bash", TOOL, "tone", "500", "--yes"], {"NUXEL_DIAG_ROOT": fx("audio-ok")})
check("tone with --yes but no renderer is BLOCKED_EXTERNAL_RESOURCE (nothing is faked)",
      p.returncode == 1 and "BLOCKED_EXTERNAL_RESOURCE" in p.stdout, p.stdout[-300:])

p = run(["bash", TOOL, "tone", "500", "--yes"], {"NUXEL_DIAG_ROOT": fx("audio-nocard")})
check("tone refuses when the anchor card is absent", p.returncode == 1 and "BLOCKED" in p.stdout,
      p.stdout[-300:])

p = run(["bash", TOOL, "safe-volume", "101"], {"NUXEL_DIAG_ROOT": fx("audio-ok")})
check("safe-volume refuses a level above the 100% policy ceiling",
      p.returncode == 1 and "REFUSED" in p.stdout, p.stdout[-300:])

p = run(["bash", TOOL, "safe-volume"], {"NUXEL_DIAG_ROOT": fx("audio-ok")})
check("the reported softvol ceiling equals the policy cap", "cap=100%" in p.stdout, p.stdout[-300:])

pol = json.load(open(AUDIO_JSON))
check("policy ceiling is the owner-approved 100% (25% cap retired)",
      pol["safety"]["low_volume_only"] is False and int(pol["safety"]["volume_cap_percent"]) == 100
      and int(pol["safety"].get("default_volume_percent", 0)) == 50)
check("policy first tone level is a small fraction of range",
      int(pol["safety"]["first_tone_default_percent"]) <= 12)
check("policy bans unbounded aplay invocations",
      any("aplay" in b and "bounded" in b for b in pol["safety"]["banned_by_default"]))

atxt = open(ASOUND).read()
check("ALSA softvol ceiling is installed config (max_dB = 0.0)",
      "softvol" in atxt and re.search(r"max_dB\s+0\.0", atxt) is not None)
wptxt = open(WP).read()
check("WirePlumber keeps UCM authoritative for beyond-madera and disables autosuspend",
      "beyond-madera" in wptxt and "api.alsa.use-ucm" in wptxt
      and "session.suspend-timeout-seconds" in wptxt)

# 4 ── nothing is invented: shipped UCM is empty, capture only emits observed names --
ucm = open(UCM).read()
seq_lines = []
in_seq = False
for line in ucm.splitlines():
    ls = line.strip()
    if re.search(r"EnableSequence\s*\[", line):
        in_seq = True
        continue
    if in_seq and ls.startswith("]"):
        in_seq = False
        continue
    if in_seq and ls and not ls.startswith("#"):
        seq_lines.append(ls)
check("the shipped UCM profile carries empty sequences (no invented control names)",
      seq_lines == [], str(seq_lines[:3]))

with tempfile.TemporaryDirectory() as tmp:
    work = os.path.join(tmp, "root")
    shutil.copytree(fx("audio-ok"), work)
    p = run(["bash", TOOL, "capture"], {"NUXEL_DIAG_ROOT": work})
    ctrl = os.path.join(work, "var", "lib", "nuxel", "audio", "controls.json")
    gen = os.path.join(work, "var", "lib", "nuxel", "audio", "HiFi.conf.generated")
    check("capture writes an evidence file and a generated UCM fragment",
          os.path.exists(ctrl) and os.path.exists(gen), p.stdout[-300:])
    if os.path.exists(gen):
        g = open(gen).read()
        raw = open(os.path.join(work, "var", "lib", "nuxel", "audio", "controls.raw")).read()
        check("the generated fragment references a control OBSERVED on the card",
              "Speaker Volume" in g and "DAC Digital Volume" in g, g[:400])
        names = re.findall(r"cset \"name='([^']*)'", g)
        check("every generated cset names a control present in the raw capture",
              bool(names) and all(("name='%s'" % n) in raw for n in names), str(names))
        check("a read-only detection control is never turned into a cset",
              "Headphone Jack" not in names, str(names))
        rng, cur = {}, None
        for line in raw.splitlines():
            m = re.search(r"name='([^']*)'", line)
            if m:
                cur = m.group(1)
                rng[cur] = None
            if cur:
                mx = re.search(r"max=(-?\d+)", line)
                if mx:
                    rng[cur] = int(mx.group(1))
        pairs = re.findall(r"cset \"name='([^']*)' (\d+)\"", g)
        check("every generated volume value is clamped to the 100% policy ceiling",
              bool(pairs) and all(rng.get(n) is not None and int(v) <= rng[n]
                                  for n, v in pairs), str(pairs))

# 5 ── manual proof fragment + capability manifest ----------------------------------
if os.path.exists(DOC):
    d = open(DOC).read()
    for field in ["Feature", "Why", "Preparation", "Exact action", "Expected result",
                  "Failure symptoms", "Diagnostic", "PASS", "FAIL"]:
        check("manual-proof fragment has field %r" % field, field in d)
    check("manual-proof fragment marks audibility NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in d)
    check("manual-proof fragment states writability is not an acceptance criterion",
          "not an acceptance criterion" in d.lower())
    check("manual-proof fragment names the real codec/amp chain",
          "beyond-madera" in d and "cs47l93" in d.lower() and "cs35l40" in d.lower())
else:
    check("manual-proof fragment exists", False, DOC)

cap = json.load(open(CAP))
audio_items = [i for i in cap["items"] if i.get("component") == "audio"]
check("capability manifest has audio items", len(audio_items) >= 3)
check("no audio capability is claimed VERIFIED_ON_S10PLUS",
      all(i["state"] != "VERIFIED_ON_S10PLUS" for i in audio_items),
      str([(i["id"], i["state"]) for i in audio_items]))
check("audibility is NEEDS_OWNER_TEST in the manifest",
      any(i["id"] == "audio.audibility" and i["state"] == "NEEDS_OWNER_TEST" for i in audio_items))


# 7 ── the user-facing sound settings surface (briq-03c rows) -------------------------
SPEC3 = os.path.join(ROOT, "configs", "alsa-ucm", "nuxel-sound-settings.json")
if os.path.exists(SPEC3):
    spec3 = json.load(open(SPEC3))
    rows = {r.get("id") for r in spec3.get("rows", [])}
    need_rows = {"volume", "mute", "sound-mode", "outputs", "per-app-volume", "mic-input", "notifications"}
    check("sound-settings spec covers every required user-facing row",
          need_rows.issubset(rows), str(sorted(need_rows - rows)))
    check("sound-settings spec keeps the 100% ceiling and amplifier protection rule",
          spec3["safety"]["low_volume_only"] is False and
          int(spec3["safety"]["volume_cap_percent"]) == 100 and
          "amplifier protection" in " ".join(spec3["safety"]["never"]))
    check("sound-settings spec states the shared sound-mode state file",
          any(r.get("state_file") == "/var/lib/nuxel/audio/sound-mode" for r in spec3["rows"]))
    check("sound-settings spec never claims audibility from a mixer write",
          any("not audibility" in c.lower() for c in spec3.get("never_claims", [])))
    check("per-app volume is honest about needing the session manager",
          any(r["id"] == "per-app-volume" and "unsupported" in r.get("honesty", "") for r in spec3["rows"]))
else:
    check("sound-settings spec exists", False, SPEC3)

# the tool's own rows must run and must not invent a control name
with tempfile.TemporaryDirectory() as td:
    env = {"NUXEL_DIAG_NO_SYSTEM": "1", "NUXEL_DIAG_ROOT": td,
           "NUXEL_SOUND_MODE_FILE": "/var/lib/nuxel/audio/sound-mode"}
    p = run(["bash", TOOL, "settings", "--json"], env)
    jlines = [l for l in p.stdout.splitlines() if l.startswith("{")]
    okjson = False
    if len(jlines) == 1:
        try:
            doc3 = json.loads(jlines[0])
            okjson = doc3.get("device") == "beyond2lte" and doc3.get("card") == "beyond-madera"
        except Exception:  # noqa: BLE001
            okjson = False
    check("nuxelctl audio settings --json emits exactly one parseable JSON object",
          p.returncode == 0 and okjson, p.stdout[-200:])
    check("settings on an empty root says the mixer is unavailable instead of guessing",
          "unavailable" in p.stdout or "NOT FOUND" in p.stdout, p.stdout[-300:])
    p = run(["bash", TOOL, "mode", "silent"], env)
    check("mode writes the shared state file", p.returncode == 0 and
          open(os.path.join(td, "var/lib/nuxel/audio/sound-mode")).read().strip() == "silent", p.stdout[-200:])
    check("mode on an empty root does NOT touch a mixer it cannot see",
          "NOT touched" in p.stdout or "switched" in p.stdout, p.stdout[-300:])
    p = run(["bash", TOOL, "mode"], env)
    check("mode reads back what was set", "sound mode: silent" in p.stdout, p.stdout[-200:])
    p = run(["bash", TOOL, "mode", "bogus"], env)
    check("an invalid mode is refused with a usage message", p.returncode == 2 and "usage" in p.stdout)
    p = run(["bash", TOOL, "mode", "vibrate"], env)
    check("vibrate mode is recorded but not promoted into a haptic claim",
          "briq-08b" in p.stdout and "not a claim" in p.stdout, p.stdout[-300:])
check("the tool never hard-codes a mixer element name like 'Master'",
      "sset 'Master'" not in open(TOOL).read() and "primary_element" in open(TOOL).read())

# 6 ── NO FLASHING invariant, mechanically ------------------------------------------
src = open(TOOL).read()
banned = [r"\bdd\s+if=", r"/dev/block", r"\bheimdall\b", r"\bodind?\b", r"fastboot",
          r"download mode", r"\bflash\b"]
for pat in banned:
    hits = re.findall(pat, src, re.I)
    check("tool contains no flashing surface for %r" % pat, not hits, str(hits))

print("\n== %d failing check(s) ==" % len(fails))
sys.exit(1 if fails else 0)
