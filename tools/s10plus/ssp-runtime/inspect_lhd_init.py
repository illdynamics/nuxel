#!/usr/bin/env python3
"""Read-only, hash-bound extraction of the matched lhd initializer dispatch.

These are static binary facts, NOT a firmware protocol implementation. The
handler labels were correlated with the daemon's own adjacent log strings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

EXPECTED = '6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe'
LABELS = [
    'FD_REQUEST_DOWNLOAD', 'FD_WAIT4AUTOBAUD', 'FD_SENT_AUTOBAUD',
    'waiting/default dispatch', 'FD_GOT_SYNC', 'FD_TIMEOUT_SYNC',
    'FD_GOT_SYNC_INIT', 'FD_WAIT4VERSION_INIT', 'FD_GOT_VERSION_INIT',
    'FD_ROMRESET', 'FD_WAIT4DOWNLOAD_START', 'FD_WAIT4DOWNLOAD_COMPLETE',
    'FD_WAIT4APP', 'FD_GOT_SYNC_CONFIRM', 'FD_WAIT4VERSION_CONFIRM',
    'FD_GOT_VERSION_CONFIRM',
]


def inspect(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED:
        raise ValueError('not the reviewed G975FXXS9DTK9 lhd; offsets are not portable')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    entsize, count = struct.unpack_from('<HH', data, 54)

    def read(va, size):
        for i in range(count):
            typ, _, off, addr, _, filesz, _, _ = struct.unpack_from(
                '<IIQQQQQQ', data, phoff + i * entsize)
            if typ == 1 and addr <= va and va + size <= addr + filesz:
                return data[off + va - addr:off + va - addr + size]
        raise ValueError('unmapped virtual address')

    targets = struct.unpack('<16H', read(0xdfc4, 32))
    # ELF64 SHT_RELA entries carry the callback addresses as addends. Reading
    # raw pointer slots alone misses the dynamic loader's relocation contract.
    shoff = struct.unpack_from('<Q', data, 40)[0]
    shentsize, shcount = struct.unpack_from('<HH', data, 58)
    callback_refs = []
    callback_targets = {0x39b9c, 0x39d08, 0x39d00, 0x39e64}
    for i in range(shcount):
        section = struct.unpack_from('<IIQQQQIIQQ', data, shoff + i * shentsize)
        if section[1] != 4:  # SHT_RELA
            continue
        for off in range(section[4], section[4] + section[5], section[9]):
            slot, info, addend = struct.unpack_from('<QQq', data, off)
            if info == 1027 and addend in callback_targets:  # RELATIVE, symbol 0
                callback_refs.append({'slot_va': hex(slot), 'target_va': hex(addend)})
    return {
        'kind': 'STATIC BINARY ANALYSIS', 'hardware_verified': False,
        'binary_sha256': digest, 'dispatch_va': '0x389fc',
        'state_member_offset': 1256, 'table_va': '0xdfc4',
        'states': [{'state': i + 1, 'handler_va': hex(0x38a48 + 4 * offset),
                    'log_label': LABELS[i]} for i, offset in enumerate(targets)],
        'done_state': 17,
        'sync_initial_constants': list(struct.unpack('<II', read(0xde38, 8))),
        'sync_confirmation_constants': list(struct.unpack('<II', read(0xde60, 8))),
        'version_callback_gates': {
            'normal_callback_va': '0x39b9c', 'extended_callback_va': '0x39d08',
            'transitions': {'8': 9, '15': 16},
            'other_states': 'unexpected-version log; no state advance',
            'pre_gate_writes': {
                'owner_pointer_member_offset': 24,
                'owner_fields': {'2320': 'argument w1', '2324': 'argument w2',
                                 '2328': 'argument w3',
                                 '2332': 'argument w2 only when old value is 0xffffffff'},
                'normal_callback_extra_write': {
                    'pointer_member_offset': 32, 'field_offset': 18832,
                    'value': 'argument w1'},
                'normal_store_range': ['0x39c34', '0x39c68'],
                'extended_store_range': ['0x39d8c', '0x39db4'],
                'implication': 'unexpected state does not imply no metadata mutation'},
            'relative_relocations': callback_refs,
            'adjustor_thunks': {
                '0x39d00': 'subtract 16 from x0; tail branch to 0x39b9c',
                '0x39e64': 'subtract 16 from x0; tail branch to 0x39d08'},
            'scope': 'callback control flow, not verified on-wire RPC decoding'},
        'unverified': ['RPC reply schemas and dispatch validation',
                       'internal sync payload and ACK ordering',
                       'memory-write completion and retry/abort semantics',
                       'timer virtual methods and units',
                       'reset/power sequencing and later Android dependencies'],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    args = ap.parse_args()
    print(json.dumps(inspect(args.binary), indent=2))


if __name__ == '__main__':
    main()
