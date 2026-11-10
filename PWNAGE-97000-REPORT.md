# PWNAGE-97000 — NUXEL FILE HANDLERS / SYSTEM FILE PICKER

**Version:** `v0.8.2-beta`  
**Device:** Samsung Galaxy S10+ (`beyond2lte`), Fedora 43 ARM64, Phoc/Wayland  
**Live host:** `root@10.20.30.16`  
**Evidence root:** `docs/pwnage-97000/evidence/20261108T233433Z/`  
**Status:** general portal path **PASS**; Settings File Handlers **PASS**; Flatpak sandbox dispatch + document grant **PASS**; physical Electron/Qt preview **BLOCKED** by the installed zypak/Chromium inner-sandbox spawn path (no `--no-sandbox` workaround used).

---

## 1. Executive result

Nuxel now has a real XDG Desktop Portal `FileChooser` frontend/backend path, selected through a valid `.portal` descriptor and `/etc/xdg-desktop-portal/portals.conf`. The backend is the separate `org.freedesktop.impl.portal.desktop.nuxel` service. The private hardware-permission broker `org.nuxel.Portal` was **not** merged into or replaced by it.

The picker has two sources backed by the real apps:

- **Gallery** — `org.nuxel.Photos`, using `storage.media-list` plus the file-backed camera media store. It returns only real, existing media paths.
- **Files** — `org.nuxel.Files`, using the same `PwaStore` storage provider and approved roots.

`OpenFile`, `SaveFile` and `SaveFiles` were exercised through the **frontend → backend** path with single, multiple, image-filtered, generic-file, directory, Unicode/space-name, save, save-files and cancellation cases.

Sandboxed Flatpak callers were exercised through each app's real `xdg-dbus-proxy`: the portal observed the correct stable app ID and returned a Documents-portal URI under `/run/user/1000/doc/...`. The file content was then read successfully **inside** the same Flatpak sandbox.

The one honest blocker is physical UI preview in Electron/QtWebEngine apps: the installed zypak/Chromium host-spawn path fails with `org.freedesktop.DBus.Error.InvalidArgs: Could not find requesting pid` before a renderer/window is created. The only known workaround is `--no-sandbox`, which this mission forbids. The general portal path and the app-ID/document-grant path remain correct and are covered by harness tests. No success is claimed for the physical preview.

---

## 2. Root cause

### 2.1 Portal frontend/backend were historically absent

The A53 report was accurate for that image: `xdg-desktop-portal` and `xdg-desktop-portal-gtk` were absent. A `portals.conf` file alone could not create a chooser. In the current live S10+ image the frontend and GTK backend are installed, and the Nuxel backend is installed and activated.

### 2.2 `org.nuxel.Portal` is not the FileChooser

`services/nuxel-portal/src/portal.py` remains the private hardware/permission broker. It does not implement `org.freedesktop.portal.FileChooser`. The FileChooser backend is a separate service:

- bus name: `org.freedesktop.impl.portal.desktop.nuxel`
- descriptor: `/usr/share/xdg-desktop-portal/portals/nuxel.portal`
- D-Bus activation: `/usr/share/dbus-1/services/org.freedesktop.impl.portal.desktop.nuxel.service`
- implementation: `/usr/libexec/nuxel/nuxel-portal-chooser`

### 2.3 The app dialogs

Ferdium 7.2.3, Signal Desktop 8.33.0 and ZapZap 7.5.1 (the installed WhatsApp client) are **system Flatpak** apps. Their file choosers use the XDG portal when the Flatpak sandbox is active. WhatsApp was not found as a separate native package; ZapZap is the installed WhatsApp wrapper. Ferdium may additionally host a WhatsApp web service.

The live app IDs are:

