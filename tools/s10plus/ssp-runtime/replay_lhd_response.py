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
INIT_INTERFACE = OWNER + 0xa00
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

    def execute(self, entry, arguments, budget=20000):
        self.events = []
        self.uc.reg_write(UC_ARM64_REG_SP, STACK + 0xff00)
        self.uc.reg_write(UC_ARM64_REG_TPIDR_EL0, TLS)
        self.uc.reg_write(UC_ARM64_REG_X30, RETURN)
        for index, argument in enumerate(arguments):
            self.uc.reg_write(UC_ARM64_REG_X0 + index, argument)
        self.uc.emu_start(entry, RETURN, count=budget)
        if self.uc.reg_read(UC_ARM64_REG_PC) != RETURN:
            raise RuntimeError('instruction budget exhausted')

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
        self.input_len = len(payload)
        self.uc.mem_write(INPUT, b'\x00' * 0x10000)
        if payload:
            self.uc.mem_write(INPUT, payload)
        self.execute(0x3e2f4 if wire else 0x3e740, [RPC, INPUT, len(payload)], budget)
        return {'fixture': 'SYNTHETIC; not a captured hardware response',
                'entry_layer': 'escaped TL bytes' if wire else 'RPC list',
                'input_hex': payload.hex(), 'events': list(self.events),
                'state': self.word(OWNER + 1256),
                'metadata': {str(off): self.word(OWNER + off)
                             for off in (2320, 2324, 2328, 2332)},
                'normal_extra': self.word(PLATFORM + 18832)}


class FinalVersionReplay(Replay):
    """Original state-16 comparison, timer arithmetic and DONE/cancel cleanup.

    Synthetic patch metadata is already marked available. Patch loading and
    higher-level completion effects are not emulated. No READY is emitted.
    """

    def __init__(self, binary, asic, patch_asic, original_version=0xffffffff,
                 confirmation_only=False, now=1000):
        super().__init__(binary, state=16, original_version=original_version)
        self.put64(OWNER + 8, PLATFORM)
        self.put64(OWNER + 16, INIT_INTERFACE)
        self.put64(OWNER + 1208, RPC)
        self.put64(INIT_INTERFACE, 0x48720)
        self.put64(INIT_INTERFACE + 8, PLATFORM)
        self.put32(OWNER + 2320, asic)
        self.put32(OWNER + 40 + 1056, patch_asic)
        self.uc.mem_write(OWNER + 40 + 1160, b'\x01')
        self.uc.mem_write(OWNER + 2345, bytes([bool(confirmation_only)]))
        self.put32(PLATFORM + 18824, now)

    def _code(self, uc, addr, size, user):
        if addr == 0x37508:
            self.events.append({'kind': 'completion_boundary',
                                'success': bool(uc.reg_read(UC_ARM64_REG_X1) & 1),
                                'asic': uc.reg_read(UC_ARM64_REG_X2) & 0xffffffff})
            self._return()
            return
        if addr == 0x376c8:
            self.events.append({'kind': 'diagnostic_boundary'})
            self._return()
            return
        if (0x389fc <= addr < 0x396ac or 0x37908 <= addr < 0x37944
                or 0x3c75c <= addr < 0x3c76c or 0x3eac4 <= addr < 0x3ebac):
            return
        super()._code(uc, addr, size, user)

    def step(self, cancel=False):
        self.execute(0x39684 if cancel else 0x389fc, [OWNER])
        return {'fixture': 'SYNTHETIC patch/version fields; not firmware acceptance',
                'events': list(self.events), 'state': self.word(OWNER + 1256),
                'timer_deadline': self.word(INIT_INTERFACE + 16),
                'timer_active': bool(self.uc.mem_read(INIT_INTERFACE + 20, 1)[0]),
                'registered': self.word(RPC + 0x3540) != 0}


class SyncReplay(Replay):
    """Original internal synchronization with synthetic time and intercepted sends.

    The scheduler runs with no pending reliable queue. Completion stops at the
    platform callback; this does not establish an MCU session or initialize it.
    """

    CLOCK, SCHEDULE, SYNC_DONE, COMM_ERROR = (STUBS + 16, STUBS + 20,
                                            STUBS + 24, STUBS + 28)
    TRANSPORT = RPC + 24

    def __init__(self, binary, now=1000):
        super().__init__(binary, state=4)
        self.now = now
        for offset, callback in ((16, self.SCHEDULE), (24, self.CLOCK),
                                 (40, self.COMM_ERROR), (56, self.SYNC_DONE)):
            self.put64(PLATFORM + 0x100 + offset, callback)
        self.uc.mem_write(self.TRANSPORT + 0x34f0, b'\x01\x00')

    def _code(self, uc, addr, size, user):
        if addr == self.CLOCK:
            uc.reg_write(UC_ARM64_REG_X0, self.now & 0xffffffff)
            self._return()
            return
        if addr in (self.SCHEDULE, self.SYNC_DONE, self.COMM_ERROR):
            argument = uc.reg_read(UC_ARM64_REG_X1) & 0xffffffff
            if addr == self.SCHEDULE:
                self.events.append({'kind': 'schedule_boundary',
                                    'delay_ms': argument if argument < 0x80000000 else argument - 0x100000000})
            elif addr == self.SYNC_DONE:
                self.events.append({'kind': 'sync_completion_boundary', 'success': bool(argument & 1)})
            else:
                self.events.append({'kind': 'communication_error_boundary'})
            self._return()
            return
        if addr == 0x3f3d8:
            length = uc.reg_read(UC_ARM64_REG_X0 + 3) & 0xffff
            pointer = uc.reg_read(UC_ARM64_REG_X2)
            self.events.append({'kind': 'transport_send_boundary',
                                'flags': uc.reg_read(UC_ARM64_REG_X1) & 0xffff,
                                'payload_hex': bytes(uc.mem_read(pointer, length)).hex()})
            uc.reg_write(UC_ARM64_REG_X0, 0)
            self._return()
            return
        if (0x3f0fc <= addr < 0x3f3d8 or 0x407f0 <= addr < 0x40b10
                or 0x3ebac <= addr < 0x3ec30 or 0x396ac <= addr < 0x3970c):
            return
        super()._code(uc, addr, size, user)

    def snapshot(self):
        return {'fixture': 'SYNTHETIC internal response and clock; sends intercepted',
                'events': list(self.events),
                'active': bool(self.uc.mem_read(self.TRANSPORT + 0x350d, 1)[0]),
                'token': self.word(self.TRANSPORT + 0x3514),
                'transport_bytes': {hex(offset): self.uc.mem_read(self.TRANSPORT + offset, 1)[0]
                                    for offset in (0xc56, 0x34f0, 0x34f1, 0x428, 0x431, 0x432)},
                'previous_reliable_length': self.uc.mem_read(self.TRANSPORT + 0x434, 2).hex()}

    def start(self):
        self.execute(0x3f0fc, [self.TRANSPORT])
        return self.snapshot()

    def poll(self, now):
        self.now = now
        self.execute(0x3f1f8, [self.TRANSPORT])
        return self.snapshot()

    def receive(self, payload):
        if len(payload) > 0x7fff:
            raise ValueError('offline fixture too large')
        self.input_len = len(payload)
        self.uc.mem_write(INPUT, b'\x00' * 0x10000)
        if payload:
            self.uc.mem_write(INPUT, payload)
        self.execute(0x407f0, [self.TRANSPORT, INPUT, len(payload)])
        return self.snapshot()


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
