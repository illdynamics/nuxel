#!/usr/bin/env python3
"""nuxel-live-ssh — explicit Tri-Link transport selection and SSH console.

Examples:
  nuxel-live-ssh.py --transport auto --discover
  nuxel-live-ssh.py --transport wlan --host 10.20.30.16 --shell
  nuxel-live-ssh.py --transport usb --usb-host 10.15.19.82 --diagnose
  nuxel-live-ssh.py --transport wlan --host 10.20.30.16 --exec 'systemctl is-active sshd'
  nuxel-live-ssh.py --transport wlan --host 10.20.30.16 --put ./x /var/tmp/x
  nuxel-live-ssh.py --transport serial --run 'uname -a'

Serial is delegated to scripts/s10plus-debug-pack/nuxel-live.sh.  That remains
the recovery path and is never opened by this program.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nuxel_tri_link as tl  # noqa: E402


def _print_json(doc):
    print(json.dumps(doc, indent=2, sort_keys=True, default=str))


def _config(args):
    cfg = tl.load_config(args.config)
    wlan = args.host or cfg.get("wlan_host") or os.environ.get("NUXEL_WLAN_HOST")
    usb = args.usb_host or cfg.get("usb_host") or os.environ.get("NUXEL_USB_HOST")
    user = args.user or cfg.get("user") or tl.DEFAULT_USER
    port = int(args.port or cfg.get("port") or tl.DEFAULT_PORT)
    key = Path(args.key or cfg.get("key") or tl.DEFAULT_KEY).expanduser()
    known = Path(args.known_hosts or cfg.get("known_hosts") or
                 tl.DEFAULT_KNOWN_HOSTS).expanduser()
    alias = args.host_key_alias or cfg.get("host_key_alias") or tl.DEFAULT_HOST_KEY_ALIAS
    serial_dev = args.serial_dev or cfg.get("serial_dev") or os.environ.get("NUXEL_SERIAL_DEV")
    return cfg, wlan, usb, user, port, key, known, alias, serial_dev


def _target(transport, wlan, usb, user, port, key, known, alias):
    host = wlan if transport == "wlan" else usb
    if not host:
        if transport == "wlan":
            raise tl.UsageError(
                "WLAN target unknown: pass --host (or set NUXEL_WLAN_HOST); "
                "the tool never guesses an address")
        raise tl.UsageError(
            "USB target unknown: pass --usb-host (the USB adapter only works "
            "when the phone exposes usb0/ncm0/rndis0)")
    return tl.SshTarget(transport, host, user=user, port=port, key=key,
                        known_hosts=known, host_key_alias=alias)


def _serial(dev):
    return tl.SerialAdapter(dev)


def _check_conflict_only(args, ssh_adapter=None):
    """Refuse mutation while a serial deployment/session owns the phone.

    A read/exec is deliberately NOT put behind the exclusive transfer guard:
    an operator must still be able to inspect a phone while a transfer runs, and
    transfers stage to a temporary path before an atomic rename.  Mutating
    transfers do acquire DeploymentGuard(), which excludes another transfer or
    deployment.
    """
    if ssh_adapter is not None:
        serial = _serial(args.serial_dev)
        owner = serial.deployment_conflict()
        if owner and not args.allow_busy_deploy:
            raise tl.LockConflict(
                "a serial deployment/session currently owns %s (pid=%s op=%s); "
                "refusing to mutate the same target over SSH"
                % (serial.dev, owner.get("pid"), owner.get("op")))


def _conflict_guard(args, ssh_adapter=None, *, mutating=True):
    """Acquire the cross-transport guard and refuse an active serial deploy."""
    _check_conflict_only(args, ssh_adapter)
    guard = tl.DeploymentGuard(wait=args.lock_wait,
                               op=(args.exec or "transfer")[:80] if mutating else "read")
    guard.acquire()
    return guard


def _trust_host_key(target):
    kh = Path(target.known_hosts)
    existing = []
    try:
        existing = tl.parse_known_host_key(kh.read_text(), target.host_key_alias)
    except OSError:
        pass
    scanned = []
    if tl._which("ssh-keyscan"):
        p = subprocess.run(["ssh-keyscan", "-T", "5", "-p", str(target.port),
                            "-t", "ed25519", target.host], capture_output=True, text=True)
        if p.returncode == 0:
            scanned = tl.parse_scanned_key(p.stdout)
    if not scanned:
        raise tl.NetworkFailure("ssh-keyscan returned no host key; refusing to guess")
    if existing:
        verdict = tl.compare_host_keys(existing, scanned)
        if verdict != "ok":
            raise tl.HostKeyMismatch(
                "pinned host key for %s does not match the phone; refusing to "
                "overwrite it (inspect the phone before trusting a new key)"
                % target.host_key_alias)
        return existing[0]
    keytype, key = scanned[0]
    line = "%s %s %s\n" % (target.host_key_alias, keytype, key)
    kh.parent.mkdir(parents=True, exist_ok=True)
    with open(kh, "a") as fh:
        fh.write(line)
    return keytype, key


def _init_key(key):
    key = Path(key)
    if key.exists():
        pub = Path(str(key) + ".pub")
        return {"created": False, "key": str(key),
                "public_key": pub.read_text().strip() if pub.exists() else ""}
    key.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C",
                    "nuxel-tri-link@%s" % os.uname().nodename, "-f", str(key)],
                   check=True)
    return {"created": True, "key": str(key),
            "public_key": Path(str(key) + ".pub").read_text().strip()}


def _remember(args, wlan, usb, user, port, key, known, alias):
    path = Path(args.config or (Path.home() / ".config" / "nuxel" / "live-ssh.json"))
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        doc = {}
    if wlan:
        doc["wlan_host"] = wlan
    if usb:
        doc["usb_host"] = usb
    doc.update({"user": user, "port": port, "key": str(key),
                "known_hosts": str(known), "host_key_alias": alias,
                "updated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z")})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return path


def _discovery(args, wlan, usb, user, port, key, known, alias):
    iface, definitive = tl.usb_host_presence()
    usb_available = True if not definitive else bool(iface)
    reports = tl.discover_ssh_reports(
        wlan_host=wlan, usb_host=usb, user=user, port=port, key=key,
        known_hosts=known, host_key_alias=alias, check_network=True,
        usb_available=usb_available)
    selected = tl.select_auto(reports)
    serial = _serial(args.serial_dev).status()
    return reports, selected, serial


def _preflight_or_raise(report):
    if report.status != "AVAILABLE":
        kind = report.status.lower()
        if kind == "hostkey_mismatch":
            raise tl.HostKeyMismatch(report.detail)
        if kind == "authentication":
            raise tl.AuthenticationFailed(report.detail)
        if kind in ("unreachable", "network"):
            raise tl.NetworkFailure(report.detail)
        raise tl.TransportUnavailable(report.detail or report.status)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Nuxel Tri-Link console: serial, USB SSH, WLAN SSH, explicit auto")
    ap.add_argument("--transport", choices=("serial", "usb", "wlan", "auto"),
                    default="auto")
    ap.add_argument("--host", help="WLAN SSH target (never guessed)")
    ap.add_argument("--usb-host", help="USB-network SSH target (default from config)")
    ap.add_argument("--user", help="remote account (default nuxel)")
    ap.add_argument("--port", type=int, help="SSH port (default 22)")
    ap.add_argument("--key", help="private key path")
    ap.add_argument("--known-hosts", help="pinned known_hosts path")
    ap.add_argument("--host-key-alias", help="HostKeyAlias (default nuxel-s10plus)")
    ap.add_argument("--config", help="JSON config file")
    ap.add_argument("--serial-dev", help="serial console node")
    ap.add_argument("--serial-launcher", help="serial launcher path")
    ap.add_argument("--exec", metavar="CMD", help="run a remote command, preserve its exit code")
    ap.add_argument("--shell", "--interactive", action="store_true",
                    help="open an interactive shell (Bash when present)")
    ap.add_argument("--put", nargs=2, metavar=("LOCAL", "REMOTE"),
                    help="upload a file with staged SHA-256 verification")
    ap.add_argument("--get", nargs=2, metavar=("REMOTE", "LOCAL"),
                    help="download a file with staged SHA-256 verification")
    ap.add_argument("--run", metavar="CMD", help="serial transport: framed command")
    ap.add_argument("--pull", nargs=2, metavar=("REMOTE", "LOCAL"),
                    help="serial transport: pull a file")
    ap.add_argument("--batch", metavar="FILE", help="serial transport: one command per line")
    ap.add_argument("--deploy-manifest", metavar="FILE",
                    help="serial transport: run the proven deploy transaction under the guard")
    ap.add_argument("--discover", action="store_true", help="report discovery and exit")
    ap.add_argument("--status", action="store_true", help="alias for --discover")
    ap.add_argument("--diagnose", action="store_true", help="connection diagnostics")
    ap.add_argument("--init-key", action="store_true", help="create the host key if absent")
    ap.add_argument("--trust-host-key", action="store_true",
                    help="explicitly pin a NEW host key after showing its fingerprint")
    ap.add_argument("--remember", action="store_true", help="remember target in the user config")
    ap.add_argument("--retries", type=int, default=2, help="bounded SSH retries (exec only)")
    ap.add_argument("--retry-delay", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--lock-wait", type=float, default=0.0)
    ap.add_argument("--allow-busy-deploy", action="store_true",
                    help="permit SSH mutation while a serial deploy is active (dangerous)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    cfg, wlan, usb, user, port, key, known, alias, serial_dev = _config(args)

    if args.init_key:
        doc = _init_key(key)
        if args.json:
            _print_json(doc)
        else:
            print("# private key: %s" % doc["key"])
            print("# public key (deploy to /home/nuxel/.ssh/authorized_keys):")
            print(doc["public_key"])
        return 0

    if args.remember:
        path = _remember(args, wlan, usb, user, port, key, known, alias)
        print("# remembered %s" % path)
        return 0

    if args.trust_host_key:
        if not wlan and not usb:
            raise tl.UsageError("--trust-host-key needs --host or --usb-host")
        transport = "wlan" if wlan else "usb"
        target = _target(transport, wlan, usb, user, port, key, known, alias)
        keytype, keydata = _trust_host_key(target)
        line = "%s %s %s\n" % (target.host_key_alias, keytype, keydata)
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write(line)
            tmp = fh.name
        try:
            p = subprocess.run(["ssh-keygen", "-lf", tmp, "-E", "sha256"],
                               capture_output=True, text=True)
            fp = p.stdout.strip()
        finally:
            os.unlink(tmp)
        print("# pinned %s" % target.host_key_alias)
        print("# %s" % fp)
        return 0

    if args.run is not None or args.pull or args.batch or args.deploy_manifest:
        if args.transport != "serial":
            raise tl.UsageError(
                "--run/--pull/--batch/--deploy-manifest are serial-only; "
                "pass --transport serial explicitly (auto never switches silently)")
        serial = _serial(serial_dev)
        if args.deploy_manifest:
            st = serial.status()
            if st.status != "AVAILABLE":
                raise tl.LockConflict(st.detail or "serial console unavailable")
            manifest = os.path.abspath(args.deploy_manifest)
            deploy = str(HERE / "nuxel-live-deploy.py")
            with tl.DeploymentGuard(wait=args.lock_wait, op="serial-deploy"):
                argv2 = [sys.executable, deploy, "--manifest", manifest, "--apply",
                         "--dev", serial.dev, "--timeout", str(args.timeout),
                         "--lock-wait", str(args.lock_wait)]
                if args.allow_busy_deploy:
                    pass
                return subprocess.run(argv2).returncode
        if args.run is not None:
            return serial.run(args.run, timeout=args.timeout)
        if args.pull:
            remote, local = args.pull
            return serial.pull(remote, local, timeout=args.timeout)
        if args.batch:
            return serial.batch(args.batch, timeout=args.timeout)
        st = serial.status()
        if args.json:
            _print_json(st.as_dict())
        else:
            print("# " + st.line())
            for c in st.checks:
                print("#   %-12s %-12s %s" % (c.name, c.status, c.detail))
        return st.exit_code

    if args.transport == "auto":
        reports, selected, serial = _discovery(args, wlan, usb, user, port, key, known, alias)
        if args.discover or args.status or not (args.exec or args.shell or args.put or args.get or args.diagnose):
            if args.json:
                _print_json({"reports": [r.as_dict() for r in reports],
                             "selected": selected.as_dict() if selected else None,
                             "serial": serial.as_dict()})
            else:
                print(tl.format_discovery(reports, selected, serial))
            return 0 if selected else tl.EXIT_UNAVAILABLE
        if selected is None:
            print(tl.format_discovery(reports, None, serial), file=sys.stderr)
            raise tl.TransportUnavailable(
                "no SSH transport is available; serial recovery is explicit: "
                "use --transport serial")
        transport, host = selected.transport, (wlan if selected.transport == "wlan" else usb)
        print("# selected: %s -> %s" % (transport, selected.target), file=sys.stderr)
    else:
        transport = args.transport
        host = wlan if transport == "wlan" else usb

    target = _target(transport, wlan, usb, user, port, key, known, alias)
    adapter = tl.SshAdapter(target)

    if args.discover or args.status:
        report = adapter.preflight()
        if args.json:
            _print_json(report.as_dict())
        else:
            print("# " + report.line())
            for c in report.checks:
                print("#   %-12s %-12s %s" % (c.name, c.status, c.detail))
        return report.exit_code

    if args.diagnose:
        doc = adapter.diagnose()
        if args.json:
            _print_json(doc)
        else:
            print("# transport %s -> %s (account %s)"
                  % (transport, target.endpoint, target.user))
            pre = doc["preflight"]
            print("# status: %s (%s)" % (pre["status"], pre["detail"]))
            fpr = doc.get("host_key_fingerprint", ("unknown", ""))
            print("# host key: %s %s" % (fpr[0], fpr[1]))
            for name in ("id", "uname", "boot_id", "shell", "wlan", "usb", "sshd",
                         "sshd_effective"):
                val = doc.get(name)
                if isinstance(val, dict):
                    print("# %-14s rc=%s %s" % (name, val.get("rc"), val.get("stdout", "")[:300]))
        return 0 if doc["preflight"]["status"] == "AVAILABLE" else doc["preflight"]["exit_code"]

    if args.put:
        local, remote = args.put
        guard = _conflict_guard(args, adapter, mutating=True)
        try:
            doc = adapter.put(local, remote)
        finally:
            guard.release()
        if args.json:
            _print_json(doc)
        else:
            print("# put %s -> %s (%d bytes, sha256 %s verified)"
                  % (local, remote, doc["bytes"], doc["sha256"]))
        return 0

    if args.get:
        remote, local = args.get
        guard = _conflict_guard(args, adapter, mutating=True)
        try:
            doc = adapter.get(remote, local)
        finally:
            guard.release()
        if args.json:
            _print_json(doc)
        else:
            print("# get %s -> %s (%d bytes, sha256 %s verified)"
                  % (remote, local, doc["bytes"], doc["sha256"]))
        return 0

    if args.exec:
        report = adapter.preflight()
        _preflight_or_raise(report)
        _check_conflict_only(args, adapter)
        return adapter.execute(args.exec, retries=args.retries,
                               retry_delay=args.retry_delay)

    if args.shell:
        report = adapter.preflight()
        _preflight_or_raise(report)
        _check_conflict_only(args, adapter)
        shell = adapter.remote_shell()
        if not shell:
            raise tl.TransportUnavailable("the remote account has no usable shell")
        print("# transport %s; account %s; shell %s; exit status is the shell's"
              % (transport, target.user, shell), file=sys.stderr)
        return adapter.interactive(shell)

    # No action: report status, never open an accidental shell.
    report = adapter.preflight()
    if args.json:
        _print_json(report.as_dict())
    else:
        print("# " + report.line())
        for c in report.checks:
            print("#   %-12s %-12s %s" % (c.name, c.status, c.detail))
    return report.exit_code


def cli(argv=None):
    """Entry point with clean, classified failure and cancellation handling."""
    try:
        return main(argv)
    except KeyboardInterrupt:
        print("!! cancelled by operator (Ctrl-C); remote work already handed to "
              "the phone may still finish", file=sys.stderr)
        return tl.EXIT_CANCELLED
    except tl.TriLinkError as e:
        print("!! %s: %s" % (e.kind, e), file=sys.stderr)
        if getattr(e, "detail", ""):
            print(e.detail, file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    raise SystemExit(cli())
