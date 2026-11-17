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

## Milestone 5: reliable completion versus application startup

Milestone 4 is committed as `90445249`. The next extension executes the actual
bounded transport ring allocator/free routines, reliable enqueue, cumulative
ACK/NACK handlers, resend scheduler, and the state-12 post-supply branches.
[Inventory](evidence/ssp-reliable-contract-20261117/contract.json),
[replays](evidence/ssp-reliable-contract-20261117/replays.json),
[tests](evidence/ssp-reliable-contract-20261117/tests.txt) and annotated-by-range
disassembly are preserved. Confidence: STATIC_VERIFIED / OFFLINE_EMULATED.

The counter at transport +`0x3508` is **pending reliable payload bytes**, not
completed firmware operations. Enqueue `0x3fa24` adds payload length. ACK
`0x4050c` searches the queue for the reported u8 sequence, retires every entry
through that match, subtracts their lengths, then invokes saved callbacks.
Unknown/duplicate ACKs do not retire more entries. Packet ACK alone cannot
drain the queue. NACK `0x40674` can retire a prefix and mark the suffix for
resend after matching a queued packet sequence. These tests do not establish
that an actual BCM47752 accepted any request.

Reliable retransmission interval is 500ms, also triggered by a resend flag.
After ten send attempts, the scheduler calls the communication-error interface;
it does not itself clear pending bytes or report application success. The
higher-level error callback is intercepted, not assumed harmless. No-pending
sync, retry and cancellation tests from milestone 4 continue to pass.

State 12 calls patch supply `0x399fc`, then reads the pending counter through
`0x3e3f0 -> 0x3f0f4`. Nonzero prevents application startup. Zero proceeds to
the startup branch. Static supply logic requires at least 2048 bytes of ring
capacity, feeds at most 512 patch bytes per iteration, then compares a local
checksum byte after supply. **The new branch fixture stages synthetic patch
metadata as already consumed; it does not prove patch validation or successful
memory writes.**

| Post-supply branch | Original serializer / request | Next state and delay |
|---|---|---|
| Patch type `0x41` (scratch log branch) | `0x3cee0`: RPC 46, LE32 entry, unreliable send | 13, 40ms |
| Other type (service log branch) | `0x3cff8`: RPC 55, LE32 entry plus four zero LE32s, unreliable send | 13, 100ms |
| Entry `0xffffffff` | No startup request; reliable empty RPC 0 version request | 15, 250ms |

Interface +48 resolves to `0x387f0`, which reads core byte +18808. When true,
the two startup branches choose state 16 instead of 13. Its production
configuration is not assumed enabled. Normally state 13 starts a second sync
sequence with destination 14, leading to final version confirmation. Thus
queue drain and the startup send are **not** sufficient MCU-ready evidence.

The suite now has 51 original-code tests, plus seven isolation tests. Added
checks include CRC rejection before ACK processing, packet/reliable separation,
cumulative/partial/unknown/duplicate ACKs, NACK resend, retry exhaustion, 300
enqueue/free cycles spanning ring and u8 sequence wrap, pending-byte startup
gating, metadata refusal and all four startup branches. Actual send is still
intercepted with explicitly synthetic packet-sequence return 0; no live response
or successful firmware operation is fabricated. The native regression suite
also runs with AddressSanitizer/UndefinedBehaviorSanitizer; see
[build/test output](evidence/ssp-reliable-contract-20261117/native-sanitizers.txt).

Reproduce these traces with the same environment and test commands above:

```sh
/tmp/nuxel-lhd-analysis-env/bin/python tools/s10plus/ssp-runtime/replay_lhd_response.py packs/sensors/acquired/vendor-bin-hw-lhd --reliable-queue
```

## Milestone 6: running build identification and confirmed receive-path conflict

Milestone 5 is committed as `6437658b`. New identity tooling compares a saved
`/sys/kernel/notes` capture with ELF PT_NOTE entries, refusing malformed,
oversized, conflicting or non-AArch64 inputs. It does not connect to hardware.
[Identity result](evidence/ssp-safety-contract-20261117/kernel-identity.json):

