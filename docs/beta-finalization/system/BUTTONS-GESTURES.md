# Hardware buttons and screen gestures on the S10+ (areas 16, 17, 20)

Scope: Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Fedora 43
ARM64 userspace, Linux 4.14.253. Everything below is either verifiable from this
repository or explicitly marked as not yet observed on hardware.

**Terminal states for this area**

| Item | State |
|---|---|
| A32 button behaviour (power/volume/Bixby single press) | `VERIFIED_ON_S10PLUS` — A32 record, preserved byte-identically |
| A33 state machine, menu, gesture recogniser (sources + spec) | `OFFLINE_TESTED` |
| A33 daemon built for aarch64 (Fedora 43 guest) | `VERIFIED_IN_VM_ONLY` |
| A33 daemon installed on the handset | `IMPLEMENTED_NOT_DEPLOYED` |
| Recovery / Download-Mode entries | `OFFLINE_TESTED` (refusal is the tested behaviour) |
| Gesture actions on the glass | `NEEDS_OWNER_TEST` |
| Chords, panels, early hold, mapping (spec + C + traces) | `OFFLINE_TESTED` |
| Daemon syntax gate (stub alsa header; negative control) | `OFFLINE_TESTED` |
| Sound-mode cycle effect on the mixer | `OFFLINE_TESTED` (the mode; audibility is area 6 → `NEEDS_OWNER_TEST`) |

No claim in this document is `VERIFIED_ON_S10PLUS` for the A33 behaviour: the
A33 manager has not run on the handset in this cycle.

---

## 1. Why this exists

The S10+ keypad is **one** evdev device, `gpio_keys` (measured in A32:
`/proc/bus/input/devices` → `Handlers=sec_key_notifier`, KEY bitmap with
VOLUMEDOWN=114, VOLUMEUP=115, POWER=116 and the Samsung assistant key
0x2bf=703). Nothing else in this userspace owns those keys: there is no logind
session, phoc treats them as an ordinary keyboard, and the A27 framebuffer UI
(which used to read them) is masked. **One process must own the keypad**, or a
key press is handled twice — once by the real owner and once by a stale reader.

A32 established that ownership model and proved it on the handset. A33 keeps it
and completes the state machine: press *classes* (single / double / long / very
long), a real power menu, and the three screen gestures.

## 2. Input nodes are selected by capability, never by `eventN`

`/dev/input/eventN` numbering is a property of the kernel's enumeration order,
not of the hardware. It changes between boots and between kernel builds, and a
manager that hard-codes it breaks silently — the buttons simply stop working with
no error. Therefore:

| Node | Selection rule |
|---|---|
| keypad | scan `/dev/input/event*`; require `EVIOCGBIT(EV_KEY)` ⊇ {POWER, VOLUMEUP, VOLUMEDOWN}; tie-break on the name containing `gpio_keys`/`sec_key_notifier` |
| touchscreen | require `EVIOCGBIT(EV_ABS)` ⊇ {`ABS_MT_POSITION_X`, `ABS_MT_POSITION_Y`} **and** `EVIOCGPROP` with `INPUT_PROP_DIRECT`; tie-break on `sec_touchscreen`/`sec_ts` |

Capability bits are read with the kernel's own long size, so a key the driver
really reports can never be mis-classified as absent. `nuxel-button-manager
--probe` prints every node, its raw key/abs bitmaps and the resolved choice, so
the selection can be checked against `/proc/bus/input/devices` instead of being
trusted.

The touchscreen is opened **read-only and is never grabbed** (no `EVIOCGRAB`):
libinput, Phoc and the launcher keep receiving every event they receive today.
Gesture dispatch is therefore *additive*, and every action it emits is
idempotent (`action home` while already home is a no-op), so a gesture that the
launcher also handled cannot produce a double transition.

## 3. Press classes

All windows live in `configs/nuxel/input/button-fsm.json` and are mirrored as
`NUXEL_FSM_*` defines in `tools/s10plus/a33/nuxel-button-fsm.h`. The offline test
cross-checks JSON ↔ C ↔ the protected A32 source, so the three cannot drift.

