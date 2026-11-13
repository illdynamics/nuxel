All details, evidence and artifacts are in `NFC-STATUS-20261112.md`; the work is committed as `cf1ff930`, and all services are healthy on the phone now.
I picked up where the last session stopped. Here's the honest state — most of what you asked is **live and verified**, but **NFC tag reading is not working yet** and needs a decision from you.

## ✅ Done, deployed live, verified after a reboot

**Microphone (Ferdium, WhatsApp, Signal, ZapZap, Teams…)**
- Real root cause: the audio server runs as root, and its pulse socket directory was `0700 root:root`, so every app running as your user got "Connection refused" — the mic worked as root only.
- Fixed and made reboot-proof (session script loop + new `nuxel-audio-perms` unit). After a full reboot, the session user now lists `alsa_input.hw_0_13` ("S10+ microphone").
- WebKit apps can now also capture audio from any trusted local app (previously only the Recorder).

**Permissions**
- **Microphone** and **NFC** toggles now exist in both Permission Manager and Settings → Permissions, and are real grants.
- An app asking for mic or NFC now raises the on-screen card with **Allow once / Allow always / Deny / Cancel** (previously these never reached the prompt). Tested live: "Allow once" and "Allow always" both succeeded, and "Allow always" is persisted in permD, which Settings reads back.
- Fixed a store-permission bug that stopped the NFC service from reading grants.

**Quick Settings**
- "Settings" and "Verbose boot" tiles are gone (the verbose-boot switch lives in Settings → Developer).

## ⚠️ NFC — genuinely blocked by hardware clocking

What now works: the kernel NFC driver owns the controller and registers `nfc0`; the daemon talks to it via netlink; the rail, pins and IRQ are correct. No reflash of the rootfs was needed — I only rewrote the `boot` partition via `dd`, every time hash-verified.

What fails: **the NFC reference clock reports 0 Hz**. `clk_set_rate(26 MHz)` returns success but the clock stays at 0, so the chip answers in bootloader mode but never answers the NCI `CORE_RESET` — no tag can be read.

I also confirmed there is **no newer firmware to flash**: the shipped image is byte-identical to the pinned vendor blob.

The phone is currently booted with the safe fallback (legacy `sec-nfc` bound, no `/dev/nfc0`), so it boots normally.

## Your call for next round
1. **Accept** NFC as blocked-by-clock (everything else stays), or
2. **One more boot-image experiment** (another `dd` of `boot` only) where the probe pre-programs the `OSC_NFC` CAL clock path and retries `CORE_RESET` — best remaining chance, not guaranteed.

tokens used
All details, evidence and artifacts are in `NFC-STATUS-20261112.md`; the work is committed as `cf1ff930`, and all services are healthy on the phone now.
180,584,761
[codeseeq] stopping owned bridge process (pid=79462)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel


---

## CONTINUATION 2026-11-13 (second session) — decisive findings

### Proven on the live device (kernel #48, boot-ssp-v14, sec-nfc currently bound)
1. NFC chip answers on I2C: `i2cdetect -y -r 7` shows `UU` (claimed) at 0x27.
2. **`/dev/sec-nfc` cannot be opened today**: `open()` returns -EBUSY because
   `CONFIG_ESE_SECURE=y` makes `sec_nfc_open()` call `tz_tee_ese_secure_check()`
   (`ese_p3.c`), which logs
   `tz_tee_ese_drv, cmd Resume result=0xffff000d origin=0x3` and then
   `[sec_nfc] sec_nfc_open: eSE spi is not Secured`.
   This is the **eSE (embedded Secure Element / Samsung Pay) TEE gate**, not NFC.
   Nuxel does not use the eSE, so this gate has no reason to block the NFC
   reader path, and it makes the ONLY working userspace transport unusable.
3. The CAL clock model is fully mapped (see below) — `OSC_NFC` = gate-VCLK
   `VCLK_CLKOUT1`, and `ra_enable_clkout()` writes PMU `0x15860A0C`
   (bit0 enable, `1 = gate OFF`, bits[13:8] sel = `0` = TCXO).  Live `/sys/kernel/debug/vclk`
   exists (927 vclk entries + `clk_info`/`set_freq`), but **`OSC_NFC` and
   `VCLK_CLKOUT1` are NOT in the vclk debugfs list** → the clock object the
   `s3fwrn5_i2c` probe enabled is a separate `clk` from the clock provider, and
   the debugfs never sees it under that name.
4. Reference implementation (LineageOS `android_kernel_samsung_exynos9820`,
   `lineage-22.2`) is byte-identical in `drivers/clk/samsung/clk-exynos9820.c`,
   `composite.c` (`cal_vclk_enable`), `cal-if/vclk.c`, `cal-if/ra.c` and
   `cal-if/exynos9820/clkout_exynos9820.c`.  It also keeps `sec-nfc` bound with
   a `clk_req` GPIO IRQ and does **not** call `clk_prepare_enable` at probe.

