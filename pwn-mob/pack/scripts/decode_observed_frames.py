#!/usr/bin/env python3
"""Offline structural decoder of two *reported* Stage 05 messages.

Not a general authenticated Samsung protocol decoder. Never touches hardware.
The data comes from user-reported sanitized captures, not independent verification.
"""
import argparse
import json
from pathlib import Path
import struct

FMT_SAMPLE = bytes.fromhex(
    '19 00 00 00 13 05 03 0f 00 0d 0a 41 53 54 5f 50 4f 57 45 52 4f 4e 0d 0a 00'
)
RFS_SAMPLE = bytes.fromhex(
    '19 00 00 00 0b 01 0f 00 00 00 44 45 4c 45 54 45 5f 41 4c 4c 5f 56 49 53 00'
)


def fmt_record(frame: bytes) -> dict:
    if len(frame) < 7:
        return {'ok': False, 'error': 'underflow: <7 byte reported inner FMT header'}
    declared = struct.unpack_from('<H', frame, 0)[0]
    if declared != len(frame):
        return {'ok': False, 'error': 'inner FMT total-length mismatch',
                'declared_length': declared, 'observed_length': len(frame)}
    # Only fields demonstrated by the reported Nuxel Stage 05 FMT parser.
    result = {'ok': True, 'type': 'reported_inner_fmt', 'observed_length': len(frame),
              'declared_length': declared, 'payload_length': len(frame) - 7,
              'main': f'0x{frame[4]:02x}', 'sub': f'0x{frame[5]:02x}',
              'message_type': f'0x{frame[6]:02x}',
              'semantics': 'UNKNOWN, except user-reported AST_POWERON boot notification'}
    if frame == FMT_SAMPLE:
        result['matches_known_reported_sample'] = True
    return result


def rfs_record(frame: bytes) -> dict:
    if len(frame) < 10:
        return {'ok': False, 'error': 'underflow: <10 byte proposed RFS fields'}
    declared = struct.unpack_from('<I', frame, 0)[0]
    if declared != len(frame):
        return {'ok': False, 'error': 'proposed RFS total-length mismatch',
                'declared_length': declared, 'observed_length': len(frame)}
    width_field = struct.unpack_from('<H', frame, 6)[0]
    data = frame[10:]
    # A printable label is a clue, not proof of operation semantics.
    printable = bool(data) and data[-1] == 0 and all(32 <= b <= 126 for b in data[:-1])
    text = data[:-1].decode('ascii') if printable else None
    risk = 'REVIEW/DENY: potential destructive semantics' if text and text.startswith('DELETE') else 'UNKNOWN: no action authorized'
    result = {'ok': True, 'type': 'reported_rfs_candidate',
              'observed_length': len(frame), 'declared_length': declared,
              'byte4': f'0x{frame[4]:02x}', 'byte5': f'0x{frame[5]:02x}',
              'le16_at_6': width_field, 'bytes8_9': frame[8:10].hex(),
              'label_if_printable': text, 'safe_handling': risk,
              'response_semantics': 'UNKNOWN; do not send ACK or mutate filesystem'}
    if frame == RFS_SAMPLE:
        result['matches_known_reported_sample'] = True
    return result


def self_test() -> None:
    a = fmt_record(FMT_SAMPLE)
    b = rfs_record(RFS_SAMPLE)
    assert a['ok'] and a['payload_length'] == 18
    assert (a['main'], a['sub'], a['message_type']) == ('0x13', '0x05', '0x03')
    assert b['ok'] and b['le16_at_6'] == 15 and b['label_if_printable'] == 'DELETE_ALL_VIS'
    for bad in (b'', b'\x00' * 6, FMT_SAMPLE[:-1], b'\x00' * 2040):
        assert not fmt_record(bad)['ok']
    for bad in (b'', b'\x00' * 9, RFS_SAMPLE[:-1], b'\xff' * 2040):
        assert not rfs_record(bad)['ok']


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test', action='store_true')
    group.add_argument('--samples', action='store_true')
    group.add_argument('--hex', help='Hex bytes for OFFLINE analysis')
    group.add_argument('--input-file', type=Path, help='OFFLINE hex text file')
    p.add_argument('--kind', choices=('fmt', 'rfs'), help='Required with --hex')
    args = p.parse_args()
    if args.self_test:
        self_test()
        print('PASS: 12 reported-vector and negative-boundary assertions')
        return
    if args.samples:
        output = {'fmt': fmt_record(FMT_SAMPLE), 'rfs': rfs_record(RFS_SAMPLE)}
    else:
        if args.kind is None:
            p.error('--kind fmt|rfs required for custom input')
        raw = args.input_file.read_text(encoding='utf-8') if args.input_file else args.hex
        if raw is None:
            p.error('--hex needs a value or use --samples')
        try:
            value = bytes.fromhex(raw)
        except ValueError as e:
            p.error(f'invalid hex input: {e}')
        output = fmt_record(value) if args.kind == 'fmt' else rfs_record(value)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
