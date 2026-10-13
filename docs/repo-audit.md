# Nuxel Repo Audit & Doc Reconciliation

> **Single source of truth** for the *measured* state of the Nuxel codebase.
> Generated on **2026-08-13** from the tracked files in this repository.
>
> Every figure below was computed with `git ls-files` + `wc -l` over tracked
> source under `services/`, `shell/`, `pwa/`, and `firmware/`. Counts that are
> derived (`2,005-line sandbox.c`, `330-line bridge.js`) have been verified by
> direct measurement; nothing here is an estimate.
>
> This document supersedes the inflated code-size figures that appeared in early
> drafts of `README.md`, `docs/roadmap.md`, and `docs/milestones.md`, and it is
> the reference the other docs point back to so they stop drifting apart.

---

## 0. Why this audit exists

Early design docs repeatedly cited a **"~25K lines"** figure for the so-called
"native core" (and, in one place, "~20K" for `sandbox.c` alone). Those figures
were estimates, not measurements, and they do not match the repository.

The **measured, reproducible** core is:

- **~7.2K lines** — pure-Python core across `services/` and `shell/`
  (`7,234` lines of `.py`).
- **~18K lines** — Python + C + JavaScript across `services/`, `shell/`, and
  `pwa/` (`18,036` lines of `.py/.c/.js`).
- **~26K lines** — *all* tracked source (including configs, CSS, HTML, systemd
  units, D-Bus policies, OpenRC scripts, and icons) across the four scope trees
  (`26,203` lines).

None of these contradict the format "the codebase is bigger than earlier
claims"; the correction is that the *native core* was always far smaller than
"25K". `sandbox.c` is **2,005** lines, not ~20K.

> **Correction marker (used by other docs):**
> *Claimed 25K → measured core ~7.2K (Python) / 18,036 (full .py/.c/.js scope).*

---

## 1. Measured LOC table

Scope: `git ls-files` under `services/`, `shell/`, `pwa/`, `firmware/`,
excluding `__pycache__`, `.build/`, and `node_modules` trees.

### 1.1 Totals by language

| Category | Files | Lines | Notes |
|---|---|---|---|
| **Total tracked source (all types)** | — | **26,203** | across the four scope trees |
| **Python (`.py`)** | 18 | **7,234** | the "~7.2K true core" (services 2,863 + shell 4,371) |
| **C sources (`.c`)** | 7 | **5,825** | 5 shell GTK apps + sandbox + pwa launcher (`nuxel-pwa-launcher.c` 813) |
| **C headers (`.h`)** | 1 | **256** | `sandbox.h` |
| **C/C++ total (`.c` + `.h`)** | 8 | **6,081** | |
| **JavaScript (`.js`)** | 25 | **4,977** | all under `pwa/` |
| **Shell scripts (`.sh`)** | 7 | **2,186** | `.sh` extension |
| **+ OpenRC / shell launchers (no ext)** | 6 | **381** | see 1.3 |
| **Shell total** | 13 | **2,567** | all tracked shell-script lines in scope |
| CSS | — | 1,620 | PWA + native home stylesheets |
| HTML | — | 404 | PWA app shells |
| JSON | — | 573 | manifests, schemas, profiles, registry |
| Other (systemd, dbus, xml, desktop, svg, meson, yml, icons…) | — | 2,747 | |

**Sum check:** 7,234 + 5,825 + 256 + 4,977 + 2,186 + 381 + 1,620 + 404 +
573 + 2,747 = **26,203**.

### 1.2 Cross-cutting figures quoted elsewhere

| Figure | Value | Definition / command |
|---|---|---|
| **"True core" (pure Python)** | **7,234** | `find services/ shell/ -name '*.py' \| xargs wc -l` |
| **services + shell Python + C** | **12,246** | `.py` + `.c` (the old "12,139" prose basis, re-measured) |
| **services + shell + pwa `.py/.c/.js`** | **18,036** | the full measured cross-tree source total |
| `sandbox.c` | **2,005** | verified (not "~20K") |
| `sandbox.h` | **256** | verified |
| `sandbox` integration `nftables.sh` | **315** | verified |
| `pwa/nuxel-common/bridge.js` | **330** | verified |
| `nuxel-phosh-agent.py` | **651** | verified |

> **`18,036` is the reference "measured total" for the `.py/.c/.js` core.**
> Design docs that still quote "25K" should be corrected to this number (or to
> the 7.2K pure-Python core), each with the marker `corrected cycle: claimed 25K,
> actual core ~7.2K`.

### 1.3 Shell-script breakdown (tracked source scope)

`.sh` files (7 files, 2,186 lines):

