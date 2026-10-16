# Area 9/22 — Flashlight, notification LED and edge lighting (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for control logic).
Owner action required? **Yes** — light can only be confirmed by eyes.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820): a dual-LED rear flash driven by the camera/PMIC LED class, a front
notification LED, and a curved AMOLED display. Which **Linux LED classes** are
bound is *enumerated at runtime* and printed by the tool — a class that does not
exist is reported `NOT_SUPPORTED_ON_DEVICE` and is never emulated. **Samsung's
"Edge lighting" is a display effect on the curved AMOLED, not a LED**: this
repository models it as `display_overlay` (`hardware_led: false`) that depends on
the display bridge, and does not claim it as working.

---

## 1. Feature

`configs/nuxel/leds/leds.json` + `tools/s10plus/a33/nuxel-led-diag.sh`:

* **class enumeration** for `flashlight` (torch/flash), `notification`, and the
  truthful `edge_lighting` display-overlay model;
* an **explicit OFF** (`off`) that forces `brightness 0` on every class found;
* a **bounded torch** (`flash --yes <ms>`) with a policy cap (60 s), forced OFF on
  exit, and **no auto-on at boot** (`safety.auto_on_boot = false`);
* a notification-LED path (`notify <colour>`) that reports absence honestly and
  names the display fallback.

## 2. Why this matters

A flashlight is a safety feature and an LED is a notification channel that works
with the screen off; both must have a truthful state. The mission's evidence rule
is explicit: a writable node is not proof of visible light, and a class that is
absent must be labelled, not faked — so the tool prints the real path per class,
labels absent classes `NOT_SUPPORTED_ON_DEVICE`, and leaves the "did you see it"
verdict to the owner.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode.
2. Console/SSH or the on-device terminal.
3. A dark-ish room makes the torch and the notification LED easy to judge.
4. Snapshot first:

   ```sh
   nuxel-led-diag.sh status            # classes found + real paths + current ON/OFF
   nuxel-led-diag.sh status --json     # machine-readable (Settings/launcher)
   ```

   If `flashlight : NOT_SUPPORTED_ON_DEVICE`, record it and **stop** — this is a
   real verdict (kernel/driver layer), not a retry problem. It does not gate any
   other area.

## 4. Exact action

1. **Explicit OFF first:** `nuxel-led-diag.sh off` — every class found must read
   `brightness 0`; the tool prints how many nodes it cleared.
2. **Torch ON, bounded:** `nuxel-led-diag.sh flash --yes 3000` — the rear flash
   must light for about 3 s and then go **off by itself**. Watch the emitter; if
   the phone gets noticeably hot, stop and record FAIL.
3. **Cap check:** `nuxel-led-diag.sh flash --yes 999999` must print
   `capping … to the policy maximum 60000 ms` (do not actually wait it out — the
   point is the printed cap; press Ctrl-C and re-run `off` if needed).
4. **Refusal check:** `nuxel-led-diag.sh flash 3000` (no `--yes`) must refuse and
   light nothing.
5. **Notification LED:** `nuxel-led-diag.sh notify red` — if the class exists the
   LED lights red for 3 s then goes off; if it does not exist the tool says
   `NOT_SUPPORTED_ON_DEVICE` and names the display-overlay fallback. Record which
   happened rather than assuming.
6. **Persistence / no auto-on:** reboot normally and watch the screen and the
   rear flash — **nothing may light at any boot stage**.
7. **Edge lighting (honest check):** confirm `status` reports
   `edge_lighting : NOT_SUPPORTED_ON_DEVICE_AS_LED` and that the display-overlay
   dependency (`/run/nuxel-wl-fb.cmd`) is stated. There is no edge-lighting LED
   to test; if a future build drives the overlay, that is display work (area 9),
   not an LED.

## 5. Expected result

* `off` leaves every class found at `brightness 0`.
* `flash --yes 3000` lights the rear flash once and turns it off by itself; the
  cap is printed and enforced; `flash` without `--yes` refuses.
* `notify red` either lights the front LED for 3 s or returns
  `NOT_SUPPORTED_ON_DEVICE` with the display fallback named.
* Nothing lights at boot; edge lighting is reported as a display effect, not a LED.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `flashlight : NOT_SUPPORTED_ON_DEVICE` | No torch/flash LED class bound → kernel/driver gap. Offline work; not a user error. |
| Node found, `writable: (none)` | Class bound but read-only → `PARTIAL`; capture `ls -l <node>` and `dmesg | grep -i -E 'led|flash|torch'`. |
| Torch lights but never turns off | Real defect. Run `nuxel-led-diag.sh off` immediately and report the path written; never leave the emitter on. |
| Torch write returns 0 but no light | Report **FAIL** for visible behaviour (a write is not light) with the node path and value. |
| Notification LED absent | Expected on some units/kernels: `NOT_SUPPORTED_ON_DEVICE`; the notifier must use the display overlay. |
| Anything lights at boot | A real defect: find the writer (`grep -rl brightness /etc/systemd /usr/lib/systemd`) and report it. |

## 7. Diagnostic command / log path

* `nuxel-led-diag.sh status | flash --yes <ms> | off | notify <colour> | report`
  (`tools/s10plus/a33/nuxel-led-diag.sh`)
* Evidence log: `/var/log/nuxel/led-diag.log`
* Kernel side: `dmesg | grep -i -E 'led|flash|torch|gpio-leds'`;
  `ls -l /sys/class/leds/`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py`
  and `nuxel-led-diag.sh selftest` (3 fixtures: torch only / notification only / none).

## 8. PASS / FAIL

* **PASS** — steps 1–7 all hold: explicit OFF works, one bounded torch cycle that
  ends by itself, the cap printed and enforced, `--yes` required, the
  notification LED either visibly lighting for 3 s or honestly
  `NOT_SUPPORTED_ON_DEVICE`, and nothing lighting at boot.
* **FAIL** — no class bound, or a write that produces no light, or a torch that
  stays on, or any boot-time lighting. Record the exact class path, the writable
  file, the value written and the printed cap string; that is what a repair cycle
  needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-led-diag.sh selftest` → 3/3 fixtures PASS
  (`fixtures/leds-torch`, `leds-notif`, `leds-none`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py` → all checks
  PASS (enumeration, absent-class labelling, explicit OFF, `--yes` gate, cap,
  notify fallback, no flashing surface, fragment completeness).
* Visible light: **not claimed** — `status --json` emits
  `"flashlight_verified": false`, and the capability manifest keeps this at
  `NEEDS_OWNER_TEST`.