| App | Package | App ID | Desktop ID |
|---|---|---|---|
| Ferdium | Flatpak `org.ferdium.Ferdium` 7.2.3 | `org.ferdium.Ferdium` | `org.ferdium.Ferdium.desktop` |
| Signal | Flatpak `org.signal.Signal` 8.33.0 | `org.signal.Signal` | `org.signal.Signal.desktop` |
| WhatsApp (ZapZap) | Flatpak `com.rtosta.zapzap` 7.5.1 | `com.rtosta.zapzap` | `com.rtosta.zapzap.desktop` |
| Gallery | PWA `org.nuxel.Photos` | `org.nuxel.Photos` | `org.nuxel.Photos.desktop` |
| Files | PWA `org.nuxel.Files` | `org.nuxel.Files` | `org.nuxel.Files.desktop` |

---

## 3. Live package/service inventory

Observed on `root@10.20.30.16` after deployment:

```text
xdg-desktop-portal-1.20.4-1.fc43.aarch64
xdg-desktop-portal-gtk-1.15.3-2.fc43.aarch64
xdg-desktop-portal-wlr-0.8.1-1.fc43.aarch64
flatpak-1.16.6-2.fc43.aarch64
zerotier-one-1.16.2-1.fc40.aarch64
wayvnc-0.9.1-3.fc43.aarch64
xrdp-0.10.6.1-3.fc43.aarch64
```

Portal bus owners after restart:

```text
org.freedesktop.portal.Desktop
org.freedesktop.portal.Documents
org.freedesktop.impl.portal.desktop.nuxel
org.freedesktop.impl.portal.desktop.gtk
```

`/usr/bin/nuxel-portal-status` reports:

- frontend available: true
- FileChooser backend config: `nuxel`
- selected backend available: true
- Documents portal available: true
- backend descriptor: `/usr/share/xdg-desktop-portal/portals/nuxel.portal`
- `portals.conf`: `/etc/xdg-desktop-portal/portals.conf`
- desktop identity: `Nuxel`

---

## 4. Portal implementation

### 4.1 Backend contract

`services/nuxel-portal-chooser/src/nuxel_portal_chooser.py` implements:

```text
OpenFile (osssa{sv}) -> ua{sv}
SaveFile (osssa{sv}) -> ua{sv}
SaveFiles (osssa{sv}) -> ua{sv}
org.freedesktop.impl.portal.Request.Close()
```

It preserves:

- request handle and exported Request object;
- calling `app_id` from the portal frontend (not UI input);
- title, parent window marker, filters, `current_filter`;
- `multiple`, `directory`, `current_folder`, `current_file`/`current_name`;
- accept/cancel/error response codes (`0` success, `1` cancel, `2` error);
- request timeout and maximum active requests;
- read/write semantics for save results (`writable=true`).

Selected paths are validated with canonical resolution against approved roots. Symlinks and `..` escapes are rejected. URIs are produced with `Path.as_uri()`/`urllib` encoding, not string concatenation.

### 4.2 Gallery source

Gallery rows come from the real `PwaStore.storage_media_list()` and the file-backed camera media store. Base64-only camera records are excluded; no `file://` URI is fabricated. MIME filters are applied to media rows. Confirmed live result:

```text
file:///home/nuxel/Gallery/nuxel-p97000-test.png
```

### 4.3 Files source

Files uses the same `PwaStore` root and `storage_list_dir()` used by `org.nuxel.Files`. It supports breadcrumbs, navigation, file metadata, filters, multiple selection, directory selection, save-name entry and collision handling.

---

## 5. Settings → File Handlers

Added to `pwa/nuxel-apps/settings/index.html` and `pwa/nuxel-apps/settings/file-handlers-settings.js`:

- tab **File Handlers** next to Apps/Permissions;
- global policy `ask` / `gallery` / `files`;
- per-app overrides for discovered apps (`inherit`, `ask`, `gallery`, `files`);
- persisted schema in `$XDG_CONFIG_HOME/nuxel/file-handlers.json`;
- authoritative MIME defaults written to `$XDG_CONFIG_HOME/mimeapps.list`;
- portal health from the real D-Bus session;
- **Test File Picker** that invokes the real frontend and reports the actual response.

Live settings response:

```json
{
  "schema_version": 1,
  "global_picker_policy": "ask",
  "app_picker_overrides": {
    "com.rtosta.zapzap": "inherit",
    "org.ferdium.Ferdium": "inherit",
    "org.signal.Signal": "inherit"
  },
  "mime_defaults": {}
}
```

Effective seeded MIME defaults include:

```text
image/jpeg  -> org.nuxel.Photos.desktop
image/png   -> org.nuxel.Photos.desktop
image/webp  -> org.nuxel.Photos.desktop
video/mp4   -> org.nuxel.Photos.desktop
inode/directory -> org.nuxel.Files.desktop
```

The Test Picker RPC now returns the real success payload instead of the previous parse-failure wrapper. The client parser was moved into `nuxel_file_handlers.parse_test_picker_output()` and unit-tested.

---

## 6. MIME handlers / desktop integration

`shell/config/org.nuxel.Photos.desktop` declares only supported image/video MIME types. `shell/config/org.nuxel.Files.desktop` declares only `inode/directory;`. `desktop-file-validate` passes for both on the live phone.

MIME defaults are per-user in `/home/nuxel/.config/mimeapps.list`; unrelated entries are preserved.

---

## 7. App integration results

### 7.1 Harness: real frontend → backend dispatch

The test client calls `org.freedesktop.portal.FileChooser` through `org.freedesktop.portal.Desktop`. The backend receives the request and the state records the caller app ID.

| Case | Result | Evidence |
|---|---|---|
| Gallery single, image filter | PASS | `portal/open-flows.txt` |
| Gallery multi, image filter | PASS | `portal/open-flows.txt` |
| Files single, generic file | PASS | `portal/open-flows.txt` |
| Directory selection | PASS | `portal/open-flows.txt` |
| Cancel | PASS (response 1) | `portal/open-flows.txt` |
| SaveFile with Unicode/emoji name | PASS | `portal/save-flows.txt` |
| SaveFiles multi with collision avoidance | PASS | `portal/save-flows.txt` |
| Settings Test Picker RPC | PASS | `runtime/file-handlers-settings-rpc.txt` |

### 7.2 Sandboxed Flatpak callers

The native test client was connected to each app's real `xdg-dbus-proxy` socket (`/proc/<sandbox-pid>/root/run/flatpak/bus`) so the portal saw the **Flatpak app identity**, not a native test identity. Document grants were verified by reading the file inside the same sandbox.

| App | Portal app ID observed | Document URI | Read in sandbox |
|---|---|---|---|
| Ferdium | `org.ferdium.Ferdium` | `file:///run/user/1000/doc/d9a3d8d/nuxel-file-handler-test.txt` | PASS |
| Signal | `org.signal.Signal` | same grant | PASS |
| WhatsApp / ZapZap | `com.rtosta.zapzap` | same grant | PASS |

### 7.3 Physical UI preview — BLOCKED

All three Electron/QtWebEngine sandboxes start, but Electron does not create a renderer/window without disabling its inner Chromium sandbox:

```text
[2 preload-host-spawn-strategy] Failed to call Spawn:
org.freedesktop.DBus.Error.InvalidArgs: Could not find requesting pid
```

Zypak spawn strategies `0`, `1` and `2` all fail on this image. The only observed way to get a Ferdium window previously was `--no-sandbox`, which this mission prohibits. Therefore:

- physical attachment preview in Ferdium, Signal and ZapZap: **BLOCKED**;
- portal dispatch and document access for each app identity: **PASS**;
- no brute-force workaround or sandbox bypass was added.

Safe fallback: the same files remain available through the general XDG portal and through Files/Gallery; a native or non-Chromium portal client receives the selected file normally. The exact blocker is reproducible from the evidence logs and does not affect portal correctness.

---

## 8. Additional owner requests

### 8.1 Wi-Fi and devmgmt IP address

