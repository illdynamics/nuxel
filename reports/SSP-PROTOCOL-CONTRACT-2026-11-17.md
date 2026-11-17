# BCM47752 protocol contract review — 2026-11-17

**Physical sensors and automatic rotation remain NOT VERIFIED.** SSH to
root@10.11.12.99 with the supplied key succeeded. No live BBD descriptor was
opened, no power/reset/watchdog setting was changed, and no firmware was sent.
The stock runtime was neither re-extracted nor rerun through its known assertion.
Commits `7cd354d4` and `3c06d253`, UI work, firmware and runtime are preserved.

This continuation started with uncommitted native downloader hardening and
protocol evidence already present. Those edits were reviewed and extended,
not discarded. The pre-existing recovery-report and `ssp.md` edits are untouched.

## Evidence and scope

The [stock-runtime report](SSP-STOCK-RUNTIME-2026-11-17.md) remains authoritative
for runtime identity and the last physical sample capture (zero vectors).
[Review inventory](evidence/ssp-protocol-20261117/stock-evidence-review.json)
records all 50 supporting files, hashes, JSON structures, daemon outputs and
relevant syscall excerpts. No new physical sample claim is made here.

Kernel review uses the locally patched `kernel/s10plus/.build/src`, based on
Linux4 commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, **not an assertion that
unmodified upstream source equals the running image**. The reviewed file and
configuration hashes are [retained](evidence/ssp-protocol-20261117/review-source-hashes.json).
The first five hashes also match the earlier protocol evidence inventory.