### Two concrete defects to fix (both kernel-side)
* **D1 — eSE gate blocks NFC.**  With `CONFIG_ESE_SECURE`, `sec_nfc_open()`
  hard-fails when the TEE eSE check fails.  Fix: when the TEE reports the eSE
  is not secured, continue opening the **NFC** misc device (NFC reader does not
  need the secure element).  Keep the eSE itself gated.
* **D2 — probe-time power sequence.**  `sec_nfc_set_mode()` does
  VEN=OFF → wait 20 ms → VEN=ON → wait 10 ms, then enables the clk_req IRQ.
  The patched `s3fwrn5_i2c` probe used VEN=1 (OFF) then VEN=0 (ON) but drives
  FIRM based only on the target mode; it never opens the clk_req window before
  waiting for the `GET_BOOTINFO`/NCI reply, so the chip may not see its 26 MHz.

### Next action this session
* Produce patch `0017-nuxel-sec-nfc-ese-gate.patch` (D1).  This makes the
  already-deployed `SecNfcTransport` + `NciController` (already NCI-framed in
  the `sec_nfc_write()` code from commit cf1ff930) reachable.
* Build a new boot image on top of `boot-ssp-v14` (so the SSP / userns work is
  kept) with only this patch, flash boot partition only, then test NFC end to
  end with `services/nuxel-nfc` over `/dev/sec-nfc`.
* If that answers `CORE_RESET`, add the clk_req timing fix (D2) as a second
  image only if needed.

---

## CONTINUATION 2026-11-13 (afternoon) — NFC brought up to bootloader, NCI runtime pending

### What was fixed and deployed live (commit pending)
Kernel `#52` (`boot-nfc-ese-v18.img`, sha `1f56f16c…`) booted and stable:
* **0017** — `sec_nfc`: the eSE TEE gate no longer blocks the NFC reader.  Before
  this patch `open("/dev/sec-nfc")` hard-failed; with the naive bypass the TEE
  result `0xffff000d` leaked into the kernel open path and panicked under
  `oops=panic`.  Final patch records the eSE as "not secured" **without** calling
  the TEE and adds a NULL guard; `open()` now works.
* **0018** — `sec_nfc`: force `oscclk_nfc` on for every non-OFF mode.  This board's
  S3NRN82 does not assert `clk_req` before it is clocked, so the IRQ-driven gating
  left the 26 MHz reference permanently off.
* **0019** — `sec_nfc`: hold the reference clock for the whole open session (the
  `clk_req` line toggles per frame and gating between frames NACKs the next read).
* `nuxel-ssp-bridge` masked on the device; `kernel.hung_task_panic=0` persisted in
  `/etc/sysctl.d/95-nuxel-nohungpanic.conf`.  Before this, the **SSP bring-up**
  (today's separate work) hung the kernel watchdog and rebooted the phone during
  NFC tests; that is not an NFC defect.

### Proven on hardware after the fix
* `/dev/sec-nfc` opens/closes without crashing (repeatable).
* I2C 0x27 ACKs.
* Bootloader **GET_BOOTINFO answers**: `82 00 01 00 | sector=0x1000 page=0x0200`.
* A raw `GET_BOOTINFO` downloader drove the part and got coherent replies.

### Remaining blocker (precise)
The S3NRN82 answers **bootloader** commands but does not acknowledge
**ENTER_UPDATE_MODE / UPDATE_SECTOR / COMPLETE_UPDATE_MODE**: every reply is the
stale 14-byte bootinfo frame (`81 00 0e 00 …` with the code byte flipping to
`0x80` by parity).  `sec_nfc`'s read path does not do the mailbox
clear/ack that `s3fwrn5`'s firmware.c does, so the part never leaves bootloader
and NCI runtime mode NACKs its address (`-ENXIO` on every write).

**Correct fix (one more boot image):** let the kernel `s3fwrn5_i2c` driver own
7-0027 instead of `sec-nfc`, and hold `oscclk_nfc` enabled across its probe +
bootloader handshake (it already implements the firmware download + NCI switch).
The `sec_nfc` yield-to-s3fwrn5 logic exists (patch 0007) but the probe's
handshake ran before the clock was reliably held on, so it declined and
`sec-nfc` re-bound.  With the clock-hold knowledge from 0018/0019 applied to the
`s3fwrn5` probe, the NCI core can run CORE_RESET/CORE_INIT and RF discovery.

### Other requests — verified live this round
* Microphone visible to the session user: `alsa_input.hw_0_13` via
  `XDG_RUNTIME_DIR=/run/user/1000 pactl`.
* `scripts/nuxel-deploy-live.py --apply` ran: bridge/http/soundd/clockd/nfcd/
  permd/portal/consent-agent all active.
* Permission capabilities deployed with `microphone` + `nfc` entries; Quick
  Settings "Settings"/"Verbose boot" tiles remain removed (`_buildVerboseBootTile`
  is a documented no-op).
