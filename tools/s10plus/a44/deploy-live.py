#!/usr/bin/env python3
"""A44 atomic userspace deploy over the live S10+ USB console.

Only the launcher code/manifest that changed for icon delivery is written, plus
the generated icon registry.  Every target is backed up, staged through verified
frames, installed by same-directory rename, read back by SHA-256, and protected
by a generated rollback script.  Static webroot files need no service restart;
the already-running WebKit view is reloaded through the host's own FIFO (or the
host's documented web-process recovery path if the old host binary refuses the
new action).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/beta/live"))
import nuxel_live as nl  # noqa: E402

DEV_ROOT = "/usr/share/nuxel"
# Physical tree behind the /pwa/nuxel-home symlink that nuxel-web serves.
FILES = [
    "pwa/nuxel-home/index.html",
    "pwa/nuxel-home/manifest.json",
    "pwa/nuxel-home/sw.js",
    "pwa/nuxel-home/icon-registry.json",
    "pwa/nuxel-home/js/apps.js",
    "pwa/nuxel-home/js/qs.js",
    "pwa/nuxel-home/js/icon-health.js",
    "pwa/nuxel-home/icon-health-trigger.json",
    "pwa/nuxel-common/app-registry.json",
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(c, command, timeout=35, tries=4):
    last = None
    for attempt in range(tries):
        r = c.run(command, timeout=timeout)
        if r.ok:
            return r
        last = r
        c.interrupt()
        time.sleep(0.35 + attempt * 0.25)
    raise RuntimeError("console frame failed after %d tries for %r" % (tries, command[:80]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--evidence-dir", default=str(ROOT / "docs/live/v0.6.3-beta-20261020-a44"))
    ap.add_argument("--backup", help="reuse an existing pre-deploy backup directory")
    args = ap.parse_args()
    ev = Path(args.evidence_dir)
    ev.mkdir(parents=True, exist_ok=True)

    plan = []
    for rel in FILES:
        src = ROOT / rel
        if not src.is_file():
            raise SystemExit("missing source: " + rel)
        data = src.read_bytes()
        plan.append({"source": rel, "target": DEV_ROOT + "/" + rel.replace("pwa/nuxel-home/", "nuxel-home/", 1)
                     if rel.startswith("pwa/nuxel-home/") else DEV_ROOT + "/" + rel,
                     "bytes": len(data), "sha256": sha(data)})
    print(json.dumps({"plan": plan, "apply": args.apply}, indent=2))
    if not args.apply:
        print("DRY-RUN: no device write attempted")
        return 0

    nodes = nl.enumerate_console_nodes()
    node = ({"callout": args.dev, "match_stage": "explicit"} if args.dev
            else nl.select_console_node(nodes, serial=nl.DEFAULT_SERIAL))
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = args.backup or ("/var/backups/nuxel/a44-icon-delivery-" + stamp)
    stage = "/var/tmp/nuxel-a44-stage-" + stamp

    with nl.Console(node["callout"], timeout=30, lock_wait=30) as c:
        probe = c.probe(6.0)
        if not probe.reachable:
            raise SystemExit("console byte-silent: " + json.dumps(probe.as_dict()))
        pre = run(c, "uname -m; uname -r; pid=$(pgrep -f 'http.server 8000'|head -1); "
                     "readlink -f /proc/$pid/cwd 2>/dev/null; "
                     "test -f %s/nuxel-home/index.html && echo WEBROOT-OK; "
                     "systemctl is-active nuxel-wayland nuxel-wl-fb" % DEV_ROOT)
        print("PREFLIGHT:\n" + pre.output)
        if "aarch64" not in pre.output or "WEBROOT-OK" not in pre.output:
            raise SystemExit("preflight failed: wrong architecture or webroot")
        if "active" not in pre.output:
            raise SystemExit("UI units are not active; refusing to deploy")

        mk = run(c, "mkdir -p %s/webroot %s/staged && echo BACKUP-READY" % (backup, stage))
        if "BACKUP-READY" not in mk.output:
            raise SystemExit("cannot create backup/stage roots")
        # A plan file keeps every console command short.  Long inline paths were
        # intermittently shredded by the kmsg-mirroring console even though the
        # remote command itself was correct.
        plan_text = "".join("%s\t%s\n" % (x["source"], x["target"]) for x in plan)
        nl.push_bytes(c, plan_text.encode(), "/var/tmp/nxl-a44-plan", mode="0644")
        backup_helper = r"""#!/bin/sh
set -eu
B=$1
while IFS='	' read -r rel target; do
  bpath="$B/webroot/$rel"
  mkdir -p "$(dirname "$bpath")"
  if [ -e "$bpath" ]; then
    printf '%s PRESENT %s\n' "$rel" "$(sha256sum "$bpath"|cut -d' ' -f1)"
  elif [ -e "$target" ]; then
    cp -a "$target" "$bpath"
    printf '%s PRESENT %s\n' "$rel" "$(sha256sum "$bpath"|cut -d' ' -f1)"
  else
    printf '%s MISSING\n' "$rel"
  fi
