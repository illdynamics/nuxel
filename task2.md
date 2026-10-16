# QONQRETE — NUXEL TASK 2 — "LAND IT ON THE PHONE"

## Apply everything already built to the REAL Samsung Galaxy S10+ · finish `task.md` on-device · produce real phone evidence

**Device:** Samsung Galaxy S10+ — SM-G975F — `beyond2lte` — Exynos 9820 — Fedora 43 ARM64 — kernel 4.14.253 (Samsung vendor)
**Repository / host:** `dextronux` (Linux x86_64, Fedora 43) at `/x/nuxel`
**Live console:** USB CDC-ACM gadget `18d1:4ee7` "Nuxel S10+ Live Console", serial `NUXEL-S10PLUS-0001`, host node `/dev/ttyACM0`
**Repository revision to start from:** `git rev-parse HEAD` in `/x/nuxel` (as of this prompt: `c6c1ad7`, `VERSION` = `v0.5.0-beta-rc1`)

---

# 0. WHY THIS MISSION EXISTS — READ THIS BEFORE ANYTHING ELSE

Task 1 (`task.md`) was executed as a **repository-only** pass. That is a fact, not an opinion, and the repository proves it:

* `docs/beta-finalization/live/evidence/deploy-20261016T164637+0200/deployment.json` says, verbatim:
  * `"apply": false`
  * `"results": []`
  * `"verdict": "IMPLEMENTED_NOT_DEPLOYED"`
  * `"verdict_note": "plan + install scripts generated and guarded; no device write attempted (pass --apply for the live run)"`
  * `"steps": 37`
* The live-phone work-queue records are still open with **no verdict**:
  * `docs/beta-finalization/workqueue/briq-10a-live-reachability-preflight.json` → `"state": "pending"`, `"verdict": null`
  * `docs/beta-finalization/workqueue/briq-10b-live-deploy-userspace.json` → `"state": "pending"`, `"verdict": null`
  * (also present, unstarted: `briq-10c-live-reboot-and-verify`, plus 34 records overall with `verdict: null`)
* Every reachability attempt recorded from the MacBook ended `"verdict": "BLOCKED_EXTERNAL_RESOURCE"` with a **byte-silent port** (`bytes_in: 0`, `"gadget_descriptor_present": false`) — the old host could not reach the handset at all, and the report's Beta verdict is therefore `BETA_CANDIDATE_PENDING_HARDWARE_PROOF`, not an acceptance.
* The staged userspace lives only in the working tree (`pwa/`, `services/`, `configs/`, `tools/s10plus/a33/`, `images/s10plus/packages-manifest.json`, …). None of it was written to the phone.

The owner's report is exactly consistent with this: *"no difference on my phone"*, *"I don't think it even rebooted"*, *"no launcher home I can see"*. Nothing was applied, so nothing could change.

**Two additional root causes found at the start of this task (both verified live — see §3):**

1. The handset is currently booted in **LPM / charger mode** (`androidboot.mode=charger`, `charging_mode=0x3030` in `/proc/cmdline`). Per this repository's own root-cause work (`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`, `briq-01c`), that makes `sec_ts` refuse to initialize, so the touchscreen does not exist at all and `nuxel-touch-arm.service` fails. This is why the phone looks dead-to-the-touch even when the Nuxel stack is running.
2. The deploy manifest `tools/beta/live/deploy-manifest.json` covers only **7 groups / 37 file steps** (launcher PWA, safe zones, session units, animation handoff, touch+buttons, audio/network config, and one deliberately-skipped kernel-adjacent group). The remainder of the built programme — the PWA application suite (`pwa/nuxel-apps/*`), the native shell apps, the `a33` tooling/diagnostics, package installation, Flatpak, permissions/firewall, and the services under `services/*` — **is not in any deploy plan at all**. It therefore cannot have reached the phone even in principle.

**This task is the "on the phone, for real" pass.** Do not re-do repository work that is already finished and tested. Land it. Then finish `task.md`'s device-tier requirements **on the real handset**, with real on-device evidence, and repair the reports so that they describe the phone as it actually is.

---

# 1. ABSOLUTE RULES (carried forward, plus new environment rules)

All of `task.md` §1 remains in force, unchanged and absolute:

**NEVER** flash BOOT / USERDATA / SYSTEM / RECOVERY / DTB / DTBO / VBMETA / radio / modem / anything; never write a raw partition block device; never repartition UFS; never run Heimdall/Odin/any flashing wrapper; never enter Download Mode; never enter TWRP; never touch EFS/SEC_EFS/calibration/IMEI/PIT/partition metadata; never install a new kernel to the phone; never silently change hardware identity; never claim untested hardware works.

Added for this environment:

1. **The console port is a single-owner resource.** Exactly one host tool may hold `/dev/ttyACM0` at a time. Every run through `nuxel-live.sh` / `nuxel_live.py` takes an exclusive `flock`; do not defeat it, do not run two tools in parallel, do not open the port with `screen`/`minicom`/`cat` while a tool is running.
2. **Always use `sudo` for the console.** `/dev/ttyACM0` is `root:dialout 0660`; the interactive user `wicked` is **not** in `dialout`. `sudo -n true` succeeds (passwordless). See §3.4 for the stale-lock quirk.
3. **SELinux is `Enforcing` on this host.** Do not disable it; do not pass `--sandbox_permissions`; do not `setenforce 0`.
4. **Normal OS reboot is authorised** (it is the documented remedy for the charger-mode condition and is required by `task.md` §53). It must always go through `tools/beta/reboot-policy.sh` / `nuxel-live-reboot-verify.py --reboot --reason … --diagnostic …` discipline: pre-flight, saved state, bounded reconnect, one reason, a **different** diagnostic per reboot, 3-reboot budget, and never a blind repeat. Never reboot into recovery or Download Mode. Never `reboot` a phone whose console you have not verified in this session.
5. **Nothing may be written to the phone before a rollback baseline exists** (§7).
6. **One truth, recorded.** Every claim you make about the phone must be backed by a fresh artifact under `docs/beta-finalization/live/evidence/<run-name>/` produced in this task, from this host, with the real device response. Legacy MacBook evidence (`/Users/wicked/x/nuxel/...` paths inside old bundles) is historical input only — never cite it as a current device capture.

