# Hardware-denied SSP runtime trial

Build the diagnostic helpers from source on a host with the AArch64 GNU
toolchain (tested with GCC 15.2.0):

```sh
make -C tools/s10plus/ssp-runtime OUT=/tmp/nuxel-ssp-helpers all check
```

The probe is static and has no ELF interpreter. The logging shim is freestanding,
has no DT_NEEDED entries, and resolves only `vsnprintf` and `write` from the
reviewed Android runtime. It does not substitute GPIO, Binder, properties or HALs.

Before staging a daemon trial, recover and review the **matching** Samsung
runtime and vendor hashes as required by the recovery mission. A dependency
closure or an Android 10 Halium image alone does not establish that match.
Keep proprietary files owner-local and outside Git.

In the host staging root, install the newly built probe at `isolation-probe`,
the shim at `system/lib64/libssp-log-stderr.so`, and create empty `proc`, `dev`,
`tmp`, `data`, `logs` directories. Generate the hardware-denied configuration
and a manifest covering **every regular file except the manifest itself**.
Symlinks, special files, missing hashes and unlisted files are refused. Retain
previous manifests/results separately; never overwrite evidence.

Transfer the reviewed root to a temporary directory on the phone. Run
`run_isolated.py --root ROOT --output NEW_RESULT_DIR --probe` first. Inspect
`stdout.log`, `syscalls.log`, and `result.json`: UID/GID 65534, zero effective
capabilities, NoNewPrivs, read-only runtime and denied hardware paths are
required. Only then, with the matched runtime reviewed, run a separate bounded
trial without `--probe`. No hardware mode exists.

A probe-only test can use the static probe plus the original `lhd` as a
read-only file fixture, with no Android linker/libraries. This tests isolation
only; it cannot execute `lhd` and says nothing about its ABI compatibility or
the sensor hub. The November 16, 2026 recovery report records such a live test.

No firmware upload, reset, power operation, or boot flash is authorized by
these commands. The native downloader's `--download` refusal remains in place.

For the matched Samsung Android 10 tree, `--stock-namespaces` uses only
`/vendor/lib64` in `LD_LIBRARY_PATH` and preloads the diagnostic shim from
`vendor/lib64/libssp-log-stderr.so`. Stage the unmodified stock
`system/etc/ld.config.29.txt` also as `system/etc/ld.config.txt`, together with
the referenced VNDK-29 variants and canonical runtime APEX files. This makes
the stock namespace policy select the VNDK dependencies; the broad static
resolver alone cannot do that. The flag requires the config in the integrity
manifest. Probe and daemon trials retain identical hardware restrictions.
Private `/tmp/nv` and `/tmp/log` directories support the vendor lock/log paths.

## Offline protocol work after matched runtime recovery

Do not rerun the known missing-BBD assertion to investigate the firmware
protocol. The recovered stock runtime remains intact. Instead:

```sh
make -C tools/s10plus/ssp-native OUT=/tmp/ssp-offline all check
python3 tools/s10plus/ssp-runtime/check_protocol_replay.py --decoder /tmp/ssp-offline/nuxel_bbd_download
python3 tools/s10plus/ssp-runtime/inspect_lhd_init.py packs/sensors/acquired/vendor-bin-hw-lhd
```

Replay uses simulated bytes, an independent bitwise CRC calculation, bounded
subprocess execution, and the native stdin-only decoder. It exercises ACK/NACK
framing, internal payload isolation, extended lengths, malformed RPC rejection,
CRC failure and stream resynchronization. It opens no device and cannot verify
operation completion or physical sensor samples. Native socketpair tests also
require that matching/stale packet ACKs, reliable ACK/NACKs and unrelated RPCs
never complete a query. `make check` runs both sets of checks.

The static initializer inspector rejects any daemon hash other than the matched
stock binary. It records dispatch addresses and reviewed callback gates; it
explicitly lists the remaining unverified protocol semantics.