| Class | Power | Bixby / assistant | Volume |
|---|---|---|---|
| debounce (below = ignored) | 30 ms | 20 ms | 20 ms |
| short press | 30 ms … 2000 ms | 20 ms … 1500 ms | any press |
| long press | ≥ 2000 ms | ≥ 1500 ms | ≥ 500 ms opens the hold class (panel) |
| very long press | ≥ 8000 ms | — | — |
| double press gap | 400 ms | 400 ms | — |
| chord (both keys) | Power+VolUp / Power+VolDn held ≥ 500 ms from the second key | | |
| autorepeat cadence (opt-in) | — | — | 400 ms, then every 250 ms |
| step per press | — | — | 5 % of the mixer range (range ÷ 20, floored at 1) |

**A32 compatibility.** A32 dispatched the power short-press action immediately on
release. A33 keeps that (`defer_power_short_for_double: false`) because the
protected baseline must not gain latency on a screen toggle. The *Bixby*
short press **is** deferred by the 400 ms double-press gap
(`defer_bixby_short_for_double: true`), which is where single-versus-double
actually matters (open-terminal versus voice-input); that is a documented,
intentional difference from A32, and the A32 source itself is untouched.

Actions per class:

| Key + class | Default action | Dispatch |
|---|---|---|
| power short | `screen-toggle` | display bridge FIFO (`/run/nuxel-wl-fb.cmd`) |
| power long | `power-menu` | opens the menu (§6) |
| power double | `camera` | launcher host FIFO |
| power very long (≥ 8 s) | `reboot-request` | gated userspace reboot (§7) |
| volume up / down | `volume-up` / `volume-down` | real ALSA mixer of the `beyond-madera` card |
| volume up held (≥ 500 ms) | `notifications-panel` | launcher host FIFO |
| volume down held (≥ 500 ms) | `all-apps` | launcher host FIFO |
| volume up/down held, **opt-in** | `volume-up-autorepeat` / `volume-down-autorepeat` | real ALSA mixer, A32 cadence |
| **Power + VolumeUp held ≥ 500 ms** | `sound-mode-cycle` | normal → vibrate → silent (`/var/lib/nuxel/audio/sound-mode`) |
| **Power + VolumeDown held ≥ 500 ms** | `screenshot` | launcher host FIFO |
| Bixby single | `open-terminal` | launcher host FIFO |
| Bixby double | `flashlight` | request consumed by the camera/flashlight arbitration (briq-08c) |
| Bixby long, outside the early window | `disabled` | intentionally inert |
| **Bixby long, inside the first 2 s of Nuxel userspace** | `verbose-boot-note` | one-time verbose boot for that boot only (§5) |

The mapping above is the **briq-03e exact mapping**, and it is checked twice: the
offline test compares it against `configs/nuxel/input/button-fsm.json`, and every
one of the 20 recorded traces must replay to its expected action sequence through
the real C state machine.

**A volume HOLD is not a key repeat.** The shipped default opens a panel, because
that is the mapping the beta specifies; the A32 autorepeat cadence is *preserved,
not deleted* — remap `volume_up_long` / `volume_down_long` to the
`*-autorepeat` actions (or set `volume_repeat_enabled: true`) and the 400 ms /
250 ms cadence runs exactly as A32 did, which the `volume-hold-autorepeat` trace
proves. **Predictability:** exactly one step is emitted per press (on the press,
like A32), so a press that turns out to be long still yields exactly one step and
never two; a chord buffers the step and delivers it on release if the chord does
not complete, so no press is ever silently swallowed. There is no double-press
volume class at all.

## 4. Chords and arbitration

Priority, highest first (enforced inside `nuxel_fsm_feed`, not by convention):

1. **Samsung hardware emergency combos** — never intercepted. The keypad is
   opened **without `EVIOCGRAB`**, so the kernel, the bootloader and Samsung's own
   reset/recovery key handling keep receiving every event. A Power+VolumeDown
   hold long enough for Samsung's reset still resets the handset regardless of
   what this state machine does.
2. **Multi-key chords** — Power+VolumeUp → `sound-mode-cycle`,
   Power+VolumeDown → `screenshot`, both after 500 ms measured from the *second*
   key press. While a chord is being decided the volume class is completely
   silenced, and when it fires it sets `power_used_long`,
   `power_used_very_long` and `vol_used_long`, so **no lower class — including
   the 8 s reboot class — can also act during that hold.**
3. **Long press** — power menu, notifications panel, all-apps, verbose note.
4. **Double press** — camera, flashlight.
5. **Single press** — screen toggle, terminal, one volume step.
6. **Key-repeat volume** — opt-in only (`volume_repeat_enabled`).

