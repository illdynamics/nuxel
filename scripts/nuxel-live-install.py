#!/usr/bin/env python3
"""Install a Nuxel live-userspace staging tarball on the running phone.

The tarball is produced by scripts/nuxel-deploy-live.py and contains:

    plan.json                  [{source,target,mode,sha256,bytes}, ...]
    files/<repo-relative>      exact bytes from tools/s10plus/a43/package-live.py

This installer is intentionally userspace-only.  It refuses any target outside
the phone userspace roots, backs up every replaced file, installs atomically and
rolls the whole transaction back if a service health check fails.

Usage (normally invoked by nuxel-deploy-live.py):
  sudo python3 nuxel-live-install.py --payload /tmp/nuxel-live.tar.gz

Safety:
  * no partition, kernel, DTB/DTBO, firmware, modem/EFS or block-device writes;
  * every source is SHA-256 checked against the plan before one byte is written;
  * the previous file bytes are kept under
    /var/lib/nuxel/live-deploy/rollback-<stamp>/<absolute target>;
  * --root DIR installs into a local test root and never calls systemctl.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ALLOWED_PREFIXES = (
    "/usr/share/nuxel/",
    "/usr/share/applications/",
    "/usr/share/xdg-desktop-portal/",
    "/usr/share/dbus-1/services/",
    "/etc/xdg-desktop-portal/",
    "/usr/lib/nuxel/",
    "/usr/libexec/nuxel/",
    "/usr/bin/nuxel-",
    "/etc/nuxel/",
    "/etc/profile.d/",
    "/etc/xrdp/",
    "/etc/pam.d/",
    "/etc/dbus-1/system.d/",
    "/etc/systemd/system/",
    "/usr/local/libexec/nuxel/",
    "/usr/local/bin/nuxel-",
)
FORBIDDEN_PARTS = ("/dev/", "/boot/", "/proc/", "/sys/", "/run/", "/var/lib/nuxel/live-deploy/")
FORBIDDEN_SUFFIXES = (".img", ".dtb", ".dtbo", ".gz", ".tar", ".ko")

# v0.8.2: the legacy profile hook printed a second, different ASCII banner on
# top of sshd's canonical /etc/banner.  /etc/profile.d/nuxel-banner.sh is now
# the one local-TTY hook and is silent for SSH; retire the duplicate.
LEGACY_REMOVE = ("/etc/profile.d/99-nuxel-banner.sh",)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_target(target: str) -> bool:
    if not target.startswith("/") or ".." in target.split("/"):
        return False
    if not any(target.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False
    if any(part in target for part in FORBIDDEN_PARTS):
        return False
    if target.endswith(FORBIDDEN_SUFFIXES):
        return False
    return True


def under_root(root: Path, target: str) -> Path:
    return root / target.lstrip("/")


def rollback(root: Path, backup_root: Path, entries: list[dict], changed: list[str]) -> None:
    for target in reversed(changed):
        dest = under_root(root, target)
        backup = backup_root / target.lstrip("/")
        try:
            if backup.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(backup, dest)
                shutil.copymode(backup, dest)
                print("ROLLBACK restored %s" % target)
            elif dest.exists():
                dest.unlink()
                print("ROLLBACK removed %s" % target)
        except OSError as exc:
            print("ROLLBACK FAILED %s: %s" % (target, exc), file=sys.stderr)


def systemctl(*args: str, check: bool = False) -> int:
    return subprocess.run(["systemctl", *args], check=check).returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--stamp", default=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    ap.add_argument("--root", default="/")
    ap.add_argument("--restart", default="nuxel-bridge,nuxel-http-bridge,nuxel-soundd,nuxel-clockd")
    ap.add_argument("--no-restart", action="store_true")
    ap.add_argument("--health-timeout", type=float, default=25.0)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    local = root == Path("/")
    payload = Path(args.payload)
    if not payload.is_file():
        print("missing payload: %s" % payload, file=sys.stderr)
        return 2

    work = Path(tempfile.mkdtemp(prefix="nuxel-live-install-"))
    changed: list[str] = []
    backup_root = root / "var/lib/nuxel/live-deploy" / ("rollback-" + args.stamp)
    try:
        with tarfile.open(payload, "r:gz") as tf:
            for member in tf.getmembers():
                name = Path(member.name)
                if name.is_absolute() or ".." in name.parts or member.issym() or member.islnk() or member.isdev():
                    raise SystemExit("unsafe payload member: %s" % member.name)
            tf.extractall(work, filter="data")

        plan = json.loads((work / "plan.json").read_text())
        if not isinstance(plan, list) or not plan:
            raise SystemExit("plan.json is empty")

        # Validate the whole plan before touching the device.
        seen: dict[str, str] = {}
        for entry in plan:
            target = entry["target"]
            source = entry["source"]
            if not safe_target(target):
                raise SystemExit("refused target: %s" % target)
            src = work / "files" / source
            if not src.is_file():
                raise SystemExit("payload missing source: %s" % source)
            got = sha256_file(src)
            if got != entry["sha256"]:
                raise SystemExit("payload hash mismatch for %s: %s != %s" % (source, got, entry["sha256"]))
            if target in seen and seen[target] != got:
                raise SystemExit("conflicting bytes for target %s" % target)
            seen[target] = got
        print("VALIDATED %d file(s), %d target(s)" % (len(plan), len(seen)))

        # Back up and install.
        for entry in plan:
            source, target, mode = entry["source"], entry["target"], int(entry["mode"])
            src = work / "files" / source
            dest = under_root(root, target)
            if dest.exists() and dest.is_dir():
                raise SystemExit("refusing to replace directory: %s" % target)
            if target not in changed:
                if dest.exists():
                    backup = backup_root / target.lstrip("/")
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, backup)
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_name(dest.name + ".nuxel-new")
                shutil.copyfile(src, tmp)
                os.chmod(tmp, mode)
                os.replace(tmp, dest)
                changed.append(target)
            got = sha256_file(dest)
            if got != entry["sha256"]:
                raise SystemExit("installed hash mismatch for %s: %s != %s" % (target, got, entry["sha256"]))
        for target in LEGACY_REMOVE:
            if target in seen:
                continue
            dest = under_root(root, target)
            if not dest.exists() and not dest.is_symlink():
                continue
            backup = backup_root / target.lstrip("/")
            backup.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_symlink():
                os.symlink(os.readlink(dest), backup)
            elif dest.is_file():
                shutil.copy2(dest, backup)
            dest.unlink()
            changed.append(target)
            print("RETIRED legacy file %s" % target)
        print("INSTALLED %d target(s); rollback=%s" % (len(changed), backup_root))

        if not local:
            print("SKIP systemd checks for --root %s" % root)
            print("DEPLOY_COMPLETE stamp=%s targets=%d" % (args.stamp, len(changed)))
            return 0

        systemctl("daemon-reload")
        if not args.no_restart and args.restart.strip():
            services = [s.strip() for s in args.restart.split(",") if s.strip()]
            for svc in services:
                systemctl("restart", svc)
            deadline = time.time() + args.health_timeout
            failed = []
            while time.time() < deadline:
                failed = [svc for svc in services if systemctl("is-active", "--quiet", svc) != 0]
                if not failed:
                    break
                time.sleep(1)
            if failed:
                print("HEALTH_FAILED %s; rolling back" % ",".join(failed), file=sys.stderr)
                rollback(root, backup_root, plan, changed)
                systemctl("daemon-reload")
                for svc in services:
                    systemctl("restart", svc)
                return 1
            print("HEALTH_OK %s" % ",".join(services))

        # The firewall provider is imported by the bridge; prove the installed
        # layout resolves before declaring the deploy complete.
        sys.path.insert(0, "/usr/lib/nuxel/nuxel-firewall")
        try:
            import nuxel_firewall.provider  # noqa: F401
            print("FIREWALL_IMPORT_OK")
        except Exception as exc:  # pragma: no cover - on-device check
            print("FIREWALL_IMPORT_FAILED %s; rolling back" % exc, file=sys.stderr)
            rollback(root, backup_root, plan, changed)
            systemctl("daemon-reload")
            return 1

        (backup_root / "COMMITTED").parent.mkdir(parents=True, exist_ok=True)
        (backup_root / "COMMITTED").write_text(args.stamp + "\n")
        print("DEPLOY_COMPLETE stamp=%s targets=%d" % (args.stamp, len(changed)))
        return 0
    except SystemExit:
        raise
    except Exception as exc:
        print("DEPLOY_FAILED %s" % exc, file=sys.stderr)
        if changed:
            rollback(root, backup_root, [], changed)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
