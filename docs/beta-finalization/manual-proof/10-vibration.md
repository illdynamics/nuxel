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
* a **bounded owner test buzz** (`buzz --yes <ms>`, capped at 1500 ms).

## 2. Why this matters

Haptics are the only feedback channel that works with the screen off, and the
button manager (bg-03) and the notification daemon both need a single, honest
API. The mission's evidence rule is explicit: a registered driver is not proof of
working hardware and a writable node is not proof of a felt buzz — so the tool
reports the node it found, refuses to buzz without an owner command, and leaves
the felt verdict to the owner.

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
6. **Consumers:** with the switch OFF, trigger a button action and a test
   notification; neither must buzz. With it ON, both should.
7. **No boot buzz:** reboot normally and watch the whole boot — nothing may buzz
   at any boot stage (there is no boot-time buzz path).

## 5. Expected result

* `status` prints the real actuator node and its writable file(s), or an honest
  `BLOCKED_KERNEL` when no node is bound.
* One short, clearly felt buzz on `buzz --yes 120`; distinguishable intensities
  *only* if the node exposes a strength file.
* The 1500 ms cap is enforced and printed.
* `buzz` without `--yes`, and every path while the switch is OFF, refuse.
* No buzz at boot; no automated path buzzes.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `actuator node : NONE` | No vibrator node bound → `BLOCKED_KERNEL`. Kernel-side work (offline), never a retry loop. |
| Node found, `writable files: none` | Driver bound but exposes no writable file — `PARTIAL`; capture `ls -l <node>` and `dmesg | grep -i -E 'vib|haptic|timed_output'`. |
| `buzz --yes` returns 0 but nothing is felt | Hardware/actuator unobvious: report **FAIL** for felt haptics (not PASS) and keep `NEEDS_OWNER_TEST`-above evidence: node path, write file, duration. |
| Intensity changes nothing | No strength control; `intensity_mode=duration` is the honest answer. |
| Phone buzzes at boot | A real defect: find the writer with `grep -r vibrator /etc/systemd /usr/lib/systemd` and report it; nothing in this subsystem buzzes at boot. |
| Buzz continues indefinitely | Stop it with `nuxel-haptics-diag.sh off` and write `0`/`1` to the node's `activate` file only — never to any other device. |

## 7. Diagnostic command / log path

* `nuxel-haptics-diag.sh status | on | off | intensity | pattern | buzz --yes | report`
  (`tools/s10plus/a33/nuxel-haptics-diag.sh`)
* Evidence log: `/var/log/nuxel/haptics-diag.log`
* Kernel side: `dmesg | grep -i -E 'vibrat|haptic|timed_output|leds'`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-diag.py`
  and `nuxel-haptics-diag.sh selftest` (2 fixtures: present / absent).

## 8. PASS / FAIL

* **PASS** — steps 1–7 all hold: exactly one felt buzz per explicit `buzz --yes`,
  the cap printed and honoured, refusals working (no `--yes`; switch OFF),
  consumer paths respecting the switch, and no buzz at boot.
* **FAIL** — no node bound, or a write returns 0 while nothing is felt, or any
  automated/boot buzz occurs. Record the node path, the write file, the
  millisecond duration and the exact output; that is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-haptics-diag.sh selftest` → 2/2 fixtures PASS
  (`fixtures/haptics-present`, `fixtures/haptics-absent`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-haptics-diag.py` → all
  checks PASS (enumeration, json contract, refusals, cap, pattern expander,
  switch persistence, fragment completeness).
* Felt haptics: **not claimed** — every `status --json` emits
  `"felt_haptics_verified": false`, and the capability manifest keeps this at
  `NEEDS_OWNER_TEST`.