---

# 2. MISSION STATEMENT FOR THIS TASK

1. Restore a **validated, non-charger-mode** console session with the handset.
2. Capture a **live baseline** of the phone as it actually is (briq-10a).
3. Protect that baseline (rollback capture) **before** the first write.
4. **Apply** the already-built userspace to the phone — first the 37 guarded steps of the existing manifest, then *extend the manifest* so the rest of what QonQrete built (apps, tools, services, configs, packages) actually lands too.
5. Prove each deployment **on the phone** with the smallest service restart, a health check, and — where the repository says so — the owner's finger.
6. Finish the remaining `task.md` device-tier work **on the handset**: touch, launcher/boot handoff, buttons, audio, time, networking, app inventory, security/permissions posture, hardware-subsystem diagnostics, reboot persistence, soak.
7. Repair the release record so it describes the phone truthfully: work-queue records, the device capability manifest, `docs/beta-finalization/live/BASELINE-CAPTURE.md`, `docs/beta-finalization/live/DEPLOYMENTS.md`, the two mandatory reports, changelog.
8. Commit everything. Leave the phone in a known-good, recoverable state.

---

# 3. THE WORKING ENVIRONMENT (verified at the start of this task — re-verify, do not assume)

## 3.1 Host and toolchain

* Host `dextronux`, Linux 6.17.1-300.fc43.x86_64, SELinux **Enforcing**; repository `/x/nuxel` on the `main` branch; `sudo -n` works passwordless.
* `adb` is installed but **sees no device** (`adb devices -l` → empty). The handset is *not* in adb/fastboot mode and must not be put there.
* Python 3.11, `bash`, `curl` present. All repository tooling under `tools/beta/` and `scripts/s10plus-debug-pack/` is Linux-capable (`nuxel_live.enumerate_console_nodes()` has an explicit Linux `/sys/class/tty/*/device/../idVendor` branch — the Mac-only `ioreg` path is not used here).

## 3.2 The console node

```
$ lsusb | grep -i nuxel          # (descriptor appears as 18d1:4ee7)
$ sudo dmesg | tail -6
usb 2-3: New USB device found, idVendor=18d1, idProduct=4ee7
usb 2-3: Product: Nuxel S10+ Live Console
usb 2-3: Manufacturer: Nuxel
usb 2-3: SerialNumber: NUXEL-S10PLUS-0001
cdc_acm 2-3:1.0: ttyACM0: USB ACM device
```

## 3.3 Verified console access (these exact commands worked, from this host, in this task)

```bash
# reachability preflight (read-only). exit 0 = reachable, 3 = blocked
sudo python3 tools/beta/live/nuxel-live-reachability.py --dev /dev/ttyACM0 --json

# when the primary probe is silent, change the diagnostic before concluding anything
sudo timeout 120 python3 tools/beta/live/nuxel-live-reachability.py --dev /dev/ttyACM0 --escalate --json
```
```bash
# one command over the framed channel (unique request id, on-device sha256, real exit code)
sudo timeout 120 bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 \
     --run 'id; cat /proc/uptime; tr " " "\n" < /proc/cmdline | grep -E "androidboot.mode="; systemctl is-system-running' \
     --timeout 40
# →  rc=1 frame=d03b7a63 sha_ok=yes
#    uid=0(root) gid=0(root) groups=0(root)
#    850.62 5882.66
#    androidboot.mode=charger
#    degraded
```
```bash
# a batch file (one command per line) — the pattern the earlier live preflight used
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 \
     --batch docs/beta-finalization/preflight/live/<your-batch>.txt --timeout 25
```

A healthy capture shows `sha_ok=yes` and `rc=0` on every frame the phone actually ran. **A half-alive port that echoes bytes but produces no verified frame is `BLOCKED_EXTERNAL_RESOURCE`, never success** — the tool already produces exactly that verdict (`reachability-20261016T212618+0200` recorded `"blocked_reason": "port answered bytes but no verified command frame (half-alive console)"`). When that happens, change the diagnostic (alternate DTR assert, `--escalate`, re-enumerate, re-probe), do not retry blindly.

## 3.4 Host quirks you must know before you blame the phone

