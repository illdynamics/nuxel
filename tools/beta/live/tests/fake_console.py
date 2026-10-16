#!/usr/bin/env python3
"""fake_console — a faithful, offline stand-in for the Nuxel S10+ live console.

WHY
===
The live group's tooling (baseline capture, staged deploy, reboot+verify) can
only ever be *trusted* if its shell framing is exercised against a far end that
speaks the exact same protocol.  The real phone console is byte-silent for most
of this mission (see docs/beta-finalization/live/BASELINE-CAPTURE.md), so this
harness supplies an OFFLINE_TESTED substitute: a PTY whose far end

  * echoes a CR the way the device's shell + kmsg mirror does,
  * evaluates the *exact* `_N=<rid>;...{ <cmd> ;} ><tmp> ...@@B/@@R/@@S/@@E`
    wrapper that tools/beta/live/nuxel_live.py transmits, using a real POSIX
    shell over a **fake root tree**,
  * maps the device's absolute paths (/proc, /var/lib/nuxel, /etc/nuxel,
    /usr/local, /home/nuxel/nuxel, /dev, /run) onto that tree so a deploy really
    stages, verifies, atomically installs and rolls back files,
  * shims the target-only tools the scripts call (sha256sum, systemctl, uname,
    hostname, id, curl) with stateful fakes,
  * can be run in `silent` mode, which reproduces the measured failure so the
    reachability escalation path is proven against a real silent port too,
  * models a power cycle: `systemctl reboot` (and plain `reboot`) set a flag that
    ends the session, and `post-reboot` mode boots a tree with a *different*
    kernel boot_id, a reset uptime and an incremented boot counter — so the host
    tool's reconnect watch, its real-reboot proof and its reboot policy are all
    exercised without touching the phone.

It is a TEST DOUBLE.  Nothing it does is evidence about the physical phone; it
only proves the host tooling behaves correctly.  Stdlib only; never touches
.qq/RUN_ROOT, never writes outside --root, never invokes flash tooling.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import time

WRAPPER_RE = re.compile(
    r"_N=(?P<rid>[0-9a-f]+);rm -f (?P<tmp>\S+);\{ (?P<cmd>.*) ;\} >(?P<out>\S+) "
    r"2>&1 </dev/null", re.S)

#: Longest prefixes first so /etc/nuxel/ never lands on /etc/.
PATH_MAP = (
    "/home/nuxel/nuxel/", "/etc/nuxel/", "/etc/systemd/", "/var/lib/nuxel/",
    "/usr/local/", "/var/tmp/", "/var/lib/", "/run/nuxel", "/dev/block/",
    "/dev/input", "/dev/fb", "/proc/", "/sys/", "/dev/", "/run/", "/etc/",
)
#: Device nodes the shell itself must keep pointing at the *host* (redirections).
DEV_PASSTHRU = ("/dev/null", "/dev/stdout", "/dev/stderr", "/dev/zero", "/dev/tty")

SENTINEL = "\x00NXLDEV%d\x00"


def unprotect_devs(cmd: str) -> str:
    for tok in DEV_PASSTHRU:
        cmd = cmd.replace(SENTINEL % DEV_PASSTHRU.index(tok), tok)
    return cmd


def protect_devs(cmd: str) -> str:
    for i, tok in enumerate(DEV_PASSTHRU):
        cmd = cmd.replace(tok, SENTINEL % i)
    return cmd


_MAP_RE = re.compile("|".join(re.escape(p) for p in PATH_MAP))


def map_paths(cmd: str, root: str) -> str:
    """Rewrite device-absolute paths onto the fake root, in ONE pass.

    A single pass matters: iterating the prefix table re-mapped paths that had
    already been prefixed (the temp root itself contains /var/lib/...-looking
    text), which produced a doubled root and bogus "No such file" output.
    """
    cmd = protect_devs(cmd)
    cmd = _MAP_RE.sub(lambda m: root + m.group(0), cmd)
    return unprotect_devs(cmd)


SHIM_SHA256SUM = """#!/bin/sh
# target shim: GNU coreutils sha256sum on a host that has shasum instead
case "$1" in
  -c) f="$2"; rc=0
      while IFS= read -r line; do
        [ -n "$line" ] || continue
        want=$(printf '%s' "$line" | cut -d' ' -f1)
        path=$(printf '%s' "$line" | cut -d' ' -f3-)
        [ -n "$path" ] || path=$(printf '%s' "$line" | cut -d' ' -f2)
        if [ ! -e "$path" ]; then echo "$path: FAILED (missing)"; rc=1; continue; fi
        got=$(shasum -a 256 "$path" | cut -d' ' -f1)
        if [ "$got" = "$want" ]; then echo "$path: OK"; else echo "$path: FAILED"; rc=1; fi
      done < "$f"; exit $rc ;;
  *) for f in "$@"; do [ -e "$f" ] || { echo "sha256sum: $f: No such file or directory"; exit 1; }
       printf '%s  %s\\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$f"; done ;;
