codex
Definitive: in NCI runtime mode the chip never ACKs, even after cold boot. It only speaks bootloader. So the flash has **no valid NCI firmware** (or the bootloader-mode default). This requires the firmware download to complete, which needs the proper mailbox — the `s3fwrn5` driver.

I have exhausted safe remote approaches. The honest, responsible conclusion: NFC needs the `s3fwrn5`-owns-device image next round. Let me make sure the delivered state is correct and give the user a complete report.
exec
/bin/zsh -lc "ssh -i ~/.ssh/wicked_wqn_id_rsa -o BatchMode=yes root@192.168.178.167 'uptime; systemctl is-system-running; systemctl is-active nuxel-nfcd nuxel-bridge nuxel-permd; echo \"=== NFC honest status via daemon ===\"; python3 -c \"
import sys,json; sys.path.insert(0,\\\"/usr/lib/nuxel/nuxel-nfc\\\")
from nuxel_nfc.daemon import *\" 2>&1 | head -3; cat /run/nuxel/nfc/state.json 2>&1 | head -20' 2>&1 | tail -12" in /Users/wicked/x/nuxel
 succeeded in 618ms:
  "last_scan_finished": 0.0,
  "last_scan_started": 0.0,
  "last_tag_present": false,
  "payment_supported": false,
  "pid": 5757,
  "protocol": "NCI 1.0/2.0 via kernel s3fwrn5_i2c (nfc0)",
  "schema": "nuxel.nfc-daemon/1",
  "state": "ERROR",
  "tag_writes_supported": true,
  "updated_at": 1794573525.7656786,
  "write_requires_confirmation": true
}

codex
The daemon honestly reports `ERROR` (no fake success). Good — the system is truthful.

I've spent an enormous amount of effort and reached a well-characterized hardware/firmware blocker. Let me give the user a complete, honest status report as instructed. First, ensure everything committed.
exec
/bin/zsh -lc 'cd /Users/wicked/x/nuxel && git status --short nfc3.md kernel/s10plus/patches/001[789]* 2>/dev/null; git log --oneline -3; echo "=== live image ==="; echo "kernel #52, boot-nfc-ese-v18.img sha 1f56f16cea1a38fd"' in /Users/wicked/x/nuxel
 succeeded in 0ms:
597db284 (HEAD -> feature/v0.8.3-beta-screen-off) docs(nfc): final session status — bootloader proven, NCI transition pending s3fwrn5 ownership
723c425f feat(nfc): eSE gate bypass, forced/hold reference clock, eSE panic fix
cf1ff930 feat(nfc/mic/permissions): NFC NCI bring-up, microphone for session-user apps, live consent grants
=== live image ===
kernel #52, boot-nfc-ese-v18.img sha 1f56f16cea1a38fd

codex
All committed. The device is stable and healthy. Here is my honest status report.

## Status: NFC still NOT reading tags — but the blocker is now precisely identified, no reflash of the rootfs needed

### ✅ Fixed and live this round (kernel **#52**, `boot-nfc-ese-v18.img`, device stable & healthy)

I found and fixed **three real kernel defects** that were the actual reason NFC never worked — none of them were the "0 Hz clock" story from before:

1. **eSE TEE gate (0017)** — `/dev/sec-nfc` could never be opened: `CONFIG_ESE_SECURE` made `sec_nfc_open()` call the TEE eSE check (a Samsung-Pay check, unrelated to the reader), fail, and return `-EBUSY`. Worse, the naive bypass leaked the TEE result `0xffff000d` as a pointer and **panicked the kernel** under `oops=panic`. My final patch records the eSE state without calling the TEE + adds a NULL guard. `/dev/sec-nfc` now opens/closes cleanly, repeatably.
2. **Reference clock never turned on (0018)** — this S3NRN82 does **not** assert `clk_req` before it's clocked, so the IRQ-driven gating left `oscclk_nfc` off forever. Now force-enabled for every active mode.
3. **Clock gated between frames (0019)** — the write ACKs but the next read NACKs because the clock is gated per-frame. Now held for the whole open session.

