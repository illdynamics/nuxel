#!/usr/bin/env python3
"""Nuxel ADB recovery flasher: fail-closed, raw images, independently verifiable.

Requires: Python 3.9+ and platform-tools adb. No third-party Python dependencies.
Everything defaults to read-only unless --action flash is explicitly requested.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BLOCK = 1024 * 1024
SAFE_PARTITION = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SAFE_SERIAL = re.compile(r"^[a-zA-Z0-9:._-]+$")
SAFE_DEVICE = re.compile(r"^/dev/block/(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+$")
DENY = {"recovery", "dtb", "dtbo", "vbmeta", "efs", "sec_efs", "persist", "persistent", "modem", "radio", "bootloader", "sboot", "abl", "xbl", "xbl_config", "tz", "rpm", "hyp", "cm", "keydata", "keyrefuge", "keystorage", "param", "misc", "frp", "super"}

class Abort(Exception):
    pass


def run(argv: list[str], *, check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as ex:
        raise Abort(f"Command failed: {argv[0]}: {ex}") from ex
    if check and p.returncode != 0:
        raise Abort(f"Command exited {p.returncode}: {' '.join(argv[:3])}: {p.stderr.decode('utf-8', 'replace')[-600:]}")
    return p


class Adb:
    def __init__(self, serial: str):
        self.serial = serial
        self.base = ["adb", "-s", serial]

    def shell(self, command: str, *, check: bool = True, timeout: int = 35) -> str:
        p = run(self.base + ["shell", command], check=check, timeout=timeout)
        return p.stdout.decode("utf-8", "replace").strip().replace("\r", "")

    def prop(self, name: str) -> str:
        return self.shell(f"getprop {name}", check=False).strip()


def find_adb_serial(requested: str | None) -> str:
    p = run(["adb", "devices"], timeout=25)
    found = []
    for line in p.stdout.decode('utf-8', 'replace').splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("device", "recovery"):
            found.append(parts[0])
    if requested:
        if not SAFE_SERIAL.fullmatch(requested):
            raise Abort("Invalid ADB serial")
        if requested not in found:
            raise Abort(f"ADB device {requested} not available; connected={found}")
        return requested
    if len(found) != 1:
        raise Abort(f"Expected exactly one accessible ADB device, found {found}. Use --serial.")
    return found[0]


def ensure_root_recovery(adb: Adb, profile: str) -> dict:
    state = adb.shell("id -u")
    if state != "0":
        raise Abort(f"ADB shell must be root (uid=0); got: {state}")
    props = {
        "serial": adb.serial,
        "device": adb.prop("ro.product.device"),
        "model": adb.prop("ro.product.model"),
        "twrp": adb.prop("ro.twrp.version"),
        "slot_suffix": adb.prop("ro.boot.slot_suffix") or adb.prop("ro.boot.slot"),
        "bootmode": adb.prop("ro.bootmode"),
    }
    if not props['twrp'] and 'recovery' not in props['bootmode'].lower():
        devices_line = run(["adb", "devices"]).stdout.decode('utf-8', 'replace')
        if f"{adb.serial}\trecovery" not in devices_line:
            raise Abort("Not positively identified as recovery (TWRP/ADB recovery); writes disabled.")
    if profile == 's10plus' and props['device'].lower() != 'beyond2lte':
        raise Abort(f"S10+ profile requires beyond2lte, saw {props['device']!r}")
    if profile == 'g7power' and props['device'].lower() != 'ocean':
        raise Abort(f"G7 Power profile requires ocean, saw {props['device']!r}")
    return props


def get_byname(adb: Adb) -> list[str]:
    out = []
    for directory in ['/dev/block/by-name', '/dev/block/bootdevice/by-name', '/dev/block/platform/13d60000.ufs/by-name']:
        res = adb.shell(f"ls -l {directory} 2>/dev/null", check=False)
        if res and (' -> ' in res):
            out.append(f"=== {directory} ===\n{res}")
    return out


def select_parts(args: argparse.Namespace, props: dict) -> tuple[str, str | None]:
    # `is True` (not bool()) so partially-specified test namespaces never count as boot-only.
    boot_only = getattr(args, 'boot_only', False) is True
    bp = args.boot_partition or ('boot' if args.profile == 's10plus' else None)
    if boot_only:
        # BOOT-only mode: the rootfs target is not used at all (USERDATA untouched).
        rp = None
    else:
        rp = args.rootfs_partition or ('userdata' if args.profile == 's10plus' else None)
    if not bp or (not rp and not boot_only):
        raise Abort("Partition names must be explicit for this profile: --boot-partition and --rootfs-partition. No G7 guesses.")
    for part in ([bp] + ([rp] if rp else [])):
        if not SAFE_PARTITION.fullmatch(part):
            raise Abort(f"Invalid partition name {part!r}: use by-name entries, e.g. boot_a or userdata")
        if part in DENY or part.startswith(('modem_', 'vbmeta_', 'dtbo_', 'recovery_', 'bootloader_')):
            raise Abort(f"Blocked high-risk partition {part!r}. Only BOOT and explicitly selected rootfs targets allowed.")
    if (rp is not None and bp == rp) or not re.fullmatch(r'boot(?:_[ab])?', bp):
        raise Abort("Boot target must be boot, boot_a, or boot_b and distinct from rootfs target.")
    if rp is not None and not re.fullmatch(r'(?:userdata|system(?:_[ab])?)', rp):
        raise Abort("Rootfs target must be explicitly selected: userdata, system, system_a, or system_b.")
    if args.profile == 's10plus' and (bp != 'boot' or (rp is not None and rp != 'userdata')):
        raise Abort('For s10plus, only the confirmed boot and userdata layout is enabled.')
    if args.profile == 'g7power':
        active = props.get('slot_suffix', '').lower().replace('_', '')
        if active not in ('a', 'b'):
            raise Abort('G7 Power A/B slot unknown. Query getprop ro.boot.slot_suffix and use a recovery that exposes it.')
        if bp != f'boot_{active}':
            raise Abort(f"G7 Power active slot is {active}; select --boot-partition boot_{active}. Inactive-slot writes blocked.")
        if rp and rp.endswith(('_a', '_b')) and not rp.endswith('_'+active):
            raise Abort(f"G7 Power active slot is {active}; rootfs target {rp} belongs to the other slot.")
    return bp, rp


def resolve_partition(adb: Adb, name: str) -> tuple[str, int]:
    candidate = None
    for directory in ('/dev/block/by-name', '/dev/block/bootdevice/by-name', '/dev/block/platform/13d60000.ufs/by-name'):
        path = f'{directory}/{name}'
        ok = adb.shell(f'test -b {path} && echo FOUND', check=False)
        if ok == 'FOUND':
            candidate = path
            break
    if not candidate:
        raise Abort(f"Partition {name!r} not found as a block device in supported by-name locations")
    actual = adb.shell(f'readlink -f {candidate}', check=False)
    if not SAFE_DEVICE.fullmatch(actual):
        raise Abort(f"Unexpected partition resolution: {candidate} -> {actual!r}")
    size_text = adb.shell(f'blockdev --getsize64 {actual}', check=False)
    if size_text.isdigit():
        size = int(size_text)
    else:
        # /sys/class/block/<kernel-name>/size reports 512-byte sectors.
        kernel_name = actual.rsplit('/', 1)[-1]
        sectors = adb.shell(f'cat /sys/class/block/{kernel_name}/size', check=False)
        if not sectors.isdigit():
            raise Abort(f"Can't verify size of {name}: blockdev and sysfs both unavailable")
        size = int(sectors) * 512
    if size <= 0:
        raise Abort(f"Invalid reported capacity for {name}: {size}")
    return actual, size


def inspect_image(path: Path, role: str) -> dict:
    if not path.is_file():
        raise Abort(f"Missing {role} image: {path}")
    size = path.stat().st_size
    if size == 0:
        raise Abort(f"Empty {role} image")
    h = hashlib.sha256()
    with path.open('rb') as f:
        header = f.read(4096)
        f.seek(0)
        while True:
            data = f.read(8 * BLOCK)
            if not data: break
            h.update(data)
    if header[:4] == b'\x3a\xff\x26\xed':
        raise Abort(f"{role} is an Android sparse image. Convert to raw first; never dd sparse images directly.")
    if role == 'boot' and not header.startswith(b'ANDROID!'):
        raise Abort('BOOT must start with ANDROID! (Android boot image); refusing unknown format.')
    if role == 'rootfs' and header[1080:1082] != b'\x53\xef':
        raise Abort('Rootfs must be raw ext4 (magic absent at superblock offset 0x438).')
    return {"path": str(path.resolve()), "bytes": size, "sha256": h.hexdigest(), "type": 'android-boot' if role == 'boot' else 'ext4'}


def relevant_mounts(adb: Adb, root_part: str, root_real: str) -> list[str]:
    mounts = adb.shell('cat /proc/mounts')
    bad = []
    for line in mounts.splitlines():
        fields = line.split()
        if len(fields) < 2: continue
        device, mountpoint = fields[:2]
        if device == root_real or device.endswith('/' + root_part):
            bad.append(line)
        if root_part.startswith('userdata') and (mountpoint == '/data' or mountpoint.startswith(('/data/', '/sdcard', '/storage/emulated', '/mnt/user'))):
            bad.append(line)
        if root_part.startswith('system') and (mountpoint in ('/system', '/system_root') or mountpoint.startswith(('/system/', '/system_root/'))):
            bad.append(line)
    return sorted(set(bad))


def check_images_fit(parts: dict, images: dict):
    # Only validate the roles actually supplied (BOOT-only mode supplies no rootfs).
    for role in [r for r in ('boot', 'rootfs') if r in images and r in parts]:
        expected = images[role]['bytes']
        capacity = parts[role]['capacity']
        if expected > capacity:
            raise Abort(f"{role} image ({expected} bytes) EXCEEDS target partition ({capacity} bytes)")


def remote_dump(adb: Adb, actual: str, bytecount: int, out_file: Path, label: str, compare_hash: str | None = None) -> str:
    blocks = math.ceil(bytecount / BLOCK)
    command = f'dd if={actual} bs={BLOCK} count={blocks} 2>/dev/null'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    read_count = 0
    # Capture stderr to avoid deadlock, stream stdout in chunks; never load partitions into memory.
    with tempfile.TemporaryFile() as stderr_buf:
        proc = subprocess.Popen(adb.base + ['exec-out', command], stdout=subprocess.PIPE, stderr=stderr_buf)
        try:
            with out_file.open('wb') as dest:
                while True:
                    chunk = proc.stdout.read(BLOCK)
                    if not chunk: break
                    if read_count < bytecount:
                        wanted = chunk[:bytecount - read_count]
                        digest.update(wanted)
                        dest.write(wanted)
                        read_count += len(wanted)
        finally:
            proc.stdout.close()
        code = proc.wait()
        stderr_buf.seek(0)
        errors = stderr_buf.read(2000).decode('utf-8','replace')
    if code != 0 or read_count != bytecount:
        out_file.unlink(missing_ok=True)
        raise Abort(f"{label} readback failed: adb_exit={code}, received={read_count}, expected={bytecount}, stderr={errors[-500:]}")
    result = digest.hexdigest()
    if compare_hash and compare_hash != result:
        raise Abort(f"{label} MISMATCH! expected {compare_hash}, readback {result}. Do not reboot.")
    return result


def verify_partition(adb: Adb, real: str, img: dict, label: str) -> str:
    # No persistent 4 GiB duplicate on Mac: temp file is sparse? Instead use temp file,
    # removed automatically. Stream to SHA-256 with a 1MiB bounded memory buffer.
    expected = img['sha256']
    size = img['bytes']
    blocks = math.ceil(size / BLOCK)
    command = f'dd if={real} bs={BLOCK} count={blocks} 2>/dev/null'
    digest = hashlib.sha256()
    read_count = 0
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(adb.base + ['exec-out', command], stdout=subprocess.PIPE, stderr=errors)
        try:
            while True:
                chunk = proc.stdout.read(BLOCK)
                if not chunk: break
                if read_count < size:
                    need = chunk[:size-read_count]
                    digest.update(need)
                    read_count += len(need)
        finally:
            proc.stdout.close()
        code = proc.wait()
        errors.seek(0)
        err = errors.read(800).decode('utf-8','replace')
    actual = digest.hexdigest()
    if code != 0 or read_count != size:
        raise Abort(f"{label} readback INCOMPLETE: exit={code} bytes={read_count}/{size} {err}")
    if actual != expected:
        raise Abort(f"{label} SHA256 MISMATCH\n expected: {expected}\n   actual: {actual}\nDO NOT REBOOT.")
    print(f"  VERIFIED {label}: {actual} ({size:,} bytes)", flush=True)
    return actual


def transfer_image(adb: Adb, path: Path, device: str, expected_size: int, label: str) -> None:
    print(f"  FLASHING {label}: {expected_size:,} bytes -> {device}", flush=True)
    cmd = f'dd of={device} bs={BLOCK} && sync'
    with path.open('rb') as img, tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(adb.base + ['shell', '-T', cmd], stdin=subprocess.PIPE,
                                stdout=errors, stderr=errors)
        total = 0
        try:
            while True:
                chunk = img.read(BLOCK)
                if not chunk: break
                proc.stdin.write(chunk)
                total += len(chunk)
                if total // (256*BLOCK) != (total-len(chunk)) // (256*BLOCK):
                    print(f"    sent {total / (1024**3):.2f} GiB", flush=True)
            proc.stdin.close()
        except BrokenPipeError as ex:
            proc.stdin.close()
            proc.wait()
            errors.seek(0)
            raise Abort(f"ADB pipe closed while flashing {label}: {errors.read(1000).decode('utf-8','replace')}") from ex
        code = proc.wait()
        errors.seek(0)
        log = errors.read(2000).decode('utf-8','replace')
    if code != 0 or total != expected_size:
        raise Abort(f"FLASH FAILED {label}: adb_exit={code} transferred={total}/{expected_size}: {log[-700:]}")
    print(f"    write command completed; doing mandatory full readback...", flush=True)


def confirm_write(serial: str, boot: str, root: str | None):
    msg = f'FLASH {serial} {boot} {root}' if root else f'FLASH {serial} {boot}'
    print("\nWRITING WILL OVERWRITE THE SELECTED PARTITIONS.", flush=True)
    if root == 'userdata':
        print('USERDATA includes Android data and internal storage. Back up anything important before continuing.')
    print('Required exact phrase:', msg)
    typed = input('Type phrase to authorize writes: ').strip()
    if typed != msg:
        raise Abort('Confirmation phrase did not match; no writes performed')
    if root == 'userdata':
        loss = input('Type ERASE-USERDATA to acknowledge data loss: ').strip()
        if loss != 'ERASE-USERDATA':
            raise Abort('USERDATA deletion not authorized; no writes performed')


def save_json(path: Path, doc: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description='ADB recovery BOOT + rootfs flashing with backup and full SHA256 readback')
    ap.add_argument('--action', choices=['discover', 'preflight', 'backup', 'flash', 'verify'], default='preflight')
    ap.add_argument('--profile', choices=['s10plus', 'g7power', 'generic'], default='generic')
    ap.add_argument('--serial', help='ADB serial; mandatory if several phones attached')
    ap.add_argument('--boot', type=Path, help='Raw Android BOOT .img')
    ap.add_argument('--rootfs', type=Path, help='Raw ext4 rootfs .img')
    ap.add_argument('--boot-partition', help='Exact /dev/block/by-name NAME, e.g. boot or boot_a')
    ap.add_argument('--rootfs-partition', help='Exact NAME, e.g. userdata or system_a')
    ap.add_argument('--backup-dir', type=Path, default=Path.cwd()/'backups'/'nuxel-adb')
    ap.add_argument('--execute', action='store_true', help='Required for --action flash; interactive double-confirmation still required')
    ap.add_argument('--boot-only', action='store_true',
                    help='Flash/verify ONLY the BOOT partition; no rootfs image required and USERDATA is never touched')
    ap.add_argument('--backup-recovery', action='store_true', help='Also save recovery if independent recovery partition exists')
    args = ap.parse_args(argv)
    serial = find_adb_serial(args.serial)
    adb = Adb(serial)
    props = ensure_root_recovery(adb, args.profile)
    print(f"Device: {serial} model={props['model']} codename={props['device']} TWRP={props['twrp'] or '-'} slot={props['slot_suffix'] or 'none'}")
    if args.action == 'discover':
        print('\n'.join(get_byname(adb)) or '(No by-name symlinks listed)')
        print('\n=== MOUNTS ===\n' + adb.shell('cat /proc/mounts'))
        print('\n=== PARTITIONS ===\n' + adb.shell('cat /proc/partitions'))
        return 0
    boot_name, root_name = select_parts(args, props)
    boot_real, boot_capacity = resolve_partition(adb, boot_name)
    parts = {'boot': {'name': boot_name, 'device': boot_real, 'capacity': boot_capacity}}
    print(f"BOOT:   {boot_name} -> {boot_real} size={boot_capacity:,} bytes")
    root_real = None
    if root_name:
        root_real, root_capacity = resolve_partition(adb, root_name)
        if boot_real == root_real:
            raise Abort('BOOT and rootfs resolve to same physical device')
        parts['rootfs'] = {'name': root_name, 'device': root_real, 'capacity': root_capacity}
        print(f"ROOTFS: {root_name} -> {root_real} size={root_capacity:,} bytes")
        mounted = relevant_mounts(adb, root_name, root_real)
        if mounted:
            raise Abort('Rootfs partition or data/system mount appears active:\n' + '\n'.join(mounted) + '\nUnmount safely using recovery before proceeding.')
    else:
        print("BOOT-ONLY: no rootfs target; USERDATA will not be touched.", flush=True)
    images = {}
    if args.action in ('preflight', 'flash', 'verify'):
        if not args.boot:
            raise Abort('--boot image path is required for this action')
        images = {'boot': inspect_image(args.boot, 'boot')}
        if args.boot_only:
            if args.rootfs:
                print('NOTE: --boot-only given; --rootfs is ignored and USERDATA is not touched.', flush=True)
        else:
            if not args.rootfs:
                raise Abort('Both --boot and --rootfs image paths are required unless --boot-only is set')
            images['rootfs'] = inspect_image(args.rootfs, 'rootfs')
        check_images_fit(parts, images)
        for role in ('boot', 'rootfs'):
            if role in images:
                print(f"IMAGE {role}: {images[role]['path']} {images[role]['bytes']:,} bytes sha256={images[role]['sha256']}")
    if args.action == 'preflight':
        print('\nPREFLIGHT PASS: no bytes written; this does not establish device-tree or boot compatibility.')
        return 0
    session = args.backup_dir / f"{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{serial}"
    if args.action in ('backup', 'flash'):
        if args.action == 'flash' and not args.execute:
            raise Abort('--action flash requires --execute. No writes performed.')
        if args.action == 'flash':
            confirm_write(serial, boot_name, root_name)
        session.mkdir(parents=True, exist_ok=False)
        receipt = {'device': props, 'partitions': parts, 'images': images, 'action': args.action,
                   'boot_only': bool(args.boot_only),
                   'date_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'state': 'STARTED'}
        save_json(session/'receipt.json', receipt)
        print(f"BACKING UP BOOT to Mac: {session}", flush=True)
        try:
            orig_hash = remote_dump(adb, boot_real, boot_capacity, session/'boot-before.img', 'BOOT backup')
            receipt['boot_backup_sha256'] = orig_hash
            if args.backup_recovery:
                recovery_real, recovery_size = resolve_partition(adb, 'recovery')
                if recovery_real in (boot_real, root_real):
                    raise Abort('Recovery resolves to a flashing target; refusing backup ambiguity')
                receipt['recovery_backup_sha256'] = remote_dump(adb, recovery_real, recovery_size,
                                                               session/'recovery-before.img', 'RECOVERY backup')
            receipt['state'] = 'BACKUPS_COMPLETE'
            save_json(session/'receipt.json', receipt)
            print('BACKUP COMPLETE. Keep originals on the Mac, not on USERDATA.', flush=True)
            if args.action == 'backup': return 0
            # Rootfs first, readback first. Never write BOOT when rootfs verification fails.
            if 'rootfs' in images:
                transfer_image(adb, args.rootfs, root_real, images['rootfs']['bytes'], 'ROOTFS')
                receipt['state'] = 'ROOTFS_WRITTEN_UNVERIFIED'
                save_json(session/'receipt.json', receipt)
                receipt['rootfs_readback_sha256'] = verify_partition(adb, root_real, images['rootfs'], 'ROOTFS')
                receipt['state'] = 'ROOTFS_VERIFIED'
                save_json(session/'receipt.json', receipt)
            else:
                receipt['state'] = 'ROOTFS_SKIPPED_BOOT_ONLY'
                save_json(session/'receipt.json', receipt)
            transfer_image(adb, args.boot, boot_real, images['boot']['bytes'], 'BOOT')
            receipt['state'] = 'BOOT_WRITTEN_UNVERIFIED'
            save_json(session/'receipt.json', receipt)
            receipt['boot_readback_sha256'] = verify_partition(adb, boot_real, images['boot'], 'BOOT')
            receipt['state'] = 'FLASH_AND_READBACK_VERIFIED'
            save_json(session/'receipt.json', receipt)
            print('\nPASS: every written partition matches its local image by full SHA256 readback.')
            print('NO AUTOMATIC REBOOT. Hardware boot / display remain unverified.')
            return 0
        except (Abort, KeyboardInterrupt) as ex:
            receipt['state'] = 'INTERRUPTED_OR_FAILED'
            receipt['error'] = str(ex)
            save_json(session/'receipt.json', receipt)
            raise
    if args.action == 'verify':
        if 'rootfs' in images:
            verify_partition(adb, root_real, images['rootfs'], 'ROOTFS')
        verify_partition(adb, boot_real, images['boot'], 'BOOT')
        print('PASS: full readback SHA256 matches. No writes performed.')
        return 0
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Abort, KeyboardInterrupt) as ex:
        print(f"\nSTOP: {ex}", file=sys.stderr)
        sys.exit(2)
