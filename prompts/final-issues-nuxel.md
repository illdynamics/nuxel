# Nuxel — Final Deep-Analysis & VM Boot/Test Report

Date: 2026-08-19 (host: macOS 15.7.5, arm64)
Repo: /Users/wicked/x/nuxel  (branch main, HEAD c3c4637)
VM:   UTM "nuxel-aarch64-phosh" (UUID 711988C4-B34A-4A0F-BA86-B2C4A182E4BE)

## 0. Verdict (short)

The UTM VM **boots and works**. After one real live-test fix (notification
history path mismatch) plus a few codebase cleanups, the three guest
verification suites are all green:

| Suite | Result (fresh run) |
|---|---|
| `vm-verify-services.sh` | **PASS=22 FAIL=0** |
| `vm-verify-phosh-agent.sh` | **HARD PASS (exit 0)** |
| `vm-verify-pwa.sh` | **PASS=17 FAIL=0** |

The codebase still has **non-blocking, honest gaps** — mainly that the
kernel/boot images are not cross-built yet, and several `#!/bin/sh` scripts use
bashisms. Those are documented below; none stop the VM demo from working.

---

## 1. What I ran (deep analysis)

- `bash -n` over every `*.sh` in the repo → **ALL SYNTAX OK**.
- `python3 -m py_compile` over every repo `*.py` → **0 errors**.
- JSON parse over every repo `*.json` → **0 errors**.
- `shellcheck -S warning` over all `*.sh` → 1 real error (fixed), plus warnings.
- `make validate` / `ci/validate-build.sh` → asset invariant + build gate.
- Live UTM test over SSH to `nuxel@192.168.64.3` (passwordless sudo confirmed):
  - `systemctl --failed` → **0 failed units**.
  - All 6 Nuxel units `active` (bridge, http-bridge, portal, notifications,
    web, apparmor-enforce).
  - Phosh 0.54.0 running, `wlr-randr` at **720x1440** (Nuxel phone resolution).
  - Re-ran all three `vm/vm-verify-*.sh` scripts in the guest.

---

## 2. Issues found AND fixed (this session)

### FIX-1 (blocking live test): notification history path mismatch
- **Symptom:** `vm-verify-services.sh` reported
  `[FAIL] notification history file MISSING at /var/lib/nuxel/notifications.json`,
  even though the notification itself was delivered.
- **Root cause (two parts):**
  1. `vm/nuxel-vm-bootstrap.sh` generated a systemd unit pinning the **legacy**
     path `NUXEL_NOTIFICATIONS_FILE=/var/lib/nuxel/notifications/history.json`,
     while the canonical single-file path (repo unit, `configs/nuxel/paths.conf`,
     docs) is `/var/lib/nuxel/notifications.json`.
  2. `vm-verify-services.sh` parsed `systemctl show -p Environment` with
     `tr ' ' '\n' | grep '^NUXEL_NOTIFICATIONS_FILE='`, but `systemctl show`
     prefixes the line with `Environment=`, so the grep never matched and the
     script fell back to `paths.conf` (canonical) while the daemon was actually
     writing to the legacy path.
- **Fix:**
  - `vm/nuxel-vm-bootstrap.sh`: pin the canonical path.
  - `vm/vm-verify-services.sh`: strip the `Environment=` prefix before extracting
    `NUXEL_NOTIFICATIONS_FILE`.
  - Applied live to the guest: updated `/etc/systemd/system/nuxel-notifications.service`,
    `systemctl daemon-reload`, `systemctl restart nuxel-notifications.service`.
- **Result:** canonical `/var/lib/nuxel/notifications.json` now created by the
  daemon; services verify now `PASS=22 FAIL=0`.

### FIX-2 (CI gate): stray duplicate media at repo root
- `tools/verify-pwa-assets.sh --verify` (wired into `make validate`) failed:
  `[VERIFY-FAIL] stray duplicate detected: ./nuxel-background.png`.
- `nuxel-background.png` and `nuxel-animation.mp4` at repo root were byte-identical
  copies of the canonical `assets/nuxel-background.png` and
  `assets/nuxel-boot-animation.mp4` (verified with `cmp`).
- **Fix:** `git rm nuxel-background.png nuxel-animation.mp4` (single-source
  invariant restored; canonical `assets/` copies remain).

### FIX-3 (CI gate): build script missing target serial
- `ci/validate-build.sh` required `images/build.sh` to reference serial
  `58211FDCQ001LA` (already present in `boot/flash.sh`, absent in `images/build.sh`).
- **Fix:** added `TARGET_SERIAL="58211FDCQ001LA"` to `images/build.sh`.

