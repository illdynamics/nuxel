# PWNAGE CAM — Samsung Galaxy S10+ Camera Bring-up for Nuxel

**Read and obey `full-pwnage-cam.md` completely.** It contains the detailed hardware investigation, firmware requirements, TWRP/flash loop, SSH handoff, permission-manager work, PipeWire/XDG portal requirements, app validation, security policy and acceptance tests.

## Starting state and owner authorization

I will start you with the Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) already booted into **TWRP and connected over USB/ADB**.

You are authorized to:

- inspect the exact repo and device;
- acquire ordinary matching camera firmware/HAL/config files from the owner's own already-mounted stock vendor/system filesystem using the read-only acquisition script in this pack;
- build the pinned kernel and DTBs;
- build a verified boot candidate;
- flash the verified boot image using the repository's guarded TWRP script;
- reboot and diagnose failed boot attempts;
- once Nuxel boots, connect over Wi-Fi SSH with my key and continue implementing/testing/deploying camera userspace.

Do not use generic fastboot on this S10+. Inspect `boot/s10plus/flash.sh`, `build-candidate.sh`, `kernel/s10plus/build-kernel.sh`, the completed device inventory and actual partition topology before writing anything. The current plan mentions A/B, but the real S10+ partition layout must be measured; do not invent slots. Never flash userdata/rootfs, EFS, persist, modem, recovery, bootloader or PIT without an independently verified target and explicit data-impact approval.

## Critical reboot interpretation

**If you flash/reboot and the phone returns to TWRP, that means the Nuxel boot attempt failed. I did not manually return it to TWRP.** Treat it as a bootloop/hang/crash. Collect TWRP/pstore/last-kmsg/kernel/initramfs/filesystem logs, identify the root cause, fix the source, rebuild, pass the gates, reflash the corrected boot candidate and reboot again. Never repeat the same failing image blindly.

