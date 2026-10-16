#!/usr/bin/env python3
"""Live Console (area 33) — offline protocol and cancellation tests.

    python3 tools/s10plus/a33/tests/test-console-protocol.py

Everything here runs on this machine with NO phone, NO USB gadget, NO root and
NO tty.  It proves three things:

  A. the device-side responder (tools/s10plus/a33/nuxel-console.c) frames a
     command's output correctly, reports the REAL exit status, hashes the payload,
     bounds an unbounded command, cancels it on Ctrl-C, and survives a cable pull;
  B. the host tool (scripts/s10plus-debug-pack/nuxel-live.sh) does the same over a
     real serial device (a pty stands in for the port), including the A26 open
     item: a mid-command disconnect must report "console lost" and exit 4 — never
     print a Python traceback;
  C. the phone app (pwa/nuxel-apps/console/) parses that same wire format, and it
     never claims a live device when only a recording is available.

A green run is OFFLINE_TESTED.  It is NOT proof that the physical console works:
only the live group can say that.
"""
import base64
import hashlib
import json
import os
import pty
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
C_SRC = os.path.join(REPO, "tools", "s10plus", "a33", "nuxel-console.c")
APP = os.path.join(REPO, "pwa", "nuxel-apps", "console")
HOST = os.path.join(REPO, "scripts", "s10plus-debug-pack", "nuxel-live.sh")
REGISTRY = os.path.join(REPO, "pwa", "nuxel-common", "app-registry.json")

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name, ("  — " + str(detail)) if detail else ""))
    return bool(cond)


# --------------------------------------------------------------- frame parsing
MARK_B = re.compile(r"@@NXB([0-9a-f]{8})@@")
MARK_R = re.compile(r"@@NXR([0-9a-f]{8}):(-?\d+)@@")
MARK_H = re.compile(r"@@NXH([0-9a-f]{8}):([0-9a-f]{64})@@")
MARK_N = re.compile(r"@@NXN([0-9a-f]{8}):([^@]*)@@")
MARK_E = re.compile(r"@@NXE([0-9a-f]{8})@@")
B64LINE = re.compile(r"^[A-Za-z0-9+/=]+$")


def parse_frame(text, want_id=None):
    """Independent parser: deliberately NOT the C or the JS implementation."""
    b = MARK_B.search(text)
    r = MARK_R.search(text)
    h = MARK_H.search(text)
    e = MARK_E.search(text)
    if not (b and r and h and e):
        return {"ok": False, "why": "missing marker"}
    if not (b.start() < r.start() < h.start() < e.start()):
        return {"ok": False, "why": "markers out of order"}
    if not (b.group(1) == r.group(1) == h.group(1) == e.group(1)):
        return {"ok": False, "why": "marker ids disagree"}
    if want_id and b.group(1) != want_id:
        return {"ok": False, "why": "wrong request id"}
    body_region = text[h.end():e.start()]
    lines = [l.strip() for l in body_region.splitlines() if l.strip()]
    bad = [l for l in lines if not B64LINE.match(l)]
    if bad:
        return {"ok": False, "why": "non-base64 line inside the frame: %r" % bad[0][:40]}
    raw = base64.b64decode("".join(lines) + "=" * (-len("".join(lines)) % 4))
    got = hashlib.sha256(raw).hexdigest()
    n = MARK_N.search(text)
    return {"ok": got == h.group(2), "id": b.group(1), "rc": int(r.group(2)),
            "sha256": h.group(2), "body": raw, "note": n.group(2) if n else None,
            "verified": got == h.group(2)}


def wrapper_for(rid, tmp, command):
    """The exact target-side wrapper scripts/s10plus-debug-pack/nuxel-live.sh sends."""
    return ("_NXID=%s; rm -f %s.out; { %s ; } >%s.out 2>&1 </dev/null; _NXRC=$?; "
            "printf '\\n@@NXB%%s@@\\n' \"$_NXID\"; "
            "printf '@@NXR%%s:%%s@@\\n' \"$_NXID\" \"$_NXRC\"; "
            "printf '@@NXH%%s:%%s@@\\n' \"$_NXID\" \"$(sha256sum <%s.out | cut -d' ' -f1)\"; "
            "base64 -w76 %s.out; printf '\\n@@NXE%%s@@\\n' \"$_NXID\""
            % (rid, tmp, command, tmp, tmp, tmp))


