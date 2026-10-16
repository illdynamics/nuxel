# Nuxel Beta — Manual Proof Checklist (26 areas)

**For the phone owner.** This document is the human half of the beta acceptance: everything a script,
a VM or a unit test cannot settle. Every area below carries the **Feature**, **Why it matters**,
**Exact preparation**, **Exact action**, **Expected result**, **Failure symptoms**, **Diagnostic
command or log path**, **PASS**, **FAIL** and **Current automatic evidence**.

| Field | Value |
|---|---|
| Document | `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` |
| Device | Samsung Galaxy S10+ **SM-G975F** (`beyond2lte`, Exynos 9820) |
| Platform | Nuxel — Fedora 43 ARM64 userspace, Linux **4.14.253** (Samsung vendor), systemd PID 1 |
| Probe | Nuxel Home PWA over WebKitGTK → headless Phoc/Wayland → `nuxel-wl-fb` → `/dev/fb0` |
| Compiled by | `bg-12-reports` / `briq-12b-manual-proof-checklist` at repository revision `838a00a5…` |
| Area 1 re-stamped | `bg-01-touch-pipeline` / `briq-01d-touch-owner-test`, over the same consolidation base (`f36646a` + cycle-002 working tree): area 1's action sequence now matches what `nuxel-touch-capture.sh` prints (tap / three taps / swipe / multi-contact / select an app / on-screen keyboard), the counts are refreshed (240 PASS, gate 27 files, self-test 43/43) and the measured charger-mode state is carried. Sections 2–26 are otherwise unchanged. |
| Pass 1 (areas 1–19) | 2026-10-16T14:26Z (16:26 +02:00, `Europe/Amsterdam`) — from the `manual-proof/` fragments |
| Pass 2 (areas 20–26) | 2026-10-16T16:55Z (18:55 +02:00, `Europe/Amsterdam`) — synthesized; source fragments for these areas were not present at either pass (see each area's **Source note**) |

> **You are the instrument.** Nothing in this document has been promoted to "verified" by a script.
> A green test in the tree is `OFFLINE_TESTED`; it means the *tooling* works, not that the *hardware*
> does. Your observation is what turns a `NEEDS_OWNER_TEST` item into a verdict. **Never record an
> observation you did not make**, and never write PASS for a step you skipped — "could not test" is an
> honest and useful result.

> **Absolute invariant — read before starting.** Do **not** flash anything, ever. No Odin, no
> Heimdall, no Download Mode, no Recovery, no TWRP, no raw-partition writes. The **Recovery** and
> **Download Mode** entries in the power menu (area 8) are *designed to refuse* and must never be
> triggered by any other means. Reboots are allowed but must return to Nuxel; if a reboot does not
> return to Nuxel, stop and use the rollback path (`tools/nuxel-rollback-home.sh`) rather than
> repeating the reboot.

---

## How to read this document

### Verdict legend (what "current automatic evidence" means)

| Tag | Meaning |
|---|---|
| `VERIFIED_ON_S10PLUS` | observed working **on the physical handset**. In this document this appears only where an **A32/A24 record** measured it on hardware; a script cannot earn this tag. |
| `VERIFIED_IN_VM_ONLY` | proven in the UTM Fedora 43 guest, not on the phone |
| `OFFLINE_TESTED` | executed on the build host (unit test / build / static analysis) — the *tooling* is sound |
| `DEPLOYED_UNVERIFIED` | staged to the phone but not yet exercised |
| `IMPLEMENTED_NOT_DEPLOYED` | code/config exists; nothing deployed |
| `NEEDS_OWNER_TEST` | implemented + instrumented; **your** action on the device is required |
| `BLOCKED_KERNEL` / `BLOCKED_FIRMWARE` / `BLOCKED_HARDWARE` | needs a kernel/firmware/hardware change that is **not** deployed |
| `BLOCKED_EXTERNAL_RESOURCE` | a phone console / VM / owner / input archive is not reachable |
| `NOT_SUPPORTED_ON_DEVICE` | will never work on this hardware, by design |
| `FAILED` / `DEFERRED` | attempted and did not work / deliberately out of this beta |

### Roll-up — all 26 areas at a glance

| # | Area | On-device verdict | Owner action? | Primary diagnostic |
|---|---|---|---|---|
| 1 | Touchscreen | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxel-touch-capture.sh --seconds 90` |
| 2 | Launcher | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`; VM leg = `bg-11`) | **Yes** | `launcher-registry-test.js` + `curl` |
| 3 | Display & boot animation | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxelctl handoff audit` |
| 4 | Wi-Fi / internet | `NEEDS_OWNER_TEST` (default `BLOCKED_FIRMWARE`) | **Yes** | `nuxelctl wifi status` |
| 5 | Timekeeping | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxelctl time verify` |
| 6 | Audio & microphone | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxelctl audio pipeline` |
| 7 | Headphones | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxelctl headphone status` |
| 8 | Hardware buttons | A32 part `VERIFIED_ON_S10PLUS` (record); A33 FSM `OFFLINE_TESTED`; gestures `NEEDS_OWNER_TEST` | **Yes** | `nuxelctl buttons fsm` |
| 9 | Flashlight | `NEEDS_OWNER_TEST` (control logic `OFFLINE_TESTED`) | **Yes** | `nuxel-led-diag.sh status` |
| 10 | Vibration | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxel-haptics-diag.sh status` |
| 11 | Bluetooth | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxel-bluetooth-diag.sh status` |
| 12 | NFC | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxel-nfc-diag.sh status` |
| 13 | GPS / GNSS | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** (outdoors) | `nuxel-gnss-diag.sh status` |
| 14 | Sensors | `NEEDS_OWNER_TEST` (repo `OFFLINE_TESTED`) | **Yes** | `nuxel-sensors-diag.sh status` |
| 15 | Camera | `NEEDS_OWNER_TEST`; capture unproven; app `present/partial` | **Yes** | camera app + `nuxelctl` |
| 16 | SIM & mobile data | `BLOCKED_FIRMWARE` (no upstream Shannon modem plugin) + `NEEDS_OWNER_TEST` (SIM detect) | **Yes** (confirm honesty) | `nuxel-power-diag.sh` + ModemManager |
| 17 | Phone calls & SMS | `BLOCKED_FIRMWARE` (modem plugin) — apps must **report** the gap | **Yes** (confirm honest UI) | `test-phone-apps.py` + dialer |
| 18 | microSD | `NEEDS_OWNER_TEST` (doc not present at aggregation) | **Yes** | block-device probe |
| 19 | App Store | `NEEDS_OWNER_TEST` (NuXtore `present/full` offline; doc not present) | **Yes** | NuXtore app |
| 20 | Applications | `NEEDS_OWNER_TEST`; inventory `present/full` for 19 apps | **Yes** | `verify-app-inventory.py` + launch each |
| 21 | VPN & remote access | `NEEDS_OWNER_TEST` (repo claim ladder `OFFLINE_TESTED`) | **Yes** | `nuxel-vpn-tor.sh claims` |
| 22 | Firewall & permissions | `OFFLINE_TESTED` (49/49) + `NEEDS_OWNER_TEST` (on-device apply) | **Yes** | `nuxel-firewall.sh show` |
| 23 | Live Console local takeover | console path A24 `VERIFIED_ON_S10PLUS` (record); PWA surface **absent** (`icons only`) | **Yes** | `nuxel-console-host.sh` |
| 24 | Battery & power management | `NEEDS_OWNER_TEST` (control surface `OFFLINE_TESTED`) | **Yes** | `nuxel-power-diag.sh status` |
| 25 | Reboot persistence | `NEEDS_OWNER_TEST`; release doc not present at aggregation | **Yes** | `nuxelctl time mark/compare` + boot state |
| 26 | Long-term stability | `NEEDS_OWNER_TEST` / not measured; soak doc not present | **Yes** (multi-hour) | `nuxelctl` + journal |

> **Where a source document was not present at aggregation time**, the row says so in its
> "Current automatic evidence" field and the entry is synthesized from the evidence that *does* exist
> (the app inventory, the working tools, the A32 record). Absent evidence is named, never invented.

### Universal preparation (do these once, before area 1)

1. Boot the handset **normally** into Nuxel (not charger mode). Verify:
   ```sh
   tr ' ' '\n' < /proc/cmdline | grep androidboot.mode      # must print NOTHING
   ```
   If it prints `androidboot.mode=charger`, the touchscreen does not exist for this boot — unplug the
   charger, reboot normally, and start again.
2. Reach the **live root console** (USB CDC-ACM) or the on-device **Terminal** app. Keep a second
   terminal open for `journalctl -f`.
3. Confirm the **rollback path** exists before you change anything:
   `test -x tools/nuxel-rollback-home.sh && echo ROLLBACK-OK`.
4. Work through the areas in order; each area is independent, and a FAIL in one does **not** block the
   others. After **three same-mode failures** on the same step, stop and change strategy (a different
   location, cable, tag, peer or measurement) — do not loop.

---

## Area 1 — Touchscreen: finger on the glass, end to end

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes.**

**Feature.** Interactive touch input on the S10+ across the whole chain
`sec_ts → IRQ → evdev → libinput → phoc → Wayland → WebKitGTK → Nuxel Home`, proven by a real contact
with real coordinates reaching the launcher document and the launcher acting on it.

**Why.** Without touch the phone is not interactive: the launcher, Settings, every app and the whole
"interactive Nuxel" claim depend on it. This is also the area that misled six earlier cycles — first by
a charger-mode boot in which the touchscreen genuinely does not exist, then by measuring a fixed input
node number that belonged to the wrong device. The test therefore **checks the boot mode first** and
selects the panel **by capability, never by node number**.

**Exact preparation.**
1. Normal boot (see the universal preparation); `tr ' ' '\n' < /proc/cmdline | grep androidboot.mode`
   must print nothing.
2. Root console or on-device Terminal.
3. Sanity: `grep -A5 sec_touchscreen /proc/bus/input/devices` → expect `B: PROP=2` and MT axes.
4. Nothing else. The harness takes an owner-test lock (`/run/nuxel-touch-capture.lock`) so the boot-mode
   guard cannot reboot mid-test, holds the reader open only for the bounded window, and releases it on
   exit. Budget 90 s of touching; the session is hard-bounded and cannot hang the console.

**Exact action.** `nuxel-touch-capture.sh --seconds 90` prints this sequence before it arms; perform it
deliberately and slowly, in this order (it is the same text the harness writes into `<BUNDLE>/commands.txt`):

1. **TAP DOWN/UP** — one tap in the centre of the screen (slow, ~0.3 s).
2. **THREE TAPS** — top-left, centre, bottom-right (catches a swapped/inverted axis).
3. **SWIPE** — bottom third → top third, slowly (≥ 1 s), for scroll/gesture.
4. **MULTI-CONTACT** — two fingers down together for ~1 s, then lift both (slot + tracking-id behaviour).
5. **SELECT AN APP** — tap a launcher tile (Terminal or Settings) and let it open.
6. **KEYBOARD** — if a text field is reachable, type three keys on the on-screen keyboard (it proves the
   keyboard's own hit testing on the same pipeline).

The **completion definition for the whole touch mission** is: a real finger opens **Settings**, returns
**Home**, opens **Terminal**, scrolls the launcher, selects an app, and uses the on-screen keyboard.
Anything less is not a finished touch story even if the machine gate passes.

Then:
1. If the harness says layer 7 has no evidence, stage the probe and repeat the taps in it:
   `python3 /usr/libexec/nuxel/nuxel-touch-trace.py --stage-probe`, then open `/touch-probe.html` as the
   receipt instructs.
2. Save the `BUNDLE=…` path and the verdict block.
3. Confirm the human half: did the tapped tile **open**? Does a tap ring/dot appear under your finger on
   the probe page? Does a swipe move the UI in the direction you swiped?
4. Write down: the actions you performed, the `CAPTURE_GATE=` line, the `FIRST_FAIL_LAYER=` line, and
   your answer to step 3.

**Expected result.**
* `CAPTURE_GATE=PASS` with `gate.json` showing `down ≥ 1`, `up ≥ 1`, `coords_plausible: true`,
  `dom_layer_state: "ok"`.
* `grep '^LAYER=' <BUNDLE>/trace.txt` shows `STATE=ok` for layers 1–7.
* Coordinates track your finger (top-left → small x/y; bottom-right → large; the swipe keeps x roughly
  constant while y changes monotonically).
* The launcher tile opens, and the probe page draws a ring under your finger.
* `<BUNDLE>/events.jsonl` exists with one JSON record per input event (kernel timeval `ts`/`iso`) and a
  `point` record per frame carrying raw + mapped coordinates; `<BUNDLE>/coordinate-map.json` records the
  1440x3040 panel, the device range and its source, the output scale/transform and `validation.verdict`.
* **Completion definition for the whole touch mission** (nothing less counts as a finished touch story):
  a real finger opens **Settings**, returns **Home**, opens **Terminal**, scrolls the launcher, selects
  an app, and uses the on-screen keyboard.

**Failure symptoms.** `charger` in `/proc/cmdline` or `verdict=CHARGER_MODE_TOUCH_DISABLED` (harness
exit 10) = charger/LPM boot — unplug, reboot normally, redo. No `sec_touchscreen` = driver did not bind.
Layer 2 `drop` = events come from the wrong device. Layer 3 `drop` = node lacks `INPUT_PROP_DIRECT`.
Layer 4 `drop` = shim rejected every candidate. Layer 5 `drop` = compositor holds no input fd. Layer 6
`drop`/`blocked` = no `wl_touch`. Layer 7 `blocked` with others `ok` = no DOM evidence. `points=0` =
glass was not touched in the window. Coordinates plausible but the UI did not react = a launcher issue,
not a driver issue. Taps at the mirrored position = axis orientation.

**Diagnostic command / log path.**
```sh
tr ' ' '\n' < /proc/cmdline | grep -E 'androidboot.mode|lpcharge|charging_mode'
dmesg | grep -i -E 'sec_ts|sec_touchscreen|tsp_|is_lpm' | tail -40
grep -A5 sec_touchscreen /proc/bus/input/devices
grep -a 'accepted=1' /run/nuxel-libinput-path.state | tail -3
p=$(systemctl show -p MainPID --value nuxel-wayland); ls -l /proc/$p/fd | grep -c input
grep -a NUXEL_INPUT /run/nuxel-home.state | tail -10
```
Bundle files: `<BUNDLE>/gate.json`, `trace.txt`, `touch-events.log`, `raw-touch.bin`, `evdev.txt`,
`libinput-path.state`, `compositor-fds.txt`, `wayland-seat.txt`, `dom.txt`, `diagnostics.txt`,
`bootmode.txt`; plus `/run/nuxel-touch-dom.log`, `/run/nuxel-home.state`, `/run/nuxel-bootmode.json`.
Offline regression for the tooling: `./tools/s10plus/a33/tests/run-touch-tests.sh`.

**PASS.** On a **normal** boot: `CAPTURE_GATE=PASS` with `down ≥ 1`, `up ≥ 1`, coordinates inside the
device range observed at the DOM layer, **and** you confirm the UI responded correctly. Attach the
bundle path and the `LAYER=` lines.

**FAIL.** Any of: charger-mode boot, no `CAPTURE_GATE=PASS`, coordinates outside the device range,
inverted/mirrored mapping, no UI reaction, or a check you could not perform. Record the exact
`FIRST_FAIL_LAYER=` line and do not report any layer as working that was not observed.

**Current measured state — read this before planning the test.** A bounded, read-only probe of the
running phone over the USB CDC-ACM console found the handset **booted in charger / low-power mode**
(transcript and grading: `docs/beta-finalization/live/evidence/touch-20261016T193756+0200-cycl001-p0probe-live-run/`):

| Probe | Result on that boot |
|---|---|
| `/proc/cmdline` | `androidboot.mode=charger`, `charging_mode=0x3030` |
| `dmesg` | `[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1` |
| `grep -c sec_touchscreen /proc/bus/input/devices` | `0` |
| `/sys/class/sec/tsp`, `/proc/interrupts` `sec_ts` line | absent |
| `nuxel-touch-arm.service` | `failed` |
| fb0 panel | `U:1440x3040p-0`, virtual_size `1440,6080`, 32 bpp |

**Consequence: this test cannot pass in that state.** On a charger-mode boot the controller is never
initialised, so no touch device exists and no finger can produce an event; every layer grades `blocked`
(never `ok`) with `FIRST_FAIL_LAYER=1`. Preparation step 1 (unplug + normal reboot) is what changes it.

**Current automatic evidence.** `./tools/s10plus/a33/tests/run-touch-tests.sh` → **`TOUCH-TESTS: ALL
PASS`** (**240 PASS / 0 FAIL**: `test-touch-trace.py` 67/67, `test-bootmode-guard.py` 53/53,
`test-capture-harness.py` 33/33, `test-no-eventn-literal.py` **27 files checked**/0 failing,
`test-libinput-shim-invocation.py` 27/27, shim fixtures 19/19, A31/A33 parity 6/6, plus the 8
`run_step` summary lines). `nuxel-touch-trace.py --self-test` → **`SELF-TEST: PASS (43/43
assertions)`**. Archived real handset captures graded: A20/A21 → layers 1 and 3 `ok`,
`FIRST_FAIL_LAYER=2`; older captures honestly all-`blocked`. Full table:
`docs/beta-finalization/touch/OFFLINE-TEST-RESULTS.md`; owner procedure in full:
`docs/beta-finalization/manual-proof/01-touchscreen.md`. **No finger produced a real contact in this
cycle**, so the area stays `NEEDS_OWNER_TEST`.

---

## Area 2 — Launcher: the Nuxel Home PWA, its registry, its apps and its safe areas

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · VM leg owned by
`bg-11-vm-parity` (`docs/beta-finalization/vm/LAUNCHER-PARITY.md`, not present at aggregation) ·
**Owner action: Yes.**

**Feature.** The launcher is the existing **Nuxel Home PWA** — not a new launcher — served by
`nuxel-pwa-host` (WebKitGTK on headless Phoc/Wayland, presented through the framebuffer bridge). Four
claims: (2.1) the served bundle is the current one (status bar `0.4.1-a33`, cache namespace `v5-a33`);
(2.2) the registry contains **Terminal** and a runnable **Settings**; (2.3) tapping a tile really opens
the app; (2.4) the status bar lays every item **outside** the ten-zone blocked intervals (S10+ portrait:
zones 9,10 = the hole-punch cutout).

**Why.** The launcher is the only UI the phone has — home screen, app switcher and entry point to every
app. Parity with the VM matters because the VM is the reference truth. Cache/version drift matters
because a stale service-worker bundle silently serves an old UI that *looks fine* — exactly how
Terminal went missing on the device copy.

**Exact preparation.**
1. Normal boot, screen on, not charger mode (area 1).
2. Root console or Terminal; the launcher must be foreground. If the boot animation is still up, read
   `cat /run/nuxel-anim-handoff` — it must contain `owner=ui`.
3. Record the current bundle (30 s):
   ```sh
   curl -s http://127.0.0.1:8000/pwa/nuxel-home/js/status-bar.js | grep -m1 VERSION
   curl -s http://127.0.0.1:8000/pwa/nuxel-home/manifest.json | python3 -c \
     'import json,sys; print(json.load(sys.stdin)["nuxel"])'
   ```
   Expect `VERSION = "0.4.1-a33"`, `pwa_version 0.4.1-a33`, `cache_version v5-a33`, `registry_version 4`.
4. Nothing needs to be installed, flashed or rebooted for this test.

**Exact action.**
1. **Registry:** confirm the grid contains Terminal, Settings, Phone, Messages, Contacts, Mail,
   Calendar, Notes, Files, Camera and Live Console.
2. **Launch Terminal:** a real PTY must open inside the frame (a prompt; typing `id` answers). Tap
   Back/close → the grid returns without a reload flash.
3. **Launch Settings:** the real Settings UI must render (tabs Display/Sound/Buttons/Developer/…), not a
   blank frame.
4. **Safe areas (portrait):** look at the top-right corner around the hole-punch. The clock, battery,
   signal and Wi-Fi items must all be clear of the cutout; nothing under it; no painted "blocked zone".
5. **Editor:** Settings → Display → Safe zones. The preview strip must move like the real bar. Block
   zones 9 and 10 in portrait and press *Apply to real status bar (preview)* — the right cluster must
   move **left**, not off the panel. Press *Cancel* to restore.
6. **Stale-bundle check:** reboot normally once (area 25) and confirm steps 1–4 still hold.

**Expected result.** App grid identical to the UTM VM, Terminal and Settings present and opening real
content; status-bar items readable and none under the cutout, with no shift when a notification arrives;
the editor's preview and the real bar agree for the S10+ preset and for zones 1,2 (left) and 5,6
(centre); no crash, no double launcher, one status bar.

**Failure symptoms.** Terminal missing / Settings blank ⇒ stale bundle or registry ≠ v4. Icons and
wallpaper with R/B swapped ⇒ colour conversion (area 3), not the launcher. Items under the cutout or
vanishing ⇒ safe-zone layout did not run. Right cluster pushed off-panel ⇒ the A32 one-way push
returned. Row drifts on each notification ⇒ non-idempotent layout. Never appears after the animation ⇒
handoff (area 3).

**Diagnostic command / log path.**
```sh
grep -i 'status-bar\|safezones' /run/nuxel-home.state
grep -i SAFEZONES /var/log/nuxel/*.log 2>/dev/null
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/manifest.json
node tools/s10plus/a33/tests/launcher-registry-test.js
node tools/s10plus/a32/tests/safe-zones-test.js
bash tools/beta/regression-guard.sh
```
Logs: `/var/log/nuxel/pwa-host.log`, `/run/nuxel-home.state`.

**PASS.** The grid matches the VM; Terminal opens a working PTY; Settings renders real content; the
status bar is clear of the cutout; the editor's preview and the real bar agree; the same holds after one
normal reboot.

**FAIL.** Any of: missing Terminal/Settings, a blank frame, items under the cutout, the right cluster
off-panel, or a UI that disappears after the animation. Attach the `curl` output and the `SAFEZONES …`
line.

**Current automatic evidence.** Run this cycle: `node tools/s10plus/a33/tests/launcher-registry-test.js`
→ *passed* (1 warning: the Live Console entry is served by another build group);
`node tools/s10plus/a32/tests/safe-zones-test.js` → *all safe-zone tests passed* (44/44);
`bash tools/beta/regression-guard.sh` → `PASS` (INV-1, INV-3 green). A32 record: the handset and the VM
share byte-identical `index.html`/CSS/icons and `js/apps.js`. **No owner observation on the glass**, so
this area stays `NEEDS_OWNER_TEST`.

---

## Area 3 — Display and boot animation

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` (colour bridge also
VM-built) · live leg owned by `bg-10`, VM leg by `bg-11` · **Owner action: Yes.**

**Feature.** Five owner-visible properties of the boot surface, in order: (3.1) the boot animation plays
**at least one complete cycle** (192 frames @ 24 fps = 8000 ms) before the panel changes hands; (3.2)
**exactly one** process writes `/dev/fb0` and the handoff is recorded as a receipt; (3.3) the launcher
takes over only **after** it is ready, else the animation **resumes**; (3.4) colour order is correct — a
pure red image is red, not blue (XRGB8888 shm → DECON `ABGR_8888`); (3.5) the **verbose-boot** option
exists in Settings, is durable, and puts the boot log on the glass early, with the one-time **Bixby
hold** override either honoured or honestly reported as requiring a BOOT update; (3.6) the status bar
stays inside the ten-zone safe areas through and after the handoff.

**Why.** The boot surface is the first thing you see and the one place where a defect is unmistakable:
a cut animation, a frozen wallpaper, a blue sky that should be red, or a boot log that never appears. It
is also where two writers can corrupt each other's frames, so single ownership is a correctness
property, not a style choice.

**Exact preparation.**
1. Live console, root, **not** in charger mode. Nothing is flashed; this is one **normal reboot** and a
   read-only audit.
2. Capture the pre-reboot state:
   ```sh
   cat /run/nuxel-anim-handoff 2>/dev/null
   cat /var/lib/nuxel/fb-owner 2>/dev/null
   tail -n 20 /var/lib/nuxel/anim-handoff.log 2>/dev/null
   ```
3. Confirm a rollback path exists (`docs/beta-finalization/release/ROLLBACK.md` — not present at
   aggregation; the in-tree rollback is `tools/nuxel-rollback-home.sh`).
4. Budget one boot (~60–90 s) plus 5 minutes of reading receipts. **One** reboot, not a loop.

**Exact action.**
1. Reboot normally (`systemctl reboot`) and watch the panel from the first frame.
2. Reconnect the console and audit: `nuxelctl handoff status`, `nuxelctl handoff audit`,
   `cat /run/nuxel-anim-handoff`.
3. Read the kernel markers:
   `dmesg | grep -E 'NUXEL_ANIM|ANIM_MIN_CYCLE|ANIMATION_STOP|LAUNCHER_DISPLAY|NUXEL_FB_OWNER_BUSY'`.
4. **Colour order** through the real pipeline:
   ```sh
   sudo systemctl set-environment NUXEL_HOME_URL=http://127.0.0.1:8000/pwa/nuxel-home/colour-test.html
   sudo systemctl restart nuxel-pwa-host        # the glass must be RED; tap cycles R/G/B/WHITE/BLACK/GREY/THIRDS
   sudo systemctl unset-environment NUXEL_HOME_URL
   sudo systemctl restart nuxel-pwa-host        # back to the normal launcher
   ```
5. **Verbose boot:** `nuxelctl verbose-boot status`, then `nuxelctl verbose-boot on`, reboot once, and
   confirm the boot log appears on the glass early; afterwards `nuxelctl verbose-boot off`.
6. **Safe areas after handoff:** confirm zones 9,10 are still excluded in portrait (area 2, step 4).

**Expected result.** The animation plays **all the way through** (a full golden/logo cycle, no truncated
loop) and then, without a blank frame, the launcher appears. Receipts: `NUXEL_ANIM_LOOP=n` increasing;
`ANIM_MIN_CYCLE … n/1 reached=1` then `ANIM_MIN_CYCLE_COMPLETED`; `ANIMATION_STOP_REQUESTED` →
`ANIMATION_STOP_CONFIRMED`; `LAUNCHER_DISPLAY_OWNER` + `NUXEL_ANIM_HANDOFF receipt=<id> owner=ui
stage=LAUNCHER_DISPLAY_OWNER terminal=1`; `/run/nuxel-anim-handoff` with `owner=ui`, `stage`,
`terminal=1`, `loops=n/m`, `boot_id`, `ts`; `/var/lib/nuxel/fb-owner` with a single writer; **no**
`NUXEL_FB_OWNER_BUSY` in a healthy boot; `colour=R@0,G@8,B@16_abgr8888_override=1`. Verbose boot: the
log is visible before the launcher, the setting survives the reboot with `set_by=user`,
`/run/nuxel/verbose-boot` reports `NUXEL_VERBOSE_BOOT=1 SOURCE=config`, and the receipt says
`reason=verbose_boot_requested terminal=0` (a deliberate waiver — never reported as a completed cycle).

**Failure symptoms.** Animation stops halfway / freezes ⇒ the minimum-cycle floor was not honoured
(`ANIM_MIN_CYCLE_NOT_SEEN`, `_DEGRADED`, or a `terminal=0` receipt). Animation plays but the panel shows
a static wallpaper piece or black ⇒ the launcher never took ownership and no resume happened. Frames
from two sources alternate ⇒ two `/dev/fb0` writers; look for `NUXEL_FB_OWNER_BUSY`. Everything blue
that should be red ⇒ colour conversion bypassed. Verbose boot ON but no log ⇒ the early boot stage did
not read `/etc/nuxel/boot/verbose-boot.json`. Bixby hold does nothing ⇒ **expected today**:
`BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED`, deliberately not faked.

**Diagnostic command / log path.**
```sh
nuxelctl handoff status | simulate | audit
nuxelctl verbose-boot status | on | off | override
cat /run/nuxel-anim-handoff /var/lib/nuxel/fb-owner /var/lib/nuxel/anim-min-cycle.completed
cat /run/nuxel/verbose-boot /run/nuxel/anim-skip.request /run/nuxel/boot-stage-capabilities
tail /var/lib/nuxel/anim-handoff.log /var/log/nuxel/boot-stage.log
dmesg | grep -E 'NUXEL_ANIM|ANIM_MIN_CYCLE|ANIMATION_STOP|LAUNCHER_DISPLAY|NUXEL_FB_OWNER_BUSY'
python3 tools/s10plus/a33/nuxel-anim-handoff.py audit
python3 tools/s10plus/a33/nuxel-verbose-boot.py --selftest
```

**PASS.** A full animation cycle, a clean handoff with a valid receipt and a single owner, a red image
that is red on the glass, verbose boot visible + durable, and the status bar clear of the cutout.

**FAIL.** Any of: a truncated animation, a blank/static panel after the animation, two framebuffer
writers, a wrong colour order, a verbose boot that shows nothing, or an override that claims to work
without doing so.

**Current automatic evidence.** `tools/s10plus/a33/tests/run-boot-tests.sh` → `BOOT-TESTS: ALL PASS`
(colour golden bytes; handoff decision table + single-owner proof; verbose-boot durability; safe zones).
The A33 bridge built as an aarch64 ELF on the UTM Fedora 43 guest (sha256
`2d8718c4d92858bbae02b7e914f0172d295b1c12446eb861e91c355f2ac912fc`) and passed its own
`--colour-selftest`/`--handoff-selftest` there — **not deployed** to the phone. Bixby-hold override is
`BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED`. **No boot was observed by a human in this run**, so the area
stays `NEEDS_OWNER_TEST`.

---

## Area 4 — Wi-Fi association and data path

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · default state
`BLOCKED_FIRMWARE` until an association is observed · **Owner action: Yes.**

**Feature.** Wi-Fi bring-up on the S10+ radio (Murata/Broadcom **BCM4375-class** behind the Samsung
SDIO/PCIe glue): NetworkManager policy (`configs/networkmanager/10-nuxel-s10plus-wifi.conf`), supplicant
parameters, a credential-free connection template, the evidence-only diagnostic
`tools/s10plus/a33/nuxel-wifi-diag.sh` (also `nuxelctl wifi …`), and the manual association test below.

**Why.** Network, time sync (area 5), the browser, NuxTore and every "online" claim depend on a working
radio. The repository must not claim Wi-Fi works because files exist: the diagnostic reports only what
the live kernel, firmware directory and NetworkManager actually show. **Note:** the repo's Pixel
`BCM4390` document does **not** apply to this device and was not used.

**Exact preparation.**
1. Normal boot, screen unlocked; a 2.4/5 GHz AP in range whose **WPA2-PSK** credential you know
   (Enterprise/WPA3-SAE out of scope).
2. Console/SSH or the Terminal app.
3. Zero-cost snapshot first:
   ```sh
   nuxelctl wifi status ; nuxelctl wifi status --json ; nuxelctl wifi firmware
   ```
   If the verdict is `BLOCKED_DRIVER` or `BLOCKED_FIRMWARE`, **stop** — bring-up work is needed
   (offline, no flashing), not a retry loop.

**Exact action.**
1. `nuxelctl wifi report > /tmp/wifi-before.txt` (also appended to `/var/log/nuxel/wifi-diag.log`).
2. `nuxelctl wifi scan` → the SSID must appear with the expected security.
3. `nuxelctl wifi connect "<SSID>"` (type the PSK when prompted; the tool never stores it).
4. `nuxelctl wifi status` → verdict line `ASSOCIATED`.
5. Prove the data path: `ip -4 addr show dev wlan0` shows an IPv4 address; `getent hosts fedoraproject.org`
   resolves; open the Nuxel browser and load one page.
6. Leave it connected 10 minutes and re-run `nuxelctl wifi status` — a link that drops while idle is a
   power-save failure and must be reported as such, not as "Wi-Fi works".
7. Save: post-run `nuxelctl wifi report` + `journalctl -b -u NetworkManager --no-pager | tail -100`.

**Expected result.** The scan lists the AP with a plausible signal; connect returns success and status
prints `ASSOCIATED` with a non-empty IPv4 address; DNS resolves and one page loads; after 10 idle minutes
the link is still associated.

**Failure symptoms.** `BLOCKED_DRIVER` (no wireless netdev / no module) = kernel-side. `BLOCKED_FIRMWARE`
(netdev present, no blob) = deploy firmware into `/lib/firmware` (repository-only; never a flash).
`BLOCKED_EXTERNAL_RESOURCE` (no `wpa_supplicant`) = package gap. Scan sees the AP but connect fails
`Secrets were required` = wrong PSK/key management. Connects but no IPv4 = DHCP failure. Drops after
minutes = firmware/power-save; capture `dmesg` before touching config. Empty scan is **not** a failure —
report as unproven, never PASS.

**Diagnostic command / log path.**
```sh
nuxelctl wifi status | firmware | scan | report        # tools/s10plus/a33/nuxel-wifi-diag.sh
dmesg | grep -i -E 'bcmdhd|brcmfmac|dhd|4375|sdio|wlan'
journalctl -b -u NetworkManager --no-pager | tail -100
python3 tools/s10plus/a33/tests/test-wifi-diag.py ; nuxel-wifi-diag.sh selftest
```
Evidence log: `/var/log/nuxel/wifi-diag.log`.

**PASS.** Steps 2–7 all hold and both evidence logs + the NM journal excerpt are attached.

**FAIL.** Any of: no `ASSOCIATED`, no IPv4, no DNS resolution, no page load, or a link that drops while
idle. Record the exact verdict string from `nuxelctl wifi status`.

**Current automatic evidence.** `nuxel-wifi-diag.sh selftest` → 5/5 fixtures PASS;
`test-wifi-diag.py` → all checks PASS. Live radio unknown by design —
`configs/nuxel/capabilities/connectivity-time-audio-buttons.json` holds
`wifi.radio.association = BLOCKED_FIRMWARE` until an association is observed.

---

## Area 5 — Timekeeping: time, RTC and timesync

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes**
(one ordinary reboot).

**Feature.** The PMIC RTC read/write path, the timesync backend (systemd-timesyncd preferred, chrony
fallback), the periodic evidence-only verifier (`nuxel-rtc-check.timer`), and `nuxelctl time status |
verify | rtc | mark | compare | sync | set`.

**Why.** An unset clock breaks TLS, breaks NTP, makes every log line useless and turns the status-bar
clock into decoration. RTC persistence is the only thing that keeps the clock sane on a network-less
boot.

**Exact preparation.**
1. Normal boot, screen unlocked, console access.
2. Note the time from a **second device** (watch or another phone) — the independent reference.
3. `nuxelctl time status` → record the verdict line. If it is `RTC_ABSENT`, stop: the RTC driver is not
   bound and persistence cannot pass; that is a kernel-side finding, not a retry.

**Exact action.**
a. Backend sanity: `nuxelctl time verify` — every line PASS except `NEEDS_OWNER_TEST RTC persistence`.
b. Clock correctness: `nuxelctl time sync`; `nuxelctl time rtc`; then confirm the status-bar clock
   matches (`nuxelctl time status` → `launcher_agrees=yes`).
c. **Persistence:** `nuxelctl time mark`; perform **exactly ONE** ordinary reboot that returns to
   Nuxel; `nuxelctl time compare`. Do not repeat the reboot if the compare fails.
d. Independent cross-check: compare the launcher clock with the reference (difference < 1 min);
   `journalctl -b -n 5 --no-pager` (timestamps near "now"); after 30 idle minutes `nuxelctl time verify`
   should show a fresh block appended to `/var/log/nuxel/time.log`.

**Expected result.** `nuxelctl time verify` → `summary: pass=6 fail=0` (persistence reads
`NEEDS_OWNER_TEST` until (c)); `compare` → `PASS rtc_epoch advanced by Xs, wall clock by Ys`; launcher,
system and reference agree within a minute; the timer appends a block every ~30 min.

**Failure symptoms.** `RTC_ABSENT` = no RTC driver (offline work). `NO_TIMESYNC_BACKEND` = no daemon
active. `CLOCK_NOT_SET` = epoch 1970 (RTC unreadable or `CONFIG_RTC_HCTOSYS` off). `compare` FAIL with a
positive RTC error = the RTC lost time or `systohc` never ran. `compare` reports `same boot_id` = no
reboot happened; the pair proves nothing. `journald_agrees=NO` = journald frozen/stale.
`launcher_agrees=UNKNOWN` = bridge unreachable; state that, never assume fine.

**Diagnostic command / log path.**
```sh
nuxelctl time status|verify|rtc|mark|compare    # tools/s10plus/a33/nuxel-time.sh
cat /var/log/nuxel/time.log
cat /var/lib/nuxel/time/rtc-before.json /var/lib/nuxel/time/rtc-after.json
nuxelctl time rtc                                # reads /boot/config-$(uname -r)
python3 tools/s10plus/a33/tests/test-time-rtc.py
```

**PASS.** Parts (a)–(d) hold: `verify` shows `fail=0`, `compare` returns PASS with the numbers quoted,
the independent reference agrees within a minute, and the timer keeps appending evidence.

**FAIL.** Any FAIL line from `verify`; a FAIL/UNKNOWN `compare`; a launcher clock outside tolerance; a
missing timer entry. Quote the exact `compare` line.

**Current automatic evidence.** `nuxelctl time selftest` → 5/5 fixtures PASS (`RTC_ABSENT`,
`NO_TIMESYNC_BACKEND`, `CLOCK_NOT_SET`, `PARTIAL_EVIDENCE`, `CLOCK_OK_UNVERIFIED_PERSISTENCE`);
`test-time-rtc.py` → all checks PASS including the same-boot-id refusal. On-device RTC persistence is
**not** claimed; the capability slice holds `time.rtc.persistence_across_reboot = NEEDS_OWNER_TEST`.

---

## Area 6 — Audio and microphone: speaker path (beyond-madera / CS47L93 / CS35L40 / ABox, low volume only)

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes.**

**Feature.** The real speaker playback path and its bring-up tooling: UCM2 master profile for
`beyond-madera` (`configs/alsa-ucm/beyond-madera/{HiFi,VoiceCall,beyond-madera}.conf`); PipeWire +
WirePlumber device policy (`configs/pipewire/*`, `configs/wireplumber/*`); the ALSA-layer low-volume
safety cap (`configs/pipewire/asound-nuxel-safe.conf`, softvol `max_dB = -6.0`); and the pipeline walker
`tools/s10plus/a33/nuxel-audio-diag.sh` (`status`, `pipeline`, `controls`, `capture`, `ucm-install`,
`tone`, `safe-volume`, `selftest`).

**Why.** The amplifier path here is large and device-specific, and a first bring-up at full scale is a
real hazard (to the speaker and your ear). The default is **low-volume-only**, enforced at the ALSA
layer where a session restore cannot defeat it. **Hard rule:** a *writable mixer control is not an
acceptance criterion* — writability is a register property, audibility is a speaker-and-ear property.
The **microphone** half of this area is unproven on hardware; the Recorder app reports "mic provisioning
only" rather than faking a capture.

**Device truth.** ALSA card **`beyond-madera`** = Cirrus Logic CS47L93 (MADERA) + 2× CS35L40 smart amps in
the Exynos 9820 ABox. A config that names any other card is wrong for this device; Pixel documents were
not applied.

**Exact preparation.**
1. Normal boot, screen unlocked, console access.
2. Quiet room, phone at arm's length, volume low. Nothing here should ever be driven loud; if it is,
   stop and treat that as a safety finding.
3. Zero-cost snapshot: `nuxelctl audio status`, `nuxelctl audio status --json`, `nuxelctl audio cards`.
   If the verdict is `NO_CARD`, `BLOCKED_FIRMWARE` or `NO_PCM`, **stop** — offline bring-up work, never
   a louder retry. `NO_CONTROLS` = no mixer reader installed; `DAC_NOT_RUNNING` = a stream never left
   `SETUP`.

**Exact action.**
a. Walk the pipeline: `nuxelctl audio pipeline`; `nuxelctl audio controls`.
b. Generate the concrete UCM route from what the card **actually** exposes (nothing hand-written):
   ```sh
   nuxelctl audio capture         # -> /var/lib/nuxel/audio/controls.{json,raw}, HiFi.conf.generated
   nuxelctl audio ucm-install --yes
   nuxelctl audio pipeline        # re-walk; the route stage must now be OK
   ```
c. Render the bounded **low-volume** tone and let the tool decide whether the DAC/ABox actually ran:
   `nuxelctl audio tone 800 --yes` (8 % of range, bounded to 800 ms, cap 25 %). Then **listen**.
d. Re-run the tone while watching `nuxelctl audio pipeline` in another shell; the PCM must be
   `state=RUNNING` **while** the tone plays.
e. Cap check: `nuxelctl audio safe-volume` prints the ceiling; `nuxelctl audio safe-volume 90` must be
   **REFUSED**.
f. Save: `nuxelctl audio pipeline --json > /tmp/audio-after.json` and the kernel/session excerpt.

**Expected result.** The pipeline walks all six stages ending `OK_DAC_RUNNING` with
`first_broken_stage=none`; the tone is **quiet** (≈8 %, never full scale) and reports `DECISION: the
DAC/ABox ran`; `safe-volume 90` is refused with a message naming the cap; **you hear the tone** from the
speaker; afterwards ordinary playback is audible at normal volume without a clipped first moment.

**Failure symptoms.** `NO_CARD` = codec/ABox driver did not bind (offline). `BLOCKED_FIRMWARE` = codec DSP
firmware (`cs47l93-dsp*.wmfw`, `cs35l40-dsp*.wmfw`) missing from `/lib/firmware`. `NO_PCM` = DAI link not
up. `NO_CONTROLS` = no `amixer`/`tinymix`. `DAC_NOT_RUNNING` = the "silent phone" case. Pipeline `OK`
but nothing heard = routing/gain/amp finding — report as unproven audibility, never PASS. Tone very loud
= safety violation (softvol cap missing/bypassed) — stop and fix the cap first. Crackle/clipped first
word = amp re-enable/clocking; capture the PipeWire journal before changing anything.
`BLOCKED_EXTERNAL_RESOURCE` on `tone` = no `aplay`.

**Diagnostic command / log path.**
```sh
nuxelctl audio status|pipeline|controls|capture|ucm-install|tone|safe-volume
cat /var/lib/nuxel/audio/controls.json /var/lib/nuxel/audio/HiFi.conf.generated
cat /var/log/nuxel/audio-diag.log
dmesg | grep -i -E 'asoc|madera|cs35l|abox|dapm'
journalctl -b -u pipewire -u wireplumber --no-pager
python3 tools/s10plus/a33/tests/test-audio-diag.py ; nuxel-audio-diag.sh selftest
```

**PASS.** Pipeline ends `OK_DAC_RUNNING` with `first_broken_stage=none`, the low-volume tone renders with
`state=RUNNING`, **you hear it**, `safe-volume 90` is refused, and the status JSON + journal excerpts are
attached.

**FAIL.** Any `NO_*`/`BLOCKED_*`/`DAC_NOT_RUNNING` verdict; no audible tone despite an OK pipeline
(record as unproven audibility); an uncomfortably loud tone; or a cap that can be exceeded. Quote the
exact `nuxelctl audio pipeline --json` line (`first_broken_stage` names the layer).

**Current automatic evidence.** `nuxel-audio-diag.sh selftest` → 8/8 pipeline fixtures PASS;
`test-audio-diag.py` → all checks PASS (including the "writable controls but silent PCM ⇒
`DAC_NOT_RUNNING`" case and the cap refusal). Audibility is **not** claimed; the capability slice holds
`audio.audibility = NEEDS_OWNER_TEST`.

---

## Area 7 — Headphones and USB-C audio adapters

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes.**

**Feature.** 3.5 mm jack detection from ALSA jack kcontrols (`amixer -c beyond-madera contents`) with
codec pin registers as corroboration; USB-C accessory detection from `/sys/class/typec/port*/data_role`,
a new USB ALSA card and (when present) `lsusb`; a revert-aware route decision driven by
`configs/nuxel/audio/jack-routes.json` (headphones / headset / USB-C UAC / analog accessory / speaker);
the bounded diagnostic `tools/s10plus/a33/nuxel-headphone-diag.sh` (`status`, `jack`, `usbc`, `route`,
`watch`, `tone`).

**Why.** Plugging in headphones must silence the speaker and route playback to the jack; unplugging must
return to the speaker. Getting it wrong is a usability bug *and* a safety bug (a route that stays on the
CS35L40 amp while you expect silence). Control **names are never invented** — they are discovered from
the live card; if no jack control is found the verdict is `UNKNOWN`, never a guess.

**Exact preparation.**
1. Normal boot, screen unlocked, console access.
2. **3.5 mm:** a stereo plug **and** a TRRS headset with a mic (a plain plug exercises `Headphones`, a
   mic headset exercises `Headset`).
3. **USB-C:** a USB-C → 3.5 mm DAC/adapter or USB-C headset (UAC); optionally a passive USB-C → 3.5 mm
   adapter (different detection path).
4. Snapshot: `nuxelctl headphone status` / `--json` / `jack` / `usbc`. If `status` reports
   `jack: UNKNOWN`, stop and record it — do not "listen" to a guess.

**Exact action.**
a. `nuxelctl headphone watch 30` (logged transitions; applies **no** route).
b. **3.5 mm:** plug the stereo plug in → confirm `jack=INSERTED route=Headphones`; then
   `nuxelctl headphone route --yes` and `nuxelctl headphone tone 800 --yes`; listen; unplug → back to
   `route=Speaker`.
c. **TRRS headset:** repeat; the route must be `Headset` (a control named like `Headset Mic Jack` is the
   **microphone**, never the output jack).
d. **USB-C:** unplug the 3.5 mm first, then plug the adapter → `USB-C Headset (UAC)` for a recognised
   accessory, or `UNKNOWN_USBC_ACCESSORY` for a passive analog one (which is refused by design).
e. Save: `nuxelctl headphone status --json > /tmp/hp-after.json` and the journal excerpt.

**Expected result.** `status` transitions `REMOVED → INSERTED` on plug-in and back on removal; the route
is `Headphones`/`Headset`/`Speaker` as appropriate; a recognised USB-C accessory is reported as its own
path; `tone 800 --yes` renders a low-volume bounded tone with the pipeline `state=RUNNING`; **you hear it
through the accessory and the speaker is silent while plugged**; on unplug playback returns to the
speaker.

**Failure symptoms.** `jack: UNKNOWN` even inserted = detection unproven. Route stays `Speaker` but the
tone is heard in the headphones = detection/pin mismatch. Tone heard **and** speaker still playing = a
real routing bug. No tone through the accessory but pipeline `OK_DAC_RUNNING` = adapter/codec-AUX/cable
issue (unproven audibility). USB-C adapter not detected = try the other adapter class; capture `lsusb` +
`nuxelctl headphone usbc`. `BLOCKED_EXTERNAL_RESOURCE` on `route --yes` = no `alsaucm`.
`REFUSED` = unproven/unknown accessory (intended). Headset reported as plain `Headphones` = the mic
control was not seen.

**Diagnostic command / log path.**
```sh
nuxelctl headphone status|jack|usbc|route|watch|tone
cat /etc/nuxel/audio/jack-routes.json /var/lib/nuxel/audio/jack-state.json
cat /var/log/nuxel/audio-diag.log ; cat /proc/asound/card*/codec#*
journalctl -b --no-pager | grep -i -E 'jack|headphone|headset|codec|madera' | tail -60
python3 tools/s10plus/a33/tests/test-headphone-route.py ; nuxel-headphone-diag.sh selftest
```

**PASS.** The route matches what was plugged, you hear the low-volume tone through the accessory, the
speaker is silent, the route reverts to `Speaker` on unplug, and the status JSON + journal are attached.

**FAIL.** Any of: detection stays `UNKNOWN`; no tone heard; the speaker keeps playing with the plug in;
no revert on unplug; the accessory is not detected. Quote the `nuxelctl headphone status --json` `route`
and `rule` fields.

**Current automatic evidence.** `nuxel-headphone-diag.sh selftest` → 7/7 jack/USB-C fixtures PASS;
`test-headphone-route.py` → all checks PASS (route logic, mic-before-jack ordering, refusal of unknown
accessory, revert rule, cap). Audibility **not** claimed; capability slice holds
`audio.headphone_audibility = NEEDS_OWNER_TEST`.

---

## Area 8 — Hardware buttons and screen gestures

**On-device verdict: A32 behaviour `VERIFIED_ON_S10PLUS` (A32 record); the A33 state machine, power menu
and gestures `OFFLINE_TESTED`; gestures on the glass `NEEDS_OWNER_TEST`.** · **Owner action: Yes.**

**Feature.** The single owner of the `gpio_keys` keypad: press classes (single/double/long/very-long), a
real power menu, and three screen gestures (edge-back, swipe-up-home, swipe-up-hold-recents), with node
selection by capability and never by `eventN`.

**Why.** The S10+ keypad is **one** evdev device; if two readers own it, a key press is handled twice.
The touchscreen is opened **read-only and never grabbed**, so libinput/Phoc/the launcher keep every event
they receive and gesture dispatch is strictly additive and idempotent.

**Exact preparation.**
1. Normal boot, screen on. `nuxelctl buttons fsm` shows the spec; `nuxel-button-manager --probe` shows
   the real nodes, their capability bitmaps and the resolved choice.
2. Budget ~15 minutes; a second terminal for `journalctl -f -u nuxel-button-manager`.

**Exact action.**
1. **Power short** → screen off; press again → screen on.
2. **Power long (≈ 2 s)** → the power menu appears; volume moves the highlight; the menu closes itself
   after ~15 s if left alone.
3. **Power long → Restart** → must be **refused** (`MENU_REFUSED … reason=gate-closed-owner-absent` in
   `/var/log/nuxel/buttons.log`). Nothing may reboot.
4. **Power long → Recovery / Download Mode** → refused with `reason=NO_FLASH_INVARIANT`. The phone must
   stay in Linux. **Do not** enter Download Mode or the bootloader by any other means.
5. **Volume ±** → the OSD appears and the mixer follows (`nuxelctl audio status`). A writable control is
   not audibility (area 6).
6. **Bixby single** → Terminal opens; **Bixby double** → voice input; **Bixby long** → nothing (mapped
   to `disabled` by design).
7. **Swipe up** → home; **swipe up and hold** → recents; **edge swipe inward** → back. Each gesture must
   produce exactly **one** action (no double transition).
8. **Power ≥ 8 s** → the menu closes and the reboot class fires; the gate refuses by default and logs
   `REBOOT_REFUSED`. Do **not** enable the gate to "make it work" during the test.

**Expected result.** Display toggles on short power with no second framebuffer owner (`nuxelctl handoff
status`); the menu renders and all five entries behave exactly as their gate says (only Lock screen and
screenshot act; Restart/Power off/Recovery/Download Mode refuse with their reason); volume drives the
real ALSA element with an OSD; Bixby does what its class says; each gesture produces one action; the 8 s
hold is refused by the closed gate.

**Failure symptoms.** No OSD at all ⇒ the manager is not running (`systemctl status
nuxel-button-manager`). `KEY_DEVICE_NOT_FOUND` ⇒ keypad node resolution. `TOUCH_DEVICE_NOT_FOUND` ⇒
gestures will be silently absent. `POWER_DEBOUNCED held=…ms` ⇒ press windows. `REBOOT_REFUSED reason=…` ⇒
the gate working as designed. Double transitions on a swipe ⇒ a second reader is also handling gestures.

**Diagnostic command / log path.**
```sh
nuxelctl buttons fsm | menu | gates
nuxel-button-manager --probe | --menu-dump | --config-check | --capture 10
cat /var/log/nuxel/buttons.log /etc/nuxel/buttons/reboot-gate.json /etc/nuxel/input/buttons.json
python3 tools/s10plus/a33/tests/test-button-fsm.py
bash tools/s10plus/a32/tests/run-tests.sh      # A32 floor, INV-4
tools/beta/regression-guard.sh
```

**PASS.** Every step above behaves as stated and every refusal is logged with its reason; nothing
reboots; no gesture double-fires.

**FAIL.** No OSD, a refused entry acting anyway, a double transition, a gesture that never fires with a
resolved touch device, or any path that reboots without the gate opening. Record the `KEY_DEVICE_*` /
`REBOOT_REFUSED` / `MENU_REFUSED` line verbatim.

**Current automatic evidence.** **A32 record:** POWER short verified live
(`DISPLAY_OFF brightness=0 saved=12800` → `DISPLAY_ON brightness=12800`), volume → element
`Left AMP PCM Gain`, key 703 recognised (EVIOCGBIT) — this is the one `VERIFIED_ON_S10PLUS` button item,
inherited from A32. This cycle: `test-button-fsm.py` all PASS (replay, JSON↔C↔A32 parity, gate, 14 traces);
`run-p3-tests.sh` → `P3-TESTS: ALL PASS`; invariant `INV-4` hard-pinned and green. The **A33** manager has
not run on the handset, so the A33 behaviour and the gestures stay `OFFLINE_TESTED` / `NEEDS_OWNER_TEST`.
(Note: the fragment file `docs/beta-finalization/manual-proof/10-vibration.md` internally labels vibration
"Area 21" and the flashlight fragment "Area 9/22"; the authoritative **area numbers are those in this
document**.)

---

## Area 9 — Flashlight, notification LED and edge lighting

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` (control logic) ·
**Owner action: Yes** (light can only be confirmed by eyes).

**Feature.** `configs/nuxel/leds/leds.json` + `tools/s10plus/a33/nuxel-led-diag.sh`: class enumeration
for `flashlight` (torch/flash) and `notification`, and the truthful `edge_lighting` **display-overlay**
model; an explicit **OFF** (forces `brightness 0` on every class found); a bounded torch
(`flash --yes <ms>`, cap 60 s, forced OFF on exit, `safety.auto_on_boot = false`); and a notification-LED
path that reports absence honestly.

**Why.** A flashlight is a safety feature and an LED is a notification channel that works with the screen
off; both need a truthful state. A writable node is not proof of visible light; a class that is absent
must be labelled `NOT_SUPPORTED_ON_DEVICE`, not faked. **Samsung "Edge lighting" is a display effect on
the curved AMOLED, not a LED** — modelled as `display_overlay` (`hardware_led:false`), not claimed.

**Exact preparation.** Normal boot, screen on, not charger mode; console/Terminal; a dark-ish room;
`nuxel-led-diag.sh status` (+ `--json`). If `flashlight : NOT_SUPPORTED_ON_DEVICE`, record it and **stop**
(kernel/driver layer).

**Exact action.**
1. `nuxel-led-diag.sh off` → every class found reads `brightness 0`.
2. `nuxel-led-diag.sh flash --yes 3000` → the rear flash lights ~3 s then goes **off by itself**; stop if
   the phone gets hot and record FAIL.
3. `nuxel-led-diag.sh flash --yes 999999` → prints `capping … to the policy maximum 60000 ms` (do not wait
   it out; Ctrl-C and re-run `off`).
4. `nuxel-led-diag.sh flash 3000` (no `--yes`) → refuses, lights nothing.
5. `nuxel-led-diag.sh notify red` → lights red 3 s then off, or says `NOT_SUPPORTED_ON_DEVICE` and names
   the display-overlay fallback.
6. Reboot normally and watch the screen and rear flash — **nothing may light at any boot stage**.
7. `status` must report `edge_lighting : NOT_SUPPORTED_ON_DEVICE_AS_LED` and name the `/run/nuxel-wl-fb.cmd`
   dependency.

**Expected result.** `off` clears every node; one bounded torch cycle that ends by itself; cap printed and
enforced; `--yes` required; the notification LED lights for 3 s or is honestly absent; nothing lights at
boot; edge lighting reported as a display effect.

**Failure symptoms.** `NOT_SUPPORTED_ON_DEVICE` = no torch class bound (offline work). Node found but
`writable: (none)` = `PARTIAL`. Torch never turns off = real defect — run `off` immediately and report the
path. Write returns 0 but no light = report FAIL (a write is not light). Notification LED absent =
expected on some units. Anything lighting at boot = a real defect; find the writer with
`grep -rl brightness /etc/systemd /usr/lib/systemd`.

**Diagnostic command / log path.**
```sh
nuxel-led-diag.sh status | flash --yes <ms> | off | notify <colour> | report
cat /var/log/nuxel/led-diag.log ; ls -l /sys/class/leds/
dmesg | grep -i -E 'led|flash|torch|gpio-leds'
python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py ; nuxel-led-diag.sh selftest
```

**PASS.** Steps 1–7 hold: explicit OFF works, one bounded torch cycle ends by itself, the cap is printed
and enforced, `--yes` is required, the notification LED either visibly lights or is honestly absent, and
nothing lights at boot.

**FAIL.** No class bound; a write with no light; a torch that stays on; any boot-time lighting. Record the
class path, the writable file, the value written and the printed cap string.

**Current automatic evidence.** `nuxel-led-diag.sh selftest` → 3/3 fixtures PASS (torch-only /
notification-only / none); `test-led-diag.py` → all checks PASS (`status --json` emits
`"flashlight_verified": false`). Capability slice keeps this `NEEDS_OWNER_TEST` for visible light.

---

## Area 10 — Vibration and haptics

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` (API) · **Owner action: Yes**
(a buzz can only be confirmed by hand).

**Feature.** `configs/nuxel/haptics/haptics.json` + `tools/s10plus/a33/nuxel-haptics-diag.sh`: node
enumeration across `/sys/class/leds/*vib*`, `/sys/class/timed_output/*`, `/sys/class/vibrator/*` (never a
hard-coded path); named patterns (`tap`, `double`, `long`, `buzz_test`, `notify`, `alarm`, `button`,
`gesture`) expanded to ms step sequences; intensity (`light` 30 / `medium` 55 / `strong` 85) with an
honest `intensity_mode=duration` when there is no strength file; one persisted global switch
(`/var/lib/nuxel/haptics/state.json`); a bounded owner test buzz (`buzz --yes <ms>`, cap 1500 ms).

**Why.** Haptics are the only feedback channel that works with the screen off, and the button manager and
notifications both need one honest API. A registered driver is not proof of working hardware and a
writable node is not proof of a felt buzz.

**Exact preparation.** Normal boot, screen on, not charger mode; console/Terminal; then
`nuxel-haptics-diag.sh status` (`--json`) and `nuxel-haptics-diag.sh on`. If it says
`actuator node : NONE`, **stop** — `BLOCKED_KERNEL`, no node bound.

**Exact action.**
1. `nuxel-haptics-diag.sh pattern notify` → prints a ms sequence, buzzes nothing.
2. `nuxel-haptics-diag.sh buzz --yes 120` → hold the phone; you should feel ONE short buzz (~0.12 s).
3. `intensity 30` → `buzz --yes 120` (lighter); `intensity 85` → `buzz --yes 120` (stronger). Note
   whether they differ; if not, that is expected (`intensity_mode=duration`).
4. `buzz --yes 9999` → prints `capping 9999 ms to the policy maximum 1500 ms` and buzzes ≤ 1.5 s.
5. `buzz` (no `--yes`) refuses; `off` then `buzz --yes 120` refuses with `switch is OFF`; then `on`.
6. With the switch OFF, a button action and a test notification must not buzz; with it ON they should.
7. Reboot normally and watch the whole boot — nothing may buzz.

**Expected result.** `status` prints the real actuator node + writable file(s) or an honest
`BLOCKED_KERNEL`; one felt buzz per explicit `buzz --yes`; intensities distinguishable only if a strength
file exists; the 1500 ms cap enforced and printed; refusals work (no `--yes`; switch OFF); no boot buzz.

**Failure symptoms.** `actuator node : NONE` = `BLOCKED_KERNEL`. Node found but `writable files: none` =
`PARTIAL`. `buzz --yes` returns 0 but nothing felt = report FAIL (not PASS) with the node path, write
file and duration. Intensity changes nothing = `intensity_mode=duration`. A boot buzz = a real defect.
A buzz that never stops = run `off` immediately.

**Diagnostic command / log path.**
```sh
nuxel-haptics-diag.sh status | on | off | intensity | pattern | buzz --yes | report
cat /var/log/nuxel/haptics-diag.log
dmesg | grep -i -E 'vibrat|haptic|timed_output|leds'
python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-diag.py ; nuxel-haptics-diag.sh selftest
```

**PASS.** Steps 1–7 hold: exactly one felt buzz per explicit `buzz --yes`, the cap printed and honoured,
refusals working, consumer paths respecting the switch, and no buzz at boot.

**FAIL.** No node bound; a write returns 0 while nothing is felt; any automated/boot buzz. Record the node
path, write file, ms duration and the exact output.

**Current automatic evidence.** `nuxel-haptics-diag.sh selftest` → 2/2 fixtures PASS; `test-haptics-diag.py`
→ all checks PASS (`status --json` emits `"felt_haptics_verified": false`).

---

## Area 11 — Bluetooth

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes**
(pairing needs a peer).

**Feature.** `configs/nuxel/bluetooth/bluetooth.json` (evidence sources, stage order `adapter → rfkill →
module → firmware → service → pairing`), the BlueZ drop-in
`configs/nuxel/bluetooth/main.conf.d/60-nuxel.conf` (`AutoEnable=false`, `ControllerMode=dual`,
`Privacy=device`, no stored credentials), and `tools/s10plus/a33/nuxel-bluetooth-diag.sh`
(`status`, `firmware`, `on`, `off`, bounded `scan`, `report`, `selftest`).

**Why.** A registered module is **not** proof that the radio works, and configuration alone is **not** a
pairing. The diagnostic names the **first failing stage** and never claims more.

**Device truth.** Broadcom **BCM4375** (Wi-Fi 6 + BT 5.0); vendor HCD `bcm4375B1_semco.hcd`. Nothing
powers the adapter at boot.

**Exact preparation.** Normal boot, screen on, not charger mode; a **second device** discoverable and
within a metre; console/Terminal; then `nuxel-bluetooth-diag.sh status` / `--json` / `firmware`.
`BLOCKED_HARDWARE` = no adapter/rfkill/module ⇒ stop. `BLOCKED_FIRMWARE` = deploy the HCD into
`/lib/firmware/brcm` (repository-only; never a flash). `RFKILL_BLOCKED` = `nuxel-bluetooth-diag.sh on`.

**Exact action.**
1. `nuxel-bluetooth-diag.sh firmware` — note which candidate is FOUND (or that none is).
2. `nuxel-bluetooth-diag.sh on` → `status` must show `adapter: present:hci0`, `rfkill: unblocked:…`.
3. Make the peer discoverable.
4. `nuxel-bluetooth-diag.sh scan 15` → the peer's **MAC** must appear; record it.
5. `bluetoothctl pair <MAC>` → `trust` → `connect` → `info` must show `Connected: yes`.
6. Prove the **data path**: play ~10 s of audio to a BT speaker/headset or send one file. A
   connected-but-silent link is a FAIL.
7. `bluetoothctl disconnect <MAC>` then `nuxel-bluetooth-diag.sh off`.
8. Reboot normally and confirm the adapter is **not** auto-powered (only after `on`).

**Expected result.** Healthy stack shows `adapter: present:hci0`, `rfkill: unblocked:…`,
`module: loaded:…`, `firmware: found:…`, verdict `READY_FOR_PAIRING`; the scan lists the peer; pair/trust/
connect succeed; the exercised data path really works; nothing powers the adapter at boot.

**Failure symptoms.** `BLOCKED_HARDWARE` = radio never came up (kernel/driver). `BLOCKED_FIRMWARE` = no
HCD in `/lib/firmware/brcm`. `RFKILL_BLOCKED` = kill switch on. `PARTIAL` = read the per-stage lines.
Empty scan = report unproven, never PASS. `AuthenticationFailed`/`AlreadyExists` = remove the stale link
key once; if it fails the same way three times, change strategy (peer side). Connects but no data =
data-path failure; capture the journal. Adapter powers up at boot = a real defect.

**Diagnostic command / log path.**
```sh
nuxel-bluetooth-diag.sh status | firmware | on | off | scan [secs] | report
cat /var/log/nuxel/bluetooth-diag.log
dmesg | grep -i -E 'bluetooth|hci|btbcm|bcm4375|hci_uart|rfkill'
journalctl -b -u bluetooth --no-pager | tail -100 ; bluetoothctl show ; bluetoothctl devices
python3 tools/s10plus/a33/tests/hw-subsystems/test-bluetooth-diag.py
```

**PASS.** Steps 2–8 hold: adapter enumerated and unblocked, peer found by MAC, pair/trust/connect to
`Connected: yes`, the exercised data path carries real audio/file, and no auto-power at boot.

**FAIL.** No adapter; no HCD; rfkill blocked; peer never appears; pairing fails three ways; link connects
but carries no data. Record the exact verdict and the first failing stage.

**Current automatic evidence.** `nuxel-bluetooth-diag.sh selftest` → 4/4 fixtures PASS; `test-bluetooth-diag.py`
→ all checks PASS (`"pairing_verified": false`).

---

## Area 12 — NFC

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes** (a
physical tag).

**Feature.** `configs/nuxel/nfc/nfc.json` (stage order `controller → firmware → subsystem → stack → tag`)
and `tools/s10plus/a33/nuxel-nfc-diag.sh` (`status`, `firmware`, bounded `read`, `report`, `selftest`).
Device truth: Samsung **sec-nfc (S3FWRN5-family)** at **I2C 0x27** with an embedded SE.

**Why.** NFC is exactly where a vendor kernel most often exposes **nothing usable**; a UID is never
invented. The honest verdict may well be `BLOCKED_KERNEL` or `NOT_SUPPORTED_ON_DEVICE`.

**Exact preparation.** Normal boot, screen on, not charger mode; **any NFC tag** (NTAG213/215/216 or
MIFARE Classic) whose UID you know, **plus a second, different tag**; console/Terminal; then
`nuxel-nfc-diag.sh status` / `--json` / `firmware`. `BLOCKED_KERNEL` (no controller/module) or
`BLOCKED_FIRMWARE` or `BLOCKED_EXTERNAL_RESOURCE` (no `neard`/`nfc-list`) ⇒ stop and record.

**Exact action.** Only continue when the verdict is `READY_FOR_TAG`.
1. `nuxel-nfc-diag.sh read 15` — runs the real client and prints what it reports.
2. Tap **tag #1** flat on the **upper back** near the camera for ~2 s → one tag with a UID.
3. Compare the UID with the tag's known UID (the format `04:A1:B2:C3:D4:E5:F6` is only the format; the
   digits must be *your* tag's).
4. **Cross-check tag #2** → the UID must be **different**.
5. Remove the tag and repeat → no tag must be reported (a phantom read is a failure).
6. Save `nuxel-nfc-diag.sh report` plus the dmesg lines.

**Expected result.** `status` prints each stage's evidence and the first failing stage; with a usable
stack, `read 15` reports exactly one tag per tap with a UID matching the physical tag and a **different**
UID for a different tag; removing the tag yields no tag; a missing stage yields the honest `BLOCKED_*` /
`NOT_SUPPORTED_ON_DEVICE` verdict and **no claimed UID**.

**Failure symptoms.** `controller : absent` → `BLOCKED_KERNEL` (offline driver work; if no supported path,
`NOT_SUPPORTED_ON_DEVICE`). `firmware : missing` → `BLOCKED_FIRMWARE`. `stack : no-stack` →
`BLOCKED_EXTERNAL_RESOURCE`. UID all zeros/constant = not a real read. No tag detected with
`READY_FOR_TAG` = try the documented position, a different tag type, a longer hold; after three same-mode
attempts change strategy. `read` hangs = reduce the timeout.

**Diagnostic command / log path.**
```sh
nuxel-nfc-diag.sh status | firmware | read [secs] | report
cat /var/log/nuxel/nfc-diag.log
dmesg | grep -i -E 'nfc|sec-nfc|s3fwrn5|nci|i2c.*0027' ; ls -l /sys/class/nfc /dev/nfc* 2>/dev/null
systemctl status neard --no-pager
python3 tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py ; nuxel-nfc-diag.sh selftest
```

**PASS.** Steps 1–6 hold: two different physical tags read with two different matching UIDs, and no
phantom read when the tag is removed.

**FAIL.** A missing stage; a UID that does not match the physical tag; a constant/zero UID; a phantom
read. Record the exact verdict, the first failing stage and the two UIDs — never a UID you did not observe.

**Current automatic evidence.** `nuxel-nfc-diag.sh selftest` → 4/4 fixtures PASS; `test-nfc-diag.py` → all
checks PASS (`"tag_read_verified": false`).

---

## Area 13 — GPS / GNSS and OpenStreetMap

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes**
(**outdoors**, clear sky).

**Feature.** `configs/nuxel/gnss/gnss.json` (stage order `device_node → module → firmware → stream →
fix`), the offline-first OSM contract `configs/nuxel/gnss/osm-tiles.json`, and
`tools/s10plus/a33/nuxel-gnss-diag.sh` (`status`, `firmware`, bounded `stream`, bounded `monitor`, `map`,
`report`, `selftest`).

**Why.** Location feeds the map, camera geotagging and time zones, and it is the subsystem most likely to
be *claimed* from a device node that never produced a sentence. A device node is **not** a fix, and **no
coordinate is ever fabricated** — indoors the honest answer is `NO_FIX`.

**Exact preparation.** Normal boot, screen on, not charger mode; a **clear view of the sky** (outdoors or
a large window; a metal/glass roof makes a fix impossible); console/Terminal that can keep running while
you hold the phone; optionally offline OSM tiles; then `nuxel-gnss-diag.sh status` / `--json` /
`firmware` / `map`.

**Exact action.**
1. Sample the stream (indoors is fine): `nuxel-gnss-diag.sh stream 10` → counts of NMEA sentence types.
2. Outdoors cold start: `nuxel-gnss-diag.sh monitor 300` (or 60 s if warm). It prints a decoded `$..GGA`
   position **only** when a real fix sentence with non-empty lat/lon and fix quality ≥ 1 appears.
3. Record either the decoded coordinate/accuracy/time-to-first-fix **or** `NO_FIX` with how long you
   waited and where you stood. **Indoors it is always `NO_FIX` and that is not a repository failure.**
4. Cross-check on the offline map: open the Maps app with the network **off**; the cached area must
   render (a blank grid without an "offline" message is a map bug, not a GNSS success).
5. Accuracy: pass when the reported accuracy is ≤ 50 m and agrees with the map within that accuracy.
6. Save `nuxel-gnss-diag.sh report` plus the monitor output and dmesg.

**Expected result.** `status` prints each stage's evidence and the first failing stage; `stream` shows
non-zero counts for ≥1 NMEA type; outdoors `monitor 300` eventually prints a decoded position that
matches the offline map within the reported accuracy (≤ 50 m); indoors `monitor` prints `NO_FIX` and no
coordinate; the offline map renders the cached area with the radio off.

**Failure symptoms.** `device_node : absent` → `BLOCKED_KERNEL` (never fabricate a coordinate).
`module : none-loaded` with a node present → `PARTIAL`. `firmware : missing` → `BLOCKED_FIRMWARE`. `stream`
shows zero sentences = no data path. `NO_FIX` outdoors after 300 s = after **three** same-mode attempts
at different locations, change strategy. Fix quality 0 / empty lat-lon = `NO_FIX`, not PASS. Coordinates
jumping wildly = poor sky view or a decode bug. Blank map offline = a Maps regression.

**Diagnostic command / log path.**
```sh
nuxel-gnss-diag.sh status | firmware | stream [secs] | monitor [secs] | map | report
cat /var/log/nuxel/gnss-diag.log
dmesg | grep -i -E 'gnss|gps|nmea|s5p_gnss' ; ls -l /dev/gnss* 2>/dev/null
python3 tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py ; nuxel-gnss-diag.sh selftest
```

**PASS.** Steps 1–6 hold: a real NMEA stream, a decoded position with fix quality ≥ 1 and accuracy
≤ 50 m agreeing with the offline map, with the time-to-first-fix recorded.

**FAIL.** A missing stage; zero sentences; `NO_FIX` outdoors after three attempts at different locations;
a coordinate that does not agree with the map. Record the exact verdict, the first failing stage, the raw
sentence and the times — never a coordinate you did not read.

**Current automatic evidence.** `nuxel-gnss-diag.sh selftest` → 4/4 fixtures PASS; `test-gnss-diag.py` →
all checks PASS (`"fix_verified": false`; no fabricated coordinate; offline-map contract enforced).

---

## Area 14 — Remaining sensors (accel, gyro, mag, proximity, light, barometer, …)

**On-device verdict: `NEEDS_OWNER_TEST`** · repository side: `OFFLINE_TESTED` · **Owner action: Yes**
(motion/rotation/covering/altitude can only be physically induced).

**Feature.** `configs/nuxel/sensors/sensors.json` (capability manifest for accelerometer, gyroscope,
magnetometer, proximity, ambient light, barometer, plus optional heart-rate/grip/hall) and
`tools/s10plus/a33/nuxel-sensors-diag.sh` (per-class enumeration across **IIO** `/sys/bus/iio/devices`,
the **input** subsystem `/proc/bus/input/devices` and the **sensor-hub** driver set; `read`; bounded
`watch` ≤ 120 s; `manifest`; `report`).

**Why.** Sensors drive screen rotation, auto-brightness, proximity-during-call and compass heading, and
they are the subsystem most easily "verified" from a driver name. A class is `readable` only when a real
raw channel returns a value; enumeration without a channel is `present-unreadable`; nothing is reported
from a flag. The `expected_on_s10plus` flags are the device's **documented hardware, not observations**
(the A32 hub devices `grip_sensor`/`ssp_context`/`hall`/`certify_hall` are input evidence, not values).

**Exact preparation.** Normal boot, screen on, not charger mode; a console/Terminal so `watch` can run
while you move the phone; a dark corner + a lit area (light), optionally a lift/stairs (barometer) and a
magnet/flip cover (hall). Then `nuxel-sensors-diag.sh status` / `--json` / `manifest`. A class reported
`NOT_SUPPORTED_ON_DEVICE` is a real verdict — record it, do not retry.

**Exact action.** For each class: `read` it, then `watch <class> <secs>` while performing the documented
gesture (printed by `manifest`).
1. **Accelerometer** — `watch accelerometer 20` while tilting left/right/forward/back; values change and
   settle when still.
2. **Gyroscope** — `watch gyroscope 20` while rotating about each axis; rates move and return to ≈0.
3. **Magnetometer** — `read`, then `watch magnetometer 30` while turning through a full circle.
4. **Proximity** — `watch proximity 20` while covering the top of the screen with your hand and removing.
5. **Ambient light** — `watch ambient_light 20` while moving dark → lit; lux rises and falls.
6. **Barometer** — `watch barometer 30` while changing altitude slightly; a perfectly static value is
   **unproven**, not PASS.
7. **Optional classes** (heart-rate/grip/hall) — only if enumerated; follow their gesture, else record
   `NOT_SUPPORTED_ON_DEVICE`.
8. Save `nuxel-sensors-diag.sh report` plus the per-class `watch` output.

**Expected result.** `status` prints every class with its state and evidence source; at least one class
is `readable` when the kernel exposes IIO channels; `watch` prints `samples=N`, first/last values and
`CHANGED` for the moved channel(s) and `unchanged` for untouched ones; `read` prints only real channels;
unexposed classes are honestly `NOT_SUPPORTED_ON_DEVICE`.

**Failure symptoms.** `BLOCKED_KERNEL` = nothing enumerated. `PRESENT_UNREADABLE` = the hub is enumerated
but exposes no raw channel (userspace/driver gap). A class `NOT_SUPPORTED_ON_DEVICE` = no evidence.
`watch` unchanged for every channel = re-run once with a clearer gesture, and after three same-mode
attempts change strategy. Values random = noise/wrong channel mapping. Barometer static = unproven.
`status` disagrees with the launcher's rotation/brightness = report both separately.

**Diagnostic command / log path.**
```sh
nuxel-sensors-diag.sh status | read <class…> | watch <class> <secs> | manifest | report
cat /var/log/nuxel/sensors-diag.log
ls /sys/bus/iio/devices/ ; cat /sys/bus/iio/devices/*/name
sed -n 's/^N: Name="\(.*\)"$/\1/p' /proc/bus/input/devices
dmesg | grep -i -E 'sensor|accel|gyro|magn|prox|illuminance|baro|ssp'
python3 tools/s10plus/a33/tests/hw-subsystems/test-sensors-diag.py ; nuxel-sensors-diag.sh selftest
```

**PASS.** For each class you claim: `status` enumerates it, `read` returns real raw channels, and `watch`
shows the documented gesture changing ≥1 channel with the expected behaviour — with channel names and
first/last values recorded.

**FAIL.** `BLOCKED_KERNEL`; `PRESENT_UNREADABLE` for a class you claim works; a `watch` that never
changes; or a value you did not read. Record the class, evidence source, channel names and first/last
values.

**Current automatic evidence.** `nuxel-sensors-diag.sh selftest` → 3/3 fixtures PASS;
`test-sensors-diag.py` → all checks PASS (`"observed_motion_verified": false`).

---

## Area 15 — Camera and gallery

**On-device verdict: `NEEDS_OWNER_TEST`** (real capture unproven) · repository side: partial —
userland app + inventory `present/partial` · **Owner action: Yes.**
**Source note:** the dedicated build-group fragment `docs/beta-finalization/manual-proof/15-camera.md`
was **not present in the tree at aggregation time** (its owner group was mid-flight). This entry is
therefore synthesized from the in-tree evidence that *does* exist and is marked accordingly.

**Feature.** The Camera app surface (`pwa/nuxel-apps/camera-gallery/`, `index.html` present) and the
Photos/Gallery viewer (`pwa/nuxel-apps/photos/`, `present/full`). Device truth: the S10+ rear camera is a
Samsung module behind the Exynos ISP; there is **no DRM/KMS and no verified V4L2 capture path** in this
beta, and the camera is a class of feature that the repository deliberately does **not** claim.

**Why.** A camera tile that shows a preview photo is not a camera. Where a hardware path is unproven, the
app must say so — the inventory records `org.nuxel.Camera` as `present/partial` with the gap
`gap-camera-capture` ("real capture is unproven on hardware") and `nuxel-camera` as a placeholder with no
`/usr/bin/nuxel-camera` binary, and those two rows are exactly what this area is meant to settle.

**Exact preparation.**
1. Normal boot, screen on, not charger mode; console/Terminal available.
2. Snapshot the honest state first:
   ```sh
   nuxelctl status 2>/dev/null | head
   ls -l /sys/class/video4linux/ /dev/video* 2>/dev/null   # what, if anything, is bound
   dmesg | grep -i -E 'camera|exynos|ispp|sensor|mipi|v4l2' | tail -40
   ```
3. Open **Camera** from the launcher and from the registry URL
   `http://127.0.0.1:8000/pwa/nuxel-apps/camera-gallery/index.html`.

**Exact action.**
1. Tap the Camera tile **and** open the Photos/Gallery app; both must render their real surface (no blank
   frame, no error page).
2. Attempt one capture **only if** the app presents a live viewfinder. If it does not show a live preview,
   do **not** force a capture — record that the capture path is absent and move on.
3. Open the Photos/Gallery app and confirm it browses whatever the camera-gallery storage actually
   contains (a viewer over the real folder, not a mocked list).
4. Record the app's own capability sentence verbatim — a correct app states that capture is unavailable
   rather than showing a fake "captured" image.
5. Save the kernel lines from step 2 and the app screenshot/URL.

**Expected result.** Both apps render real content. If the camera path is unavailable (the expected
result in this beta), the apps say so plainly, the gallery still works over real storage, and the kernel
shows no bound capture device. A **PASS** here is not "a photo was taken"; it is "the surface and the
gallery behave truthfully and a capture, if the path exists, produces a real file".

**Failure symptoms.** Camera tile shows a blank frame or an error page ⇒ serving/registry bug (area 2).
App shows a fake viewfinder or a pre-baked image ⇒ **FAIL** (a cosmetic switch that lies). A capture
"works" but no file appears in the gallery storage ⇒ FAIL. Nothing enumerates under
`/sys/class/video4linux/` ⇒ the capture path is absent (`BLOCKED_HARDWARE`/offline work), which is an
honest result, not a retry.

**Diagnostic command / log path.**
```sh
ls -l /sys/class/video4linux/ /dev/video* 2>/dev/null
dmesg | grep -i -E 'camera|exynos|ispp|sensor|mipi|v4l2' | tail -40
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/pwa/nuxel-apps/camera-gallery/index.html
python3 tools/s10plus/a33/verify-app-inventory.py        # asserts the camera entries are honest
```

**PASS.** Both apps render truthfully; the gallery browses real storage; and either a real capture
produces a real file **or** the app honestly reports that capture is unavailable.

**FAIL.** A blank/error surface; a fabricated preview or capture; a capture with no resulting file; or a
claim of a working camera path that produced nothing.

**Current automatic evidence.** `docs/beta-finalization/apps/APP-INVENTORY.md` lists
`org.nuxel.Camera = present/partial` (gap `gap-camera-capture`, unproven on hardware) and
`nuxel-camera = present/partial` (placeholder, no binary). The core-app DOM run
(`RESULT: PASS=130 FAIL=0 WARN=0`) proves the app surfaces load without console errors offline. **No
capture was attempted and no capture is claimed.**

---

## Area 16 — SIM and mobile data (modem / cellular)

**On-device verdict: `BLOCKED_FIRMWARE` (calls/data) + `NEEDS_OWNER_TEST` (SIM/microSD detection) ·
repository side: `OFFLINE_TESTED` diagnostics · Owner action: Yes (confirm honest reporting).**
**Source note:** the dedicated fragment `docs/beta-finalization/manual-proof/16-sim-mobile-data.md` was
**not present at aggregation time**; this entry is synthesized from in-tree evidence.

**Feature.** Honest enumeration of the cellular and removable-storage path on the S10+:
`configs/nuxel/modem/` policy, the power/capability diagnostics that read `/sys/class/power_supply/*` and
the `rmnet0` interface state, and the dialer/messages/mail apps' on-screen capability sentences. Device
truth: Samsung **Shannon LTE** modem with **no upstream ModemManager plugin**.

**Why.** Cellular is the single most commonly faked feature ("4G" icon with nothing behind it). The
mission forbids it: the repository's modem state is `BLOCKED_FIRMWARE` because no plugin exists, and the
apps and diagnostics must say so on screen. `remote-access.json` forbids remote access over `rmnet0`, and
the firewall config disables `rmnet0`.

**Exact preparation.**
1. Normal boot, screen on, not charger mode.
2. Insert the **SIM** and (separately) a **microSD card** you can identify.
3. Console/Terminal; open a second terminal for `dmesg -w`.

**Exact action.**
1. Insert / remove the SIM with `dmesg -w` running; note the real kernel lines (if any).
2. `nuxel-power-diag.sh status` (boot mode + gauge) and the modem interface state:
   `ip link show rmnet0 2>/dev/null`; `ls /sys/class/net/`.
3. `systemctl status ModemManager --no-pager` and `mmcli -L 2>/dev/null` (if ModemManager is present) —
   record whether a modem object is seen at all.
4. Open the Dialer and Messages apps and read their **capability sentence** — it must spell out that
   calls/SMS are unavailable because there is no modem plugin, and must refuse rather than show a
   "Calling/Connected" state.
5. Insert the microSD and look for a block device / mountable filesystem; record the device name and
   whether the Files app or a mount path exposes it.
6. Record the actual state of every step; do not write "works" for anything you did not see.

**Expected result.** The honest outcome in this beta: the SIM may be detected at the PMIC/GPIO level and
the microSD may enumerate as a block device, but **calls, SMS and mobile data do not work** because the
Shannon modem has no upstream plugin — and both the apps and the diagnostics state that clearly. `rmnet0`
is disabled in the firewall policy. If the microSD mounts, the Files app can browse it.

**Failure symptoms.** The dialer shows "Calling"/"Connected" with no modem ⇒ **FAIL** (fabrication).
A mobile-data icon turns on without an interface ⇒ FAIL. `mmcli -L` lists no modem but the UI claims
service ⇒ FAIL. `BLOCKED_EXTERNAL_RESOURCE` on `mmcli` ⇒ ModemManager absent. microSD not detected ⇒
record it; check `dmesg` and the mmc host, do not claim it works.

**Diagnostic command / log path.**
```sh
dmesg | grep -i -E 'mmc|sdhci|sim|modem|shannon|ss310|rmnet' | tail -60
ip link show ; ls -l /sys/class/net/ ; lsblk 2>/dev/null || cat /proc/partitions
systemctl status ModemManager --no-pager ; mmcli -L 2>/dev/null
nuxel-power-diag.sh status
python3 tools/s10plus/a33/tests/test-phone-apps.py    # asserts the honest capability sentences
```
Evidence: the in-tree app inventory (`docs/beta-finalization/apps/APP-INVENTORY.md`, gap
`gap-modem-plugin`), the firewall config (`configs/nftables/nuxel-firewall-config.json`, `rmnet0`
disabled), `configs/nuxel/security/remote-access.json` (cellular egress forbidden).

**PASS.** Every path reports its **real** state: the apps refuse calls/SMS with the correct reason, the
diagnostics print the actual modem/interface/SIM/microSD findings, and no UI fakes a connection.

**FAIL.** Any UI or diagnostic that shows a connection, a call, a message sent, or mobile data when the
underlying modem object does not exist; or a microSD reported as mounted when it is not.

**Current automatic evidence.** `tools/s10plus/a33/tests/test-phone-apps.py` → `PASS=37 FAIL=0`
(verifies the dialer's capability sentence comes from the probe, spells out the no-modem case, records a
refusal instead of a fake call, and contains no unconditional "Calling/Connected" claim).
`test-phone-apps.py` also proves the messages app has a queued-not-sent state and never claims a sent
SMS. The modem is `BLOCKED_FIRMWARE` (no plugin) in the repo's honest state.

---

## Area 17 — Phone calls and SMS

**On-device verdict: `BLOCKED_FIRMWARE` (modem) — the apps must **report** the gap; `NEEDS_OWNER_TEST` to
confirm that they do · repository side: `OFFLINE_TESTED` · Owner action: Yes (confirm honest UI).**
**Source note:** the fragment `docs/beta-finalization/manual-proof/17-calls-sms.md` was **not present at
aggregation time**; this entry is synthesized from the in-tree app inventory and phone-app test suite.

**Feature.** The native Phone (dialer), Messages and Contacts applications sharing one data layer,
`shell/nuxel-shell/nuxel-phone-data` (contact store, call log, message threads, number normalisation,
vCard import/export, atomic save, corrupt-store recovery, honest capability model), plus the Mail app's
queued-send behaviour.

**Why.** "The dialer opens" is not "a call works", and a message that shows "Sent" when nothing left the
device is the textbook fabrication this mission forbids. On this handset calls/SMS cannot work because the
Samsung **Shannon** modem has no upstream ModemManager plugin — a `BLOCKED_FIRMWARE` condition, not a UI
defect — and the apps must say exactly that.

**Exact preparation.** Normal boot, screen on, not charger mode; console/Terminal; the Contacts data
layer present (a few sample contacts are fine); the second terminal for `journalctl -f`.

**Exact action.**
1. Open **Contacts** — add/browse/edit a contact; the store must persist across an app restart.
2. Open **Phone (dialer)** — type a number; read the capability sentence. Confirm it refuses to place a
   call with a clear reason (no modem plugin) and never enters a "Calling/Connected" state.
3. Open **Messages** — open/create a thread, compose a message. Confirm it shows a **queued** (not
   "sent") state and never fabricates delivery.
4. Open **Mail** — compose a message with no network; confirm it is queued locally and not shown as sent.
5. Note the exact refusal/queue wording for each app.
6. Save the journal excerpt for the dialer/messages attempt.

**Expected result.** Contacts work fully (store + vCard import/export). Dialer and Messages **refuse**
with the correct, specific reason and never fake a call/message state. Mail queues sends and labels them
queued. Nothing claims a sent SMS or a connected call.

**Failure symptoms.** Dialer enters "Calling"/"Connected" with no modem ⇒ **FAIL**. Messages shows "Sent"
⇒ **FAIL**. A call is "placed" but `mmcli`/journal show no modem ⇒ FAIL. Contacts fail to persist ⇒ a
real bug (capture the store path and the write error). `BLOCKED_EXTERNAL_RESOURCE` ⇒ a phone-data
dependency missing.

**Diagnostic command / log path.**
```sh
python3 tools/s10plus/a33/tests/test-phone-apps.py
shell/nuxel-shell/nuxel-phone-data/run-tests.sh
journalctl -b --no-pager | grep -i -E 'dialer|message|modem|shannon|call' | tail -60
systemctl status ModemManager --no-pager ; mmcli -L 2>/dev/null
```
Evidence: `docs/beta-finalization/apps/APP-INVENTORY.md` §4.1 (phone applications) and gap
`gap-modem-plugin`.

**PASS.** Contacts persist; the Dialer and Messages apps refuse with the correct specific reason and never
show a fake call/message state; Mail queues; no fabricated delivery anywhere.

**FAIL.** Any fabricated "Calling/Connected" or "Sent" state; a contact store that loses data; a
dependency that silently fails.

**Current automatic evidence.** `tools/s10plus/a33/tests/test-phone-apps.py` → `PASS=37 FAIL=0`: the
dialer's capability sentence comes from the probe and contains no unconditional "Calling/Connected"
claim; the messages app uses the shared thread model with a queued-not-sent state; mail's transport never
fabricates a connection state. `shell/nuxel-shell/nuxel-phone-data/run-tests.sh` covers the data layer.
Calls/SMS on the handset are `BLOCKED_FIRMWARE` (no upstream modem plugin).

---

## Area 18 — microSD card

**On-device verdict: `NEEDS_OWNER_TEST` · repository side: partial · Owner action: Yes.**
**Source note:** the fragment `docs/beta-finalization/manual-proof/18-microsd.md` was **not present at
aggregation time**; this entry is synthesized from the in-tree storage/Files evidence. The microSD is
covered together with the SIM in area 16 for the modem-adjacent detection; this entry is the
storage-specific test.

**Feature.** Removable-storage handling: the microSD slot on the S10+, enumerating as an mmc block device
(`/dev/mmcblk*` / `/dev/sd*`), mountable and browsable from the Files app while the internal `USERDATA`
ext4 rootfs (discovered at boot) is left untouched.

**Why.** A card slot is easy to claim and easy to get wrong (a card reported as mounted when it is not, or
a mount that corrupts the card). The mission requires the real device name, the real mount, and an honest
report — and the **NO-FLASHING** invariant means no raw-partition writes, ever.

**Exact preparation.**
1. Normal boot, screen on, not charger mode.
2. A microSD card formatted with a filesystem Linux can mount (ext4 or exFAT-with-support) that you can
   identify; a second terminal for `dmesg -w`.
3. Confirm the internal rootfs is the discovered `USERDATA` (do not touch any block device with `dd`).

**Exact action.**
1. With `dmesg -w` running, insert the microSD; note the real kernel lines and the device name.
2. `lsblk` (or `/proc/partitions`) — note the new block device.
3. Mount it read-write at a scratch path (e.g. `/mnt/sdcard`) using the normal `mount`, **never** a raw
   write:
   ```sh
   sudo mkdir -p /mnt/sdcard && sudo mount /dev/<the-card> /mnt/sdcard
   ls -la /mnt/sdcard
   ```
4. Open the **Files** app and browse to the card; create a file, read it back, delete it.
5. Unmount cleanly (`sudo umount /mnt/sdcard`), remove the card, and confirm the device disappears.
6. Record the device name, filesystem, mount result and the Files-app view.

**Expected result.** The card enumerates as a real block device, mounts, is browsable from the Files app
with read/write, and unmounts cleanly. The internal `USERDATA` rootfs is untouched. If the card does not
enumerate, that is an honest `BLOCKED_HARDWARE`/driver finding — record it, do not fake a mount.

**Failure symptoms.** Insert → nothing in `dmesg` ⇒ the slot/driver is not bound (record it). Device
appears but mount fails ⇒ filesystem/permission issue; capture the exact `mount` error. Files app shows
the card but a write fails ⇒ a real bug. Do **not** attempt to format the card or write the partition
table from this test.

**Diagnostic command / log path.**
```sh
dmesg | grep -i -E 'mmc|sdhci|card|exfat|ext4' | tail -60
lsblk 2>/dev/null || cat /proc/partitions
mount | grep -i sdcard ; findmnt /mnt/sdcard 2>/dev/null
```

**PASS.** The card enumerates, mounts, is browsable/read-write from the Files app, and unmounts cleanly;
the internal rootfs is untouched.

**FAIL.** A claimed mount that did not happen; a card not enumerated with the slot present; or any raw
write. Record the device name, filesystem and the exact error.

**Current automatic evidence.** The A32 baseline recorded the internal rootfs as the discovered
`USERDATA` ext4 (A25 record `/dev/sda31`) and the Files app is `present/full` in the inventory. **No
microSD detection result exists in the tree**, so the area is `NEEDS_OWNER_TEST`; the NO-FLASHING
invariant forbids any raw-partition write during this test.

---

## Area 19 — App Store (NuxTore)

**On-device verdict: `NEEDS_OWNER_TEST` · repository side: `OFFLINE_TESTED` (NuXtore `present/full`) ·
Owner action: Yes.**
**Source note:** the fragment `docs/beta-finalization/apps/NUXTORE.md` was **not present at aggregation
time** (its owner group was mid-flight); this entry is synthesized from the in-tree app inventory and the
NuXtore app directory.

**Feature.** NuxTore — the custom Nuxel app store (`pwa/nuxel-apps/nuxtore/`, `index.html` present,
inventory `present/full`), **offline-first** and **with no store submission**: it catalogs apps that are
already in the repository/PWA tree and installs/launches them locally. There is no third-party
publishing channel and no network submission of anything.

**Why.** The store is where a beta most easily lies ("install" that does nothing, or a catalog pointing at
apps that do not exist). NuxTore must resolve every entry against a real app in the tree, show real
install/launch state, and work with no network.

**Exact preparation.** Normal boot, screen on; console/Terminal; the launcher up. Optionally turn the
network **off** to prove offline-first.

**Exact action.**
1. Open **NuXtore** from the launcher (and via
   `http://127.0.0.1:8000/pwa/nuxel-apps/nuxtore/index.html`).
2. Confirm the catalog lists real apps (the ones from `docs/beta-finalization/apps/APP-INVENTORY.md`) and
   that each entry resolves to a real `index.html` in the tree.
3. Use the store's install/launch action on one app (e.g. Notes or Calculator) and confirm it **launches**
   the real app.
4. With the network off, repeat steps 1–2 — the store must still render and work offline.
5. Record any entry that fails to resolve and the exact error the store shows.

**Expected result.** NuXtore renders offline, lists real apps, and its install/launch action opens the
real app. No entry points at a missing surface without saying so. No network submission happens.

**Failure symptoms.** A catalog entry that opens nothing ⇒ a real gap (report the app id). A store that
requires the network to render ⇒ offline-first regression. An "install" that reports success while
nothing changes ⇒ FAIL (fabrication). A tile for an app whose surface is absent (e.g. the Live Console —
see area 23) must be labelled, not silently broken.

**Diagnostic command / log path.**
```sh
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/pwa/nuxel-apps/nuxtore/index.html
python3 tools/s10plus/a33/verify-app-inventory.py     # every inventory entry vs the real tree
python3 tools/s10plus/a33/verify-app-registry.py      # every registry entry resolves to real files
```

**PASS.** NuXtore renders offline, lists only real apps, and its install/launch action opens real apps.

**FAIL.** A store that needs the network; an entry that resolves to nothing; an install that reports
success without effect.

**Current automatic evidence.** `docs/beta-finalization/apps/APP-INVENTORY.md` lists
`org.nuxel.NuXtore = present/full` (owner `bg-07-specialty-apps`). `verify-app-registry.py` and
`verify-app-inventory.py` enforce that registry/inventory entries resolve to real `index.html` files.
NuXtore's own on-device install flow has **not** been exercised, so the area stays `NEEDS_OWNER_TEST`.

---

## Area 20 — Applications: every registered app opens its own real surface

**On-device verdict: `NEEDS_OWNER_TEST` · repository side: `OFFLINE_TESTED` (static) — the DOM runtime
leg (`OFFLINE_RUNTIME_PASSED`) is recorded in the inventory and needs a browser/jsdom that this host did
not have · Owner action: Yes.**

**Source note:** the fragment `docs/beta-finalization/manual-proof/20-applications.md` was **not present
at aggregation time**; this entry is synthesized from `docs/beta-finalization/apps/APP-INVENTORY.md`,
the `pwa/nuxel-apps/` tree, the launcher registry (`pwa/nuxel-common/app-registry.json`,
`registry_version 4`) and the app test suites (`tools/s10plus/a33/tests/test-core-apps.py`,
`test-phone-apps.py`, `verify-app-registry.py`).

**Feature.** The application layer as the owner actually meets it: **24 directories** under
`pwa/nuxel-apps/` (**19** carry an `index.html`), the native shell apps under
`shell/nuxel-shell/{nuxel-dialer,nuxel-messages,nuxel-contacts,nuxel-settings,nuxel-phone-data}`, and the
registry-driven launch path from Nuxel Home (tile → `launch` URL → WebKitGTK document). This area is the
**integration** test of area 19: a store/inventory can claim an app; only opening it proves one exists.

**Why.** The mission's core-app gap matrix exists because *a directory name is not an application and an
icon is not an application*. Three registry entries (`console`, `penguinterface`, `privacy`) are still
**icons only** — no `index.html` — and the launcher must not present a tile that opens nothing without
saying so. Applications that declare a hardware capability they cannot have (camera on a
`BLOCKED_FIRMWARE` path, cellular on a device with no modem plugin) must degrade in the UI, not lie.

**Exact preparation.**
1. Normal boot, screen on, launcher up, console/Terminal available (universal preparation).
2. Optionally turn Wi-Fi **off** so the offline behaviour of the core apps is visible.
3. Keep `journalctl -f` running in a second terminal.

**Exact action.**
1. Open **every tile** in the launcher grid in turn. For each, confirm the app renders **its own**
   surface (title, controls) and that the back/Home gesture returns to the launcher.
2. For each inventoried app, compare against `docs/beta-finalization/apps/APP-INVENTORY.md`: the status
   there must match what you see (`present/full` ⇒ a working surface; `present/partial` ⇒ the missing
   piece stated on screen or in the app; `missing` ⇒ the store must not offer it).
3. Deliberately try the entries that are **not** complete (Live Console, PenguInterface, the privacy
   surface). A tile that opens a blank/white document, a 404 or an unstyled page is a real gap — record
   the app id and the exact error.
4. Turn off the network and repeat step 1 for the core offline apps — Notes, Calculator, Clock, Files,
   Terminal, Settings, Weather, Maps. They must render and work with no network.
5. In one app that owns data (Notes or Files), create an item, close the app, reopen it, and confirm the
   item persisted. Then reboot (area 25) and confirm it persisted again.
6. Open one app that needs hardware that is honestly absent (Camera, Phone, Messages) and confirm it
   **says** the path is unavailable instead of showing a fake success.

**Expected result.** Every registered app opens its own surface; the 19 apps with an `index.html` render;
icons-only entries are labelled, absent from the grid, or open a "not available" surface; the core apps
work with no network; an item created in an app persists across an app restart and a reboot; hardware-
dependent apps report the real limitation. No app opens an empty document.

**Failure symptoms.**
* A tile that opens a **blank/white page** or a 404 ⇒ the registry points at a surface that is absent.
* An app that renders but whose buttons do nothing (an inert mock) ⇒ FAIL.
* An app that shows "Camera ready"/"Call connected"/"Sent" while the underlying path is
  `BLOCKED_FIRMWARE` ⇒ **fabrication**; report it as a defect, not a cosmetic bug.
* Data created in an app lost after an app restart or a reboot ⇒ a persistence defect.
* A core app that needs the network to render ⇒ offline-first regression.

**Diagnostic command / log path.**
```sh
python3 tools/s10plus/a33/verify-app-registry.py            # every registry entry -> real files
python3 tools/s10plus/a33/verify-app-inventory.py           # every inventory claim vs the tree
python3 tools/s10plus/a33/tests/test-core-apps.py           # L1-L3 offline; L4 runtime if jsdom reachable
python3 tools/s10plus/a33/tests/test-phone-apps.py          # dialer/messages/mail honesty
curl -s -o /dev/null -w '%{http_code} %{url_effective}\n' \
  http://127.0.0.1:8000/pwa/nuxel-apps/notes/index.html     # per app, from the served docroot
journalctl -b -p warning --no-pager | tail -50              # JS/engine errors appear here
```
Log paths: the launched app's document is `http://127.0.0.1:8000/pwa/nuxel-apps/<dir>/index.html`;
WebKit messages land in `journalctl -u nuxel-pwa-host`.

**PASS.** Every registered app opens its own real surface; the core apps work offline; app data persists
across restart and reboot; hardware-absent apps state the limitation truthfully and no icons-only entry
is silently presented as a working app.

**FAIL.** Any tile that opens nothing (blank/404/inert), any app that fabricates a hardware success, any
core app that needs the network, or any app-created data lost across a restart/reboot.

**Current automatic evidence.** `pwa/nuxel-apps/` holds **24** app directories; **19** carry an
`index.html` (`_shared` is not an app; `console`, `penguinterface`, `privacy` are icons-only and are
recorded as open gaps owned by `bg-07`/`bg-05`). Re-measured by this briQ on the build host:
`tools/s10plus/a33/tests/test-core-apps.py` → **`RESULT: PASS=86 FAIL=0 WARN=0 verdict=OFFLINE_STATIC_ONLY`**
(the L4 jsdom layer was skipped because no `node_modules` carrying jsdom is reachable on this host; the
inventory's own recorded runtime run is `PASS=130 FAIL=0 WARN=0 verdict=OFFLINE_RUNTIME_PASSED`,
`docs/beta-finalization/apps/APP-INVENTORY.md` line 111), and `test-phone-apps.py` →
**`RESULT: PASS=37 FAIL=0 verdict=OFFLINE_TESTED`**. **Open defect recorded, not hidden:**
`tools/s10plus/a33/verify-app-inventory.py` currently **FAILS** with
`APP-INVENTORY.md: the machine-readable block markers <!-- INVENTORY-DATA:BEGIN --> /
<!-- INVENTORY-DATA:END --> are missing` — the document and its executable form are out of sync at
aggregation time (owner `bg-06-core-phone-apps`; expected to land with that group's final write).
The app surfaces themselves cannot be *seen* by a script, so the area stays `NEEDS_OWNER_TEST`.

---

## Area 21 — VPN and remote access: honestly-labelled privacy

**On-device verdict: `NEEDS_OWNER_TEST` · repository side: `OFFLINE_TESTED` (claim ladder) ·
Owner action: Yes — a real leak test needs an **external vantage point**.**

**Source note:** `docs/beta-finalization/manual-proof/21-vpn-remote.md` and
`docs/beta-finalization/security/VPN-TOR-REMOTE.md` were **not present at aggregation time** (their owner
group `bg-05-security-permissions` was mid-flight; `docs/beta-finalization/security/` was an empty
directory). This entry is synthesized from the real tool in the tree
(`tools/s10plus/a33/nuxel-vpn-tor.sh`), its configs (`configs/nuxel/security/{privacy-config,remote-access}.json`,
`configs/nuxel/security/tor/torrc`) and its live output, quoted below.

**Feature.** VPN, Tor and remote access with a **three-claim truth ladder** per feature:
(1) the *process is running*, (2) the *circuit/tunnel exists*, (3) *traffic actually goes through it*.
Claim 3 is **not observable on the device** — it needs a second network vantage — so it stays
`unproven` even when 1 and 2 are evidenced. Remote access is **off by default**, requires a visible
status indicator, and **refuses a wildcard bind**.

**Why.** This is where a beta most easily lies to its owner: *"tor.service is active"* is not
anonymisation, and *"wg0 exists"* is not a tunnel carrying your traffic. The mission forbids any
cosmetic switch that lies about enforcement, and requires a closed claim vocabulary
(`evidenced` / `unproven` / `unavailable` / `unknown`) that no UI may upgrade.

**Exact preparation.**
1. Normal boot; console/Terminal; network reachable (Wi-Fi per area 4, or USB tether).
2. For a real tunnel: a WireGuard/OpenVPN profile file placed by **path** (private keys are never read
   into output or logs — the tool only checks existence and mode).
3. For the leak test: a **second vantage point** — a different network (a phone hotspot does not count
   for a Tor exit check; use an external host you control, or an honest leak-test service).
4. Keep the console guard in mind: enabling a kill switch delegates to the firewall (area 22), which
   must leave the USB console reachable.

**Exact action.**
1. Read the ladder before changing anything:
   ```sh
   tools/s10plus/a33/nuxel-vpn-tor.sh claims            # all surfaces, human-readable
   tools/s10plus/a33/nuxel-vpn-tor.sh claims --json     # machine-readable
   ```
   Confirm every claim carries a level from the closed vocabulary and that
   `traffic_routed_through_tor` and `traffic_routed_through_vpn` are `unproven` on a fresh boot.
2. Confirm remote access is **off** and its indicator is honest:
   `nuxel-vpn-tor.sh remote status`; then try to enable it with a wildcard bind
   (`remote on --bind 0.0.0.0`) and confirm it is **refused**; enable it bound to the gadget address
   only if you intend to test it, and confirm the on-screen indicator appears.
3. Bring the tunnel up: `nuxel-vpn-tor.sh vpn on --profile <name>`, then
   `vpn status` (claim 1 = process, claim 2 = handshake). For Tor: `tor on`, `tor status`,
   `tor circuits`.
4. **Leak test from the second vantage point** (this is the only thing that can move claim 3):
   from the handset, `curl -s https://<external-host>/ip` and a DNS-resolution check, then compare the
   observed exit address/asn against the VPN exit or the Tor exit list. Record the raw output as the
   evidence for claim 3.
5. Turn everything off (`vpn off`, `tor off`, `remote off`) and re-read `claims` — every level must
   return to its off/unproven state.

**Expected result.** The ladder is honest at every step (claim 3 never upgrades without external
evidence); remote access defaults to off and refuses a wildcard bind; the indicator renders before
remote access is allowed; enabling the kill switch never removes the console guard; secrets stay
path-only. The exit address observed from the external vantage matches the tunnel's exit (claim 3
`evidenced`) — or, if it does not, the tool keeps saying `unproven`/`suspect` and the owner records the
leak.

**Failure symptoms.** A surface that says "private"/"anonymous"/"protected" with claim 3 `unproven` ⇒ a
lying UI (FAIL). A wildcard bind accepted, or remote access enabled with no indicator ⇒ FAIL. A
kill-switch apply that drops the USB console ⇒ stop and roll back (`nuxel-firewall.sh rollback`). Any
output that prints a private key ⇒ security defect. A DNS answer outside the tunnel while claim 3 reads
`evidenced` ⇒ leak; record it and do not update the claim.

**Diagnostic command / log path.**
```sh
tools/s10plus/a33/nuxel-vpn-tor.sh claims --json
tools/s10plus/a33/nuxel-vpn-tor.sh vpn status --json ; nuxel-vpn-tor.sh tor status --json
tools/s10plus/a33/nuxel-vpn-tor.sh tor leak-probe      # device-side suspect list, not a proof
tools/s10plus/a33/nuxel-firewall.sh show               # kill-switch + console-guard state
ss -tunlp ; ip -br addr ; ip route get 1.1.1.1
journalctl -u tor -u wg-quick@<iface> -u sshd-gadget --no-pager | tail -50
```
State/evidence paths: `/var/lib/nuxel/security/*.json`, `/run/nuxel/remote-access.state`,
`/var/lib/nuxel/firewall/*`.

**PASS.** Every claim is honest; remote access is off by default and refuses a wildcard bind; the
indicator is rendered when remote access is on; the console survives every kill-switch apply; and — if
the owner performed the external-vantage test — the observed exit matches the claimed path.

**FAIL.** A privacy claim upgraded without external evidence; remote access on with no indicator; a
wildcard bind accepted; the console lost after a firewall apply; a printed secret.

**Current automatic evidence.** Real output captured by this briQ on the build host
(`nuxel-vpn-tor.sh claims --json`, `2026-10-16T16:40:36Z`, exit 0): the ladder reports
`traffic_routed_through_tor = unproven` ("no device-side evidence is possible: proving that this
device's traffic exits via Tor needs an external vantage point"), `service_running = unavailable`,
`circuits_built = unknown`, `control_port_authenticated = unproven`,
`remote_access_enabled = evidenced` with `default: "off"` and `indicator: "absent"`, and
`killswitch_armed = unknown`; `invalid_claim_levels: []`. **Open defect recorded:** the tool printed a
non-fatal `ValueError: not enough values to unpack (expected 7, got 6)` from an internal helper before
the JSON (its Tor sub-parser), i.e. it degrades honestly but is not clean — owner
`bg-05-security-permissions`. No external-vantage leak test exists anywhere in the tree, so no privacy
claim here is `VERIFIED_ON_S10PLUS`.

---

## Area 22 — Firewall and permissions: what is actually enforced

**On-device verdict: `OFFLINE_TESTED` (49/49) + `NEEDS_OWNER_TEST` for the on-device apply ·
Owner action: Yes — the *ruleset in the kernel* can only be read on the handset.**

**Source note:** `docs/beta-finalization/manual-proof/22-firewall-permissions.md`,
`docs/beta-finalization/security/{FIREWALL,PERMISSIONS,ENFORCEMENT-PROOF,THREAT-MODEL}.md` were **not
present at aggregation time**; `docs/beta-finalization/security/` was empty. This entry is synthesized
from the real tools (`nuxel-firewall.sh`, `verify-permissions.py`, the permission manager and the portal)
and the test suite output quoted below.

**Feature.** (a) The **nftables firewall application**: render → `nft -c -f` check → snapshot → atomic
apply → verify → auto-revert within 60 s unless confirmed, with the **console guard** (`nuxel-console-guard.nft`,
table priority −200) loaded last and re-verified after every apply. (b) The **permission manager**
(`shell/nuxel-shell/nuxel-permissions/`) with per-capability grants and app sandbox profiles
(`shell/nuxel-shell/nuxel-sandbox/profiles/*.json`). (c) The **portal** consent flow (per-app, per-type,
`once`/`session`/`always`, 30 s deny-by-default timeout). (d) The **honest enforcement statement**, made
per attacker-privilege class — with the Linux 4.14 mechanisms that are **absent** named as limitations.

**Why.** Enforcement claims are the easiest thing in a beta to overstate. On this device the available
mechanisms are nftables (with `meta cgroup <classid>` — `socket cgroupv2` matching needs ≥ 5.13 and is
**not** used), cgroups, polkit and filesystem DAC; **Landlock (≥ 5.13), kernel lockdown (≥ 4.17),
BPF-LSM (≥ 5.7) and arm64 CFI/SCS/BTI do not exist on 4.14.253** and must be named as absent rather
than promised by a switch. Root compromise is **out of scope** of every claim here.

**Exact preparation.**
1. Normal boot; console/Terminal; `nft` present on the target (`command -v nft`).
2. Confirm the console is up and you can reach it (this is the recovery path if a ruleset is wrong).
3. Note the current ruleset: `nuxel-firewall.sh show` (this is the rollback baseline).

**Exact action.**
1. Snapshot the live posture and the console verdict:
   ```sh
   tools/s10plus/a33/nuxel-firewall.sh show
   tools/s10plus/a33/nuxel-firewall.sh console-verify
   ```
2. Apply with an automatic rollback window and **watch the console**: 
   ```sh
   tools/s10plus/a33/nuxel-firewall.sh apply --rollback-after 60
   ```
   Then either `nuxel-firewall.sh confirm` (keep it) or let the 60 s window expire and confirm it
   auto-reverts to the snapshot.
3. Prove the console guard survived: `nuxel-firewall.sh console-verify` after the apply, and read the
   real ruleset (`nft list ruleset`) to see the guard table still present.
4. Exercise the permission manager: read an app's capability list, **remove** a grant, then open that app
   and confirm the capability is **refused** (not silently allowed). Re-add it and confirm the app can use
   it again.
5. Exercise the portal: trigger a hardware permission (camera/mic) and confirm the consent sheet appears
   with `once`/`session`/`always`; answer nothing and confirm it **denies by default after 30 s**.
6. Read the honest enforcement statement and confirm it is scoped per privilege class: ask for
   `nuxel-security-audit.sh` output and check that an unavailable source prints `unknown` (never a
   plausible default).

**Expected result.** The apply is atomic and reversible; the console guard is present after every apply
and the console never dies; a capability with no grant is refused; the portal is deny-by-default; the
enforcement statement names the 4.14 absences (Landlock, lockdown, BPF-LSM, CFI/SCS/BTI) and scopes each
claim to a non-root attacker. Nothing is called "unbypassable".

**Failure symptoms.** A ruleset applied that removes the console guard, or a console that stops
responding ⇒ stop; `nuxel-firewall.sh rollback` and record it. An app that uses a capability with no
grant ⇒ a permission hole (FAIL). A consent sheet that grants by default, or a timeout that allows ⇒
FAIL. A policy document that claims enforcement the kernel cannot provide (e.g. Landlock on 4.14) ⇒ a
lying claim (FAIL). An audit that prints a *default* value where a source was unreadable ⇒ FAIL.

**Diagnostic command / log path.**
```sh
tools/s10plus/a33/nuxel-firewall.sh show | status | evidence [--out DIR]
tools/s10plus/a33/nuxel-firewall.sh console-verify
nft list ruleset                      # the REAL kernel posture, not a summary
nft -c -f <rendered.ruleset>          # the same check the tool runs before an apply
python3 tools/s10plus/a33/verify-permissions.py repo     # grants vs the real capability set
python3 tools/s10plus/a33/verify-permissions.py device   # on the handset
tools/s10plus/a33/nuxel-security-audit.sh --self-test    # per-privilege-class exposure report
journalctl -u nuxel-firewall -u nuxel-permd -u nuxel-portal --no-pager | tail -60
```
State/evidence paths: `/var/lib/nuxel/firewall/` (snapshots + evidence), `/etc/nuxel/permissions/`.

**PASS.** The apply is atomic and auto-reverts unless confirmed; the console guard is present and the
console survives; grants are enforced (no grant ⇒ refusal); the portal is deny-by-default with a 30 s
timeout; the enforcement statement is per-privilege-class and names the 4.14 absences.

**FAIL.** `nft` apply that drops the console; an unearned enforcement claim; a capability granted without
a grant record; a portal that allows by default; an audit that invents a value for an unreadable source.

**Current automatic evidence.** Re-run by this briQ:
`tools/s10plus/a33/security-tests/test-firewall.sh` → **`== results: 49 passed, 0 failed ==` /
`FIREWALL TESTS PASSED`**, including *"the tool never invokes a flashing tool (command position only)"*
and *"no repository ruleset references a block device"* (the NO-FLASHING invariant is machine-checked
here). `tools/s10plus/a33/verify-permissions.py` (16,554 bytes, 2026-10-16 16:20) provides `repo` and
`device` modes and fails on unsupported capability tokens and on grants that **overstate** enforcement;
`tools/s10plus/a33/nuxel-security-audit.sh` (24,833 bytes) prints `unknown` for an unavailable source.
The **live** ruleset on the handset was **not** read in this run (`BLOCKED_EXTERNAL_RESOURCE` — the
console is byte-silent, see area 23), so on-device enforcement remains `NEEDS_OWNER_TEST`.

---

## Area 23 — Live Console local takeover (console path **and** the on-screen app)

**On-device verdict: the console path is A24/A32-record `VERIFIED_ON_S10PLUS`; this run's live leg is
`BLOCKED_EXTERNAL_RESOURCE`; the PWA surface is `IMPLEMENTED_NOT_DEPLOYED`/absent ·
Owner action: Yes.**

**Source note:** `docs/beta-finalization/apps/LIVE-CONSOLE.md` was **not present at aggregation time**
(owner `bg-07-specialty-apps` mid-flight). This entry is synthesized from the A24 postmortem
(`docs/s10plus-autonomous-boot-repair/A24-POSTMORTEM.md`), the tagged console protocol
(`tools/s10plus/a33/nuxel-console.c`), the host tools (`scripts/s10plus-debug-pack/nuxel-console-host.sh`,
`nuxel-live.sh`), the bridge policy and this run's own live-reachability evidence.

**Feature.** Two distinct things share the name:
1. **The console path (works, proven on hardware).** The USB CDC-ACM gadget ("Nuxel S10+ Live Console")
   carries an interactive **root shell** *and* a live mirror of the target's `/dev/kmsg`. A24 fixed the
   original single-use defect (`tools/s10plus/a24-nuxel-console.c`: ignored-signal shell +
   `trap '' HUP; exec /bin/sh -i` + a supervisor that respawns it after *any* exit). The host side
   (`nuxel-console-host.sh`, `nuxel-live.sh`) enumerates the port **by capability** (VID/PID + TTY
   base/suffix + serial — never a hard-coded node), holds an exclusive `flock`, frames every command with
   a unique request id and a target-side SHA-256, reports the real exit status, and survives a cable pull
   with a clean `!! console lost (…)` (exit 4) instead of a traceback.
2. **The Live Console *app* (the on-screen surface).** `pwa/nuxel-apps/console/` currently holds only
   `css/`, `js/`, `icons/`, `tests/`, `tools/` — **no `index.html`, no `manifest.json`, no `sw.js`** — so
   the registry serves a tile for a surface that does not exist. The local-takeover *protocol* is
   implemented (`nuxel-console.c`, 62,786 bytes) and `tools/s10plus/a33/tests/test-console-protocol.py`
   (17,801 bytes) exercises it.

**Why.** Local takeover is the owner's escape hatch and the beta's recovery channel: if the launcher is
dead, the console is how it is fixed. It is also the exact place where a **false green** is expensive —
the port can be byte-silent while the gadget enumerates, and a "console works" claim from a *present*
device node would be wrong.

**Exact preparation.**
1. Handset booted into Nuxel **normally** (not charger mode).
2. USB cable to the Mac; **never open `/dev/fb0`** from any process while observing the panel (A21
   measured that a single `fb_release` disables the DECON; the host tools refuse to touch it).
3. A second terminal to watch for the re-enumeration after a cable pull.

**Exact action.**
1. Enumerate by capability:
   ```sh
   scripts/s10plus-debug-pack/nuxel-console-host.sh --list
   ```
   The port node **changes across reboots** — the tool must find it, so do **not** assume a node name.
2. Open a session and run a bounded command:
   ```sh
   scripts/s10plus-debug-pack/nuxel-console-host.sh --run 'id; systemctl --failed; free -m'
   ```
   Confirm the framed answer carries the target-side SHA-256 and the **real** exit status.
3. Kill the foreground job with Ctrl-C and confirm the shell is not wedged (the next command answers).
4. **Cable-pull test:** start `nuxel-live.sh --run 'sleep 30; echo hi'`, pull the cable mid-command, and
   confirm a clean `!! console lost (…)` report with exit 4 — **never** a Python traceback — then
   `--wait-reconnect 60` and confirm the gadget re-enumerates and the same command retries once.
5. Confirm the shell **respawns** after exit (A24 behaviour): leave the interactive shell, reconnect, and
   confirm a new shell is serving the port.
6. Only then attempt the **on-screen** Live Console app from the launcher, if a surface exists in your
   build. If the tile opens nothing, that is the recorded gap below — do not paper over it.

**Expected result.** The console is found by capability, answers bounded commands with framed + SHA-
verified output and the real exit status, survives a cable pull cleanly and reconnects by itself, and the
shell respawns after any exit. The on-screen Live Console app either delivers a real local-console
surface or is honestly labelled as not available.

**Failure symptoms.** No `/dev/cu.usbmodem*` at all ⇒ the gadget is not enumerating (a Nuxel-side or
cable side issue). A node that exists but is **byte-silent** (`bytes_in=0`, no echo) ⇒ the on-device
console responder is not serving the port — this is exactly what this run measured; do **not** call that
"console OK". A traceback on cable pull, a wedged port after Ctrl-C, a command whose output belongs to
another request (framing bug), or a shell that does not respawn ⇒ FAIL. A Live Console tile that opens a
blank document ⇒ the recorded gap; report it, do not promote it.

**Diagnostic command / log path.**
```sh
scripts/s10plus-debug-pack/nuxel-console-host.sh --list | --run '<cmd>' | --accept | --watch
scripts/s10plus-debug-pack/nuxel-live.sh --run '<cmd>' --timeout 45
python3 tools/beta/live/nuxel-live-reachability.py --json   # capability + byte-silence verdict
python3 tools/s10plus/a33/tests/test-console-protocol.py    # protocol suite (see defect below)
journalctl -u nuxel-console --no-pager | tail -40
```

> **Linux hosts:** pass the node explicitly (`--dev /dev/ttyACM0`) until the glob-safe discovery revision is in your tree - before it the documented bare form above produced no output at all on Linux (the macOS-only glob made the tool abort before its own diagnostic; pinned `INV-10`).
Evidence path: `docs/beta-finalization/live/evidence/reachability-*/` (`reachability.json`,
`probe-raw.txt`, `SHA256SUMS`).

**PASS.** The port is found by capability; a bounded command returns framed, SHA-verified output with the
real exit code; a cable pull yields a clean report and a working reconnect; the shell respawns; the
on-screen console surface (if present) works locally with no network.

**FAIL.** Byte-silent port treated as success; a traceback instead of a clean link-loss report; a wedged
port; a shell that does not respawn; a console app tile that opens nothing.

**Current automatic evidence.** The **console path** is A24/A32-record `VERIFIED_ON_S10PLUS`: the A24
postmortem records the shell respawn supervisor and the kmsg mirror, and the A32 record pins the console
binary (`tools/s10plus/a24-nuxel-console.c`
`d5d4c65c0605f88e8769a1e04d00795e27048899d493dee212f97e7134ad6dd1`, hard pin `INV-5`). **This run** did
**not** re-measure it: `docs/beta-finalization/live/evidence/reachability-20261016/reachability.json`
→ **`"verdict": "BLOCKED_EXTERNAL_RESOURCE"`** — the gadget *did* enumerate (`/dev/cu.usbmodem201`,
`pid 0x4ee7` → 20199, `serial NUXEL-S10PLUS-0001`, matched `vid+pid+ttybase+serial`), but the port was
**byte-silent** (`probe.bytes_in = 0` over `11.38 s`, `echo_ok = false`; the dial-in node
`/dev/tty.usbmodem201` returned `Resource busy`; a 4 KiB burst write failed with `Resource temporarily
unavailable`), and `adb devices` was empty. **Open defects recorded:** (i) `pwa/nuxel-apps/console` has
**no `index.html`/`manifest.json`** — `IMPLEMENTED_NOT_DEPLOYED` (owner `bg-07`); (ii)
`tools/s10plus/a33/tests/test-console-protocol.py` prints its device-side `PASS` lines and then **aborts**
with `ValueError: flush of closed file` (its `subprocess.communicate()` runs after
`proc.stdin.close()` under Python 3.11), so its **host-side half never runs** — the suite is not green and
the console protocol is not fully offline-verified (owner `bg-07`).

---

## Area 24 — Battery and power management: profiles, the power menu, charging

**On-device verdict: `NEEDS_OWNER_TEST` · repository side: `OFFLINE_TESTED` (control surface) +
`BLOCKED_KERNEL` for the fuel gauge on a host without one · Owner action: Yes — battery drain and the
feel of a profile cannot be measured without the handset and time.**

**Source note:** the fragment `docs/beta-finalization/manual-proof/24-battery-power.md` **is present**
(owner `bg-08-hardware-subsystems`) and is the authoritative owner procedure; this entry summarizes it
and adds the repository/tooling evidence measured by this briQ.

**Feature.** (a) The three **power profiles** — **Adaptive / Balanced / Performance** — mapped to a real
`cpufreq` governor and a cgroup CPU weight (`configs/nuxel/power/power.json`). (b) The **power menu**
(long-press POWER): **Lock screen, Restart, Power off, Recovery, Download Mode**, with the flashing
entries **implemented to refuse** (`configs/nuxel/power/power-menu.json`). (c) **Charge control** with
`allow_writes: false` (read-only truth, no register pokes). (d) **Boot-mode detection** — `lpcharge` /
`androidboot.mode=charger` is a *distinct boot mode* that disables `sec_ts` (see area 1 and
`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`). (e) The **reboot/power-off gate**
(`configs/nuxel/buttons/reboot-gate.json`), closed by default because the owner is absent.

**Why.** Battery behaviour is where a beta can quietly destroy trust: a percentage that is invented, a
profile switch that changes nothing, or a power menu whose "Recovery"/"Download Mode" entries actually do
something. The mission requires the last two to be **implemented and offline-tested but never triggered**,
and the fuel-gauge read to be honest about a driver that is not bound.

**Exact preparation.**
1. Normal boot, screen on, **not** charger mode; battery above ~40 %.
2. Console/Terminal; a charger; a watch/clock for the drain window.
3. Note the visible battery percentage from the status bar and the ambient temperature (a phone in the
   sun is not a valid thermal measurement).

**Exact action.**
1. Enumerate the real hardware first — never assume a node:
   ```sh
   tools/s10plus/a33/nuxel-power-diag.sh status      # boot mode, fuel gauge, profile, verdict
   tools/s10plus/a33/nuxel-power-diag.sh menu        # the power-menu table and its refusals
   ```
2. Compare the on-screen percentage against the read fuel gauge
   (`/sys/class/power_supply/*/capacity`). They must agree; a bar without a gauge must be labelled as
   unavailable.
3. Switch profile **Balanced → Performance → Adaptive** and confirm the governor/cgroup actually change
   (`cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`), and that the feel and the drain change.
4. Open the power menu by long-press POWER. Confirm the entries render and that **Recovery** and
   **Download Mode** *refuse* (they must never be triggered). Confirm **Lock screen** locks and
   **Power off**/**Restart** are gated by the reboot policy (area 25) rather than acting immediately.
5. **Drain measurement:** record the gauge, leave the phone idle 30 min at a known brightness, record
   again; repeat for 10 min with the screen on and one app active. Optionally run
   `tools/beta/soak.sh --device --duration 3600` for a bounded, instrumented version.
6. **Charging measurement:** plug the charger; observe the charge rate, the reported charge current and
   the temperature over 10 min; confirm charging rises and the phone does not overheat.
7. Confirm the boot mode stays **normal** throughout (`tr ' ' '\n' < /proc/cmdline | grep
   androidboot.mode` must print nothing). If it ever prints `charger`, the touchscreen does not exist for
   that boot — see area 1.

**Expected result.** The visible percentage matches the real gauge (or is honestly labelled
unavailable); a profile switch changes the governor and is felt; the power menu opens and **refuses** the
Recovery/Download-Mode and (by default) the Restart/Power-off actions; charging raises the gauge with
sane thermals; idle drain is plausible (single-digit %/hour) and the screen-on drain is higher but not
runaway. No battery percentage is ever invented.

**Failure symptoms.** A percentage that does not match the gauge, or a bar with no gauge and no label ⇒
FAIL. A profile switch with no governor change ⇒ a cosmetic switch that lies. A **Recovery/Download-Mode
entry that acts** ⇒ **stop immediately** (NO-FLASHING invariant); this must never happen. A phone that
will not charge, or charges while the temperature climbs without bound ⇒ a hardware/thermal finding.
Idle drain so high that a normal day is impossible ⇒ record it with the numbers.

**Diagnostic command / log path.**
```sh
tools/s10plus/a33/nuxel-power-diag.sh status | menu | profiles
cat /sys/class/power_supply/*/{name,capacity,status,current_now,voltage_now} 2>/dev/null
cat /sys/class/thermal/thermal_zone*/{type,temp} 2>/dev/null
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
tr ' ' '\n' < /proc/cmdline | grep androidboot.mode    # must print nothing on a normal boot
tools/beta/soak.sh --plan                              # the instrumented probe set + criteria
upower -d 2>/dev/null ; journalctl -u nuxel-power-mode --no-pager | tail -40
```
Config paths: `configs/nuxel/power/{power.json,power-menu.json}`, `configs/nuxel/buttons/reboot-gate.json`.

**PASS.** The percentage is real (or labelled unavailable); profiles change the governor and are felt;
the power menu refuses the flashing entries; charging raises the gauge with sane thermals; the boot mode
stays normal.

**FAIL.** An invented percentage; a profile switch with no effect; a Recovery/Download-Mode entry that
acts; charging that does not charge; unbounded temperature.

**Current automatic evidence.** `docs/beta-finalization/manual-proof/24-battery-power.md` is present
(owner `bg-08`). Re-measured by this briQ on the build host: `nuxel-power-diag.sh status` →
```
state: BLOCKED_KERNEL   (no gauge driver bound on this kernel)
battery: no /sys/class/power_supply/*/capacity node — no fuel gauge bound. No battery percentage is invented.
boot mode: unknown — /proc/cmdline unreadable or carries no androidboot.mode
active profile: balanced ; governor(cpu0): unavailable ; cgroup: unavailable
```
— i.e. the tool reports the honest state and refuses to fabricate. The hardware-subsystem suite
(`tools/s10plus/a33/tests/hw-subsystems/run-all.sh`) → **`ALL HARDWARE-SUBSYSTEM OFFLINE SUITES PASS
(OFFLINE_TESTED; owner tests remain NEEDS_OWNER_TEST)`**. The **power menu's Restart/Power-off/Recovery/
Download-Mode actions are closed by default**: `configs/nuxel/buttons/reboot-gate.json` has
`enabled: false`, `allow_restart: false`, `allow_poweroff: false`, `min_interval_s: 1800`,
`max_reboots_per_hour: 1`, `require_rollback_path: true` and an explicit
`refusal_reason` ("gate closed: owner absent and no repository-side reboot policy has authorised a
restart in this cycle"). Real drain, real charging and the *feel* of a profile need the handset ⇒
`NEEDS_OWNER_TEST`.

---

## Area 25 — Reboot persistence: a normal reboot returns to Nuxel, unchanged

**On-device verdict: `NEEDS_OWNER_TEST` · repository side: `OFFLINE_TESTED` (gate + rollback path) ·
live leg `BLOCKED_EXTERNAL_RESOURCE` in this run · Owner action: Yes — one ordinary reboot, performed by
the owner, with the checklist below.**

**Source note:** `docs/beta-finalization/release/REBOOT-ROLLBACK.md` was **not present at aggregation
time** (owner `bg-09-integration-release` mid-flight; `docs/beta-finalization/release/` did not exist).
This entry is synthesized from the in-tree pieces that *do* exist: the reboot gate
(`configs/nuxel/buttons/reboot-gate.json`), the rollback path (`tools/nuxel-rollback-home.sh`, hash-pinned
`INV-6`), the time mark/compare tooling (`nuxelctl time mark|compare`,
`docs/beta-finalization/system/TIME-RTC.md`), the boot-mode guard
(`configs/nuxel/touch/{bootmode-guard.json,nuxel-bootmode-reboot.service}`) and this run's live
reachability evidence.

**Feature.** The owner-visible property that the phone **comes back**: a *normal* reboot returns to Nuxel
with the launcher up, the persisted settings intact (verbose boot, safe zones, the haptics switch, the
power profile), the RTC within tolerance, the same set of systemd units, and a **known-working userspace
rollback path** available throughout. The mission permits ordinary reboots but forbids **blind repeat
reboots**, and requires the console-reconnect and pre/post-reboot checklists to be honoured.

**Why.** Rebooting is the one destructive-looking action the mission still allows, so it is the one most
likely to drop the phone into a state only a flash could fix — and flashing is absolutely forbidden. The
gate is therefore **closed by default** (`enabled: false`) because the owner is absent; it is the owner's
job to open it deliberately, once, with the checks below. A reboot that lands in **charger mode** is not a
brick: the touchscreen is simply absent for that boot (area 1), and a normal reboot returns.

**Exact preparation.**
1. Console/Terminal reachable; a second terminal for the reconnect watch.
2. Confirm the rollback path exists **before** you reboot:
   ```sh
   test -x tools/nuxel-rollback-home.sh && echo ROLLBACK-OK
   ```
3. Record the **pre-reboot baseline** so the post-reboot comparison is real:
   ```sh
   nuxelctl time mark before
   systemctl --failed --no-pager ; cat /run/nuxel-wl-fb.state 2>/dev/null
   systemctl is-active nuxel-pwa-host phoc nuxel-anim-handoff 2>/dev/null
   ```
4. Read the gate and the policy: `cat /etc/nuxel/buttons/reboot-gate.json` and
   `/var/lib/nuxel/reboot/policy.json` if present. If the gate is closed, a restart is **refused** — that
   is correct behaviour for an unattended run; only proceed if *you* (the owner) are present and have
   deliberately authorised it.

**Exact action.**
1. `nuxelctl time mark before`; reboot **once** — via the power menu **Restart** (which the gate must
   honour/refuse honestly) or, from the console, `systemctl reboot`. Never `reboot -f`, never
   `echo b > /proc/sysrq-trigger`.
2. **Reconnect:** let the gadget re-enumerate by itself (it does — measured A26); the host side can wait
   with `nuxel-live.sh --wait-reconnect 60`. Do not pull/replug repeatedly.
3. Post-reboot checks — run each one and record the raw output:
   ```sh
   tr ' ' '\n' < /proc/cmdline | grep androidboot.mode     # MUST print nothing (not charger mode)
   systemctl is-system-running ; systemctl --failed --no-pager
   cat /run/nuxel-wl-fb.state                              # the launcher must own the panel, once
   ```
4. Confirm on the glass: the launcher is up, the wallpaper/status bar/safe areas are as before, touch
   works (area 1), and the verbose-boot log is present if you had enabled it (area 3).
5. Confirm **persisted state** survived: verbose-boot setting, ten-zone safe-area editor values, the
   haptics switch, the power profile, and any app data you created (area 20).
6. Confirm **time persisted**: `nuxelctl time compare before` (RTC within tolerance) and
   `nuxelctl time verify`.
7. Compare `systemctl --failed` with the pre-reboot baseline — it must be **identical or better**.
8. If the launcher is not up, **do not reboot again**: run `bash tools/nuxel-rollback-home.sh` and record
   the outcome. After **three same-mode failures**, stop and change strategy (console instead of the UI,
   a different cable/port, a different measurement) — never loop.

**Expected result.** The phone reboots **once** and returns to Nuxel within a normal boot time
(≈8.3 s on the A32 record); the launcher owns the panel; `systemctl --failed` matches the baseline; the
persisted settings and app data survive; the RTC is within tolerance; the console reconnects by itself;
`/proc/cmdline` carries no `androidboot.mode=charger`. If anything is wrong, the rollback script restores
the known-working PWA kiosk home.

**Failure symptoms.** Boot lands in **charger mode** (`androidboot.mode=charger` printed) ⇒ the
touchscreen is absent for that boot; a **normal** reboot fixes it — this is not a reason to flash
anything. A **dark / no launcher** panel ⇒ run the rollback path, do **not** reboot again. Persisted state
lost (verbose boot, safe zones, haptics, profile, app data) ⇒ a persistence defect; record which key was
lost. RTC wildly wrong ⇒ the RTC path did not persist (area 5). New failed units after a reboot that were
not failed before ⇒ an ordering regression. The gate **allowing** a restart with `enabled:false` ⇒ a gate
defect (record it).

**Diagnostic command / log path.**
```sh
nuxelctl time mark before ; nuxelctl time compare before ; nuxelctl time verify
systemctl is-system-running ; systemctl --failed --no-pager
journalctl -b -1 --no-pager | tail -80 ; journalctl -b --no-pager | tail -80
cat /run/nuxel-wl-fb.state ; systemctl status nuxel-pwa-host phoc --no-pager
tr ' ' '\n' < /proc/cmdline | grep androidboot.mode
bash tools/nuxel-rollback-home.sh              # the known-working rollback path
scripts/s10plus-debug-pack/nuxel-live.sh --wait-reconnect 60 --run 'uptime; systemctl is-system-running'
```

> **Linux hosts:** as above - add `--dev /dev/ttyACM0` to the `nuxel-live.sh` call until the glob-safe discovery revision is in your tree.
Config/pin paths: `configs/nuxel/buttons/reboot-gate.json`, `tools/nuxel-rollback-home.sh`
(`b6288c34e1117edfccaa76bd7d764fbb903108a9dc29ea88e9582c27993c1f24`, hard pin `INV-6`),
`configs/nuxel/touch/nuxel-bootmode-guard.service`, `configs/nuxel/touch/nuxel-bootmode-reboot.service`.

**PASS.** One normal reboot returns to Nuxel with the launcher up, no new failed units, persisted
settings and app data intact, the RTC within tolerance, the console reconnected by itself, no charger
mode, and the rollback path untouched because it was not needed.

**FAIL.** No launcher after the reboot; charger mode after an ordinary restart; lost persisted state; a
new unit failure; a gate that permitted the restart while closed. In all these cases: **use the rollback
path, do not reboot again**, and record the raw evidence.

**Current automatic evidence.** The **A32 record** proves normal boots land in Nuxel
(`systemd[1]: systemd 258.11-1.fc43 … arm64`; 3.910 s kernel + 4.378 s userspace = 8.289 s) and the
rollback path is present and hash-pinned: `tools/nuxel-rollback-home.sh` is a real 310-byte script this
run, sha256 `b6288c34…` (hard pin `INV-6`, re-checked by `tools/beta/regression-guard.sh --json` →
`{"verdict":"PASS","pass":44,"fail":0,"warn":5,"info":2}`). The **reboot gate is closed by default** and
documents exactly why: `enabled:false, allow_restart:false, allow_poweroff:false, min_interval_s:1800,
max_reboots_per_hour:1, require_rollback_path:true, require_clean_journal:true`, with the forbidden
actions listed (`reboot -f (sysrq)`, `echo b > /proc/sysrq-trigger`, any `/dev/block` write, any
bootloader interface). **This run performed no reboot** and could not have verified one: the live console
was **byte-silent** (`docs/beta-finalization/live/evidence/reachability-20261016/reachability.json` →
`BLOCKED_EXTERNAL_RESOURCE`, probe `bytes_in=0`), so the live reboot leg is blocked and
`docs/beta-finalization/release/REBOOT-ROLLBACK.md` did not exist at aggregation time. The owner's single
ordinary reboot is what turns this area into a verdict.

---

## Area 26 — Long-term stability: hours, not minutes

**On-device verdict: `NEEDS_OWNER_TEST` (multi-hour soak; never run on the handset) · harness
`OFFLINE_TESTED` · device soak `BLOCKED_EXTERNAL_RESOURCE` in this run · Owner action: Yes.**

**Source note:** `docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md` and
`docs/beta-finalization/testing/TEST-STRATEGY.md` were **not present at aggregation time** (owner
`bg-09-integration-release` mid-flight). This entry is synthesized from the in-tree harness
(`tools/beta/soak.sh`, `tools/beta/soak_lib.py`, `tools/beta/run-all-tests.sh`) and this run's own
`--selftest` output, quoted below.

**Feature.** The property that the phone is still usable **hours** later: no service restart loop, no
memory or file-descriptor leak, no thermal runaway, no journal flood, no launcher death, no gradual loss
of touch/audio/network. The harness is `tools/beta/soak.sh`: `--plan` prints the probe set and the gated
pass criteria; `--device --duration 28800` runs an 8 h soak **on the handset** (producing
`VERIFIED_ON_S10PLUS` or, honestly, `BLOCKED_EXTERNAL_RESOURCE`); `--vm --duration 1800` is the bounded
VM leg (`VERIFIED_IN_VM_ONLY`); `--replay FILE.ndjson` re-evaluates recorded samples. The harness writes
only under its evidence directory and **never** touches a block device, never reboots, never starts/stops
a phone service.

**Why.** Everything else in this checklist is a snapshot; a beta that survives ten minutes and dies after
three hours has not been tested at all. The mission's own discipline applies hard here: *a green harness
is not a soak*, and no sample may ever be fabricated. The precise failure modes — a unit flapping every
few seconds, an RSS curve that only goes up, a thermal clamp, a journal saturated by one component — are
invisible to a unit test and obvious in a multi-hour record.

**Exact preparation.**
1. Read the criteria **before** starting, so the result cannot be rationalised afterwards:
   ```sh
   tools/beta/soak.sh --plan
   ```
2. Phone on the charger, on a hard surface in the shade (a bedding/sofa soak is a thermal-invalid soak),
   screen brightness fixed and recorded, Wi-Fi on if you want the radio included.
3. Console/Terminal for the sample stream; ~8 h of owner patience (or start with the 1 h smoke if the
   battery/thermals are unknown).
4. Make sure the rollback path is available (area 25) and that nothing in the soak can reboot the phone
   (the harness never does).

**Exact action.**
1. Start the soak with its evidence directory, and **use the phone normally** while it runs (the point is
   a realistic load, not an idle table):
   ```sh
   tools/beta/soak.sh --device --duration 28800 --interval 60 --evidence-dir <dir> --json <report.json>
   ```
   If the live console is not reachable, the harness exits **3** with `BLOCKED_EXTERNAL_RESOURCE` — record
   that as the honest result and fall back to the VM leg (`--vm --duration 1800`) plus a manual
   observation window.
2. During the run, from a second terminal, keep an eye on the obvious failure signals:
   ```sh
   systemctl --failed --no-pager ; systemctl list-units --state=restarting
   free -m ; ls /proc/*/fd 2>/dev/null | wc -l
   journalctl -b --since '-10min' --no-pager | wc -l
   cat /sys/class/thermal/thermal_zone*/temp
   ```
3. At the end, replay the recorded samples for the machine verdict:
   ```sh
   tools/beta/soak.sh --replay <samples.ndjson> --json <report.json>
   ```
4. Confirm the **launcher is still alive and interactive** (area 1/2) at the end of the soak, the RTC is
   still correct (area 5), and the battery percentage is still real (area 24).
5. Record any component that showed a monotonic trend (memory, temperature, fd count) with the numbers —
   a trend is the finding, even if the threshold was not crossed in 8 h.

**Expected result.** The full duration completes with no service restart loop, a stable memory/fd
profile, temperature inside a sane band, no kernel oops, no journal flood, and a launcher that is still
respondent at the end — or the harness reports the honest blocker and the VM/manual leg is used instead.

**Failure symptoms.** A unit in `restarting`/flapping ⇒ an ordering or crash-loop defect (name it).
Monotonically growing RSS or fd count ⇒ a leak; record the slope. Temperature climbing without
stabilising ⇒ a thermal finding (stop the soak; do not cook the phone). A journal that grows without
bound from one component ⇒ a logging defect. A launcher that is dead or unresponsive at the end ⇒ FAIL.
A soak verdict claimed without a samples file ⇒ fabrication (never).

**Diagnostic command / log path.**
```sh
tools/beta/soak.sh --plan | --selftest | --replay <samples.ndjson> [--json <out>]
tools/beta/soak.sh --device --duration 28800 --interval 60     # handset (needs the live console)
tools/beta/soak.sh --vm --duration 1800                        # VM leg (VERIFIED_IN_VM_ONLY)
tools/beta/run-all-tests.sh                                    # the repository-side release gate
journalctl -b --no-pager | tail -200 ; systemctl --failed ; free -m
```
Evidence/report paths: the harness's `--evidence-dir` and `--json` outputs
(`build/reports/**` by default; never `.qq/`, never a QonQrete receipt).

**PASS.** The soak reaches its duration with no restart loop, no leak trend, sane thermals, no oops, no
journal flood, and a responsive launcher — with the samples file as evidence.

**FAIL.** A restart loop; a leak; thermal runaway; a dead launcher; or any soak verdict asserted without
recorded samples.

**Current automatic evidence.** The harness exists (`tools/beta/soak.sh` + `soak_lib.py`, briq-09a) and
its offline self-verification was re-run by this briQ: **7 of 8 checks PASS** —
`plan lists probe set + gated criteria`; `guard refuses .qq evidence dir`; `recorded good series
evaluates PASS`; `recorded reboot series evaluates FAIL (reboot detected)`; `replay writes a report with
terminal state OFFLINE_TESTED`; `unreachable device => exit 3 + BLOCKED_EXTERNAL_RESOURCE`. The eighth
check, `no writes under .qq`, **FAILED** — and the reason is important and honest: the only file carrying
the run-unique stamp `20261016T163833+0200` was
`.qq/runs/20261016-154919-6beeeda9/.codeseeq-home/call-6fa9eaf6-a1/sessions/…/rollout-*.jsonl`, i.e. the
**QonQrete pipeline's own transcript of this briQ's terminal output**, not anything the harness wrote. The
harness itself wrote nothing under `.qq`; the check is conservative and produces a false positive when the
pipeline records the harness's stdout (recorded as an environment artefact, owner `bg-09`). **No device
soak has ever been run** — there is no samples file anywhere in the tree — so long-term stability is
`NEEDS_OWNER_TEST`, and the device leg could not even be attempted this run (console
byte-silent ⇒ `BLOCKED_EXTERNAL_RESOURCE`, see area 23).

---

*End of the 26 areas. Areas 1–19 were compiled from the `manual-proof/` fragments; areas 20–26 were
synthesized from the evidence docs and tools named in their "Source note" fields, because the
corresponding fragments (`apps/LIVE-CONSOLE.md`, `apps/NUXTORE.md`-adjacent material,
`security/*.md`, `release/REBOOT-ROLLBACK.md`, `testing/SOAK-AND-PERFORMANCE.md`) were not present at
aggregation time. Every "Current automatic evidence" field above cites a path or a command that was
actually run; nothing in this document is a human observation, because no human was present.*

---

# UPDATE — LIVE ON-DEVICE PASS (task2.md)

The userspace is now **actually on the phone**. This update tells you what changed for each area and
what still needs your hands. The device is currently on a **normal boot** (not charger/LPM mode) with
the touchscreen registered, so the touch tests below can be attempted.

## What is confirmed by device logs (not by a person)

* Launcher served from `/usr/share/nuxel/pwa/nuxel-home/index.html`, hash `a15be137…` = the repository,
  `HTTP 200`; 25 web apps present and serving (`settings`, `snekbyte`, `clock`, … all `200`).
* `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-touch-arm`, `nuxel-button-manager`, `seatd` all **active**;
  `systemctl --failed` empty.
* Display bridge `/run/nuxel-wl-fb.state` = `FRAMES_OK … owner=nuxel-wl-fb display=on` (one writer).
* Touchscreen: `sec_ts` on IRQ 431; `sec_touchscreen → event2` with `INPUT_PROP_DIRECT`; libinput shim
  `PATH_ASSIGN_SEAT … direct_devices_seen=2`.
* ALSA card 0 `beyond-madera` present. `rpm -qa` = 410 packages. Touch/config/tool files all deployed
  with verified hashes.

## Area 1 — Touchscreen (PRIORITY, still needs you)

**Why:** a registered driver and a mounted event node are proven; a finger is not.

**Preparation:** leave the phone on (do **not** hold Power — an 11 s hold reboots it, and a
USB-attached reboot can come back in charger mode, where the touchscreen does not exist).

**Action:** tap the launcher, open Settings, return Home, open Terminal, scroll the launcher, tap an
app tile, type on the on-screen keyboard.

**PASS:** each action responds. **FAIL:** no response at all (E = pipeline), or wrong coordinates
(E = mapping). **Diagnostic:**
`sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --batch <touch-reads>.txt`
and `journalctl -b -u nuxel-touch-arm --no-pager | tail`.

## Area 2 — Launcher / boot animation

Confirmed live: the served launcher is the deployed revision and the display bridge renders. What still
needs you: that the boot animation hands off cleanly to the launcher and that you see the wallpaper
colour correctly — record what you actually see, including any black frame or ghost frame.

## Area 26 — Long-term stability

`nuxel-postboot.sh` was seen restart-looping `nuxel-ui` on an earlier boot (≥148 iterations). Watch the
phone over an hour: if the UI blanks and returns every ~30 s, that loop is still live — capture
`tail -40 /var/lib/nuxel/bootreport.txt`.

## Newly relevant gap — Timekeeping (area 5)

The device clock is **wrong**: it reads `2026-09-15T00:01Z` while the real date is 2026-10-16. The time
config is deployed but the clock is not synchronised. Until it is fixed, timestamps in logs are wrong.
