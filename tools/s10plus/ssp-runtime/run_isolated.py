#!/usr/bin/env python3
"""Run one bounded Android lhd startup trial with NO handset device access.

Run on the AArch64 handset, not on the host. All runtime files are read-only;
the vendor process sees fresh PID/network/IPC namespaces, private temporary
storage and pseudo devices only. There is deliberately no hardware mode.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import stat
import subprocess
import time


def verify(root):
    root = root.resolve(strict=True)
    manifest_path = root / "sha256-manifest.json"
    if not stat.S_ISREG(manifest_path.lstat().st_mode):
        raise ValueError("manifest must be a regular file")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("manifest must be a nonempty file/hash mapping")
    for rel, expected in manifest.items():
        path = root / rel
        if (Path(rel).is_absolute() or ".." in Path(rel).parts or
                Path(rel).as_posix() != rel or rel == "sha256-manifest.json"):
            raise ValueError("unsafe manifest path: " + rel)
        if not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError("missing/escaping runtime file: " + rel)
    # The entire root is bound into the sandbox, so checking only the listed
    # files leaves unlisted loader configs/libraries and symlinks unaudited.
    actual = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError("symlink or special runtime file: " + str(path))
            if stat.S_ISREG(mode) and path != manifest_path:
                actual.add(path.relative_to(root).as_posix())
    if actual != set(manifest):
        raise ValueError("unlisted runtime files: " + ", ".join(sorted(actual - set(manifest))))
    for rel, expected in manifest.items():
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != expected:
            raise ValueError("runtime checksum mismatch: " + rel)
    return manifest


def sandbox(root, bwrap, probe=False, logs=None, stock_namespaces=False):
    args = [bwrap, "--unshare-all", "--die-with-parent", "--new-session",
            "--uid", "65534", "--gid", "65534", "--cap-drop", "ALL",
            "--ro-bind", str(root), "/", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--dir", "/tmp/nv", "--dir", "/tmp/log",
            "--tmpfs", "/data", "--dir", "/data/ssp-private",
            "--clearenv", "--setenv", "PATH", "/system/bin",
            "--setenv", "ANDROID_ROOT", "/system", "--setenv", "ANDROID_DATA", "/data",
            "--setenv", "LD_LIBRARY_PATH", ("/vendor/lib64" if stock_namespaces else
             "/system/lib64:/vendor/lib64:/apex/com.android.runtime/lib64/bionic"),
            "--setenv", "LD_PRELOAD", ("/vendor/lib64/libssp-log-stderr.so" if stock_namespaces
                              else "/system/lib64/libssp-log-stderr.so"),
            "--chdir", "/tmp"]
    if logs is not None:
        args += ["--bind", str(logs), "/logs"]
    return args + ["--"] + (
                ["/isolation-probe"] if probe else
                ["/vendor/bin/hw/lhd", "/vendor/etc/sensor/lhd-isolated.conf"])


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--bwrap", default="/opt/nuxel-bwrap011/bwrap")
    ap.add_argument("--seconds", type=int, default=8, choices=range(1, 21))
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--stock-namespaces", action="store_true",
                    help="use staged stock ld.config.txt and VNDK libraries")
    args = ap.parse_args()
    if platform.machine() != "aarch64" or os.geteuid() != 0:
        ap.error("requires root on the AArch64 target")
    root = args.root.resolve(strict=True)
    manifest = verify(root)
    required = ["isolation-probe"] if args.probe else [
        "vendor/bin/hw/lhd", "vendor/etc/sensor/lhd-isolated.conf", "system/bin/linker64",
        ("vendor/lib64/libssp-log-stderr.so" if args.stock_namespaces else
         "system/lib64/libssp-log-stderr.so")]
    if args.stock_namespaces:
        required.append("system/etc/ld.config.txt")
    if any(p not in manifest for p in required):
        ap.error("required trial files absent from integrity manifest")
    for name in ("proc", "dev", "tmp", "data", "logs"):
        if not (root / name).is_dir():
            ap.error("missing sandbox mountpoint: " + name +
                     " (create empty directories in the staging root before the trial)")
    args.output.mkdir(parents=True, exist_ok=False)
    logs = args.output.resolve() / "logs"
    logs.mkdir()
    with open("/run/nuxel-ssp-isolated.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cmd = sandbox(root, args.bwrap, args.probe, logs, args.stock_namespaces)
        trace = ["/usr/bin/strace", "-f", "-s", "160", "-o", str(args.output / "syscalls.log"),
                 "-e", "trace=%file,%process,%network,read,write,ioctl,prctl", "--"]
        start = time.monotonic()
        timed_out = False
        with (args.output / "stdout.log").open("wb") as log:
            p = subprocess.Popen(trace + cmd, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, preexec_fn=limits)
            try:
                p.wait(timeout=args.seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(timeout=2)
        result = {"kind": "isolation-probe" if args.probe else "lhd-no-devices",
                  "elapsed_seconds": round(time.monotonic() - start, 3),
                  "returncode": p.returncode, "timed_out": timed_out,
                  "hardware_devices_exposed": [], "sensor_success": False,
                  "command": cmd}
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return 0 if timed_out and not args.probe else p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