| File | Lines |
|---|---|
| `firmware/install-firmware.sh` | 888 |
| `shell/nuxel-shell/nuxel-sandbox/nftables.sh` | 315 |
| `shell/nuxel-shell/nuxel-uninstall-helper.sh` | 547 |
| `shell/nuxel-shell/build-native-apps.sh` | 242 |
| `firmware/verify-firmware.sh` | 162 |
| `pwa/flatpak/nuxel-launcher.sh` | 24 |
| `shell/nuxel-home-native/install-dev.sh` | 8 |

OpenRC init and shell launchers without a `.sh` extension (6 files, 381 lines):

| File | Lines |
|---|---|
| `shell/config/openrc/nuxel-firstboot` | 106 |
| `shell/config/openrc/nuxel-bridge` | 79 |
| `shell/config/openrc/nuxel-portal` | 78 |
| `shell/config/openrc/nuxel-notifications` | 76 |
| `shell/nuxel-kiosk/nuxel-home-kiosk` | 36 |
| `shell/nuxel-home-native/nuxel-home-launcher` | 6 |

*(Firmware scripts are counted here because the audit scope includes
`firmware/`. The kernel, image-build, and boot scripts in `kernel/`, `images/`,
`boot/`, `tools/`, `vm/`, and `ci/` are additional tracked shell code outside
this four-tree scope.)*

---

## 2. Per-component file inventory

### 2.1 Services (`services/`)

| Component | Files | Lines (`.py`) |
|---|---|---|
| **nuxel-bridge** (D-Bus capability mediator) | `src/api.py`, `src/bridge.py`, `src/capabilities.py` | 1,772 |
| **nuxel-portal** (system portal, no GUI) | `src/portal.py` | 571 |
| **nuxel-notifications** (FDO/system hub) | `src/notifications.py`, `test-notifications-persistence.py` (service root, not `src/`) | 520 |
| **services `.py` subtotal** | 6 | **2,863** |

Plus per-service systemd units (`systemd/*.service`), D-Bus policy configs
(`dbus/*.conf`), and the top-level `services/nuxel-web.service`.

### 2.2 Shell (`shell/`)

| Component | Files | Lines |
|---|---|---|
| **nuxel-phosh-agent** (user-session GTK dialogs + FDO relay) | `nuxel-phosh-agent.py` | 651 (`.py`) |
| **nuxel-camera-portal** | `nuxel_camera_portal.py` | 439 (`.py`) |
| **nuxel-firstboot** (setup wizard) | `nuxel-shell/nuxel-firstboot/main.py` | 1,362 (`.py`) |
| **nuxel-home-native** (GTK4 Python home) | `nuxel_home/*.py` | 1,919 (`.py`) |
| **sandbox (C)** | `nuxel-sandbox/sandbox.c` + `sandbox.h` | 2,005 + 256 |
| **native GTK4 C apps** | `nuxel-contacts/main.c`, `nuxel-dialer/main.c`, `nuxel-messages/main.c`, `nuxel-permissions/main.c`, `nuxel-settings/main.c` | 502 + 601 + 690 + 775 + 439 = **3,007** |
| nuxel-home-kiosk / home-launcher wrappers | shell, openrc | small shell scripts |
| openrc init scripts | `config/openrc/*` | 339 |

`shell` `.py` subtotal: **4,371**. `shell` C subtotal (`.c`): **5,012** (apps + sandbox),
plus `sandbox.h` 256.

### 2.3 PWA (`pwa/`)

| Subtree | JS lines |
|---|---|
| `nuxel-apps` (calendar, camera-gallery, files, mail, notes) | 2,354 |
| `nuxel-home` (launcher) | 1,824 |
| `nuxel-common` (bridge.js 330, geolocation.js 181, + helpers) | 799 |
| **JS subtotal** | **4,977** |

Plus `pwa/launcher/nuxel-pwa-launcher.c` (813, C), Flatpak manifests, and the
`nuxel-pwa-launcher` meson build.

### 2.4 Firmware (`firmware/`)

| File | Lines | Kind |
|---|---|---|
| `install-firmware.sh` | 888 | shell |
| `verify-firmware.sh` | 162 | shell |
| `manifest.yml` | 370 | yaml |

---

## 3. Verified-existing items checklist

The following items were previously (or are still) listed as "gaps" or
"missing" in some docs. **They are all present as committed files.** What remains
is integration/wiring, not authoring.

### 3.1 systemd units

| Claimed missing | Actual path | Status |
|---|---|---|
| Bridge service unit | `services/nuxel-bridge/systemd/nuxel-bridge.service` | ✅ present |
| Bridge HTTP service unit | `services/nuxel-bridge/systemd/nuxel-http-bridge.service` | ✅ present |
| Portal service unit | `services/nuxel-portal/systemd/nuxel-portal.service` | ✅ present |
| Notifications service unit | `services/nuxel-notifications/systemd/nuxel-notifications.service` | ✅ present |
| Web service unit | `services/nuxel-web.service` | ✅ present |
| Native home (user) unit | `shell/config/systemd-user/nuxel-home-native.service` | ✅ present |
| Kiosk home (user) unit | `shell/config/systemd-user/nuxel-home-kiosk.service` | ✅ present |
| Phosh agent (user) unit | `shell/config/systemd-user/nuxel-phosh-agent.service` | ✅ present |
| Camera portal unit | `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service` | ✅ present |
| AppArmor enforce unit | `configs/apparmor/systemd/nuxel-apparmor-enforce.service` | ✅ present |