* **Shared-lock quirk.** `/tmp/nuxel-live.<dev>.lock` may exist owned by a *different* uid; on this host root then cannot open it for writing (`[Errno 13] Permission denied`) even though the port itself is fine. `scripts/s10plus-debug-pack/nuxel-live.sh` already detects this and falls back to a private lock (`/tmp/nuxel-live.<dev>.0.lock`) with an explicit stderr note; `tools/beta/live/nuxel_live.py` does **not** and will traceback. Before a deploy run, remove stale locks you own (`python3 -c "import glob,os;[os.unlink(p) for p in glob.glob('/tmp/nuxel-live.*.lock')]"`) or set `NUXEL_LIVE_LOCK`. **Fix `nuxel_live.py` to use the same fallback** (it is a real defect on Linux) and commit it.
* **A silent `--dev /dev/ttyACM0` is not always a dead phone.** In this task the gadget re-enumerated (kernel log shows `USB disconnect … device number 15` → `new SuperSpeed USB device number 16`) and the port was byte-silent for ~2 minutes, then answered normally on the framed channel with no action taken. Always: probe → if silent, wait/re-enumerate/re-probe → only then escalate.
* **kmsg interleaving.** The console mirrors `/dev/kmsg`; vendor kernel threads flood it (SSP/TrustZone lines, e.g. `[SSP]: debug_work_func(...)`, load average ~12 inherited from the Samsung vendor kernel — see `briq` A31 notes). Long or unframed commands get shredded. Always use the framed channel with short commands; never rely on terminal echo.
* **Two evidence-path generations exist.** Old bundles contain MacBook paths. Yours must be written from this host; the `evidence_dir` recorded inside each new bundle must be under `/x/nuxel/...`.

## 3.5 Naming and evidence conventions to keep

* Evidence bundles: `docs/beta-finalization/live/evidence/<kind>-YYYYMMDDTHHMMSS+0200/` with a `SHA256SUMS`, a machine-readable `*.json`, and the raw transcript.
* Kinds already used: `reachability-*`, `deploy-*`, `baseline-*`, `reboot-verify-*`, `touch-*`, `soak-*`. Keep the same grammar.
* Every bundle is committed to git in the same commit as the claim it supports.

---

# 4. STEP 0 — RESTORE A VALIDATED CONSOLE AND A NON-CHARGER BOOT (MANDATORY, DO THIS FIRST)

Nothing else can be verified until this is true.

## 4.1 Confirm the console, then read the boot mode — do not guess

```bash
sudo python3 tools/beta/live/nuxel-live-reachability.py --dev /dev/ttyACM0 --json                          # expect exit 0
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run \
  'tr " " "\n" < /proc/cmdline | grep -E "androidboot.mode=|charging_mode="; cat /proc/uptime; ls /sys/class/sec/tsp 2>&1; systemctl --failed --no-pager' \
  --timeout 40
```

## 4.2 If `androidboot.mode=charger` is present (it is, right now), the touchscreen cannot exist

This is a **boot-time** kernel decision (`lpcharge=1` → `sec_ts_init()` returns `-ENODEV` before `i2c_add_driver()`), not a userspace bug, and it cannot be worked around in userspace. There is no `CONFIG_KEXEC` and the driver is not modular. The documented, permitted remedy is a **normal boot that is not in charger/LPM mode**.

Order of attempts (each one bounded, each one recorded):

1. **Normal OS reboot from the running system** (this is what A32 demonstrated removes the condition):
   ```bash
   sudo python3 tools/beta/live/nuxel-live-reboot-verify.py --dev /dev/ttyACM0 --checklist-only      # dry: show the checklist
   sudo python3 tools/beta/live/nuxel-live-reboot-verify.py --dev /dev/ttyACM0 \
        --reboot --reason "clear LPM/charger-mode boot so sec_ts can initialise" \
        --diagnostic "re-read /proc/cmdline for androidboot.mode and confirm sec_touchscreen is registered" \
        --reconnect-timeout 240 --probe-seconds 8 --json
   ```
   Then re-read `/proc/cmdline`, `ls /sys/class/sec/tsp`, `cat /proc/bus/input/devices`, `systemctl status nuxel-touch-arm.service`.
   **Do not** issue a second reboot because the first has not reconnected yet.
2. If the phone comes back in charger mode again, this is a **physical, owner-side boot condition**: with the handset powered off and on battery (USB cable out), boot with the power button, wait ~30 s, then reattach the cable for the console. Record this as a `NEEDS_OWNER_TEST` instruction if you cannot perform it, and continue with everything that does not require touch.
3. If charger-mode persists across a genuine normal boot, the durable fix is the existing offline source patch, which stays **`BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED`** — document it, do **not** flash it. (`tools/s10plus/a33/nuxel-bootmode-guard.py`, `configs/nuxel/touch/bootmode-guard.json` and its unit are part of the guarded deploy for exactly this reason.)

**Gate for proceeding:** record, in the new evidence bundle, the console receipt, `/proc/cmdline`, the boot mode, uptime, the input-node inventory and the failed-unit list. If touch cannot be restored in this session, say so and continue all non-touch work — never stall, never fake it.

---

# 5. STEP 1 — LIVE BASELINE CAPTURE (closes `briq-10a`)

```bash
sudo python3 tools/beta/live/nuxel-live-baseline.py --dev /dev/ttyACM0 --json
```

This records the A32 baseline against the *real* device (kernel, Fedora, cmdline, fb, input, audio, radio, power, packages, services, PWA hashes) into a fresh `baseline-*` bundle. Then close the record honestly:

* If the console was reachable and the bundle is real → `briq-10a` → `VERIFIED_ON_S10PLUS` for the capture itself (state: implemented), with the bundle path in `evidence[]`.
* If the console was not reachable → `BLOCKED_EXTERNAL_RESOURCE` and say why, with the raw transcript.

Also write the missing expected artefact: **`docs/beta-finalization/live/BASELINE-CAPTURE.md`** — what was captured, when, from which host, with which commands, and the exact device facts (including `androidboot.mode`, uptime, kernel, rootfs usage, failing units).

