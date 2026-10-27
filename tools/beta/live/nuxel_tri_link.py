#!/usr/bin/env python3
"""Nuxel Tri-Link transport manager (NUXEL-26000).

Three transports, kept deliberately separate:

  * serial — delegates to the existing, proven ``nuxel-live.sh`` framed console.
    This module never re-implements the serial protocol and never opens the
    serial device itself.
  * wlan   — OpenSSH over the phone's existing Wi-Fi address.
  * usb    — OpenSSH over a USB network gadget (only when the phone exposes a
    real usb0/ncm0/rndis0 interface; otherwise the transport is UNAVAILABLE).

The SSH adapters always pin a host key and always use public-key auth.  They do
not silently fall back to another transport.  Every local failure is classified
so an operator can tell Wi-Fi loss, route loss, refusal, timeout, authentication
failure and host-key mismatch apart.

This file is host-side code.  The on-device side is OpenSSH plus the policy
drop-in in configs/nuxel/security/ssh/.  The USB configfs helper is separate so
it cannot be mistaken for a host transport adapter.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import posixpath
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

VERSION = "26000"

# Local exit codes.  A remote command's own 0..255 status is returned verbatim
# when the SSH transport itself succeeded; these codes are used only when the
# local adapter had to refuse or could not establish the connection.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNAVAILABLE = 3
EXIT_HOSTKEY = 4
EXIT_AUTH = 5
EXIT_NETWORK = 6
EXIT_TRANSFER = 7
EXIT_LOCK = 8
EXIT_CANCELLED = 130

DEFAULT_USER = "nuxel"
DEFAULT_PORT = 22
DEFAULT_HOST_KEY_ALIAS = "nuxel-s10plus"
DEFAULT_WLAN_HOST = "10.20.30.16"
DEFAULT_USB_HOST = "10.15.19.82"
DEFAULT_USB_SUBNET = "10.15.19.0/24"
DEFAULT_WLAN_SUBNET = "10.20.30.0/24"

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KEY = Path.home() / ".ssh" / "nuxel-tri-link_ed25519"
DEFAULT_KNOWN_HOSTS = REPO_ROOT / "configs" / "nuxel" / "security" / "ssh" / "known_hosts"
SERIAL_LAUNCHER = REPO_ROOT / "scripts" / "s10plus-debug-pack" / "nuxel-live.sh"

#: OpenSSH's "transport failed" status.  A remote command can legitimately exit
#: 255 too, so callers that preserve remote status must rely on the parsed
#: stderr/kind as well as this value.
SSH_TRANSPORT_RC = 255

HOST_RE = re.compile(r"^[A-Za-z0-9._:%\[\]-]+$")

SSH_TRANSPORT_PATTERNS = (
    "connection refused", "connection reset", "connection closed",
    "connection timed out", "operation timed out", "timeout",
    "no route to host", "network is unreachable", "could not resolve hostname",
    "name or service not known", "temporary failure in name resolution",
    "broken pipe", "kex_exchange_identification", "client_loop",
    "connection to .* closed by remote host", "remote host identification",
    "host key verification failed",
)


class TriLinkError(Exception):
    """Base class for a bounded, classified transport failure."""

    kind = "error"
    exit_code = EXIT_UNAVAILABLE

    def __init__(self, message: str, *, kind: str | None = None,
                 exit_code: int | None = None, detail: str | None = None):
        super().__init__(message)
        if kind is not None:
            self.kind = kind
        if exit_code is not None:
            self.exit_code = exit_code
        self.detail = detail or ""


class UsageError(TriLinkError):
    kind = "usage"
    exit_code = EXIT_USAGE


class TransportUnavailable(TriLinkError):
    kind = "unavailable"
    exit_code = EXIT_UNAVAILABLE


class HostKeyMismatch(TriLinkError):
    kind = "host_key"
    exit_code = EXIT_HOSTKEY


class AuthenticationFailed(TriLinkError):
    kind = "authentication"
    exit_code = EXIT_AUTH


class NetworkFailure(TriLinkError):
    kind = "network"
    exit_code = EXIT_NETWORK


class TransferFailure(TriLinkError):
    kind = "transfer"
    exit_code = EXIT_TRANSFER


class LockConflict(TriLinkError):
    kind = "lock"
    exit_code = EXIT_LOCK


@dataclass
class Check:
    """One observable discovery/preflight fact."""

    name: str
    status: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass
class TransportReport:
    transport: str
    status: str
    target: str = ""
    account: str = ""
    detail: str = ""
    checks: list[Check] = field(default_factory=list)
    exit_code: int = EXIT_OK

    def as_dict(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "status": self.status,
            "target": self.target,
            "account": self.account,
            "detail": self.detail,
            "exit_code": self.exit_code,
            "checks": [c.as_dict() for c in self.checks],
        }

    def line(self) -> str:
        parts = ["%-6s %s" % (self.transport, self.status)]
        if self.target:
            parts.append(self.target)
        if self.account:
            parts.append("account=%s" % self.account)
        if self.detail:
            parts.append(self.detail)
        return " ".join(parts)


def validate_host(host: str) -> str:
    """Reject wildcard/bind-style hosts.  Never guess or synthesize an address."""
    h = str(host or "").strip()
    if not h:
        raise UsageError("empty SSH target")
    if h in ("0.0.0.0", "::", "*", "any", "all"):
        raise UsageError("refusing wildcard SSH target %r" % h)
    if not HOST_RE.match(h):
        raise UsageError("invalid SSH target %r" % h)
    return h


def validate_remote_path(path: str) -> str:
    p = str(path or "").strip()
    if not p:
        raise UsageError("empty remote path")
    if "\x00" in p or "\n" in p or "\r" in p:
        raise UsageError("remote path contains a control character")
    return p


def q(value: str) -> str:
    return shlex.quote(str(value))


def sha256_file(path: str | os.PathLike[str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _which(tool: str) -> str | None:
    return shutil.which(tool)


def _run_quiet(args: Sequence[str], timeout: float = 10.0,
               runner: Callable[..., subprocess.CompletedProcess] = subprocess.run
               ) -> subprocess.CompletedProcess:
    return runner(list(args), capture_output=True, text=True, timeout=timeout,
                  stdin=subprocess.DEVNULL)


def parse_known_host_key(text: str, alias: str) -> list[tuple[str, str]]:
    """Return [(keytype, base64)] for exact alias entries in a known_hosts file."""
    out: list[tuple[str, str]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 3:
            continue
        hosts = fields[0].split(",")
        if alias in hosts:
            out.append((fields[1], fields[2]))
    return out


def parse_scanned_key(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) >= 3:
            out.append((fields[1], fields[2]))
    return out


def compare_host_keys(pinned: Sequence[tuple[str, str]],
                      scanned: Sequence[tuple[str, str]]) -> str:
    """Return ok / missing / mismatch / unknown for two key lists."""
    if not pinned:
        return "missing"
    if not scanned:
        return "unknown"
    pset = {(k, v) for k, v in pinned}
    sset = {(k, v) for k, v in scanned}
    return "ok" if pset & sset else "mismatch"


def classify_ssh_failure(rc: int, stderr: str) -> TriLinkError | None:
    """Classify an SSH/SCP failure into an operator-actionable error."""
    if rc == 0:
        return None
    text = (stderr or "").lower()
    if "host key verification failed" in text or \
            "remote host identification has changed" in text or \
            "no .* host key is known" in text:
        return HostKeyMismatch(
            "SSH host key verification failed; refusing to connect",
            detail=(stderr or "").strip()[-2000:])
    if "scp:" in text and "permission denied (publickey" not in text:
        return TransferFailure("SCP transfer failed",
                               detail=(stderr or "").strip()[-2000:])
    if "permission denied" in text or "authentication failed" in text or \
            "no supported authentication methods" in text:
        return AuthenticationFailed(
            "SSH public-key authentication failed",
            detail=(stderr or "").strip()[-2000:])
    if "connection refused" in text:
        return NetworkFailure("SSH connection refused (service down or port closed?)",
                              detail=(stderr or "").strip()[-2000:])
    if "timed out" in text or "timeout" in text:
        return NetworkFailure("SSH connection timed out", detail=(stderr or "").strip()[-2000:])
    if "no route to host" in text or "network is unreachable" in text:
        return NetworkFailure("no route to the SSH target", detail=(stderr or "").strip()[-2000:])
    if "could not resolve hostname" in text or "name or service not known" in text:
        return NetworkFailure("SSH target name could not be resolved",
                              detail=(stderr or "").strip()[-2000:])
    if any(p in text for p in SSH_TRANSPORT_PATTERNS):
        return NetworkFailure("SSH transport failed", detail=(stderr or "").strip()[-2000:])
    return NetworkFailure("SSH failed (rc=%s)" % rc, detail=(stderr or "").strip()[-2000:])


def tcp_probe(host: str, port: int, timeout: float = 5.0) -> tuple[bool, str]:
    """Real TCP reachability check; does not authenticate or trust anything."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, "tcp connect ok"
    except socket.timeout:
        return False, "tcp connect timed out"
    except ConnectionRefusedError:
        return False, "tcp connection refused"
    except OSError as e:
        return False, "tcp connect failed: %s" % e


