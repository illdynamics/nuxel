#!/usr/bin/env python3
"""Execute hash-bound lhd RPC decoder/callback instructions in Unicorn only.

All input is SYNTHETIC. No ELF process, syscall, socket, device or firmware is
executed. This is NOT an MCU simulator or proof of a valid firmware response.
Initializer continuation, diagnostic logging and locks are explicit boundaries.
Requires unicorn==2.1.4; no Android runtime or pyelftools dependency.
"""
import argparse
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2
from unicorn.arm64_const import UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_PC
from unicorn.arm64_const import UC_ARM64_REG_TPIDR_EL0
from inspect_lhd_init import MatchedImage

OWNER, PLATFORM, RPC, INPUT = 0x100000, 0x110000, 0x120000, 0x130000
STACK, TLS, STUBS = 0x200000, 0x300000, 0x310000
RETURN, DIAG, LOCK = STUBS, STUBS + 4, STUBS + 8
ALLOWED = ((0x3e740, 0x3e9b0), (0x3d1a8, 0x3d364),
           (0x39b9c, 0x39e6c), (0x41000, 0x41224),
           (0x3e2f4, 0x3e358), (0x3ebfc, 0x3ec04),
           (0x3fe80, 0x40508), (0x40f90, 0x41000))


def rpc_record(rpc_id, body):
    """Synthetic RPC-list fixture, not a transmitted request or ROM response."""
    def field(value):
        if not 0 <= value <= 0x7fff:
            raise ValueError('RPC field exceeds 15 bits')
        return bytes([value]) if value < 128 else bytes([0x80 | value >> 8, value & 255])
    return field(rpc_id) + field(len(body)) + body


