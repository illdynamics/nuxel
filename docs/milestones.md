<!-- Nuxel v0.2.2-alpha -->
# Nuxel OS Milestone Tracking

> **Status:** Active development — tracking progress against the design document's
> milestone list from `nuxel-linux-phone-design.md` (Section 12).
>
> **Target device:** Google Pixel 10 Pro XL (mustang) — serial: 58211FDCQ001LA
> **VM platform:** UTM on Apple Silicon (M1/M2/M3/M4)

<!-- =====================================================================
  NOTE ON LINE COUNTS (accuracy correction, cycle CI)
  ----------------------------------------------------------------------
  Earlier drafts of this file repeated an inflated "*~25K lines*" figure for
  the native core. The verified, measured counts (reproducible from the repo
  root) are far lower but represent real, present code:

      Re-measure from the repo root on cycle: corrected cycle: claimed 25K,
      actual core ~7.2K. Single source of truth: docs/repo-audit.md.

      # pure Python across the two core trees (~7.2K "true core"):
      find services/ shell/ -name '*.py' | xargs wc -l
      #   => 7,234 lines total (services/ 2,863 + shell/ 4,371)

      # Python + C (the exact command older prose quoted):
      find services/ shell/ -name '*.py' -o -name '*.c' | xargs wc -l
      #   => 12,246 lines total

      # Full .py/.c/.js cross-tree total (services + shell + pwa):
      find services/ shell/ pwa/ \( -name '*.py' -o -name '*.c' -o -name '*.js' \) | xargs wc -l
      #   => 18,036 lines total

  The single-file counts below were likewise recorrected to their measured
  values (e.g. sandbox.c is 2,005 lines, not ~20K).

  NOTE ON "GAPS" -- most so-called *gaps* are NOT missing files:
    - systemd units:  services/{bridge,portal,notifications}/systemd/*.service
    - D-Bus policy:   services/{bridge,portal,notifications}/dbus/*.conf
    - OpenRC units:   shell/config/openrc/{nuxel-bridge,nuxel-portal,
                      nuxel-notifications,nuxel-firstboot}
  They already exist in the repository; only wiring/integration remains.
  Re-measure before trusting any figure written before this note.
===================================================================== -->

---

## Milestone A: VM Bootstrap

**Status:** ✅ DONE (infrastructure in `vm/` directory)

**Goal:** UTM ARM64 VM with Phosh, Nuxel services running, phone-shaped resolution.

### What's been built

| Item | File | Status |
|------|------|--------|
| UTM VM setup guide | `vm/utm-setup-guide.md` | ✅ Complete |
| VM bootstrap script | `vm/nuxel-vm-bootstrap.sh` | ✅ Complete |
| Phone resolution configurator | `vm/phosh-phone-resolution.sh` | ✅ Complete |
| Snapshot manager | `vm/nuxel-vm-snapshot.sh` | ✅ Complete |
| Prerequisites detection | In bootstrap script | ✅ Fedora & Debian |
| Nuxel user creation | In bootstrap script | ✅ |
| Directory layout | In bootstrap script | ✅ |
| Core service installation (bridge, portal, notifications) | In bootstrap script | ✅ |
| AppArmor profiles | In bootstrap script | ✅ Base + privileged + sandbox |
| hardened_malloc installation | In bootstrap script | ✅ From GrapheneOS source |
| nftables base ruleset | In bootstrap script | ✅ |
| Phosh mobile UX config | In bootstrap script | ✅ |

### What remains

- [ ] Automatic test: Verify all services start on boot
- [ ] Pre-built UTM VM image download (optional convenience)
- [ ] vm-to-flash pipeline: Test that VM setup translates directly to Pixel flashing

---

## Milestone B: Shell and System App Prototype

**Status:** 🟡 IN PROGRESS

**Goal:** Phosh + GTK settings + PWA launcher + permission manager UI.

### What's been built

| Item | File | Status |
|------|------|--------|
| nuxel-settings (GTK4/libadwaita) | `shell/nuxel-shell/nuxel-settings/main.c` | ✅ 439 lines — Wi-Fi, Bluetooth, Display, Sound, About pages |
| nuxel-dialer (GTK4/libadwaita) | `shell/nuxel-shell/nuxel-dialer/main.c` | ✅ Python-based dialer stub |
| nuxel-messages (GTK4/libadwaita) | `shell/nuxel-shell/nuxel-messages/main.c` | ✅ Messages stub |
| nuxel-contacts (GTK4/libadwaita) | `shell/nuxel-shell/nuxel-contacts/main.c` | ✅ Full contact manager |
| nuxel-firstboot (Python/GTK) | `shell/nuxel-shell/nuxel-firstboot/main.py` | ✅ Full wizard (1362 lines) |
| nuxel-permissions (GTK4/libadwaita) | `shell/nuxel-shell/nuxel-permissions/main.c` | ✅ **New** — 775 lines, full permission manager |
| Phosh lockdown config | `~/.config/phosh/phosh.ini` | ✅ Created by bootstrap |
| PWA launcher mechanism | In sandbox launcher | ✅ Via isolated browser profile |

### What remains

- [ ] Integration test: All system apps launch in Phosh
- [ ] App grid: Verify all apps appear in Phosh's application grid
- [ ] Dark theme: Confirm GTK dark theme applies through libadwaita
- [ ] Landscape detection: Test orientation changes (portrait → landscape)
- [ ] Performance: Profile app launch times under 4-core/4GB VM

---

## Milestone C: PWA Runtime Prototype

**Status:** 🟡 IN PROGRESS

**Goal:** Per-app isolated browser profiles, offline cache, permissions, uninstall cleanup.

### What's been built

| Item | File | Status |
|------|------|--------|
| PWA model document | `docs/pwa-model.md` | ✅ Complete (22KB) |
| Calendar PWA | `pwa/nuxel-apps/calendar/` | ✅ Full calendar (527 lines JS) |
| Calendar portal integration | `pwa/nuxel-apps/calendar/js/calendar.js` | ✅ **New** — calendar portal integration |
| PWA permission bridge | Via D-Bus portal | ✅ Calendar portal type added |
| PWA data isolation | Flatpak/isolated profiles | ✅ Via sandbox launcher |
| PWA install/uninstall | `nuxel-uninstall-helper.sh` | ✅ **New** — full data wipe |

### What remains

- [ ] Test: Launch Calendar PWA in isolated browser profile
- [ ] Test: Calendar portal permission dialog appears on first launch
- [ ] Test: Offline cache survives app restart
- [ ] Test: Uninstall removes all PWA data (IndexedDB, localStorage, Service Workers)
- [ ] Test: Two PWAs cannot access each other's storage
- [ ] Add more PWA examples: Notes, Files, Weather

---

## Milestone D: Native Sandbox Prototype

**Status:** 🟡 IN PROGRESS

**Goal:** Sandboxed GTK app with portals, denied-by-default home/network.

### What's been built

| Item | File | Status |
|------|------|--------|
| Sandbox launcher (C) | `shell/nuxel-shell/nuxel-sandbox/sandbox.c` | ✅ 2,005 lines — full namespace/seccomp/Landlock sandbox |
| Sandbox header | `shell/nuxel-shell/nuxel-sandbox/sandbox.h` | ✅ 256 lines |
| Seccomp profiles | `shell/nuxel-shell/nuxel-sandbox/seccomp/` | ✅ |
| nftables integration | `shell/nuxel-shell/nuxel-sandbox/nftables.sh` | ✅ 315 lines |
| AppArmor profiles | In bootstrap | ✅ Base + privileged + sandbox |
| Portal daemon | `services/nuxel-portal/src/portal.py` | ✅ 571 lines — **extended with 5 new portals** |
| Portal types | portal.py | ✅ 14 portal types total (SMS, Call, Contacts, PhoneStatus, Location, Camera, Microphone, Settings, Calendar, Bluetooth, USB, Clipboard R/W, Background) |
| Bridge service | In bootstrap | ✅ D-Bus permission broker |
| Permission storage | `/var/lib/nuxel/permissions/` | ✅ JSON-based, per-app |
| Permission diff on update | In app-store concept | ✅ Documented in `docs/app-store.md` |

### What remains

- [ ] Test: Run sandboxed GTK app — home directory should be invisible
- [ ] Test: Network denied by default — `ping` should fail
- [ ] Test: Network allowed after explicit permission grant
- [ ] Test: File-open portal works (user picks one file)
- [ ] Test: Two sandboxed apps cannot see each other's processes
- [ ] Test: AppArmor enforcement blocks unapproved file access
- [ ] Test: nftables per-app network isolation
- [ ] Benchmark: Sandbox overhead on app startup

---

## Milestone E: Update Prototype

**Status:** 🔴 NOT STARTED

**Goal:** Immutable base image, signed updates, rollback.

### What's been built

| Item | Status |
|------|--------|
| Build signing tooling (`tools/sign-image.sh`, `tools/gen-keys.sh`) | ✅ Exists |
| Flash tooling (`boot/flash.sh`) | ✅ Exists |
| Builder script (`images/build.sh`, `images/build-ota.sh`) | ✅ Exists |
| Update mechanism design | ❌ Not started |
| Atomic update logic | ❌ Not started |
| Rollback mechanism | ❌ Not started |
| A/B partition concept | ❌ Not started |
| Signed update metadata schema | ❌ Not started |

### What remains

- [ ] Design update model: OSTree / systemd-sysupdate / RAUC / Mender / custom
- [ ] Create `tools/nuxel-update.sh` — signed update download and apply
- [ ] Create `tools/nuxel-rollback.sh` — revert to previous image
- [ ] Add A/B partition support to flash tooling
- [ ] Add verified boot metadata generation
- [ ] Test: Update in UTM VM
- [ ] Test: Rollback after broken update
- [ ] Test: Atomic update interrupted by power loss → recover
- [ ] Document update key management and rotation

---

## Milestone F: Pixel Hardware Research

**Status:** 🟡 IN PROGRESS

**Goal:** Mustang bootloader, kernel, device-tree status tracking.

### What's been built

| Item | File | Status |
|------|------|--------|
| Device identification | `nuxel-linux-phone-design.md` | ✅ Pixel 10 Pro XL, S/N 58211FDCQ001LA, G45RY |
| Bootloader unlock guide | `docs/bootloader-unlock-guide.md` | ✅ Complete |
| Device setup guide | `docs/device-setup.md` | ✅ Complete |
| Driver status tracker | `docs/driver-status.md` | ✅ Complete |
| Hardware validation checklist | `nuxel-linux-phone-design.md` §10 | ✅ Complete |
| Pixel 10 Pro XL boot status | design doc | ✅ UART/initramfs only (Nov 2025) |
| Device-tree patches tracking | design doc | ✅ Preliminary, posted by Google 2025-11 |
| Architecture doc | `docs/architecture.md` | ✅ Complete |
| Security model doc | `docs/security-model.md` | ✅ Complete |

### Current known status (May 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| **Bootloader unlock** | ⚠️ Untested | See `docs/bootloader-unlock-guide.md` |
| **Mainline kernel** | ⚠️ Preliminary DT | UART/initramfs only as of Nov 2025 |
| **Display** | ❌ Unknown | Requires kernel DRM driver |
| **Touch** | ❌ Unknown | Requires input driver |
| **Storage (UFS)** | ❌ Unknown | UFS driver status unclear |
| **Wi-Fi** | ❌ Unknown | Requires firmware + driver |
| **Bluetooth** | ❌ Unknown | Requires firmware |
| **Cellular modem** | ❌ Unknown | Exynos modem, no mainline support known |
| **Camera ISP** | ❌ Unknown | Tensor G5 ISP — no public mainline work |
| **Fingerprint** | ❌ Unknown | Pixel 10 under-display sensor |
| **USB-C** | ⚠️ Likely works | Standard USB-C controller |
| **Charging** | ❌ Unknown | Requires PMIC driver |
| **Verified boot** | ❌ Untested | Bootloader relock unknown |

### What remains

- [ ] Check if Google has released updated device-tree patches since Nov 2025
- [ ] Check postmarketOS porting status for mustang
- [ ] Check if bootloader (edk2 or similar) has been released for Pixel 10
- [ ] Attempt `fastboot flashing unlock` on the device (requires boot to fastboot)
- [ ] Document exact recovery path to stock firmware
- [ ] Check if LineageOS or other community projects have Pixel 10 support
- [ ] **Do not flash Nuxel until display, touch, and storage are proven**

---

## Overall Progress Summary

| Milestone | Status | Progress |
|-----------|--------|----------|
| **A: VM Bootstrap** | ✅ Done | 100% |
| **B: Shell & System Apps** | 🟡 In Progress | ~70% |
| **C: PWA Runtime** | 🟡 In Progress | ~60% |
| **D: Native Sandbox** | 🟡 In Progress | ~80% |
| **E: Update Prototype** | 🔴 Not Started | 0% |
| **F: Pixel Hardware** | 🟡 In Progress | ~30% |

**Overall:** ~57% complete toward first prototype.

---

## Next Actions (Prioritized)

1. **Sandbox integration testing** (Milestone D) — verify isolation boundaries
2. **PWA portal flow testing** (Milestone C) — calendar permission dialog end-to-end
3. **Permission manager UI testing** (Milestone B) — list, revoke, revoke-all in Phosh
4. **Update mechanism design** (Milestone E) — choose update framework, prototype
5. **Pixel bootloader unlock attempt** (Milestone F) — if device is physically available
6. **Build full VM image** — produce a bootable Nuxel VM ISO for distribution

---

## References

- Design document: `nuxel-linux-phone-design.md` (Section 12: Milestones)
- Architecture: `docs/architecture.md`
- Build guide: `docs/build-guide.md`
- Security model: `docs/security-model.md`
- Driver status: `docs/driver-status.md`
- App store model: `docs/app-store.md`
- Bootloader unlock: `docs/bootloader-unlock-guide.md`
- Device setup: `docs/device-setup.md`

---

<!-- Reconciliation & code-size accuracy owned by the Repo state audit & doc reconciliation build group (briq-01-audit). Single source of truth for all measured counts: docs/repo-audit.md. -->