def looks_like_private_key(path: str | os.PathLike[str]) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(80)
        return b"PRIVATE KEY" in head
    except OSError:
        return False


@dataclass
class SshTarget:
    transport: str
    host: str
    user: str = DEFAULT_USER
    port: int = DEFAULT_PORT
    key: Path = DEFAULT_KEY
    known_hosts: Path = DEFAULT_KNOWN_HOSTS
    host_key_alias: str = DEFAULT_HOST_KEY_ALIAS
    connect_timeout: int = 8
    server_alive_interval: int = 15
    server_alive_count_max: int = 3

    def __post_init__(self) -> None:
        self.host = validate_host(self.host)
        self.user = str(self.user or DEFAULT_USER)
        self.port = int(self.port or DEFAULT_PORT)
        if self.transport not in ("wlan", "usb"):
            raise UsageError("SSH target transport must be wlan or usb")
        if not re.match(r"^[a-z_][a-z0-9_-]*$", self.user):
            raise UsageError("invalid SSH account %r" % self.user)

    @property
    def endpoint(self) -> str:
        return "%s@%s:%d" % (self.user, self.host, self.port)


class SshAdapter:
    """A pinned-host-key, public-key-only OpenSSH adapter.

    All process execution goes through ``runner`` so the failure classifier and
    transfer/checksum logic are deterministically testable without a phone.
    """

    def __init__(self, target: SshTarget,
                 runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 probe: Callable[[str, int, float], tuple[bool, str]] = tcp_probe,
                 sleep: Callable[[float], None] = time.sleep):
        self.target = target
        self.runner = runner
        self.probe = probe
        self.sleep = sleep

    # -- command construction ------------------------------------------------
    def ssh_options(self, *, batch: bool = True, tty: bool = False) -> list[str]:
        t = self.target
        opts = [
            "-i", str(t.key),
            "-o", "IdentitiesOnly=yes",
            "-o", "PubkeyAuthentication=yes",
            "-o", "PasswordAuthentication=no",
            "-o", "KbdInteractiveAuthentication=no",
            "-o", "PreferredAuthentications=publickey",
            "-o", "HostKeyAlias=%s" % t.host_key_alias,
            "-o", "UserKnownHostsFile=%s" % t.known_hosts,
            "-o", "GlobalKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "CheckHostIP=no",
            "-o", "ConnectTimeout=%d" % t.connect_timeout,
            "-o", "ServerAliveInterval=%d" % t.server_alive_interval,
            "-o", "ServerAliveCountMax=%d" % t.server_alive_count_max,
            "-o", "LogLevel=ERROR",
        ]
        if batch:
            opts += ["-o", "BatchMode=yes"]
        if tty:
            opts.append("-tt")
        opts += ["-p", str(t.port)]
        return opts

    def ssh_argv(self, command: str | None = None, *, batch: bool = True,
                 tty: bool = False) -> list[str]:
        argv = ["ssh"] + self.ssh_options(batch=batch, tty=tty)
        argv += ["-l", self.target.user, self.target.host]
        if command is not None:
            argv.append(command)
        return argv

    def scp_options(self) -> list[str]:
        t = self.target
        return [
            "-i", str(t.key),
            "-o", "IdentitiesOnly=yes",
            "-o", "PubkeyAuthentication=yes",
            "-o", "PasswordAuthentication=no",
            "-o", "KbdInteractiveAuthentication=no",
            "-o", "PreferredAuthentications=publickey",
            "-o", "HostKeyAlias=%s" % t.host_key_alias,
            "-o", "UserKnownHostsFile=%s" % t.known_hosts,
            "-o", "GlobalKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "CheckHostIP=no",
            "-o", "ConnectTimeout=%d" % t.connect_timeout,
            "-o", "LogLevel=ERROR",
            "-P", str(t.port),
        ]

    def remote_spec(self, path: str) -> str:
        return "%s@%s:%s" % (self.target.user, self.target.host, q(path))

    # -- observability -------------------------------------------------------
    def host_key_fingerprint(self) -> tuple[str, str]:
        """Return (status, fingerprint-or-detail) for the pinned alias."""
        try:
            text = Path(self.target.known_hosts).read_text()
        except OSError as e:
            return "missing", str(e)
        keys = parse_known_host_key(text, self.target.host_key_alias)
        if not keys:
            return "missing", "no entry for %s" % self.target.host_key_alias
        line = "%s %s %s\n" % (self.target.host_key_alias, keys[0][0], keys[0][1])
        with tempfile.NamedTemporaryFile("w", prefix="nuxel-kh-", delete=False) as fh:
            fh.write(line)
            tmp = fh.name
        try:
            p = _run_quiet(["ssh-keygen", "-lf", tmp, "-E", "sha256"], runner=self.runner)
            if p.returncode == 0:
                return "ok", p.stdout.strip()
            return "unknown", (p.stderr or p.stdout).strip()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def scan_host_key(self) -> list[tuple[str, str]]:
        if not _which("ssh-keyscan"):
            return []
        try:
            p = _run_quiet(["ssh-keyscan", "-T", "5", "-p", str(self.target.port),
                            "-t", "ed25519", self.target.host], runner=self.runner)
        except (OSError, subprocess.SubprocessError):
            return []
        return parse_scanned_key(p.stdout) if p.returncode == 0 else []

    def check_host_key(self) -> Check:
        try:
            text = Path(self.target.known_hosts).read_text()
        except OSError as e:
            return Check("host-key", "MISSING", str(e))
        pinned = parse_known_host_key(text, self.target.host_key_alias)
        if not pinned:
            return Check("host-key", "MISSING",
                         "no pinned key for alias %s" % self.target.host_key_alias)
        scanned = self.scan_host_key()
        verdict = compare_host_keys(pinned, scanned)
        if verdict == "ok":
            return Check("host-key", "OK", "pinned key matches the phone")
        if verdict == "mismatch":
            return Check("host-key", "MISMATCH",
                         "pinned key does NOT match the key now served by %s"
                         % self.target.host)
        return Check("host-key", "UNVERIFIED",
                     "could not fetch a key to compare (ssh-keyscan unavailable/failed)")

    # -- preflight -----------------------------------------------------------
    def preflight(self, *, check_network: bool = True) -> TransportReport:
        t = self.target
        checks: list[Check] = []
        for tool in ("ssh", "scp", "ssh-keyscan", "ssh-keygen"):
            checks.append(Check("tool:%s" % tool, "OK" if _which(tool) else "MISSING"))
        if not all(c.status == "OK" for c in checks if c.name.startswith("tool:")):
            return TransportReport(t.transport, "UNAVAILABLE", t.endpoint, t.user,
                                   "missing local OpenSSH client tools",
                                   checks, EXIT_UNAVAILABLE)
        key_ok = Path(t.key).is_file() and os.access(t.key, os.R_OK)
        checks.append(Check("private-key", "OK" if key_ok else "MISSING", str(t.key)))
        if not key_ok:
            return TransportReport(t.transport, "UNAVAILABLE", t.endpoint, t.user,
                                   "private key not found; run --init-key",
                                   checks, EXIT_UNAVAILABLE)
        if looks_like_private_key(t.key):
            try:
                mode = os.stat(t.key).st_mode & 0o777
                checks.append(Check("private-key-mode", "OK" if mode & 0o077 == 0 else "WARN",
                                    "0%o" % mode))
            except OSError:
                pass
        kh = self.check_host_key()
        checks.append(kh)
        if kh.status == "MISMATCH":
            return TransportReport(t.transport, "HOSTKEY_MISMATCH", t.endpoint, t.user,
                                   kh.detail, checks, EXIT_HOSTKEY)
        if kh.status == "MISSING":
            return TransportReport(t.transport, "HOSTKEY_MISSING", t.endpoint, t.user,
                                   kh.detail, checks, EXIT_HOSTKEY)
        if check_network:
            ok, detail = self.probe(t.host, t.port, t.connect_timeout)
            checks.append(Check("tcp", "OK" if ok else "FAIL", detail))
            if not ok:
                return TransportReport(t.transport, "UNREACHABLE", t.endpoint, t.user,
                                       detail, checks, EXIT_NETWORK)
        p = self.runner(self.ssh_argv("true"), capture_output=True, text=True,
                        timeout=t.connect_timeout + 5, stdin=subprocess.DEVNULL)
        err = classify_ssh_failure(p.returncode, p.stderr or "")
        if err is not None:
            checks.append(Check("auth", "FAIL", err.kind))
            return TransportReport(t.transport, err.kind.upper(), t.endpoint, t.user,
                                   str(err), checks, err.exit_code)
        checks.append(Check("auth", "OK", "publickey accepted"))
        shell = self.remote_shell()
        checks.append(Check("remote-shell", "OK" if shell else "UNKNOWN", shell or "?"))
        return TransportReport(t.transport, "AVAILABLE", t.endpoint, t.user,
                               "host key verified; public-key auth ok",
                               checks, EXIT_OK)

    # -- remote execution ----------------------------------------------------
    def _run(self, argv: list[str], timeout: float | None = None,
             capture: bool = True) -> subprocess.CompletedProcess:
        kwargs = {"capture_output": capture, "text": True, "timeout": timeout}
        if capture:
            # Never let a preflight/checksum SSH invocation consume stdin that
            # belongs to a subsequently exec'd interactive shell.
            kwargs["stdin"] = subprocess.DEVNULL
        return self.runner(argv, **kwargs)

    def run_capture(self, command: str, timeout: float | None = None) -> subprocess.CompletedProcess:
        return self._run(self.ssh_argv(command), timeout=timeout, capture=True)

    def remote_shell(self) -> str:
        try:
            p = self.run_capture("command -v bash 2>/dev/null || command -v sh 2>/dev/null",
                                 timeout=10)
        except (OSError, subprocess.SubprocessError):
            return ""
        return (p.stdout or "").strip().splitlines()[-1] if p.stdout else ""

    def execute(self, command: str, *, retries: int = 2,
                retry_delay: float = 1.0) -> int:
        """Run a remote command; return its exit status verbatim when possible."""
        if not command.strip():
            raise UsageError("empty remote command")
        last: subprocess.CompletedProcess | None = None
        for attempt in range(max(1, int(retries) + 1)):
            last = self._run(self.ssh_argv(command), timeout=None, capture=False)
            if last.returncode == 0:
                return 0
            err = classify_ssh_failure(last.returncode, "")
            # With inherited stderr we cannot inspect text; 255 is the only
            # signal.  Retry only 255, and only while attempts remain.
            if last.returncode != SSH_TRANSPORT_RC or attempt >= retries:
                return last.returncode
            self.sleep(retry_delay)
        return last.returncode if last else EXIT_NETWORK

    def interactive(self, shell: str | None = None) -> int:
        """exec a genuine interactive shell with PTY, resize and signals intact."""
        remote = "/bin/bash -l" if (shell or "").endswith("/bash") else "/bin/sh -l"
        if shell and shell not in ("/bin/bash", "/usr/bin/bash"):
            remote = "%s -l" % q(shell)
        argv = self.ssh_argv("exec " + remote, batch=False, tty=True)
        os.execvp(argv[0], argv)
        return 127  # unreachable

    # -- verified transfers --------------------------------------------------
    def put(self, local: str, remote: str) -> dict[str, Any]:
        remote = validate_remote_path(remote)
        local = os.path.abspath(local)
        if not os.path.isfile(local):
            raise UsageError("local file not found: %s" % local)
        want = sha256_file(local)
        tmp = "%s.nuxel-tmp-%d-%s" % (remote.rstrip("/"), os.getpid(),
                                      hashlib.sha256(os.urandom(16)).hexdigest()[:8])
        try:
            self._scp(["-p", local, self.remote_spec(tmp)])
            got = self.remote_sha256(tmp)
            if got != want:
                raise TransferFailure("upload checksum mismatch for %s (want %s, got %s)"
                                      % (remote, want, got))
            self._ssh_checked("mv -f %s %s" % (q(tmp), q(remote)))
            final = self.remote_sha256(remote)
            if final != want:
                raise TransferFailure("installed checksum mismatch for %s" % remote)
        except BaseException:
            self._cleanup_remote(tmp)
            raise
        return {"direction": "put", "local": local, "remote": remote,
                "bytes": os.path.getsize(local), "sha256": want, "verified": True}

    def get(self, remote: str, local: str) -> dict[str, Any]:
        remote = validate_remote_path(remote)
        local = os.path.abspath(local)
        os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
        remote_hash = self.remote_sha256(remote)
        fd, tmp = tempfile.mkstemp(prefix=".nuxel-get-", dir=os.path.dirname(local) or ".")
        os.close(fd)
        try:
            self._scp([self.remote_spec(remote), tmp])
            got = sha256_file(tmp)
            if got != remote_hash:
                raise TransferFailure("download checksum mismatch for %s (want %s, got %s)"
                                      % (remote, remote_hash, got))
            os.replace(tmp, local)
            if sha256_file(local) != remote_hash:
                raise TransferFailure("local file changed during install: %s" % local)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return {"direction": "get", "remote": remote, "local": local,
                "bytes": os.path.getsize(local), "sha256": remote_hash,
                "verified": True}

    def remote_sha256(self, remote: str) -> str:
        p = self.run_capture("sha256sum %s 2>/dev/null | cut -d' ' -f1" % q(remote),
                             timeout=30)
        err = classify_ssh_failure(p.returncode, p.stderr or "")
        if err is not None:
            raise err
        value = (p.stdout or "").strip().splitlines()
        if not value or not re.match(r"^[0-9a-f]{64}$", value[-1]):
            raise TransferFailure("remote sha256 unavailable for %s" % remote,
                                  detail=(p.stderr or p.stdout or "")[-1000:])
        return value[-1]

    def _scp(self, args: list[str]) -> None:
        p = self.runner(["scp"] + self.scp_options() + args,
                        capture_output=True, text=True,
                        stdin=subprocess.DEVNULL)
        err = classify_ssh_failure(p.returncode, p.stderr or "")
        if err is not None:
            raise err

    def _ssh_checked(self, command: str) -> None:
        p = self.run_capture(command, timeout=30)
        err = classify_ssh_failure(p.returncode, p.stderr or "")
        if err is not None:
            raise err
        if p.returncode != 0:
            raise TransferFailure("remote command failed (rc=%s): %s"
                                  % (p.returncode, command),
                                  detail=(p.stderr or p.stdout or "")[-1000:])

    def _cleanup_remote(self, path: str) -> None:
        try:
            self.run_capture("rm -f %s" % q(path), timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass

    # -- diagnostics ---------------------------------------------------------
    def diagnose(self) -> dict[str, Any]:
        report = self.preflight()
        doc: dict[str, Any] = {"target": self.target.as_dict() if hasattr(self.target, "as_dict")
                               else self.target.__dict__, "preflight": report.as_dict(),
                               "host_key_fingerprint": self.host_key_fingerprint()}
        if report.status != "AVAILABLE":
            return doc
        probes = {
            "uname": "uname -a",
            "boot_id": "cat /proc/sys/kernel/random/boot_id",
            "id": "id",
            "shell": "getent passwd %s | cut -d: -f7" % q(self.target.user),
            "wlan": "ip -4 -o addr show wlan0 2>/dev/null || true",
            "usb": "ip -4 -o addr show usb0 2>/dev/null || true",
            "sshd": "systemctl is-active sshd.service 2>/dev/null || true",
            "sshd_effective": "sshd -T 2>/dev/null | grep -E '^(passwordauthentication|kbdinteractiveauthentication|allowusers|permitrootlogin) ' || true",
        }
        for key, cmd in probes.items():
            try:
                p = self.run_capture(cmd, timeout=15)
                doc[key] = {"rc": p.returncode,
                            "stdout": (p.stdout or "").strip(),
                            "stderr": (p.stderr or "").strip()}
            except (OSError, subprocess.SubprocessError) as e:
                doc[key] = {"error": str(e)}
        return doc


# --------------------------------------------------------------------------- #
# Deployment / transfer exclusion
# --------------------------------------------------------------------------- #
DEFAULT_GUARD_LOCK = Path(os.environ.get("NUXEL_TRILINK_LOCK",
                                         "/tmp/nuxel-trilink-deploy.lock"))


def guard_owner_path(path: Path) -> Path:
    return Path(str(path) + ".owner.json")


def guard_status(path: Path | str = DEFAULT_GUARD_LOCK) -> dict[str, Any]:
    """Probe the shared Tri-Link guard without ever deleting it."""
    p = Path(path)
    doc: dict[str, Any] = {"path": str(p), "state": "absent"}
    try:
        doc.update(json.loads(guard_owner_path(p).read_text()))
    except (OSError, ValueError):
        pass
    fd = None
    try:
        fd = os.open(p, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
    except PermissionError:
        try:
            fd = os.open(p, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        except FileNotFoundError:
            doc["state"] = "absent"
            return doc
        except OSError:
            doc["state"] = "unknown"
            return doc
    except FileNotFoundError:
        doc["state"] = "absent"
        return doc
    except OSError:
        doc["state"] = "unknown"
        return doc
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            doc["state"] = "free"
        except BlockingIOError:
            doc["state"] = "held"
    finally:
        os.close(fd)
    return doc


class DeploymentGuard:
    """A host-wide mutex for transfers/deployments.

    The existing serial transaction keeps its own port flock.  This guard is
    deliberately a second, *cross-transport* lock: an SSH transfer must not
    stage files while a serial deploy is mutating the same target, and two SSH
    transfers must not race.  It is never used to serialize ordinary shells.
    """

    def __init__(self, path: Path | str = DEFAULT_GUARD_LOCK, *,
                 op: str = "transfer", wait: float = 0.0):
        self.path = Path(path)
        self.op = op
        self.wait = float(wait)
        self.fd: int | None = None
        self.acquired = False

    def __enter__(self) -> "DeploymentGuard":
        self.acquire()
        return self

    def __exit__(self, *exc) -> bool:
        self.release()
        return False

    def acquire(self) -> None:
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | \
            getattr(os, "O_NOFOLLOW", 0)
        try:
            self.fd = os.open(self.path, flags, 0o666)
        except PermissionError:
            try:
                self.fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            except OSError as e:
                raise LockConflict("cannot open Tri-Link guard %s: %s" % (self.path, e))
        except OSError as e:
            raise LockConflict("cannot open Tri-Link guard %s: %s" % (self.path, e))
        deadline = time.monotonic() + max(0.0, self.wait)
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    owner = guard_status(self.path)
                    self._close()
                    raise LockConflict(
                        "another Tri-Link transfer/deploy owns %s (owner=%s op=%s)"
                        % (self.path, owner.get("owner"), owner.get("op")))
                time.sleep(0.05)
        self.acquired = True
        doc = {"pid": os.getpid(), "host": socket.gethostname(), "op": self.op,
               "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "owner": "%s:%d" % (socket.gethostname(), os.getpid())}
        try:
            guard_owner_path(self.path).write_text(json.dumps(doc, sort_keys=True))
        except OSError:
            pass

    def release(self) -> None:
        if self.fd is None:
            return
        try:
            owner = json.loads(guard_owner_path(self.path).read_text())
            if str(owner.get("pid")) == str(os.getpid()):
                guard_owner_path(self.path).unlink(missing_ok=True)
        except (OSError, ValueError):
            pass
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        except OSError:
            pass
        self._close()
        self.acquired = False

    def _close(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None


# --------------------------------------------------------------------------- #
# Serial recovery adapter (delegates; never re-implements the protocol)
# --------------------------------------------------------------------------- #
def find_serial_devices(glob_root: str = "/dev") -> list[str]:
    env = os.environ.get("NUXEL_SERIAL_DEV")
    if env:
        return [env] if os.path.exists(env) else []
    found: list[str] = []
    for pattern in ("ttyACM*", "cu.usbmodem*"):
        found.extend(sorted(str(p) for p in Path(glob_root).glob(pattern)))
    return found


def _serial_lock_owner(dev: str) -> dict[str, Any]:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import nuxel_live as nl  # noqa: WPS433
        return nl.read_lock_owner(dev)
    except Exception as e:  # noqa: BLE001 - status must never crash the manager
        return {"lock_state": "unknown", "error": str(e)}


class SerialAdapter:
    """The existing serial Live Console, called through its proven launcher."""

    def __init__(self, dev: str | None = None, launcher: str | Path = SERIAL_LAUNCHER):
        self.dev = dev or (find_serial_devices()[0] if find_serial_devices() else None)
        self.launcher = Path(launcher)

    def status(self) -> TransportReport:
        checks: list[Check] = []
        checks.append(Check("launcher", "OK" if self.launcher.is_file() else "MISSING",
                            str(self.launcher)))
        if not self.dev:
            return TransportReport("serial", "UNAVAILABLE", detail="no console node",
                                   checks=checks, exit_code=EXIT_UNAVAILABLE)
        checks.append(Check("node", "OK" if os.path.exists(self.dev) else "MISSING",
                            self.dev))
        if not os.path.exists(self.dev):
            return TransportReport("serial", "UNAVAILABLE", self.dev,
                                   detail="console node disappeared", checks=checks,
                                   exit_code=EXIT_UNAVAILABLE)
        owner = _serial_lock_owner(self.dev)
        state = owner.get("lock_state", "unknown")
        checks.append(Check("port-lock", state.upper(),
                            "op=%s pid=%s" % (owner.get("op"), owner.get("pid"))))
        if state == "held":
            return TransportReport("serial", "BUSY", self.dev,
                                   detail="serial console is owned by another process",
                                   checks=checks, exit_code=EXIT_LOCK)
        if state == "unknown":
            return TransportReport("serial", "UNKNOWN", self.dev,
                                   detail="serial lock state unreadable; failing closed",
                                   checks=checks, exit_code=EXIT_LOCK)
        return TransportReport("serial", "AVAILABLE", self.dev,
                               detail="recovery transport (framed commands; not SSH)",
                               checks=checks, exit_code=EXIT_OK)

    def ensure_free(self) -> None:
        owner = _serial_lock_owner(self.dev or "")
        if owner.get("lock_state") in ("held", "unknown"):
            raise LockConflict("serial console %s is busy/unknown (state=%s op=%s pid=%s)"
                               % (self.dev, owner.get("lock_state"),
                                  owner.get("op"), owner.get("pid")))

    def _call(self, args: list[str]) -> int:
        if not self.dev:
            raise TransportUnavailable("no serial console node")
        if not self.launcher.is_file():
            raise TransportUnavailable("serial launcher missing: %s" % self.launcher)
        argv = [str(self.launcher), "--dev", self.dev] + args
        p = subprocess.run(argv)
        return p.returncode

    def run(self, command: str, timeout: float = 20.0, wait_reconnect: float = 0.0) -> int:
        args = ["--run", command, "--timeout", str(timeout)]
        if wait_reconnect:
            args += ["--wait-reconnect", str(wait_reconnect)]
        return self._call(args)

    def pull(self, remote: str, out: str, timeout: float = 20.0) -> int:
        return self._call(["--pull", remote, "--out", out, "--timeout", str(timeout)])

    def batch(self, path: str, timeout: float = 20.0) -> int:
        return self._call(["--batch", path, "--timeout", str(timeout)])

    def deployment_conflict(self) -> dict[str, Any] | None:
        if not self.dev:
            return None
        owner = _serial_lock_owner(self.dev)
        if owner.get("lock_state") != "held":
            return None
        return owner


# --------------------------------------------------------------------------- #
# USB capability audit
# --------------------------------------------------------------------------- #
def parse_kernel_config(text: str) -> dict[str, str]:
    doc: dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and " is not set" in line:
            key = line[2:].split(" is not set", 1)[0].strip()
            doc[key] = "n"
        elif "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            doc[key.strip()] = value.strip().strip('"')
    return doc


def gadget_function_names(root: str | Path = "/sys/kernel/config/usb_gadget") -> dict[str, list[str]]:
    """Map gadget name -> function instance names (e.g. acm.usb0)."""
    out: dict[str, list[str]] = {}
    r = Path(root)
    if not r.is_dir():
        return out
    for gadget in sorted(p for p in r.iterdir() if p.is_dir()):
        fns = gadget / "functions"
        out[gadget.name] = sorted(p.name for p in fns.iterdir() if p.is_dir()) \
            if fns.is_dir() else []
    return out


def gadget_links(root: str | Path = "/sys/kernel/config/usb_gadget") -> list[str]:
    links: list[str] = []
    r = Path(root)
    if not r.is_dir():
        return links
    for gadget in (p for p in r.iterdir() if p.is_dir()):
        cfg_root = gadget / "configs"
        if not cfg_root.is_dir():
            continue
        for cfg in (p for p in cfg_root.iterdir() if p.is_dir()):
            for item in cfg.iterdir():
                if item.is_symlink():
                    links.append(str(item))
    return links


def net_interfaces(root: str | Path = "/sys/class/net") -> list[str]:
    r = Path(root)
    return sorted(p.name for p in r.iterdir()) if r.is_dir() else []


def usb_host_gadget_interface(root: str | Path = "/sys/class/net",
                              vid: str = "18d1", pid: str = "4ee7") -> str | None:
    """Find a host net interface belonging to the Nuxel USB gadget by VID/PID."""
    r = Path(root)
    if not r.is_dir():
        return None
    for iface in sorted(p for p in r.iterdir() if p.is_dir()):
        dev = iface / "device"
        try:
            got_vid = (dev / "idVendor").read_text().strip().lower()
            got_pid = (dev / "idProduct").read_text().strip().lower()
        except OSError:
            continue
        want_vid = vid.lower().replace("0x", "")
        want_pid = pid.lower().replace("0x", "")
        if got_vid.replace("0x", "") == want_vid and got_pid.replace("0x", "") == want_pid:
            return iface.name
    return None


def usb_host_presence(net_root: str | Path = "/sys/class/net") -> tuple[str | None, bool]:
    """(interface, definitive) for the host side.

    Linux sysfs is authoritative: no matching VID/PID interface means the
    current gadget exposes no network function.  Other hosts (macOS) cannot be
    judged from sysfs; return definitive=False so the adapter still probes TCP
    instead of inventing an UNAVAILABLE verdict.
    """
    if sys.platform.startswith("linux"):
        return usb_host_gadget_interface(net_root), True
    return None, False


def usb_capability(kernel_config: str, gadget_root: str | Path = "/sys/kernel/config/usb_gadget",
                   net_root: str | Path = "/sys/class/net") -> dict[str, Any]:
    cfg = parse_kernel_config(kernel_config)
    functions = gadget_function_names(gadget_root)
    links = gadget_links(gadget_root)
    current = sorted({f for names in functions.values() for f in names})
    compiled = {
        "ncm": cfg.get("CONFIG_USB_CONFIGFS_NCM") == "y" and cfg.get("CONFIG_USB_F_NCM") == "y",
        "rndis": cfg.get("CONFIG_USB_CONFIGFS_RNDIS") == "y" and cfg.get("CONFIG_USB_F_RNDIS") == "y",
        "ecm": cfg.get("CONFIG_USB_CONFIGFS_ECM") == "y",
        "ecm_subset": cfg.get("CONFIG_USB_CONFIGFS_ECM_SUBSET") == "y",
        "eem": cfg.get("CONFIG_USB_CONFIGFS_EEM") == "y",
        "configfs": cfg.get("CONFIG_USB_CONFIGFS") == "y",
        "dwc3": cfg.get("CONFIG_USB_DWC3") == "y" or "CONFIG_USB_DWC3_DUAL_ROLE" in cfg,
    }
    has_net_function = any(n.startswith(("ncm.", "rndis.", "ecm.", "eem.")) for n in current)
    host_iface = usb_host_gadget_interface(net_root)
    if not compiled["configfs"] or not compiled["dwc3"]:
        status = "BLOCKED_KERNEL"
    elif not (compiled["ncm"] or compiled["rndis"] or compiled["ecm"]):
        status = "BLOCKED_KERNEL"
    elif host_iface:
        status = "AVAILABLE"
    elif has_net_function:
        status = "FUNCTION_PRESENT_NO_HOST_IFACE"
    else:
        status = "SUPPORTED_NOT_ENABLED"
    return {
        "status": status,
        "compiled": compiled,
        "functions": functions,
        "links": links,
        "current_functions": current,
        "host_gadget_interface": host_iface,
        "interfaces": net_interfaces(net_root),
        "preferred_mode": ("ncm" if compiled["ncm"] else
                           ("rndis" if compiled["rndis"] else
                            ("ecm" if compiled["ecm"] else None))),
    }


def read_kernel_config(path: str | Path = "/proc/config.gz") -> str:
    p = Path(path)
    try:
        if p.suffix == ".gz":
            import gzip
            with gzip.open(p, "rt", errors="replace") as fh:
                return fh.read()
        return p.read_text(errors="replace")
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# Reconnect classification
# --------------------------------------------------------------------------- #
def classify_reconnect(boot_before: str | None, boot_after: str | None,
                       sshd_entered_before: str | None,
                       sshd_entered_after: str | None) -> str:
    """Distinguish a phone reboot, an sshd restart and a network/USB loss.

    A new boot id is proof of a reboot.  The same boot id with a changed sshd
    ActiveEnterTimestamp is a service restart.  Otherwise the transport (Wi-Fi,
    route or USB re-enumeration) was lost while the phone stayed up.
    """
    if boot_before and boot_after and boot_before != boot_after:
        return "phone_reboot"
    if sshd_entered_before and sshd_entered_after and \
            sshd_entered_before != sshd_entered_after:
        return "sshd_restart"
    return "transport_loss"


# --------------------------------------------------------------------------- #
# Discovery and explicit auto selection
# --------------------------------------------------------------------------- #
def load_config(path: str | Path | None = None) -> dict[str, Any]:
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.append(Path.home() / ".config" / "nuxel" / "live-ssh.json")
    candidates.append(REPO_ROOT / "configs" / "nuxel" / "live-ssh.json")
    for p in candidates:
        try:
            doc = json.loads(p.read_text())
            if isinstance(doc, dict):
                doc["_source"] = str(p)
                return doc
        except (OSError, ValueError):
            continue
    return {}


def discover_ssh_reports(*, wlan_host: str | None, usb_host: str | None,
                         user: str, port: int, key: Path, known_hosts: Path,
                         host_key_alias: str, check_network: bool = True,
                         usb_available: bool | None = None,
                         adapter_factory: Callable[..., SshAdapter] = SshAdapter
                         ) -> list[TransportReport]:
    reports: list[TransportReport] = []
    for transport, host in (("wlan", wlan_host), ("usb", usb_host)):
        if transport == "usb" and usb_available is False:
            reports.append(TransportReport(
                transport, "UNAVAILABLE", detail=(
                    "no Nuxel USB network interface on this host; the current "
                    "gadget exposes only CDC-ACM serial (usb0/ncm0/rndis0 absent)")))
            continue
        if not host:
            reports.append(TransportReport(
                transport, "UNAVAILABLE", detail="target not supplied (never guessed)"))
            continue
        try:
            target = SshTarget(transport, host, user=user, port=port, key=key,
                               known_hosts=known_hosts,
                               host_key_alias=host_key_alias)
            adapter = adapter_factory(target)
            reports.append(adapter.preflight(check_network=check_network))
        except TriLinkError as e:
            reports.append(TransportReport(transport, "INVALID", host, user,
                                           str(e), exit_code=e.exit_code))
    return reports


def select_auto(reports: Sequence[TransportReport],
                preference: Sequence[str] = ("wlan", "usb")) -> TransportReport | None:
    """Choose one AVAILABLE SSH transport.  Never fall back after selection."""
    by_name = {r.transport: r for r in reports}
    for name in preference:
        r = by_name.get(name)
        if r and r.status == "AVAILABLE":
            return r
    return None


def format_discovery(reports: Sequence[TransportReport],
                     selected: TransportReport | None,
                     serial: TransportReport | None = None) -> str:
    lines = ["# auto discovery (explicit; no silent fallback)"]
    for r in reports:
        lines.append("#   " + r.line())
        for c in r.checks:
            if c.status not in ("OK",):
                lines.append("#     %-12s %-12s %s" % (c.name, c.status, c.detail))
    if serial is not None:
        lines.append("#   " + serial.line())
        if serial.status != "AVAILABLE":
            lines.append("#     serial recovery is currently not available")
    if selected is not None:
        lines.append("# selected: %s -> %s" % (selected.transport, selected.target))
    else:
        lines.append("# selected: none (serial recovery remains the explicit fallback)")
    return "\n".join(lines)