If a chord is armed but the other key is released before 500 ms, the chord is
cancelled and the buffered volume step is delivered: the `chord-cancelled-step`
trace pins that behaviour, including the power hold that continues on its own and
still opens the menu.

## 5. The one-time verbose-boot note (Bixby early hold)

Holding Bixby during the first **2 s of Nuxel's userspace** is the documented
one-time override that turns a verbose boot on *for that boot only* — it is never
persisted.

What actually exists, honestly:

* The daemon **synchronises the held-key state at start-up** with `EVIOCGKEY`.
  A key the owner is already holding when the manager opens the node produces no
  further evdev event, so without that sync a Bixby held through the boot would
  be invisible. A set bit becomes a synthetic press at `t ≈ start`, which lands
  inside the FSM's early window (measured from the first event the manager sees).
  The node is never grabbed and no release is ever synthesised.
* On the hold (≥ 1500 ms) the FSM emits `verbose-boot-note`. The daemon publishes
  the request `/run/nuxel/boot-verbose-once` — the file briq-02b's consumer reads
  — **only if that consumer has not run yet**.
* The button manager starts *after* the early boot stage, so in practice it
  usually **cannot** change the current boot. When the consumer has already run,
  the daemon records `VERBOSE_ONCE_REFUSED reason=boot-stage-already-ran
  state=BOOT_UPDATE_REQUIRED`: honouring an early hold *before the first userspace
  stage* needs a key capture in the initramfs/BOOT stage, which requires a BOOT
  update and is **not claimed as working**. That refusal is the honest result, not
  a silent no-op.
* The key must be Bixby (703), which is not part of any Samsung recovery combo, so
  the override cannot collide with a bootloader key combination.

An action set in `/etc/nuxel/input/buttons.json` (the A32 file, written by the
Settings UI and by `nuxelctl buttons set`) **wins** over the defaults above, so an
owner remap can never be overridden by the state machine.

## 6. The power menu

Long-press power opens a real menu. It is a state machine, not a placeholder:
the current selection is rendered into the launcher's own runtime document
(`/usr/share/nuxel/runtime/osd.json`, served by the launcher's static server, so
no new service or socket is needed), and it can be driven from the console
through the control FIFO (`/run/nuxel-buttons.cmd`: `menu-open`, `menu-up`,
`menu-down`, `menu-select`, `menu-close`).

| # | Entry | Action | Triggerable | Why |
|---|---|---|---|---|
| 0 | Lock screen | `lock` | yes | launcher host |
| 1 | Take screenshot | `screenshot` | yes | launcher host |
| 2 | **Restart** | `systemctl-reboot` | **no** | reboot gate closed: owner absent, no repository-side reboot policy has authorised a restart |
| 3 | **Power off** | `systemctl-poweroff` | **no** | powering off with no owner present would strand the mission |
| 4 | **Recovery (Samsung)** | `enter-recovery` | **no** — `NO_FLASH_INVARIANT` | entering Recovery means leaving Linux for the Samsung bootloader |
| 5 | **Download Mode (Odin)** | `enter-download-mode` | **no** — `NO_FLASH_INVARIANT` | Download Mode exists only to flash; this mission performs **no flashing of any kind** |

Navigation: volume up/down moves the selection, a short power press selects, a
second long press dismisses the menu, and an untouched menu closes itself after
15 s (`menu-close-timeout`) so a stray long press can never leave a modal menu on
the glass. A **refused** selection keeps the menu open and publishes the refusal
(`MENU_REFUSED action=… reason=…`) — the refusal is the observable proof, which
is exactly why the two bootloader entries exist in the table at all.

The invariant is enforced in code, not in a comment: `perform()` in
`nuxel-button-manager.c` intercepts `enter-recovery` and `enter-download-mode`
and refuses before any effect, and the manager contains no `heimdall`, `odin`,
`fastboot`, `/dev/block`, `dd if=`, `sysrq-trigger` or `reboot -f` surface at
all (checked mechanically by the offline test).

## 7. The reboot class and its gate

Holding power past **8 s** escalates from the menu to the reboot class: the menu
is dismissed and a `reboot-request` is produced. The request is *not* the
action — `nuxel_fsm_gate_decide()` decides, from
`/etc/nuxel/buttons/reboot-gate.json` plus bg-09's `/var/lib/nuxel/reboot/policy.json`
when that file exists, and the answer is **refused unless every one of these
holds**:

1. the gate is explicitly `enabled` (shipped default: **false**),
2. the per-action flag allows it (`allow_restart` / `allow_poweroff`; shipped: **false**),
3. bg-09's policy file, when present, also says `allow_reboot: true` (AND, never OR,
   so neither build group can override the other),
4. a known-working rollback path exists (`tools/nuxel-rollback-home.sh` or a
   `.prev-a32` bridge binary),
5. the minimum interval since the last reboot has elapsed (default 1800 s),
6. the hourly cap has not been reached (default 1 per hour),
7. when required, `journalctl --verify` reports a clean journal.

A `systemctl reboot` / `systemctl poweroff` is the **only** execution path, and it
is the single chokepoint in the program (`gated_system_action`). No sysrq trigger,
no `reboot -f`, no block-device write. Every decision — allowed or refused — is
appended to `/var/log/nuxel/buttons.log`, so a refusal is as auditable as an
action.

## 8. Screen gestures

| Gesture | Recognizer | Emitted action |
|---|---|---|
| swipe inward from the left/right edge (≤ 400 ms, ≥ 90 px, mostly horizontal) | edge-back | `back` |
| swipe up from the bottom 48 px zone (≤ 600 ms, ≥ 90 px, mostly vertical) | swipe-up-home | `home` |
| swipe up and **hold** ≥ 500 ms in the bottom zone (drift ≤ 24 px) | swipe-up-hold-recents | `recents` (fires once, on the timer, not on release) |

Multi-touch is deliberately limited to the primary slot (slot 0): the three
gestures this manager owns are single-finger gestures, and pretending to
recognise pinch would be dishonest. A lifted contact whose `ABS_MT_TRACKING_ID`
never arrives is dropped after `stale_track_ms` (1500 ms) rather than leaving a
phantom track behind.

## 9. Files

| File | Role |
|---|---|
| `configs/nuxel/input/button-fsm.json` | authoritative spec: press classes, action defaults, menu entries, gesture geometry, gate integration |
| `configs/nuxel/buttons/reboot-gate.json` | the gate itself (closed by default) |
| `configs/nuxel/buttons/settings-surface.json` | Buttons & Gestures settings contract (append point for briq-06d) |
| `configs/nuxel/buttons.json` | A32 owner-remappable action map (unchanged, still wins) |
| `tools/s10plus/a33/nuxel-button-fsm.h` | dependency-free, replayable state machine + the `-DNUXEL_FSM_MAIN` offline harness |
| `tools/s10plus/a33/nuxel-button-manager.c` | the daemon: node selection, mixer, OSD, menu, dispatch, gate |
| `tools/s10plus/a33/nuxel-button-manager.service` | systemd unit (single owner, `Restart=always`) |
| `tools/s10plus/a33/build-a33-buttons.sh` | builds the daemon and the replay helper |
| `tools/s10plus/a33/tests/test-button-fsm.py` | offline tests (replay, parity, gate, invariants) |
| `tools/s10plus/a33/tests/fixtures-p3/button-fsm/*.trace` + `.expected` | 20 recorded event traces with their expected action sequences (incl. the chords, the volume-hold panel, the opt-in autorepeat and the early hold) |
| `tools/s10plus/a33/tests/stub-include/alsa/asoundlib.h` | stub alsa declarations so the **daemon** can be syntax-checked on a host without alsa-lib (syntax gate only, never a build) |
| `tools/s10plus/a32/nuxel-button-manager.c` | **protected A32 baseline — untouched** |

## 10. How to inspect it

```sh
# whole system, one screen
nuxelctl buttons fsm                # spec + live state
nuxelctl buttons menu               # the menu table and why each entry is refused
nuxelctl buttons gates              # reboot gate decision and its inputs

# the manager itself
nuxel-button-manager --probe        # real nodes, capabilities, resolved choice, mixer
nuxel-button-manager --menu-dump    # the menu table as the daemon will render it
nuxel-button-manager --config-check # parse every config, print the gate decision
nuxel-button-manager --capture 10   # decode KEY/MT events for 10 s
nuxel-button-fsm-sim trace.json     # replay a recorded trace offline

# offline proof (no hardware, no phone)
python3 tools/s10plus/a33/tests/test-button-fsm.py
bash tools/s10plus/a32/tests/run-tests.sh        # A32 baseline suites
tools/beta/regression-guard.sh                   # A32 protected-asset gate (INV-4)
```