A trustworthy comparison is Google's published
[BCM47765 BBD source](https://android.googlesource.com/kernel/google-modules/gps/broadcom/bcm47765/+/refs/tags/android-16.0.0_r0.4%5E%21/).
It corroborates the bridge/control architecture, but is a different chip and
cannot establish BCM47752 ROM RPC responses, firmware ACKs or power timing.
Searches for BCM47752 firmware_downloader and the daemon's exact state names
found no matching published protocol specification. This is a search result,
not proof no such source exists. Existing upstream URL/hash evidence is retained.

## Verified kernel-facing contract

| Interface/layer | Evidence-backed behavior | Limit |
|---|---|---|
| `/dev/ttyBCM` | `bcm_spi_open` clears read/write rings, rejects busy ownership, enables IRQ; SPI worker performs MCU_REQ/MCU_RESP wakeup and SSI transport | Opening it is state-changing even before a version request |
| `/dev/bbd_patch` | `bbd_patch_read` selects the embedded patch using AP/hardware revision callbacks and returns bytes | It does not transmit firmware; an EOF resets position, so consumers must stop at EOF |
| `/dev/bbd_sensor` | `bbd_send_packet` queues `[native u16 length][SSP bytes]` for lhd to wrap in RPC (little endian on this target) | Native peer mode changes the route; dual ownership must be excluded |
| RPC sensor data | `bbd_rpc_lh.c` enum assigns sensor request 0x20 and response 0x21; response starts with little-endian u16 sensor length | These are sensor bridge records, not firmware-operation acknowledgements |
| `/dev/bbd_control` | daemon strings `ESW:READY`, `ESW:NOTREADY`, `ESW:CRASHED` enter `bbd_control` | They are daemon notifications, not proof independently obtained from the hub |
| `ESW:READY` | queues `bbd_mcu_ready_work_func`, which waits for sensor readiness, enables SSP, calls `initialize_mcu`, then restores sensor state | Sending READY manually could trigger live initialization; never synthesize it |
| NOTREADY / CRASHED | clear the sensor receive queue and disable SSP; CRASHED also invokes the control callback | Not a firmware NACK schema |
| Reset request | `bbd_mcu_reset` queues NUL-terminated `BBD:RESET_REQ` if killer disabled; if enabled, may SIGKILL registered lhd | Stopping lhd is not necessarily sufficient recovery |
| Watchdog | `lk_enable` changes driver behavior; `BBD:PassThru=1/0` controls the patch watchdog for registered lhd; `SSI:PassThru=1` takes a patch wake lock | Default watchdog timeout is 10 seconds; sysfs writes are hardware-trial actions |

`initialize_mcu` first requires the expected chip ID, then AP information,
sensor positions and a nonzero scanning mask; it also initializes sensor
metadata and reads firmware revision. A successful loader alone does not prove
this SSP handshake, streaming or rotation.

Timeouts have distinct meanings:

- Kernel TL source declares reliable retry defaults of 1000 ms / 10 retries,
  150 in-flight packets, and 2048-byte payload limits. This receive-side file
  does not implement the complete reliable sender retry engine. Those defaults
  are **not verified daemon/ROM operation deadlines**.
- MCU_REQ polling uses approximately 100 one-millisecond checks, with extra
  GPIO toggles/delays every 20 iterations. It is not an exact 100-ms deadline.
- The SSP ready worker waits up to `2*HZ` for MCU sensor readiness when the
  divided-rail path is present; otherwise it sleeps 1000 ms. It tries
  `initialize_mcu` up to four times, delaying 100 ms after failures.
- BBD sensor pulls use 1000 ms; SSP command completion uses the caller's timeout.
- Native query observation windows and the one-second write limit are host
  safety bounds, not vendor protocol timing.

The custom native bring-up hook also contains a regulator power-cycle fallback.
It must not be invoked as a read-only diagnostic or used to infer Samsung's
stock power contract.

## Verified framing; operation completion still unknown

Decoded TL body is `seq | payload_size_low | flags_low | details | payload | crc`.
Size counts payload only. Each set flag consumes a detail in increasing bit
order; bit 6 adds size high, bit 7 adds flags high. CRC excludes sequence and
itself, uses the source table (MSB-first polynomial 0x4d), and swaps nibbles.
Escape framing is `b0 00 ... b0 01`; escaped B0/11/13 use 03/04/05.

Packet ACK (bit 0) carries packet sequence; reliable ACK (bit 2) carries reliable
sequence; reliable NACK (bit 3) carries the last remote reliable sequence.
Neither packet nor reliable ACK proves that MemoryWrite or StartScratchApp
succeeded. The receive source detects reliable duplicates using sequence,
CRC and length; next-sequence acceptance and NACK paths are separate. It computes
ACK flags, but that function does not itself send a complete ACK transaction.
Do not infer lhd's sender ownership or internal synchronization from those flags.
Internal payloads must not enter RPC decoding. RPC ID/length fields are 15-bit,
one byte below 0x80 and two bytes otherwise.

Native `transact()` previously used a received-packet count as success. The
retained hardening now returns no verified completion regardless of transport
activity, and live query exits nonzero with `COMPLETION UNVERIFIED`. The disabled
speculative upload sequence is removed; `--download` still refuses before I/O.
Tests cover unrelated RPCs, matching and stale packet ACKs, reliable ACKs and
NACKs. No response matcher or downloader state machine is invented.

Additional fixes: native payload/detail sizing, bounded malformed decoding,
resynchronization and source-sized payload limits; Python CRC entry 0xe6
(correct 0xbe), extension flags/details, packet-length validation, parser reset
and overflow handling, preserved ACK/NACK metadata, strict RPC truncation checks.
The Python daemon skips internal records and malformed RPC lists. Native test
builds now depend on the included C source, preventing stale test executables.

Caller review found the Python session emitted `SSI:PassThru=1` and `ESW:READY`
after merely reading a firmware file, without a verified download. That path
is removed: `run_session` now returns `INITIALIZATION_PROTOCOL_UNVERIFIED`
before any inventory, power, device or control call. A regression fails on any
such call. CLI exit 2 remains compatible with the optional unit's existing
`SuccessExitStatus=2`. This change is local only; no service was deployed or
restarted. Low-level helper methods remain experimental, not approved trials.

## Matched daemon static initialization evidence

`lhd` SHA-256 is `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`.
[Hash-bound inspector](../tools/s10plus/ssp-runtime/inspect_lhd_init.py),
[dispatch results](evidence/ssp-protocol-20261117/lhd-dispatch-review.json), and
[regenerated disassembly](evidence/ssp-protocol-20261117/lhd-init-disassembly.txt)
make this analysis repeatable.

The dispatch at 0x389fc reads state offset 1256 and a 16-entry jump table at
0xdfc4. Its own log strings distinguish request-download, autobaud, sync,
initial version, ROM reset, download start/completion, app wait, confirmation
sync/version, and DONE (17). These are **not a verified linear recipe**.

Both version callbacks (0x39b9c and 0x39d08) advance only 8→9 or 15→16.
Other states log an unexpected version. This is actual control-flow evidence
beyond string matching, but it does not establish on-wire IDs, parameter decode
validation or all conditions preceding callback invocation. The initializer
contains distinct patch validation, scratch-app versus service-app branches,
ROM mismatch reset and sync retry paths. Timer-like virtual calls receive
constants including 250 and 100, but their units and complete failure semantics
are not yet proven; they are not implemented as protocol timeouts here.

## Configuration, Binder and socket diagnostics

The retained stock trace shows initialization continues after unknown-key
warnings for FlpName, LheClockMHz, LheSensorIpc and LhePinMux. Those keys also occur
in the matching stock config. Missing UrgentPatch and LheFailSafe warnings are
consistent with their absence/commenting in that config. They are not the
observed fatal blocker; this does not prove later behavior is unaffected.
The stock config lists LheMaxMcuResetTries twice (4, then 3); parser precedence
must not be guessed for a hardware trial.

`/dev/hwbinder` access fails before `defaultServiceManager() is null`, then lhd
continues into `GlLhdInterface::Init` and BBD open. This is a sandbox absence,
not unresolved DT_NEEDED. Whether a later initialization stage requires Android
services remains unknown. Do not expose host Binder merely to silence this log.
The trace-marker open failure is diagnostic infrastructure absence.

AF_INET socket creation fails with EACCES before BBD open. Source has
`CONFIG_ANDROID_PARANOID_NETWORK=y`; `inet_create` requires initial-namespace
AID_INET group 3003 or CAP_NET_RAW. New **socket-only** experiments in a private
network/mount/PID namespace establish:

- Original user-namespace setup: UID/GID 65534 fails; using namespace GID 3003
  also fails (a namespace-local number is insufficient).
- A no-user-namespace bwrap attempt with `--uid` is rejected by bwrap; retained
  as a failed diagnostic, not a daemon result.
- A static probe dropping supplementary groups, real GID and UID before socket
  creation: GID 65534 fails with errno 13; GID 3003 succeeds with errno 0.

[Probe source](../tools/s10plus/ssp-runtime/network_probe.c) only opens/closes a
socket; it never binds/connects. [Results](evidence/ssp-protocol-20261117/socket-permission-drop-review.txt)
confirm the group-permission distinction. No daemon sandbox policy was relaxed.
These results explain the observed socket denial; they do not establish that
TCP service setup or privileged port 300 would succeed later.

The immediate fatal blocker in the prior daemon trial is the deliberately
missing BBD control endpoint. Repeating that assertion would add no protocol
evidence. Power/watchdog opens precede it, so exposing BBD without reviewing
those effects is not an acceptable next step.

## Safe validation completed

- 95 orientation, GNSS and isolation tests passed:
  [log](evidence/ssp-protocol-20261117/regression-review.txt).
- Native host tests and patch-verifier tests pass with ASan/UBSan and warnings
  as errors; 12 independent-CRC offline replay cases pass:
  [sanitizers](evidence/ssp-protocol-20261117/sanitizer-review.txt),
  [replay](evidence/ssp-protocol-20261117/replay-review.json).
- The AArch64 native tests pass on Nuxel with only their static executable and
  pseudo-devices mounted, UID/GID 65534, all capabilities dropped and private
  namespaces: [target log](evidence/ssp-protocol-20261117/target-review.txt).
  Inputs are SIMULATED, not measured sensor data.
- Read-only phone check: orientation service active, no failed units reported,
  no lhd process reported: [check](evidence/ssp-protocol-20261117/phone-review.txt).
  Service activity is not proof of rotation.

## Remaining gate and recovery provisions

A physical-init trial is **not ready for approval**. The unresolved prerequisite
is the exact ROM/internal-sync and RPC-response contract, including payload
schemas, sequence/session correlation, rejection, retransmission, timeout,
abort and power/reset order. The current evidence verifies portions of the
bridge and daemon state gates, not an end-to-end safe initialization path.

Two ways to close this gap are deeper hash-bound analysis of the matched daemon
(including its RPC decoder, transport internal handlers and virtual timer/power
methods), or a matching Samsung/Broadcom implementation or annotated trace of a
successful stock BCM47752 startup. A trace must preserve direction, timestamps,
control strings, power events and ROM/app identity. No additional runtime
archive is needed. No indispensable external artifact has yet been proved
necessary; binary analysis remains possible, but incomplete.

Before requesting approval, prepare a concrete single-owner runner with exact
allowed nodes/actions, expected transitions and byte/time budgets; prove its
abort behavior offline. Account for the kernel watchdog, native peer and
regulator fallbacks. Record pretrial service/power/transport state, retain the
known boot image and verified recovery route, and specify which approved action
restores each changed state if lhd or SSH fails. Terminating a process cannot be
represented as undoing a power or firmware change. No reboot/flash should be
proposed merely to bypass missing protocol evidence.

Only after that review and explicit owner approval may hardware initialization
run. Acceptance then requires correlated physical six-face accelerometer data,
positive/negative gyro turns, hardware-driven rotation, and suspend/resume plus
cold/warm-start regressions. These criteria remain outstanding.
