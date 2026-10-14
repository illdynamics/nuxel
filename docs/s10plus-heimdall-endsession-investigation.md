# S10+ Heimdall v2.2.2 EndSession failure — investigation, instrumentation, verdict

**Date:** 2026-10-14
**Scope:** Samsung Galaxy S10+ (beyond2lte, Exynos 9820) flashing with Heimdall v2.2.2.
**Symptom:** BOOT and USERDATA both reach 100% and report "*upload successful*",
then the session fails / the handset remains in Download Mode.

> **VERDICT: UNRESOLVED.**
> The failure classes are now distinguished and unit-tested, the wrapper can no
> longer report a false success, and a real packet trace has been captured — but
> the underlying cause cannot be *confirmed fixed* without the physical handset
> (and, for the protocol-mismatch class, a USB capture of a **successful Odin
> flash** of the same device). No on-device confirmation was obtained. Per the
> task rules, no success is asserted.

---

## 1. What was read

| Area | Path |
|---|---|
| Progress/status claims | `S10PLUS-PROGRESS.md`, `S10PLUS-RELEASE-READ-ME-FIRST.md`, `README.md` |
| Supplied PIT text | `docs/s10plus-device-pit-2026-10-14.txt` (LSI9820, 41 entries) |
| Flash scripts | `boot/s10plus/flash-heimdall.sh`, `boot/initramfs/flash-heimdall.sh`, `boot/s10plus/flash.sh` |
| Guides | `macbook-s10plus-flash-guide-final-full.md`, `s10plus-flash-guide*.md`, `mac-quickstart-s10plus-flash-finisha.md` |
| Raw operator logs | `heim.md` (v2.2.2 BOOT-only run), `heimd.md` (`print-pit`, access errors) |
| BOOT/USERDATA paths | `build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img` (22,431,744 B), `build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img` (135,304,192 B) |
| Upstream source | `git.sr.ht/~grimler/Heimdall` tag `v2.2.2` = `d9554e7…` |

The installed `/opt/homebrew/bin/heimdall` is `v2.2.2` and is effectively a build
of that source (144,648 B vs 144,552 B for a local build of the same tree), so
the source analysis applies directly.

## 2. The EndSession code path (v2.2.2)

```
flash
 └─ Initialise (LOKE handshake: "ODIN" -> "LOKE")
 └─ BeginSession      (control 0x64, SessionSetupResponse)
 └─ sendTotalTransferSize, DownloadPitFile, SendFile(...) per partition
 └─ EndSession(reboot)
      ├─ SendPacket(EndSessionPacket(request=0))   // 1024-byte ControlPacket, type 0x67 @0, request @4
      ├─ ReceivePacket(ResponsePacket(0x67))       // 8 bytes; LE32 @0 must equal 0x67
      └─ if reboot: SendPacket(EndSessionPacket(request=1)) + ReceivePacket(0x67)
```

Facts from the source:

* `BridgeManager.h`: `kDefaultTimeoutSend = 3000`, `kDefaultTimeoutReceive = 3000`,
  `kDefaultTimeoutEmptyTransfer = 100`.
* `ControlPacket.h`: control packets are **1024 bytes** (that is the 1024 in the
  libusb logs, not a read).
* `ResponsePacket.h`: `InboundPacket(8)`; `Unpack()` fails unless the little-endian
  word at offset 0 equals the expected type `0x67`.
* `BridgeManager::ReceivePacket()` returns `false` for **four different
  reasons** — read error (`< 0`), wrong size, unpack mismatch, or a rejected
  response type — but all four print the same
  `Failed to receive session end confirmation!`. Upstream also returns a bare
  exit status `1` from `FlashAction`.

**Consequence:** the upstream error text and exit code cannot distinguish a
timeout from a USB disconnect, a malformed packet, a rejected command or a
missing acknowledgement. That is the first thing that had to be fixed.

### 2.1 libusb bulk-read behaviour and the timeout asymmetry

