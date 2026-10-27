# NUXEL-28000 — Tri-Link Applications entries + unlock-to-Home fix

Date: 2026-10-27 (Europe/Amsterdam)  
Host: `dextronux` (Fedora 43 x86_64)  
Target: Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
Kernel: Samsung-derived Linux **4.14.253** (unchanged; nothing flashed/repartitioned)
Boot id during verification: `a269e14b-2ccd-4f0a-bbeb-088e84daa5a3`

## Status matrix

| Item | Verdict | Evidence |
|---|---|---|
| Boot → lockscreen → successful unlock → Home | **PASS (physical)** | `/run/nuxel-home.state`: `lockscreen-controller ... boot`, `unlock:home reason=unlock`, `home:complete`; Home screenshot dock templates match Settings 0.915 / Terminal 0.921 |
| Three console entries registered once | **PASS (offline + physical registry)** | `tests/a80/test_tri_link_console.py`; device registry version 6 reports each ID exactly once |
| Serial Live Console | **PASS (physical)** | Serial used for the staged deploy and every readback; lock stayed exclusive; no second serial client |
| Wi-Fi SSH Console | **PASS (physical)** | Pinned Ed25519 host key, public-key auth, Bash, remote rc=7 preserved, 44-byte put/get SHA-256 round trip |
| USB SSH Console | **BLOCKED_KERNEL_PANIC (honest)** | API/UI report the NUXEL-26000 `ncm_free_inst` panic evidence; no USB network interface; no fake connection |
| Applications launch handlers | **PASS (physical launch by registry ID)** | `app:launch id=org.nuxel.LiveConsole name=Serial Live Console`; `...USBSSHConsole name=USB SSH Console`; `...WiFiSSHConsole name=Wi-Fi SSH Console` |
| Existing Wi-Fi / web / browser asset / charging / serial | **PASS (physical smoke)** | `wlan0 10.20.30.16/24`; home/browser/console pages HTTP 200; external power true, battery 100%; serial and console indicators active |
| Visual verification of lockscreen artwork/animation and icon grid layout | **NOT MEASURED unattended** | No synthetic touch injection was used for visual acceptance; launch-by-registry and compositor screenshots are the physical evidence |

## 1. Root cause: unlock revealed the stale launcher route

`NuxelHome._unlock()` hid `#lockscreen` and re-enabled the nav dock, but never reset the launcher. The canonical Home reset exists in `Launcher.mainDesktop()` and was only called by the Home button. Therefore:

- an Applications drawer that was open before locking remained underneath the overlay;
- a manifest/deep-link `#app=<id>` could build an app/PWA surface while locked, because `_openPwa()` / `_launchNative()` had no lock gate;
- hiding the lockscreen revealed the stale route instead of Home.

The fix is in `pwa/nuxel-home/js/app.js`:

- `_unlock()` now calls `_enterHomeAfterUnlock()` immediately and synchronously after the successful lock-state transition;
- `_enterHomeAfterUnlock()` clears a stale `#app=` history route, then calls the existing `home()` path, which dismisses overlays, backgrounds the foreground app, and calls `launcher.mainDesktop()` (desktop 1, drawer closed);
- `_openPwa()` and `_launchNative()` ignore launches while locked;
- failed/rejected unlocks never reach the Home transition.

## 2. Three Applications entries

| App ID | Label | Icon asset | Handler |
|---|---|---|---|
| `org.nuxel.LiveConsole` | **Serial Live Console** | `/assets/nuxel-applications-icon-pack/05-05_live-console.png` | `/pwa/nuxel-apps/console/index.html` (`startTriLinkConsole('serial')`) |
| `org.nuxel.USBSSHConsole` | **USB SSH Console** | `/assets/nuxel-applications-icon-pack/06-05_usb-connection.png` | `/pwa/nuxel-apps/console-usb/index.html` (`startTriLinkConsole('usb')`) |
| `org.nuxel.WiFiSSHConsole` | **Wi-Fi SSH Console** | `/assets/nuxel-quicksettings-icon-pack/01-wifi.png` | `/pwa/nuxel-apps/console-wifi/index.html` (`startTriLinkConsole('wifi')`) |

Discovery path: `pwa/nuxel-common/app-registry.json` → `pwa/nuxel-home/js/apps.js` (`NUXEL_APPS`, `NUXEL_APP_ICON_ASSETS`) → launcher grid/drawer and `appRegistry.launchApp()`. The native consumer `shell/nuxel-home-native/nuxel_home/app_registry.json` is regenerated from the same canonical registry. Registry revision is **6**.

The three entries remain present even when unavailable. Each page reads `system.tri-link` from the bridge and renders its own state; there is no shared "pretend connected" fallback.

