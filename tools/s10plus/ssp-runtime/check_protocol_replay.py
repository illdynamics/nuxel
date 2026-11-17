#!/usr/bin/env python3
"""Exercise source-backed framing through the native decoder, without devices.

All inputs are SIMULATED. This tests decoding/rejection, never firmware ACKs
or physical samples. No runtime root, sysfs, device path or socket is needed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def frame(body):
    # Independent MSB-first polynomial implementation, not the production table.
    crc = 0
    for byte in body[1:]:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ (0x4d if crc & 128 else 0)) & 255
    raw = body + bytes([((crc << 4) | (crc >> 4)) & 255])
    escaped = bytearray(b'\xb0\x00')
    for byte in raw:
        escaped.extend({0xb0: b'\xb0\x03', 0x11: b'\xb0\x04',
                        0x13: b'\xb0\x05'}.get(byte, bytes([byte])))
    return bytes(escaped) + b'\xb0\x01'


def cases():
    ack = frame(bytes([7, 0, 5, 42, 9]))
    return [
        ('packet-and-reliable-ack', ack, 0, 1),
        ('reliable-nack', frame(bytes([8, 0, 8, 8])), 0, 1),
        ('repeated-ack-observation-only', ack * 2, 0, 2),
        ('internal-not-rpc', frame(bytes([10, 1, 128, 1, 0, 255])), 0, 1),
        ('extended-size', frame(bytes([0, 4, 64, 1]) + bytes(260)), 0, 1),
        ('missing-detail', frame(bytes([9, 0, 1])), 2, 0),
        ('unknown-flag', frame(bytes([9, 0, 128, 4, 0])), 2, 0),
        ('surplus-payload', frame(bytes([9, 0, 0, 0])), 2, 0),
        ('truncated-rpc', frame(bytes([9, 3, 0, 1, 2, 0])), 2, 0),
        ('bad-crc', ack[:-3] + bytes([ack[-3] ^ 1]) + ack[-2:], 2, 0),
        ('unfinished-frame', ack[:-2], 2, 0),
        ('restart-partial', b'\xb0\x00\x99\x20\x00' + ack, 0, 1),
    ]


def run(decoder):
    results = []
    for name, wire, status, packets in cases():
        proc = subprocess.run([str(decoder), '--replay-stdin'], input=wire,
                              capture_output=True, timeout=3)
        output = proc.stdout.decode(errors='replace')
        passed = (proc.returncode == status and
                  f'OFFLINE REPLAY: packets={packets} ' in output and
                  'hardware_verified=false' in output)
        results.append({'name': name, 'input_sha256': hashlib.sha256(wire).hexdigest(),
                        'returncode': proc.returncode, 'passed': passed,
                        'stdout': output, 'stderr': proc.stderr.decode(errors='replace')})
    return {'kind': 'SIMULATED framing replay', 'hardware_verified': False,
            'operation_completion_verified': False,
            'decoder_sha256': hashlib.sha256(decoder.read_bytes()).hexdigest(),
            'passed': all(r['passed'] for r in results), 'cases': results}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--decoder', required=True, type=Path)
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    result = run(args.decoder.resolve(strict=True))
    print(json.dumps({k: result[k] for k in ("kind", "passed", "hardware_verified",
                                             "operation_completion_verified")}
                     if args.summary else result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