---

# 6. STEP 2 — DEVICE INVENTORY AND BLOCK-ORDER CHECK (read-only)

Re-run the preflight batches on this boot and keep the outputs as the *current* baseline (the existing ones are from 2026-10-16 19:26–20:26 on this host and are still useful as comparison, but the phone has rebooted since):

```bash
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --batch docs/beta-finalization/preflight/live/batch-1-identity.txt --timeout 25
# … and batch-2-graphics-input.txt, batch-3-audio-radio-power.txt, batch-4-pkgs-services-receipts.txt
```

Then, before you write anything, answer these on paper (put it in the evidence bundle):

* Does `/home/nuxel/nuxel` exist? Is the PWA tree there? Which revision/version does the device believe it is running?
* Does `/etc/systemd/system/nuxel-*.service` exist and match the repository's definitions?
* Is `nuxel-web` answering on `127.0.0.1:8000`? (`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html`)
* Is `/usr/local/bin/nuxel-console` present? Are the `a33` tools present in `/usr/local/bin`?
* Is `flatpak` present on the phone? (Baseline says **no** — `flatpak: command not found`.) That has a direct consequence for NuXtore (§8.9).
* Is `/etc/nuxel/` populated? Which of the 37 deploy targets already exist, and do their hashes match the repository?

---

# 7. STEP 3 — PROTECT THE BASELINE BEFORE THE FIRST WRITE (mandatory)

```bash
tools/beta/rollback.sh status
tools/beta/rollback.sh capture --briq briq-10b-live-deploy-userspace --label pre-live-deploy-$(date +%Y%m%dT%H%M%S%z)
```

Confirm, for **every** target you are about to overwrite: previous hash recorded, previous file preserved, and a documented restore command. Then read `docs/beta-finalization/release/REBOOT-ROLLBACK.md` and `ROLLBACK.md` and confirm the userspace fallback frontend is known-good (`tools/nuxel-rollback-home.sh` must remain a working route: native home → PWA kiosk home).

Rules (task.md §54), restated because they are the difference between a beta and a bricked demo:

1. record previous hash → 2. stage next to target → 3. verify sha256 → 4. atomic rename install → 5. restart **only the smallest affected service** → 6. health-check → 7. on failure, restore the recorded baseline and report `ROLLED_BACK`.

Never run two clients against `/dev/fb0`, the ALSA card or the input nodes at once. Never let a network/firewall change sever the only reachable console without a time-bounded auto-rollback.

---

# 8. STEP 4 — APPLY THE BUILD TO THE PHONE

## 8.1 Dry-run the existing plan first (proves the invariants still hold)

```bash
python3 tools/beta/live/nuxel-live-deploy.py --json                 # plan/dry-run only → IMPLEMENTED_NOT_DEPLOYED
```
Review the generated bundle: 37 steps, 7 groups, the single deliberate skip (`console-and-kernel-side-followups` → `BLOCKED_KERNEL`), and every target path resolving under a userspace root. Any invariant violation must be fixed **before** `--apply`.

The plan you are re-running is exactly this (targets on the device in the third column):

| # | group | repository source | device target |
|---|---|---|---|
| 1–21 | `launcher-pwa` | `pwa/nuxel-home/{index.html,manifest.json,sw.js,colour-test.html}` + `css/*.css` + `js/*.js` | `/home/nuxel/nuxel/pwa/nuxel-home/…` |
| 22 | `status-bar-safe-zones` | `configs/nuxel/statusbar-safezones.json` | `/etc/nuxel/statusbar-safezones.json` |
| 23–28 | `session-units` | `services/nuxel-session/systemd/*.service`, `services/nuxel-web.service` | `/etc/systemd/system/{nuxel-wayland,nuxel-wl-fb,nuxel-touch-arm,nuxel-button-manager,seatd,nuxel-web}.service` |
| 29–30 | `animation-handoff` | `configs/nuxel/boot/animation-handoff.json`, `verbose-boot.json` | `/etc/nuxel/boot/…` |
| 31–33 | `touch-and-buttons` | `configs/nuxel/touch/bootmode-guard.json`, `configs/nuxel/buttons/reboot-gate.json`, `configs/nuxel/touch/nuxel-bootmode-guard.service` | `/etc/nuxel/touch/…`, `/etc/nuxel/buttons/…`, `/etc/systemd/system/nuxel-bootmode-guard.service` |
| 34–37 | `audio-and-network-config` | `configs/nuxel/audio/audio.json`, `jack-routes.json`, `configs/nuxel/time/nuxel-chrony.conf`, `configs/nuxel/app-registry/app_registry.json` | `/etc/nuxel/audio/…`, `/etc/nuxel/time/…`, `/etc/nuxel/app-registry/…` |

## 8.2 Apply it, group by group, in this order, with a health check between groups

```bash
# lowest risk first: launcher assets, then its config, then the session graph, then the rest
sudo python3 tools/beta/live/nuxel-live-deploy.py --apply --only launcher-pwa,status-bar-safe-zones --json
sudo python3 tools/beta/live/nuxel-live-deploy.py --apply --only session-units --json
sudo python3 tools/beta/live/nuxel-live-deploy.py --apply --only animation-handoff,touch-and-buttons,audio-and-network-config --json
```
(or one `--apply` run for all groups if the first groups are clean — but the *evidence* must show per-group results).

