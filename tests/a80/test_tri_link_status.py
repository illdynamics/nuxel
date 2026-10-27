"""Offline tests for the phone-side Tri-Link status reader (NUXEL-28000)."""
from __future__ import annotations

import base64
import fcntl
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/nuxel-bridge/src/tri_link_status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tri_link_status_under_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class Runner:
    def __init__(self, addresses="", default="", rc=0):
        self.addresses = addresses
        self.default = default
        self.rc = rc
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        out = self.addresses if "addr" in argv else self.default
        return subprocess.CompletedProcess(argv, self.rc, stdout=out, stderr="")


def wifi_fixture(tmp_path: Path):
    proc = tmp_path / "proc"
    write(proc / "net/tcp", "  sl local_address rem_address st\n"
          "   0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000\n")
    ssh = tmp_path / "etc/ssh"
    write(ssh / "sshd_config.d/60-nuxel-tri-link.conf",
          "PasswordAuthentication no\nKbdInteractiveAuthentication no\n"
          "PermitRootLogin prohibit-password\nAllowUsers nuxel@10.20.30.0/24\n")
    write(ssh / "ssh_host_ed25519_key.pub",
          "ssh-ed25519 " + base64.b64encode(b"test-host-key").decode() + " root@test\n")
    keys = tmp_path / "home/nuxel/.ssh"
    write(keys / "authorized_keys", "ssh-ed25519 AAAA nuxel@host\n")
    runner = Runner("2: wlan0    inet 10.20.30.16/24 brd 10.20.30.255 scope global wlan0\n",
                    "default via 10.20.30.1 dev wlan0 proto dhcp\n")
    return proc, ssh, keys, runner


def test_wifi_reports_real_dynamic_target_and_key_only_policy(tmp_path):
    mod = load_module()
    proc, ssh, keys, runner = wifi_fixture(tmp_path)
    st = mod.wifi_status(runner=runner, proc_root=proc, ssh_dir=ssh,
                         authorized_keys_dir=keys)
    assert st["status"] == "AVAILABLE"
    assert st["target"] == "nuxel@10.20.30.16:22"
    assert st["auth"] == "publickey only"
    assert "10.20.30.16" in st["host_command"]
    assert any(c["name"] == "sshd-listen" and c["status"] == "OK" for c in st["checks"])


def test_wifi_never_guesses_when_interface_or_daemon_is_absent(tmp_path):
    mod = load_module()
    proc, ssh, keys, _ = wifi_fixture(tmp_path)
    # No IPv4 address: target must be empty, never an invented address.
    st = mod.wifi_status(runner=Runner("", ""), proc_root=proc, ssh_dir=ssh,
                         authorized_keys_dir=keys)
    assert st["status"] == "UNAVAILABLE"
    assert st["target"] == "Wi-Fi"
    # Interface but no listening sshd.
    write(proc / "net/tcp", "  sl local_address rem_address st\n")
    runner = Runner("2: wlan0    inet 10.20.30.16/24 brd 10.20.30.255 scope global wlan0\n",
                    "default via 10.20.30.1 dev wlan0\n")
    st = mod.wifi_status(runner=runner, proc_root=proc, ssh_dir=ssh,
                         authorized_keys_dir=keys)
    assert st["status"] == "UNAVAILABLE"
    assert "not listening" in st["detail"]


def test_wifi_refuses_to_claim_secure_when_password_auth_is_enabled(tmp_path):
    mod = load_module()
    proc, ssh, keys, runner = wifi_fixture(tmp_path)
    write(ssh / "sshd_config.d/61-unsafe.conf", "PasswordAuthentication yes\n")
    st = mod.wifi_status(runner=runner, proc_root=proc, ssh_dir=ssh,
                         authorized_keys_dir=keys)
    assert st["status"] == "UNAVAILABLE"
    assert "not key-only" in st["detail"]
    auth = next(c for c in st["checks"] if c["name"] == "authentication")
    assert auth["status"] == "FAIL"


def test_serial_requires_acm_tty_and_reports_lock_owner(tmp_path):
    mod = load_module()
    gadget = tmp_path / "sys/kernel/config/usb_gadget"
    (gadget / "nuxel/functions/acm.usb0").mkdir(parents=True)
    tty = tmp_path / "sys/class/tty"
    (tty / "ttyGS0").mkdir(parents=True)
    udc = tmp_path / "sys/class/udc"
    write(udc / "dwc3/state", "configured\n")
    lock = write(tmp_path / "run/nuxel-console.lock", "")
    st = mod.serial_status(gadget_root=gadget, tty_root=tty, udc_root=udc, lock_path=lock)
    assert st["status"] == "AVAILABLE"
    assert st["auth"] == "none (exclusive host console)"
    assert any(c["name"] == "console-lock" and c["status"] == "FREE" for c in st["checks"])

    fd = lock.open("r+")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        st = mod.serial_status(gadget_root=gadget, tty_root=tty, udc_root=udc, lock_path=lock)
        assert st["status"] == "AVAILABLE"
        assert "single-owner lock" in st["detail"]
        assert any(c["name"] == "console-lock" and c["status"] == "HELD" for c in st["checks"])
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()