## 11. Owner test (NEEDS_OWNER_TEST)

Owner action is required for the parts no repository test can reach. Full
procedure: `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`, area 16/17/20.
Short form, with the phone in hand and the console available:

1. **Power short** → screen off, press again → screen on. Expected: display
   toggles, `nuxelctl status` shows the bridge state changing, no second
   framebuffer owner appears (`nuxelctl handoff status`).
2. **Power long (≈ 2 s)** → the power menu appears. Volume up/down moves the
   highlight; the highlight must not wrap incorrectly; the menu closes itself
   after ~15 s if left alone.
3. **Power long → Restart** → the entry must be **refused** with
   `MENU_REFUSED … reason=gate-closed-owner-absent` in
   `/var/log/nuxel/buttons.log`. Nothing may reboot.
4. **Power long → Recovery / Download Mode** → refused with
   `reason=NO_FLASH_INVARIANT`. The phone must stay in Linux. **Do not** enter
   Download Mode or the bootloader by any other means.
5. **Volume ±** → the volume OSD appears and the mixer value follows
   (`nuxelctl audio status`). A writable control is not audibility — sound is
   area 6.
6. **Bixby single** → the terminal opens; **Bixby double** → a flashlight
   request is published (`FLASHLIGHT_REQUESTED` in the audit log and
   `/run/nuxel/flashlight.request`); **Bixby long** → nothing happens
   (`disabled` by design) unless it is inside the 2 s early window.
7. **Volume up held ~1 s** → the notifications panel opens; **volume down held
   ~1 s** → the all-apps view opens. Only one step of volume must be applied per
   press. If the owner prefers the A32 ramping feel, set "Hold volume to repeat".
8. **Power + VolumeDown held together ~1 s** → exactly one `screenshot` action.
   **Do not** keep holding to test Samsung's reset (that resets the handset by
   hardware design and is out of scope).
9. **Power + VolumeUp held together ~1 s** → the sound mode cycles
   normal → vibrate → silent (`SOUND_MODE=…` in the log,
   `/var/lib/nuxel/audio/sound-mode`); whether the mode is *audible* is area 6.
10. **Bixby held from before the launcher starts** → `VERBOSE_ONCE_REQUESTED` or,
    as expected on the current BOOT image, `VERBOSE_ONCE_REFUSED
    reason=boot-stage-already-ran state=BOOT_UPDATE_REQUIRED`. Both are correct;
    a silent no-op would not be.
7. **Swipe up** → home; **swipe up and hold** → recents; **edge swipe inward** →
   back. Expected: each gesture produces exactly one action (no double
   transition) because dispatch is idempotent and the touchscreen is not grabbed.
11. **Power ≥ 8 s** → the menu closes and the reboot class fires; the gate refuses
   by default and logs `REBOOT_REFUSED`. Do **not** enable the gate to "make it
   work" during the owner test.

Failure symptoms to report verbatim: no OSD at all (the manager is not running:
`systemctl status nuxel-button-manager`), `KEY_DEVICE_NOT_FOUND` (keypad node
resolution), `TOUCH_DEVICE_NOT_FOUND` (gestures will be silently absent),
`POWER_DEBOUNCED held=…ms` (press windows), `REBOOT_REFUSED reason=…` (the gate
working as designed), double transitions on a swipe (a second reader is also
handling gestures).

## 12. Rollback

The A33 manager is additive: the A32 binary, service unit and `buttons.json` are
untouched, so the rollback is a straight reinstall of the A32 pair.

```sh
# keep the current state, then return to the verified A32 manager
install -m0755 /usr/lib/nuxel/nuxel-button-manager /usr/lib/nuxel/nuxel-button-manager.a33
git checkout -- tools/s10plus/a32/nuxel-button-manager.c tools/s10plus/a32/nuxel-button-manager.service
bash tools/s10plus/a32/build-a32.sh          # rebuild on the guest
install -m0755 build/out/s10plus/a32/nuxel-button-manager /usr/lib/nuxel/nuxel-button-manager
install -m0644 tools/s10plus/a32/nuxel-button-manager.service /etc/systemd/system/nuxel-button-manager.service
systemctl daemon-reload && systemctl restart nuxel-button-manager
```

After any rollback, re-run `tools/beta/regression-guard.sh` — INV-4 must stay
green.
