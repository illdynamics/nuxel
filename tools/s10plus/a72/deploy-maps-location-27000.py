#!/usr/bin/env python3
"""Deploy the PWNAGE-27000 Location/Maps repair over the verified live console.

Only userspace files are touched.  Every target is backed up under
/var/lib/nuxel/a72/rollback-<stamp>/ with its before-sha256; the pushed file is
read back and its SHA-256 verified by nuxel_live.push_bytes.  No partition,
boot image, kernel, modem or firmware path is involved.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "beta", "live"))
import nuxel_live as nl  # noqa: E402

FILES = [
    ("pwa/nuxel-common/maps-core.js", "/usr/share/nuxel/pwa/nuxel-common/maps-core.js", "0644"),
    ("pwa/nuxel-common/bridge.js", "/usr/share/nuxel/pwa/nuxel-common/bridge.js", "0644"),
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
    ("tools/s10plus/a33/nuxel-gnss-diag.sh", "/usr/local/bin/nuxel-gnss-diag.sh", "0755"),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    stamp = time.strftime("%Y%m%dT%H%M%S%z")
    backup = "/var/lib/nuxel/a72/rollback-" + stamp
    con, node, notes = nl.open_console(timeout=30.0)
    con.open()
    evidence = {"stamp": stamp, "console": node, "notes": notes, "files": [], "checks": {}}
    try:
        print("# console", node.get("callout"), notes)
        r = con.run("mkdir -p " + shlex.quote(backup))
        assert r.ok and r.rc == 0, r.output
        evidence["backup_dir"] = backup

        for rel, remote, mode in FILES:
            local = os.path.join(ROOT, rel)
            before = con.run("sha256sum %s 2>/dev/null || echo absent" % shlex.quote(remote))
            before_text = before.output.strip().splitlines()[-1] if before.output.strip() else "absent"
            flat = remote.strip("/").replace("/", "_")
            if before.ok and before.rc == 0 and not before_text.startswith("absent"):
                cp = con.run("cp -a %s %s" % (shlex.quote(remote), shlex.quote(os.path.join(backup, flat))))
                assert cp.ok and cp.rc == 0, "backup failed for %s: %s" % (remote, cp.output)
            data = open(local, "rb").read()
            res = nl.push_bytes(con, data, remote, mode=mode)
            local_sha = sha256_file(local)
            if res["decoded_sha256"] != local_sha:
                raise SystemExit("readback mismatch for %s: %s != %s" %
                                 (remote, res["decoded_sha256"], local_sha))
            evidence["files"].append({
                "source": rel, "target": remote, "mode": mode,
                "bytes": res["bytes"], "sha256": local_sha, "before": before_text,
            })
            print("# pushed", rel, "->", remote, "sha256", local_sha[:16], "bytes", res["bytes"])

        # Restart only the bridge units whose code changed; the compositor,
        # NetworkManager, browser and serial console are untouched.
        r = con.run("systemctl restart nuxel-bridge nuxel-http-bridge", timeout=30)
        evidence["checks"]["restart"] = {"ok": r.ok, "rc": r.rc, "output": r.output}
        time.sleep(2)
        for cmd, key in (
            ("systemctl is-active nuxel-bridge nuxel-http-bridge", "bridge_units"),
            ("systemctl is-active NetworkManager nuxel-web nuxel-wayland nuxel-console", "preserved_units"),
            ("nuxel-gnss-diag.sh status", "gnss_diag"),
            ("curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/maps/js/maps.js", "maps_http"),
            ("curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/maps-core.js", "core_http"),
            ("curl -sS http://127.0.0.1:8000/pwa/nuxel-apps/maps/js/maps.js | grep -c 'nuxelMaps'", "maps_marker"),
        ):
            r = con.run(cmd, timeout=30)
            evidence["checks"][key] = {"ok": r.ok, "rc": r.rc, "output": r.output.strip()}
            print("# %s rc=%s\n%s" % (key, r.rc, r.output.strip()[:4000]))

        # Canonical provider status from the restarted bridge.
        py = ("python3 - <<'PY'\n"
              "import dbus,json\n"
              "b=dbus.SystemBus()\n"
              "i=dbus.Interface(b.get_object('org.nuxel.Bridge','/org/nuxel/Bridge'),'org.nuxel.Bridge')\n"
              "print(i.LocationGetStatus('nuxel-settings'))\n"
              "PY")
        r = con.run(py, timeout=30)
        evidence["checks"]["location_status"] = {"ok": r.ok, "rc": r.rc, "output": r.output.strip()}
        print("# location_status rc=%s\n%s" % (r.rc, r.output.strip()[:4000]))

        rollback = [
            "PWNAGE-27000 rollback (" + stamp + ")",
            "Backups: " + backup,
            "To restore:",
            "  systemctl stop nuxel-bridge nuxel-http-bridge",
        ]
        for item in evidence["files"]:
            flat = item["target"].strip("/").replace("/", "_")
            if item.get("before") and not str(item["before"]).startswith("absent"):
                rollback.append("  cp -a %s/%s %s" % (backup, flat, item["target"]))
            else:
                rollback.append("  rm -f %s" % item["target"])
        rollback += [
            "  systemctl start nuxel-bridge nuxel-http-bridge",
            "No kernel, boot, partition, modem or firmware file is part of this rollback.",
        ]
        rb_text = "\n".join(rollback) + "\n"
        rb_path = "/var/lib/nuxel/a72/ROLLBACK-27000-" + stamp + ".txt"
        nl.push_bytes(con, rb_text.encode(), rb_path, mode="0644")
        evidence["rollback_file"] = rb_path
        print(rb_text)
    finally:
        con.close()

    out_dir = os.path.join(ROOT, "docs", "beta-finalization", "live", "evidence", "pwnage-27000-" + stamp)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "deploy.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)
    print("# evidence", out_dir)


if __name__ == "__main__":
    main()