## 3. Transport implementation

### Serial Live Console

- Reuses the existing host-side `scripts/s10plus-debug-pack/nuxel-live.sh` framed console and its exclusive serial lock.
- The phone view reports the real CDC-ACM function, `ttyGS0`, UDC state and lock state.
- It never opens the serial port and never starts a second reader/writer. The host command is displayed for an explicit operator action.

### Wi-Fi SSH Console

- Real host-side OpenSSH session into the phone, verified this cycle:
  - pinned Ed25519 host key `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`;
  - public-key-only authentication (`passwordauthentication no`, `kbdinteractiveauthentication no`);
  - `AllowUsers` restricted to the WLAN/USB/loopback CIDRs;
  - Bash remote shell; remote exit status preserved (`rc=7`);
  - staged 44-byte put/get with identical SHA-256 `6edc5c58…`.
- The phone view discovers the active IPv4 interface dynamically from sysfs + `SIOCGIFADDR` (no guessed IP, no `ip` dependency) and shows the exact host command. It does **not** store a private key on the phone, per the specification.

### USB SSH Console

- Capability audit: `CONFIG_USB_CONFIGFS=y`, NCM/RNDIS compiled, but the live gadget exposes only `acm.usb0`; no `usb0`/`ncm0`/`rndis0` host interface exists.
- NUXEL-26000 physically proved that NCM teardown panics this 4.14.253 kernel (`ncm_free_inst`; pstore `Panic#2`). The app and API therefore report **BLOCKED_KERNEL_PANIC** and link to `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`.
- No gadget was created, no UDC was rebound, and no SSH readiness is claimed.

## 4. Changed files (principal)

- `pwa/nuxel-home/js/app.js` — unlock → Home transition, locked launch gate.
- `pwa/nuxel-home/js/apps.js`, `pwa/nuxel-common/app-registry.json`, `shell/nuxel-home-native/nuxel_home/app_registry.json` — three distinct entries, icons, descriptions and handlers.
- `pwa/nuxel-home/index.html`, `manifest.json`, `sw.js` — registry revision 6, cache-buster v47-a80-tri-link, shortcuts.
- `pwa/nuxel-common/bridge.js` — `system.tri-link` never receives a fake success in mock mode.
- `pwa/nuxel-apps/console/**`, `pwa/nuxel-apps/console-usb/**`, `pwa/nuxel-apps/console-wifi/**` — shared status UX + three explicit transport surfaces.
- `services/nuxel-bridge/src/tri_link_status.py` — read-only phone-side transport truth.
- `services/nuxel-bridge/src/api.py` — `/api/v1/system/tri-link` and `system.tri-link` RPC.
- `tools/beta/live/nuxel-28000-tri-link-ui-manifest.json` — staged/atomic/rollback deployment plan.
- `tests/a80/**` — 22 focused tests for registration, status truth, API and unlock/Home.
- `tools/s10plus/a45/test-lockscreen-unlock.js` — real state-machine coverage for unlock→Home, drawer reset, locked deep-link refusal and failed unlock.

## 5. Deployment

Evidence: `docs/beta-finalization/live/evidence/n28000-tri-link-apply/`,
`...-apply-r2/`, `...-apply-r3/`.

- Final apply: `DEPLOYED_UNVERIFIED` → post-checks passed, transaction `COMPLETE`.
- Final changed module: `tri_link_status.py`; earlier apply installed the 24 PWA assets and `api.py`.
- No kernel/partition/DTB/modem/EFS write occurred.
- `nuxel-web.service` is inactive on this image (disabled); the live PWA server is the `python3 -m http.server 8000` child of `nuxel-pwa-host` in `nuxel-wayland`. The first deploy manifest unnecessarily attempted to restart `nuxel-web`, which failed to bind the already-owned port. Its failed state was cleared, and the manifest was corrected to use a declared reload rather than a service restart. The PWA never stopped serving.
- Final services: `nuxel-wayland active`, `nuxel-http-bridge active`, `sshd active`.

## 6. Tests

Host-only (not phone evidence):

```text
python3 -m pytest tests/a80 tools/beta/live/tests/test_tri_link.py -q
# 73 passed

node tools/s10plus/a45/test-lockscreen-unlock.js
# ALL PASS (56/56)

node tools/s10plus/a33/tests/launcher-registry-test.js
# passed

python3 tools/s10plus/a33/tests/test-app-infrastructure.py
# all checks passed

python3 services/nuxel-bridge/test-system-indicators.py
# ALL PASS

python3 services/nuxel-bridge/test-{launcher-activation,camera-bridge,wifi-activation,bluetooth-location,grant-store,media-store}.py
# all passed

python3 -m pytest tools/beta/live/tests/test_live_lib.py \
                 tools/beta/live/tests/test_live_reload_and_transport.py -q
# 79 passed
```

