# NUXEL R22 — Notification LEDs, edge lighting and flashlight
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r22-notification-leds-edge-lighting-torch`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement truthful notification LED, edge-lighting, and torch behaviour. This branch must discover actual LED/torch interfaces, keep torch and camera resource ownership safe, enforce a bounded ON time and always-available OFF path, and label the S10+'s curved-display edge lighting as a software effect rather than a hardware LED.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/leds/leds.json`, `tools/s10plus/a33/nuxel-led-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py`, the `leds-*` fixtures, `configs/nuxel/camera/camera.json`, `services/nuxel-notifications/src/notifications.py`, `pwa/nuxel-home/js/qs.js`, and `pwa/nuxel-home/js/status-bar.js`. The manifest marks visible light and torch as NEEDS_OWNER_TEST and says edge lighting is not a hardware LED.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns LED/torch discovery, status/notification mapping, torch timeout/off path, and EDGE_LIGHTING state reporting. Does not own camera capture or the notification daemon's message store. No automatic strobe, no torch-on-boot, and no camera/ISP changes.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate `/sys/class/leds/*`, V4L2 flash controls, and any notification LED paths; record which are truly writable.
2. Implement torch ON/OFF with explicit owner action, a maximum ON duration, automatic OFF on exit/error, and a hardware-off verification.
3. Implement notification LED mapping only when a real LED exists; otherwise report NOT_SUPPORTED_ON_DEVICE and use an honest display fallback.
4. Model edge lighting as a display overlay tied to the display bridge, with `hardware_led=false` and a clear NOT_VERIFIED state when the bridge is unavailable.
5. Audit camera/torch resource contention and ensure torch cannot run while a camera stream owns the flash.
6. Add tests for absent class, permission denied, write failure, timeout, and forced service exit.
7. Define a physical owner check for visible torch/LED and safe OFF.

## Failure modes and diagnostics
- Watch for a flash node that accepts `brightness` but never emits light, `flash_strobe` semantics differing from torch, two apps toggling the torch, and a display overlay being mistaken for a hardware LED.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names each real LED/torch path or explicitly reports it absent.
2. Torch ON/OFF is explicit, bounded, and returns to OFF after timeout, error, or service exit.
3. No torch or LED turns on during boot or automatically from a notification.
4. Notification LED is claimed only when the class exists and a write is observed; otherwise the UI says unsupported.
5. Edge lighting is reported as a display effect, not a hardware LED.
6. Camera/torch ownership conflict is detected and refused safely.
7. A visible-light owner result is recorded separately from sysfs tests.

## Hardware, privilege and rollback safety
Torch is a high-power emitter: enforce short tests, explicit `--yes`, and always-off cleanup. No strobing, no camera-module register writes, no boot-time activation.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r22-notification-leds-edge-lighting-torch`, with tests and docs for this component only.
- `docs/component-reports/r22.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the LED class is absent or the only write path is unsafe/unknown. Report NOT_SUPPORTED or BLOCKED; never emulate the hardware and call it verified.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