- Settings Wi-Fi panel already renders live `IPv4 address`/`IPv6 address` from `phone.status`.
- devmgmt renders the same live NetworkManager facts under **Network / Wi-Fi**.
- Live value: `10.20.30.16/24`, active connection `Nuxel Snoerbreuk`, state `internet`.

### 8.2 Private DNS and VPN

`pwa/nuxel-apps/network-manager/` wraps the existing `settings/wifi-settings.js` connector without a second backend. It adds:

- Private DNS providers (Cloudflare, Quad9, custom, DHCP) applied to the active profile;
- WireGuard and OpenVPN import/connect/disconnect/delete;
- truthful plugin state (`openvpn`, `wireguard`, `nm_openvpn`).

Live RPC: `dns-status`, `vpn-status` and `get` all succeed; `nm_openvpn=true`.

### 8.3 ZeroTier

`zerotier-one` 1.16.2 is installed and active on aarch64. Node address: `c1ab327d70`.

Joined network:

```text
0cccb752f72ecf52  ACCESS_DENIED  PRIVATE  ztly5zthnf
```

`ACCESS_DENIED` is the expected controller-side state until the owner approves the node in ZeroTier Central. A boot-safe drop-in grants only the `zerotier-one` group access to `/dev/net/tun` (`0660`, never `0666`):

`services/nuxel-s10/systemd/zerotier-one.service.d/10-nuxel-tun.conf`

### 8.4 VNC / Jump Desktop

- VNC is a separate X11/Openbox session on TCP `5900`, bound to `10.20.30.16` (not wildcard).
- TigerVNC `VncAuth` with a real generated password.
- Landscape geometry is enforced: `1520x720` (the S10+ current logical landscape).
- `nuxel-remote-vnc.service` is enabled at boot.  The first post-reboot check
  exposed that it was attached to `graphical.target` while the phone boots
  `multi-user.target`; the unit now uses `WantedBy=multi-user.target` and was
  verified active on a second reboot.  The wrapper falls back to the current
  `wlan0` IPv4 if the generated address is stale.
- Jump Desktop profile `nux-vnc` was updated to `1520x720`, host `10.20.30.16`, port `5900`, user `nuxel`, saved password.

The live Xvnc process and XRandR readback both report `1520x720`; the previous 1024x768 portrait/4:3 session is gone.

RDP was left running but is not part of this final acceptance per the owner's "nvm xRDP for now" instruction.

### 8.5 SSH banner

Only `/etc/banner` is printed for SSH. The legacy `/etc/profile.d/99-nuxel-banner.sh` duplicate was retired by the live installer and is absent on the phone. An interactive PTY test produced exactly one banner occurrence.

---

## 9. Security tests

Focused suite: `tests/pwnage97000/` — **46 passed**.

Covered:

- URI round-trip with spaces, Unicode, emoji, `#`, `%`, parentheses;
- canonical path, `..` traversal and symlink escape rejection;
- save-target validation and collision handling;
- MIME association validation (handler must declare the MIME type);
- MIME defaults precedence and preservation of unrelated `mimeapps.list` entries;
- picker policy precedence (app override > global > default);
- app inventory deduplication by stable ID;
- Flatpak app IDs stay stable;
- source scans forbid `--filesystem=host`, `--device=all`, `--no-sandbox`;
- zoom/Flatpak launch flags keep the sandbox enabled;
- private `org.nuxel.Portal` remains free of FileChooser;
- ZeroTier `/dev/net/tun` drop-in grants group access only;
- VNC geometry is landscape-only.

Additional live rejection evidence: the picker never returned a path outside the approved root; save collision produced a new ` (1)` name rather than overwriting.

---

## 10. Deployment and rollback

Deployment used the repository-supported path:

```text
scripts/nuxel-deploy-live.py --host 10.20.30.16 --user root \
  --key ~/.ssh/wicked_wqn_id_rsa --apply
```

- Payload: `build/out/s10plus/nuxel-v0.8.2-beta-live-userspace.tar.gz`
- Stamp: `20261108T233453Z`
- Installed targets: see `deploy/deploy-apply.txt`
- Pre-deploy hashes: `deploy/pre-deploy-hashes.txt`
- Rollback: `/var/lib/nuxel/live-deploy/rollback-20261108T233453Z/` with `COMMITTED`

