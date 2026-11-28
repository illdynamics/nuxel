# NUXEL S10+ — Full Hardware Component State and Camera Fault Audit
**Date:** 2026-11-20  
**Input:** User-provided `nuxel-main (1)(1).zip` (complete, readable ZIP, unlike an older corrupted camera attachment referred to by the existing V2 audit)  
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte`, Exynos9820 board rev 26, Samsung-derived kernel 4.14.253, Nuxel `v0.9.1-beta` repository  
**Evidence level:** source files, embedded documentation, older recorded live-device tests, current independent static inspection and host-only tests. **Not a fresh phone session.**

## Scope and integrity

The uploaded ZIP expands to a full Nuxel source archive with approximately 18,598 regular files (~809 MB extracted) plus directory entries. It has a camera V2 kit, sensor V2 kit, services, desktop/PWA/Flatpak integrations, firmware manifests, multiple historic hardware trace folders, media tools and kernel patches. **Missing from this archive:** `.git`, full kernel checkout/build tree, the referenced root `reports/` directory, owner's separate CP/AP archives, a fresh physical connection, and proof that the patched kernel is what the phone currently boots. Named commits in reports cannot be reverified from this archive.

**Report labels:** `Verified in ZIP` means code/data are present and inspected. `Recorded live` means an earlier dated test describes a physical result. `Unverified` means no real-world completion evidence in this attachment. Never promote a configured UI or /dev node into end-to-end success.

## Camera — primary workstream / BLOCKED_FIRMWARE + CAPTURE + APPLICATION INTEGRATION

### Device topology

- Controller: FIMC-IS `170e0000.fimc_is`; kernel 4.14.253 downstream FIMC-IS2 camera pipeline, CSI/EEPROM/OIS/actuators registered.
- Rear main: 2L4 (`setfile_2l4.bin`); rear tele 3M3; rear ultrawide 3P9; front main 3J1; front depth/IR 4HA. `docs/a52-camera/HARDWARE-INVENTORY.md` records role, bus, modules and board revision.
- Video nodes include `exynos-fimc-is-ss0..ss5`, `exynos-fimc-is-30*`, `-31*`, `-32*`, ISP nodes and virtual channels; approximately 68 FIMC-IS nodes. They are **not** all image-capture endpoints, and MFC / JPEG / scaler nodes should not be confused with camera.
- Historically `/dev/media*` and `/dev/v4l-subdev*` absent. Legacy Samsung vendor IOCTL and MPLANE support cannot be assumed equivalent to generic UVC V4L2, and a standard `VIDIOC_S_FMT` returned `ENOTTY`, buffer requests `EINVAL` in earlier tests.
- `tools/s10plus/fimc-capture/nuxel-fimc-capture.c` is a dedicated MPLANE tool with explicit sensor-init opt-in, formatting / buffer checks and JSON evidence; it **builds natively on the audit host** but a valid phone frame remains unverified.

### Firmware truth (highest-priority forensic finding)

Repo `firmware/s10plus/camera-stock-DTK9.json` says its eight camera firmware blobs were independently re-extracted from owner's original `G975FXXS9DTK9` Android 10 AP, and the uploaded binaries **all match this owner-stock manifest** by independent SHA-256 verification. The archive `firmware/s10plus/manifest.yml` instead pins Linux4 public vendor commit `05c9ef8f16e0ad5ab274e408c120dfd99fd5c628`; those public-reference checksums match only **one of eight** bundled files.

| File | Size | Owner stock vs bundled | Linux4 pinned reference |
| --- | ---: | --- | --- |
| `fimc_is_fw_mcu.bin` | 34,348 B | Match | Match |
| `fimc_is_lib.bin` | 4,432,944 B | Match | Mismatch |
| `fimc_is_rta.bin` | 3,986,208 B | Match | Mismatch |
| `setfile_2l4.bin` | 4,080,120 B | Match | Mismatch |
| `setfile_3j1.bin` | 3,944,440 B | Match | Mismatch |
| `setfile_3m3.bin` | 2,858,784 B | Match | Mismatch |
| `setfile_3p9.bin` | 3,265,896 B | Match | Mismatch |
| `setfile_4ha.bin` | 3,944,440 B | Match | Mismatch |

`setfile_3j1.bin` and `setfile_4ha.bin` have identical hashes in the owner's stock extraction AND identical pairs in the Linux4 reference; do not call that alone corruption. A file that matches Android 10 *stock* does **not** prove that its ISP DDK binary ABI matches the **running** Nuxel kernel, which appears to be derived in part from a later source branch. Existing `tools/s10plus/camera-recovery/prepare.py` intentionally blocks unverified DDK ABI deployment.

### Last recorded physical failure

Latest camera recovery evidence describes a *bounded*, owner-permitted rear-main 2L4 sensor selection that reached EEPROM/calibration and returned:

```
Camera: Failed open phone firmware
fimc_is_sec_run_fw_sel ... (-5)
```

`-5` is Linux `-EIO`, not a reliable missing-file diagnosis. The source must be traced to the first failing read, name, path, version or calibration predicate, observing which earlier warnings are consequential. A previous camera report referenced this but the complete `reports/CAMERA-RECOVERY-2026-11-17.md` and `reports/CAMERA-FIRST-REAL-FRAME.md` are **not in the ZIP**.

### Special kernel patch: inspect whether compiled AND booted

`kernel/s10plus/patches/0022-nuxel-fimc-is-linux-firmware-paths.patch` modifies `request_binary()` in `drivers/media/platform/exynos/fimc-is2/fimc-is-binary.c` to attempt `/lib/firmware/` and `/usr/lib/firmware/` and log `path-linux load(<path>) ret(<errno>)`. Existing vendor paths and `request_firmware()` fallback remain. The patch header notes OEM Android paths do not exist on Nuxel's rootfs; this is a plausible causal fix, **not proven active on the live phone**. The associated header defines `FIMC_IS_FW = "fimc_is_fw.bin"`, a filename not included among the eight verified stock blobs. The exact runtime `load_fw_name` may be module-specific; determine requested basename from source + live log before fetching or renaming anything. Do not replace `fimc_is_fw.bin` with `fimc_is_fw_mcu.bin` on speculation.

### User-space camera bugs independently identified

- `shell/nuxel-camera-portal/nuxel_camera_portal_impl.py`: `camera_present()` returns true if *some* FIMC nodes and a PipeWire socket exist. That may declare the camera present despite no camera producer streaming frames. **Require a validated real source and readiness check.**
- Same file's `OpenPipeWireRemote()` calls `os.open()` on a Unix-domain socket pathname. The standard portal needs an actual connected PipeWire remote FD via supported mechanisms, proper D-Bus FD ownership and restricted client permissions; opening the path like a regular file is not a valid substitute.
- `shell/nuxel-camera-portal/nuxel_camera_portal.py` still creates `v4l2src device=<Samsung FIMC node> ... ! pipewiresink` although its own comment acknowledges standard V4L2 ioctl rejection. Replace / adapt capture source only after a real working sensor-to-ISP path. `synthetic-colorbar` must stay separately labeled for VM demos, never count as real physical camera success.
- `shell/nuxel-camera-native/nuxel_camera_native.py` has GTK UI with honest `capture_verified` gating and intended `pipewiresrc → gtk4paintablesink`, but no verified physical frame feed. `pwa/nuxel-apps/camera-gallery/js/camera.js` calls `navigator.mediaDevices.getUserMedia`, controls permission/recording/gallery; backend not verified.
- Standard camera portal implementation exists, correcting older historical documentation's *absence of an implementation*; actual deployment, correct protocol and stream still need validation. Ensure portal permission store, private bridge and PWA prompts are consistently fail-closed.

### Camera recovery fault tree

1. Match current device/boot/source, ensure patch 0022 is truly active; find all loader paths, effective firmware rootfs mount points and requested firmware names.
2. Determine whether `fimc_is_sec_run_fw_sel` fails because of missing phone FW basename/path, ownership/perms, EEPROM/CRC, incompatible DDK, bad calibration branch or rejected module version. Annotate exact source file/function/return.
3. Reconcile owner-stock 8/8 hash identity against public manifest and running kernel ABI; choose one coherent, individually documented candidate group; preserve authoritative owner stock and hash manifests unmodified.
4. Stage minimal host-side fix and tests. Do not auto-flash; get approval for exact file/writes, recovery and rollback first.
5. Once approved, capture **one** genuine 2L4 frame with valid negotiated width/height/fourcc/plane sizes, QBUF/STREAMON/DQBUF/STREAMOFF, nonzero bytes and two real-scene changes; store hash/timing/format and review kernel faults.
6. Repeat for the other four physical modules, controls, photos and video. Ensure no false screenshot/virtual test source success.
7. Implement a functioning PipeWire camera publisher and standard camera portal, then verify GTK, PWA, Flatpak and third-party conferencing/camera consumers with permission allow/deny/revoke, front/rear, suspend/resume, multiple sequential sessions and hot-restarts.

**Success gate:** 1 physical frame != full camera; `CAMERA_FULLY_FUNCTIONAL` only when all supported modules and app matrix pass on actual phone.

## Mobile networking — BLOCKED_FIRMWARE / NOT_CONNECTED

**Recorded live:** Samsung Shannon S5000AP modem controller, `/dev/umts_boot0`, `/dev/umts_ipc*` and RFS channels, `rmnet0..7`, kernel driver and SIPC/SHMEM/secure boot infrastructure. CP in `OFFLINE (0)` state; ModemManager 1.24.2 detected zero supported modems. Generic AT/QMI/MBIM/standard Samsung plugin do not constitute a verified Shannon transport. No confirmed SIM state, network registration, LTE bearer, SMS, calling or IMS/VoLTE.

**Progress beyond early missing firmware:** `mobile.md` documents the owner **already has** a model/build-matching CP package: `CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`, with `modem.bin.lz4`, `modem_debug.bin.lz4`. This separate archive is not in uploaded ZIP. Reuse owner-host AP/CP, validate identity, compare Samsung `cbd` (`cpboot_v3`) to the exact kernel, then develop native transport, modem manager integration and bearer. CP firmware presence on host != phone boot. No partition/IMEI/EFS modifications.

**Next acceptance:** CP boots with valid IPC, SIM detected, modem registration and real mobile data across airplane-mode/resume, then test SMS, voice and IMS independently.

## SSP / auto-rotation — BLOCKED_VENDOR_RUNTIME

**Recorded live:** Broadcom BCM47752-family BBD sensorhub, ST LSM6DSO 6-axis accelerometer/gyro enumerated, `/dev/bbd_sensor`, `/dev/bbd_control`, `/dev/bbd_patch`. Kernel `ssp_down=true`, `enable=0`; accelerometer/gyro raw samples `0,0,0`. Seven rotation policy modes and compositor transform + touch matrix are **live verified** manually, but physical auto-rotate cannot work with no real sensor stream.

**Tools present:** `NUXEL_SSP_RECOVERY_V2/`, `tools/s10plus/ssp-runtime`, stock `lhd`/`lhd.conf` references, embedded BBD patch and host-side Bionic closure audit. Existing older SSP audit records an absent or unverified exact matching Android/Bionic linker+VNDK+APEX dependency closure and an incomplete native BBD download ACK state machine. The stock config references a GNSS-related power path; avoid speculative sensor/GPS shared resets. User's preference for zero Android dependencies means the native firmware handshake is the preferred long-term solution; isolated vendor tools can inform research but not become a permanent hidden Android stack.

**Next acceptance:** firmware hub ready, accel/gyro vary with physical rotation and settle, axes remap correctly, compositor and touch respond, lock mode respected; verify cold boot/resume. Never synthesize readings to mark sensor recovered.

## NFC — BLOCKED_KERNEL / REFERENCE CLOCK

**Recorded live:** Samsung S3NRN82 I2C at `7-0027`, `/dev/sec-nfc`, firmware `nfc/sec_s3nrn82_firmware.bin` 151,852 B, SHA-256 `d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb`, `nuxel-nfcd` daemon fail-closed off. Proprietary bootloader GET_BOOTINFO framing was previously seen. `oscclk_nfc` reportedly 0 Hz and NCI `CORE_RESET` did not return a usable reply. Existing patches 0018/0019/0021/0023 address driver/clock plumbing but current execution not proved.

**Next acceptance:** correct stable reference clock, NCI INIT/RESET response, adapter discovery, actual NFC tag reading at controlled distance, public application permission boundaries and suspend/resume. Do not infer functioning NFC from firmware+I2C enumeration. Payments/emulation are separate work.

## Fingerprint — BLOCKED_SECURE_PROVIDER

**Recorded live:** Qualcomm QBT2000 ultrasonic sensor exposes `/dev/qbt2000_fd` and `/dev/qbt2000_ipc`, sysfs and type-check path. Firmware/driver presence doesn't supply an authenticated, secure biometric pipeline. Nuxel provider intentionally reports `BLOCKED_SECURE_PROVIDER`, no enrollment or matching. Correct PIN fallback.

**Next acceptance:** legitimate TEE-backed trusted application and secure template handling compatible with this device; real enrollment, match, delete, locked screen, failed attempts and permissions. Do not implement insecure userspace template extraction or fake `fprintd` success.

## Hotspot, Wi-Fi/USB and Bluetooth tethering — PARTIAL, with live success history

**Recorded live in `docs/v0.8.5-beta/REPORT.md`:** Wi-Fi hotspot `wlan1` AP using hostapd+dnsmasq, `wlan0` uplink, nftables NAT and `ip_forward=1`; corrected early nftables app-firewall DROP policy that shadowed the tether forwarding chain; fixed rp_filter and persisted forwarding. USB tethering provider tests and earlier live checks. These are meaningful successes, **not a fresh assurance after later release changes**. Revalidate from a separate client with DNS, HTTPS, multiple concurrent devices, firewall deny leakage, stop/restart and suspend. Tethered uplink through cellular requires mobile networking first, unless using Wi-Fi uplink.

**Bluetooth contrast:** BlueZ code/config exists but earlier reports say `bluetoothctl list` showed no usable adapter / HCI interface. No working pairing is proved and no complete PAN/NAP tethering setup is evidenced. Firmware candidates for BCM4375 include exact model B0/B1 module variants in the beyond2lte vendor manifest; must select by observed chip ID, not random HCD. Restore `hci0`, pair securely, then BlueZ PAN/NAP, DHCP/subnet/routing/firewall and actual client networking. BT audio and BT tethering are separate verifications.

## Microphone and camera in PWA, Flatpak and native GTK — AUDIO PARTIAL PASS / VIDEO BLOCKED

**Audio live evidence:** real ALSA hardware WDMA1 capture (`hw:0,13`) and PipeWire source, 48 kHz stereo configuration under `configs/s10plus/pipewire/51-nuxel-s10-mic.conf`; privacy mute passed. `docs/v0.8.5-beta/REPORT.md` records a **393 KB captured real microphone sample inside Flatpak**, correcting a broken PulseAudio socket mount and empty-socket override. That is strong evidence for the tested Flatpak session, not a universal PWA/GTK/third-party matrix.

**Cross-app matrix to complete:** native GTK capture and permissions, Nuxel WebKitGTK PWA `getUserMedia({audio:true})` with prompts/revocation, Flatpak Stremio/Signal and test apps with portal/socket mappings, devices switching, sample rate/channel mismatch, suspend/resume, echo cancellation/noise processing where applicable. Audit Pulse relay permission and Unix socket ownership; don't assume a world-accessible bridge is secure just because mic captures.

**Camera in all apps:** blocked by absence of real physical frames and a reliable publisher/portal. The Camera Gallery PWA's UI, native GTK Camera app and desktop portal are not substitutes for an actual source. Keep per-app consent and revocation consistent and test front/rear exposure separately.

## GPU, desktop rendering and HD video / Stremio — PARTIAL GPU, HW DECODE UNVERIFIED

**Recorded live:** Mali-G76 MC12 Panfrost GLES 3.2 through `/dev/mali0`, compositor GPU contexts and graphics fixes in `docs/releases/v0.7.5-beta.md`; WebKit `KBASE_IOCTL_JOB_SUBMIT` measured, **GPU-rendered but SHM-presented**. Zero-copy DMA-BUF/DRM/GBM path not fully available. `services/nuxel-s10/bin/nuxel-flatpak-firefox` explicitly forces `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`, `MESA_LOADER_DRIVER_OVERRIDE=llvmpipe`; therefore **all apps cannot truthfully be called full-GPU accelerated**. Audit exact process environment and renderer per PWA, Flatpak Stremio/Firefox, and GTK.

**Video decoder distinct from GPU renderer:** Exynos MFC (`/dev/video6` decoder, `/dev/video7` encoder) detected, driver requests `mfc_fw.bin`. At the time of `evidence/pwnage-60000/mfc/README.md`, the file was absent on the live phone and firmware request fallback could hang; the repo uses a fail-closed GStreamer guard. Later repo evidence records a 685,832-byte host reference (`SHA256 f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f`), but this audit does not find a deployed copy or physical hardware-decode success. Do not confuse charger `mfc_fw_flash*.ihex` with Exynos video `mfc_fw.bin`.

**Next acceptance:** provenance-validated model/kernel-matched `mfc_fw.bin`, safe no-hang open/close, repeatable V4L2 M2M decode with correct output verified, GStreamer hardware decoder registered only when safe, PipeWire/UI integration, and actual 720p/1080p H.264+HEVC playback in Stremio with smooth A/V sync, seeking, resume and no software-decoder fallback. Confirm per-process CPU, MFC codec activity, dropped frames, GPU contexts, output path and video sync; 'Stremio launches' is not decode success.

## Recommended prioritized order

1. **P0 camera**: prove loader failure root cause, patch status, coherent firmware, one rear-main physical frame; then other sensors and portal/app matrix.
2. **P0 GPU/MFC quick dependency inventory in parallel**: known firmware and explicit Firefox llvmpipe can be triaged without touching camera state.
3. **P1 SSP**: BBD runtime → moving samples → automatic rotate.
4. **P1 mobile**: local CP known → documented `cbd`/kernel compatibility → data then telephony.
5. **P1 NFC**: reference clock/NCI and tag reads; fingerprint secure TEE provider is a longer discrete security project.
6. **P1 Bluetooth**: restore HCI before PAN/NAP and tethering.
7. **P1 cross-app regression**: microphone, camera, PWA/Flatpak/GTK, Stremio; hotspot/USB regression and suspend/reboot durability.

### Stop conditions and integrity rules

Any operation needing actual sensor power/reset, CP boot, EEPROM writes, kernel flash, unverified blob replacement or credential exposure must be separated from offline research and explicitly approved with a rollback path. Preserve the working Wi-Fi and USB link. Don't claim 100% until actual physical evidence is collected. Do not store IMEI, EFS content, personally identifying serials, application recordings or hotspot credentials in public reports.
