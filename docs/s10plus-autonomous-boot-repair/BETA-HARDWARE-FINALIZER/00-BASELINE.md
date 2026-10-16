# 00 — BASELINE (A32, 2026-10-16)

Both live targets were inspected before any patch.  Every value below is a
measured value with the command that produced it; nothing is inferred from a
photograph.

## Physical target — Samsung Galaxy S10+ (live USB console /dev/cu.usbmodem201)

| Item | Value | How it was read |
|---|---|---|
| OS | Fedora Linux 43 (Forty Three) | `cat /etc/os-release` |
| Kernel | `4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64` | `uname -a` |
| PID 1 | `systemd` | `cat /proc/1/comm` |
| Boot mode (BEFORE) | `androidboot.mode=charger`, `charging_mode=0x3030`, `sec_bat_is_lpm_check: Low power charging mode: 1` | `/proc/cmdline`, `dmesg` |
| Boot time | 3.910 s kernel + 4.378 s userspace = 8.289 s | `systemd-analyze` |
| Panel | `/dev/fb0` 1440x3040, 32 bpp, stride 5760, virtual 1440x6080 | `/sys/class/graphics/fb0/*` |
| fb_var declared order | `R@16 G@8 B@0` (XRGB8888) — the driver never programmes it | `NUXEL_ANIM_FB_*` log lines |
| DECON hardware order | `R@0 G@8 B@16` = **ABGR_8888** | same log, `nuxel-anim-player` override |
| Backlight | `brightness=12800`, `max_brightness=48600` | `/sys/class/backlight/panel/` |
| Touchscreen (BEFORE) | **ABSENT** — `sec_ts_init: Do not load driver due to : lpm 1` | `dmesg`, `/proc/bus/input/devices` |
| Input devices (BEFORE) | meta_event, gpio_keys, grip_sensor, ssp_context, Headset, hall, certify_hall | `/proc/bus/input/devices` |
| Key device | `/dev/input/event1 name=gpio_keys` keys **114/115/116/703** | `nuxel-button-manager --probe` (EVIOCGBIT) |
| Audio | card0 `beyond-madera`; mixer element `Left AMP PCM Gain` 0..20, current 19 | alsa-lib via the same probe |
| Userspace audio tools | **absent**: no amixer/alsactl/aplay/pactl/wpctl (alsa-lib 1.2.16.1 present) | `command -v`, `rpm -q` |
| Launcher stack | phoc headless + libinput shim, `nuxel-pwa-host` (WebKitGTK 2.52), python http.server :8000 docroot `/usr/share/nuxel` | systemctl, `/proc/<pid>/cmdline` |
| Framebuffer owner | exactly one: `nuxel-wl-fb` (1440x3040, 21-24 fps, blit 35-43 ms) | `/run/nuxel-wl-fb.state` |
| Stale frontend | `/usr/share/nuxel/nuxel-home/js/status-bar.js` = v0.3.2-alpha (v0.4.0-alpha in the repo) | sha256 comparison |

## Running UTM guest — the authority for the launcher

| Item | Value | How it was read |
|---|---|---|
| Access | `ssh nuxel@192.168.64.3` (key auth, IP from `utmctl ip-address nuxel-aarch64-phosh`) | host tooling |
| OS / kernel | Fedora 43 aarch64, `6.17.1-300.fc43.aarch64`, host `nuxel-phosh` | `ssh ... uname -a` |
| Session | phosh on `phoc -v -S -C /usr/share/phosh/phoc.ini -E gnome-session --session=phosh` | `ps -eo pid,args` |
| Launcher source | repo mirror `/home/nuxel/nuxel` served by `nuxel-web.service` = `python3 -m http.server 8000` (docroot = repo root) | `systemctl cat nuxel-web.service` |
| Launcher URL | `http://127.0.0.1:8000/pwa/nuxel-home/index.html` | service definition + `Exec` |
| PWA tree | 129 files under `pwa/` (nuxel-home, nuxel-common, nuxel-apps) | `find pwa -type f` |
| Same launcher as the handset? | **Yes** — `index.html`, all CSS, all icons and `js/apps.js` are byte-identical; the only JS differences were the handset's own `?boot=os` handling and its two stale files | sha256 diff of both trees |

## What was already correct (and was not touched)

* One framebuffer owner; animation handoff acknowledged (`ANIMATION_STOP_CONFIRMED`).
* The original boot animation container (`/usr/share/nuxel/boot/nuxel-animation.nux`,
  sha256 `7d296871…`, 192 frames @24 fps from `assets/nuxel-boot-animation.mp4`).
* The wallpaper asset `assets/nuxel-background.png`
  (sha256 `6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29`) — the CSS
  reference `../assets/nuxel-background.png` already resolves inside the served tree.
* Fedora service health, the USB live console and rollback of every replaced file.