Also: the **SSP sensor bring-up** (today's separate work) was hanging the kernel watchdog and **rebooting the phone during NFC tests** — I masked `nuxel-ssp-bridge` and set `hung_task_panic=0`. That crash was *not* NFC.

### ✅ Other requested items — verified live
- **Microphone**: `alsa_input.hw_0_13` visible to the session user (`nuxel`).
- **Deploy**: `scripts/nuxel-deploy-live.py --apply` ran; bridge/http/soundd/clockd/nfcd/permd/portal/consent-agent all active.
- **Permissions**: `microphone` + `nfc` capabilities live; consent flow intact from the prior commit.
- **Quick Settings**: "Settings" and "Verbose boot" tiles gone (the builder is a documented no-op).

### ⚠️ The remaining NFC blocker (precise, measured)
With the clock held, the chip now **answers its bootloader** — `GET_BOOTINFO` → `82.00.01.00, sector 4096, page 512`. But:
- It **does not ACK** `ENTER_UPDATE_MODE`/`UPDATE_SECTOR`/`COMPLETE_UPDATE_MODE` — `sec_nfc`'s read path replays the stale bootinfo frame.
- In **NCI runtime mode** the chip **never ACKs its I2C address** (even after a cold boot) → the flash has no valid NCI firmware.
- So firmware must be downloaded, which needs the kernel **`s3fwrn5_i2c`** driver's mailbox (it already has `s3fwrn5_fw_download` + the NCI switch), but `sec-nfc` currently owns 7-0027 and yields only when `s3fwrn5` fails its handshake.

### ▶️ Next round — **one boot-image revision, no rootfs reflash, no TWRP needed**
I can write it from Nuxel over SSH (`dd` to `/dev/sda14` only, as done 4× today, every hash verified). The change: let **`s3fwrn5_i2c` own 7-0027** and hold `oscclk_nfc` across probe → bootloader handshake → firmware download → NCI switch (reuse the 0018/0019 clock-hold technique). That's the correct architecture and the last missing piece. Rollback image is on-device (`/tmp/pre18.img`) and `backups/boot/boot-orig-20261113.img`.

Committed: `723c425f` + `597db284`. Full details in `nfc3.md`.
All committed. The device is stable and healthy. Here is my honest status report.

## Status: NFC still NOT reading tags — but the blocker is now precisely identified, no reflash of the rootfs needed

### ✅ Fixed and live this round (kernel **#52**, `boot-nfc-ese-v18.img`, device stable & healthy)

I found and fixed **three real kernel defects** that were the actual reason NFC never worked — none of them were the "0 Hz clock" story from before:

1. **eSE TEE gate (0017)** — `/dev/sec-nfc` could never be opened: `CONFIG_ESE_SECURE` made `sec_nfc_open()` call the TEE eSE check (a Samsung-Pay check, unrelated to the reader), fail, and return `-EBUSY`. Worse, the naive bypass leaked the TEE result `0xffff000d` as a pointer and **panicked the kernel** under `oops=panic`. My final patch records the eSE state without calling the TEE + adds a NULL guard. `/dev/sec-nfc` now opens/closes cleanly, repeatably.
2. **Reference clock never turned on (0018)** — this S3NRN82 does **not** assert `clk_req` before it's clocked, so the IRQ-driven gating left `oscclk_nfc` off forever. Now force-enabled for every active mode.
3. **Clock gated between frames (0019)** — the write ACKs but the next read NACKs because the clock is gated per-frame. Now held for the whole open session.

Also: the **SSP sensor bring-up** (today's separate work) was hanging the kernel watchdog and **rebooting the phone during NFC tests** — I masked `nuxel-ssp-bridge` and set `hung_task_panic=0`. That crash was *not* NFC.

### ✅ Other requested items — verified live
- **Microphone**: `alsa_input.hw_0_13` visible to the session user (`nuxel`).
- **Deploy**: `scripts/nuxel-deploy-live.py --apply` ran; bridge/http/soundd/clockd/nfcd/permd/portal/consent-agent all active.
- **Permissions**: `microphone` + `nfc` capabilities live; consent flow intact from the prior commit.
- **Quick Settings**: "Settings" and "Verbose boot" tiles gone (the builder is a documented no-op).

### ⚠️ The remaining NFC blocker (precise, measured)
With the clock held, the chip now **answers its bootloader** — `GET_BOOTINFO` → `82.00.01.00, sector 4096, page 512`. But:
- It **does not ACK** `ENTER_UPDATE_MODE`/`UPDATE_SECTOR`/`COMPLETE_UPDATE_MODE` — `sec_nfc`'s read path replays the stale bootinfo frame.
- In **NCI runtime mode** the chip **never ACKs its I2C address** (even after a cold boot) → the flash has no valid NCI firmware.
- So firmware must be downloaded, which needs the kernel **`s3fwrn5_i2c`** driver's mailbox (it already has `s3fwrn5_fw_download` + the NCI switch), but `sec-nfc` currently owns 7-0027 and yields only when `s3fwrn5` fails its handshake.

### ▶️ Next round — **one boot-image revision, no rootfs reflash, no TWRP needed**
I can write it from Nuxel over SSH (`dd` to `/dev/sda14` only, as done 4× today, every hash verified). The change: let **`s3fwrn5_i2c` own 7-0027** and hold `oscclk_nfc` across probe → bootloader handshake → firmware download → NCI switch (reuse the 0018/0019 clock-hold technique).tokens used
 That's the correct architecture and the last missing piece. Rollback image is on-device (`/tmp/pre18.img`) and `backups/boot/boot-orig-20261113.img`.

Committed: `723c425f` + `597db284`. Full details in `nfc3.md`.
86,506,565
[codeseeq] stopping owned bridge process (pid=84285)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel
╰─❯❯❯ 


---

## CONTINUATION 2026-11-13 (third session) — s3fwrn5 owns 7-0027, measured hardware limit on NFC

Kernel **#64** (`boot-nfc-custom-fw-v28.img`) is live and boots reliably.  The
NCI driver now owns the controller, `/sys/class/nfc/nfc0` exists and the NFC
service is healthy.  **Tag reading still does not work**, and the reason is now
a measured, reproducible hardware/transport limit rather than missing code.

### What was fixed for real (all verified on the handset, rolling flash)
* **Boot loop root cause** — the first attempt ran a 2-4 s bootloader poll
  inside the `device_initcall`; that starved the UFS RPMB worker and panicked
  at `scsi_srpmb-teegris.c:374` ("timeout while waiting for scsi device").
  Probe is now short, never fails, and all controller work runs from a
  workqueue with retries.  The phone boots every time on #60..#64.
* **NULL-deref boot loop** — a bootloader reply arriving before the firmware
  completion was initialised faulted in `__wake_up_common` (the `BUG_ON` was
  after the fault).  The completion is initialised in `s3fwrn5_probe()`.
* **Late/duplicate frame BUG_ON** — `s3fwrn5_fw_recv_frame()` no longer
  `BUG_ON(fw_info->rsp)`; a newer reply replaces an unconsumed one.
* **Wrong firmware name** — the driver asked for `sec_s3fwrn5_firmware.bin`;
  the part ships `sec_s3nrn82_firmware.bin` (`/lib/firmware/nfc/` and
  `/vendor/firmware/nfc/`, hash `d315cd8b…`).  The driver now tries the board
  image first and cleans up a failed request safely (no double release).
* **Custom firmware signature** — GET_BOOTINFO reports `hw_version[2]=0x01`;
  this image is a *custom-format* image (header 0x10=0x45, 0x11=0x09) whose
  172-byte custom signature at 0x24 must be sent, not the 128-byte standard
  signature (0x14).  `firmware.c` now selects it from the bootloader reply.
* **Firmware transfer size** — a 256-byte data packet needs a 260-byte frame,
  which the kernel i2c core refuses as one message.  Added a `write_bulk`
  transport op that sends the complete frame in one transfer.
* **Reference clock** — `oscclk_nfc` is a CAL vclk CLKOUT (PMU-selected); it
  has no settable rate, so the previous `clk_set_rate(26 MHz)` "success, 0 Hz"
  was a red herring.  Prepare/enable is the whole operation and it is held for
  the whole NCI session.
* **Flash pacing** — `ENTER_UPDATE_MODE`/signature and each `UPDATE_SECTOR`
  are separated from the following command (the bootloader ACKs before it has
  committed the write), and the custom-format reply timeout is 5 s.

### The measured blocker (decisive)
On a *fresh power cycle* (rail dropped, VENDOR NPT order: VEN, wait, FIRM) the
S3NRN82 accepts exactly **one** frame and answers it:

```
nci rx: 81 00 0e 00 82 00 01 00 00 10 00 02 06 01 00 02
        hw=82.00.01.00  sector=4096  page=512  frame=262  ...
```

Every following transaction on hsi2c 0x108E0000 wedges the bus:

```
hsi2c 108e0000: SDA check timeout AT READ!!!  SDA : HIGH, SCL : LOW
                rx timeout -> xfer message failed -> -EIO (-121)
```

There is no address ACK for the second frame, so a *raw* NCI `CORE_RESET`
(0x20 00 01 00) is never answered (`-110`), and a firmware download (>= 600
frames) is impossible on this path.  Because the very first frame is
consumed by the read, bootloader mode leaves the part in this state; the
`OPEN`/`PROBE` trick did not reset it either.  This is unchanged across
#52 (v18 `sec_nfc`), #60-#64: NFC never reads tags in any build so far, and
`sec_nfc` also only ever answered its bootloader probe (nfc3/nfc4).

### What would unblock it (needs a decision, not more blind flashing)
1. A reference signal that truly drives OSC_NFC externally / a vendor NCI
   reset that leaves the part in a readable runtime state (hardware).
2. Confirming how the stock ROM loads the S3NRN82 image (S-Boot partition or
   a bootloader NCI mode) and mirroring exactly that entry, i.e. what makes
   the part enter NCI runtime without a driver download.
Until then the kernel deliberately does **not** fake success: the NFC state
stays `ERROR`/no tag, all boot paths are stable, and no rootfs reflash is
required (only `/dev/sda14` = boot was rewritten, each write hash-verified).