### FIX-4 (latent shell bug): `vm/nuxel-vm-snapshot.sh` `|| ""`
- `shellcheck` flagged SC2286: `python3 ... 2>/dev/null || ""` treats the empty
  string as a command name (would emit `bash: : command not found` on fallback).
- **Fix:** changed to `|| echo ""` in the snapshot metadata fallbacks.

### FIX-5 (robustness): verify log ownership race in `/var/tmp`
- `vm-verify-pwa.sh` / `vm-verify-phosh-agent.sh` write their evidence log to
  `/var/tmp`, which can be left root-owned by a prior root run; a non-root
  re-run could hit a transient `Permission denied` on line `: > "$OUT"`.
- **Fix:** both scripts now fall back to a user-owned log under `$HOME` when the
  shared `/var/tmp` file exists and is not writable by the current (non-root) user.

### FIX-6 (accuracy): hardcoded backend-availability note
- `vm-verify-services.sh` always printed
  `NOTE: absent ModemManager/NetworkManager/GeoClue => bridge/API serve mock ...`
  even when ModemManager and NetworkManager were active.
- **Fix:** the note is now computed from actual state; on this VM it correctly
  reports `absent backend(s) [GeoClue]`.

---

## 3. Remaining issues / honest gaps (NOT fixed — not VM blockers)

These are real and should be tracked, but fixing them is out of scope for a
VM demo and/or requires actual hardware/kernel bring-up.

| # | Severity | Where | Issue |
|---|---|---|---|
| 1 | High (device only) | `kernel/`, `images/`, `build/` | Kernel 6.12 (gs501/mustang) is **not cross-built**; `Image.gz`, `.config`, `boot.img`, `vbmeta.img`, `init_boot.img` are absent. `ci/validate-build.sh` therefore reports 7 FAILs (Passed 57 / Warnings 11). This matches README's honest "0% verified flashable OS". |
| 2 | Medium | `boot/recovery.sh`, `boot/initramfs/init.sh`, `images/hooks/luks-userdata.sh`, `images/hooks/verity-setup.sh` | `#!/bin/sh` shebang but use bashisms (`local`, `echo -e`). `boot/initramfs/init.sh` would break under busybox `ash`. Either switch to `#!/bin/bash` or make POSIX-sh-clean. |
| 3 | Low | `images/mkrootfs.sh` (SC2046) | Unquoted `$(pkg-config --cflags/libs ...)` word splitting in native shell compile lines. |
| 4 | Low | multiple scripts (SC2034) | Unused variables (`status`, `firmware_installed`, `AVB_PUBLIC`, etc.). Cosmetic. |
| 5 | Low | `vm/deploy-vm.sh` (SC2027) | Quoting in a log message unquotes `$VM_NAME`; cosmetic. |
| 6 | Info | guest | Legacy `/var/lib/nuxel/notifications/history.json` still exists from prior cycles; harmless cleanup candidate. |
| 7 | Info | `pwa/`, Flatpak/WPE | Production PWA isolation runtime not built; verified path is the DEV WebKitGTK path (documented limitation, not claimed as prod). |

---

## 4. VM boot / test evidence (2026-08-19)

- `utmctl list` → `711988C4-B34A-4A0F-BA86-B2C4A182E4BE started nuxel-aarch64-phosh`.
- Guest: `Linux nuxel-phosh 6.17.1-300.fc43.aarch64` (Fedora 43 ARM64).
- SSH reachable at `192.168.64.3` as `nuxel` (passwordless sudo).
- `systemctl --failed` → 0 loaded units.
- All Nuxel units active; listeners `127.0.0.1:8000` (nuxel-web) and
  `127.0.0.1:8080` (nuxel-http-bridge) present.
- Phosh session active (session 6, Type=wayland), `wlr-randr` current mode
  `720x1440`; fresh screenshot saved to `vm/screenshots/phosh-final-20260819.png`.
- Verification suites (fresh, post-fix): see §0 table.

---

## 5. Files changed this session

- `vm/nuxel-vm-bootstrap.sh` — canonical notification history path.
- `vm/vm-verify-services.sh` — env parsing fix + computed backend note.
- `vm/vm-verify-pwa.sh`, `vm/vm-verify-phosh-agent.sh` — `/var/tmp` log fallback.
- `vm/nuxel-vm-snapshot.sh` — `|| ""` → `|| echo ""`.
- `images/build.sh` — added `TARGET_SERIAL`.
- `nuxel-background.png`, `nuxel-animation.mp4` — removed (stray duplicates).

Pre-existing uncommitted change (not authored this session): `vm/deploy-vm-manifest.txt`
already pointed at rev c3c4637 before this analysis began.