* `ReceiveBulkTransfer()` substitutes a 1-byte buffer for `data == nullptr` (the
  "empty transfer" probe), which on most hosts simply times out at 100 ms and is
  logged as a *warning* only in verbose mode. It is noise, not the failure.
* Both `SendBulkTransfer`/`ReceiveBulkTransfer` retry up to 5 times with growing
  delays when `retry == true` (the default). A single EndSession acknowledgement
  is therefore bounded by roughly 6 × timeout + ~3.75 s of sleeps.
* `BeginSession` raises `fileTransferSequenceTimeout` to **120 000 ms** when the
  device advertises large-packet support, but `EndSession` still reads its
  acknowledgement with `kDefaultTimeoutReceive = 3000 ms`. That is the shortest
  timeout in the whole session, applied at the moment the phone is most likely
  still committing large writes to UFS. This asymmetry is why a *bounded but
  configurable* end-session timeout is the right instrumentation: it can be
  raised (`--nuxel-session-timeout`) without guessing at a new hard-coded value.

## 3. Reading the existing evidence correctly

### 3.1 The `heim.md` v2.2.2 run (BOOT only)

```
Uploading BOOT 100% -> BOOT upload successful
Ending session...
Rebooting device...          <- first 0x67 ack WAS received
Releasing device interface...  <- destructor; no error, reboot step also acked
```

No error was printed, so the handshake **succeeded** — yet the phone stayed in
Download Mode. That is the `still_in_download_mode` class: transfer and protocol
fine, the device-side commit/boot policy did not leave Download Mode. A host
protocol change cannot fix this; it points at the flashed image / S-Boot
verification / DTBO, none of which are USB problems.

### 3.2 The "Failed to receive session end confirmation" runs (issue #518 / #503)

Upstream issue #518 contains a full libusb debug trace. In it the final 8-byte
read **completed** (`urb status=0 transferred=8`) and *then* Heimdall printed
`Failed to receive session end confirmation!`. A completed 8-byte read that still
fails can only be `ResponsePacket::Unpack()` — i.e. the response type was **not
`0x67`**: the **rejected/unexpected-response** class, not a timeout.

So the two operator symptoms are *different* classes:

| Symptom | Class | Where the fault is |
|---|---|---|
| `heim.md`: "Rebooting device…", no error, stuck in Download Mode | `still_in_download_mode` | device/bootloader/image policy |
| guide + #518/#503: "Failed to receive session end confirmation" | `rejected_command` (per #518 trace) | protocol mismatch / desync |

Issue #503 (S10e `beyond0lte`) is the same story and is **still open**; the
maintainer explicitly asked for "captured usb-traffic logs from wireshark of
when odin flashes stock android … to see if the protocol has changed". That fix
does not exist upstream.

### 3.3 A real trace we captured (macOS, instrumented fork)

On this Mac the instrumented build received the `0x67` acknowledgement on the
first attempt (~7 ms) for both EndSession and reboot
(`external/heimdall-nuxel/docs/captured-endsession-trace-macos-2026-10-14.txt`).
So the same class of device *can* ack on a different host stack, which makes a
host-stack/timing difference (delayed acknowledgement) a live candidate for the
Linux-only failure — see H-C below.

### 3.4 Root-cause candidates, ranked by available evidence

| ID | Candidate | Evidence for | Evidence against | Detectable by |
|---|---|---|---|---|
| **H-A** | Flash did not commit / S-Boot declined to boot the image (wrong DTBO, AVB, verification) | `heim.md` acked everything but phone stayed in Download Mode | none yet | `still_in_download_mode` + boot logs |
| **H-B** | EndSession protocol mismatch/desync on S10-gen S-Boot | #518 trace: 8 bytes received, wrong type; #503 open upstream | our macOS run got a clean `0x67` | `rejected_command` / `malformed_packet` |
| **H-C** | Acknowledgement arrives later than the 3000 ms bound on Linux | Linux fails, macOS succeeds; Linux libusb 100 ms empty-transfer timeouts | #518's read completed instantly | `timeout` / `ok_delayed_ack` |
| **H-D** | USB disconnect / hub / cable | generic USB flashing failure mode | no disconnect in the captured logs | `usb_disconnect` |
| **H-E** | Wrong image or board revision | merged DTB is `BEYOND2LTE EUR OPEN 26`, unmatched | not yet checked on-device | PIT checker (section 6), not USB code |