**When the phone reaches the Nuxel environment and its boot health check confirms userspace, that is a successful boot.** Then connect to the owner-provided Wi-Fi address using:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167
```

Resolve the key path correctly on the workstation. Never print/copy the private key or disable SSH host-key checking. Verify the target identity after connecting. If Wi-Fi SSH is unavailable, use the preserved USB console; do not reflash just because Wi-Fi did not come up.

## Current camera state — do not start from zero

The uploaded repo already has:

- five observed FIMC-IS sensor modules: rear S5K2L4, tele S5K3M3, UW S5K3P9, front S5K3J1, IR/depth S5K4H7;
- dozens of Samsung Exynos FIMC-IS `/dev/video*` nodes;
- OIS/EEPROM/MIPI/FIMC-IS kernel support and secure-camera handshake evidence;
- camera diagnostic, Camera and Photos apps, native GTK Camera shell, bridge/API media store, private `org.nuxel.Camera` broker and camera Permission Manager capability.

The previous measured verdict was `BLOCKED_FIRMWARE`: no genuine sensor/ISP setfiles/firmware on the Nuxel rootfs, no `/dev/media*` or `/dev/v4l-subdev*`, standard `VIDIOC_S_FMT` on the inspected Samsung nodes returned `ENOTTY`, `REQBUFS`/`QUERYBUF` returned `EINVAL`, and no real S10+ frame has ever been verified. The test fixture's `s5k2l4_setfile.bin` is only 3 bytes: it is fake placeholder data and must never be installed.

The current private camera broker is NOT `org.freedesktop.portal.Camera`. The current Camera app UI is substantially implemented but does not have a real hardware source. The current native Camera app is an honest status shell and needs a genuine live viewfinder/capture path.

## Your immediate tasks

1. Inspect `git status`, `REFLASH-PLAN.md`, the complete camera report/docs, current deployed state and concurrent NFC agent changes. Preserve them; do not reset/stash/clean/revert.
2. Reverify the exact handset, five sensor IDs, FIMC-IS nodes, media graph, camera firmware paths, kernel logs, TEE secure-camera path and actual source commit.
3. Read the exact pinned Linux4 Exynos9820 4.14.253 kernel source. Trace FIMC-IS sensor drivers, firmware request names, private ioctls/structs, mode tables, media-controller setup, CSI/ISP/DMA path and sensor power sequencing. Investigate the S5K3P9 `gpio_subcam_sel`/`gpio_mipi_sel` errors using matching DTS evidence only.
4. Run `scripts/acquire-s10plus-camera-assets.py` in inventory-only mode. Then use `--pull` to acquire exact ordinary files from the owner's own matching, already-mounted vendor/system/odm paths. Use `--include-vendor-calibration` only for owner-authorized regular vendor calibration files. Do not mount/write partitions, read EFS/persist/RPMB/raw EEPROM/TEE memory or access user data.
5. Obtain only genuine, compatible Samsung camera sensor setfiles, Exynos9820 FIMC-IS MCU/ISP/RTA libraries, OIS firmware and calibration/tuning files from the exact SM-G975F firmware family. Verify paths, SHA256, sizes, versions, ELF ABI, dependencies and driver consumers. Do not use Qualcomm/Pixel/other-device blobs or fake fixtures. Do not edit or re-sign proprietary firmware.
6. Prove the pipeline architecture from source. A generic libcamera install will not fix missing media graph/private Samsung ioctls. Choose a working native libcamera/private-ABI handler, safe kernel media-controller adaptation, or a narrowly scoped exact-device vendor provider. Do not create a fake media graph or blindly stream from `/dev/video0`.
7. Start with rear-main S5K2L4 real preview + still, then front-main S5K3J1, then tele/UW if supported. Handle S5K4H7 as IR/depth, not an ordinary RGB webcam.
8. Fix the camera diagnostic's false readiness path: one present blob is not enough, the 3-byte fixture must be rejected, and capture must not pick the first arbitrary video node. Require verified firmware load, exact supported pipeline and decoded real frames.
9. Finish the native GTK Camera app so it shows the real physical live preview and captures real still/video into the existing file-backed media store. Keep Camera PWA and Photos working through the same provider; no duplicate capture owners.
10. Properly finish the Permission Manager and privacy enforcement. The canonical `camera` capability and label already exist; verify aliases (`camera:preview`, `camera:capture`, existing `camera:read`), default-deny, central permD storage, real portal/PipeWire enforcement and app identity. Separate live camera permission from saved-media read/delete permission. Fix fail-open privacy-provider exceptions. No world-writable `/dev/video*` devices.
11. Implement the actual standard XDG `org.freedesktop.portal.Camera` + PipeWire/WirePlumber path (AccessCamera request/response, OpenPipeWireRemote FD, per-app node access). Keep private `org.nuxel.Camera` separate; never claim it is the freedesktop portal.
12. Discover actual ZapZap and Ferdium app IDs/package type/runtime on the phone. Test each with physical `getUserMedia`/video preview, explicit permission, denial and revoke. Do not assume those packages or Flatpak are installed. Never disable sandboxing to make tests pass.
13. Preserve visible camera-use indicator and stop control for every app, and stop streams on revoke, lock, app exit or privacy block. Mic remains a separate permission.

## One coherent reflash

The owner wants one combined reflash batch with NFC and any other ready kernel/vendor-gated work. Do not perform a camera-only flash that omits the in-progress NFC patch if it is ready to integrate. Build from one exact pinned source tree and coherent patch/config set. Add a camera patch only if source/evidence proves it is needed. The authorized boot flash is through the guarded repo TWRP script, after backup/checksum/partition/inventory/build gates. Do not write the userdata rootfs default just because `flash.sh --rootfs` accepts it.

After the combined boot image boots, finish and hash-verify safe userspace deployment over the specified Wi-Fi SSH session. The repo live deploy helper is currently framed serial-console deployment; do not call that SSH. Use an atomic/hash-verified SSH staging workflow for Wi-Fi deployment and keep exact rollback copies.

## Required final acceptance

- Rear-main and front-main actual S10+ camera preview + still verified; video verified; other lenses separately classified.
- 100+ frames per accepted stream with no driver/ISP/DMA crash.
- Native Camera app foregrounded on the phone and real preview visible to the owner.
- Photos opens saved capture.
- Standard XDG Camera portal and PipeWire provide the camera to compatible clients.
- ZapZap and Ferdium tested with actual camera where their installed builds support it; exact app IDs and unsupported cases documented.
- Permission Manager camera grant/deny/revoke really gates acquisition; privacy errors fail closed; indicator reflects all active clients.
- Camera diagnostic correctly distinguishes enumeration, firmware load, pipeline readiness and physical frame capture.
- Boot/reflash log includes every candidate hash and every return-to-TWRP failure/repair. Live deploy log includes target identity and installed file hashes.
- Final reports and a combined `PWNAGE-CAM-REFLASH-MANIFEST.md` are saved.

Use `PASS_PHYSICAL`, `PASS_BUILD`, `PASS_RUNTIME`, `BLOCKED_FIRMWARE`, `BLOCKED_VENDOR_ABI`, `BLOCKED_PIPELINE`, `BLOCKED_PORTAL`, `BLOCKED_PERMISSION`, `BLOCKED_COMPATIBILITY`, `FAIL`, `NOT_TESTED` or `UNSUPPORTED` accurately. Do not claim the camera is fixed until real built-in S10+ frames are visible in Nuxel Camera and the app stack has been tested.

**Continue implementing and physically verifying the real camera until it works. If the exact OEM firmware or private ABI is genuinely unavailable, document the precise missing Samsung input—do not fabricate a blob, bypass checks or substitute synthetic frames.**
