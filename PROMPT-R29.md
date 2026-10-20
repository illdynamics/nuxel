# NUXEL R29 — Native virtual keyboard
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r29-native-virtual-keyboard`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the native on-screen keyboard reliably usable: correct text-input protocol, focus, caret, show/hide, layout, key injection, backspace/shift/enter/space, viewport avoidance, and key haptics. This branch must distinguish the system OSK from in-page fallback key pads and must not steal focus from the WebKit text field.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/keyboard/keyboard.json`, `configs/nuxel/keyboard/keyboard.schema.json`, `configs/nuxel/keyboard/nuxel-keyboard-apply.service`, `configs/nuxel/keyboard/nuxel-keyboard-apply.path`, `tools/s10plus/a33/nuxel-keyboard-apply.sh`, `tools/s10plus/a33/keyboard-probe.html`, `pwa/nuxel-home/js/touch-keyboard.js`, `pwa/nuxel-home/js/app.js`, and `pwa/nuxel-apps/settings/settings-model.js`. The stack probes stevia/stevia-phosh-osk-provider and supports squeekboard as an alternate; an in-page pad is only a labeled fallback.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns OSK provider selection, text-input protocol/focus, keyboard layout/height settings, key haptics wiring, and viewport avoidance. Does not own app text models or the compositor's text-input implementation. No fake OSK status when neither provider is installed.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Probe the installed OSK provider and text-input protocol; report NO_OSK_INSTALLED rather than assuming stevia/squeekboard exists.
2. Verify focus/caret/selection in a real WebKit text field through `zwp_text_input_manager_v3`.
3. Implement show, hide, reopen, layout switch, Shift, symbols, Backspace/repeat, Enter, Space, and clipboard behavior.
4. Ensure the keyboard stays above the dock/app content without covering the focused field or intercepting the whole viewport.
5. Wire key haptics through the single haptics API and honor the global off switch.
6. Test app switching, iframe focus, background/foreground, and keyboard dismissal without losing typed text.
7. Define an owner test that types a sentence in Calendar and Settings, hides/reopens, and confirms cursor/keys.

## Failure modes and diagnostics
- Watch for two OSK providers, a compositor focus mismatch, WebKit not enabling text input, keyboard height resizing the viewport twice, and a fallback key pad intercepting touches after dismissal.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The active OSK provider and text-input protocol are identified, or NO_OSK_INSTALLED is reported.
2. A real WebKit field shows a caret and receives every required key, including Shift/symbols/Backspace/Enter/Space.
3. Hide/reopen preserves focus and the in-progress text.
4. The keyboard does not cover the focused field and does not block unrelated touch targets.
5. Key haptics work through the single haptics owner and stop when the global switch is off.
6. No in-page fallback is labeled as the system keyboard.
7. Owner-visible typing and feel are recorded separately from protocol tests.

## Hardware, privilege and rollback safety
Do not replace the compositor or claim haptics/speaker success from keyboard tests. No kernel/flash changes. Preserve existing app data and focus behavior.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r29-native-virtual-keyboard`, with tests and docs for this component only.
- `docs/component-reports/r29.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if no supported OSK provider is installed or if the compositor text-input protocol is absent. Report the exact missing package/protocol rather than building a competing full keyboard.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