- Running capture and local vmlinux GNU build ID:
  `69020d959693f8302669c37a77636ee06825cf94`.
- Local vmlinux SHA-256:
  `333297b336070c9a508f28d5c000789edcb238ee88c8ee126766accbf41f0a09`.
- Capture SHA-256:
  `e1e9f3cc02bddaf8b48d1f1761de61785b381e1bedf0b8ecd0977218f9d57a0c`.

This identifies the local build artifact; it is not full running-memory
attestation or proof that every current dirty source file produced it. The
relevant compiled functions were therefore disassembled directly:

1. `bbd_common_open` compares minor 1 at `ffffff8009139eb4` and calls
   `bbd_nuxel_peer_open` at `ffffff8009139eec`.
2. `bbd_nuxel_peer_open` sets the native-active flag and conditionally calls
   `enable_irq` at `ffffff8008dad05c`.
3. `bcm_on_packet_received` calls `bbd_nuxel_peer_active` at
   `ffffff8008db0380`; a true result branches away from tty queueing to
   `bbd_nuxel_peer_rx` and returns.
4. `bbd_nuxel_peer_release` clears the flag but does not disable that IRQ.

See [open](evidence/ssp-safety-contract-20261117/bbd_common_open.txt),
[attach](evidence/ssp-safety-contract-20261117/bbd_nuxel_peer_open.txt),
[receive](evidence/ssp-safety-contract-20261117/bcm_on_packet_received.txt),
[detach](evidence/ssp-safety-contract-20261117/bbd_nuxel_peer_release.txt).
Matched stock config selects **both** `/dev/ttyBCM` and `/dev/bbd_sensor`.
Consequently the compiled native-peer policy is incompatible with treating a
stock sensor-node open as a passive bridge attachment. This is now a confirmed
compiled-code compatibility gate, not merely a speculative source mismatch.
No live open was used to demonstrate it.