Known pre-existing/blocked host checks (not caused by this change):

- `verify-app-registry.py`: 2 remaining launcher/canonical drift findings (`BrowserNative`/`CameraNative` missing from `apps.js`; nine older launcher extras absent from canonical). The three new console entries are exact and covered by `tests/a80`.
- `test-boot-surface-contract.py`: 2 executable-bit failures (runner/build script modes).
- `test-wifi-diag.py`: 5 missing-fixture-verdict failures.
- `test-console-protocol.py`: expects a different legacy four-tab console app implementation; the app tree was absent before this cycle. The new status console is covered by `tests/a80`.
- `test-web-server.py`: blocked by the repository file not being executable for its direct Popen.
- `tools/s10plus/a58/test-browser.py`: blocked because Playwright is not installed on the host.

## 7. Physical S10+ evidence

All under `docs/beta-finalization/live/evidence/n28000-tri-link-ui/`:

- `n28000-unlock-launch.log` — boot lockscreen, `unlock:home`, `home:complete`, then each correct `app:launch` label.
- `home-after-unlock.png` — 720×1520 compositor capture; dock template match proves Home visible.
- `serial-live-console.png`, `usb-ssh-console.png`, `wifi-ssh-console.png` — distinct captures after launching each registry ID.
- `n28000-tri-link-status.json` — Wi-Fi `AVAILABLE` at `nuxel@10.20.30.16:22`; serial `AVAILABLE`; USB `BLOCKED_KERNEL_PANIC`.
- `regression-proof.txt` — services, HTTP 200s, Wi-Fi address, indicators, sshd policy, kernel/boot id.
- `wifi-ssh-proof.txt` — real shell exit 7 and identical put/get SHA-256.
- `device-registry-counts.txt` — every console ID exactly once on the device.
- `screenshot-analysis.txt`, `SHA256SUMS`.

Physical acceptance:

- Boot lockscreen: **PASS** (state machine log).
- Unlock → Home: **PASS**.
- Repeat after a real reboot with Applications selected: **NOT RUN** (no disruptive reboot; reload-launcher exercised the same boot-lock path).
- Three Apps entries once: **PASS** (registry + launch).
- Serial console: **PASS**.
- Wi-Fi SSH real shell/auth: **PASS**.
- USB SSH unsupported state: **PASS** (honest blocker).
- USB unplug/reconnect and lockscreen artwork/animation visual acceptance: **NOT MEASURED** (no synthetic touch or deliberate USB detach in this cycle).
- Wi-Fi/DNS/TLS/browser page/charging/serial smoke: **PASS** as listed above.

## 8. Rollback

Pre-NUXEL-28000 copies are per-transaction:

```sh
# Static PWA files (served immediately by the running session fallback; no restart needed)
for f in \
  /usr/share/nuxel/pwa/nuxel-home/index.html \
  /usr/share/nuxel/pwa/nuxel-home/manifest.json \
  /usr/share/nuxel/pwa/nuxel-home/sw.js \
  /usr/share/nuxel/pwa/nuxel-home/js/app.js \
  /usr/share/nuxel/pwa/nuxel-home/js/apps.js \
  /usr/share/nuxel/pwa/nuxel-common/app-registry.json \
  /usr/share/nuxel/pwa/nuxel-common/bridge.js; do
  install -m 0644 "$f.nuxel-rollback.pre-n28000-tri-link-apply" "$f"
done

# Bridge API
install -m 0644 \
  /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback.pre-n28000-tri-link-apply \
  /usr/lib/nuxel/nuxel-bridge/api.py
systemctl restart nuxel-http-bridge
```

`tri_link_status.py` may be left in place (then unused) or removed with
`python3 -c "import os; os.unlink('/usr/lib/nuxel/nuxel-bridge/tri_link_status.py')"`.
The three PWA directories may likewise be left unregistered; remove them only if a
full feature removal is intended. Do **not** start `nuxel-web`; it is not the live
server on this image and cannot bind the already-owned port.

After rollback verify:

```sh
curl -sS http://127.0.0.1:8080/api/v1/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/pwa/nuxel-home/index.html
systemctl is-active nuxel-http-bridge sshd
```

Serial recovery is independent (host-side `/dev/ttyACM0` + exclusive flock).

## 9. Safety confirmation

- No kernel flash, bootloader change, repartition, wipe or factory reset.
- No USB gadget/configfs mutation and no NCM retry.
- No concurrent serial writers; every serial action completed before the next began.
- No private key copied to the phone; SSH host key is pinned; password/KbdInteractive auth remain disabled.
- New console unavailable states never claim “connected”.