esac
"""

SHIM_SYSTEMCTL = """#!/bin/sh
# target shim: stateful fake systemd. Unit state lives in $NXL_FAKE_ROOT/run/nuxel-units/<unit>
S="$NXL_FAKE_ROOT/run/nuxel-units"; mkdir -p "$S"
act() { echo "$1" > "$S/$2"; }
case "$1" in
  is-active) u="$2"; [ -f "$S/$u" ] && cat "$S/$u" || echo inactive; exit 0 ;;
  restart)   u="$2"; act active "$u"; echo "restart $u ok" ;;
  start)     u="$2"; act active "$u"; echo "start $u ok" ;;
  stop)      u="$2"; act inactive "$u"; echo "stop $u ok" ;;
  --failed)  echo "0 loaded units listed." ;;
  reboot)    : > "$NXL_FAKE_ROOT/run/reboot-requested"; echo "reboot requested" ;;
  *)         echo "systemctl shim: unhandled $*"; exit 1 ;;
esac
exit 0
"""

#: The plain `reboot` command a root shell would use.  Both entry points set the
#: same flag so the harness can model a power cycle for the offline reboot tests.
SHIM_REBOOT = """#!/bin/sh
: > "$NXL_FAKE_ROOT/run/reboot-requested"
echo "reboot requested"
"""

SHIM_MISC = """#!/bin/sh
case "$NXL_SHIM" in
  uname)    echo "${NXL_FAKE_KERNEL:-4.14.253-nuxel-g9f2c}" ;;
  hostname) echo s10plus ;;
  id)       echo "uid=0(root) gid=0(root) groups=0(root) context=system_u:system_r:kernel_t" ;;
  uptime)   cat "$NXL_FAKE_ROOT/proc/uptime" ;;
esac
"""

SHIM_CURL = """#!/bin/sh
# target shim: curl against the fake launcher's registry
url=""; code=200
for a in "$@"; do case "$a" in http*) url="$a";; -o) shift;; esac; done
case "$url" in
  *-w*) ;;
esac
case "$*" in *%{http_code}*) printf '200\\n'; exit 0;; esac
if [ -f "$NXL_FAKE_ROOT/var/lib/nuxel/pwa/registry.json" ]; then
  head -c 400 "$NXL_FAKE_ROOT/var/lib/nuxel/pwa/registry.json"; echo; exit 0