class Replay:
    def __init__(self, binary, state=0, original_version=0xffffffff,
                 deliver_reliable_duplicates=False):
        self.image = MatchedImage(binary)
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        # File-backed contents plus RELATIVE relocations, all offline.
        self.uc.mem_map(0, 0x60000)
        for addr, _, data, _ in self.image.segments:
            self.uc.mem_write(addr, data)
        for slot, value in self.image.relocations.items():
            self.put64(slot, value)
        for addr, size in ((OWNER, 0x10000), (PLATFORM, 0x10000),
                           (RPC, 0x10000), (INPUT, 0x10000),
                           (STACK, 0x10000), (TLS, 0x1000), (STUBS, 0x1000)):
            self.uc.mem_map(addr, size)
        self.uc.mem_write(STUBS, bytes.fromhex('c0035fd6') * 3)
        # Equivalent reviewed callback subobjects installed at 0x388a8..0x388e8.
        self.put64(OWNER + 0x4c0, 0x48ad0)
        self.put64(OWNER + 0x4c8, 0)
        self.put64(OWNER + 0x4d0, 0x48b10)
        self.put64(OWNER + 0x4d8, OWNER)
        self.put64(OWNER + 0x4e0, PLATFORM)
        self.put32(OWNER + 1256, state)
        self.put32(OWNER + 2332, original_version)
        self.put64(RPC, PLATFORM)
        # Constructor 0x3e250 supplies this interface to the transport at +24.
        self.put64(RPC + 8, 0x48e70)
        self.put64(RPC + 16, RPC)
        self.put64(RPC + 24 + 8, RPC + 8)
        # Reviewed constructor defaults (0x3edb8), with explicit caller option.
        self.uc.mem_write(RPC + 24 + 0x428, b'\xff')
        self.uc.mem_write(RPC + 24 + 0x431, b'\xff')
        self.uc.mem_write(RPC + 24 + 0x3521, bytes([bool(deliver_reliable_duplicates)]))
        self.put64(RPC + 0x3540, OWNER + 0x4c0)
        self.uc.mem_write(RPC + 0x3d71, b'\x01')
        self.put64(PLATFORM, PLATFORM + 0x100)
        self.put64(PLATFORM + 0x130, DIAG)
        self.put64(PLATFORM + 0x140, LOCK)
        self.events = []
        self.input_len = 0
        self.uc.hook_add(UC_HOOK_CODE, self._code)
        self.uc.hook_add(UC_HOOK_MEM_READ, self._read)

    def put64(self, addr, value):
        self.uc.mem_write(addr, struct.pack('<Q', value))

    def put32(self, addr, value):
        self.uc.mem_write(addr, struct.pack('<I', value))

    def word(self, addr):
        return struct.unpack('<I', self.uc.mem_read(addr, 4))[0]

    def _return(self):
        self.uc.reg_write(UC_ARM64_REG_PC, self.uc.reg_read(UC_ARM64_REG_X30))

    def _read(self, uc, access, addr, size, value, user):
        if INPUT <= addr < INPUT + 0x10000 and addr + size > INPUT + self.input_len:
            self.events.append({'kind': 'read_past_supplied_input',
                                'pc': hex(uc.reg_read(UC_ARM64_REG_PC)),
                                'offset': addr - INPUT, 'size': size})

    def _code(self, uc, addr, size, user):
        if addr == RETURN:
            uc.emu_stop()
            return
        if addr == 0x34d78:  # logging predicate: disabled, no formatting/string dereference
            uc.reg_write(UC_ARM64_REG_X0, 0)
            self._return()
            return
        boundaries = {0x3f3d8: 'transport_send_boundary',
                      0x4050c: 'reliable_ack_handler_boundary',
                      0x40674: 'reliable_nack_handler_boundary',
                      0x407f0: 'internal_message_boundary'}
        if addr in boundaries:
            self.events.append({'kind': boundaries[addr],
                                'w1': uc.reg_read(UC_ARM64_REG_X1) & 0xffffffff})
            self._return()
            return
        if addr in (DIAG, LOCK, 0x18050, 0x389fc):
            kind = {DIAG: 'postcheck_or_envelope_diagnostic', LOCK: 'lock_stub',
                    0x18050: 'empty_method', 0x389fc: 'initializer_boundary'}[addr]
            self.events.append({'kind': kind, 'state': self.word(OWNER + 1256)})
            self._return()
            return
        if not any(a <= addr < b for a, b in ALLOWED):
            raise RuntimeError(f'unreviewed execution at {addr:#x}')
        instruction = bytes(uc.mem_read(addr, 4))
        # Reject all exception-generating instructions, including SVC.
        if struct.unpack('<I', instruction)[0] & 0xff000000 == 0xd4000000:
            raise RuntimeError('exception/syscall instruction forbidden')
        if addr in (0x39b9c, 0x39d08):
            self.events.append({'kind': 'version_callback', 'pc': hex(addr),
                                'arguments': [uc.reg_read(UC_ARM64_REG_X1 + i) & 0xffffffff
                                              for i in range(3)],
                                'state_before': self.word(OWNER + 1256)})
        if addr in (0x3e924, 0x3e940):
            self.events.append({'kind': 'post_callback_check' if addr == 0x3e924 else 'reader_error',
                                'state': self.word(OWNER + 1256)})

    def run(self, payload, budget=20000, wire=False):
        if len(payload) > 0x7fff:
            raise ValueError('offline fixture too large')
        self.events = []
        self.input_len = len(payload)
        self.uc.mem_write(INPUT, b'\x00' * 0x10000)
        if payload:
            self.uc.mem_write(INPUT, payload)
        self.uc.reg_write(UC_ARM64_REG_SP, STACK + 0xff00)
        self.uc.reg_write(UC_ARM64_REG_TPIDR_EL0, TLS)
        self.uc.reg_write(UC_ARM64_REG_X30, RETURN)
        self.uc.reg_write(UC_ARM64_REG_X0, RPC)
        self.uc.reg_write(UC_ARM64_REG_X1, INPUT)
        self.uc.reg_write(UC_ARM64_REG_X2, len(payload))
        self.uc.emu_start(0x3e2f4 if wire else 0x3e740, RETURN, count=budget)
        if self.uc.reg_read(UC_ARM64_REG_PC) != RETURN:
            raise RuntimeError('instruction budget exhausted')
        return {'fixture': 'SYNTHETIC; not a captured hardware response',
                'entry_layer': 'escaped TL bytes' if wire else 'RPC list',
                'input_hex': payload.hex(), 'events': list(self.events),
                'state': self.word(OWNER + 1256),
                'metadata': {str(off): self.word(OWNER + off)
                             for off in (2320, 2324, 2328, 2332)},
                'normal_extra': self.word(PLATFORM + 18832)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    ap.add_argument('--hex', required=True, help='synthetic RPC-list bytes')
    ap.add_argument('--state', type=int, default=0)
    ap.add_argument('--wire', action='store_true', help='input is escaped TL bytes, still offline')
    args = ap.parse_args()
    replay = Replay(args.binary, args.state)
    result = replay.run(bytes.fromhex(args.hex), wire=args.wire)
    result['binary_sha256'] = replay.image.digest
    result['boundaries'] = ['initializer continuation intercepted', 'logging disabled',
                            'diagnostic and lock callbacks stubbed',
                            'send, reliable ACK/NACK handlers and internal operations intercepted']
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
