# S10+ daily-driver checkpoint

Last updated: 2026-10-20 (live S10+ A41 dock repair deployment).

This is the resumable status record for the userspace-only daily-driver work.
It does not upgrade a software result into hardware verification.

| Work item | Status | Evidence / next action |
|---|---|---|
| Repository and deployment audit | SOFTWARE VERIFIED | Branch `feature/haptic-and-triple-button`; pre-existing dirty A39/A40 work preserved. Active launcher origin is `http://127.0.0.1:8000/pwa/nuxel-home/index.html`. |
| USB console | SOFTWARE VERIFIED | The expected Nuxel CDC gadget is `/dev/ttyACM0` (`18d1:4ee7`, serial `NUXEL-S10PLUS-0001`). A host-side CDC reset recovered a wedged shell without rebooting the phone; framed root commands pass afterwards. |
| Custom dock artwork | SOFTWARE VERIFIED — owner test pending | A41 changed both shortcut and Back/Home/Recents paint-only layers from height-constrained `contain` to full-width aspect-preserving art (`100% auto`, 33.34vw paint layer). One persisted picker now changes BG1/BG2 on both surfaces and offers `None`; artwork remains pointer-inert. The deployed JS/CSS hashes match the `:8000` responses. Physical render/touch confirmation remains required. |
| PWA cache deployment | SOFTWARE VERIFIED — owner test pending | Cache version is `v21-a41-full-width-dock`; the A41 installer restarted only `nuxel-wayland`, the host opened a new cache-busted launcher URI, and verified every served PWA payload byte after restart. Physical cache/render confirmation remains required. |
| CPU/RAM/GPU/GPU MEM monitor | SOFTWARE VERIFIED — owner test pending | AArch64 `nuxel-metricsd` is live at `127.0.0.1:8624/metrics`: CPU uses `/proc/stat` deltas, RAM uses `MemAvailable`, GPU uses a documented Mali node, and shared GPU memory is unavailable rather than invented. A live two-sample check reported CPU 12.7%/1232 MHz then 13.3%/1180 MHz, RAM 10.3% (783 MiB/7.25 GiB), GPU 0%/0 MHz, GPU MEM `N/A`. Physical screen confirmation remains required. |
| Cellular/status truthfulness | SOFTWARE VERIFIED — owner test pending | Status starts unknown/hidden, never turns generic network state into SIM bars, and requires an explicit registered modem. The live bridge reports no ModemManager connection rather than fabricated signal. |
| Wi-Fi adapter and scan | HARDWARE VERIFIED | `NetworkManager-wifi`, `wpa_supplicant`, `iw`, `wireless-regdb`, and libnl dependencies installed from signature-verified Fedora RPMs. Exact BCM4375 CLM/station/NVRAM blobs were installed and hash-verified from the pinned manifest. `wlan0` and `wlan1` are managed Wi-Fi devices; a credential-free live scan returned 25 AP records. |
| Quick Settings Wi-Fi control | HARDWARE VERIFIED — owner UI test pending | The tile now requests `network:manage`, sets NetworkManager `WirelessEnabled`, and reads it back. Live API proof transitioned Wi-Fi to `disabled` (both devices state 20) and back to `enabled_disconnected` (both state 30). The bridge uses a narrowly scoped PolicyKit rule for only `enable-disable-wifi`; its static JS, service worker, and manifest are HTTP 200 with matching deployed hashes. |
| Wi-Fi association, DNS, HTTPS and Browser | BLOCKED — owner network credentials | The radio is enabled and scans. No password, connection profile, IP configuration, DNS, gateway or external HTTPS test has been authorized/provided. |
| Wi-Fi startup compatibility | SOFTWARE VERIFIED — reboot test pending | `nuxel-network-udev-seed.service` is enabled before NetworkManager. It creates only missing runtime udev records for genuine `wlan*` PHYs, because systemd-udevd remains deliberately masked on this 4.14 kernel. No reboot was performed. |
| Files, audio, Bluetooth, NFC, GNSS/Maps, camera, hardware shortcuts | NOT STARTED | Continue independently after the current Wi-Fi/UI checkpoints; do not claim physical behavior without a device test. |

## Prepared Milestone A payload

`tools/s10plus/a40/package-live.sh` produces a userspace-only ARM64 payload.
The on-device installer is `tools/s10plus/a40/install-live.py`; it backs up each
target under `/var/lib/nuxel/a40-monitor/<UTC timestamp>/`, installs atomically,
restarts only `nuxel-wayland`, enables the socket-activated metrics service, and
rolls back its files if a hash, service, served-resource, or metrics-endpoint
check fails. It never writes boot, kernel, partitions, firmware, or modem data.

Before another deployment, run the guarded reachability probe. After deployment,
capture the receipt, hashes, active services, HTTP responses, and a real
framebuffer/owner visual test before marking a visual item HARDWARE VERIFIED.

The live delta intentionally excludes artwork already verified byte-for-byte on
the phone: the protected CDC console uses tiny, checksum-framed binary chunks.
The dock/nav/Quick Settings images are audited via HTTP and SHA-256 before the
code delta; a complete icon-pack refresh remains a separate resumable transfer.

## A41 dock deployment and rollback

The deployed transaction receipt is
`/var/lib/nuxel/a40-monitor/20261020T092143Z/receipt.json`; its status is
`DEPLOYED_UNVERIFIED` by design until the owner checks the physical display. It
contains the prior copy of every affected file under its `backup/` directory.
The installer restores those files atomically and restarts only `nuxel-wayland`
if a payload hash, service, served-resource, or metrics check fails. The active
`nuxel-wl-fb` bridge reported `FRAMES_OK`, display on, and successful DECON pans
after this launcher restart; that confirms presentation activity, not glass
appearance.

## Live Wi-Fi receipts and rollback

The package transaction receipt is `/var/lib/nuxel/a41-wifi/20261020T081951Z`.
Firmware receipts are the `*-clm`, `*-sta`, and `*-nvram` directories under the
same root; the persistent udev compatibility service receipt is
`20261020T083641Z-udev-seed`, and the bridge rebind receipt is
`20261020T083750Z-bridge-rebind`.  The Quick Settings and least-privilege
permission-policy receipts are `20261020T083948Z-qs-wifi`,
`20261020T084059Z-bridge-permissions`, and
`20261020T084145Z-network-polkit`. Each contains the pre-state and a rollback
instruction. The active bridge result at `/api/v1/phone/status` is truthful:
`wifi_state=enabled_disconnected`, two Wi-Fi devices, and no Internet claim.