fi
echo "curl shim: no registry"; exit 7
"""


def build_fake_root(root: str, mode: str = "healthy"):
    """Materialise an A32-baseline-shaped device tree under `root`."""
    def w(rel, text, mode_=0o644):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        os.chmod(p, mode_)
        return p

    for d in ("proc", "sys", "dev/input/by-path", "dev/block/by-name", "run",
              "var/lib/nuxel", "var/tmp", "etc/nuxel", "etc/systemd/system",
              "usr/local/bin", "home/nuxel/nuxel/pwa/nuxel-home",
              "bin", "sbin", "usr/bin", "run/nuxel-units", "var/lib/nuxel/pwa"):
        os.makedirs(os.path.join(root, d), exist_ok=True)

    post = (mode == "post-reboot")
    w("proc/uptime", "24.10 91.44" if post else "18432.55 51233.11")
    w("proc/sys/kernel/random/boot_id",
      "b41f7c9e-6d21-4f8a-9e77-2c0d51a4f8b3" if post
      else "1d6f0a77-2b93-4c58-8d1e-77ae30c9b4d2")
    w("var/lib/nuxel/boot-count", "8" if post else "7")
    w("proc/cmdline",
      "console=ttySAC2,115200 androidboot.mode=normal androidboot.hardware=beyond2lte "
      "androidboot.selinux=permissive nuxel.bootmode=normal")
    w("proc/interrupts",
      "           CPU0       CPU1\n 41:      92833          0       GIC  41 Level     sec_ts\n")
    w("proc/asound/cards",
      " 0 [beyondmadera   ]: beyond-madera - beyond-madera\n"
      "                      Samsung Exynos9820-Audio (beyond-madera)")
    w("proc/bus/input/devices",
      'I: Bus=0018 Vendor=0000 Product=0000 Version=0000\n'
      'N: Name="sec_touchscreen"\n'
      'P: Phys=0-0048/input0\n'
      'S: Sysfs=/devices/.../input/input2\n'
      'U: Uniq=\n'
      'H: Handlers=event4\nB: PROP=2\nB: EV=b\n')
    w("dev/input/by-path/platform-0-0048-event", "event4")
    w("dev/fb0-info", "var:640x1440 depth:32\n")
    w("run/nuxel-wl-fb.state", "owner=nuxel-wl-fb pid=812 fb=/dev/fb0 state=running")
    w("var/lib/nuxel/fb-owner", "nuxel-wl-fb")
    w("var/lib/nuxel/animation", "handoff=ok ready=1 fb_owner=nuxel-wl-fb at=2026-10-16T16:02:11Z")
    w("var/lib/nuxel/pwa/registry.json",
      '{"schema":1,"apps":[{"id":"nuxel-home","title":"Nuxel Home","url":"/index.html"},'
      '{"id":"terminal","title":"Terminal","url":"/apps/terminal/"}]}')
    w("etc/nuxel/button/gestures.conf", "# A32 baseline gesture state machine\n")
    w("etc/nuxel/touch/nuxel-touch.conf", "# A32 baseline touch config\n")
    w("etc/systemd/system/nuxel-wl-fb.service", "[Unit]\nDescription=Nuxel fb bridge\n")
    w("usr/local/bin/nuxel-wl-fb", "#!/bin/sh\necho nuxel-wl-fb\n", 0o755)
    pwa = ("index.html", "js/apps.js", "js/qs.js", "js/status-bar.js", "js/safe-zones.js")
    for rel in pwa:
        w("home/nuxel/nuxel/pwa/nuxel-home/" + rel,
          "<!-- fake A32 PWA baseline: %s -->" % rel)

    units = {"nuxel-wayland": "active", "nuxel-wl-fb": "active",
             "nuxel-button-manager": "active", "nuxel-touch-arm": "active",
             "seatd": "active", "nuxel-pwa": "active", "nuxel-console": "active"}
    if mode == "touch-broken":
        units["nuxel-touch-arm"] = "failed"
    if mode == "no-launcher":
        units["nuxel-pwa"] = "inactive"
    for u, s in units.items():
        w("run/nuxel-units/" + u, s)

    shim = os.path.join(root, "nxl-shim")
    os.makedirs(shim, exist_ok=True)
    for name, body in (("sha256sum", SHIM_SHA256SUM), ("systemctl", SHIM_SYSTEMCTL),
                       ("curl", SHIM_CURL)):
        p = os.path.join(shim, name)
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, 0o755)
    for name, body in (("reboot", SHIM_REBOOT),):
        p = os.path.join(shim, name)
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, 0o755)
    for name in ("uname", "hostname", "id", "uptime"):
        p = os.path.join(shim, name)
        with open(p, "w") as fh:
            fh.write(SHIM_MISC)
        os.chmod(p, 0o755)
    return shim


class FakeConsole:
    """PTY server that speaks the live-console framing over a fake root."""

    def __init__(self, root, mode="healthy", shim=None, log=None):
        self.root, self.mode = root, mode
        self.shim = shim or os.path.join(root, "nxl-shim")
        self.log = log or []
        self.master, self.slave = os.openpty()
        try:
            self.name = os.ttyname(self.slave)
        except OSError:
            self.name = None
        self.buf = b""
        self.running = True
        self.requests = 0

    # -- protocol ---------------------------------------------------------- #
    def respond(self, rid, rc, body):
        b64 = base64.b64encode(body).decode()
        sha = hashlib.sha256(body).hexdigest()
        out = ("\n@@B%s@@\n@@R%s:%s@@\n%s\n@@S%s:%s@@\n@@E%s@@\n"
               % (rid, rid, rc, b64, rid, sha, rid))
        os.write(self.master, out.encode())

    SCRIPT_RE = re.compile(r"sh (/[\w./+-]+\.sh)")

    def materialise_scripts(self, mapped_cmd):
        """Rewrite device paths *inside* a staged script, as the device would run it.

        A deploy pushes its install script to /var/tmp and runs `sh <path>`, so the
        path translation has to happen to the file's contents, not to the command
        line.  Doing it here keeps the offline harness faithful to the real flow.
        """
        for m in self.SCRIPT_RE.finditer(mapped_cmd):
            real = m.group(1)
            if not os.path.isfile(real):
                continue
            try:
                with open(real) as fh:
                    body = fh.read()
                with open(real, "w") as fh:
                    fh.write(map_paths(body, self.root))
            except OSError:
                pass

    def execute(self, cmd):
        mapped = map_paths(cmd, self.root)
        self.materialise_scripts(mapped)
        env = dict(os.environ)
        env["PATH"] = self.shim + ":" + env.get("PATH", "/usr/bin:/bin")
        env["NXL_FAKE_ROOT"] = self.root
        env["NXL_FAKE_KERNEL"] = "4.14.253-nuxel-g9f2c"
        if cmd.strip().split(" ")[0] in ("uname", "hostname", "id", "uptime"):
            env["NXL_SHIM"] = cmd.strip().split(" ")[0]
            mapped = os.path.join(self.shim, cmd.strip().split(" ")[0])
            if len(cmd.strip().split(" ")) > 1:
                mapped += " " + " ".join(cmd.strip().split(" ")[1:])
        try:
            p = subprocess.run(["/bin/sh", "-c", mapped], capture_output=True,
                               env=env, cwd=self.root, timeout=25)
            return p.returncode, p.stdout + p.stderr
        except subprocess.SubprocessError as e:
            return 126, ("fake console could not run command: %s" % e).encode()

    def handle_line(self, line):
        line = line.strip("\r\n")
        if self.mode == "silent":
            # the measured failure mode: the gadget is enumerated but nothing
            # on the far end ever answers — not a CR echo, not a frame.
            return
        if not line:
            os.write(self.master, b"\r\nnuxel@s10plus:~$ ")
            return
        m = WRAPPER_RE.search(line)
        if not m:
            if self.mode != "silent":
                os.write(self.master, ("\r\nsh: %s\r\nnuxel@s10plus:~$ " % line[:120]).encode())
            return
        self.requests += 1
        rid = m.group("rid")
        rc, body = self.execute(m.group("cmd"))
        self.log.append({"rid": rid, "cmd": m.group("cmd"), "rc": rc,
                         "bytes": len(body)})
        if self.mode == "frame-broken":
            # a far end that answers but never frames a verified result
            os.write(self.master, b"sh: unexpected token\r\n")
            return
        self.respond(rid, rc, body)

    def serve(self, seconds=600.0, ready_file=None):
        if ready_file:
            with open(ready_file, "w") as fh:
                fh.write(self.name or "")
        t0 = time.time()
        while self.running and time.time() - t0 < seconds:
            r, _, _ = select.select([self.master], [], [], 0.1)
            if not r:
                continue
            try:
                chunk = os.read(self.master, 65536)
            except OSError:
                break
            if not chunk:
                break
            self.buf += chunk
            stopped = False
            while b"\r" in self.buf:
                line, self.buf = self.buf.split(b"\r", 1)
                self.handle_line(line.decode("utf-8", "replace"))
                if os.path.exists(os.path.join(self.root, "run", "reboot-requested")):
                    # the "device" is power-cycling: this console stops serving, so
                    # the host must reconnect (and re-resolve the node) from scratch
                    stopped = True
                    break
            if stopped:
                break

    def close(self):
        for fd in (self.master, self.slave):
            try:
                os.close(fd)
            except OSError:
                pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="offline fake Nuxel live console")
    ap.add_argument("--root", required=True)
    ap.add_argument("--mode", default="healthy",
                    choices=("healthy", "silent", "frame-broken", "touch-broken",
                             "no-launcher", "post-reboot"))
    ap.add_argument("--ready-file", default=None)
    ap.add_argument("--seconds", type=float, default=600.0)
    ap.add_argument("--log", default=None)
    args = ap.parse_args(argv)

    build = not os.path.exists(os.path.join(args.root, "proc", "uptime"))
    shim = build_fake_root(args.root, args.mode) if build else None
    fc = FakeConsole(args.root, args.mode, shim=shim)
    try:
        fc.serve(args.seconds, args.ready_file)
    except KeyboardInterrupt:
        pass
    finally:
        if args.log:
            import json
            with open(args.log, "w") as fh:
                json.dump(fc.log, fh, indent=2)
        fc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
