# SSP final recovery — 2026-11-17

**Physical accelerometer/gyro streaming and automatic rotation are NOT VERIFIED.**
Original investigation started at `6bcbcea6` on `feat/ssp`. This continuation
reconciled a clean checkout at `61eee374` on **`feat/png`**; no branch switch or
reset was made. Earlier work, including the `ssp.md` edit, is preserved.
No transport was opened, firmware transmitted, service changed,
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

## Milestone 2: escaped transport through callback

Milestone 1 is committed as `c24ff705`. The extended replay now runs the original
escaped-byte parser, frame validator and RPC delivery path. Evidence:
[transport mapping](evidence/ssp-final-20261117/transport-path.json),
[machine code](evidence/ssp-final-20261117/transport_receive.txt),
[CRC implementation](evidence/ssp-final-20261117/transport_crc.txt),
[wire-to-callback replay](evidence/ssp-final-20261117/wire-empty-version-replay.json).
Confidence: STATIC_VERIFIED and OFFLINE_EMULATED; input remains SYNTHETIC.

The complete reviewed receive path is `0x3e2f4 -> 0x3fe80/0x3fe84 ->
0x40098 -> virtual +0x30 -> 0x3ebfc -> 0x3e740 -> 0x3e884 ->
0x3d1a8 -> callback thunk -> version callback`. Constructor 0x3e250 supplies
the transport interface at RPC-object +8, with vtable 0x48e70.

- Frame minimum is four decoded bytes. CRC covers bytes after packet sequence
  and before CRC, using the embedded table and nibble swap. Bad CRC rejects
  before RPC. Unconsumed flags and payload-size mismatches also reject.
- Packet sequence mismatch increments loss statistics; it does not suppress
  an otherwise accepted unreliable payload. Unreliable duplicates/reordering
  therefore reach version callbacks.
- Reliable duplicate identity uses reliable sequence, payload CRC and length.
  Normal mode suppresses duplicates and non-next sequences, emitting ACK/NACK
  through the transport-send method. Both reviewed constructor call sites pass
  false for the alternative duplicate-delivery option at transport offset
  0x3521. Next sequence is accepted modulo 256. This is not a session nonce or
  firmware-operation completion check.
- Internal payloads route to 0x407f0 instead of RPC. Packet/reliable ACK-only
  frames do not invoke version callbacks. ACK/NACK handlers, internal handling
  and actual transmission remain intercepted boundaries in this replay.
- A CRC-valid synthetic frame containing `03 00` still reaches metadata writes
  and 8->9 before underflow diagnosis. CRC does not establish RPC schema validity.

[20 tests pass](evidence/ssp-final-20261117/transport-tests.txt), including
all earlier tests plus CRC/length rejection, reliable ordering, internal routing,
ACK-only frames, escaping, every split point of a frame and parser restart.
The configurable duplicate-delivery mode is tested separately and is not claimed
to be the installed daemon default. The source-backed independent polynomial
fixture encoder is reused from `check_protocol_replay.py`.

## Milestone 3: final verification, DONE and timer units

Milestone 2 is committed as `f3fbff72`. Confidence for the following is
STATIC_VERIFIED and OFFLINE_EMULATED, with synthetic, already-available patch
metadata. Evidence: [mapping](evidence/ssp-final-20261117/final-verification-path.json),
[initializer/cancel](evidence/ssp-final-20261117/initializer_and_cancel.txt),
[completion/timers](evidence/ssp-final-20261117/completion_and_timer_methods.txt),
[replays](evidence/ssp-final-20261117/done-replays.json).

State 16 compares current ASIC identity (owner +2320) with the patch object's
ASIC field (+1056, object at owner +40). The BCM4775b0 branch masks the current
ASIC to 24 bits before comparison. A separate legacy exception accepts 4774a0
against patch 4774a1 only when original-version field +2332 is 0x36a07.
The reviewed branch does not generally compare the other two version words.
Owner flag +2345, set by start argument bit 0, bypasses this comparison and
reports success; it is labeled confirmation-only in the analysis.

