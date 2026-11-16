#!/usr/bin/env python3
"""Read-only S10+ modem evidence collector (TWRP ADB or Nuxel SSH).

It never reads modem/EFS partitions, SIM identifiers, calibration, or private
keys; never opens modem control nodes; and never writes to the phone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone

REMOTE_SCRIPT = r'''#!/bin/sh
set +e
section() { printf '\n===== %s =====\n' "$1"; }
section IDENTITY
uname -a
printf 'model='; tr -d '\000' </proc/device-tree/model 2>/dev/null
printf '\ncompatible='; tr '\000' ' ' </proc/device-tree/compatible 2>/dev/null; printf '\n'
section MODEM_DEVICE_NODES
for p in /dev/umts_boot0 /dev/umts_ipc0 /dev/umts_ipc1 /dev/umts_rfs0 /dev/umts_dm0 /dev/umts_cass /dev/umts_csd /dev/cbd0 /dev/cbd1; do
  if [ -e "$p" ]; then stat -c '%n type=%F major_minor=%t:%T mode=%a uid=%u gid=%g' "$p" 2>/dev/null || ls -l "$p"; fi
done
section NETWORK_INTERFACES
for p in /sys/class/net/rmnet* /sys/class/net/wwan* /sys/class/net/pdp* /sys/class/net/rev_rmnet*; do
  [ -e "$p" ] || continue
  n=${p##*/}; printf '%s ' "$n"
  for f in operstate carrier type; do [ -r "$p/$f" ] && printf '%s=%s ' "$f" "$(cat "$p/$f" 2>/dev/null)"; done
  printf '\n'
done
ip -brief link show 2>/dev/null
section KERNEL_CONFIG
if [ -r /proc/config.gz ]; then
  zcat /proc/config.gz 2>/dev/null | grep -E '^CONFIG_(SEC_SIPC_MODEM_IF|SEC_MODEM_S5000AP|UMTS_MODEM_S5000AP|LINK_DEVICE_SHMEM|LINK_DEVICE_NAPI|CP_ZEROCOPY|CP_SECURE_BOOT|MODEM_IF_NET_GRO)=' || true
else
  echo '/proc/config.gz unavailable'
fi
section MODEM_KERNEL_LOG
(dmesg 2>/dev/null | grep -iE 's5000ap|modem_probe|modemctl|modem_v1|shmem|SIPC|umts_|rmnet|cpif|mailbox' | tail -n 180) || true
section MODEMMANAGER
if command -v mmcli >/dev/null 2>&1; then
  mmcli --version 2>&1
  mmcli -L 2>&1
else
  echo 'mmcli not installed'
fi
for d in /usr/lib64/ModemManager/plugins /usr/lib/ModemManager/plugins /usr/libexec/ModemManager; do
  if [ -d "$d" ]; then echo "plugin_dir=$d"; find "$d" -maxdepth 1 -type f -printf '%f %s bytes\n' 2>/dev/null | sort; fi
done
section SERVICES
if command -v systemctl >/dev/null 2>&1; then
  systemctl is-active ModemManager.service NetworkManager.service 2>&1
  systemctl --no-pager --full status ModemManager.service 2>&1 | head -n 35
else
  echo 'systemd unavailable (expected in some recovery environments)'
fi
if command -v nmcli >/dev/null 2>&1; then nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2>&1; fi
section NUXEL_DIAGNOSTIC
if command -v nuxel-modem-diag.sh >/dev/null 2>&1; then
  nuxel-modem-diag.sh status --json 2>&1
elif [ -x /usr/local/bin/nuxel-modem-diag.sh ]; then
  /usr/local/bin/nuxel-modem-diag.sh status --json 2>&1
else
  echo 'nuxel-modem-diag.sh unavailable'
fi
section PROTECTED_PARTITION_POLICY
printf '%s\n' 'Collector did not access modem, efs, efsg, sec_efs, persist, param, carrier, or NV/calibration partitions.'
printf '%s\n' 'Collector did not read SIM identifiers or issue modem control ioctls.'
'''

IDENTIFIER_RE = re.compile(
    r'(?i)\b(IMEI|IMSI|ICCID|MSISDN|ESN|MEID|PIN|PUK|SPN|SERIAL(?:NO)?)\b'
    r'(\s*[:=]\s*|\s+)([A-Z0-9*#-]{4,})'
)
LONG_DIGITS_RE = re.compile(r'(?<![0-9A-Fa-f])\d{14,20}(?![0-9A-Fa-f])')


def redact(text: str) -> str:
    text = IDENTIFIER_RE.sub(lambda m: f'{m.group(1)}{m.group(2)}[REDACTED]', text)
    return LONG_DIGITS_RE.sub('[REDACTED-LONG-NUMBER]', text)


def run_remote(args: argparse.Namespace) -> tuple[str, str]:
    if args.transport == 'adb':
        proc = subprocess.run(['adb', 'devices', '-l'], text=True, capture_output=True, check=False)
        serials = []
        for line in proc.stdout.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 2 and fields[1] == 'device':
                serials.append(fields[0])
        if args.serial:
            if args.serial not in serials:
                raise RuntimeError(f'ADB serial {args.serial!r} is not an online device; online={serials!r}')
            serial = args.serial
        else:
            if len(serials) != 1:
                raise RuntimeError(f'expected exactly one online ADB device, found {serials!r}; pass --serial')
            serial = serials[0]
        cmd = ['adb', '-s', serial, 'shell', 'sh', '-s']
        result = subprocess.run(cmd, input=REMOTE_SCRIPT, text=True, capture_output=True, check=False)
        meta = f'adb serial={serial} profile={args.profile}'
    else:
        if not args.target:
            raise RuntimeError('--target is required for --transport ssh')
        key = os.path.expanduser(args.key)
        if not os.path.isfile(key):
            raise RuntimeError(f'SSH identity file not found: {key}')
        cmd = ['ssh', '-i', key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
               args.target, 'sh', '-s']
        result = subprocess.run(cmd, input=REMOTE_SCRIPT, text=True, capture_output=True, check=False)
        meta = f'ssh target={args.target} profile={args.profile}'
    output = result.stdout + (('\n[stderr]\n' + result.stderr) if result.stderr.strip() else '')
    return meta, redact(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=('adb', 'ssh'), default='adb')
    parser.add_argument('--profile', choices=('twrp', 'nuxel'), default='twrp',
                        help='label only; collection remains read-only')
    parser.add_argument('--serial', help='ADB serial when more than one device is online')
    parser.add_argument('--target', default='root@192.168.178.167',
                        help='SSH target (default: root@192.168.178.167)')
    parser.add_argument('--key', default='~wicked/.ssh/wicked_wqn_id_rsa',
                        help='SSH identity path; never copied or printed')
    parser.add_argument('--output', default='./modem-evidence')
    args = parser.parse_args()

    try:
        meta, evidence = run_remote(args)
    except (OSError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report = outdir / f's10plus-modem-evidence-{stamp}.txt'
    header = (
        'Nuxel S10+ modem evidence (read-only)\n'
        f'Collected UTC: {stamp}\nTransport: {meta}\n'
        'Privacy: long numeric identifiers and labelled SIM/device identifiers redacted.\n'
        'Scope: no protected partition access; no modem-control ioctl; no SIM identifier read.\n'
        'This is evidence collection only, not proof of an active cellular service.\n\n'
    )
    data = header + evidence
    report.write_text(data, encoding='utf-8')
    digest = hashlib.sha256(data.encode('utf-8')).hexdigest()
    manifest = {
        'schema_version': 1,
        'collected_utc': stamp,
        'transport': meta,
        'profile': args.profile,
        'report': report.name,
        'sha256': digest,
        'read_only': True,
        'protected_partition_access': False,
        'sim_identifiers_collected': False,
        'modem_control_ioctls_issued': False,
    }
    manifest_path = outdir / f's10plus-modem-evidence-{stamp}.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {report}')
    print(f'Wrote {manifest_path}')
    print(f'SHA-256 {digest}')
    if '[stderr]' in evidence or 'not installed' in evidence:
        print('Collection finished with one or more unavailable commands; inspect the evidence file.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
