# NFC + Microphone + Permissions — status 2026-11-12 22:35 CET

Phone: SM-G975F (beyond2lte), root@192.168.178.167, key `~wicked/.ssh/wicked_wqn_id_rsa`.
No reflash was done; only the `boot` partition was rewritten via `dd` (24 verified flashes, every one hash-checked before and after).

## DONE and verified live

### Microphone (Ferdium / WhatsApp / Signal / ZapZap / any app)
Root cause found: the audio server runs in the **root** compositor runtime
(`/run/nuxel-wayland/pulse`), whose directory was `0700 root:root`. Any app running
as uid `nuxel` (all Flatpaks, Signal, Firefox) therefore got `Connection refused`
even though the mic captured fine as root.

Fix (live, reboot-verified): `/run/nuxel-wayland/pulse` is `0750 root:nuxel`, socket
`0770 root:nuxel`, and `/run/user/1000/pulse` is a real directory containing a
`native` symlink to the socket. Three places keep it correct:
`services/nuxel-s10/bin/nuxel-audio-session.sh` (continuous re-assert loop),
`services/nuxel-s10/bin/nuxel-audio-perms.sh` + `.service` (oneshot after boot,
waits for the socket, enabled by the live installer), and `nuxel-session.sh`.
Both helpers delete a stale `pulse` directory symlink and a self-referencing
`native` link first — that loop (ELOOP) was what kept killing the audio server.
Verified after a **full reboot**: `su nuxel -c "pactl list short sources"` lists
`alsa_input.hw_0_13` ("S10+ microphone"). Root capture RMS ≈ 180 (real audio).

Also changed: the WebKit PWA host now allows microphone from **any trusted local
origin** after the one-shot host grant (previously only the Recorder page), so any
bundled app can record a voice note once the permission is granted.

### Permissions
* Permission Manager + Settings → Permissions now show **Microphone** and **NFC**
  toggles for every app (even if the app manifest does not declare them), and a
  toggle is a real permD grant/deny.
* New: bridge/portal route `microphone` → `RequestMicrophone` and `nfc` →
  `RequestNfcAccess`, so an app asking for either now raises the on-screen
  consent card (Allow once / Allow always / Deny / Cancel).
* "Allow always" writes a durable permD grant (verified: after answering, `permD
  check` returns allowed). "Allow once" writes a one-shot record that is consumed
  by the next check (not by the verification step).
* Permission-store reads by the NFC daemon were broken by a 0640 `root:nuxel-bridge`
  store file; permD/bridge now add POSIX ACL read entries for `nuxel-bridge` and
  `nuxel`, and existing records were repaired.
* End-to-end proof (live, over the session bus): NFC prompt posted as notification
  109, answered `allow-once` → `{"success":true,"state":"granted","duration":"once"}`;
  microphone prompt 110 answered `allow-always` → granted and persisted.

### Quick Settings
* "Settings" tile: removed (Home still opens Settings).
* "Verbose boot" tile: removed (switch lives in Settings → Developer).
Verified: `qs.js` and `index.html` contain no tile markup for either.

## NFC — hard blocker, needs a decision

What is now **working** (verified in the running kernel):
* The NFC core, the `nfc0` device and the S3FWRN5 NCI driver are all in the kernel
  image, and the driver now binds 7-0027 instead of the legacy `sec-nfc` transport
  (ordering fixed: s3fwrn5 registers at `device_initcall`, sec-nfc defers one pass).
* The driver correctly registers `nfc0` (`/sys/class/nfc/nfc0`) and the daemon sees
  it through generic netlink (`NFC_CMD_GET_DEVICE` → index 0, protocols 222).
* The NFC 1.8 V rail (`VDD_NFC_1P8`) is enabled by the probe.

What blocks tag I/O:
1. **The NFC reference clock reads 0 Hz.** `devm_clk_get("oscclk_nfc")` succeeds and
   `clk_prepare_enable()` returns 0, but `clk_get_rate()` is 0. A digital controller
   cannot answer anything without its clock. (The vendor's `sec-nfc,clk_req-gpio`
   gate wiring is documented in `sec_nfc.c`; the vendor driver does not enable the
   clock itself either — the Android clock framework pre-enables it.)
2. With the clock off, the part does not answer NCI `CORE_RESET` (the old `DEV_UP`
   failure was this). In bootloader mode it returns a coherent GET_BOOTINFO reply
   (hw 82.00.01.00, sector 4096, page 512), so the framing/IRQ path works.
3. The GET_BOOTINFO **23-byte reply layout** of this part is not the 10-byte upstream
   layout; the NCI framing after mode switch is still the upstream one and remains
   unverified against a working reference.
4. The shipped firmware is **byte-identical** to the pinned vendor blob
   (`d315cd8b…`, 2018-12-27, 37 sectors) — there is no newer image to flash and the
   vendor tree has no `rfreg` file for this device.
5. After a failed NCI probe the node falls back to `sec-nfc` (by design), so the
   current boot is honest but has no `nfc0`.

Decision needed (one of):
* **(A)** Accept the current state (driver, daemon, permissions and consent all
  correct; tag I/O blocked by hardware clocking). Next boot must then use a boot
  image whose probe succeeds — or the legacy transport — and NFC reports
  "blocked: NFC clock" instead of a fake success.
* **(B)** Authorise one more boot-image experiment that pre-enables the NFC clock
  in the probe path (e.g. walk the `oscclk_nfc` parent chain / use the CLKOUT1 mux)
  and retries `CORE_RESET`. That is another `dd` of `boot` (no rootfs reflash).
* **(C)** Stop here on NFC and ship everything else.

## Boot images produced this round
`build/out/s10plus/debug-candidates/p111000-nfc-handshake/` — `boot-nfc-v5…v22.img`,
all pass `tools/s10plus/verify-boot-image.py`; `v20` is the last image that boots
with the full NFC daemon path (binds s3fwrn5 only when the bootloader answers).
v25 (#30) adds the vendor "NPT" power-on sequence (VEN asserted 20 ms, then FIRM
high) before the handshake; outcome unchanged: `GET_BOOTINFO(-ENXIO)`, s3fwrn5
declines, `sec-nfc` binds. **Current boot partition is v25 (#30).**

## Live deployment
`scripts/nuxel-deploy-live.py --host 192.168.178.167 --user root --apply` ran twice;
all services active (`nuxel-bridge`, `nuxel-http-bridge`, `nuxel-soundd`,
`nuxel-clockd`, `nuxel-nfcd`, `nuxel-permd`, `nuxel-portal`, `nuxel-consent-agent`).

## Extra evidence gathered after the first write-up
* `/sys/kernel/debug/clk/clk_summary` is unavailable (debugfs not mounted); the
  probe prints `oscclk_nfc enabled (0 Hz)` and `clk_set_rate(26 MHz) = 0`.
* The clock is a CAL virtual clock (`cal_clk_enable`/`cal_clk_getrate`) driven by
  the TEE/CMU calibration daemon; on this image the firmware/CMU side never
  programs `OSC_NFC` (CLKOUT1). The vendor `nfc_nci.*.so` HAL is not in the
  public vendor-blob tree, so its exact sequence cannot be copied.
* Bootloader-mode framing works (GET_BOOTINFO reply), NCI-mode framing does not
  get a single IRQ — consistent with "no reference clock".
* After a failed NCI probe the node deliberately returns to `sec-nfc`, which is
  functional (no panic, no bootloop). `nuxel-nfcd` keeps running and reports
  `kernel_nci.present=false` (honest, no fake success).