Per group: the tool stages → verifies SHA-256 → atomically installs → restarts only the declared smallest service → health-checks → auto-rolls-back on failure. Expected restart mapping: `launcher-pwa`/`status-bar-safe-zones` → `nuxel-web`; `animation-handoff` → `nuxel-wayland`; `touch-and-buttons` → `nuxel-touch-arm`. Groups with `restart_service: None` must be paired with a deliberate, documented reload (or a later reboot) — say explicitly in the evidence which it was.

After the session units land, re-verify on the phone:
```bash
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run \
  'systemctl daemon-reload; systemctl is-system-running; systemctl --failed --no-pager; systemctl status nuxel-wayland nuxel-wl-fb nuxel-web nuxel-touch-arm nuxel-button-manager --no-pager | grep -E "^\s*(●|\*)?\s*nuxel|Active:"' --timeout 60
```
and confirm the launcher answers: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html` → `200`.

Use `--observation "<verbatim on-device observation>"` to upgrade a verdict from `DEPLOYED_UNVERIFIED`, and only when the observation is verbatim and real.

## 8.3 THEN extend the manifest — because most of what QonQrete built is still not deployable

This is a **substantive requirement of this task**, not an optional nicety. The built programme is far larger than 37 files:

* `pwa/nuxel-apps/*` — settings, terminal, nuxtore, snekbyte, authenticator, downloader, media, photos, files, maps, mail, calendar, notes, calculator, clock, cleanup, rootcontrol, devmgmt, console, camera-gallery, recorder, casting(placeholder) …
* `shell/nuxel-shell/*` — native dialer, messages, contacts, settings, permissions
* `tools/s10plus/a33/*` — `nuxelctl`, the `*-diag.sh` hardware diagnostics, `nuxel-firewall.sh`, `nuxel-security-audit.sh`, `nuxel-vpn-tor.sh`, `nuxel-touch-trace.py`, `nuxel-touch-capture.sh`, `touch-probe.html`, `keyboard-probe.html`, `nuxel-time.sh`, `nuxel-verbose-boot.py`, and the compiled `nuxel-wl-fb`, `nuxel-button-manager`, `libnuxel-libinput-path.so`
* `services/*` — the notification/portal/bridge/console services and their unit files
* `configs/nuxel/**` beyond the 5 currently listed
* the boot animation container and its derived runtime artefact
* the package set in `images/s10plus/packages-manifest.json` (50 essential packages across 11 groups; `tools/s10plus/a33/verify-packages.py` reports `50/50` resolved offline)
* the app registry (`/etc/nuxel/app-registry/app_registry.json`) plus the PWA app registrations that make the launcher tiles real

Extend `tools/beta/live/deploy-manifest.json` (and the guard logic if needed) so that all of it is covered by the **same** invariants: userspace roots only, `assert_userspace_path`, stage→verify→atomic install→smallest restart→health check→rollback, per-group risk, per-group rollback text, and an explicit list of anything that is deliberately *not* deployable (with the reason and the terminal state). Then apply it in ascending risk order, with the same per-group evidence. Anything that needs a compiler, a package transaction or network access gets a clearly documented on-device install procedure and its own verdict.

Keep the manifest honest: a file that is staged but unverified is `DEPLOYED_UNVERIFIED`, not `VERIFIED_ON_S10PLUS`.

## 8.4 Native binaries

For `nuxel-wl-fb`, `nuxel-button-manager`, `nuxel-pwa-host`, `nuxel-console`, `libnuxel-libinput-path.so`: confirm ELF architecture is aarch64 and the build is reproducible from the repository, push with `scripts/s10plus-debug-pack/nuxel-live-deploy.sh <file> --to /usr/bin/<name> --restart <unit>`, and verify the installed SHA-256 plus a *behavioural* check — a matching hash is not proof the service works. If a rebuild is needed, build offline in the repository and never install a kernel.

**Do not run two framebuffer owners.** Before/after any graphics deploy, assert exactly one writer owns `/dev/fb0` and that `nuxel-wl-fb` is the intended one (the A32 `INV-4` hard pin).

---

# 9. STEP 5 — BOOT MODE, ANIMATION HANDOFF AND LAUNCHER ON THE REAL PANEL

`task.md` §7 and §8 must now be finished **on the phone**, with receipts, not by inspection.

1. **Readiness-driven handoff.** Verify the published handoff contract (`configs/nuxel/boot/animation-handoff.json`, `services/nuxel-animation`, the PWA first-frame readiness receipt) actually gates the transition: the animation must stop because the PWA reported ready with a display-ownership receipt — **not** because a timeout expired. Capture the receipts.
2. **Single display owner through the transition.** Prove no second framebuffer writer, no old first-light artwork, no redundant PWA splash video, no ghost frames, no animation continuing over the launcher, no abrupt black frames.
3. **Verbose boot** (`configs/nuxel/boot/verbose-boot.json`) must be switchable and observable on-device. The one-time **Bixby-hold override** is `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED` — assert that it is **refused, not faked**.
4. **Normal reboot validation** (`briq-10c-live-reboot-and-verify`): the phone must return to Nuxel, the console must come back, the launcher must start, and input devices must be present (touch permitted only in a non-charger boot — §4.2).
5. **Launcher parity and cache invalidation.** The authoritative launcher is the Nuxel Home PWA in WebKitGTK. Prove the deployed revision is what the phone serves (hash the served bytes, not the file), that the service worker does not resurrect stale assets, and that Settings/Terminal open from the launcher. Compare against the UTM VM reference where a VM is available (`bg-11-vm-parity`) — but never let VM success be reported as phone success.

**Do not flash the animation into BOOT and do not replace the launcher.** The deployed userspace handoff is the deliverable.

---

# 10. STEP 6 — TOUCHSCREEN, END TO END, ON THIS BOOT (priority zero — `task.md` §6)

Only meaningful in a non-charger boot. Trace the real chain: **sec_ts → IRQ → evdev → libinput → Phoc → Wayland → WebKitGTK → Nuxel Home PWA → action.**

On the phone (via the console, from the `a33` tooling you just deployed):

```bash
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run \
  'ls -la /dev/input/; ls -l /sys/class/input/; cat /proc/bus/input/devices; ls /sys/class/sec/tsp 2>&1; grep -iE "sec_ts|tsp|touch" /proc/interrupts; journalctl -b -u nuxel-touch-arm --no-pager | tail -40' --timeout 60
```

Then arm the bounded capture and produce the per-layer verdict:

```bash
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run \
  'nuxel-touch-capture.sh --budget 3 --dry-run' --timeout 60     # arming path first
# then, when the owner can touch the screen, the real capture with --expect-finger
```

Hardware truth rules: a registered driver is not working hardware; `libinput` discovering the device is not a finger; a synthetic console tap is not an interaction. The completion bar is a **real finger** opening Settings, returning Home, opening Terminal, scrolling the launcher, selecting an app, and using the on-screen keyboard. Until that happens, every touch claim is `NEEDS_OWNER_TEST` — but the pipeline diagnosis (which layer loses the event, if any) must be finished and recorded by you now.

Deploy `touch-probe.html` and `keyboard-probe.html`, stage the DOM collector, and leave the exact owner procedure in the manual checklist. Archive the bundle into `docs/beta-finalization/live/evidence/touch-*`.

---

# 11. STEP 7 — FINISH THE REST OF `task.md` ON THE PHONE

`task.md` §9–§52 were completed as repository work. Your job now is the **device tier** for each, with real evidence and honest verdicts. Minimum set — do not stop at the first three:

1. **Buttons** (`briq-03e`, power/volume/Bixby): deploy `nuxel-button-manager` + `configs/nuxel/input/button-fsm.json`; verify the key bitmap by capability (114/115/116/703), the POWER short-press screen toggle via `/sys/class/graphics/fb0/blank` + backlight, volume through the real ALSA element, and Bixby → Terminal. Physical presses are `NEEDS_OWNER_TEST`; the state machine and the config path are yours to prove.
2. **Audio** (`briq-03c/03d`): card0 `beyond-madera` (CS47L93 + 2× CS35L40); deploy `configs/nuxel/audio/audio.json` + `jack-routes.json`; verify mixer writes through the real element and the jack route logic. **Audibility and headphones are `NEEDS_OWNER_TEST`; mixer success is not sound.**
3. **Time / RTC** (`briq-03b`): the phone's clock is **wrong right now** (a live capture read `2026-09-15T00:15Z` while the real date was 2026-10-16) — this is a real, user-visible defect. Deploy `configs/nuxel/time/nuxel-chrony.conf`, run `nuxel-time.sh`, and get the clock right (NTP if the network is available, otherwise set from the host of a documented value and say so). Persistence across reboot remains `NEEDS_OWNER_TEST`.
4. **Wi-Fi / networking** (`briq-03a`): the driver side is present (`phy0`, `brcmfmac-wifi`, `wlan0`/`wlan1`/`p2p0`, `rmnet0-7`, `mcps0`, `umts_dm0`), and `rfkill` shows the Wi-Fi radios unblocked while **Bluetooth is soft-blocked**. Deploy `nuxel-wifi-diag.sh`; association/firmware availability is the honest `BLOCKED_FIRMWARE`/`NEEDS_OWNER_TEST` split — do not invent a signal.
5. **Bluetooth / NFC / GNSS / sensors / camera / microSD / modem** (`briq-08b…08i`): run each `a33` `*-diag.sh` **on the phone**, capture the raw output, and set the verdict the device actually supports (`Needs_OWNER_TEST`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `NOT_SUPPORTED_ON_DEVICE`). `mmcli -L` currently reports **no modems** — the Shannon LTE gap stays `BLOCKED_FIRMWARE`, and the dialer/messages apps must keep reporting it truthfully on screen.
6. **App inventory and registry** (`briq-06a…06e`): deploy the app registry and the PWA app tree so the launcher tiles resolve to real, servable applications; re-run `verify-app-registry.py` / `verify-app-inventory.py` against what is actually on the device. A directory name is not an application, and an icon is not an application.
7. **Settings** (`briq-06d`): extend the existing Settings app on the phone (never a second Settings app), including the **About Phone** page fed by *real* device identity (model `SM-G975F`, `beyond2lte`, Exynos 9820, kernel 4.14.253, Fedora 43, Nuxel `v0.5.0-beta-rc1`+build hash), and the **Developer** page (live console, logs, devices, services, framebuffer). No security lock-screen patterns/PIN/biometrics in this cycle; no hidden developer options; no Android-style accessibility-control services.
8. **Security and privacy** (`briq-05a…05d`): deploy the permission manager, firewall, VPN/remote surfaces and the security auditor, and **test the denials on the device** (direct device access, alternate D-Bus paths, bridge APIs, direct sockets, reopening a revoked permission). Fail closed where 4.14 allows; document exactly what it cannot enforce. Never ship a switch that lies about its protection. The Live Console manager must keep a local owner takeover path.
9. **NuXtore and application installation** (`briq-07a`): NuXtore is the Flatpak-fronted app store, and the phone currently has **no `flatpak` binary at all**. Install Flatpak (and the runtime) on the phone through the normal package path if the repository/network state allows, or set the correct honest state — `IMPLEMENTED_NOT_DEPLOYED` / `BLOCKED_EXTERNAL_RESOURCE` — with the reason. Do not claim an app store works when its backend is absent.
10. **Specialty apps** (`briq-07b…07f`): cleanup, DevMgmt, media/downloader, authenticator (TOTP/HOTP, local-only, encrypted store, no secrets in logs), SnekByte (original gameplay, WoNQ Mode and the Poop-o-meter preserved, touch + physical keyboard), Penguinterface (cosmetic compatibility profiles only — no enterprise/attestation bypass), Live Console app. Deploy them; verify launch behaviour on the phone where possible.
11. **Packages** (`briq-04a`): reconcile `images/s10plus/packages-manifest.json` with `rpm -qa` on the device (baseline: **410 packages**). Install what the verified manifest says is missing, using the normal package manager; never install a kernel.
12. **Performance and storage** (`task.md` §50): rootfs `/dev/sda31` is 3.9 G with **47% used** — measure, don't speculate. Watch WebKit subprocess count/memory, Phoc and `nuxel-wl-fb` CPU (baseline showed `nuxel-wl-fb` at ~63% and `phoc` at ~32%), leftover animation processes, swap (none configured), temperature.

For every one of these: the device-side action, the raw capture, the verdict, and — where a human is required — a `NEEDS_OWNER_TEST` row in the manual checklist. **Never** promote a `NEEDS_OWNER_TEST` to `VERIFIED_ON_S10PLUS`.

---

# 12. STEP 8 — ON-DEVICE SOAK AND STABILITY

```bash
tools/beta/soak.sh --plan
tools/beta/soak.sh --device --duration 1800        # bounded on-device soak; 8 h is the device tier
```
Requirements: no spontaneous reboot; `systemctl --failed` empty (or every entry explained); single framebuffer owner; launcher answering; stack CPU and RSS not growing without bound; disk headroom measured; terminal state `VERIFIED_ON_S10PLUS` **only** for the samples the device produced. An unreachable console is `BLOCKED_EXTERNAL_RESOURCE`, never a fabricated sample.

---

# 13. STEP 9 — REPAIR THE RELEASE RECORD (this is part of the deliverable)

The reports currently describe a repository-only pass. After this task they must describe the phone.

1. **Work queue** — record real verdicts and evidence for `briq-10a`, `briq-10b`, `briq-10c`, and for every record whose state this task changed (`python3 tools/beta/workqueue.py --help` for the exact CLI; `verify-schema --json` must stay `"ok": true`). Keep `docs/beta-finalization/BASELINE-PROTECTION.md` / `baseline-protection.json` truthful.
2. **Create the missing expected artefacts:** `docs/beta-finalization/live/BASELINE-CAPTURE.md` and `docs/beta-finalization/live/DEPLOYMENTS.md` (per-deploy: component, source revision, device target, staged hash, installed hash, restart performed, health result, rollback route, timestamp, evidence bundle).
3. **Device capability manifest** — update `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.{md,json}` for every subsystem this task actually touched, keeping `tools/beta/validate-capability-manifest.py` green (no verdict stronger than its work-queue record).
4. **Both mandatory reports** — `docs/beta-finalization/BETA-FINALIZATION-ENGINEERING-REPORT.md` and `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` — must now include the on-device results, the deploy hashes, the reboot results, the boot-mode finding, and the still-open items. The Beta verdict must be re-derived from the new evidence and must stay honest:
   * `BETA_ACCEPTANCE_PASSED` only if the physical acceptance tests were actually observed;
   * otherwise `BETA_CANDIDATE_PENDING_HARDWARE_PROOF` (or `BETA_BLOCKED` / `ALPHA_ONLY` if the evidence says so).
5. **Changelog + version** — add the deployment cycle to `CHANGELOG.md` in lockstep with `VERSION` (bump only if the cycle warrants it; do not silently renumber).
6. **Repository hygiene** — commit the `nuxel_live.py` lock-fallback fix, the deploy-manifest extension, any Linux-host discovery fixes, all new evidence bundles, the updated reports, and the work-queue records. `git status` must be clean except for unavoidable artefacts. Nothing important may exist only on the phone.
7. **Rollback documentation** must state, for every deployed component, how to get back — and the rollback must be *tested*, not merely described.

---

# 14. EVIDENCE AND VERDICT LAW

* A verdict is only as strong as its capture. `VERIFIED_ON_S10PLUS` requires a fresh artifact produced **by the device** in this session, stored in the repository.
* `DEPLOYED_UNVERIFIED` is the honest state for anything written but not behaviourally confirmed.
* A passing unit test can never yield `VERIFIED_ON_S10PLUS`.
* `NEEDS_OWNER_TEST` is terminal for this task: never auto-promoted, never inferred from a synthetic action.
* A missing userspace package is not proof a kernel driver is missing; a registered kernel driver is not proof the hardware works; a hash match is not proof a service works.
* If three attempts fail the same way, change the diagnostic. If the console is lost, follow the reboot policy — bounded, one reason, different diagnostic, no blind repeats — and stop device-side automation if recovery would be required.
* `task.md`'s core rule stands: **do not assume a feature works because its files exist.**

---

# 15. PRACTICAL PLAYBOOK (copy/paste, adapt paths)

```bash
cd /x/nuxel
git rev-parse HEAD && cat VERSION && git status --short

# --- console ---
sudo -n true
sudo python3 tools/beta/live/nuxel-live-reachability.py --dev /dev/ttyACM0 --json
sudo timeout 120 python3 tools/beta/live/nuxel-live-reachability.py --dev /dev/ttyACM0 --escalate --json

# --- device reads (always framed, always short) ---
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run 'uname -a; id' --timeout 30
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run \
  'tr " " "\n" < /proc/cmdline | grep -E "androidboot.mode=|charging_mode="; cat /proc/uptime; ls /sys/class/sec/tsp 2>&1; systemctl --failed --no-pager' --timeout 40
sudo bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --batch <file>.txt --timeout 25

# --- baseline / protection ---
sudo python3 tools/beta/live/nuxel-live-baseline.py --dev /dev/ttyACM0 --json
tools/beta/rollback.sh status
tools/beta/rollback.sh capture --briq briq-10b-live-deploy-userspace --label pre-live-deploy

# --- deploy ---
python3 tools/beta/live/nuxel-live-deploy.py --json                      # dry run
sudo python3 tools/beta/live/nuxel-live-deploy.py --apply --only launcher-pwa,status-bar-safe-zones --json
sudo python3 tools/beta/live/nuxel-live-deploy.py --apply --only session-units --json
sudo python3 tools/beta/live/nuxel-live-deploy.py --apply --only animation-handoff,touch-and-buttons,audio-and-network-config --json

# --- health / reboot / soak ---
tools/beta/health-check.sh --json build/reports/health.json
sudo python3 tools/beta/live/nuxel-live-reboot-verify.py --dev /dev/ttyACM0 --checklist-only
sudo python3 tools/beta/live/nuxel-live-reboot-verify.py --dev /dev/ttyACM0 --reboot \
  --reason "<one reason>" --diagnostic "<a diagnostic that differs from last time>" \
  --reconnect-timeout 240 --json
tools/beta/soak.sh --device --duration 1800

# --- repository gates (keep them green or declare the raw verdict) ---
tools/beta/run-all-tests.sh
python3 tools/beta/validate-capability-manifest.py
python3 tools/beta/workqueue.py verify-schema --json
```

Known pre-existing gate state to fix or explain: the last full gate run (`build/reports/beta-tests/summary.json`, `/tmp/finalrun.txt`, 2026-10-16 21:11) was `gate: red`, `verdict: OFFLINE_TESTED_FAIL`, with 6 hard failures owned by `bg-00-preflight` (`U-workqueue-schema`, `U-workqueue-unit`, `U-regression-guard-selftest`, `U-baseline-regression-guard`, `U-baseline-a32-suite`, `U-boot-s10plus-gates`) plus 5 cross-group allowances and 7 warnings. Do not hide these: fix them or report them with the raw verdict.

---

# 16. DEFINITION OF DONE FOR TASK 2

1. A console session that is verified, bounded and reproducible from this host, with the boot mode read from the device and recorded.
2. A live baseline bundle for the current boot, archived and committed; `briq-10a` closed with a real verdict.
3. A rollback baseline captured **before** the first write, with a tested restore route stated in the docs.
4. The 37-step manifest **applied** (`--apply`), per-group, with install hashes, the smallest service restarts, health checks, and per-group results in a `deploy-*` bundle; `briq-10b` closed with a real verdict.
5. The manifest **extended** so that the rest of the built programme (apps, tools, native binaries, services, configs, packages) is deployable and, where verified, deployed — with everything not deployed named, reasoned and given a terminal state.
6. Touchscreen: the full pipeline traced on this boot; the failing layer (if any) identified; the owner procedure staged; verdict `NEEDS_OWNER_TEST` unless a real finger proved otherwise.
7. Boot animation handoff, display ownership and launcher parity verified on-device with receipts; a normal reboot performed and verified (`briq-10c`); the phone returns to Nuxel with a working console.
8. On-device results for buttons, audio, time/RTC, networking, hardware subsystems, app inventory, settings, security posture, package reconciliation and NuXtore — each with its honest verdict.
9. A bounded on-device soak with no unexplained reboot.
10. The release record repaired: work-queue records, capability manifest (validator green), `BASELINE-CAPTURE.md`, `DEPLOYMENTS.md`, both mandatory reports, changelog, all committed; `git status` clean; every persistent change represented in the repository.
11. The phone left in a known-good state with a documented way back, and a clear statement of what still needs the owner's hands.

---

# 17. FINAL DIRECTIVE

The build is done. The phone is plugged in. The console works from this host right now.

1. Verify the console. Read the boot mode. Fix the charger-mode boot condition (normal reboot; never flash).
2. Capture the baseline. Protect it. Then write.
3. Apply the built userspace in guarded groups, verifying every step on the device.
4. Extend the deploy so that *everything* that was built can actually reach the phone.
5. Finish `task.md`'s device-tier requirements on the handset — touch first, then boot/animation/launcher, then buttons, audio, time, networking, apps, security, hardware subsystems.
6. Reboot normally at least once and prove Nuxel comes back.
7. Soak it, measure it, and report exactly what the phone does.
8. Repair the release record so it describes this phone, on this boot, with this evidence.

Do not declare success because a script exited 0. Declare success because the phone, observed over the live console, did the thing.

**NUXEL IS ALREADY WRITTEN. NOW MAKE THE PHONE SHOW IT.** 🐧🔥
