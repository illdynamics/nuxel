# 01 — DISCOVERY: the launcher, from source and from the running VM

Every line below names the file, command or measurement it comes from. Where a
fact was taken from a live guest, the VM was started and inspected over SSH
(`utmctl start nuxel-aarch64-phosh`, `ssh nuxel@192.168.64.3`) during this
session.

## 1. The twelve discovery questions

| # | Question | Answer (evidence) |
|---|---|---|
| 1 | Which executable/application is the launcher? | **Nuxel Home**, the PWA at `pwa/nuxel-home/index.html`. `services/nuxel-web.service` describes itself as *"Nuxel PWA Static Web Server (nuxel-home launcher on :8000)"*. The native GTK4 front-end for the same registry (`shell/nuxel-home-native/`) is installed but disabled and currently crashes on start (see #12). |
| 2 | Which process launches it? | `nuxel-home-kiosk` (`shell/nuxel-kiosk/nuxel-home-kiosk`) opens `http://127.0.0.1:8000/pwa/nuxel-home/index.html?kiosk=…` with `chromium-browser`/`chromium` (`--kiosk --ozone-platform=wayland`) or `firefox --kiosk`. In the VM that script's first three candidates are absent, so a WebKitGTK browser (`epiphany`, `/usr/bin/epiphany`) is what renders it — the same engine `vm/vm-verify-pwa.sh` drives. |
| 3 | Which service starts it? | `shell/config/systemd-user/nuxel-home-kiosk.service` (`ExecStart=/home/<user>/bin/nuxel-home-kiosk`, `Wants=nuxel-web.service`) for the kiosk; `nuxel-web.service` (system) is what *serves* the launcher. Live VM: `nuxel-web` active, `nuxel-home-kiosk` **disabled/inactive**, `nuxel-home-native` **disabled/inactive** — i.e. the launcher is opened on demand, not by a unit. |
| 4 | Which source directory builds it? | `pwa/nuxel-home/` (index.html + js/ + css/ + icons/ + manifest.json). No build step: it is static and served as-is. |
| 5 | Which graphical framework does it use? | Plain web platform (HTML/CSS/JS) inside a browser; in the VM, **WebKitGTK 4.1** (`/usr/lib64/libwebkit2gtk-4.1.so.0.21.9`). The optional native twin is **GTK4 4.20.4 + libadwaita 1.8.7** (`rpm -q gtk4 libadwaita`) via `python3-gobject 3.54.5`. |
| 6 | Which libraries does it require? | The PWA: only the browser. The native twin: `python3-gobject`, `python3-dbus`, `gtk4`, `libadwaita`; `pwa/launcher` (hardened PWA runner): `webkitgtk-6.0`, `gtk4`, `json-glib`. |
| 7 | Which graphics/display backend? | Wayland (`phoc` compositor) in the VM: `phoc -v -S -C /usr/share/phosh/phoc.ini`, `phosh 0.54.0`, output `Virtual-1 720x1440`. |
| 8 | Which application manifest? | `pwa/nuxel-home/manifest.json` (web app manifest) **and** the launcher's own registry `pwa/nuxel-home/js/apps.js` (`NUXEL_APPS`). |
| 9 | Where are icons/assets loaded from? | Grid/dock icons are the registry's **emoji glyphs**, drawn in each app's colour (`js/launcher.js`); the PWA's own icons are `pwa/nuxel-home/icons/icon-*.png` (manifest); the wallpaper is `pwa/nuxel-home/assets/nuxel-background.png`, i.e. the repo asset `assets/nuxel-background.png` (`/usr/share/nuxel/nuxel-background.png` in the phone image). |
| 10 | Which input mechanism? | Browser pointer/touch events: `document.addEventListener('pointerdown'/'pointermove'/'pointerup')` plus `touchstart`/`touchend` in `js/launcher.js` (tap to launch, long-press to reorder). Under it: libinput -> Wayland -> the browser. |
| 11 | How does it launch applications? | `AppRegistry.launchApp()` (`js/apps.js`) records a recent app, dispatches `app:launch`, then `_launchPwa()` dispatches `pwa:open` (handled in `js/app.js` by creating a full-screen `<iframe>` with the app URL / opening a window) or `_launchNative()` dispatches `native:launch` for the `nuxel-<app>://` URL scheme. The hardened runner equivalent is `pwa/launcher/nuxel-pwa-launcher` (`WebKitGTK`, isolated `WebKitWebsiteDataManager` per app). |
| 12 | UTM vs S10+ runtime differences | VM: Linux 6.17.1, virtio-gpu, Wayland/Phoc, WebKitGTK, 720x1440. S10+: Linux **4.14.253**, `# CONFIG_DRM is not set` (no `/dev/dri`), DECON **fbdev** at 1440x3040 ABGR_8888, no compositor and **no browser engine in the image**. |

## 2. The application registry, from the launcher's own code

`pwa/nuxel-home/js/apps.js` defines nine apps; `getAllApps()` sorts by name and
`getDockedApps()` filters `docked`:

```
grid (6): Calendar, Camera, Contacts, Files, Mail, Notes
dock (3): Messages, Phone, Settings
```

That ordering, those ids, those colours and those emoji are what
`tools/s10plus/a28/gen-launcher.py` compiles into the phone binary — and what
`vm/vm-verify-pwa.sh` measured on the live VM display (6 grid / 3 dock). Two
independent front-ends, one registry.

`shell/nuxel-home-native/nuxel_home/app_registry.json` is the native twin's copy
of the same nine apps. The generator cross-checks them (ids, names, categories)
and **records divergences instead of silently choosing**: the only one found is

```
Camera: apps.js = native "nuxel-camera://" | app_registry.json = pwa
        "http://127.0.0.1:8000/pwa/nuxel-apps/camera-gallery/index.html"
```

The launcher (`apps.js`) is the authority for what is displayed, as the mission
requires; the divergence is reported by `gen-launcher.py` on every run and is
visible in `generated/nuxel-launcher.json`.

## 3. Live VM state captured this session (verbatim)

```
$ /Applications/UTM.app/Contents/MacOS/utmctl list
UUID                                 Status   Name
711988C4-B34A-4A0F-BA86-B2C4A182E4BE started  nuxel-aarch64-phosh

$ ssh nuxel@192.168.64.3 'systemctl --user list-unit-files | grep -i nuxel'
nuxel-home-kiosk.service    disabled  disabled
nuxel-home-native.service   disabled  disabled
nuxel-phosh-agent.service   enabled   disabled

$ ssh nuxel@192.168.64.3 'ls /usr/lib64/libwebkit2gtk*; for b in chromium firefox epiphany; do printf "%s: " $b; command -v $b || echo absent; done'
/usr/lib64/libwebkit2gtk-4.1.so.0 -> libwebkit2gtk-4.1.so.0.21.9
chromium: absent
firefox: absent
epiphany: /usr/bin/epiphany

$ ssh nuxel@192.168.64.3 'XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 /usr/local/bin/nuxel-home'
Traceback (most recent call last):
  File "/home/nuxel/nuxel/shell/nuxel-home-native/nuxel_home/main.py", line 32, in <module>
    from .app_launcher import launch_pwa
ImportError: attempted relative import with no known parent package
```

The last line is why the port targets the **PWA** front-end: the native GTK4
front-end as installed cannot even start (the launcher script execs `main.py`
as a script, so its package-relative imports fail). That is recorded here as a
fact, not repaired in this cycle — the phone has no GTK display path at all.

## 4. Boot -> user session -> launcher (traced)

```
UTM:  UEFI (shim/grub, vmlinuz 6.17.1) -> systemd -> gdm autologin ->
      gdm-wayland-session --register-session phosh-session ->
      phoc -v -S -C /usr/share/phosh/phoc.ini -E gnome-session --session=phosh ->
      /usr/libexec/phosh (0.54.0)  +  user units (nuxel-phosh-agent) ->
      nuxel-web.service serves /pwa/nuxel-home/ on 127.0.0.1:8000 ->
      a WebKitGTK browser displays http://127.0.0.1:8000/pwa/nuxel-home/index.html

S10+: S-Boot -> Nuxel ARM64 kernel -> embedded initramfs (/init) ->
      USERDATA -> Fedora 43 ext4 -> switch_root -> systemd 258 (PID 1) ->
      nuxel-ui.service (fbdev, single instance, owns /dev/fb0) commits its first
      frame -> boot animation stops -> nuxel-ui becomes the screen ->
      [A28] ... and that screen IS the Nuxel Home launcher.
```
