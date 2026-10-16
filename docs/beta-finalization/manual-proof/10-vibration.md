# Area 21 — Vibration and haptics (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for the API).
Owner action required? **Yes** — a buzz can only be confirmed by a human hand.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820). The haptic actuator sits behind the PMIC and the *exact node is not
assumed*: `nuxel-haptics-diag.sh status` enumerates `/sys/class/leds/*vib*`,
`/sys/class/timed_output/*` and `/sys/class/vibrator/*` and prints the real path
and the files it may write. **A node existing is not proof that anything is felt.**

---

## 1. Feature

`configs/nuxel/haptics/haptics.json` + `tools/s10plus/a33/nuxel-haptics-diag.sh`:

* node **enumeration** (candidate list + globs, never a hard-coded path);
* named **patterns** (`tap`, `double`, `long`, `buzz_test`, `notify`, `alarm`,
  `button`, `gesture`) expanded to millisecond step sequences;
* **intensity** (`light` 30 / `medium` 55 / `strong` 85) — amplitude when the
  node exposes a strength file, otherwise duration only, reported honestly as
  `intensity_mode=duration`;
* one persisted **global switch** (`/var/lib/nuxel/haptics/state.json`) wired to
  the button manager and notifications: when it is off, *everything* refuses;
* a **bounded owner test buzz** (`buzz --yes <ms>`, capped at 1500 ms);
* the **wiring itself** — `configs/nuxel/haptics/bridge.json` +
  `tools/s10plus/a33/nuxel-haptics-bridge.py` +
  `configs/nuxel/haptics/nuxel-haptics-bridge.service` (session unit). The bridge
  turns a *button action* (`/var/log/nuxel/buttons.log`, line
  `FSM_ACTION source=… action=…`) or a *notification*
  (`/var/lib/nuxel/notifications.json` / `NotificationAdded`) into a named
  pattern and performs it through the **gated programmatic API**
  (`nuxel-haptics-diag.sh api <pattern> --source <consumer>`).

Two surfaces, one switch:

| Surface | Who calls it | Gate |
|---|---|---|
| Owner `buzz --yes <ms>` | a human | none — it *is* the human action |
| Programmatic `api <pattern>` | the bridge (button manager, notifier) | refuses (exit 7) unless `/run/nuxel/haptics/api-enabled` exists — the bridge arms it when a session starts and disarms it on exit |

That gate is what makes *"nothing buzzes during boot"* and *"nothing buzzes with
no user session"* structural rather than a promise. `/run/nuxel-haptics.cmd` is
the request FIFO for press-time haptics and the clock's alarm; it exists only
while the bridge runs, so a writer with no session is a silent no-op.

## 2. Why this matters

Haptics are the only feedback channel that works with the screen off, and the
button manager (bg-03) and the notification daemon both need a single, honest
API. The mission's evidence rule is explicit: a registered driver is not proof of
working hardware and a writable node is not proof of a felt buzz — so the tool
reports the node it found, refuses to buzz without an owner command, and leaves
the felt verdict to the owner.

**Honest integration status.** The button manager (bg-03) is wired for *action*
haptics without any change to it, because it already writes every FSM action to
`/var/log/nuxel/buttons.log` and the bridge consumes that. Press-time (key-down)
haptics need one extra `fifo_send("/run/nuxel-haptics.cmd", "button <action>\n")`
inside the daemon; that file is owned by another in-flight build group, so the
line is **documented in `configs/nuxel/haptics/README.md` and NOT applied here**.
Until it lands, feedback fires on the action, not on the raw press.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode (`nuxel-power-diag.sh status`).
2. Console/SSH or on-device terminal to run the tool.
3. Nothing else needed — no external hardware.
4. Snapshot first:

   ```sh
   nuxel-haptics-diag.sh status          # node, writable files, switch, intensity mode
   nuxel-haptics-diag.sh status --json   # machine-readable
   nuxel-haptics-diag.sh on              # make sure the global switch is ON for the test
   ```

   If `status` says `actuator node : NONE`, **stop** — this is `BLOCKED_KERNEL`:
   no vibrator node is bound on this kernel, and no amount of retrying changes
   that. Record the verdict and move on (it does not gate other areas).
