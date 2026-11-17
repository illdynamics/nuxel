# SSP final recovery — 2026-11-17

**Physical accelerometer/gyro streaming and automatic rotation are NOT VERIFIED.**
Starting HEAD is `6bcbcea6` on `feat/ssp`. The pre-existing `ssp.md` edit is
preserved. No transport was opened, firmware transmitted, service changed,
power/reset/watchdog setting written, or boot partition touched.

## Milestone 1: decoded RPC to version callback

Evidence: [hash-bound mapping](evidence/ssp-final-20261117/response-path.json),
[decoder](evidence/ssp-final-20261117/version_decoder.txt),
[reader](evidence/ssp-final-20261117/reader.txt),
[dispatcher](evidence/ssp-final-20261117/rpc_dispatch_and_postcheck.txt), and
[original-code replay](evidence/ssp-final-20261117/empty-version-replay.json).
All addresses refer exclusively to lhd SHA-256
`6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`.
Confidence: STATIC_VERIFIED plus OFFLINE_EMULATED where stated; never hardware
acceptance. Proprietary firmware/runtime files are unchanged.

```text
initializer registration 0x389c4 -> 0x3e9b0
  inserts owner+0x4c0 in RPC object's handler list (+0x3540)
RPC-list decoder 0x3e740
  aggregate record-length prewalk, then each (id, body, length)
  -> dispatch 0x3e884 -> handler vtable +16 (slot 0x48ae0)
  -> 0x3d1a8
     ID 3:    three LE32 values -> secondary interface +16 -> 0x39d00
              -> subtract this by 16 -> normal callback 0x39b9c
     ID 0x3b: extended fields -> secondary interface +24 -> 0x39e64
              -> subtract this by 16 -> extended callback 0x39d08
     ID 4:    one LE32 -> secondary interface +32 -> empty method 0x18050
  callback stores metadata, then gates state 8->9 or 15->16
  -> initializer 0x389fc (intercepted in offline replay)
  only AFTER callback returns: remaining-length/error checks 0x3e924..0x3e95c
```

Registration and vtables are established by constructor instructions and ELF
RELATIVE relocations. The decoder's actual comparisons establish IDs 3, 4 and
59. ID 4's application meaning remains unknown; this callback implementation
ignores it. No command ID was inferred from an ELF address.

Normal schema: LE32 w1, LE32 w2, LE32 w3. Extended schema: four LE32s, u8 length
and that many bytes (x5), LE32 w6, u8 length and that many bytes (x7).
String terminators are not validated by the span reader; rendering is not
emulated. Semantic field names beyond the daemon's version log remain unproven.

Reader vtable 0x48f08 maps +0x68 to LE32 reader 0x41168, +0x48 to byte reader
0x410cc, and +0x78 to span reader 0x411e4. Scalar underflow sets error byte +36,
returns zero, and does not advance cursor. Span underflow sets error and returns
the current pointer without advancing. The version handler does not consult
that error before calling its consumer.

Pseudocode of the important ordering:

```text
prewalk_rpc_list_lengths()  // reads header bytes before per-byte bounds proof
for record in list:
    reader = bounded_reader(record.body, record.length)
    handler.decode_and_call(record.id, reader)
        values = reader.read_fields()   // may set error and return zeros
        callback(values)
            write_metadata(values)
            if state in {8,15}: advance_state(); initializer()
    if recognized and (reader.remaining != 0 or reader.error): diagnostic()
```

**New verified limitation:** synthetic `03 00` (ID 3, zero-length body) passes
the RPC aggregate-length check. The original instructions write zero metadata
and advance 8->9 before diagnosing reader underflow. Trailing normal-body bytes
also reach the callback before the remaining-length check. Truncated RPC-list
headers cause reads beyond the supplied logical extent in the prewalk; tests
track these reads inside padded emulator memory. This is not a claim of a
physical transport exploit or that arbitrary corrupt frames pass transport CRC.

Repeated normal messages reach the callback at this layer; unexpected state
prevents advancement but not metadata mutation. Field 2332 latches the first
w2 unless already initialized. No session/request token or duplicate check is
present in this reviewed RPC path. Transport acceptance remains upstream.

Implementation: extended `inspect_lhd_init.py`; added bounded original-code
`replay_lhd_response.py`, pinned Unicorn dependency, and 12 regression tests
covering every initialization state, all normal/extended truncations,
trailing bytes, duplicate/reordered messages, unknown IDs, malformed envelopes,
incomplete headers, modified ELF rejection and instruction budgets.
[Results](evidence/ssp-final-20261117/response-tests.txt): 12 tests PASS.
All fixtures and object scaffolding are synthetic. Locks and diagnostics are
stubbed, logging disabled, initializer continuation intercepted. A diagnostic
return in the harness does not assert that production assertion handling returns.

## Physical state and authorization

[Read-only SSH snapshot](evidence/ssp-final-20261117/phone-readonly.txt) records
kernel identity, service status and hub diagnostics. Orientation daemon is
active; lhd and SSP bridge units are inactive. Activity is not sensor acceptance.
Previous physical captures were zero vectors. No new movement correlation has
been performed.

The owner's current instruction requires explicit approval before hardware
changes, superseding permissive reflash language inside historical reports.
No live trial is ready for approval. Remaining prerequisites include complete
transport/session behavior, initialization timeouts/abort/reset contract and a
confirmed recovery path for loss of SSH or persistent MCU state. Process exit
is not a recovery mechanism.

## Next safe milestone

Trace the receive path above 0x3e740: RPC constructor 0x3e250 installs interface
vtable 0x48e70; transport receive 0x3fe80 calls complete-frame decoder 0x40098.
The latter dispatches noninternal payloads via interface slot +0x30 at 0x404fc
(target 0x3ebfc -> 0x3e740). Extend offline replay across CRC, sequence,
reliable duplicate filtering and internal routing. Keep ACK transmission and
internal initialization effects explicit boundaries until separately reviewed.
Then trace state 16 forward to DONE and the virtual timer implementation.