done < /var/tmp/nxl-a44-plan
"""
        nl.push_bytes(c, backup_helper.encode(), "/var/tmp/nxl-a44-backup.sh", mode="0755")
        rb = run(c, "sh /var/tmp/nxl-a44-backup.sh '%s'" % backup)
        plan_lines = [x for x in rb.output.replace("\r", "").splitlines() if x.strip()]
        records = []
        for item, line in zip(plan, plan_lines):
            parts = line.split()
            if len(parts) < 2 or parts[0] != item["source"]:
                raise SystemExit("backup receipt mismatch: %r" % line)
            prev = parts[1] + ((" " + parts[2]) if len(parts) > 2 else "")
            records.append(dict(item, backup=backup + "/webroot/" + item["source"], previous=prev))
            data = (ROOT / item["source"]).read_bytes()
            push = nl.push_bytes(c, data, stage + "/" + Path(item["source"]).name, mode="0644")
            if push["decoded_sha256"] != item["sha256"]:
                raise SystemExit("staged hash mismatch for " + item["source"])

        installed = []
        for item in plan:
            rel, target = item["source"], item["target"]
            bpath = backup + "/webroot/" + rel
            staged = stage + "/" + Path(rel).name
            script = (
                "set -eu\n"
                "T=%s\nS=%s\nB=%s\nW=%s\n"
                "mkdir -p \"$(dirname \"$T\")\"\n"
                "install -o root -g root -m 0644 \"$S\" \"$T.a44.$$\"\n"
                "mv -f \"$T.a44.$$\" \"$T\"\n"
                "C=$(sha256sum \"$T\"|cut -d' ' -f1)\n"
                "if [ \"$C\" != \"$W\" ]; then\n"
                "  if [ -e \"$B\" ]; then cp -a \"$B\" \"$T.a44.rb.$$\"; mv -f \"$T.a44.rb.$$\" \"$T\"; else rm -f \"$T\"; fi\n"
                "  echo INSTALL-FAIL $T got=$C want=$W\n  exit 1\nfi\n"
                "echo INSTALLED $T $C\n"
            ) % (target, staged, bpath, item["sha256"])
            sp = "/var/tmp/nxl-a44-install.sh"
            nl.push_bytes(c, script.encode(), sp, mode="0755")
            r = run(c, "sh %s" % sp)
            if "INSTALLED" not in r.output:
                raise SystemExit("install failed for %s: %s" % (rel, r.output[-600:]))
            installed.append({"source": rel, "target": target, "sha256": item["sha256"],
                              "previous": next(x["previous"] for x in records if x["source"] == rel)})

        rollback = backup + "/rollback.sh"
        rollback_stage = "/var/tmp/nxl-a44-rollback.sh"
        lines = ["#!/bin/sh", "set -eu", "B=%s" % backup,
                 "W=%s" % DEV_ROOT, "echo ROLLBACK %s" % backup]
        for item, rec in zip(plan, records):
            b = backup + "/webroot/" + item["source"]
            t = item["target"]
            if rec["previous"].startswith("PRESENT"):
                lines.append("mkdir -p \"$(dirname '%s')\"" % t)
                lines.append("install -o root -g root -m 0644 '%s' '%s.a44rb.$$' && mv -f '%s.a44rb.$$' '%s'" % (b, t, t, t))
            else:
                lines.append("rm -f '%s'" % t)
        lines += ["printf 'reload-launcher\\n' > /run/nuxel-pwa-host.cmd 2>/dev/null || true",
                  "echo ROLLBACK-COMPLETE"]
        rb = "\n".join(lines) + "\n"
        nl.push_bytes(c, rb.encode(), rollback_stage, mode="0755")
        run(c, "install -o root -g root -m 0755 %s %s" % (rollback_stage, rollback))
        vb = run(c, "sha256sum %s; sed -n '1,6p' %s" % (rollback, rollback))

        # Reload the live launcher. Static installs do not require a unit restart.
        before_log = run(c, "wc -l < /run/nuxel-web.log 2>/dev/null || echo 0").output.strip()
        run(c, "printf 'reload-launcher\\n' > /run/nuxel-pwa-host.cmd 2>&1 || true")
        time.sleep(7)
        after = run(c, "tail -30 /run/nuxel-web.log 2>/dev/null; echo ===HOST===; tail -12 /run/nuxel-home.state 2>/dev/null")

        # If the old host binary refused the action, use its documented recovery
        # path: terminate only WebKitWebProcess once; the host reloads the view.
        recent = after.output
        if "reload-launcher" not in recent and "GET /pwa/nuxel-home/index.html" not in recent:
            run(c, "for p in $(pgrep -x WebKitWebProcess); do kill -TERM $p; done; true")
            time.sleep(8)
            after2 = run(c, "tail -40 /run/nuxel-web.log 2>/dev/null; echo ===HOST===; tail -12 /run/nuxel-home.state 2>/dev/null")
            after_text = after.output + "\n===FALLBACK===\n" + after2.output
        else:
            after_text = after.output

        hash_helper = r"""#!/bin/sh
set -eu
while IFS='	' read -r rel target; do
  printf '%s ' "$rel"
  sha256sum "$target" | cut -d' ' -f1
done < /var/tmp/nxl-a44-plan
"""
        nl.push_bytes(c, hash_helper.encode(), "/var/tmp/nxl-a44-hash.sh", mode="0755")
        post = run(c, "sh /var/tmp/nxl-a44-hash.sh")
        svc = run(c, "systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-bridge nuxel-http-bridge")
        ev.joinpath("deploy.json").write_text(json.dumps({
            "timestamp_utc": stamp, "device": "SM-G975F beyond2lte", "arch": "aarch64",
            "console": node["callout"], "backup_dir": backup, "stage_dir": stage,
            "rollback": rollback, "installed": installed, "preflight": pre.output,
            "reload_evidence": after_text, "post_hashes": post.output,
            "services": svc.output, "rollback_script_sha256": vb.output.splitlines()[0],
        }, indent=2) + "\n")
        ev.joinpath("deploy.log").write_text(pre.output + "\n" + "\n".join(
            "INSTALLED %s %s" % (x["target"], x["sha256"]) for x in installed) +
            "\n===RELOAD===\n" + after_text + "\n===POST HASHES===\n" + post.output)
        print("DEPLOY_COMPLETE backup=%s rollback=%s" % (backup, rollback))
        print(installed)
        print(after_text)
        print(post.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
