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


class MatchedImage:
    """Minimal ELF64 reader shared by static inspection and offline emulation."""

    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.digest = hashlib.sha256(self.data).hexdigest()
        if self.digest != EXPECTED:
            raise ValueError('not the reviewed G975FXXS9DTK9 lhd; offsets are not portable')
        phoff = struct.unpack_from('<Q', self.data, 32)[0]
        entsize, count = struct.unpack_from('<HH', self.data, 54)
        self.segments = []
        for i in range(count):
            typ, flags, off, addr, _, filesz, memsz, _ = struct.unpack_from(
                '<IIQQQQQQ', self.data, phoff + i * entsize)
            if typ == 1:
                self.segments.append((addr, memsz, self.data[off:off + filesz], flags))
        self.relocations = {}
        shoff = struct.unpack_from('<Q', self.data, 40)[0]
        entsize, count = struct.unpack_from('<HH', self.data, 58)
        for i in range(count):
            s = struct.unpack_from('<IIQQQQIIQQ', self.data, shoff + i * entsize)
            if s[1] == 4:
                for off in range(s[4], s[4] + s[5], s[9]):
                    slot, info, addend = struct.unpack_from('<QQq', self.data, off)
                    if info == 1027:
                        self.relocations[slot] = addend

    def read(self, va, size):
        for addr, _, data, _ in self.segments:
            if addr <= va and va + size <= addr + len(data):
                return data[va - addr:va - addr + size]
        raise ValueError('unmapped virtual address')