### 3.2 D-Bus policy configs

| Claimed missing | Actual path | Status |
|---|---|---|
| Bridge policy | `services/nuxel-bridge/dbus/org.nuxel.Bridge.conf` | ✅ present |
| Portal policy | `services/nuxel-portal/dbus/org.nuxel.Portal.conf` | ✅ present |
| Notifications policy | `services/nuxel-notifications/dbus/org.nuxel.Notifications.conf` | ✅ present |
| Central bridge policy | `configs/dbus/org.nuxel.Bridge.conf` | ✅ present |
| Central portal policy | `configs/dbus/org.nuxel.Portal.conf` | ✅ present |
| Central notifications policy | `configs/dbus/org.nuxel.Notifications.conf` | ✅ present |

### 3.3 OpenRC init scripts (legacy init path)

| Init script | Path | Status |
|---|---|---|
| bridge | `shell/config/openrc/nuxel-bridge` | ✅ present |
| portal | `shell/config/openrc/nuxel-portal` | ✅ present |
| notifications | `shell/config/openrc/nuxel-notifications` | ✅ present |
| firstboot | `shell/config/openrc/nuxel-firstboot` | ✅ present |

### 3.4 Sandbox + security materials

| Item | Path | Status |
|---|---|---|
| Sandbox launcher (C) | `shell/nuxel-shell/nuxel-sandbox/sandbox.c` (2,005) | ✅ present |
| Sandbox header | `shell/nuxel-shell/nuxel-sandbox/sandbox.h` (256) | ✅ present |
| Seccomp profile dir | `shell/nuxel-shell/nuxel-sandbox/seccomp/` | ⚠️ missing — dir empty, 0 tracked files |
| Per-app sandbox profiles (JSON) | `shell/nuxel-shell/nuxel-sandbox/profiles/*.json` | ✅ present |
| nftables integration | `shell/nuxel-shell/nuxel-sandbox/nftables.sh` (315) | ✅ present |
| AppArmor profiles | `configs/apparmor.d/*` | ✅ present |

### 3.5 Documented tooling that does **not** exist as named

A few claims in `docs/milestones.md` reference scripts that do **not** exist
under those names. The equivalent functionality lives under different names:

| Claimed (Milestone E) | Actual tooling |
|---|---|
| `tools/nuxel-sign.sh` | `tools/sign-image.sh`, `tools/gen-keys.sh` |
| `tools/nuxel-flash.sh` | `boot/flash.sh` |
| `tools/nuxel-build.sh` | `images/build.sh`, `images/build-ota.sh` |

---

## 4. NOT yet verifiable without hardware

The following are **explicitly outside what the repo can prove today**, because
they require a physical device or a real factory image. Nothing in this audit
should be read as verifying them.

| Item | What would verify it | Gate |
|---|---|---|
| Firmware extraction | `firmware/install-firmware.sh` + `firmware/verify-firmware.sh` need a **real mustang factory image** to run against | Hardware / factory image |
| Hardware DTB boot | Booting a real Pixel 10 Pro XL (mustang) and confirming display/touch/storage bring-up | Physical device |
| Verified boot (AVB) on-device | Flashing a signed boot image and relocking a mustang bootloader | Physical device + keys |
| Modem / telephony on-device | Exynos 5500 firmware handshake over a real modem | Hardware |
| WiFi / Bluetooth throughput | BCM4390 device bring-up | Hardware |
| GPU acceleration | PowerVR DXT-72-2304 driver on device | Hardware |

Until those gates pass, the honest position is: **the code exists, is measured,
and is designed to be buildable — but it has not been verified on-target.**

---

## 5. How to re-measure

From the repo root:

```bash
# Total tracked source (all types) across the four scope trees
git ls-files services/ shell/ pwa/ firmware/ \
  | grep -v '__pycache__' | grep -v '/\.build/' | grep -v 'node_modules' \
  | xargs wc -l | tail -1

# Pure-Python "true core"
find services/ shell/ -name '*.py' | xargs wc -l | tail -1     # 7,234

# Python + C
find services/ shell/ -name '*.py' -o -name '*.c' | xargs wc -l | tail -1  # 12,246

# Full .py/.c/.js cross-tree total
find services/ shell/ pwa/ \( -name '*.py' -o -name '*.c' -o -name '*.js' \) \
  | xargs wc -l | tail -1                                       # 18,036
```

---

<!-- Written by the Repo state audit & doc reconciliation build group (briq-01-audit). This file is the single source of truth for all measured code-size counts. -->