Release-CI hardening: the v0.8.1 rootfs build failed with
`usermod: user 'nuxel' does not exist` because the inet-group usermod ran before
useradd.  The early usermod was removed; membership is written directly to the
staged `/etc/group` after the account exists.  The image builder also creates
`/etc/systemd/system/zerotier-one.service.d/` before installing the TUN
drop-in.  Both failures are covered by the PWNAGE-97000 contract tests.

Installed version after deploy: `host_version = 0.8.2-beta`; status bar `0.8.2-beta`.

---


### Local podman build note

The GitHub Release workflow's `build s10plus` job is the authoritative podman
build (`podman run --platform linux/arm64 fedora:43` on Ubuntu).  A local macOS
podman-machine attempt was also made with the direct CLI (no podman API), but
the existing machine returned `database disk image is malformed` and then
`machine is not running` even after a hard stop/start.  That is a host VM
failure, not a source failure; the live phone was deployed from the exact
repository payload via `scripts/nuxel-deploy-live.py`.

## 11. PASS / FAIL / BLOCKED matrix

| Area | Harness | Physical | Notes |
|---|---|---|---|
| Portal frontend + backend | PASS | PASS (live services) | bus owners verified |
| OpenFile single/multi/filter | PASS | PASS (native/zenity-style) | Gallery + Files |
| Directory selection | PASS | PASS | returns `/home/nuxel/Documents` |
| Cancel lifecycle | PASS | PASS | response 1, no hang |
| SaveFile / SaveFiles | PASS | PASS | Unicode/emoji + collision |
| Documents grant | PASS | PASS | read inside Flatpak sandbox |
| Ferdium app-ID dispatch | PASS | BLOCKED UI | zypak Spawn failure |
| Signal app-ID dispatch | PASS | BLOCKED UI | zypak Spawn failure |
| WhatsApp/ZapZap app-ID dispatch | PASS | BLOCKED UI | zypak Spawn failure |
| Settings File Handlers | PASS | PASS | real test picker success |
| MIME defaults | PASS | PASS | valid per-user mimeapps.list |
| Wi-Fi IP visible | PASS | PASS | Settings + devmgmt |
| Private DNS / VPN | PASS | PASS | live RPC |
| ZeroTier join | PASS | WAITING OWNER APPROVAL | `ACCESS_DENIED` |
| VNC landscape direct LAN | PASS | PASS | 1520x720 on 5900 |
| Jump Desktop profile | PASS | PASS (saved) | `nux-vnc` updated |
| Single SSH banner | PASS | PASS | one `/etc/banner` |

---

## 12. Evidence index

All under `docs/pwnage-97000/evidence/20261108T233433Z/`:

- `deploy/pre-deploy-hashes.txt`
- `deploy/deploy-apply.txt`
- `portal/open-flows.txt`
- `portal/save-flows.txt`
- `portal/signal-sandbox-dispatch.txt`
- `portal/zapzap-whatsapp-sandbox-dispatch.txt`
- `runtime/file-handlers-settings-live.txt`
- `runtime/file-handlers-settings-rpc.txt`
- `runtime/network-rpc-and-zerotier.txt`
- `runtime/final-live-state.txt`
- `runtime/ssh-banner.txt`
- `runtime/podman-rootfs-build.log`
- `security/pytest-pwnage97000.txt`
- `security/js-check.txt`

---

## 13. Remaining honest blocker

Physical attachment preview in Ferdium/Signal/ZapZap is blocked by the installed Electron/zypak inner-sandbox spawn path. This is independent of the XDG portal and document portal, which both pass. Fixing it safely requires a supported zypak/Flatpak update or a kernel/Flatpak-portal fix that lets `Spawn` resolve the requesting PID; `--no-sandbox` is explicitly not an acceptable fix.