Completion callback at 0x37508 receives a boolean. **Both true and false enter
state 17**, schedule a one-millisecond continuation, then clear state and
unregister the RPC handler. DONE is cleanup, not successful firmware execution.
Cancellation at 0x39684 similarly clears state/unregisters; it does not restore
metadata, clear the timer itself, or establish any hardware recovery.

The initializer interface vtable is 0x48720: +16 is completion 0x37508,
+24 diagnostic 0x376c8, +32 timer 0x37908, +40 clock 0x37934. Consequently
the constant 100 sent to +24 is a diagnostic/progress argument, not a timeout.
Timer deadlines are unsigned 32-bit cached elapsed time plus delay. Negative
signed delays disable the timer; the poll uses signed deadline-minus-now and
clears active before dispatch. Wraparound and cancellation are replay-tested.

Clock chain: core update 0x3507c -> interface +24 -> 0x26290 -> singleton
virtual +152 -> 0x228d8 -> 0x1f6e4 -> Android elapsedRealtime. The exact
runtime's VNDK libutils implementation divides BOOTTIME nanoseconds by 1,000,000.
Thus these timer values are **milliseconds**, supported by matched-library
[disassembly](evidence/ssp-final-20261117/vndk-elapsed-time.txt) and
[AOSP source inventory](evidence/ssp-final-20261117/clock-source.json), including
revision, SHA-256, Apache-2.0 license and Samsung differences.

Success notification can reach 0x265b0 and emit `BBD:PassThru=0` followed by
`ESW:READY` through 0x21a54; the enabled control writer and preceding helper
effects still require analysis. No READY was emitted in this work. Original-code
replay intercepts completion before its external effects and does not load patches.
[All 25 tests pass](evidence/ssp-final-20261117/final-version-tests.txt).

## Newly identified hardware compatibility gate

The local experimental kernel patch's `bbd_common_open` calls
`bbd_nuxel_peer_open()` for every bbd_sensor open. That marks a native peer
active and arms the hub IRQ. `bcm_on_packet_received` then diverts raw SSI data
to that peer and returns before queuing ttyBCM input. A stock lhd opening
bbd_sensor therefore risks diverting its own receive traffic under this source.
Peer close clears active but does not undo IRQ arming. Evidence is the local
`0013-nuxel-sensorhub-bringup-native-bbd.patch.experimental` and patched source
`bbd.c:600`, `ssp_bbd.c:217`, `bcm_gps_spi.c:865`. The exact running dirty
kernel is not yet proven identical to these sources. This must be resolved
before any live stock-runtime trial; sole daemon ownership is insufficient.

Latest read-only SSH observation (2026-11-17 10:33:28 UTC): orientationd active;
hub `mcu_probe=1 shutdown=1 resetting=0 sensor_state=0x3feff enable=0x0
shub_irq=443`. No live hardware-changing operation has been performed.

## Milestone 4: synchronization through initialization and request serialization

The isolated sync replay already added in `380d8ee1` is preserved and extended,
not reimplemented. [Hash-bound inventory](evidence/ssp-sync-contract-20261117/contract.json),
[original-code traces](evidence/ssp-sync-contract-20261117/replays.json), and
[42 passing tests](evidence/ssp-sync-contract-20261117/tests.txt) close the
callback-to-next-request gap. Confidence: STATIC_VERIFIED / OFFLINE_EMULATED.
Every response fixture is **SYNTHETIC**, never a captured ROM/application response.

```text
CRC/length-checked internal transport payload -> 0x407f0
  opcode 1: read seven u8 fields; reject error or leftover bytes
  require sync-active AND token equality; update transport fields
  clear active; run scheduler -> interface +64 -> 0x3ec18
  outer interface +56 (relocation 0x487f8) -> 0x37f88
    core state +18812 == 3 -> initializer at core+15808 -> 0x396ac
      state 4 -> 5(success) / 6(timeout) -> initializer 0x389fc
      5 -> saved destination 7(initial) / 14(confirmation); timer 0ms
      next explicit timer dispatch: 7/14 -> 8/15
        original RPC encoder emits ID 0, empty body (00 00)
        reliable enqueue boundary; timer 250ms; five retry credits
```

