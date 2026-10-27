#!/usr/bin/env python3
"""Offline tests for NUXEL-26000 Tri-Link (no phone, no root, no real SSH).

Run:
  python3 -m pytest tools/beta/live/tests/test_tri_link.py -q

The rollback test uses the repository's real fake-console PTY and the real deploy
transaction code.  It is an integration test of the host tooling, not physical
S10+ evidence.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LIVE))
from harness import FakePhone  # noqa: E402
import nuxel_tri_link as tl  # noqa: E402

REPO = tl.REPO_ROOT
KEYTYPE = "ssh-ed25519"
KEY_A = "AAAAC3NzaC1lZDI1NTE5AAAAIPJ7p1+txS0hBaDInGwCtNBOE/KLmEjVxFkWhQKt/x4e"
KEY_B = "AAAAC3NzaC1lZDI1NTE5AAAAICqAB3sxR2Q+V3jf8r/6ZOtu1x9GzveBZnZBWOkELicn"


def cp(argv, rc=0, stdout="", stderr="", **_):
    return subprocess.CompletedProcess(argv, rc, stdout, stderr)


def target(tmp: str, *, key_text: str | None = None, known: str | None = None,
           transport="wlan", host="10.20.30.16") -> tl.SshTarget:
    d = Path(tmp)
    key = d / "id_ed25519"
    key.write_text(key_text or "-----BEGIN OPENSSH PRIVATE KEY-----\nx\n")
    key.chmod(0o600)
    kh = d / "known_hosts"
    kh.write_text(known if known is not None
                  else "nuxel-s10plus %s %s\n" % (KEYTYPE, KEY_A))
    return tl.SshTarget(transport, host, key=key, known_hosts=kh)


def adapter(tmp, *, runner=None, probe=None, scan=None):
    t = target(tmp)
    a = tl.SshAdapter(t, runner=runner or (lambda argv, **kw: cp(argv)),
                      probe=probe or (lambda h, p, to: (True, "tcp connect ok")))
    if scan is not None:
        a.scan_host_key = lambda: scan  # type: ignore[method-assign]
    return a


class TestClassification(unittest.TestCase):
    def test_host_key_mismatch_wins_over_auth_text(self):
        e = tl.classify_ssh_failure(255, "Host key verification failed.")
        self.assertIsInstance(e, tl.HostKeyMismatch)
        self.assertEqual(e.exit_code, tl.EXIT_HOSTKEY)

    def test_authentication_failure(self):
        e = tl.classify_ssh_failure(255, "nuxel@host: Permission denied (publickey).")
        self.assertIsInstance(e, tl.AuthenticationFailed)
        self.assertEqual(e.exit_code, tl.EXIT_AUTH)

    def test_refused_timeout_route_and_dns_are_distinct(self):
        cases = [
            ("Connection refused", "connection refused"),
            ("Connection timed out", "timed out"),
            ("No route to host", "no route"),
            ("Could not resolve hostname", "resolved"),
        ]
        for text, needle in cases:
            e = tl.classify_ssh_failure(255, text)
            self.assertIsInstance(e, tl.NetworkFailure)
            self.assertIn(needle, str(e).lower())

    def test_scp_destination_error_is_a_transfer_failure(self):
        e = tl.classify_ssh_failure(1, "scp: /var/tmp/x: No such file or directory")
        self.assertIsInstance(e, tl.TransferFailure)
        self.assertEqual(e.exit_code, tl.EXIT_TRANSFER)

    def test_connection_reset_is_network_failure(self):
        e = tl.classify_ssh_failure(255, "Connection reset by peer")
        self.assertIsInstance(e, tl.NetworkFailure)
        self.assertEqual(e.exit_code, tl.EXIT_NETWORK)

    def test_boot_id_change_is_a_reboot(self):
        self.assertEqual(tl.classify_reconnect("a", "b", "t1", "t1"), "phone_reboot")

    def test_same_boot_new_sshd_timestamp_is_a_service_restart(self):
        self.assertEqual(tl.classify_reconnect("a", "a", "t1", "t2"), "sshd_restart")

    def test_same_boot_and_same_sshd_is_transport_loss(self):
        self.assertEqual(tl.classify_reconnect("a", "a", "t1", "t1"), "transport_loss")


class TestKnownHosts(unittest.TestCase):
    def test_parse_and_compare(self):
        text = "nuxel-s10plus %s %s\nother %s %s\n" % (KEYTYPE, KEY_A, KEYTYPE, KEY_B)
        pinned = tl.parse_known_host_key(text, "nuxel-s10plus")
        self.assertEqual(pinned, [(KEYTYPE, KEY_A)])
        self.assertEqual(tl.compare_host_keys(pinned, [(KEYTYPE, KEY_A)]), "ok")
        self.assertEqual(tl.compare_host_keys(pinned, [(KEYTYPE, KEY_B)]), "mismatch")
        self.assertEqual(tl.compare_host_keys([], [(KEYTYPE, KEY_A)]), "missing")
        self.assertEqual(tl.compare_host_keys(pinned, []), "unknown")

    def test_hashed_or_aliased_entries_are_not_confused(self):
        text = "nuxel-s10plus %s %s\n" % (KEYTYPE, KEY_A)
        self.assertEqual(tl.parse_known_host_key(text, "nuxel-s10plus"),
                         [(KEYTYPE, KEY_A)])
        self.assertEqual(tl.parse_known_host_key(text, "nuxel"), [])

    def test_host_key_check_reports_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d)
            a.scan_host_key = lambda: [(KEYTYPE, KEY_B)]  # type: ignore[method-assign]
            c = a.check_host_key()
            self.assertEqual(c.status, "MISMATCH")
            self.assertIn("does NOT match", c.detail)


class TestSshPreflight(unittest.TestCase):
    def test_missing_ssh_client_is_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d)
            with mock.patch.object(tl, "_which", return_value=None):
                r = a.preflight()
            self.assertEqual(r.status, "UNAVAILABLE")
            self.assertEqual(r.exit_code, tl.EXIT_UNAVAILABLE)

    def test_missing_private_key_is_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            t = target(d)
            t.key.unlink()
            a = tl.SshAdapter(t, runner=lambda argv, **kw: cp(argv),
                              probe=lambda h, p, to: (True, "ok"))
            r = a.preflight()
            self.assertEqual(r.status, "UNAVAILABLE")
            self.assertIn("private key", r.detail)

    def test_host_key_mismatch_refuses_before_auth(self):
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, scan=[(KEYTYPE, KEY_B)])
            r = a.preflight()
            self.assertEqual(r.status, "HOSTKEY_MISMATCH")
            self.assertEqual(r.exit_code, tl.EXIT_HOSTKEY)

    def test_auth_failure_is_reported_as_auth(self):
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, runner=lambda argv, **kw: cp(
                argv, 255, "", "Permission denied (publickey)."),
                scan=[(KEYTYPE, KEY_A)])
            r = a.preflight()
            self.assertEqual(r.status, "AUTHENTICATION")
            self.assertEqual(r.exit_code, tl.EXIT_AUTH)

    def test_refused_connection_is_reported_as_unreachable(self):
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, probe=lambda h, p, to: (False, "tcp connection refused"),
                        scan=[(KEYTYPE, KEY_A)])
            r = a.preflight()
            self.assertEqual(r.status, "UNREACHABLE")
            self.assertEqual(r.exit_code, tl.EXIT_NETWORK)

    def test_available_preflight_includes_shell(self):
        def runner(argv, **kw):
            cmd = argv[-1]
            if cmd.startswith("command -v bash"):
                return cp(argv, 0, "/usr/bin/bash\n")
            return cp(argv, 0, "")
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, runner=runner, scan=[(KEYTYPE, KEY_A)])
            r = a.preflight()
            self.assertEqual(r.status, "AVAILABLE")
            self.assertTrue(any(c.name == "remote-shell" and c.status == "OK"
                                for c in r.checks))


class TestExitCodesAndRetries(unittest.TestCase):
    def test_remote_exit_status_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, runner=lambda argv, **kw: cp(argv, 7))
            self.assertEqual(a.execute("exit 7", retries=0), 7)

    def test_transport_failure_is_retried_bounded(self):
        calls = {"n": 0}
        def runner(argv, **kw):
            calls["n"] += 1
            return cp(argv, 255, "", "Connection reset by peer") if calls["n"] < 3 else cp(argv, 0)
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, runner=runner)
            a.sleep = lambda s: None
            self.assertEqual(a.execute("true", retries=3), 0)
            self.assertEqual(calls["n"], 3)

    def test_retry_budget_is_finite(self):
        calls = {"n": 0}
        def runner(argv, **kw):
            calls["n"] += 1
            return cp(argv, 255, "", "Connection reset by peer")
        with tempfile.TemporaryDirectory() as d:
            a = adapter(d, runner=runner)
            a.sleep = lambda s: None
            self.assertEqual(a.execute("true", retries=2), 255)
            self.assertEqual(calls["n"], 3)

    def test_validation_error_code(self):
        self.assertEqual(tl.UsageError("x").exit_code, tl.EXIT_USAGE)
        self.assertEqual(tl.LockConflict("x").exit_code, tl.EXIT_LOCK)
        self.assertEqual(tl.TransferFailure("x").exit_code, tl.EXIT_TRANSFER)


class FakeTransferAdapter(tl.SshAdapter):
    """Real files in a fake remote directory; no network."""
    def __init__(self, tmp, *, corrupt=False):
        super().__init__(target(tmp))
        self.root = Path(tmp) / "remote"
        self.root.mkdir()
        self.corrupt = corrupt
        self.cleaned: list[str] = []

    def remote_spec(self, path):
        return str(self.root / Path(path).name)

    def _scp(self, args):
        src, dst = args[-2], args[-1]
        if "@" in src:
            src = str(self.root / Path(src.split(":", 1)[1]).name)
        shutil.copyfile(src, dst)

    def remote_sha256(self, path):
        p = Path(path)
        if self.corrupt:
            return "0" * 64
        return tl.sha256_file(p)

    def _ssh_checked(self, command):
        parts = command.split()
        if parts[:2] == ["mv", "-f"]:
            os.replace(parts[2], parts[3])

    def _cleanup_remote(self, path):
        self.cleaned.append(path)
        try:
            os.unlink(path)
        except OSError:
            pass


class TestTransfers(unittest.TestCase):
    def test_put_verifies_and_installs(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.txt"
            src.write_text("tri-link\n")
            a = FakeTransferAdapter(d)
            dest = str(a.root / "dest.txt")
            doc = a.put(str(src), dest)
            self.assertTrue(doc["verified"])
            self.assertEqual(Path(dest).read_text(), "tri-link\n")
            self.assertEqual(doc["sha256"], tl.sha256_file(src))

    def test_put_corruption_cleans_staging_and_does_not_install(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.txt"
            src.write_text("tri-link\n")
            a = FakeTransferAdapter(d, corrupt=True)
            dest = str(a.root / "dest.txt")
            with self.assertRaises(tl.TransferFailure):
                a.put(str(src), dest)
            self.assertFalse(Path(dest).exists())
            self.assertTrue(a.cleaned)

    def test_get_verifies_and_cleans_on_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            a = FakeTransferAdapter(d)
            remote = a.root / "remote.txt"
            remote.write_text("payload\n")
            out = Path(d) / "out.txt"
            doc = a.get(str(remote), str(out))
            self.assertTrue(doc["verified"])
            self.assertEqual(out.read_text(), "payload\n")
            a.corrupt = True
            bad = Path(d) / "bad.txt"
            with self.assertRaises(tl.TransferFailure):
                a.get(str(remote), str(bad))
            self.assertFalse(bad.exists())

    def test_remote_path_with_space_is_quoted_in_command(self):
        self.assertEqual(tl.q("/var/tmp/a b"), "'/var/tmp/a b'")
        self.assertEqual(tl.validate_remote_path("/var/tmp/a b"), "/var/tmp/a b")


class TestLocksAndConflicts(unittest.TestCase):
    def test_guard_excludes_a_second_transfer(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "guard.lock"
            one = tl.DeploymentGuard(p, wait=0)
            one.acquire()
            try:
                with self.assertRaises(tl.LockConflict):
                    tl.DeploymentGuard(p, wait=0).acquire()
                self.assertEqual(tl.guard_status(p)["state"], "held")
            finally:
                one.release()
            self.assertEqual(tl.guard_status(p)["state"], "free")
            two = tl.DeploymentGuard(p, wait=0)
            two.acquire()
            two.release()

    def test_serial_deployment_conflict_is_detected(self):
        a = tl.SerialAdapter("/dev/ttyACM0", launcher=Path(__file__))
        with mock.patch.object(tl, "_serial_lock_owner",
                               return_value={"lock_state": "held", "pid": 12,
                                             "op": "deploy-x"}):
            self.assertEqual(a.deployment_conflict()["op"], "deploy-x")

    def test_serial_unknown_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            dev = Path(d) / "ttyACM0"
            dev.write_text("")
            launcher = Path(d) / "nuxel-live.sh"
            launcher.write_text("#!/bin/sh\nexit 0\n")
            a = tl.SerialAdapter(str(dev), launcher=launcher)
            with mock.patch.object(tl, "_serial_lock_owner",
                                   return_value={"lock_state": "unknown"}):
                r = a.status()
            self.assertEqual(r.status, "UNKNOWN")
            self.assertEqual(r.exit_code, tl.EXIT_LOCK)

    def test_serial_status_busy_does_not_open_the_port(self):
        with tempfile.TemporaryDirectory() as d:
            dev = Path(d) / "ttyACM0"
            dev.write_text("")
            launcher = Path(d) / "nuxel-live.sh"
            launcher.write_text("#!/bin/sh\nexit 0\n")
            a = tl.SerialAdapter(str(dev), launcher=launcher)
            with mock.patch.object(tl, "_serial_lock_owner",
                                   return_value={"lock_state": "held", "pid": 1,
                                                 "op": "deploy"}):
                r = a.status()
            self.assertEqual(r.status, "BUSY")
            self.assertEqual(r.exit_code, tl.EXIT_LOCK)


class TestSerialDelegation(unittest.TestCase):
    def test_run_delegates_to_the_proven_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            dev = Path(d) / "ttyACM0"
            dev.write_text("")
            out = Path(d) / "args.txt"
            launcher = Path(d) / "nuxel-live.sh"
            launcher.write_text("#!/bin/sh\nprintf '%%s\\n' \"$*\" > %s\nexit 9\n" % out)
            launcher.chmod(0o755)
            a = tl.SerialAdapter(str(dev), launcher=launcher)
            self.assertEqual(a.run("id", timeout=3), 9)
            self.assertIn("--run id", out.read_text())
            self.assertIn("--dev %s" % dev, out.read_text())


class TestUsbCapability(unittest.TestCase):
    def _tree(self, d, *, functions=("acm.usb0",), host_iface=False,
              vid="18d1", pid="4ee7"):
        gadget = Path(d) / "gadget" / "nuxel"
        (gadget / "configs" / "c.1").mkdir(parents=True)
        (gadget / "functions").mkdir()
        for fn in functions:
            (gadget / "functions" / fn).mkdir()
            os.symlink(gadget / "functions" / fn, gadget / "configs" / "c.1" / fn)
        net = Path(d) / "net"
        (net / "lo").mkdir(parents=True)
        if host_iface:
            dev = net / "usb0" / "device"
            dev.mkdir(parents=True)
            (dev / "idVendor").write_text(vid + "\n")
            (dev / "idProduct").write_text(pid + "\n")
        return gadget.parent, net

    def test_ncm_compiled_but_only_acm_active(self):
        cfg = "CONFIG_USB_CONFIGFS=y\nCONFIG_USB_DWC3=y\nCONFIG_USB_CONFIGFS_ACM=y\n" \
              "CONFIG_USB_F_ACM=y\nCONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n" \
              "# CONFIG_USB_CONFIGFS_ECM is not set\n"
        with tempfile.TemporaryDirectory() as d:
            g, net = self._tree(d)
            doc = tl.usb_capability(cfg, g, net)
            self.assertTrue(doc["compiled"]["ncm"])
            self.assertFalse(doc["compiled"]["ecm"])
            self.assertEqual(doc["status"], "SUPPORTED_NOT_ENABLED")
            self.assertEqual(doc["preferred_mode"], "ncm")

    def test_missing_configfs_is_blocked_kernel(self):
        cfg = "# CONFIG_USB_CONFIGFS is not set\nCONFIG_USB_DWC3=y\n"
        with tempfile.TemporaryDirectory() as d:
            g, net = self._tree(d)
            doc = tl.usb_capability(cfg, g, net)
            self.assertEqual(doc["status"], "BLOCKED_KERNEL")

    def test_present_host_interface_is_available(self):
        cfg = "CONFIG_USB_CONFIGFS=y\nCONFIG_USB_DWC3=y\nCONFIG_USB_F_NCM=y\n" \
              "CONFIG_USB_CONFIGFS_NCM=y\n"
        with tempfile.TemporaryDirectory() as d:
            g, net = self._tree(d, functions=("acm.usb0", "ncm.usb0"), host_iface=True)
            doc = tl.usb_capability(cfg, g, net)
            self.assertEqual(doc["status"], "AVAILABLE")
            self.assertEqual(doc["host_gadget_interface"], "usb0")

    def test_linux_host_without_usb_iface_is_definitive(self):
        with tempfile.TemporaryDirectory() as d:
            net = Path(d) / "net"
            (net / "lo").mkdir(parents=True)
            with mock.patch.object(tl.sys, "platform", "linux"):
                iface, definitive = tl.usb_host_presence(net)
            self.assertIsNone(iface)
            self.assertTrue(definitive)


class TestAutoSelection(unittest.TestCase):
    def test_auto_selects_first_available_explicitly(self):
        w = tl.TransportReport("wlan", "AVAILABLE", "nuxel@10.20.30.16:22")
        u = tl.TransportReport("usb", "UNAVAILABLE", detail="no usb0")
        self.assertIs(tl.select_auto([w, u]), w)
        self.assertIs(tl.select_auto([u, w]), w)

    def test_auto_never_falls_back_to_an_unavailable_transport(self):
        u = tl.TransportReport("usb", "UNAVAILABLE")
        self.assertIsNone(tl.select_auto([u]))

    def test_missing_usb_capability_is_explicit_in_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            reports = tl.discover_ssh_reports(
                wlan_host=None, usb_host="10.15.19.82", user="nuxel", port=22,
                key=Path(d) / "k", known_hosts=Path(d) / "kh",
                host_key_alias="nuxel-s10plus", usb_available=False)
            usb = [r for r in reports if r.transport == "usb"][0]
            self.assertEqual(usb.status, "UNAVAILABLE")
            self.assertIn("usb0", usb.detail)

    def test_discovery_output_reports_selection_and_serial(self):
        w = tl.TransportReport("wlan", "AVAILABLE", "nuxel@10.20.30.16:22")
        s = tl.TransportReport("serial", "AVAILABLE", "/dev/ttyACM0")
        text = tl.format_discovery([w], w, s)
        self.assertIn("selected: wlan", text)
        self.assertIn("serial", text)
        self.assertIn("no silent fallback", text)


class TestRollbackIntegration(unittest.TestCase):
    """Real deploy transaction + real fake-console PTY; no physical phone."""

    def test_failed_health_check_restores_the_previous_ssh_config(self):
        with FakePhone("healthy") as phone:
            root = Path(phone.root)
            target = root / "etc" / "ssh" / "sshd_config.d" / "60-nuxel-tri-link.conf"
            target.parent.mkdir(parents=True)
            target.write_text("# HEALTHY OLD CONFIG\n")
            manifest = {
                "schema_version": 1,
                "groups": [{
                    "id": "tri-link-ssh-test", "component": "test",
                    "priority": 1, "risk": "low",
                    "restart_service": "sshd.service",
                    "health_check": "grep -q HEALTHY /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf",
                    "rollback": "restore <target>.nuxel-rollback and restart sshd.service",
                    "files": [{
                        "source": "configs/nuxel/security/ssh/60-nuxel-tri-link.conf",
                        "target": "/etc/ssh/sshd_config.d/60-nuxel-tri-link.conf",
                        "mode": "0644",
                    }],
                }],
            }
            with tempfile.TemporaryDirectory() as d:
                man = Path(d) / "manifest.json"
                man.write_text(json.dumps(manifest))
                env = os.environ.copy()
                env["NUXEL_LIVE_LOCK"] = str(Path(d) / "console.lock")
                p = subprocess.run(
                    [sys.executable, str(LIVE / "nuxel-live-deploy.py"),
                     "--manifest", str(man), "--evidence-dir", d,
                     "--name", "tri-link-rollback", "--dev", phone.dev,
                     "--apply", "--only", "tri-link-ssh-test",
                     "--timeout", "10", "--lock-wait", "5", "--json"],
                    capture_output=True, text=True, env=env, timeout=90)
            self.assertEqual(p.returncode, 5, p.stdout + p.stderr)
            self.assertEqual(target.read_text(), "# HEALTHY OLD CONFIG\n",
                             "rollback must restore the pre-transaction bytes")
            doc = json.loads(p.stdout)
            self.assertTrue(doc.get("rollback_ok"))
            self.assertEqual(doc.get("verdict"), "FAILED")


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- #
# USB-NCM device helper (offline fake configfs; no phone)
# --------------------------------------------------------------------------- #
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("nuxel_usb_net", LIVE / "nuxel-usb-net.py")
usbnet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(usbnet)


class TestUsbNetHelper(unittest.TestCase):
    def _fake_gadget(self, d):
        g = Path(d) / "usb_gadget" / "nuxel"
        (g / "functions" / "acm.usb0").mkdir(parents=True)
        (g / "configs" / "c.1").mkdir(parents=True)
        (g / "configs" / "c.1" / "strings" / "0x409").mkdir(parents=True)
        (g / "UDC").write_text("10c00000.dwc3\n")
        os.symlink(g / "functions" / "acm.usb0", g / "configs" / "c.1" / "acm.usb0")
        return g

    def test_subnet_conflict_is_detected_without_touching_routing(self):
        state = {"addr": "10.15.19.50/24 dev wlan9\n",
                 "route": "10.15.19.0/24 dev wlan9 proto kernel\n"}
        self.assertEqual(usbnet.subnet_in_use(state), "wlan9")
        self.assertIsNone(usbnet.subnet_in_use({"addr": "", "route": ""}))

    def test_snapshot_is_reversible_and_preserves_acm(self):
        with tempfile.TemporaryDirectory() as d:
            g = self._fake_gadget(d)
            state = Path(d) / "state"
            run = Path(d) / "run"
            backup = usbnet.snapshot(g, state)
            ncm = g / "functions" / "ncm.usb0"
            ncm.mkdir()
            link = g / "configs" / "c.1" / "ncm.usb0"
            os.symlink(ncm, link)
            backup.update({"ncm_link": str(link), "ncm_function_created": True})
            doc = usbnet._rollback_from(g, state, backup, run)
            self.assertEqual(doc["status"], "ROLLED_BACK", doc)
            self.assertFalse(link.exists())
            self.assertFalse(ncm.exists())
            self.assertTrue((g / "functions" / "acm.usb0").is_dir())
            self.assertTrue((g / "configs" / "c.1" / "acm.usb0").is_symlink())
            self.assertEqual((g / "UDC").read_text().strip(), "10c00000.dwc3")

    def test_apply_refuses_without_explicit_serial_risk_ack(self):
        with tempfile.TemporaryDirectory() as d:
            g = self._fake_gadget(d)
            with self.assertRaises(usbnet.UsbNetError):
                usbnet.apply(g, Path(d) / "state", Path(d) / "run", 30,
                             "CONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n",
                             allow_serial_risk=False)

    def test_apply_refuses_known_bad_4314_kernel(self):
        with tempfile.TemporaryDirectory() as d:
            g = self._fake_gadget(d)
            with self.assertRaises(usbnet.UsbNetError) as cm:
                usbnet.apply(g, Path(d) / "state", Path(d) / "run", 30,
                             "CONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n",
                             allow_serial_risk=True, kernel_release="4.14.253")
            self.assertIn("BLOCKED_KERNEL_PANIC", str(cm.exception))

    def test_early_failure_does_not_rebind_the_udc(self):
        with tempfile.TemporaryDirectory() as d:
            g = self._fake_gadget(d)
            state = Path(d) / "state"
            backup = usbnet.snapshot(g, state)
            ncm = g / "functions" / "ncm.usb0"
            ncm.mkdir()
            backup.update({"ncm_function_created": True, "rebind_needed": False})
            calls = []
            orig = usbnet._rebind
            usbnet._rebind = lambda *a, **k: calls.append(a)
            try:
                doc = usbnet._rollback_from(g, state, backup, Path(d) / "run")
            finally:
                usbnet._rebind = orig
            self.assertEqual(doc["status"], "ROLLED_BACK", doc)
            self.assertFalse(ncm.exists())
            self.assertEqual(calls, [], "an early failure must not rebind the live ACM gadget")

    def test_apply_refuses_when_ncm_is_not_compiled(self):
        with tempfile.TemporaryDirectory() as d:
            g = self._fake_gadget(d)
            with self.assertRaises(usbnet.UsbNetError):
                usbnet.apply(g, Path(d) / "state", Path(d) / "run", 30,
                             "# CONFIG_USB_F_NCM is not set\n",
                             allow_serial_risk=True)

    def test_capability_reports_supported_not_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            g = self._fake_gadget(d)
            doc = usbnet.capability(g, "CONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\n")
            self.assertTrue(doc["compiled_ncm"])
            self.assertTrue(doc["gadget_present"])
            self.assertEqual(doc["bound_udc"], "10c00000.dwc3")
            self.assertFalse(doc["has_usb0"])
            self.assertEqual(doc["status"], "SUPPORTED_NOT_ENABLED")

    def test_confirm_removes_timer_and_writes_marker(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / "state"
            run = Path(d) / "run"
            state.mkdir()
            (state / "timer.pid").write_text("999999\n")
            doc = usbnet.confirm(state, run)
            self.assertEqual(doc["status"], "CONFIRMED")
            self.assertTrue((run / "nuxel-usb-net.confirmed").exists())
            self.assertFalse((state / "timer.pid").exists())


# --------------------------------------------------------------------------- #
# CLI: auto never silently selects a serial-only action
# --------------------------------------------------------------------------- #
_spec_cli = importlib.util.spec_from_file_location("nuxel_live_ssh_cli",
                                                    LIVE / "nuxel-live-ssh.py")
ssh_cli = importlib.util.module_from_spec(_spec_cli)
_spec_cli.loader.exec_module(ssh_cli)


class TestCliExplicitTransport(unittest.TestCase):
    def test_auto_refuses_a_serial_only_action(self):
        with self.assertRaises(tl.UsageError):
            ssh_cli.main(["--transport", "auto", "--run", "echo nope"])

    def test_wlan_refuses_a_serial_only_action(self):
        with self.assertRaises(tl.UsageError):
            ssh_cli.main(["--transport", "wlan", "--host", "10.20.30.16",
                          "--run", "echo nope"])

    def test_keyboard_interrupt_is_clean_exit_130(self):
        with mock.patch.object(ssh_cli, "main", side_effect=KeyboardInterrupt):
            self.assertEqual(ssh_cli.cli([]), tl.EXIT_CANCELLED)

    def test_classified_error_returns_its_exit_code(self):
        with mock.patch.object(ssh_cli, "main",
                               side_effect=tl.HostKeyMismatch("mismatch")):
            self.assertEqual(ssh_cli.cli([]), tl.EXIT_HOSTKEY)