def test_serial_unavailable_without_gadget_function(tmp_path):
    mod = load_module()
    st = mod.serial_status(gadget_root=tmp_path / "none", tty_root=tmp_path / "tty",
                           udc_root=tmp_path / "udc", lock_path=tmp_path / "lock")
    assert st["status"] == "UNAVAILABLE"
    assert "not present" in st["detail"]


def test_usb_ssh_blocks_the_known_panicking_kernel(tmp_path):
    mod = load_module()
    cfg = ("CONFIG_USB_CONFIGFS=y\nCONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n")
    net = tmp_path / "sys/class/net"
    (net / "usb0").mkdir(parents=True)
    proc = tmp_path / "proc"
    write(proc / "net/tcp", "0: 00000000:0016 00000000:0000 0A 00000000:00000000\n")
    st = mod.usb_status(release="4.14.253", gadget_root=tmp_path / "gadget",
                        net_root=net, proc_root=proc, kernel_config=cfg)
    assert st["status"] == "BLOCKED_KERNEL_PANIC"
    assert "panicked" in st["detail"]
    assert "n26000-usb-ncm-panic" in st["detail"]


def test_usb_ssh_never_claims_ready_without_interface_or_ssh(tmp_path):
    mod = load_module()
    cfg = ("CONFIG_USB_CONFIGFS=y\nCONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n")
    proc = tmp_path / "proc"
    write(proc / "net/tcp", "")
    st = mod.usb_status(release="4.14.254", gadget_root=tmp_path / "gadget",
                        net_root=tmp_path / "net", proc_root=proc, kernel_config=cfg)
    assert st["status"] == "SUPPORTED_NOT_ENABLED"
    net = tmp_path / "net"
    (net / "usb0").mkdir(parents=True)
    st = mod.usb_status(release="4.14.254", gadget_root=tmp_path / "gadget",
                        net_root=net, proc_root=proc, kernel_config=cfg)
    assert st["status"] == "UNAVAILABLE"
    assert "not listening" in st["detail"]
    write(proc / "net/tcp", "0: 00000000:0016 00000000:0000 0A 00000000:00000000\n")
    st = mod.usb_status(release="4.14.254", gadget_root=tmp_path / "gadget",
                        net_root=net, proc_root=proc, kernel_config=cfg)
    assert st["status"] == "AVAILABLE"


def test_get_status_returns_all_three_and_no_secret_material(tmp_path):
    mod = load_module()
    proc, ssh, keys, runner = wifi_fixture(tmp_path)
    gadget = tmp_path / "sys/kernel/config/usb_gadget"
    (gadget / "nuxel/functions/acm.usb0").mkdir(parents=True)
    tty = tmp_path / "sys/class/tty"
    (tty / "ttyGS0").mkdir(parents=True)
    udc = tmp_path / "sys/class/udc"
    write(udc / "dwc3/state", "configured\n")
    net = tmp_path / "sys/class/net"
    (net / "usb0").mkdir(parents=True)
    doc = mod.get_status(release="4.14.254", runner=runner, proc_root=proc,
                         gadget_root=gadget, tty_root=tty, udc_root=udc,
                         net_root=net, ssh_dir=ssh, authorized_keys_dir=keys,
                         lock_path=tmp_path / "lock",
                         kernel_config="CONFIG_USB_CONFIGFS=y\nCONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n")
    assert set(doc["transports"]) == {"serial", "wifi", "usb"}
    blob = json.dumps(doc)
    assert "PRIVATE KEY" not in blob
    assert "AAAA nuxel@host" not in blob
    assert "authorized-keys" in blob


def test_hidden_home_authorized_keys_is_unknown_not_absent(tmp_path):
    """nuxel-http-bridge has ProtectHome=yes; that must not fake a missing key."""
    mod = load_module()
    proc, ssh, _keys, runner = wifi_fixture(tmp_path)
    st = mod.wifi_status(runner=runner, proc_root=proc, ssh_dir=ssh,
                         authorized_keys_dir=tmp_path / "inaccessible-home/.ssh")
    key = next(c for c in st["checks"] if c["name"] == "authorized-keys")
    assert key["status"] == "UNKNOWN"
    assert "host auth is authoritative" in key["detail"]
    assert st["status"] == "AVAILABLE"


def test_native_ip_reader_does_not_need_af_netlink():
    """The bridge unit restricts AF_NETLINK; if_nameindex() would fail there."""
    src = MODULE.read_text()
    assert "names = socket.if_nameindex()" not in src
    assert "/sys/class/net" in src and "SIOCGIFADDR" in src
