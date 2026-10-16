#!/usr/bin/env python3
"""Offline tests for the S10+ camera work (briq-08h, area 27).

Proven offline: enumeration-first sensor/node/firmware reporting driven by four
fixtures (nothing / nodes-but-unreadable / identity-without-firmware /
ready-untested), the honest verdict chain, the "never claim a frame" contract,
the bounded owner-only capture (refused without --yes and never sampled under a
faked root), the recording-privacy rules and the manual-proof fragment. A real
frame stays NEEDS_OWNER_TEST.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-camera-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "camera", "camera.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "15-camera.md")
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


def json_of(out):
    return json.loads([l for l in out.splitlines() if l.startswith("{")][0])


p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (none / unreadable / no-fw / ready) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
exp = pol["device"]["expected_sensors"]
check("policy inventories front and rear sensors separately",
      len(exp["rear"]) >= 3 and len(exp["front"]) >= 1
      and all(s["role"] and s["name"] for s in exp["rear"] + exp["front"]))
check("policy states expected_on_s10plus is shipped hardware, not an observation",
      "NOT an observation" in pol["device"]["comment_expected"])
check("policy never installs or depends on an Android camera HAL",
      any("camera" in x for x in pol["firmware_blobs"]["never_install"])
      and "No Android camera HAL" in pol["firmware_blobs"]["never_install_comment"])
check("policy requires the recording indicator and forbids stealth/bypass",
      pol["privacy"]["recording_indicator_required"] is True
      and pol["privacy"]["stealth_recording_allowed"] is False
      and pol["privacy"]["hidden_microphone_bypass_allowed"] is False)
check("background recording is user-controlled with a visible indicator + stop control",
      pol["privacy"]["background_recording"]["user_controlled_only"] is True
      and pol["privacy"]["background_recording"]["indicator_must_stay_visible"] is True
      and pol["privacy"]["background_recording"]["stop_control_always_available"] is True)
check("policy declares the five pipeline stages including capture",
      [s["id"] for s in pol["pipeline"]["stages"]]
      == ["dev_nodes", "sensor_names", "firmware", "media_graph", "capture"])
check("policy forbids automatic capture at boot",
      pol["diagnostics"]["auto_capture_on_boot"] is False
      and pol["diagnostics"]["require_explicit_yes_for_capture"] is True)

# --- verdict chain over the four fixtures ---------------------------------
d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "camera-absent"), "status", "--json"],
                {"NUXEL_DIAG_NO_SYSTEM": "1"}).stdout)
check("no nodes => NO_V4L2_DEVICE and frame_captured_verified is false",
      d["state"] == "NO_V4L2_DEVICE" and d["frame_captured_verified"] is False)
check("no nodes => first failing stage is the capture stage",
      d["first_failing_stage"] == "capture")

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "camera-partial"), "status", "--json"],
                {"NUXEL_DIAG_NO_SYSTEM": "1"}).stdout)
check("nodes without a readable sensor identity => PRESENT_UNREADABLE at sensor_names",
      d["state"] == "PRESENT_UNREADABLE" and d["first_failing_stage"] == "sensor_names")

p = run(["bash", TOOL, "--root", os.path.join(FIX, "camera-nofw"), "status", "--json"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
d = json_of(p.stdout)
check("identity without firmware => BLOCKED_FIRMWARE with the exact missing blobs",
      d["state"] == "BLOCKED_FIRMWARE" and d["first_failing_stage"] == "firmware"
      and len(d["firmware_missing"]) > 0 and d["firmware_found"] == [])
p = run(["bash", TOOL, "--root", os.path.join(FIX, "camera-nofw"), "fw"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`fw` states BLOCKED_FIRMWARE when no expected blob exists",
      "BLOCKED_FIRMWARE" in p.stdout, p.stdout)

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "camera-ready"), "status", "--json"],
                {"NUXEL_DIAG_NO_SYSTEM": "1"}).stdout)
check("ready device is READY_UNTESTED (never VERIFIED) with no frame claimed",
      d["state"] == "READY_UNTESTED" and d["frame_captured_verified"] is False)
check("enumeration reports each node once (dedupe)",
      d["video_nodes"] == ["/dev/video0"] and d["subdev_nodes"] == ["/dev/v4l-subdev0"])
check("a synthetic portal node is explicitly not hardware evidence",
      d["synthetic_chain_proof"]["synthetic_is_hardware_evidence"] is False)
check("owner-test fragment is pointed at from every status",
      d["owner_test"] == "docs/beta-finalization/manual-proof/15-camera.md")

# --- capture is an owner action, never automated, never under a faked root --
p = run(["bash", TOOL, "--root", os.path.join(FIX, "camera-ready"), "capture"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("capture without --yes refuses", p.returncode != 0 and "refused" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "camera-ready"), "capture", "--yes", "/tmp/nuxel-should-not-exist.jpg"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("capture under a faked root never samples a real device",
      p.returncode != 0 and "offline/faked root" in p.stdout, p.stdout)
check("capture under a faked root wrote no file", not os.path.exists("/tmp/nuxel-should-not-exist.jpg"))
p = run(["bash", TOOL, "--root", os.path.join(FIX, "camera-absent"), "capture", "--yes"])
check("capture on an absent device refuses and claims no frame",
      "NO_V4L2_DEVICE" in p.stdout and "no frame is claimed" in p.stdout, p.stdout)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "camera-ready"), "pipeline"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`pipeline` prints every stage and names the first failing one",
      all(s in p.stdout for s in ["dev_nodes", "sensor_names", "firmware", "media_graph", "capture"])
      and "first failing stage" in p.stdout)
check("`pipeline` marks capture as not attempted (owner action)", "not attempted here" in p.stdout)

# --- portal + gallery wiring (data-driven, verified against the tree) -------
p = run(["bash", TOOL, "portal"])
check("portal reports the real unit and backend paths from the policy",
      "shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service" in p.stdout
      and "nuxel_camera_portal.py" in p.stdout, p.stdout)
check("portal names the interface and its methods",
      "org.freedesktop.portal.Camera" in p.stdout and "RunCamera" in p.stdout, p.stdout)
check("portal verifies the capture app exists and its bridge verbs match the policy",
      "present" in p.stdout and "(match)" in p.stdout, p.stdout)
check("portal reports the synthetic backend without pretending it is hardware",
      "synthetic" in p.stdout and "NEVER evidence" in p.stdout, p.stdout)
check("portal names its own first failing stage and stays chain-only",
      "first failing :" in p.stdout and "PORTAL_READY_UNTESTED" in p.stdout
      and "chain evidence only" in p.stdout, p.stdout)
pol = json.load(open(POLICY))
check("policy carries a portal section with a synthetic contract",
      pol["pipeline"]["portal"]["synthetic_when_no_hardware"]["enabled"] is True
      and pol["pipeline"]["portal"]["first_failing_stage_order"][0] == "unit_installed")
check("policy pairs the capture app with a gallery app and one verb contract",
      pol["gallery"]["capture_app"]["path"] == "pwa/nuxel-apps/camera-gallery"
      and pol["gallery"]["bridge_verbs"] == pol["gallery"]["capture_app"]["declared_bridge_verbs"])
check("policy forbids swallowing capture autonomy",
      pol["gallery"]["capture_must_be_owner_initiated"] is True)
for rel in ("shell/nuxel-camera-portal/nuxel_camera_portal.py",
            "shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service",
            "pwa/nuxel-apps/camera-gallery/index.html",
            "pwa/nuxel-apps/camera-gallery/manifest.json"):
    check("portal/gallery artifact exists: %s" % rel, os.path.exists(os.path.join(ROOT, rel)), rel)
manifest = json.load(open(os.path.join(ROOT, "pwa/nuxel-apps/camera-gallery/manifest.json")))
check("the capture app declares the bridge verbs the policy promises",
      sorted(manifest["nuxel"]["bridge_verbs"]) == sorted(pol["gallery"]["bridge_verbs"]))
check("the capture app never silently claims hardware in its capability list",
      "camera:capture" in manifest["nuxel"]["capabilities"])

txt = open(TOOL).read()
check("tool has no flashing/partition/bootloader surface",
      all(t not in txt for t in ("/dev/block", "heimdall", "fastboot", "mmcblk")))
check("tool defaults to no frame claimed", '"frame_captured_verified":false' in txt.replace(" ", ""))

# --- manual-proof fragment --------------------------------------------------
dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment requires aiming the camera and viewing the still",
      "aim" in dtxt.lower() and "gallery" in dtxt.lower())
check("fragment marks the still NEEDS_OWNER_TEST and never claims an uncaptured frame",
      "NEEDS_OWNER_TEST" in dtxt and ("never" in dtxt.lower() and "without" in dtxt.lower()))
check("fragment documents BLOCKED_FIRMWARE and the recording-privacy rules",
      "BLOCKED_FIRMWARE" in dtxt and "stealth" in dtxt.lower())

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for config + diagnostic; NEEDS_OWNER_TEST for a real frame")
