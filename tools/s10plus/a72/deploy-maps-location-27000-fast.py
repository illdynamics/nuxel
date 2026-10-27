#!/usr/bin/env python3
"""Fast, verified PWNAGE-27000 userspace deploy.

1. pack the changed files into one archive and upload it over WLAN SSH with
   nuxel-live-ssh.py --put (staged SHA-256 verified);
2. through the serial root console, extract into /home/nuxel, back up each
   target under /var/lib/nuxel/a72/rollback-<stamp>/, install only files whose
   SHA-256 differs, and verify every readback;
3. restart only the bridge units whose code changed and collect live evidence.

No serial port is held while the upload happens; the root console is used only
for short, bounded install/verify commands.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "beta", "live"))
import nuxel_live as nl  # noqa: E402

FILES = [
    ("pwa/nuxel-common/maps-core.js", "/usr/share/nuxel/pwa/nuxel-common/maps-core.js", "0644"),
    ("pwa/nuxel-common/bridge.js", "/usr/share/nuxel/pwa/nuxel-common/bridge.js", "0644"),
    ("pwa/nuxel-common/app-registry.json", "/usr/share/nuxel/pwa/nuxel-common/app-registry.json", "0644"),
    ("pwa/nuxel-common/app-registry.json", "/etc/nuxel/app-registry/app_registry.json", "0644"),
    ("pwa/nuxel-apps/maps/index.html", "/usr/share/nuxel/pwa/nuxel-apps/maps/index.html", "0644"),
    ("pwa/nuxel-apps/maps/app.json", "/usr/share/nuxel/pwa/nuxel-apps/maps/app.json", "0644"),
    ("pwa/nuxel-apps/maps/manifest.json", "/usr/share/nuxel/pwa/nuxel-apps/maps/manifest.json", "0644"),
    ("pwa/nuxel-apps/maps/sw.js", "/usr/share/nuxel/pwa/nuxel-apps/maps/sw.js", "0644"),
    ("pwa/nuxel-apps/maps/js/maps.js", "/usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js", "0644"),
    ("pwa/nuxel-apps/maps/css/maps.css", "/usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css", "0644"),
    ("pwa/nuxel-home/js/qs.js", "/usr/share/nuxel/pwa/nuxel-home/js/qs.js", "0644"),
    ("pwa/nuxel-apps/settings/index.html", "/usr/share/nuxel/pwa/nuxel-apps/settings/index.html", "0644"),
    ("pwa/nuxel-apps/settings/app.json", "/usr/share/nuxel/pwa/nuxel-apps/settings/app.json", "0644"),
    ("pwa/nuxel-apps/settings/manifest.json", "/usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json", "0644"),
    ("pwa/nuxel-apps/settings/settings.js", "/usr/share/nuxel/pwa/nuxel-apps/settings/settings.js", "0644"),
    ("pwa/nuxel-apps/settings/location-maps.js", "/usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js", "0644"),
    ("services/nuxel-bridge/src/bridge.py", "/usr/lib/nuxel/nuxel-bridge/bridge.py", "0644"),
    ("services/nuxel-bridge/src/api.py", "/usr/lib/nuxel/nuxel-bridge/api.py", "0644"),
    ("configs/nuxel/gnss/gnss.json", "/etc/nuxel/gnss/gnss.json", "0644"),
    ("configs/nuxel/gnss/osm-tiles.json", "/etc/nuxel/gnss/osm-tiles.json", "0644"),
    ("configs/nuxel/permissions/org.nuxel.Home.json", "/var/lib/nuxel/permissions/org.nuxel.Home.json", "0644"),
    ("configs/nuxel/permissions/nuxel-settings.json", "/var/lib/nuxel/permissions/nuxel-settings.json", "0644"),
    ("configs/nuxel/permissions/org.nuxel.Maps.json", "/var/lib/nuxel/permissions/org.nuxel.Maps.json", "0644"),
    ("services/nuxel-bridge/dbus/org.nuxel.Bridge.conf", "/etc/dbus-1/system.d/org.nuxel.Bridge.conf", "0644"),
    ("tools/s10plus/a33/nuxel-gnss-diag.sh", "/usr/local/bin/nuxel-gnss-diag.sh", "0755"),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_archive(path):
    with tarfile.open(path, "w:gz") as tar:
        for rel, _remote, _mode in FILES:
            tar.add(os.path.join(ROOT, rel), arcname=rel)
    return sha256_file(path)


def main():
    stamp = time.strftime("%Y%m%dT%H%M%S%z")
    archive = "/tmp/nuxel27000-" + stamp + ".tar.gz"
    remote_archive = "/home/nuxel/nuxel27000.tar.gz"
    staging = "/home/nuxel/nuxel27000"
    archive_sha = build_archive(archive)
    key = os.environ.get("NUXEL_SSH_KEY") or "/home/wicked/.ssh/nuxel-tri-link_ed25519"
    known = os.path.join(ROOT, "configs", "nuxel", "security", "ssh", "known_hosts")
    put = subprocess.run([
        sys.executable, os.path.join(ROOT, "tools", "beta", "live", "nuxel-live-ssh.py"),
        "--transport", "wlan", "--host", "10.20.30.16", "--user", "nuxel",
        "--key", key, "--known-hosts", known, "--host-key-alias", "nuxel-s10plus",
        "--put", archive, remote_archive,
    ], capture_output=True, text=True)
    print("# upload rc=%s\n%s" % (put.returncode, (put.stdout + put.stderr)[-3000:]))
    if put.returncode != 0:
        raise SystemExit("upload failed")

    con, node, notes = nl.open_console(timeout=30.0)
    con.open()
    backup = "/var/lib/nuxel/a72/rollback-fast-" + stamp
    evidence = {"stamp": stamp, "console": node, "notes": notes, "archive_sha256": archive_sha,
                "files": [], "checks": {}, "backup_dir": backup}
    try:
        def run(cmd, timeout=30):
            last = None
            for attempt in range(3):
                r = con.run(cmd, timeout=timeout)
                if r.ok:
                    return r
                last = r
                print("# frame retry %d for %s (sha_ok=%s framed=%s)" %
                      (attempt + 1, cmd[:80], r.sha_ok, r.framed))
                time.sleep(0.4)
            raise SystemExit("console frame failed after retries: %s\n%s" % (cmd, last.output if last else ""))

        print("# console", node.get("callout"))
        r = run("sha256sum %s" % shlex.quote(remote_archive))
        got = r.output.strip().split()[0] if r.output.strip() else ""
        if got != archive_sha:
            raise SystemExit("archive checksum mismatch on phone: %s != %s" % (got, archive_sha))
        run("rm -rf %s && mkdir -p %s %s" % (shlex.quote(staging), shlex.quote(staging), shlex.quote(backup)))
        run("python3 -c \"import tarfile;tarfile.open('%s','r:gz').extractall('%s')\"" %
            (remote_archive, staging))

        for rel, remote, mode in FILES:
            local = os.path.join(ROOT, rel)
            local_sha = sha256_file(local)
            target_sha = run("sha256sum %s 2>/dev/null || echo absent" % shlex.quote(remote)).output.strip().split()[0]
            flat = remote.strip("/").replace("/", "_")
            entry = {"source": rel, "target": remote, "mode": mode, "sha256": local_sha,
                     "before": target_sha}
            if target_sha == local_sha:
                entry["action"] = "unchanged"
                evidence["files"].append(entry)
                print("# unchanged", remote)
                continue
            if target_sha != "absent":
                run("cp -a %s %s" % (shlex.quote(remote), shlex.quote(os.path.join(backup, flat))))
            src = os.path.join(staging, rel)
            run("install -m %s %s %s" % (mode, shlex.quote(src), shlex.quote(remote)))
            got_sha = run("sha256sum %s" % shlex.quote(remote)).output.strip().split()[0]
            if got_sha != local_sha:
                raise SystemExit("readback mismatch for %s: %s != %s" % (remote, got_sha, local_sha))
            entry["action"] = "installed"
            evidence["files"].append(entry)
            print("# installed", rel, "->", remote, local_sha[:16])

        changed = {e["source"] for e in evidence["files"] if e["action"] == "installed"}
        if any(src.startswith("configs/nuxel/permissions/") for src in changed):
            run("chown nuxel-bridge:nuxel-bridge /var/lib/nuxel/permissions/*.json")
        restart_needed = bool(changed & {
            "services/nuxel-bridge/src/bridge.py", "services/nuxel-bridge/src/api.py",
        }) or any(src.startswith("configs/nuxel/permissions/") for src in changed)
        if "services/nuxel-bridge/dbus/org.nuxel.Bridge.conf" in changed:
            r = run("systemctl reload dbus", timeout=30)
            evidence["checks"]["dbus_reload"] = {"rc": r.rc, "output": r.output}
            restart_needed = True
            time.sleep(1)
        if restart_needed:
            r = run("systemctl restart nuxel-bridge nuxel-http-bridge", timeout=40)
            evidence["checks"]["restart"] = {"rc": r.rc, "output": r.output}
            time.sleep(2)
        for cmd, key in (
            ("systemctl is-active nuxel-bridge nuxel-http-bridge", "bridge_units"),
            ("systemctl is-active NetworkManager nuxel-wayland nuxel-console", "preserved_units"),
            ("nuxel-gnss-diag.sh status --json", "gnss_diag"),
            ("python3 -c \"import dbus; i=dbus.Interface(dbus.SystemBus().get_object('org.nuxel.Bridge','/org/nuxel/Bridge'),'org.nuxel.Bridge'); print(i.LocationGetStatus('nuxel-settings'))\"", "location_status"),
            ("grep -c nuxelMaps /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js", "maps_marker"),
            ("grep -c DEFAULT_TILE_SOURCE /usr/share/nuxel/pwa/nuxel-common/maps-core.js", "core_marker"),
            ("grep -c 'Location &amp; Maps' /usr/share/nuxel/pwa/nuxel-apps/settings/index.html", "settings_marker"),
        ):
            r = run(cmd, timeout=35)
            evidence["checks"][key] = {"rc": r.rc, "output": r.output.strip()}
            print("# %s rc=%s\n%s" % (key, r.rc, r.output.strip()[:5000]))

        rollback = ["PWNAGE-27000 rollback (" + stamp + ")", "Backups: " + backup,
                    "  systemctl stop nuxel-bridge nuxel-http-bridge"]
        for e in evidence["files"]:
            if e["action"] != "installed":
                continue
            flat = e["target"].strip("/").replace("/", "_")
            rollback.append("  cp -a %s/%s %s" % (backup, flat, e["target"])
                            if e["before"] != "absent" else "  rm -f %s" % e["target"])
        rollback += ["  systemctl start nuxel-bridge nuxel-http-bridge",
                     "No kernel, boot, partition, modem or firmware file is involved."]
        rb = "\n".join(rollback) + "\n"
        rb_path = "/var/lib/nuxel/a72/ROLLBACK-27000-" + stamp + ".txt"
        nl.push_bytes(con, rb.encode(), rb_path, mode="0644")
        evidence["rollback_file"] = rb_path
        print(rb)
    finally:
        con.close()

    out = os.path.join(ROOT, "docs", "beta-finalization", "live", "evidence", "pwnage-27000-" + stamp)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "deploy.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)
    print("# evidence", out)


if __name__ == "__main__":
    main()