**Not candidates:** rootfs ext4 content and boot.img packaging. They cannot
change a USB/ODIN handshake outcome. No Nuxel rootfs was recompiled for this
work.

## 4. What was changed (and what was deliberately not)

Patched fork: `external/heimdall-nuxel/` (5 patches on upstream v2.2.2, pinned
to `d9554e7…`). It **adds instrumentation and safety**; it does not invent a
protocol change, because the evidence does not yet support one.

* `NuxelSession.{h,cpp}` — a libusb-free end-session state machine.
* `BridgeManager::EndSessionEx()` — always performs the full handshake (never
  skips it), bounded configurable timeouts (clamped 50..600000 ms), hex packet
  tracing, and a Download-Mode presence probe. Upstream `EndSession()` is left
  intact so diff review is easy.
* `FlashAction` — `NUXEL_*` result lines, a distinct exit code per class, and a
  post-session "did the phone actually leave Download Mode?" probe.
* **Write gate** — `flash` refuses to write to any device unless
  `NUXEL_ALLOW_DEVICE_WRITE=1`; the wrapper sets it only after explicit
  confirmation. This exists specifically because a bare `heimdall flash` can
  overwrite a phone the operator did not know was attached (see §8).
* `--nuxel-empty-transfers <none/before/after/both>` — the zero-length OUT
  transfer is configurable because upstream sends one that routinely times out
  at 100 ms; it is an *experimental* knob, not a claimed fix.

Deliberately **not** changed: `EndSession` semantics, response decoding rules,
partition table handling, `--repartition`, and the upstream default timeouts
(changing the 3000 ms default is not yet evidence-supported; it is now
overridable so it can be *tested*).

## 5. Failure decision tree

```
heimdall flash ... exits
│
├─ exit 10  no Download-Mode device
│     -> cable/port (no hub), re-enter Download Mode, re-detect. Not a flash issue.
│
├─ exit 11/12  connection or begin-session failed
│     -> access/udev/driver problem. Fix host access before touching firmware.
│
├─ exit 14  timeout  (missing acknowledgement)
│     -> retry once with --nuxel-session-timeout 20000 on a native port.
│     -> if it then succeeds as ok_delayed_ack: host-stack timing (H-C).
│     -> if it still times out: capture the [nuxel] TX/RX hex and get an Odin capture.
│
├─ exit 15  usb_disconnect
│     -> cable/port/hub or device reset. Confirm whether the phone left Download Mode.
│        Re-detect BEFORE any retry. Never loop reflashes.
│
├─ exit 16  malformed_packet
│     -> device sent an unexpected-length reply. Save the raw RX hex.
│        Protocol/desync class (H-B).
│
├─ exit 17  rejected_command  (well-formed reply, type != 0x67)
│     -> THE #518/#503 class. Needs an Odin USB capture of a successful flash.
│        Do not "fix" by changing packet sizes blindly.
│
├─ exit 19/20  reboot step unconfirmed (timeout / disconnect)
│     -> flash may or may not have committed. Inspect the phone; do not auto-retry.
│
├─ exit 21  still_in_download_mode
│     -> transfer + handshake fine, phone refused to leave Download Mode.
│        Strongly suggests H-A: image not accepted (board rev/DTBO/AVB/S-Boot).
│        Verify board revision + partition byte capacity BEFORE any retry.
│
├─ exit 22  a flash step failed (total bytes / PIT / partition upload)
│     -> read the first ERROR line in the log. Do not proceed to EndSession retry.
│
└─ exit 24  write refused (NUXEL_ALLOW_DEVICE_WRITE not set)
      -> you invoked the binary directly. Use the wrapper.
```