5. Confirm the wiring is live (a session must exist for this to work at all):

   ```sh
   systemctl --user status nuxel-haptics-bridge      # active (running) => gate armed
   nuxel-haptics-diag.sh status | grep programmatic  # "api gate ARMED"
   python3 tools/s10plus/a33/nuxel-haptics-bridge.py --status
   ```

   If the bridge is not running, the gate is closed and **every** programmatic
   request refuses (exit 7) — that is correct behaviour, not a fault.

## 4. Exact action

1. **Control check (no buzz):** `nuxel-haptics-diag.sh pattern notify` must print a
   millisecond sequence (e.g. `20 90 20 90 40`) and must not buzz.
2. **Single tap:** `nuxel-haptics-diag.sh buzz --yes 120` — hold the phone in your
   hand; you should feel ONE short buzz of about 0.12 s.
3. **Pattern feel:** set an intensity and repeat:
   `nuxel-haptics-diag.sh intensity 30` then `buzz --yes 120` (lighter),
   `nuxel-haptics-diag.sh intensity 85` then `buzz --yes 120` (stronger).
   Record whether the two intensities are distinguishable. If they are not, the
   node has no strength control — this is expected and reported as
   `intensity_mode=duration`.
4. **Cap check:** `nuxel-haptics-diag.sh buzz --yes 9999` must print
   `capping 9999 ms to the policy maximum 1500 ms` and buzz for at most 1.5 s.
5. **Refusal check:** `nuxel-haptics-diag.sh buzz` (no `--yes`) must refuse and
   buzz nothing. Then `nuxel-haptics-diag.sh off` followed by
   `nuxel-haptics-diag.sh buzz --yes 120` must refuse with `switch is OFF`.
   Re-enable with `nuxel-haptics-diag.sh on`.
6. **Consumers (the wiring):** confirm the bridge is armed
   (`nuxel-haptics-diag.sh status | grep programmatic` → `ARMED`), then:
   * **Button action** — press a volume key; the bridge maps the logged
     `FSM_ACTION … action=volume-up` to the `button` pattern and you feel a short
     tick. Confirm it in the log: `grep 'emit(buttons)' /var/log/nuxel/haptics-bridge.log`.
   * **Notification** — post one (`nuxel-notifications --test` or any app alert);
     the bridge maps it to the `notify` pattern.
   * **FIFO path** — `printf 'pattern double\n' > /run/nuxel-haptics.cmd` must
     produce exactly one double buzz.
   * **Switch OFF** — `nuxel-haptics-diag.sh off`, then repeat all three: nothing
     may buzz and the bridge log must say `refuse(...): global haptics switch is
     OFF`. Re-enable with `on`.
   * **Panic silence** — `printf 'off\n' > /run/nuxel-haptics.cmd` silences the
     bridge for 30 s without changing the persisted switch.
   * **Closed gate** — `systemctl --user stop nuxel-haptics-bridge`, then
     `nuxel-haptics-diag.sh api tap --source manual-check` must refuse with
     exit 7 (`gated OFF`).
7. **No boot buzz:** reboot normally and watch the whole boot — nothing may buzz
   at any boot stage (there is no boot-time buzz path: the bridge is a session
   unit and the API gate is closed until a session arms it).

## 5. Expected result

* `status` prints the real actuator node and its writable file(s), or an honest
  `BLOCKED_KERNEL` when no node is bound.
* One short, clearly felt buzz on `buzz --yes 120`; distinguishable intensities
  *only* if the node exposes a strength file.
