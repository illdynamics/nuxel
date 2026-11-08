"""PWNAGE-47000 GUI Tri-Link offline contract tests.

These prove registry/UI/Bridge bookkeeping and the security guards.  They do not
claim a physical RDP/VNC connection; the live acceptance evidence lives under
docs/beta-finalization/live/evidence/pwnage-47000/.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "services/nuxel-bridge/src"
REGISTRY = ROOT / "pwa/nuxel-common/app-registry.json"
APPS_JS = ROOT / "pwa/nuxel-home/js/apps.js"
NATIVE = ROOT / "shell/nuxel-home-native/nuxel_home/app_registry.json"

NEW = {
    "org.nuxel.RemoteDesktopXRDP": ("remote-xrdp", "xrdp"),
    "org.nuxel.RemoteDesktopVNC": ("remote-vnc", "vnc"),
    "org.nuxel.ScrcpyMirror": ("remote-scrcpy", "scrcpy"),
}
CONSOLES = ("org.nuxel.LiveConsole", "org.nuxel.USBSSHConsole", "org.nuxel.WiFiSSHConsole")


def load_remote():
    sys.path.insert(0, str(SRC))
    spec = importlib.util.spec_from_file_location("remote_desktop_under_test", SRC / "remote_desktop.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_registry_has_new_apps_once_and_preserves_console_ids():
    doc = json.loads(REGISTRY.read_text())
    ids = [a["id"] for a in doc["apps"]]
    assert len(ids) == len(set(ids))
    assert doc["registry_version"] == 19
    for aid in NEW:
        assert ids.count(aid) == 1
    for aid in CONSOLES:
        assert ids.count(aid) == 1
    for aid, (dir_name, service) in NEW.items():
        app = next(a for a in doc["apps"] if a["id"] == aid)
        assert app["entry"] == "pwa/nuxel-apps/%s/index.html" % dir_name
        assert app["manifest"] == "pwa/nuxel-apps/%s/manifest.json" % dir_name
        assert app["remote_service"] == service
        assert app["default_transport"] in ("wlan", "android-adb-usb")
        assert (ROOT / app["entry"]).is_file()
        assert (ROOT / app["manifest"]).is_file()


def test_three_documents_are_real_and_manifest_contract_is_not_mocked():
    for aid, (dir_name, service) in NEW.items():
        root = ROOT / "pwa/nuxel-apps" / dir_name
        html = (root / "index.html").read_text()
        manifest = json.loads((root / "manifest.json").read_text())
        appjson = json.loads((root / "app.json").read_text())
        assert 'name="nuxel-app-id" content="%s"' % aid in html
        assert 'src="js/%s.js' % dir_name in html
        assert manifest["start_url"] == "/pwa/nuxel-apps/%s/index.html" % dir_name
        assert manifest["nuxel"]["bridge_version"] == "1"
        assert manifest["nuxel"]["app_type"] == "remote-desktop"
        assert manifest["nuxel"]["off_by_default"] is True
        assert appjson["id"] == aid
        assert appjson["remote_service"] == service


def test_launcher_and_native_consumer_have_the_new_entries_once():
    text = APPS_JS.read_text()
    assert "const NUXEL_REGISTRY_VERSION = 19;" in text
    for aid in NEW:
        assert text.count("id: '%s'" % aid) == 1
    native = json.loads(NATIVE.read_text())
    nids = [a["id"] for a in native["apps"]]
    for aid in NEW:
        assert nids.count(aid) == 1
    assert "org.nuxel.WiFiSSHConsole" in nids


def test_bridge_js_has_no_mock_success_for_remote_desktop():
    text = (ROOT / "pwa/nuxel-common/bridge.js").read_text()
    assert "system.remote-desktop" in text
    assert "remote-desktop status/control was not performed" in text


def test_usb_is_blocked_without_configfs_mutation(monkeypatch):
    mod = load_remote()
    cfg = ("CONFIG_USB_CONFIGFS=y\nCONFIG_USB_DWC3=y\nCONFIG_USB_F_NCM=y\n"
           "CONFIG_USB_CONFIGFS_NCM=y\nCONFIG_USB_F_RNDIS=y\nCONFIG_USB_CONFIGFS_RNDIS=y\n")
    monkeypatch.setattr(mod, "_kernel_config_text", lambda release="": cfg)
    out = mod.usb_network_status("4.14.253-gf7194c1d15ed-dirty")
    assert out["available"] is False
    assert out["status"] == "BLOCKED_KERNEL_PANIC"
    assert out["mutated"] is False
    assert out["modes"]["ncm"]["status"] == "BLOCKED_KNOWN_PANIC"
    assert out["modes"]["rndis"]["status"] == "NEEDS_VALIDATION"
    assert "ncm_free_inst" in out["reason"]

def test_network_address_is_discovered_not_hardcoded(monkeypatch):
    mod = load_remote()
    monkeypatch.setattr(mod, "_ipv4_from_ip_tool", lambda: [
        {"interface": "wlan0", "address": "192.168.44.77", "prefix": "24"},
        {"interface": "rmnet0", "address": "10.1.2.3", "prefix": "30"},
    ])
    net = mod.network_state()
    assert net["address"] == "192.168.44.77"
    assert net["interface"] == "wlan0"
    assert net["trusted_lan"] is True
    assert "10.20.30.16" not in json.dumps(net)


def test_invalid_service_and_transport_are_refused():
    mod = load_remote()
    assert mod.handle("status", {"service": "bogus"})["error_code"] == "INVALID_SERVICE"
    assert mod.handle("set-transport", {"service": "vnc", "transport": "rmnet"})["error_code"] == "INVALID_TRANSPORT"
    assert mod.handle("set-transport", {"service": "vnc", "transport": "usb"})["error_code"] in ("BLOCKED_KERNEL_PANIC", "BLOCKED_KERNEL")


def test_start_usb_is_refused_before_any_helper_call(monkeypatch):
    mod = load_remote()
    called = []
    monkeypatch.setattr(mod, "_helper", lambda *a, **k: called.append(a) or {"success": True})
    out = mod.handle("start", {"service": "vnc", "transport": "usb"})
    assert out["success"] is False
    assert out["error_code"] in ("BLOCKED_KERNEL_PANIC", "BLOCKED_KERNEL")
    assert called == []


def test_scrcpy_native_nuxel_is_honest(monkeypatch):
    mod = load_remote()
    monkeypatch.setattr(mod, "_adb_targets", lambda: {"available": True, "targets": [], "adb_version": "adb 1"})
    monkeypatch.setattr(mod, "_scrcpy_version", lambda: None)
    monkeypatch.setattr(mod.os.path, "isdir", lambda p: p == "/usr/lib/nuxel")
    monkeypatch.setattr(mod.os.path, "exists", lambda p: False)
    st = mod._scrcpy_status()
    assert st["state"] == "NOT_APPLICABLE_NATIVE_NUXEL"
    assert st["listener_verified"] is False
    assert st["authenticated_clients"] == 0
    assert "Android ADB" in st["reason"]


def test_direct_listener_and_local_account_contract():
    """Direct LAN only: standard RDP 3389 and VNC 5900, no SSH tunnel."""
    ctl = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl").read_text()
    wrapper = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-vnc-x11").read_text()
    rd = (ROOT / "services/nuxel-bridge/src/remote_desktop.py").read_text()
    xrdp = (ROOT / "services/nuxel-remote-desktop/config/xrdp.ini").read_text()
    assert 'PORTS = {"vnc": 5900, "xrdp": 3389}' in ctl
    assert "vncpasswd" in ctl and "security_types=VncAuth" in ctl
    assert "SecurityTypes VncAuth" in wrapper and "-rfbport" in wrapper
    assert "enable_auth=false" not in ctl
    assert "port=tcp://127.0.0.1:3389" in xrdp
    assert 'BIND_ADDRESS = "trusted-lan-ipv4"' in rd
    assert '"username": "nuxel"' in rd
    assert '"requires_ssh_tunnel": False' in rd
    assert '"ssh_tunnel_command": None' in rd
    assert '"vnc_unauthenticated": False' in rd and '"vnc_authenticated": True' in rd


def test_status_never_contains_secret_fields(monkeypatch):
    mod = load_remote()
    monkeypatch.setattr(mod, "_vnc_status", lambda: {"state": "OFF", "port": 5900, "listener_verified": False})
    monkeypatch.setattr(mod, "_xrdp_status", lambda: {"state": "OFF", "port": 3389, "listener_verified": False})
    monkeypatch.setattr(mod, "_scrcpy_status", lambda: {"state": "NO_ANDROID_TARGET", "listener_verified": False})
    doc = mod.get_status()
    text = json.dumps(doc).lower()
    for forbidden in ("password", "private_key", "authorized_keys", "secret"):
        assert forbidden not in text


def test_connection_info_is_direct_and_secret_free(monkeypatch):
    mod = load_remote()
    monkeypatch.setattr(mod, "network_state", lambda: {"address": "192.168.44.77", "interface": "wlan0", "trusted_lan": True})
    monkeypatch.setattr(mod, "_xrdp_fingerprint", lambda: "AA:BB")
    info = mod.connection_info("xrdp")
    assert info["bind_address"] == "192.168.44.77"
    assert info["port"] == 3389
    assert info["direct_lan"] is True
    assert info["password_included"] is False
    assert info["ssh_tunnel_command"] is None
    assert info["jump_url"] == "rdp://192.168.44.77:3389"
    assert info["username"] == "nuxel"
    assert "password" not in json.dumps({k: v for k, v in info.items() if k != "password_included"}).lower()


def test_helper_accepts_only_fixed_service_names():
    text = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl").read_text()
    assert 'SERVICES = ("vnc", "xrdp", "scrcpy")' in text
    assert "shell=True" not in text
    assert "os.system" not in text


def test_image_disables_selinux_policy_loading_after_package_install():
    """PWNAGE-47000 boot regression: remote-desktop packages pull in an SELinux
    policy.  PID 1 and the initramfs console run in kernel_t, so enforcing that
    policy makes every helper exec fail and the phone loops on the boot
    animation.  The image builder must pin SELinux=disabled after dnf install."""
    text = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "PWNAGE-47000 BOOT SAFETY" in text
    assert "SELINUX=permissive" in text
    assert text.index("SELINUX=permissive") > text.index("dnf -y --installroot")
    assert "selinux-policy-targeted" in text
    assert ".autorelabel" in text


def test_image_puts_unprivileged_network_users_in_inet_group():
    """CONFIG_ANDROID_PARANOID_NETWORK=y: AF_INET socket() requires gid 3003.
    Both the login user (sshd local forwards) and the RDP account need it."""
    text = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "CONFIG_ANDROID_PARANOID_NETWORK=y" in text
    assert "groupadd -f -g 3003 inet" in text
    assert "usermod -aG inet nuxel" in text
    assert "usermod -aG inet nuxel-remote" not in text


def test_ctl_stop_is_bounded_and_never_targets_the_physical_session():
    text = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl").read_text()
    assert "TimeoutExpired" in text
    assert "timed out after" in text
    assert "xorg-nuxel.conf" in text
    assert "nuxel-xrdp-session" in text
    # The physical compositor and framebuffer bridge are never in the kill list.
    assert "xorg-nuxel.conf" in text
    assert "pkill phoc" not in text and "killall phoc" not in text
    assert "pkill nuxel-wl-fb" not in text and "killall nuxel-wl-fb" not in text


def test_ctl_exposes_read_only_status_for_the_quickstart():
    text = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl").read_text()
    assert 'if action == "status":' in text
    assert "NOT_APPLICABLE_NATIVE_NUXEL" in text
    assert "separate-x11-session" in text


def test_image_generates_vnc_tls_material_and_never_ships_a_password():
    text = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "tls_cert.pem" in text and "tls_key.pem" in text and "rsa_key.pem" in text
    assert "wayvnc.pam" in text and '"$STAGE/etc/pam.d/wayvnc"' in text
    assert "openssl rand -hex 14" not in text
    assert "/etc/nuxel/remote-desktop/xrdp/credential" not in text
    assert "nuxel-remote:%s" not in text


def test_ctl_clears_failed_unit_state_after_forced_stop():
    text = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl").read_text()
    assert '"systemctl", "reset-failed", "xrdp.service", "xrdp-sesman.service"' in text
    assert '"systemctl", "reset-failed", VNC_SERVICE' in text


def test_rdp_pam_is_locked_to_the_local_nuxel_account():
    """The owner wants the RDP identity to be the same local account as
    SSH/VNC.  PAM must reject the retired nuxel-remote account before the
    session launcher is ever reached."""
    pam = (ROOT / "services/nuxel-remote-desktop/config/xrdp-sesman.pam").read_text()
    session = (ROOT / "services/nuxel-remote-desktop/bin/nuxel-xrdp-session").read_text()
    builder = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "auth       required     pam_succeed_if.so user = nuxel" in pam
    assert "account    required     pam_succeed_if.so user = nuxel" in pam
    assert 'if [ "$(id -u)" -ne 1000 ] || [ "$(id -un)" != "nuxel" ]; then' in session
    assert "xrdp-sesman.pam" in builder
    assert '"$STAGE/etc/pam.d/xrdp-sesman"' in builder

def test_vnc_status_derives_effective_auth_and_never_claims_secure_when_off(tmp_path, monkeypatch):
    mod = load_remote()
    conf = tmp_path / "xvnc.conf"
    passwd = tmp_path / "vnc.passwd"
    passwd.write_bytes(b"12345678")
    monkeypatch.setattr(mod, "VNC_CONFIG", conf)
    monkeypatch.setattr(mod, "_vnc_version", lambda: "TigerVNC Xvnc 1.16.2")
    monkeypatch.setattr(mod, "_systemctl_active", lambda unit: True)
    monkeypatch.setattr(mod, "_listener_addresses", lambda port: ["192.168.178.167"])
    monkeypatch.setattr(mod, "_vnc_clients", lambda: {"count": 0, "available": True})
    monkeypatch.setattr(mod, "_read", lambda path: "")
    conf.write_text("address=192.168.178.167\nport=5900\nsecurity_types=None\n")
    st = mod._vnc_status()
    assert st["state"] == "ERROR"
    assert st["authentication"] == "UNAUTHENTICATED"
    assert st["security_verified"] is False
    conf.write_text("address=192.168.178.167\nport=5900\n"
                    "password_file=%s\nsecurity_types=VncAuth\n" % passwd)
    st = mod._vnc_status()
    assert st["state"] == "WAITING_FOR_CLIENT"
    assert st["encrypted"] is False and st["security_verified"] is True
    assert st["authentication_mode"] == "VNC password"


def test_usb_modes_are_distinct_and_never_ready(monkeypatch):
    mod = load_remote()
    cfg = ("CONFIG_USB_CONFIGFS=y\nCONFIG_USB_DWC3=y\nCONFIG_USB_F_NCM=y\n"
           "CONFIG_USB_CONFIGFS_NCM=y\nCONFIG_USB_F_RNDIS=y\nCONFIG_USB_CONFIGFS_RNDIS=y\n")
    monkeypatch.setattr(mod, "_kernel_config_text", lambda release="": cfg)
    out = mod.usb_network_status("4.14.253-gf7194c1d15ed-dirty")
    assert out["available"] is False and out["mutated"] is False
    assert out["kernel_base_release"] == "4.14.253"
    assert out["modes"]["ncm"]["status"] == "BLOCKED_KNOWN_PANIC"
    assert out["modes"]["rndis"]["status"] == "NEEDS_VALIDATION"
    assert out["modes"]["ecm"]["status"] == "BLOCKED_KERNEL"