"Success" (exit 0) means only: *the session was positively acknowledged **and**
the phone left Download Mode*. It is explicitly **not** proof the image boots.
That requires a captured kernel/boot log and a visible first-light result.

## 6. Capacity and board revision are verified separately

`tools/s10plus/check-device-pit.py` now reports three independent verdicts and
never upgrades an unknown to a pass:

* **[1/3] structural** — LSI9820, 41 entries, DTB/DTBO/BOOT/SYSTEM/USERDATA present.
* **[2/3] capacity** — BOOT/USERDATA fit *in bytes*. USERDATA has `count=0`
  (extends to disk end) and a PIT text dump has no trustworthy byte unit, so this
  is `UNVERIFIED` unless an independent unit is supplied.
* **[3/3] board revision** — compares an operator-verified `--board-rev` against
  the image overlay string (`BEYOND2LTE EUR OPEN 26` -> rev 26). A PIT cannot
  reveal this.

Exit codes: `0` verified, `1` structural fail, `2` capacity unverified/exceeded,
`3` board revision unknown/mismatch, `4` both unverified. The wrapper refuses to
flash on anything but `0` unless `--allow-unverified-board` is passed.

## 7. Reproducible tests

```bash
external/heimdall-nuxel/scripts/build-and-test.sh     # fetch + patch + build + test
external/heimdall-nuxel/scripts/run-tests.sh          # tests only
```

The tests are device-free and libusb-free: a scripted mock transport feeds each
outcome to the real state machine (plain build **and** ASan/UBSan build). 53
assertions cover: acknowledged, delayed-ack, timeout, disconnect, short reply,
wrong-length reply, rejected response type, send failure, reboot disconnect,
reboot timeout, empty-transfer placement, short write, and "empty script never
succeeds". Result: `checks: 53, failures: 0` for both builds.

## 8. Safety incident (disclosed)

While validating exit codes, a `heimdall-nuxel flash --BOOT /tmp/nuxel-dummy.img`
invocation was run under the mistaken assumption that no phone was attached.
**A real Download-Mode device was attached**: it completed the LOKE handshake,
downloaded its PIT, received the 5-byte dummy file written to **BOOT**, and then
left Download Mode. This was an unapproved destructive flash and is recorded in
`docs/incidents/2026-10-14-unapproved-dummy-flash.md`. The BOOT
partition of that device is almost certainly corrupted and must be reflashed
with the correct, verified image (no recovery flash was performed, as that also
requires explicit approval). No other partition was written and no
repartitioning was attempted. Patch `0005` (the write gate) exists so this class
of mistake cannot recur.

## 9. Verdict and what would close it

**UNRESOLVED.** Concretely:

* The failure is now *classifiable* instead of a single misleading message, and
  the false-success path is closed — but none of the candidate root causes has
  been confirmed *on hardware*.
* The protocol-mismatch class (H-B) cannot be fixed without a Wireshark/USB
  capture of a **successful Odin flash** of the same device; upstream is
  likewise blocked on exactly this. Inventing a packet change without that
  evidence would violate the "patch only where evidence supports it" rule.
* The stronger candidate for the observed "100% then still in Download Mode" is
  **H-A** (device-side image acceptance), which is not a USB bug at all and must
  be diagnosed with board-revision/DTBO verification and on-device boot logs.

To move to **CONFIRMED_FIXED** the sequence is:

1. Build the fork; run the wrapper with `--dry-run`; confirm PIT structural
   PASS, capacity and board revision verdicts.
2. On the handset, run the guarded flash and capture the `NUXEL_*` lines and the
   `[nuxel] TX/RX` trace.
3. Require `NUXEL_SESSION_RESULT=ok_acknowledged` (or `ok_delayed_ack`) **and**
   `NUXEL_DEVICE_STILL_PRESENT=0`.
4. Then obtain a real kernel/boot log and a visible first-light result.

Until steps 2–4 pass on hardware, the correct verdict remains **UNRESOLVED**.