The opcode jump table at `0xe0dd` derives dispatch targets from real binary
bytes, not callback addresses. Opcode 1 requires exactly eight payload bytes.
Byte 1 is compared with the current token; bytes 2/4/5/6 update transport
sequence bookkeeping, while bytes 3/7 are read but discarded. Exact stores
and modulo-256 adjustments are in the inventory. These local field roles do
not establish undocumented ROM semantics. Malformed sync responses reject
**before mutation**, unlike the earlier version RPC decoder.

Starter `0x3f0fc` emits internal payload `[0, token]` with transport flags
`0x300`. The no-pending-queue scheduler retries at 100ms with tokens 1..6;
at 600ms it completes false. Constants at `0xde38`/`0xde60` are `(7,5)` and
`(14,5)`: five initializer restart credits. A timeout consumes one, returns
to state 2, emits the **binary's own 36-byte autobaud constant** through a
raw-write boundary, waits 100ms, then starts synchronization again. The
new attempt resets token to 1: an old token-1 reply passes the local check.
This token is not a cross-attempt session nonce.

Both version-wait states issue the initial request plus five retries at
250ms. Exhaustion reaches assertion helper `0x34f80`; the harness stops
before its real effects. Sync restart exhaustion likewise reaches that helper.
Neither is modeled as success or a safe hardware reset.

**Cancellation safety gap:** `0x39684` clears initializer state/unregisters
its RPC handler but leaves transport synchronization active. With synthetic
core state still 3, a late valid sync reply mutates transport bookkeeping and
reaches an unexpected-state assertion with initializer state 0. This is a
bounded local finding, not a claim that the full production caller fails to
cancel or changes no other state. Higher-level cancellation and reset effects
remain a mandatory safety investigation.

Replay scope: stock instructions, exact binary hash guard, finite instruction
budget, no ELF process/syscalls/devices; logging/locks stubbed; raw writes,
transport sends and reliable enqueue intercepted. No ACK is invented. Timer
steps are explicit synthetic calls, not the actual event loop. Main-core
modes other than 3 are refused. Tests cover both destinations, retry limits,
malformed/duplicate responses, cancellation, stale token reuse and refusal
after assertion. Normal and extended version decoder tests still pass.

Reproduce on the host (use an owner-local virtual environment):

```sh
python3 -m venv /tmp/nuxel-lhd-analysis-env
/tmp/nuxel-lhd-analysis-env/bin/pip install -r tools/s10plus/ssp-runtime/requirements-analysis.txt
PYTHONPATH=tools/s10plus/ssp-runtime:tools/s10plus/ssp-native /tmp/nuxel-lhd-analysis-env/bin/python -m unittest discover -s tools/s10plus/ssp-runtime -p 'test_lhd_response.py' -v
/tmp/nuxel-lhd-analysis-env/bin/python tools/s10plus/ssp-runtime/inspect_lhd_init.py packs/sensors/acquired/vendor-bin-hw-lhd
/tmp/nuxel-lhd-analysis-env/bin/python tools/s10plus/ssp-runtime/replay_lhd_response.py packs/sensors/acquired/vendor-bin-hw-lhd --sync-initializer
```

New [read-only SSH baseline](evidence/ssp-sync-contract-20261117/phone-readonly.txt)
records kernel identity, active orientation/bridge/SSH services and node metadata.
No transport/device was opened. It is not a new physical streaming test.

## Next safe milestone

Trace reliable enqueue `0x3fa24`, ACK handler `0x4050c`, pending count
`0x3f0f4` and initializer state 12 (`0x38cdc`) together. Determine exactly
what queue drain proves before scratch/service application startup. Keep
memory writes and physical transport intercepted. Separately resolve the
experimental native-peer receive diversion and higher-level abort/reset
effects before requesting any hardware trial. A defensible end-to-end recovery
contract is not complete, so **no physical trial is proposed or authorized**.
