# NUXEL R15 — USB-C audio and jack adapters
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r15-usb-c-audio-jack`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make wired audio work independently of the unresolved built-in speaker path. This branch must detect the 3.5 mm jack and USB-C accessories from real evidence, choose the correct ALSA/PipeWire sink, handle insert/remove and hotplug safely, and return to the speaker route without restoring an unsafe volume or leaving audio routed to an absent device.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/audio/jack-routes.json`, `configs/nuxel/audio/audio.json`, `tools/s10plus/a33/nuxel-headphone-diag.sh`, `tools/s10plus/a33/tests/test-headphone-route.py`, the jack fixtures under `tools/s10plus/a33/tests/fixtures-p3/jack-*`, `configs/google-pixel-10-pro-xl/alsa-ucm/GoogleMustang/USB-C-Analog.conf` as a separate device example, and `configs/wireplumber/README.md`. The capability manifest marks jack/USB-C detection OFFLINE_TESTED but audibility and real adapters NEEDS_OWNER_TEST.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns jack/UAC detection, route selection, hotplug policy, low-volume cap reapplication, and the wired-audio diagnostic/UI state. Does not own the built-in CS35L40 speaker route or Bluetooth audio. Do not copy Pixel-specific UCM into the S10+ profile.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate ALSA jack kcontrols and codec pin states for the real `beyond-madera` card; record names, values, and source files before selecting any route.
2. Detect a UAC device through a new ALSA card/USB bus evidence and distinguish digital USB-C audio from analog USB-C accessory mode.
3. Implement route rules for headphones, headset, USB-C DAC, unplug/revert, and absent-device refusal without hard-coded card indices.
4. Reapply the 25% safety cap before the first sample after every route change.
5. Test insert, remove, reinsert, adapter absent, unsupported analog accessory, and a UAC DAC without routing to a missing sink.
6. Verify PipeWire/WirePlumber selects the intended sink and the settings/status UI reflects the real route.
7. Keep the built-in speaker result labeled separately and do not require speaker success for wired audio acceptance.

## Failure modes and diagnostics
- Watch for jack kcontrols that exist but never change, an analog USB-C accessory presenting no UAC card, PipeWire keeping a stale default sink, and a route change restoring a previously stored high volume. Never infer support from the phone having a USB-C port.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Jack/USB-C detection names the real evidence source and does not guess a card index.
2. A supported wired accessory becomes the active sink; unplug returns to the speaker route or an explicit safe state.
3. Route switching always reapplies the low-volume cap before rendering audio.
4. An unsupported accessory yields a clear NOT_SUPPORTED/REFUSED result, not silence with a false connected state.
5. UI state follows the actual route and hotplug event.
6. Owner either confirms audible wired audio or the report gives the exact missing driver/UCM/accessory reason.
7. The built-in speaker path and its safety cap are not modified or claimed as verified by this branch.

## Hardware, privilege and rollback safety
No speaker-full-scale test, no flash, no kernel changes. Wired tests require the owner to plug/unplug hardware; absent hardware remains NOT TESTED. Preserve rollback and the current speaker configuration.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r15-usb-c-audio-jack`, with tests and docs for this component only.
- `docs/component-reports/r15.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the codec route cannot be changed without undocumented register writes or if the accessory type cannot be distinguished safely. Do not modify the built-in speaker route to make wired audio appear to work.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
