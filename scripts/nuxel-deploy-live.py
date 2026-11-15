#!/usr/bin/env python3
"""Deploy the current Nuxel userspace release to a running S10+ over SSH.

This is the host half of the flash-free live-update path.  It builds the
hash-manifested payload with tools/s10plus/a43/package-live.py, verifies it with
verify-live.py, maps every repository source to its canonical phone target,
uploads one staging tarball and runs scripts/nuxel-live-install.py on the phone.

The install is userspace-only: PWA bytes, bridge/portal/notification sources,
firewall package/config, service units and audio assets.  No kernel, boot, DTB,
firmware, modem or partition path is ever written.

Usage:
  scripts/nuxel-deploy-live.py --host 192.168.178.167 --user nuxel \
      --key ~/.ssh/wicked_wqn_id_rsa --dry-run
  scripts/nuxel-deploy-live.py --host 192.168.178.167 --user nuxel \
      --key ~/.ssh/wicked_wqn_id_rsa --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_TOOL = ROOT / "tools/s10plus/a43/package-live.py"
VERIFY_TOOL = ROOT / "tools/s10plus/a43/verify-live.py"
INSTALLER = ROOT / "scripts/nuxel-live-install.py"
KNOWN_HOSTS = ROOT / "configs/nuxel/security/ssh/known_hosts"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def targets_for(source: str):
    """Return [(absolute target, mode)] for a payload source path."""
    if source == "services/nuxel-bridge/src/mic_provider.py":
        return [("/usr/lib/nuxel/nuxel-bridge/mic_provider.py", 0o644)]
    if source.startswith("pwa/"):
        out = [("/usr/share/nuxel/" + source, 0o644)]
        if source == "pwa/nuxel-common/app-registry.json":
            out.append(("/etc/nuxel/app-registry/app_registry.json", 0o644))
        if source == "pwa/nuxel-common/bridge-version.json":
            out.append(("/etc/nuxel/bridge-version.json", 0o644))
        return out
    if source.startswith("pwa/nuxel-apps/vault/"):
        return [("/usr/share/nuxel/pwa/" + source, 0o644),
                ("/usr/share/nuxel/" + source, 0o644)]
    if source.startswith("assets/"):
        return [("/usr/share/nuxel/" + source, 0o644)]
    if source == "services/nuxel-bridge/src/nfc_provider.py":
        return [("/usr/lib/nuxel/nuxel-bridge/nfc_provider.py", 0o644)]
    if source == "services/nuxel-nfc/nfc_provider.py":
        # The nfc-daemon tree's copy of the same client.  Both installed trees
        # must carry identical bytes (measured: a stale bridge copy rejected
        # the new app_id argument), so the payload ships both files.
        return [("/usr/lib/nuxel/nuxel-nfc/nfc_provider.py", 0o644)]
    if source == "services/nuxel-bridge/src/interface_state.py":
        return [("/usr/lib/nuxel/nuxel-bridge/interface_state.py", 0o644),
                ("/usr/lib/nuxel/nuxel-interface-state.d/interface_state.py", 0o644)]
    if source == "services/nuxel-s10/bin/nuxel-hardware-state":
        return [("/usr/lib/nuxel/nuxel-hardware-state", 0o755)]
    if source.startswith("services/nuxel-nfc/nuxel_nfc/"):
        rel = source[len("services/nuxel-nfc/nuxel_nfc/"):]
        return [("/usr/lib/nuxel/nuxel-nfc/nuxel_nfc/" + rel, 0o644)]
    if source == "services/nuxel-nfc/nfcd-preflight.py":
        return [("/usr/lib/nuxel/nuxel-nfc/nfcd-preflight.py", 0o755)]
    if source == "services/nuxel-nfc/nuxel-nfc":
        return [("/usr/bin/nuxel-nfc", 0o755)]
    if source == "services/nuxel-nfc/90-nuxel-nfc.rules":
        return [("/usr/lib/udev/rules.d/90-nuxel-nfc.rules", 0o644)]
    if source.startswith("services/nuxel-nfc/systemd/"):
        rel = source[len("services/nuxel-nfc/systemd/"):]
        return [("/usr/lib/systemd/system/" + rel, 0o644)]
    if source == "services/nuxel-s10/bin/nuxel-interface-state":
        return [("/usr/lib/nuxel/nuxel-interface-state", 0o755)]
    if source.startswith("services/nuxel-bridge/src/"):
        rel = source[len("services/nuxel-bridge/src/"):]
        return [("/usr/lib/nuxel/nuxel-bridge/" + rel, 0o644)]
    if source.startswith("services/nuxel-gnss/src/"):
        rel = source[len("services/nuxel-gnss/src/"):]
        return [("/usr/lib/nuxel/nuxel-gnss/" + rel, 0o755)]
    if source.startswith("services/nuxel-gnss/systemd/"):
        name = os.path.basename(source)
        return [("/etc/systemd/system/" + name, 0o644)]
    if source.startswith("configs/nuxel/permissions/") and source.endswith(".json"):
        # These are seed grants for first-party apps, not the live store: the
        # live store is the owner's authoritative data and is only ever written
        # by permD/Settings.  The bridge seeds an absent record from this tree.
        return [("/usr/share/nuxel/permissions/" + os.path.basename(source), 0o644)]
    if source == "shell/nuxel-shell/nuxel-permissions/nuxel-permd.py":
        # The unit's ExecStart is /usr/bin/nuxel-permd.py; install the same
        # bytes there (the lib copy stays for the tooling/imports).
        return [("/usr/lib/nuxel/nuxel-permissions/nuxel-permd.py", 0o755),
                ("/usr/bin/nuxel-permd.py", 0o755)]
    if source.startswith("docs/hardware/gps/") and (
            source.endswith(".md") or source.endswith(".sh")):
        mode = 0o755 if source.endswith(".sh") else 0o644
        return [("/usr/share/doc/nuxel/docs/hardware/gps/" + os.path.basename(source), mode)]
    if source == "shell/nuxel-shell/nuxel-permissions/systemd/nuxel-permd.service":
        return [("/etc/systemd/system/nuxel-permd.service", 0o644)]
    if source == "shell/nuxel-shell/nuxel-permissions/capabilities.json":
        return [("/usr/lib/nuxel/nuxel-permissions/capabilities.json", 0o644),
                ("/etc/nuxel/permissions/capabilities.json", 0o644)]
    if source == "services/nuxel-consent/nuxel_consentd.py":
        return [("/usr/lib/nuxel/nuxel-consent/nuxel_consentd.py", 0o755)]
    if source == "services/nuxel-consent/systemd/nuxel-consent-agent.service":
        return [("/etc/systemd/system/nuxel-consent-agent.service", 0o644)]
    if source == "services/nuxel-consent/dbus/org.nuxel.PhoshAgent.conf":
        # Session policy (own the name as uid 1000) and a system-bus policy so
        # the root HTTP bridge can reach the same agent.
        return [("/etc/dbus-1/session.d/org.nuxel.PhoshAgent.conf", 0o644),
                ("/etc/dbus-1/system.d/org.nuxel.PhoshAgent.conf", 0o644)]
    if source == "services/nuxel-notifications/dbus/org.nuxel.PhoshAgent.service":
        return [("/usr/share/dbus-1/services/org.nuxel.PhoshAgent.service", 0o644)]
    if source == "services/nuxel-notifications/dbus/org.nuxel.Notifications.service":
        return [("/usr/share/dbus-1/services/org.nuxel.Notifications.service", 0o644)]
    if source.startswith("services/nuxel-notifications/src/"):
        rel = source[len("services/nuxel-notifications/src/"):]
        return [("/usr/lib/nuxel/nuxel-notifications/" + rel, 0o644)]
    if source.startswith("services/nuxel-portal/src/"):
        rel = source[len("services/nuxel-portal/src/"):]
        return [("/usr/lib/nuxel/nuxel-portal/" + rel, 0o644)]
    if source == "services/nuxel-zsh/nuxel-banner.sh":
        return [("/etc/profile.d/nuxel-banner.sh", 0o755)]
    if source == "services/nuxel-zsh/nuxel.zsh":
        return [("/usr/lib/nuxel/zsh/nuxel.zsh", 0o644)]
    if source == "services/nuxel-remote-desktop/bin/nuxel-vnc-x11":
        return [("/usr/libexec/nuxel/nuxel-vnc-x11", 0o755)]
    if source == "services/nuxel-remote-desktop/bin/nuxel-vnc-wayland":
        return [("/usr/libexec/nuxel/nuxel-vnc-wayland", 0o755)]
    if source == "services/nuxel-remote-desktop/bin/nuxel-vnc-loopback":
        return [("/usr/libexec/nuxel/nuxel-vnc-loopback", 0o755)]
    if source == "services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl":
        return [("/usr/local/libexec/nuxel/nuxel-remote-desktop-ctl", 0o755)]
    if source == "services/nuxel-remote-desktop/bin/nuxel-xrdp-session":
        return [("/usr/local/bin/nuxel-xrdp-session", 0o755)]
    if source == "services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync":
        return [("/usr/libexec/nuxel/nuxel-orientation-remote-sync", 0o755)]
    if source.startswith("services/nuxel-remote-desktop/systemd/xrdp.service.d/"):
        return [("/etc/systemd/system/xrdp.service.d/" + os.path.basename(source), 0o644)]
    if source.startswith("services/nuxel-remote-desktop/config/"):
        name = os.path.basename(source)
        mapping = {
            "xrdp.ini": ("/etc/xrdp/xrdp.ini", 0o644),
            "sesman.ini": ("/etc/xrdp/sesman.ini", 0o644),
            "xorg.conf": ("/etc/xrdp/xorg-nuxel.conf", 0o644),
            "xrdp-sesman.pam": ("/etc/pam.d/xrdp-sesman", 0o644),
            "wayvnc.pam": ("/etc/pam.d/wayvnc", 0o644),
            "wayvnc.conf.example": ("/etc/nuxel/remote-desktop/vnc/wayvnc.conf.example", 0o644),
            "launcher.html": ("/usr/share/nuxel/remote-desktop/launcher.html", 0o644),
        }
        return [mapping[name]] if name in mapping else []
    if source == "services/nuxel-remote-desktop/systemd/nuxel-remote-vnc.service":
        return [("/etc/systemd/system/nuxel-remote-vnc.service", 0o644)]
    if source == "services/nuxel-remote-desktop/systemd/nuxel-remote-vnc-loopback.service":
        return [("/etc/systemd/system/nuxel-remote-vnc-loopback.service", 0o644)]
    if source.startswith("services/nuxel-s10/systemd/"):
        rel = source[len("services/nuxel-s10/systemd/"):]
        return [("/etc/systemd/system/" + rel, 0o644)]
    if source.startswith("services/nuxel-display/"):
        rel = source[len("services/nuxel-display/"):]
        name = os.path.basename(rel)
        if rel in ("bin/nuxel-displayd", "bin/nuxel-display-ctl"):
            return [("/usr/libexec/nuxel/" + name, 0o755)]
        if rel == "bin/nuxel-wl-fb-ext.c":
            return [("/usr/lib/nuxel/nuxel-display/nuxel-wl-fb-ext.c", 0o644)]
        if rel == "bin/build-nuxel-wl-fb-ext.sh":
            return [("/usr/lib/nuxel/nuxel-display/build-nuxel-wl-fb-ext.sh", 0o755)]
        if rel.startswith("lib/"):
            return [("/usr/lib/nuxel/nuxel-display/" + name, 0o644)]
        if rel.startswith("protocol/"):
            return [("/usr/lib/nuxel/nuxel-display/protocol/" + name, 0o644)]
        if rel.startswith("systemd/"):
            return [("/etc/systemd/system/" + name, 0o644)]
        if rel == "README.md":
            return [("/usr/share/doc/nuxel/HDMI-EXTERNAL-DISPLAY.md", 0o644)]
        return []
    if source == "services/nuxel-preload-cinema/nuxel-preload-cinema":
        return [("/usr/lib/nuxel/nuxel-preload-cinema", 0o755)]
    if source.startswith("services/nuxel-firewall/nuxel_firewall/"):
        rel = source[len("services/nuxel-firewall/nuxel_firewall/"):]
        return [("/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/" + rel, 0o644)]
    if source == "services/nuxel-firewall/bin/nuxel-firewall":
        return [("/usr/bin/nuxel-firewall", 0o755)]
    if source.startswith("services/nuxel-sound/"):
        name = os.path.basename(source)
        if source == "services/nuxel-sound/nuxel_audio_outputs.py":
            return [("/usr/lib/nuxel/nuxel_audio_outputs.py", 0o644)]
        if source == "services/nuxel-sound/nuxel-soundctl":
            return [("/usr/bin/nuxel-audio-ctl", 0o755)]
        if name.endswith(".py"):
            return [("/usr/libexec/nuxel/" + name[:-3], 0o755)]
        if name.endswith((".service", ".path", ".socket")):
            return [("/etc/systemd/system/" + name, 0o644)]
    if source.startswith("services/nuxel-clock/"):
        name = os.path.basename(source)
        if name.endswith(".py"):
            return [("/usr/libexec/nuxel/" + name[:-3], 0o755)]
        if name.endswith((".service", ".path", ".socket")):
            return [("/etc/systemd/system/" + name, 0o644)]
    if source.startswith(("services/nuxel-bridge/systemd/", "services/nuxel-notifications/systemd/",
                          "services/nuxel-session/systemd/", "services/nuxel-metrics/")):
        name = os.path.basename(source)
        if name.endswith((".service", ".path", ".socket")):
            return [("/etc/systemd/system/" + name, 0o644)]
    if source.startswith("services/nuxel-bridge/dbus/"):
        return [("/etc/dbus-1/system.d/" + os.path.basename(source), 0o644)]
    if source == "configs/nftables/systemd/nuxel-firewall.service":
        return [("/etc/systemd/system/nuxel-firewall.service", 0o644)]
    if source == "configs/nftables/nuxel-firewall-config.json":
        return [("/etc/nftables/nuxel-firewall-config.json", 0o644)]
    if source.startswith("configs/nftables/") and source.endswith(".nft"):
        return [("/etc/nftables/" + os.path.basename(source), 0o644)]
    if source == "tools/s10plus/a33/nuxel-firewall.sh":
        return [("/usr/bin/nuxel-firewall.sh", 0o755)]
    if source == "configs/nuxel/portals.conf":
        return [("/etc/xdg-desktop-portal/portals.conf", 0o644),
                ("/etc/nuxel/portals.conf", 0o644)]
    if source == "services/nuxel-portal-chooser/src/nuxel_portal_chooser.py":
        return [("/usr/libexec/nuxel/nuxel-portal-chooser", 0o755)]
    if source.startswith("services/nuxel-portal-chooser/dbus/"):
        return [("/usr/share/dbus-1/services/" + os.path.basename(source), 0o644)]
    if source.startswith("services/nuxel-portal-chooser/xdg-desktop-portal/"):
        return [("/usr/share/xdg-desktop-portal/portals/" + os.path.basename(source), 0o644)]
    if source == "services/nuxel-portal-chooser/bin/nuxel-portal-status":
        return [("/usr/bin/nuxel-portal-status", 0o755)]
    if source == "services/nuxel-file-handlers/src/nuxel_file_handlers.py":
        return [("/usr/lib/nuxel/nuxel_file_handlers.py", 0o644)]
    if source == "services/nuxel-file-handlers/bin/nuxel-file-handlers":
        return [("/usr/bin/nuxel-file-handlers", 0o755)]
    if source == "services/nuxel-file-handlers/bin/nuxel-open-file":
        return [("/usr/libexec/nuxel/nuxel-open-file", 0o755)]
    if source.startswith("shell/config/") and source.endswith(".desktop"):
        return [("/usr/share/applications/" + os.path.basename(source), 0o644)]
    if source == "services/nuxel-s10/bin/nuxel-flatpak-firefox":
        return [("/usr/lib/nuxel/nuxel-flatpak-firefox", 0o755)]
    if source == "services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh":
        return [("/usr/lib/nuxel/nuxel-abox-firmware-reload-boot.sh", 0o755)]
    if source == "services/nuxel-s10/bin/nuxel-audio-perms.sh":
        return [("/usr/lib/nuxel/nuxel-audio-perms.sh", 0o755)]
    if source == "services/nuxel-s10/bin/nuxel-usb-net-up.sh":
        return [("/usr/lib/nuxel/nuxel-usb-net-up.sh", 0o755)]
    if source == "services/nuxel-s10/bin/nuxel-audio-session.sh":
        return [("/usr/lib/nuxel/nuxel-audio-session.sh", 0o755)]
    if source == "services/nuxel-s10/bin/nuxel-flatpak-stremio":
        return [("/usr/lib/nuxel/nuxel-flatpak-stremio", 0o755)]
    if source == "services/nuxel-s10/bin/nuxel-flatpak-signal":
        return [("/usr/lib/nuxel/nuxel-flatpak-signal", 0o755)]
    if source == "services/nuxel-network/nuxel-hotspot.py":
        return [("/usr/libexec/nuxel/nuxel-hotspot", 0o755)]
    if source == "services/nuxel-network/nuxel-hotspot.service":
        return [("/etc/systemd/system/nuxel-hotspot.service", 0o644)]
    if source.startswith("configs/nuxel/sysctl/"):
        return [("/etc/sysctl.d/" + os.path.basename(source), 0o644)]
    if source == "services/nuxel-s10/bin/nuxel-flatpak-pulse-relay.py":
        return [("/usr/lib/nuxel/nuxel-flatpak-pulse-relay.py", 0o755)]
    if source == "services/nuxel-s10/systemd/nuxel-flatpak-pulse-relay.service":
        return [("/etc/systemd/system/nuxel-flatpak-pulse-relay.service", 0o644)]
    if source == "shell/nuxel-browser-native/nuxel_browser_native.py":
        return [("/usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py", 0o755)]
    if source == "tools/s10plus/a45/nuxel-session.sh":
        return [("/usr/lib/nuxel/nuxel-session.sh", 0o755)]
    if source == "tools/s10plus/a45/nuxel-security-state-rpc":
        return [("/usr/lib/nuxel/nuxel-security-state-rpc", 0o755)]
    if source == "tools/s10plus/a45/nuxel-shell-chrome.sh":
        return [("/usr/lib/nuxel/nuxel-shell-chrome.sh", 0o755)]
    if source.startswith("configs/nuxel/"):
        return [("/etc/nuxel/" + source[len("configs/nuxel/"):], 0o644)]
    if source.startswith("configs/dbus/"):
        return [("/etc/dbus-1/system.d/" + os.path.basename(source), 0o644)]
    # --- camera (PWNAGE-CAM) -------------------------------------------------
    # The native camera app, the private org.nuxel.Camera broker and the
    # FIMC-IS capture client/diagnostic. The portal's systemd unit is a user
    # unit (session bus/PipeWire), so it is installed under the user manager
    # location, never into the system manager.
    if source == "shell/nuxel-camera-native/nuxel_camera_native.py":
        return [("/usr/lib/nuxel/nuxel-camera-native/nuxel_camera_native.py", 0o755)]
    if source == "shell/nuxel-camera-native/org.nuxel.CameraNative.desktop":
        return [("/usr/share/applications/org.nuxel.CameraNative.desktop", 0o644)]
    if source == "shell/nuxel-camera-portal/nuxel_camera_portal.py":
        return [("/usr/libexec/nuxel/nuxel-camera-portal", 0o755)]
    if source == "shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service":
        return [("/usr/lib/systemd/user/nuxel-camera-portal.service", 0o644)]
    if source == "shell/nuxel-camera-portal/nuxel_camera_portal_impl.py":
        return [("/usr/libexec/nuxel/nuxel-camera-portal-impl", 0o755)]
    if source == "shell/nuxel-camera-portal/xdg-desktop-portal/nuxel-camera.portal":
        return [("/usr/share/xdg-desktop-portal/portals/nuxel-camera.portal", 0o644)]
    if source == "shell/nuxel-camera-portal/dbus/org.freedesktop.impl.portal.desktop.nuxel-camera.service":
        return [("/usr/share/dbus-1/services/org.freedesktop.impl.portal.desktop.nuxel-camera.service", 0o644)]
    if source == "shell/nuxel-camera-portal/systemd/nuxel-camera-portal-impl.service":
        return [("/usr/lib/systemd/user/nuxel-camera-portal-impl.service", 0o644)]
    if source == "tools/s10plus/fimc-capture/nuxel-fimc-capture":
        return [("/usr/libexec/nuxel/nuxel-fimc-capture", 0o755)]
    if source == "tools/s10plus/a33/nuxel-camera-diag.sh":
        return [("/usr/local/bin/nuxel-camera-diag.sh", 0o755)]
    if source == "tools/s10plus/a33/nuxel-sound-cue.py":
        return [("/usr/libexec/nuxel/nuxel-sound-cue", 0o755)]
    if source == "tools/s10plus/a33/doom-engines/nuxel-doom-engine":
        return [("/usr/lib/nuxel/nuxel-doom-engine", 0o755)]
    return []


def build_payload(out: Path) -> Path:
    print("BUILD payload -> %s" % out)
    subprocess.run([sys.executable, str(PAYLOAD_TOOL), str(out)], check=True)
    subprocess.run([sys.executable, str(VERIFY_TOOL), str(out)], check=True)
    return out


def load_payload(payload: Path):
    with tarfile.open(payload, "r:gz") as tf:
        manifest = json.load(tf.extractfile("manifest.json"))
    plan, missing = [], []
    for entry in manifest["files"]:
        source = entry["source"]
        targets = targets_for(source)
        if not targets:
            missing.append(source)
            continue
        for target, mode in targets:
            plan.append({
                "source": source, "target": target, "mode": mode,
                "sha256": entry["sha256"], "bytes": entry["bytes"],
            })
    if missing:
        raise SystemExit("no install mapping for: " + ", ".join(sorted(missing)))
    by_target = {}
    for item in plan:
        old = by_target.get(item["target"])
        if old and old["sha256"] != item["sha256"]:
            raise SystemExit("conflicting sources map to %s" % item["target"])
        by_target[item["target"]] = item
    return manifest, sorted(by_target.values(), key=lambda x: x["target"])


def _stage_payload_impl(payload: Path, manifest: dict, plan: list[dict]) -> Path:
    work = Path(tempfile.mkdtemp(prefix="nuxel-live-stage-"))
    (work / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    with tarfile.open(payload, "r:gz") as tf:
        sources = {e["source"] for e in plan}
        for source in sources:
            member = tf.getmember("files/" + source)
            data = tf.extractfile(member).read()
            dest = work / "files" / source
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if sha256_file(dest) != next(e["sha256"] for e in plan if e["source"] == source):
                raise SystemExit("staged hash mismatch: " + source)
    out = work / ("nuxel-%s-live-deploy.tar.gz" % manifest["version"].lstrip("v"))
    with tarfile.open(out, "w:gz") as tf:
        tf.add(work / "plan.json", arcname="plan.json")
        tf.add(work / "files", arcname="files")
    return out


def permission_store_gid(args, host: str) -> int | None:
    """Return nuxel-bridge's gid on the phone, if that account exists.

    First-party grant files are read by BOTH the bridge and permD.  permD runs
    as root, the bridge deliberately does not, so a root-only 0600 source file
    would deploy an invisible grant and reproduce the dead Location toggle.  The
    installer is root-only; this value only selects the group of files already
    inside that protected store.
    """
    cmd = subprocess.run(
        ssh_base(args, host) + ["getent group nuxel-bridge | cut -d: -f3 || true"],
        capture_output=True, text=True, timeout=20)
    value = (cmd.stdout or "").strip()
    return int(value) if value.isdigit() else None


def ensure_permd_state_acl(args, host: str) -> None:
    """Let the consent surface (uid nuxel) write permD's state sidecars.

    The consent agent runs as ``nuxel`` and calls nuxel-permd.py to record the
    owner's decision.  The grant file itself is nuxel-owned, but the
    review/enforce sidecars under state/ are root-owned on the handset, so a
    permission grant from the on-screen prompt used to fail with
    PermissionError while the same grant from Settings worked.  Grant only
    the state dirs (an ACL, no world write) and keep the files root-owned.
    """
    acl = (
        "setfacl -m u:nuxel:rwx /var/lib/nuxel/permissions/state "
        "/var/lib/nuxel/permissions/state/enforce 2>/dev/null || true; "
        "setfacl -d -m u:nuxel:rwx /var/lib/nuxel/permissions/state "
        "/var/lib/nuxel/permissions/state/enforce 2>/dev/null || true; "
        "setfacl -m u:nuxel:rw /var/lib/nuxel/permissions/state/audit.log "
        "2>/dev/null || true"
    )
    result = subprocess.run(ssh_base(args, host) + ["sudo -n sh -c " + shlex.quote(acl)],
                            capture_output=True, text=True)
    print("PERMD_STATE_ACL %s" % ("OK" if result.returncode == 0 else "WARN rc=%d" % result.returncode))


def stage(payload: Path, manifest: dict, plan: list[dict],
          permission_gid: int | None = None) -> Path:
    for item in plan:
        if item["target"].startswith("/usr/share/nuxel/permissions/"):
            item["gid"] = permission_gid
    work = Path(tempfile.mkdtemp(prefix="nuxel-live-stage-"))
    (work / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    with tarfile.open(payload, "r:gz") as tf:
        sources = {e["source"] for e in plan}
        for source in sources:
            member = tf.getmember("files/" + source)
            data = tf.extractfile(member).read()
            dest = work / "files" / source
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if sha256_file(dest) != next(e["sha256"] for e in plan if e["source"] == source):
                raise SystemExit("staged hash mismatch: " + source)
    out = work / ("nuxel-%s-live-deploy.tar.gz" % manifest["version"].lstrip("v"))
    with tarfile.open(out, "w:gz") as tf:
        tf.add(work / "plan.json", arcname="plan.json")
        tf.add(work / "files", arcname="files")
    return out


def ssh_base(args, host: str) -> list[str]:
    pin = Path(tempfile.mkdtemp(prefix="nuxel-pin-")) / "known_hosts"
    lines = [l for l in KNOWN_HOSTS.read_text().splitlines() if l.startswith("nuxel-s10plus ")]
    if not lines:
        raise SystemExit("no nuxel-s10plus pin in %s" % KNOWN_HOSTS)
    key = lines[0].split(None, 2)[2]
    pin.write_text("%s ssh-ed25519 %s\n" % (host, key))
    return [
        "ssh",
        "-i", str(Path(args.key).expanduser()),
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=%s" % pin,
        "-o", "ConnectTimeout=10",
        "%s@%s" % (args.user, host),
    ]


def remote(args, host: str, command: str, data: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(ssh_base(args, host) + [command], input=data, check=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--user", default="nuxel")
    ap.add_argument("--key", default="~/.ssh/wicked_wqn_id_rsa")
    ap.add_argument("--payload", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-restart", action="store_true")
    ap.add_argument("--restart", default="nuxel-bridge,nuxel-http-bridge,nuxel-soundd,nuxel-clockd")
    args = ap.parse_args(argv)

    if not args.payload:
        version = (ROOT / "VERSION").read_text().strip()
        payload = ROOT / "build/out/s10plus" / ("nuxel-%s-live-userspace.tar.gz" % version)
        payload.parent.mkdir(parents=True, exist_ok=True)
        build_payload(payload)
    else:
        payload = Path(args.payload).resolve()
        subprocess.run([sys.executable, str(VERIFY_TOOL), str(payload)], check=True)

    manifest, plan = load_payload(payload)
    print("PAYLOAD %s" % payload)
    print("VERSION %s  files=%d  targets=%d" % (manifest["version"], len(manifest["files"]), len(plan)))
    for item in plan:
        print("  %-64s -> %s (%04o)" % (item["source"], item["target"], item["mode"]))

    permission_gid = permission_store_gid(args, args.host)
    print("PERMISSION_STORE_GID %s" % (permission_gid if permission_gid is not None else "unresolved"))
    ensure_permd_state_acl(args, args.host)
    staged = stage(payload, manifest, plan, permission_gid)
    print("STAGED %s (%d bytes, sha256 %s)" % (staged, staged.stat().st_size, sha256_file(staged)))
    if not args.apply:
        print("DRY_RUN complete; pass --apply to deploy to %s@%s" % (args.user, args.host))
        return 0

    stamp = subprocess.run(["date", "-u", "+%Y%m%dT%H%M%SZ"], capture_output=True, text=True, check=True).stdout.strip()
    remote_path = "/tmp/nuxel-live-%s.tar.gz" % manifest["version"].lstrip("v")
    installer_path = "/tmp/nuxel-live-install.py"
    print("UPLOAD installer -> %s" % installer_path)
    remote(args, args.host, "cat > %s" % installer_path, INSTALLER.read_bytes())
    print("UPLOAD payload (%d bytes) -> %s" % (staged.stat().st_size, remote_path))
    remote(args, args.host, "cat > %s" % remote_path, staged.read_bytes())
    flags = " --no-restart" if args.no_restart else " --restart %s" % shlex.quote(args.restart)
    cmd = "sudo -n python3 %s --payload %s --stamp %s%s" % (
        installer_path, remote_path, shlex.quote(stamp), flags)
    print("RUN", cmd)
    result = subprocess.run(ssh_base(args, args.host) + [cmd])
    if result.returncode != 0:
        print("DEPLOY FAILED rc=%d" % result.returncode, file=sys.stderr)
        return result.returncode

    check = (
        'set -eu; '
        'grep -m1 "static get VERSION" /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js; '
        'grep -m1 "host_version" /usr/share/nuxel/pwa/nuxel-common/bridge-version.json; '
        'test -f /usr/share/nuxel/pwa/nuxel-home/js/qs-firewall.js; '
        'test -f /usr/share/nuxel/pwa/nuxel-apps/network-manager/index.html; '
        'test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js; '
        'test -f /usr/lib/nuxel/nuxel-bridge/network_manager.py; '
        'test -x /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl; '
        'test -f /etc/pam.d/wayvnc; '
        'grep -q "port=tcp://.*:3389" /etc/xrdp/xrdp.ini; '
        'test -f /usr/lib/nuxel/nuxel-firewall/nuxel_firewall/provider.py; '
        'test -x /usr/bin/nuxel-firewall; '
        'test -x /usr/libexec/nuxel/nuxel-display-ctl; '
        'test -f /usr/lib/nuxel/nuxel-display/nuxel-wl-fb-ext.c; '
        'test -f /etc/systemd/system/nuxel-displayd.service; '
        'grep -q "ExecStartPre=+/bin/sh" /etc/systemd/system/nuxel-bridge.service; '
        'grep -q "Location control" /usr/share/nuxel/pwa/nuxel-apps/settings/apps-permissions-settings.js; '
        'test -x /usr/bin/nuxel-permd.py; '
        'systemctl is-active nuxel-permd; '
        'test -f /usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py; '
        'test -f /etc/systemd/system/nuxel-gnss-lhd.service; '
        'systemctl is-active nuxel-bridge nuxel-http-bridge nuxel-web nuxel-soundd nuxel-clockd; '
        'echo DEVICE_VERIFY_OK'
    )
    remote(args, args.host, check)
    return 0


if __name__ == "__main__":
    sys.exit(main())