`network_probe.c` only creates and closes an AF_INET socket. The protocol report
records private-network trials distinguishing the Android AID_INET permission
check from protocol failure. Its optional argument drops supplementary groups,
GID and UID before the socket call. It never connects, binds or opens hardware.
The daemon sandbox's identity and capabilities have not been relaxed.

### Matched decoder/callback replay (offline only)

`inspect_lhd_init.py` now records the verified RPC IDs, ELF dispatch slots,
reader implementations and validation order, with hashes of each code range.
The IDs come from decoder comparisons, not callback addresses.

`replay_lhd_response.py` executes the original matched AArch64 instructions in
Unicorn. It does not execute the ELF as a process or access the handset. It
constructs synthetic objects and RPC inputs, applies ELF RELATIVE relocations,
disables logging, stubs lock/diagnostic callbacks, and intercepts the initializer
continuation. Unknown code and exception/syscall instructions fail closed; an
instruction budget bounds each replay. This is not a firmware implementation.

```sh
python3 -m venv /tmp/nuxel-lhd-replay
/tmp/nuxel-lhd-replay/bin/pip install -r tools/s10plus/ssp-runtime/requirements-analysis.txt
/tmp/nuxel-lhd-replay/bin/python -m unittest discover -s tools/s10plus/ssp-runtime -p test_lhd_response.py -v
/tmp/nuxel-lhd-replay/bin/python tools/s10plus/ssp-runtime/replay_lhd_response.py \
  packs/sensors/acquired/vendor-bin-hw-lhd --state 8 --hex 0300
```

All fixtures are **SYNTHETIC**. In particular, `0300` is an intentionally malformed
version record, not an expected ROM reply. It demonstrates callback metadata
mutation and state advance *before* the reader-error check. Logging is disabled,
so extended string formatting safety is outside this replay's claims. The
base replay intercepts the initializer; it does not emit READY.

`--wire` starts at the original transport receive wrapper. CRC, escaping,
length checks, reliable sequence filtering and noninternal RPC delivery execute
as matched machine code. Send, reliable ACK/NACK handlers and internal-message
processing are intercepted and recorded. Both reviewed constructor callers
disable reliable duplicate delivery; the alternative option is tested explicitly.
This does not emulate a session handshake, firmware execution or hardware timing.

`FinalVersionReplay`, exercised by the same test suite, runs state-16 ASIC
comparison, DONE cleanup, cancellation and timer arithmetic using synthetic
patch metadata marked available. Completion is intercepted before external
effects. Both success and failure enter DONE; neither test result establishes
firmware execution. Timer units are independently traced to the matched Android
elapsedRealtime implementation; see the final recovery report and clock evidence.
# Synchronization continuation replay

`--patch-records HEADER` verifies the existing exact embedded-patch identity,
then runs its F1 records through original parser/callback/RPC5 serializer code.
Independent checks compare destinations, lengths and hashes at every layer.
It never transmits a record, generates an ACK or includes patch data in output.
Only F1 callbacks are enabled; container/header loading is outside this replay.

`--reliable-queue` additionally executes the original ring allocator/free,
ACK/NACK, retransmission and consumed-patch startup branches. Patch fields are
synthetically staged; this is not patch validation. Actual sends and external
error handling remain intercepted. Queue drain is never called MCU success.

`replay_lhd_response.py BINARY --sync-initializer` executes bounded synthetic
initial/confirmation synchronization, timeout/restart and cancel/late-reply
scenarios using the hash-matched instructions. `SyncInitializerReplay` extends
the existing transport replay through the original platform callback and
initializer to version-request serialization. Raw writes and reliable enqueue
are intercepted; no response, ACK, physical timer or MCU is simulated as real.
Assertion-helper entry stops the replay before its side effects. Other main-core
modes are refused. See `reports/SSP-FIRST-LIGHT-FINAL-RECOVERY.md` for limitations
and test commands. This is an offline diagnostic, not a live downloader.