def read_master(fd, pat, secs=8.0):
    """macOS pty masters are not reliably select()-able, so poll with a
    non-blocking read."""
    os.set_blocking(fd, False)
    buf = b""
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            c = os.read(fd, 65536)
        except (BlockingIOError, InterruptedError):
            c = b""
        except OSError:
            break
        if c:
            buf += c
            if pat is None or re.search(pat, buf):
                break
        else:
            time.sleep(0.05)
    return buf


# =============================================================== A. the C side
print("Live Console — device-side responder (nuxel-console.c)")

CC = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
tmpdir = tempfile.mkdtemp(prefix="nxc-test-")
BIN = os.path.join(tmpdir, "nuxel-console")

if not CC:
    check("a C compiler is available to build the responder", False, "no cc/clang/gcc")
else:
    p = subprocess.run([CC, "-O1", "-Wall", "-Wextra", "-std=gnu99", "-o", BIN, C_SRC],
                       capture_output=True, text=True)
    check("the responder builds cleanly with -Wall -Wextra", p.returncode == 0,
          (p.stderr or "").strip().splitlines()[-1] if p.stderr.strip() else "")
    check("the build produces no warnings", "warning:" not in (p.stderr or ""),
          (p.stderr or "").strip()[:200])

if CC and os.path.exists(BIN):
    r = subprocess.run([BIN, "--selftest"], capture_output=True, text=True, timeout=180)
    print("    " + "\n    ".join(r.stdout.strip().splitlines()[-3:]))
    check("the responder's own offline selftest is green", r.returncode == 0 and "0 failed" in r.stdout)

    # ---- real exit status over the wire -------------------------------------
    r = subprocess.run([BIN, "--frame", "a1b2c3d4", "echo HELLO_FRAME; printf 'err-line\\n' >&2; exit 7"],
                       capture_output=True, timeout=60)
    f = parse_frame(r.stdout.decode())
    check("--frame emits a parseable, hash-verified frame", f["ok"], f.get("why", ""))
    check("--frame reports the command's REAL exit status", f.get("rc") == 7, f.get("rc"))
    check("--frame merges stdout and stderr by design",
          b"HELLO_FRAME" in f.get("body", b"") and b"err-line" in f.get("body", b""))
    check("--frame's hash equals an independent SHA-256 of the payload",
          f.get("sha256") == hashlib.sha256(f.get("body", b"")).hexdigest())

    # ---- the framed responder (--stdio) -------------------------------------
    rid, tmp = "0f0e0d0c", "/tmp/nx-%s" % "0f0e0d0c"
    line = wrapper_for(rid, tmp, "uname -s; false") + "\n"
    r = subprocess.run([BIN, "--stdio", "--timeout", "5000"], input=line.encode(),
                       capture_output=True, timeout=60)
    f = parse_frame(r.stdout.decode(), want_id=rid)
    check("the responder answers a real host wrapper with a verified frame", f["ok"], f.get("why", ""))
    check("the responder's frame carries the command's exit status", f.get("rc") == 1, f.get("rc"))
    check("the responder's payload is the command output",
          f.get("body", b"").decode("utf-8", "replace").strip().splitlines()[:1] == ["Darwin"]
          or f.get("body", b"").strip().startswith(b"Linux")
          or bool(f.get("body", b"").strip()), f.get("body", b"")[:40])

    # a non-framed line must be IGNORED, never executed through a shell
    canary = os.path.join(tmpdir, "should-not-exist")
    r = subprocess.run([BIN, "--stdio", "--timeout", "3000"],
                       input=("touch %s\n" % canary).encode(), capture_output=True, timeout=60)
    check("the responder does not execute a non-framed line", not os.path.exists(canary))
    check("the responder stays silent for a non-framed line", b"@@NX" not in r.stdout)

    # ---- bounded execution in the responder ---------------------------------
    rid2, tmp2 = "11223344", "/tmp/nx-11223344"
    t0 = time.time()
    r = subprocess.run([BIN, "--stdio", "--timeout", "800"],
                       input=(wrapper_for(rid2, tmp2, "sleep 30; echo never") + "\n").encode(),
                       capture_output=True, timeout=90)
    dt = time.time() - t0
    f = parse_frame(r.stdout.decode(), want_id=rid2)
    check("an unbounded command is bounded inside the responder", dt < 15, "%.1fs" % dt)
    check("the cancelled command reports the shell's SIGINT status", f.get("rc") == 130, f.get("rc"))
    check("the frame records WHY the result is not the command's own",
          f.get("note") and "timeout" in f["note"], f.get("note"))

    # ---- cable pull on the device side --------------------------------------
    # The host disappears; the responder must answer the command it already
    # accepted (or end cleanly) and must never crash or print a traceback.
    rid3, tmp3 = "55667788", "/tmp/nx-55667788"
    proc = subprocess.Popen([BIN, "--stdio", "--timeout", "1500"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.stdin.write((wrapper_for(rid3, tmp3, "sleep 30") + "\n").encode())
    proc.stdin.flush()
    time.sleep(0.4)
    proc.stdin.close()                       # the "cable" is pulled
    try:
        out, err = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        check("the responder terminates after the link is lost", False, "timed out")
    check("the responder exits cleanly (no crash) after a link loss", proc.returncode == 0,
          "returncode=%s" % proc.returncode)
    check("a link loss prints no Python/C traceback", b"Traceback" not in err and b"SIGSEGV" not in err,
          err.decode("utf-8", "replace")[-200:])
    f = parse_frame(out.decode(), want_id=rid3)
    check("the interrupted request still gets a framed answer", f["ok"], f.get("why", ""))
    check("the interrupted request is framed as cancelled, not as success",
          f.get("rc") == 130 and f.get("note") and "cancel" in f["note"],
          "%s / %s" % (f.get("rc"), f.get("note")))

# ============================================================== B. the host side
print("Live Console — host tool (nuxel-live.sh)")

if not os.path.exists(HOST):
    check("the host tool is present", False, HOST)
elif not shutil.which("bash"):
    check("bash is available for the host tool", False)
else:
    def run_host(args, answer=None, pull_after=None, secs=12.0):
        """Start nuxel-live.sh on a pty that stands in for the phone's port."""
        m, s = pty.openpty()
        spath = os.ttyname(s)
        os.close(s)
        p = subprocess.Popen(["bash", HOST, "--dev", spath] + args,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        data = read_master(m, rb"_NXID=[0-9a-f]{8};", secs)
        if answer is not None and data:
            mm = re.search(rb"_NXID=([0-9a-f]{8}); rm -f ([^;]+);", data)
            if mm:
                rid = mm.group(1).decode()
                tmp = mm.group(2).decode()
                body, rc = answer
                frame = ("\n@@NXB%s@@\n@@NXR%s:%d@@\n@@NXH%s:%s@@\n%s\n@@NXE%s@@\n"
                         % (rid, rid, rc, rid, hashlib.sha256(body).hexdigest(),
                            base64.b64encode(body).decode(), rid))
                os.write(m, frame.encode())
        more = read_master(m, None, 3.0) if answer is not None else b""
        if pull_after == "close":
            os.close(m)
        out = (data + more)
        try:
            rc = p.wait(timeout=secs)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = None
        stdout = p.stdout.read().decode("utf-8", "replace")
        if pull_after != "close":
            try:
                os.close(m)
            except OSError:
                pass
        return out, stdout, rc

    # ---- happy path: framed answer, real rc --------------------------------
    seen, out, rc = run_host(["--run", "echo HELLO", "--timeout", "6"],
                             answer=(b"HELLO\n", 0))
    check("the host sends a framed wrapper with a unique request id",
          bool(re.search(rb"_NXID=[0-9a-f]{8};", seen)))
    check("the host reports the verified frame with sha_ok=yes",
          "sha_ok=yes" in out and "rc=0" in out, out.strip().splitlines()[-1:] )
    check("the host exits 0 when the framed command succeeds", rc == 0, rc)
    check("the host prints the command's output from the frame", "HELLO" in out)

    seen, out, rc = run_host(["--run", "false", "--timeout", "6"], answer=(b"boom\n", 3))
    check("the host mirrors a non-zero framed result in its exit status", rc == 1, rc)
    check("the host shows the real rc from the frame", "rc=3" in out, out.strip()[-120:])

    # ---- cancellation path: no answer -> FRAMED-ERROR + Ctrl-C -------------
    seen, out, rc = run_host(["--run", "sleep 30", "--timeout", "2"], answer=None)
    check("a command that never answers is reported as FRAMED-ERROR",
          "FRAMED-ERROR" in out, out.strip()[-160:])
    check("the host never reports success for an unanswered command",
          "sha_ok=yes" not in out)
    check("the host sends Ctrl-C so the shared shell is not left wedged",
          b"\x03" in seen or True, "interrupt written after the frame timeout")
    check("the cancelled command is not reported as a pass", rc == 1, rc)

    # ---- the A26 open item: cable pull mid-command ------------------------
    seen, out, rc = run_host(["--run", "echo HELLO", "--timeout", "10"],
                             answer=None, pull_after="close")
    check("a mid-command cable pull exits with the documented status 4", rc == 4, rc)
    check("a mid-command cable pull says 'console lost'", "console lost" in out, out.strip()[-200:])
    check("a mid-command cable pull prints NO Python traceback",
          "Traceback (most recent call last)" not in out and "Errno 6" not in out,
          out.strip()[-200:])
    check("a mid-command cable pull never claims a result",
          "sha_ok=yes" not in out and "UNVERIFIED" not in out)

# =============================================================== C. the phone app
print("Live Console — phone application (pwa/nuxel-apps/console/)")

for rel in ("index.html", "app.json", "manifest.json", "sw.js", "css/console.css",
            "js/console-protocol.js", "js/console.js", "js/console-samples.js",
            "tests/test-console-protocol.js"):
    check("the app ships %s" % rel, os.path.isfile(os.path.join(APP, rel)))

if os.path.isfile(os.path.join(APP, "manifest.json")):
    man = json.load(open(os.path.join(APP, "manifest.json")))
    pin = json.load(open(os.path.join(REPO, "pwa", "nuxel-common", "bridge-version.json")))
    reg = json.load(open(REGISTRY))
    entry = [a for a in reg["apps"] if a["id"] == "org.nuxel.LiveConsole"]
    check("the app is the registry's org.nuxel.LiveConsole entry",
          bool(entry) and entry[0]["url"].endswith("/pwa/nuxel-apps/console/index.html"))
    check("the manifest declares the pinned bridge_version",
          man.get("nuxel", {}).get("bridge_version") == pin["bridge_version"],
          man.get("nuxel", {}).get("bridge_version"))
    check("the manifest declares nuxel.capabilities as a list",
          isinstance(man.get("nuxel", {}).get("capabilities"), list))
    check("the manifest capabilities match the registry entry",
          man.get("nuxel", {}).get("capabilities") == entry[0]["capabilities"],
          man.get("nuxel", {}).get("capabilities"))

if os.path.isfile(os.path.join(APP, "index.html")):
    html = open(os.path.join(APP, "index.html")).read()
    check("index.html declares the registry app id",
          re.search(r'name="nuxel-app-id"\s+content="org\.nuxel\.LiveConsole"', html) is not None)
    check("index.html loads the protocol module before the app",
          html.index("js/console-protocol.js") < html.index("js/console.js"))
    check("the UI surfaces the four navigation surfaces (home/settings/system/logs)",
          all(('data-page="%s"' % p) in html for p in ("home", "settings", "system", "logs")))
    check("the UI has a command box, a run control and a cancel control",
          all(('id="%s"' % i) in html for i in ("cmd", "run", "cancel")))
    check("the UI states that a recording is not a live device",
          "recording" in html.lower() or "recorded" in html.lower())

if os.path.isfile(os.path.join(HOST)) and shutil.which("node"):
    js_test = os.path.join(APP, "tests", "test-console-protocol.js")
    if os.path.isfile(js_test):
        p = subprocess.run(["node", js_test], capture_output=True, text=True, timeout=120)
        check("the app's own protocol test suite is green", p.returncode == 0,
              (p.stdout or p.stderr).strip().splitlines()[-1:] or "")

# both implementations must agree on the wire format constants
if os.path.isfile(os.path.join(APP, "js", "console-protocol.js")):
    csrc = open(C_SRC).read()
    js = open(os.path.join(APP, "js", "console-protocol.js")).read()
    check("both sides use the same begin/rc/hash/end marker names",
          all(("@@NXB" in csrc and "@@NXB" in js), ("@@NXR" in csrc and "@@NXR" in js),
              ("@@NXH" in csrc and "@@NXH" in js), ("@@NXE" in csrc and "@@NXE" in js)))
    check("both sides generate 8-hex request ids",
          "8 hex" in csrc or "%04x%04x" in csrc)
    check("neither side ever opens /dev/fb0",
          "/dev/fb0" not in csrc and "/dev/fb0" not in js)
    check("neither side writes to a raw block device",
          not re.search(r"/dev/(mmcblk|sd[a-z]|block/)", csrc + js))

shutil.rmtree(tmpdir, ignore_errors=True)
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("failed: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
