# Nuxel core application inventory — mission area 30

**Build group:** `bg-06-core-phone-apps` (briq-06a-core-app-inventory)
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, kernel 4.14.253 (Samsung vendor),
Fedora 43 ARM64 userspace, systemd PID 1.
**Observed:** 2026-10-16, by repository inspection only. **No handset interaction happened in this
run**, no service was started, nothing was flashed (the NO-FLASHING invariant is absolute).
**Executable form of this document:** `tools/s10plus/a33/verify-app-inventory.py`.

> A directory name is not an application. An icon is not an application. This inventory therefore
> records, for every entry, the **implementation** that exists, the **launch** path, the **capabilities**
> it declares, its **hardware dependencies**, its **offline behaviour**, the **tests** that cover it and
> a **status** that the verifier re-checks against the tree. Where something is absent, it says absent.

## 1. How to re-verify this document (one command)

```sh
tools/s10plus/a33/verify-app-inventory.py                 # every claim vs the tree
tools/s10plus/a33/verify-app-inventory.py --strict        # warnings become failures
tools/s10plus/a33/tests/run-app-tests.sh                  # the whole core-app test set
```

`verify-app-inventory.py` parses the machine-readable block in [Appendix A](#appendix-a--machine-readable-inventory-data)
and fails when

1. an entry misses a mission-area-30 field, or uses a status outside the four honest states;
2. a `present/full` entry does not really have its files (PWA: `index.html` + `manifest.json` + `sw.js`;
   native: `main.c` + desktop entry);
3. a `missing` entry *does* have an implementation on disk (or vice versa);
4. a `tests[]` path does not resolve;
5. a PWA entry's `permissions` disagree with its own manifest's `nuxel.capabilities`, or its `launch`
   URL does not point at its own `index.html`;
6. an app directory with an `index.html` is not in the inventory, or a `pwa/nuxel-apps/<dir>` with no
   implementation is silently absent from the gap table;
7. a gap names a briQ that does not exist in `docs/beta-finalization/workqueue/`, or **this group left
   one of its own gaps open**.

## 2. Status vocabulary used here

| Status | Meaning in this document |
| --- | --- |
| `present/full` | The mission-area-30 surface exists and its offline tests are in place. It is **not** a claim that the hardware path works. |
| `present/partial` | The implementation exists but something real is missing (an asset, an app.json, an unproven hardware path, or another build group's in-flight work). The reason is in the gap table. |
| `missing` | No implementation exists anywhere in this revision. Recorded so the beta never implies the feature. |
| `external` | Implemented by another build group in this cycle; this inventory records its real footprint and its owner. |

Verdict ladders used for the entries: a green offline test can only ever yield `OFFLINE_TESTED`
(or `VERIFIED_IN_VM_ONLY` for the PWA surfaces actually rendered in the UTM VM). Nothing in this
document is `VERIFIED_ON_S10PLUS`, and nothing here was promoted from a unit test.

## 3. Index — every inventoried application

| ID | Name | Category | Type | Path | Status | Owner group |
| --- | --- | --- | --- | --- | --- | --- |
| `nuxel-dialer` | Phone (dialer) | communication | native | `shell/nuxel-shell/nuxel-dialer` | present/partial | bg-06-core-phone-apps |
| `nuxel-messages` | Messages (SMS/MMS) | communication | native | `shell/nuxel-shell/nuxel-messages` | present/partial | bg-06-core-phone-apps |
| `nuxel-contacts` | Contacts | communication | native | `shell/nuxel-shell/nuxel-contacts` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Mail` | Mail | communication | pwa | `pwa/nuxel-apps/mail` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Calendar` | Calendar | productivity | pwa | `pwa/nuxel-apps/calendar` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Notes` | Notes | productivity | pwa | `pwa/nuxel-apps/notes` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Calculator` | Calculator | productivity | pwa | `pwa/nuxel-apps/calculator` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Clock` | Clock, alarms and timers | productivity | pwa | `pwa/nuxel-apps/clock` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Files` | Files (file explorer) | productivity | pwa | `pwa/nuxel-apps/files` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Terminal` | Terminal | productivity/system | pwa | `pwa/nuxel-apps/terminal` | present/full | bg-06-core-phone-apps |
| `nuxel-settings` | Settings | system | pwa | `pwa/nuxel-apps/settings` | present/partial | bg-02 / bg-08 / bg-06 (joint) |
| `nuxel-native-settings` | Native Settings shell app | system | native | `shell/nuxel-shell/nuxel-settings` | present/full | bg-06-core-phone-apps |
| `settings-surface.mobile` | Mobile Settings | system | settings-surface | `pwa/nuxel-apps/settings` | present/partial | bg-03-connectivity-time-audio-buttons |
| `settings-surface.network` | Network Settings | system | settings-surface | `pwa/nuxel-apps/settings` | present/partial | bg-03-connectivity-time-audio-buttons |
| `org.nuxel.Nuxtore` | NuxTore (app store) | system | pwa | `pwa/nuxel-apps/nuxtore` | present/full | bg-07-specialty-apps |
| `nuxel-permissions` | Permissions manager | system | native | `shell/nuxel-shell/nuxel-permissions` | present/full | bg-05-security-permissions |
| `tool.firewall` | Firewall application | system | tool | `tools/s10plus/a33/nuxel-firewall.sh` | present/partial | bg-05-security-permissions |
| `nuxel-devmgmt` | DevMgmt | system | pwa | `pwa/nuxel-apps/devmgmt` | present/full | bg-07-specialty-apps |
| `org.nuxel.LiveConsole` | Live Console | system | pwa | `pwa/nuxel-apps/console` | present/partial | bg-07-specialty-apps |
| `org.nuxel.USBSSHConsole` | USB SSH Console | system | pwa | `pwa/nuxel-apps/console-usb` | present/partial | bg-07-specialty-apps |
| `org.nuxel.WiFiSSHConsole` | Wi-Fi SSH Console | system | pwa | `pwa/nuxel-apps/console-wifi` | present/partial | bg-07-specialty-apps |
| `tool.system-monitor` | System Monitor / Diagnostics | system | tool | `tools/s10plus/a33/nuxelctl` | present/full | bg-06-core-phone-apps |
| `tool.security-audit` | Security auditor | system | tool | `tools/s10plus/a33/nuxel-security-audit.sh` | present/partial | bg-05-security-permissions |
| `nuxel-cleanup` | Safe Cleanup | system | pwa | `pwa/nuxel-apps/cleanup` | present/full | bg-07-specialty-apps |
| `nuxel-rootcontrol` | Root / sudo control | system | pwa | `pwa/nuxel-apps/rootcontrol` | present/full | bg-07-specialty-apps |
| `org.nuxel.Camera` | Camera | media | pwa | `pwa/nuxel-apps/camera-gallery` | present/partial | bg-08-hardware-subsystems |
| `nuxel-camera` | Camera (launcher placeholder entry) | media | placeholder | `pwa/nuxel-apps/camera-gallery` | present/partial | bg-08-hardware-subsystems |
| `org.nuxel.Photos` | Photos / Gallery | media | pwa | `pwa/nuxel-apps/photos` | present/full | bg-06-core-phone-apps |
| `nuxel-media` | Media players (audio + video) | media | pwa | `pwa/nuxel-apps/media` | present/full | bg-07-specialty-apps |
| `org.nuxel.Recorder` | Audio recorder | media | pwa | `pwa/nuxel-apps/recorder` | present/partial | bg-06-core-phone-apps |
| `nuxel-downloader` | Media downloader | media | pwa | `pwa/nuxel-apps/downloader` | present/full | bg-07-specialty-apps |
| `org.nuxel.SnekByte` | SnekByte (game) | game | pwa | `pwa/nuxel-apps/snekbyte` | present/full | bg-07-specialty-apps |
| `org.nuxel.Maps` | Maps (OpenStreetMap, offline-first) | connectivity | pwa | `pwa/nuxel-apps/maps` | present/full | bg-06-core-phone-apps |
| `settings-surface.bluetooth` | Bluetooth | connectivity | settings-surface | `pwa/nuxel-apps/settings` | present/partial | bg-08-hardware-subsystems |
| `settings-surface.vpn` | VPN manager | connectivity | settings-surface | `pwa/nuxel-apps/settings` | present/partial | bg-05-security-permissions |
| `settings-surface.remote` | Remote access / Device Connect | connectivity | settings-surface | `pwa/nuxel-apps/settings` | present/partial | bg-05-security-permissions |
| `placeholder.casting` | Casting | connectivity | placeholder | `pwa/nuxel-apps/casting` | missing | unassigned in this cycle |
| `nuxel-authenticator` | Authenticator (TOTP) | privacy-identity | pwa | `pwa/nuxel-apps/authenticator` | present/full | bg-07-specialty-apps |
| `tool.tor` | Tor / Onion privacy tools | privacy-identity | tool | `shell/nuxel-shell/nuxel-privacy` | present/partial | bg-05-security-permissions |
| `nuxel-penguinterface` | PenguInterface | privacy-identity | pwa | `pwa/nuxel-apps/penguinterface` | present/partial | bg-07-specialty-apps |
| `nuxel-privacy` | Privacy surface (PWA) | privacy-identity | placeholder | `pwa/nuxel-apps/privacy` | missing | bg-05-security-permissions |
| `org.nuxel.Browser` | Browser | connectivity | pwa | `pwa/nuxel-apps/browser` | present/full | bg-06-core-phone-apps |
| `org.nuxel.Weather` | Weather | connectivity | pwa | `pwa/nuxel-apps/weather` | present/full | bg-06-core-phone-apps |
| `tool.keyboard` | Virtual keyboard + keyboard settings | system | tool | `configs/nuxel/keyboard` | present/full | bg-06-core-phone-apps |

## 4. The core set this group owns — detail

Every PWA below is an offline-capable app directory with `index.html`, `css/`, `js/`, `manifest.json`
(`name`, `start_url`, `display`, `icons[]`, `nuxel.capabilities`, `nuxel.bridge_version`), icons and a
service worker with a versioned cache, and every one of them passes

```sh
NUXEL_JSDOM=<node_modules-with-jsdom> tools/s10plus/a33/tests/test-core-apps.py
```

which loads each page **over HTTP in a real DOM engine with no Nuxel host and no network** and asserts:
the expected nodes exist after the app's own scripts ran, the app's documented smoke hook is exposed,
and there are **zero console errors**. That is the VM-worst-case acceptance case, and it is green
(`RESULT: PASS=130 FAIL=0 WARN=0 verdict=OFFLINE_RUNTIME_PASSED`, 2026-10-16).

| ID | Implementation in this repository | Launch | Offline behaviour | Tests |
| --- | --- | --- | --- | --- |
| `org.nuxel.Terminal` | Real local PTY (`forkpty` + `/bin/sh`) owned by `tools/s10plus/a33/nuxel-pwa-host.c`; ↑/↓ history, font size, permanent LOCAL-ONLY notice, in-page fallback key pad | `/pwa/nuxel-apps/terminal/index.html` (or the Bixby button) | local shell only; no remote shell, no forwarded port — and the page says so | `test-core-apps.py` (L1–L4) |
| `org.nuxel.Notes` | Editor + list + pin + offline search + Markdown/JSON export + JSON import + storage report | `/pwa/nuxel-apps/notes/index.html` | localStorage `nuxel-notes`, optional bridge copy | `test-core-apps.py` |
| `org.nuxel.Files` | Browse the PWA-visible tree through the portal: grid, breadcrumb, back, honest read-only state | `/pwa/nuxel-apps/files/index.html` | renders and reports “no grant / no host” instead of failing | `test-core-apps.py` |
| `org.nuxel.Clock` | Clock, world cities, alarms, stopwatch, timer, tied to the Nuxel time/RTC surface | `/pwa/nuxel-apps/clock/index.html` | device clock + local alarms | `test-core-apps.py`, `test-time-rtc.py` |
| `org.nuxel.Calculator` | Basic + scientific pads, keyboard entry, history | `/pwa/nuxel-apps/calculator/index.html` | needs neither network nor storage | `test-core-apps.py` |
| `org.nuxel.Browser` | WebKitGTK browser surface: URL bar, start page, no external service | `/pwa/nuxel-apps/browser/index.html` | runs with no network; navigation failures are reported | `test-core-apps.py` |
| `org.nuxel.Photos` | Album/gallery over the camera-gallery storage with a viewer | `/pwa/nuxel-apps/photos/index.html` | local storage | `test-core-apps.py` |
| `org.nuxel.Recorder` | Recorder that reports its **real** capability (mic provisioning only) | `/pwa/nuxel-apps/recorder/index.html` | local storage; never fakes a capture | `test-core-apps.py` |
| `org.nuxel.Weather` | Manual/offline dataset + forecast chart, no mandatory service | `/pwa/nuxel-apps/weather/index.html` | renders the stored dataset with no network | `test-core-apps.py` |
| `org.nuxel.Maps` | OSM tile cache, offline-first, cache statistics, pins | `/pwa/nuxel-apps/maps/index.html` | cached tiles render with no network | `test-core-apps.py` |
| `org.nuxel.Mail` | Local-first mail store: accounts, compose, queue, import/export | `/pwa/nuxel-apps/mail/index.html` | store/read local; sends are **queued**, never shown as sent | `test-phone-apps.py`, `test-core-apps.py` |

### 4.1 Phone applications (mission area 30 → 17, 20)

`nuxel-dialer`, `nuxel-messages` and `nuxel-contacts` are real GTK4 C applications sharing one data
layer, `shell/nuxel-shell/nuxel-phone-data` (contact store, call log, message threads, number
normalisation, vCard import/export, atomic save, corrupt-store recovery, honest capability model).
The data layer has its own compiled test suite (`shell/nuxel-shell/nuxel-phone-data/run-tests.sh`) and
`tools/s10plus/a33/tests/test-phone-apps.py` additionally proves, offline:

* every `nuxel_phone_*` symbol the apps call is declared in the shared header (the exact link error the
  cross-compile would hit);
* the dialer's capability sentence comes from the **probe**, spells out the no-modem case, records a
  refusal instead of a fake call, and contains no unconditional “Calling/Connected” claim;
* the messages app uses the shared thread model, has a queued-not-sent state for an unavailable
  transport and never claims a sent SMS;
* mail's transport never fabricates a connection state and labels a queued send as queued.

`RESULT: PASS=37 FAIL=0 verdict=OFFLINE_TESTED` (2026-10-16). Calls and SMS on this handset require the
Samsung Shannon LTE modem, which has **no upstream ModemManager plugin** — that is a
`BLOCKED_FIRMWARE` condition, not a UI defect, and the apps say so on screen.

## 5. Gaps, and the briQ that closes each

State `open` means the work is real and unfinished; `by-design` means this group has decided not to do
it and says why (it is not silently dropped); `outside-this-group` means the remainder is a different
build group's deliverable or an owner test.

| Gap | Application | What is missing | Owner | State | Closed by |
| --- | --- | --- | --- | --- | --- |
| `gap-settings-sw` | `nuxel-settings` | no `sw.js`, so the Settings surface cannot be installed offline | bg-02-boot-animation-launcher / bg-08-hardware-subsystems | open | (owner group, same cycle) |
| `gap-registry-mail-calendar-caps` | `org.nuxel.Mail`, `org.nuxel.Calendar` | the canonical registry lists `storage:read`/`storage:write`, which are **not** bridge-enum ids, while the manifests honestly declare `storage:persistent` | bg-04c-app-infrastructure | open | `briq-04c-app-infrastructure` |
| `gap-calendar-appjson` | `org.nuxel.Calendar`, `org.nuxel.Camera` | no `app.json` metadata (every other PWA carries one) | bg-04c-app-infrastructure | open | `briq-04c-app-infrastructure` |
| `gap-camera-read-cap` | `org.nuxel.Camera` | declares `camera:read`, which the bridge enum does not define | bg-08-hardware-subsystems | open | (owner group, same cycle) |
| `gap-terminal-pty-cap` | `org.nuxel.Terminal` | `shell:local-pty` is not a bridge capability: the PTY belongs to the launcher host, not the bridge | bg-06-core-phone-apps | by-design | documented in `pwa/nuxel-common/app-registry.json` (`capability_gaps`) |
| `gap-liveconsole-index` | `org.nuxel.LiveConsole` | the registry serves a tile for an app whose `index.html`/`manifest.json` are not in the tree yet | bg-07-specialty-apps | open | `briq-07a-specialty-apps` |
| `gap-penguinterface` | `nuxel-penguinterface` | icons only; no `index.html` | bg-07-specialty-apps | open | `briq-07a-specialty-apps` |
| `gap-privacy-pwa` | `nuxel-privacy` | icons only; the privacy/permission surface is native + settings-group only | bg-05-security-permissions | open | `briq-05a-permission-manager` |
| `gap-casting` | `placeholder.casting` | no casting application, daemon or protocol surface exists anywhere in this revision (mission area 40) | unassigned in this cycle | open | (needs a dedicated briQ) |
| `gap-modem-plugin` | `nuxel-dialer`, `nuxel-messages` | no upstream ModemManager plugin for the Samsung Shannon LTE modem, so calls/SMS cannot work on this handset | bg-03-connectivity-time-audio-buttons | open | (mission area 26) |
| `gap-camera-placeholder` | `nuxel-camera` | the registry entry is a placeholder with no `/usr/bin/nuxel-camera` binary | bg-08-hardware-subsystems | open | (owner group, same cycle) |
| `gap-recorder-mic` | `org.nuxel.Recorder` | microphone capture is unproven on hardware | bg-08-hardware-subsystems | outside-this-group | owner test `docs/beta-finalization/manual-proof/06-audio.md` |
| `gap-camera-capture` | `org.nuxel.Camera` | real capture is unproven on hardware | bg-08-hardware-subsystems | outside-this-group | owner test `docs/beta-finalization/manual-proof/15-camera.md` |
| `gap-keyboard-vm` | `tool.keyboard` | the on-screen keyboard rising and delivering keys is proven only offline; it needs the VM run and the owner's finger | bg-06-core-phone-apps | outside-this-group | owner test `docs/beta-finalization/manual-proof/20-applications.md` |

**No gap owned by `bg-06-core-phone-apps` is left open.** The two entries owned by this group are
`by-design` (terminal PTY capability) and `outside-this-group` (keyboard VM/owner proof), and both name
exactly what remains.

## 6. What this inventory deliberately does NOT claim

* No entry is `VERIFIED_ON_S10PLUS`. Nothing here touched the handset in this run; a passing unit test
  is `OFFLINE_TESTED` and stays `OFFLINE_TESTED`.
* Hardware paths (camera capture, microphone capture, GNSS fix, speaker output, modem, Bluetooth
  pairing, vibration, flashlight, NFC) are **not** claimed working. Where an app depends on one, the
  inventory says so and points at the manual-proof area that must prove it.
* The status column is not a quality score: `present/full` means “the mission-area-30 surface and its
  offline tests exist”, nothing more.
* The registry (`pwa/nuxel-common/app-registry.json`) remains the canonical *launcher* contract and is
  owned by `bg-04c-app-infrastructure`; where it disagrees with a manifest, this document records the
  disagreement as a gap instead of editing another group's file.

## Appendix A — machine-readable inventory data

<!-- INVENTORY-DATA:BEGIN -->

```json
{
  "apps": [
    {
      "category": "communication",
      "dependencies": [
        "nuxel-phone-data"
      ],
      "hardware": [],
      "id": "nuxel-dialer",
      "implementation": "native C: main.c",
      "launch": "/usr/bin/nuxel-dialer",
      "name": "Phone (dialer)",
      "offline": "local store; no network dependency",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "native",
      "path": "shell/nuxel-shell/nuxel-dialer",
      "permissions": [],
      "source": "shell/nuxel-shell/nuxel-dialer",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-phone-apps.py"
      ],
      "type": "native",
      "version": "0.1.0"
    },
    {
      "category": "communication",
      "dependencies": [
        "nuxel-phone-data"
      ],
      "hardware": [],
      "id": "nuxel-messages",
      "implementation": "native C: main.c",
      "launch": "/usr/bin/nuxel-messages",
      "name": "Messages (SMS/MMS)",
      "offline": "local store; no network dependency",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "native",
      "path": "shell/nuxel-shell/nuxel-messages",
      "permissions": [],
      "source": "shell/nuxel-shell/nuxel-messages",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-phone-apps.py"
      ],
      "type": "native",
      "version": "0.1.0"
    },
    {
      "category": "communication",
      "dependencies": [
        "nuxel-phone-data"
      ],
      "hardware": [],
      "id": "nuxel-contacts",
      "implementation": "native C: main.c",
      "launch": "/usr/bin/nuxel-contacts",
      "name": "Contacts",
      "offline": "local store; no network dependency",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "native",
      "path": "shell/nuxel-shell/nuxel-contacts",
      "permissions": [],
      "source": "shell/nuxel-shell/nuxel-contacts",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-phone-apps.py"
      ],
      "type": "native",
      "version": "0.1.0"
    },
    {
      "category": "communication",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Mail",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/mail/index.html",
      "name": "Mail",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/mail",
      "permissions": [
        "notifications:send",
        "notifications:receive",
        "storage:persistent"
      ],
      "source": "pwa/nuxel-apps/mail",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "productivity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Calendar",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/calendar/index.html",
      "name": "Calendar",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/calendar",
      "permissions": [
        "notifications:send",
        "storage:persistent"
      ],
      "source": "pwa/nuxel-apps/calendar",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "productivity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Notes",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/notes/index.html",
      "name": "Notes",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/notes",
      "permissions": [
        "storage:persistent"
      ],
      "source": "pwa/nuxel-apps/notes",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "productivity",
      "dependencies": [],
      "hardware": [],
      "id": "org.nuxel.Calculator",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/calculator/index.html",
      "name": "Calculator",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/calculator",
      "permissions": [],
      "source": "pwa/nuxel-apps/calculator",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "productivity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Clock",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/clock/index.html",
      "name": "Clock, alarms and timers",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/clock",
      "permissions": [
        "notifications:send",
        "storage:persistent"
      ],
      "source": "pwa/nuxel-apps/clock",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "productivity",
      "dependencies": [],
      "hardware": [],
      "id": "org.nuxel.Files",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/files/index.html",
      "name": "Files (file explorer)",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/files",
      "permissions": [],
      "source": "pwa/nuxel-apps/files",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "productivity/system",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Terminal",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/terminal/index.html",
      "name": "Terminal",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/terminal",
      "permissions": [
        "shell:local-pty"
      ],
      "source": "pwa/nuxel-apps/terminal",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "nuxel-settings",
      "implementation": "PWA: index.html, manifest.json",
      "launch": "/pwa/nuxel-apps/settings/index.html",
      "name": "Settings",
      "offline": "no service worker (see gap)",
      "owner_group": "bg-02 / bg-08 / bg-06 (joint)",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/settings",
      "permissions": [
        "location:read",
        "location:manage"
      ],
      "source": "pwa/nuxel-apps/settings",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "nuxel-native-settings",
      "implementation": "native C: main.c",
      "launch": "/usr/bin/nuxel-settings",
      "name": "Native Settings shell app",
      "offline": "local store; no network dependency",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "native",
      "path": "shell/nuxel-shell/nuxel-settings",
      "permissions": [],
      "source": "shell/nuxel-shell/nuxel-settings",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-phone-apps.py"
      ],
      "type": "native",
      "version": "0.1.0"
    },
    {
      "category": "system",
      "dependencies": [
        "pwa/nuxel-apps/settings"
      ],
      "hardware": [],
      "id": "settings-surface.mobile",
      "implementation": "settings sub-surface inside the Settings PWA",
      "launch": "n/a (sub-surface of /pwa/nuxel-apps/settings/index.html)",
      "name": "Mobile Settings",
      "offline": "inherits the Settings PWA",
      "owner_group": "bg-03-connectivity-time-audio-buttons",
      "package_type": "settings-surface",
      "path": "pwa/nuxel-apps/settings",
      "permissions": [],
      "source": "pwa/nuxel-apps/settings",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "settings-surface",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [
        "pwa/nuxel-apps/settings"
      ],
      "hardware": [],
      "id": "settings-surface.network",
      "implementation": "settings sub-surface inside the Settings PWA",
      "launch": "n/a (sub-surface of /pwa/nuxel-apps/settings/index.html)",
      "name": "Network Settings",
      "offline": "inherits the Settings PWA",
      "owner_group": "bg-03-connectivity-time-audio-buttons",
      "package_type": "settings-surface",
      "path": "pwa/nuxel-apps/settings",
      "permissions": [],
      "source": "pwa/nuxel-apps/settings",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "settings-surface",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Nuxtore",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/nuxtore/index.html",
      "name": "NuxTore (app store)",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/nuxtore",
      "permissions": [],
      "source": "pwa/nuxel-apps/nuxtore",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "nuxel-permissions",
      "implementation": "native C: main.c",
      "launch": "/usr/bin/nuxel-permissions",
      "name": "Permissions manager",
      "offline": "local store; no network dependency",
      "owner_group": "bg-05-security-permissions",
      "package_type": "native",
      "path": "shell/nuxel-shell/nuxel-permissions",
      "permissions": [],
      "source": "shell/nuxel-shell/nuxel-permissions",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-phone-apps.py"
      ],
      "type": "native",
      "version": "0.1.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "tool.firewall",
      "implementation": "repository script/binary",
      "launch": "tools/s10plus/a33/nuxel-firewall.sh",
      "name": "Firewall application",
      "offline": "offline tool",
      "owner_group": "bg-05-security-permissions",
      "package_type": "tool",
      "path": "tools/s10plus/a33/nuxel-firewall.sh",
      "permissions": [],
      "source": "tools/s10plus/a33/nuxel-firewall.sh",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/security-tests/test-firewall.sh"
      ],
      "type": "tool",
      "version": "0.1.0"
    },
    {
      "category": "system",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "nuxel-devmgmt",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/devmgmt/index.html",
      "name": "DevMgmt",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/devmgmt",
      "permissions": [
        "system:inspect"
      ],
      "source": "pwa/nuxel-apps/devmgmt",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "org.nuxel.LiveConsole",
      "implementation": "PWA: ",
      "launch": "n/a (no index.html yet)",
      "name": "Live Console",
      "offline": "no service worker (see gap)",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/console",
      "permissions": [],
      "source": "pwa/nuxel-apps/console",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "tool.system-monitor",
      "implementation": "repository script/binary",
      "launch": "tools/s10plus/a33/nuxelctl",
      "name": "System Monitor / Diagnostics",
      "offline": "offline tool",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "tool",
      "path": "tools/s10plus/a33/nuxelctl",
      "permissions": [],
      "source": "tools/s10plus/a33/nuxelctl",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-service-graph.py"
      ],
      "type": "tool",
      "version": "0.1.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "tool.security-audit",
      "implementation": "repository script/binary",
      "launch": "tools/s10plus/a33/nuxel-security-audit.sh",
      "name": "Security auditor",
      "offline": "offline tool",
      "owner_group": "bg-05-security-permissions",
      "package_type": "tool",
      "path": "tools/s10plus/a33/nuxel-security-audit.sh",
      "permissions": [],
      "source": "tools/s10plus/a33/nuxel-security-audit.sh",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-service-graph.py"
      ],
      "type": "tool",
      "version": "0.1.0"
    },
    {
      "category": "system",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "nuxel-cleanup",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/cleanup/index.html",
      "name": "Safe Cleanup",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/cleanup",
      "permissions": [
        "storage:cleanup"
      ],
      "source": "pwa/nuxel-apps/cleanup",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "nuxel-rootcontrol",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/rootcontrol/index.html",
      "name": "Root / sudo control",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/rootcontrol",
      "permissions": [
        "system:inspect"
      ],
      "source": "pwa/nuxel-apps/rootcontrol",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "media",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Camera",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/camera-gallery/index.html",
      "name": "Camera",
      "offline": "service-worker cache",
      "owner_group": "bg-08-hardware-subsystems",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/camera-gallery",
      "permissions": [
        "camera:capture",
        "camera:preview",
        "camera:read"
      ],
      "source": "pwa/nuxel-apps/camera-gallery",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "media",
      "dependencies": [],
      "hardware": [],
      "id": "nuxel-camera",
      "implementation": "no implementation (documented in the gap table)",
      "launch": "pwa/nuxel-apps/camera-gallery/index.html",
      "name": "Camera (launcher placeholder entry)",
      "offline": "not available",
      "owner_group": "bg-08-hardware-subsystems",
      "package_type": "placeholder",
      "path": "pwa/nuxel-apps/camera-gallery",
      "permissions": [],
      "source": "pwa/nuxel-apps/camera-gallery",
      "status": "present/partial",
      "tests": [],
      "type": "placeholder",
      "version": "n/a"
    },
    {
      "category": "media",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Photos",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/photos/index.html",
      "name": "Photos / Gallery",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/photos",
      "permissions": [
        "storage:persistent"
      ],
      "source": "pwa/nuxel-apps/photos",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "media",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "nuxel-media",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/media/index.html",
      "name": "Media players (audio + video)",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/media",
      "permissions": [
        "audio:playback",
        "media:library"
      ],
      "source": "pwa/nuxel-apps/media",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "media",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Recorder",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/recorder/index.html",
      "name": "Audio recorder",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/recorder",
      "permissions": [
        "storage:persistent"
      ],
      "source": "pwa/nuxel-apps/recorder",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "media",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "nuxel-downloader",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/downloader/index.html",
      "name": "Media downloader",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/downloader",
      "permissions": [
        "download:queue"
      ],
      "source": "pwa/nuxel-apps/downloader",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "game",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.SnekByte",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/snekbyte/index.html",
      "name": "SnekByte (game)",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/snekbyte",
      "permissions": [],
      "source": "pwa/nuxel-apps/snekbyte",
      "status": "present/full",
      "tests": [
        "pwa/nuxel-apps/snekbyte/tests/test-snek-engine.js"
      ],
      "type": "pwa",
      "version": "1.1.0-a58"
    },
    {
      "category": "connectivity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Maps",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/maps/index.html",
      "name": "Maps (OpenStreetMap, offline-first)",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/maps",
      "permissions": [
        "location:read",
        "storage:persistent",
        "network:outbound"
      ],
      "source": "pwa/nuxel-apps/maps",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "connectivity",
      "dependencies": [
        "pwa/nuxel-apps/settings"
      ],
      "hardware": [],
      "id": "settings-surface.bluetooth",
      "implementation": "settings sub-surface inside the Settings PWA",
      "launch": "n/a (sub-surface of /pwa/nuxel-apps/settings/index.html)",
      "name": "Bluetooth",
      "offline": "inherits the Settings PWA",
      "owner_group": "bg-08-hardware-subsystems",
      "package_type": "settings-surface",
      "path": "pwa/nuxel-apps/settings",
      "permissions": [],
      "source": "pwa/nuxel-apps/settings",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "settings-surface",
      "version": "0.0.0"
    },
    {
      "category": "connectivity",
      "dependencies": [
        "pwa/nuxel-apps/settings"
      ],
      "hardware": [],
      "id": "settings-surface.vpn",
      "implementation": "settings sub-surface inside the Settings PWA",
      "launch": "n/a (sub-surface of /pwa/nuxel-apps/settings/index.html)",
      "name": "VPN manager",
      "offline": "inherits the Settings PWA",
      "owner_group": "bg-05-security-permissions",
      "package_type": "settings-surface",
      "path": "pwa/nuxel-apps/settings",
      "permissions": [],
      "source": "pwa/nuxel-apps/settings",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "settings-surface",
      "version": "0.0.0"
    },
    {
      "category": "connectivity",
      "dependencies": [
        "pwa/nuxel-apps/settings"
      ],
      "hardware": [],
      "id": "settings-surface.remote",
      "implementation": "settings sub-surface inside the Settings PWA",
      "launch": "n/a (sub-surface of /pwa/nuxel-apps/settings/index.html)",
      "name": "Remote access / Device Connect",
      "offline": "inherits the Settings PWA",
      "owner_group": "bg-05-security-permissions",
      "package_type": "settings-surface",
      "path": "pwa/nuxel-apps/settings",
      "permissions": [],
      "source": "pwa/nuxel-apps/settings",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "settings-surface",
      "version": "0.0.0"
    },
    {
      "category": "connectivity",
      "dependencies": [],
      "hardware": [],
      "id": "placeholder.casting",
      "implementation": "no implementation (documented in the gap table)",
      "launch": "n/a (not implemented)",
      "name": "Casting",
      "offline": "not available",
      "owner_group": "unassigned in this cycle",
      "package_type": "placeholder",
      "path": "pwa/nuxel-apps/casting",
      "permissions": [],
      "source": "pwa/nuxel-apps/casting",
      "status": "missing",
      "tests": [],
      "type": "placeholder",
      "version": "n/a"
    },
    {
      "category": "privacy-identity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "nuxel-authenticator",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/authenticator/index.html",
      "name": "Authenticator (TOTP)",
      "offline": "service-worker cache",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/authenticator",
      "permissions": [
        "storage:encrypted"
      ],
      "source": "pwa/nuxel-apps/authenticator",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "privacy-identity",
      "dependencies": [],
      "hardware": [],
      "id": "tool.tor",
      "implementation": "repository configuration tree",
      "launch": "shell/nuxel-shell/nuxel-privacy",
      "name": "Tor / Onion privacy tools",
      "offline": "offline tool",
      "owner_group": "bg-05-security-permissions",
      "package_type": "tool",
      "path": "shell/nuxel-shell/nuxel-privacy",
      "permissions": [],
      "source": "shell/nuxel-shell/nuxel-privacy",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/security-tests/test-vpn-tor.sh"
      ],
      "type": "tool",
      "version": "0.1.0"
    },
    {
      "category": "privacy-identity",
      "dependencies": [],
      "hardware": [],
      "id": "nuxel-penguinterface",
      "implementation": "PWA: ",
      "launch": "n/a (no index.html yet)",
      "name": "PenguInterface",
      "offline": "no service worker (see gap)",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/penguinterface",
      "permissions": [],
      "source": "pwa/nuxel-apps/penguinterface",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "privacy-identity",
      "dependencies": [],
      "hardware": [],
      "id": "nuxel-privacy",
      "implementation": "no implementation (documented in the gap table)",
      "launch": "n/a (not implemented)",
      "name": "Privacy surface (PWA)",
      "offline": "not available",
      "owner_group": "bg-05-security-permissions",
      "package_type": "placeholder",
      "path": "pwa/nuxel-apps/privacy",
      "permissions": [],
      "source": "pwa/nuxel-apps/privacy",
      "status": "missing",
      "tests": [],
      "type": "placeholder",
      "version": "n/a"
    },
    {
      "category": "connectivity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Browser",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/browser/index.html",
      "name": "Browser",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/browser",
      "permissions": [
        "network:outbound"
      ],
      "source": "pwa/nuxel-apps/browser",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "connectivity",
      "dependencies": [
        "nuxel-bridge"
      ],
      "hardware": [],
      "id": "org.nuxel.Weather",
      "implementation": "PWA: index.html, manifest.json, sw.js",
      "launch": "/pwa/nuxel-apps/weather/index.html",
      "name": "Weather",
      "offline": "service-worker cache",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/weather",
      "permissions": [
        "storage:persistent",
        "network:outbound"
      ],
      "source": "pwa/nuxel-apps/weather",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "tool.keyboard",
      "implementation": "repository configuration tree",
      "launch": "configs/nuxel/keyboard",
      "name": "Virtual keyboard + keyboard settings",
      "offline": "offline tool",
      "owner_group": "bg-06-core-phone-apps",
      "package_type": "tool",
      "path": "configs/nuxel/keyboard",
      "permissions": [],
      "source": "configs/nuxel/keyboard",
      "status": "present/full",
      "tests": [
        "tools/s10plus/a33/tests/test-virtual-keyboard.py"
      ],
      "type": "tool",
      "version": "0.1.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "org.nuxel.USBSSHConsole",
      "implementation": "PWA: index.html, manifest.json",
      "launch": "/pwa/nuxel-apps/console-usb/index.html",
      "name": "USB SSH Console",
      "offline": "no service worker",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/console-usb",
      "permissions": [],
      "source": "pwa/nuxel-apps/console-usb",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    },
    {
      "category": "system",
      "dependencies": [],
      "hardware": [],
      "id": "org.nuxel.WiFiSSHConsole",
      "implementation": "PWA: index.html, manifest.json",
      "launch": "/pwa/nuxel-apps/console-wifi/index.html",
      "name": "Wi-Fi SSH Console",
      "offline": "no service worker",
      "owner_group": "bg-07-specialty-apps",
      "package_type": "pwa",
      "path": "pwa/nuxel-apps/console-wifi",
      "permissions": [],
      "source": "pwa/nuxel-apps/console-wifi",
      "status": "present/partial",
      "tests": [
        "tools/s10plus/a33/tests/test-core-apps.py"
      ],
      "type": "pwa",
      "version": "0.0.0"
    }
  ],
  "gaps": [
    {
      "app": "nuxel-settings",
      "id": "gap-settings-sw",
      "missing": "no `sw.js`, so the Settings surface cannot be installed offline",
      "owner_group": "bg-02-boot-animation-launcher / bg-08-hardware-subsystems",
      "state": "open"
    },
    {
      "app": "org.nuxel.Mail`, `org.nuxel.Calendar",
      "closed_by_briq": "briq-04c-app-infrastructure",
      "id": "gap-registry-mail-calendar-caps",
      "missing": "the canonical registry lists `storage:read`/`storage:write`, which are **not** bridge-enum ids, while the manifests honestly declare `storage:persistent`",
      "owner_group": "bg-04c-app-infrastructure",
      "state": "open"
    },
    {
      "app": "org.nuxel.Calendar`, `org.nuxel.Camera",
      "closed_by_briq": "briq-04c-app-infrastructure",
      "id": "gap-calendar-appjson",
      "missing": "no `app.json` metadata (every other PWA carries one)",
      "owner_group": "bg-04c-app-infrastructure",
      "state": "open"
    },
    {
      "app": "org.nuxel.Camera",
      "id": "gap-camera-read-cap",
      "missing": "declares `camera:read`, which the bridge enum does not define",
      "owner_group": "bg-08-hardware-subsystems",
      "state": "open"
    },
    {
      "app": "org.nuxel.Terminal",
      "id": "gap-terminal-pty-cap",
      "missing": "`shell:local-pty` is not a bridge capability: the PTY belongs to the launcher host, not the bridge",
      "owner_group": "bg-06-core-phone-apps",
      "state": "by-design"
    },
    {
      "app": "org.nuxel.LiveConsole",
      "closed_by_briq": "briq-07e-live-console-app",
      "id": "gap-liveconsole-index",
      "missing": "the registry serves a tile for an app whose `index.html`/`manifest.json` are not in the tree yet",
      "owner_group": "bg-07-specialty-apps",
      "state": "open"
    },
    {
      "app": "nuxel-penguinterface",
      "closed_by_briq": "briq-07f-penguinterface",
      "id": "gap-penguinterface",
      "missing": "icons only; no `index.html`",
      "owner_group": "bg-07-specialty-apps",
      "state": "open"
    },
    {
      "app": "nuxel-privacy",
      "closed_by_briq": "briq-05a-permission-manager",
      "id": "gap-privacy-pwa",
      "missing": "icons only; the privacy/permission surface is native + settings-group only",
      "owner_group": "bg-05-security-permissions",
      "state": "open"
    },
    {
      "app": "placeholder.casting",
      "id": "gap-casting",
      "missing": "no casting application, daemon or protocol surface exists anywhere in this revision (mission area 40)",
      "owner_group": "unassigned in this cycle",
      "state": "open"
    },
    {
      "app": "nuxel-dialer`, `nuxel-messages",
      "id": "gap-modem-plugin",
      "missing": "no upstream ModemManager plugin for the Samsung Shannon LTE modem, so calls/SMS cannot work on this handset",
      "owner_group": "bg-03-connectivity-time-audio-buttons",
      "state": "open"
    },
    {
      "app": "nuxel-camera",
      "id": "gap-camera-placeholder",
      "missing": "the registry entry is a placeholder with no `/usr/bin/nuxel-camera` binary",
      "owner_group": "bg-08-hardware-subsystems",
      "state": "open"
    },
    {
      "app": "org.nuxel.Recorder",
      "id": "gap-recorder-mic",
      "missing": "microphone capture is unproven on hardware",
      "owner_group": "bg-08-hardware-subsystems",
      "state": "outside-this-group"
    },
    {
      "app": "org.nuxel.Camera",
      "id": "gap-camera-capture",
      "missing": "real capture is unproven on hardware",
      "owner_group": "bg-08-hardware-subsystems",
      "state": "outside-this-group"
    },
    {
      "app": "tool.keyboard",
      "id": "gap-keyboard-vm",
      "missing": "the on-screen keyboard rising and delivering keys is proven only offline; it needs the VM run and the owner's finger",
      "owner_group": "bg-06-core-phone-apps",
      "state": "outside-this-group"
    }
  ],
  "generated_from": "docs/beta-finalization/apps/APP-INVENTORY.md sections 3 and 5",
  "schema": "nuxel.app-inventory/1"
}
```

<!-- INVENTORY-DATA:END -->
