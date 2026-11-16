"""Host helper tests (PWNAGE-USBNET): exact interface association + probe target.

Measured on this Apple Silicon Mac (see PWNAGE-USBNET-TEST-RESULTS.md):

  * `ioreg -a` WITHOUT `-l` emits short nodes with OID references only - no
    idVendor and no BSD Name.  The helper must use `ioreg -a -l`.
  * The BSD interface is a CHILD of the driver service
    (AppleUSBDeviceNCM -> AppleUSBDeviceNCMData -> IOEthernetInterface {BSD
    Name}), not a parent of it.

These tests pin the corrected contract with synthetic IORegistry fixtures:
an unrelated Ethernet port is never selected, an ambiguous/decoy device is not
selected, --interface is verified, and diagnostics probe the PHONE address.
"""
from __future__ import annotations

import json
import os
import plistlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/s10plus-debug-pack/nuxel-usb-net-host.sh"


def run(args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(["bash", str(HELPER), *args], capture_output=True,
                          text=True, env=e, timeout=180)


def node(**kw):
    return kw


def fixture(tmp_path, *, vid=0x18D1, pid=0x4EE7, bsd="en7", decoy=True):
    dev = node(IOClass="AppleUSBDeviceNCM", idVendor=vid, idProduct=pid,
               **{"USB Product Name": "Nuxel S10+ Live Console",
                  "IORegistryEntryChildren": [
                      node(IOClass="AppleUSBDeviceNCMData",
                           IORegistryEntryChildren=[
                               node(IOClass="IOEthernetInterface", **{"BSD Name": bsd})])]})
    roots = [dev]
    if decoy:
        roots.append(node(IOClass="IOUSBHostDevice", idVendor=0x05AC, idProduct=0x1234,
                          IORegistryEntryChildren=[
                              node(IOClass="AppleUSBDeviceNCMData",
                                   IORegistryEntryChildren=[
                                       node(IOClass="IOEthernetInterface",
                                            **{"BSD Name": "en9"})])]))
    p = tmp_path / "ioreg.plist"
    with open(p, "wb") as fh:
        plistlib.dump(roots, fh)
    return p


def test_no_device_is_refused_without_unrelated_port():
    r = run(["--status", "--json"], {"NUXEL_USB_VID": "ffff", "NUXEL_USB_PID": "eeee"})
    assert r.returncode == 3, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["interface"] == "" and d["status"] == "NO_USB_NETWORK_INTERFACE"
    assert d["device_present"] is False


def test_macos_discovers_child_bsd_under_exact_device(tmp_path):
    p = fixture(tmp_path)
    r = run(["--discover", "--json"], {"NUXEL_IOREG_PLIST": str(p)})
    d = json.loads(r.stdout)
    assert d["status"] == "INTERFACE_FOUND", d
    assert d["interface"] == "en7"          # not the decoy en9
    assert d["device_present"] is True


def test_macos_wrong_vid_does_not_select(tmp_path):
    p = fixture(tmp_path)
    r = run(["--discover", "--json"],
            {"NUXEL_IOREG_PLIST": str(p), "NUXEL_USB_PID": "eeee"})
    d = json.loads(r.stdout)
    assert d["status"] == "NO_USB_NETWORK_INTERFACE"
    assert d["interface"] == ""


def test_explicit_interface_must_prove_ancestry(tmp_path):
    p = fixture(tmp_path)
    # en4 is not in the fixture at all -> refused (the helper prints a refusal).
    r = run(["--discover", "--interface", "en4", "--json"],
            {"NUXEL_IOREG_PLIST": str(p)})
    assert "refusing --interface en4" in r.stderr
    assert json.loads(r.stdout)["interface"] == ""


def test_physical_phone_default_is_dot1_not_dot82(tmp_path):
    p = fixture(tmp_path)
    d = json.loads(run(["--discover", "--json"], {"NUXEL_IOREG_PLIST": str(p)}).stdout)
    assert d["phone_address"] == "10.15.19.1"
    assert d["host_address"] == "10.15.19.2/24"


def test_explicit_phone_override_is_honoured(tmp_path):
    p = fixture(tmp_path)
    d = json.loads(run(["--discover", "--json", "--phone", "10.15.19.99"],
                       {"NUXEL_IOREG_PLIST": str(p)}).stdout)
    assert d["phone_address"] == "10.15.19.99"


def test_diagnose_probes_phone_not_host():
    src = HELPER.read_text()
    assert 'ping -c1 -W 1000 "$(phone_addr)"' in src
    assert 'ping -c1 -W 1000 "${ADDR%%/*}"' not in src
    assert 'ssh -o BatchMode=yes' in src and "$(phone_addr)" in src
    assert "--interface" in src and "iface_belongs_to_device_macos" in src
    # Must use the verbose IORegistry form that actually carries idVendor.
    assert '"ioreg", "-a", "-l", "-p", "IOService"' in src


def test_apply_does_not_rediscover_over_explicit_interface():
    src = HELPER.read_text()
    apply_block = src[src.index("  apply)"):src.index("  remove)")]
    assert "discover_macos" not in apply_block
    assert "discover_linux" not in apply_block


def test_tether_test_never_changes_default_route():
    src = HELPER.read_text()
    assert "--tether-test" in src
    body = src[src.index("tether_test() {"):src.index("case \"$ACTION\" in")]
    # default route must be untouched: only a scoped /32 host route is added
    # and it is removed again.
    assert "route -n delete -host" in body or "route del" in body
    assert "add default" not in body and "add -net default" not in body