def response_path(image):
    """Reviewed facts, bound to this binary, not a live-operation validator."""
    ranges = {
        'callback_installation': (0x388a8, 0x388ec),
        'registration': (0x389bc, 0x389c8),
        'rpc_list': (0x3e740, 0x3e884),
        'rpc_dispatch_and_postcheck': (0x3e884, 0x3e9b0),
        'version_decoder': (0x3d1a8, 0x3d364),
        'callbacks': (0x39b9c, 0x39e6c),
        'reader': (0x41000, 0x41224),
        'transport_receive': (0x3fe80, 0x40508),
        'transport_crc': (0x40f90, 0x41000),
        'transport_constructor': (0x3edb8, 0x3eed4),
        'rpc_transport_installation': (0x3e250, 0x3e358),
        'rpc_constructor_call': (0x349a8, 0x34a18),
        'rpc_constructor_reinit': (0x37198, 0x37204),
        'initializer_and_cancel': (0x389fc, 0x396ac),
        'completion_and_timer_methods': (0x37508, 0x37944),
        'patch_asic_getter': (0x3c75c, 0x3c76c),
        'timer_poll': (0x35990, 0x359c8),
        'cached_clock_update': (0x3507c, 0x35098),
        'platform_installation': (0x27530, 0x275f4),
        'platform_clock': (0x26290, 0x262b0),
        'singleton_installation': (0x210b0, 0x2114c),
        'clock_forwarder': (0x228d8, 0x228dc),
        'android_clock_wrapper': (0x1f6e4, 0x1f76c),
        'ready_notification': (0x265b0, 0x26640),
        'sync_start_and_scheduler': (0x3f0fc, 0x3f3d8),
        'internal_message_decoder': (0x407f0, 0x40b10),
        'sync_interface_forwarders': (0x3ebac, 0x3ec30),
        'sync_platform_init_branch': (0x37f88, 0x37fc0),
        'sync_initializer_callback': (0x396ac, 0x3970c),
        'sync_start_wrapper': (0x3e3a4, 0x3e3f0),
        'version_request_encoder': (0x3cd5c, 0x3cda4),
        'rpc_send_builder': (0x3e408, 0x3e740),
        'rpc_transaction': (0x3ec30, 0x3ed54),
        'rpc_writer_constructor': (0x41224, 0x41250),
        'reliable_enqueue_and_ring_allocate': (0x3fa24, 0x3fe80),
        'reliable_ring_free_and_pending': (0x3ef6c, 0x3f0fc),
        'reliable_ack_nack': (0x4050c, 0x407f0),
        'unreliable_send': (0x3f994, 0x3fa24),
        'patch_supply': (0x399fc, 0x39b9c),
        'patch_metadata_getters': (0x3c74c, 0x3c79c),
        'scratch_start_encoder': (0x3cee0, 0x3cf30),
        'service_start_encoder': (0x3cff8, 0x3d0b8),
        'writer_scalar_and_span': (0x41250, 0x413e8),
        'skip_confirmation_getter': (0x387f0, 0x38800),
        'queue_capacity': (0x40f3c, 0x40f90),
    }
    return {
        'confidence': 'STATIC_VERIFIED against exact matched ELF',
        'transport_and_hardware_verified': False,
        'download_completion': {
            'confidence': 'STATIC_VERIFIED / OFFLINE_EMULATED; staged consumed-patch metadata only',
            'pending_count': 'transport+0x3508 counts reliable payload bytes, not firmware-operation responses',
            'enqueue': '0x3fa24 allocates bounded ring descriptor/data, adds length, sends flags 2',
            'ack': '0x4050c searches queued u8 sequence; retires prefix through match; subtracts payload lengths before callbacks',
            'nack': '0x40674 matches packet sequence; retires prefix through reported reliable base and resends suffix',
            'retries': '0x3f1f8 retries at 500ms or resend flag; attempts 10 calls communication-error callback without locally draining queue',
            'state_12': '0x38cdc -> supply 0x399fc -> pending 0x3e3f0 -> 0x3f0f4; zero branches to 0x39038',
            'patch_supply': 'requires >=2048 ring capacity, reads at most 512 patch bytes per loop; after supply compares local checksum byte',
            'scratch': {'patch_type': '0x41', 'encoder': '0x3cee0', 'rpc_id': 46,
                        'body': 'LE32 entry', 'transport_flags': 0, 'delay_ms': 40},
            'service': {'patch_type': 'other reviewed branch', 'encoder': '0x3cff8', 'rpc_id': 55,
                        'body': 'LE32 entry then four zero LE32 words', 'transport_flags': 0, 'delay_ms': 100},
            'entry_ffffffff': 'skips start request; enters state 15 and requests version over reliable queue',
            'normal_continuation': 'state 13 -> confirmation sync with destination 14 and five restart credits',
            'skip_confirmation': 'interface+48 -> 0x387f0 reads core+18808; true chooses state 16 directly; not assumed enabled',
            'not_proven': ['firmware memory-write acceptance', 'ROM execution', 'live ACK identity',
                           'patch validation and record decoding', 'higher-level error recovery'],
        },
        'internal_sync': {
            'confidence': 'STATIC_VERIFIED and OFFLINE_EMULATED; synthetic replies only',
            'dispatch_table': {'va': '0xe0dd', 'base': '0x4084c',
                               'targets': [hex(0x4084c + 4*n) for n in image.read(0xe0dd, 6)]},
            'request': '0x3f0fc -> 0x3f3d8(flags=0x300, payload=[0, token])',
            'response': {'opcode': 1, 'exact_length': 8,
                         'fields': ['opcode', 'token', 'next_packet_minus_one', 'discarded',
                                    'reliable_send_base', 'received_packet_base',
                                    'next_reliable_receive', 'discarded'],
                         'order': 'bounded reads; error/remaining check; active and token check; mutations; callback',
                         'mutations': {'0xc56': '(byte2+1) mod 256', '0x34f0': '(byte4+1) mod 256',
                                       '0x34f1': 'byte4', '0x428': 'byte5',
                                       '0x431': '(byte6-1) mod 256', '0x432': 0, '0x434_u16': 0,
                                       '0x350d_sync_active': False}},
            'call_graph': ['0x407f0 -> interface +64 -> 0x3ec18',
                           'RPC outer interface +56 -> 0x37f88',
                           'core+18812 == 3 -> core+15808 -> 0x396ac',
                           'initializer state 4 -> 5 on true / 6 on false -> 0x389fc',
                           '5 -> saved destination 7 or 14; timer 0ms',
                           '7/14 -> 8/15; RPC ID 0 empty body; reliable enqueue; timer 250ms'],
            'relocations': {'0x48eb0': hex(image.relocations[0x48eb0]),
                            '0x487f8': hex(image.relocations[0x487f8])},
            'retry': '100ms interval, tokens 1..6, then false; initializer has 5 restart credits',
            'version_retry': 'initial request plus 5 retries at 250ms; exhaustion reaches assertion helper',
            'session_limit': 'new sync attempt resets token to 1; no cross-attempt nonce in reviewed path',
            'cancel_limit': '0x39684 unregisters RPC handler, but does not clear transport sync active',
            'replay_boundaries': ['raw autobaud write', 'transport send', 'reliable enqueue',
                                  'assertion helper (stops replay; real failure effects NOT emulated)',
                                  'main-core modes other than 3'],
        },
        'registration': '0x389c4 -> 0x3e9b0 adds owner+0x4c0 to RPC handler list',
        'handler_vtable': {'base': '0x48ad0', 'dispatch_slot': '0x48ae0',
                           'dispatch_target': hex(image.relocations[0x48ae0])},
        'callback_interface': {'subobject_offset': 16, 'vtable': '0x48b10',
                               'normal_slot': '0x48b20', 'extended_slot': '0x48b28'},
        'rpc_ids': {
            '3': {'compare_va': '0x3d1dc', 'fields': ['LE32 w1', 'LE32 w2', 'LE32 w3'],
                  'callback_call_va': '0x3d234', 'thunk': '0x39d00'},
            '59': {'compare_va': '0x3d1c8',
                   'fields': ['LE32 w1', 'LE32 w2', 'LE32 w3', 'LE32 w4',
                              'u8 length + bytes x5', 'LE32 w6', 'u8 length + bytes x7'],
                   'callback_call_va': '0x3d314', 'thunk': '0x39e64'},
            '4': {'compare_va': '0x3d1d4', 'fields': ['LE32 w1'],
                  'callback_call_va': '0x3d33c', 'target': '0x18050 (returns)'},
        },
        'reader': {'vtable': hex(image.relocations[0x49598] + 16),
                   'u8': '0x410cc', 'LE32': '0x41168', 'span': '0x411e4',
                   'failure': 'sets byte +36; scalar returns 0 without advancing cursor',
                   'span_failure': 'sets error but returns current pointer without advancing'},
        'validation_order': [
            '0x3e740 prewalk checks aggregate RPC record lengths before dispatch',
            'prewalk reads header bytes before proving each byte lies in supplied extent',
            '0x3e884 constructs bounded reader and calls registered handlers',
            '0x3d1a8 reads fields then invokes callback without checking reader error',
            'callback mutates metadata and may advance state / call initializer',
            '0x3e924..0x3e95c checks remaining length/error AFTER callback returns',
        ],
        'not_present_in_reviewed_rpc_path': ['request token', 'session identity',
                                             'duplicate suppression', 'CRC check'],
        'scope_limit': 'Transport CRC/sequence/internal routing is upstream; not bypassed by this claim.',
        'transport': {
            'call_graph': ['0x3e2f4 -> 0x3fe80', '0x3fe84 escaped byte parser',
                           '0x3ffbc -> 0x40098 complete frame',
                           '0x404fc interface +0x30 -> 0x3ebfc -> 0x3e740'],
            'crc': '0x400ec..0x40124: minimum 4 bytes; CRC over bytes 1..length-2; nibble swap',
            'length': '0x40318..0x4032c: all flags consumed and remaining body equals payload size',
            'packet_sequence': '0x40330..0x40370: mismatch updates statistics, not payload rejection',
            'reliable': '0x403bc..0x40490: seq/CRC/length duplicate check, next-sequence acceptance, ACK/NACK send',
            'duplicate_option': {
                'offset': '0x3521', 'default_at_both_reviewed_constructor_calls': False,
                'evidence': ['0x349d4', '0x371a0', '0x3ee88', '0x40408', '0x4046c'],
                'meaning': 'when true, also delivers duplicate/out-of-order reliable payloads'},
            'internal_route': '0x404ac..0x404bc routes internal flag to 0x407f0 instead of RPC',
            'session_identity': 'no session token in reviewed receive path; sync resets still need review',
            'replay_boundaries': ['send', 'reliable ACK/NACK processing', 'internal-message processing'],
        },
        'final_verification': {
            'interface_vtable': '0x48720',
            'completion_method': hex(image.relocations[0x48730]),
            'diagnostic_method': hex(image.relocations[0x48738]),
            'timer_method': hex(image.relocations[0x48740]),
            'state_16': '0x38e44; owner+2345 selects confirmation-only success or patch ASIC comparison',
            'normal_comparison': '0x39328: for low24(ASIC)==0x4775b0 compare patch ASIC to 0x4775b0; otherwise full ASIC equality',
            'legacy_exception': '0x39208: original version 0x36a07 and ASIC 0x4774a0 accepts patch ASIC 0x4774a1',
            'done': '0x394f4 reports boolean result; 0x39504 enters 17 for BOTH results and schedules +1',
            'cleanup': '0x38c8c clears state and +2340, then unregisters handler',
            'cancel': '0x39684 similarly clears state/+2340 and unregisters; no metadata/power restoration here',
            'ready': 'success at 0x37508 with platform+18808 nonzero -> platform interface +64 -> 0x265b0 -> BBD:PassThru=0 then ESW:READY; intervening calls still need review',
        },
        'timer': {
            'set': '0x37908: negative int32 disables; otherwise uint32 deadline=cached_time+delay, active=1',
            'poll': '0x35990: signed(deadline-cached_time)<=0 clears active then calls 0x396a8 -> initializer',
            'clock_path': ['0x3507c -> platform interface +24 (0x47af8 -> 0x26290)',
                           '0x26290 -> singleton 0x210b0; vtable 0x47688 +152 (0x47720 -> 0x228d8)',
                           '0x228d8 -> 0x1f6e4 -> android::elapsedRealtime'],
            'units': 'milliseconds; matched libutils and AOSP source evidence recorded separately',
            'caution': '100 passed at 0x391d4 is diagnostic progress, not this timer method',
        },
        'evidence_ranges': {name: {'start': hex(a), 'end_exclusive': hex(b),
                                  'sha256': hashlib.sha256(image.read(a, b-a)).hexdigest()}
                            for name, (a, b) in ranges.items()},
    }


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
        'response_path': response_path(MatchedImage(path)),
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
        'unverified': ['physical ROM/application response identity and end-to-end session correlation',
                       'sync interaction with pending reliable queue and real device timing',
                       'memory-write completion and retry/abort semantics',
                       'reset/power sequencing and later Android dependencies'],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    args = ap.parse_args()
    print(json.dumps(inspect(args.binary), indent=2))


if __name__ == '__main__':
    main()