Base source is [Linux4 f7194c1d15eded1c2a1a4dc63825b26103435cc0](https://github.com/Linux4/android_kernel_samsung_exynos9820/blob/f7194c1d15eded1c2a1a4dc63825b26103435cc0/drivers/sensorhub/brcm/bbdpl/bbd.c),
with existing Nuxel modifications. Source headers identify Broadcom GPLv2 and
Samsung GPLv2-or-later code; bbd.c also declares Dual BSD/GPL. The
[existing local delta](evidence/ssp-safety-contract-20261117/existing-kernel-local-delta.patch)
and [source/build hashes](evidence/ssp-safety-contract-20261117/local-source-build-sha256.txt)
are recorded without changing the source or kernel. A new targeted public
source search found related BCM47765 architecture, not a device-matched lhd
protocol implementation; it does not justify replacing this transport.

Fresh [ownership/state capture](evidence/ssp-safety-contract-20261117/ownership-and-state.json)
reads proc descriptor symlinks and reviewed show-only attributes. It is a
non-atomic snapshot, not an exclusive lock. The hub remains shut down; it is
not physical streaming evidence. The diagnostic read emits a kernel log line
but performs no power/reset or transport operation. Watchdog settings were
read, never changed. The compiled `bbd_mcu_reset` path may SIGKILL the
registered daemon; process termination does not establish power restoration.

All 61 offline runtime/identity/isolation tests pass. Existing orientation/GNSS
regression tests: [88 pass](evidence/ssp-safety-contract-20261117/orientation-gnss-tests.txt).
No service deployment, restart or orientation-policy change was performed.

Identity reproduction (the saved 36-byte capture is not firmware):

```sh
python3 tools/s10plus/ssp-runtime/inspect_kernel_identity.py kernel/s10plus/.build/out/vmlinux reports/evidence/ssp-safety-contract-20261117/live-notes.bin
```

### Hardware-trial decision and recovery gates

| Gate | Status / required evidence |
|---|---|
| Exact stock lhd/runtime | Present, hash-bound and hardware-denied execution verified previously |
| Host transport/initializer analysis | Expanded through sync, reliable drain and startup; real responses unverified |
| Stock/native routing coexistence | Verified incompatible compiled policy; needs separately built/reviewed compatibility change |
| tty/BBD open side effects | Confirmed IRQ/ring/owner changes; opens require approval |
| Watchdog, reset and daemon exit | Partial source/compiled evidence; no confirmed full MCU rollback |
| Bootability recovery | Preserve original boot and existing TWRP/ADB route; recovery artifacts/owner availability must be revalidated before a trial; handset is A-only |
| Loss of SSH | No unattended retry/reboot/reflash; owner-accessible recovery must be confirmed before starting |
| Accel/gyro stream and four-way rotation | NOT VERIFIED; require real changing samples and owner movement/display tests |

No trial is ready for approval. A future proposal must pin the candidate kernel,
lhd/runtime/patch hashes, exact nodes/operations, ownership exclusion, watchdog
handling, a single bounded attempt, failure capture and an independently
confirmed recovery mechanism. No broad `/sys` exposure, synthetic READY,
speculative reset, or automatic retry loop is acceptable. These are prerequisites,
not a claim that a recovery plan has already been validated.

## Milestone 7: actual acquired patch records to stock memory-write RPCs

Milestone 6 is committed as `03ee7686`. The hash-matched embedded patch is now
fed in 512-byte chunks through original instructions `0x3c7e0 -> 0x3ca50 ->
virtual +16 -> 0x39e74 -> 0x3d60c`. This is **host-side patch parsing**, not
an incoming ROM response. No ELF process, device, memory-write transmission,
transport ACK or firmware execution occurs. The actual queue operation remains
an intercepted boundary. Only hashes/counts/metadata are saved, not patch bytes.

[Actual-record replay](evidence/ssp-patch-contract-20261117/actual-record-replay.json)
and [hash-bound mapping](evidence/ssp-patch-contract-20261117/contract.json)
establish:

- Exact exported patch SHA-256:
  `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`.
- Blob SHA-256:
  `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d`.
- 438,895 blob bytes, 858 supplied chunks, **479 F1 records**, 435,542 data
  bytes, 478 serialized RPC packets (small records can share a transaction).
- F1 is a file-record tag: LE16 body length, then LE32 destination and data.
  The parser accumulates a complete body, rejects lengths above 950, and
  requires at least five body bytes for F1. It is not an RPC opcode.
- Serializer emits RPC **5**, containing LE32 destination, LE16 data count,
  then data. Every destination, size and data SHA-256 agrees across an
  independent input-record parser, original callback and independent decoded
  serialized-RPC comparison. Final parser state is idle, without residual data.
- Reliable transaction stores callback `0x39e6c`, which forwards to the
  initializer when the transport completion callback runs. That is not an
  independent firmware memory-write status response.

Confidence: STATIC_VERIFIED and OFFLINE_ORIGINAL_CODE with an identity-verified
existing artifact. The XML-like container loader, header checksum validation,
patch selection and non-F1 callbacks are not emulated. F0/F2..F5 may exist in
the binary parser but are not present in this blob; their callbacks remain
execution-denied. No new runtime/firmware download was needed.

[68 tests pass](evidence/ssp-patch-contract-20261117/tests.txt), including
fragment boundaries, incomplete records, exact little-endian serialization,
duplicate/reordered file records, maximum accepted size, malformed lengths,
unknown tags, refusal of unreviewed callbacks, and the actual acquired blob.
Synthetic rejection fixtures remain explicitly distinguished from actual data.

```sh
/tmp/nuxel-lhd-analysis-env/bin/python tools/s10plus/ssp-runtime/replay_lhd_response.py packs/sensors/acquired/vendor-bin-hw-lhd --patch-records kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h
```

## Next safe milestone

Build/review a default-preserving stock/native routing compatibility option.
Resolve the original container-loader validation/selection and higher-level
communication-error/abort effects; the
current replay deliberately stops before them. Separately resolve the
experimental native-peer receive diversion and higher-level abort/reset
effects before requesting any hardware trial. A defensible end-to-end recovery
contract is not complete, so **no physical trial is proposed or authorized**.
