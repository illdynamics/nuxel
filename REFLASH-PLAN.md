# Nuxel S10+ controlled reflash plan

This document consolidates the "reflash impact" sections added to every
`REPORT-*.md`. Its purpose is to avoid repeated emergency flashes: group every
change that genuinely needs a partition write into one planned A/B update, and
keep userspace-only work on the existing SSH deployment path.

## 1. Decision rule

A change needs a reflash **only** when it must modify one of:

- the boot/kernel image or device-tree;
- vendor firmware/calibration or a secure-world/TEE payload;
- a system-image file that is protected by dm-verity / A/B verification and
  cannot be safely replaced at runtime.

Everything else (PWA, bridge, notification hub, shell scripts, icon assets,
edge-panel UI, service-worker cache) ships over the existing SSH/deploy path.

## 2. Consolidated matrix

| Report | Reflash? | Primary partition/payload | Can ship with PWNAGE-93000 userspace? | Notes |
|---|---|---|---|---|
| [REPORT-CAMERA.md](REPORT-CAMERA.md) §17 | **YES** | system image + vendor setfiles/ISP/calibration; boot only if FIMC-IS ABI/DT changes | YES | No frame can be claimed from a driver-bound node alone. |
| [REPORT-FINGERPRINT.md](REPORT-FINGERPRINT.md) §17 | **YES** | vendor/TEE trusted application + system provider; possibly boot | YES | Userspace-only matcher is rejected for security. |
| [REPORT-GPS.md](REPORT-GPS.md) §17 | **YES** | system image with BBD loader/patch + vendor runtime; boot only if loader path/DT changes | YES | A transport node is not a fix. |
| [REPORT-LEDS.md](REPORT-LEDS.md) §17 | **NO** | none; torch sysfs + userspace policy + PWA edge lighting | YES | Edge lighting is a display overlay, not an LED. |
| [REPORT-MOBILE-NETWORKING.md](REPORT-MOBILE-NETWORKING.md) §17 | **PARTIAL / YES** | Shannon ModemManager plugin + system image; likely boot/kernel for CP transport/DT | YES | Batch with NFC/USBNET kernel work. |
| [REPORT-NFC.md](REPORT-NFC.md) §17 | **YES** | boot/kernel NFC class/netlink + system daemon; firmware already present | YES | Verify a physical tag read before claiming completion. |
| [REPORT-ROTATION.md](REPORT-ROTATION.md) §17 | **PARTIAL / YES** | system image with SSP/BBD vendor runtime; boot only if SSP driver/DT changes | YES | Manual/locked rotation must stay intact. |
| [REPORT-USBNET.md](REPORT-USBNET.md) §17 | **PARTIAL / YES** | boot/kernel gadget modes + system helper | YES | Preserve CDC-ACM recovery console in every mode experiment. |
| [REPORT-EDGE.md](REPORT-EDGE.md) §17 | **NO** for v1 | PWA + bridge + optional existing `set_grip_data` controller tuning | YES | Only a future kernel/DT/native-surface change would force a flash. |
| PWNAGE-93000 (this mission) | **NO** | PWA/bridge/notification/session userspace | — | Already deployed over SSH; include in the image if rebuilding anyway. |

## 3. Recommended one-flash batch

Because camera, fingerprint, GPS, mobile networking, NFC, rotation and USBNET
touch overlapping kernel/vendor payloads, do **one controlled A/B batch**:

1. **Prepare the inactive slot**
   - build the S10+ ARM64 system image with all agreed userspace changes
     (including PWNAGE-93000 and the edge v1 PWA/bridge work);
   - include camera/GPS/SSP/ModemManager/NFC/USB userspace payloads that are
     ready;
   - include boot/kernel/DT only for the kernel-gated items (NFC, USBNET,
     mobile transport, camera ABI if required).
2. **Verify before switching**
   - camera: enumeration + a real frame (or leave the feature flagged BLOCKED);
   - fingerprint: secure enrollment/auth + PIN fallback;
   - GPS: receiver-reported fix, not network location;
   - NFC: physical tag read;
   - rotation: nonzero accelerometer samples;
   - USBNET: one gadget mode at a time with serial recovery preserved;
   - Home: launcher, Quick Settings, notifications, sound modes, Back-to-Home,
     drawer gesture, lockscreen.
3. **Switch the A/B slot** only after the inactive slot passes the matrix.
4. **Keep the previous slot** as the rollback target; do not wipe it during the
   first boot after the switch.

## 4. Userspace-only fast path (no flash)

The following can be deployed now and do not wait for the reflash batch:

- PWNAGE-93000 launcher icons, speaker sound modes, notification hub/UI,
  swipe semantics and Back-to-Home/input cleanup;
- LED/torch policy and edge-lighting presentation;
- Nuxel-edge v1 gesture/panel/layout;
- any bridge/PWA/shell-script change whose binaries and assets are not
  dm-verity-protected in a way that blocks runtime replacement.

Deploy with the mission scripts, back up each replaced file as
`*.nuxel-rollback-p93-<UTC>`, and keep the rollback script with the evidence.

## 5. Rollback

- Userspace: `tools/pwnage93000/rollback-pwnage93000.sh` and the documented
  per-mission rollback scripts.
- Reflash: boot the previous A/B slot; keep the serial/ACM recovery console and
  the charger-mode recovery path available.
- Never mix a kernel/boot experiment with an untested system image in the same
  slot switch unless both are listed in the batch matrix.

## 6. Status in this run

- PWNAGE-93000 userspace: **deployed over SSH and verified**; no reflash needed.
- Edge v1: **report complete; implementation not started**; no reflash needed
  for the recommended userspace design.
- Firmware/secure/kernel-gated reports: **still blocked**; they are the reason
  to schedule the next controlled reflash batch.