* The 1500 ms cap is enforced and printed.
* `buzz` without `--yes`, and every path while the switch is OFF, refuse.
* No buzz at boot; no automated path buzzes.
* Button and notification events produce exactly one pattern each while the
  switch is ON, and nothing while it is OFF; the API gate refuses (exit 7) when
  the bridge is stopped.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `actuator node : NONE` | No vibrator node bound → `BLOCKED_KERNEL`. Kernel-side work (offline), never a retry loop. |
| Node found, `writable files: none` | Driver bound but exposes no writable file — `PARTIAL`; capture `ls -l <node>` and `dmesg | grep -i -E 'vib|haptic|timed_output'`. |
| `buzz --yes` returns 0 but nothing is felt | Hardware/actuator unobvious: report **FAIL** for felt haptics (not PASS) and keep `NEEDS_OWNER_TEST`-above evidence: node path, write file, duration. |
| Intensity changes nothing | No strength control; `intensity_mode=duration` is the honest answer. |
| Phone buzzes at boot | A real defect: find the writer with `grep -r vibrator /etc/systemd /usr/lib/systemd` and report it; nothing in this subsystem buzzes at boot. |
| Buzz continues indefinitely | Stop it with `nuxel-haptics-diag.sh off` and write `0`/`1` to the node's `activate` file only — never to any other device. |
| Button action produces no feedback | The bridge is not running (`systemctl --user status nuxel-haptics-bridge`), or its log shows `refuse(reason=gate_closed)` / `rate limit`. Press-time (key-down) feedback also needs the one-line daemon change documented in `configs/nuxel/haptics/README.md`. |
| A notification buzzes while the switch is OFF | Real defect: `bridge.json:always_on_off_switch` is not being honoured. Capture the bridge log line and the state file; do not paper over it. |

## 7. Diagnostic command / log path

* `nuxel-haptics-diag.sh status | on | off | intensity | pattern | buzz --yes | report`
  (`tools/s10plus/a33/nuxel-haptics-diag.sh`)
* Evidence log: `/var/log/nuxel/haptics-diag.log`
* Kernel side: `dmesg | grep -i -E 'vibrat|haptic|timed_output|leds'`
* Wiring: `python3 tools/s10plus/a33/nuxel-haptics-bridge.py --status`
  and `--selftest`; log at `/var/log/nuxel/haptics-bridge.log`;
  API audit at `/var/log/nuxel/haptics-api.log`;
  request FIFO `/run/nuxel-haptics.cmd`; API gate `/run/nuxel/haptics/api-enabled`.
* Offline suites: `python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-diag.py`,
  `python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-bridge.py`,
  `python3 tools/s10plus/a33/nuxel-haptics-bridge.py --selftest`, and
  `nuxel-haptics-diag.sh selftest` (2 fixtures: present / absent).

## 8. PASS / FAIL

* **PASS** — steps 1–7 all hold: exactly one felt buzz per explicit `buzz --yes`,
  the cap printed and honoured, refusals working (no `--yes`; switch OFF; gate
  closed), the button and notification consumers respecting the switch, and no
  buzz at boot.
* **FAIL** — no node bound, or a write returns 0 while nothing is felt, or any
  automated/boot buzz occurs. Record the node path, the write file, the
  millisecond duration and the exact output; that is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-haptics-diag.sh selftest` → 2/2 fixtures PASS
  (`fixtures/haptics-present`, `fixtures/haptics-absent`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-diag.py` → all
  checks PASS (enumeration, json contract, refusals, cap, pattern expander,
  switch persistence, fragment completeness).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-bridge.py` → all
  checks PASS (audit-line mapping, gate closed/open matrix, one switch silencing
  every consumer, tool-side rate limit, no-buzz-on-start, skip list, and the
  honesty of this fragment + `configs/nuxel/haptics/README.md`).
* `python3 tools/s10plus/a33/nuxel-haptics-bridge.py --selftest` → all 9 wiring
  checks PASS with no hardware attached.
* Felt haptics: **not claimed** — every `status --json` emits
  `"felt_haptics_verified": false`, the bridge reports
  `emitted/refused` counters only, and the capability manifest keeps this at
  `NEEDS_OWNER_TEST`.
