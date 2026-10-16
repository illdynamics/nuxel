# 09 — LIVE DEPLOYMENT RECORD (every artifact, hash-verified on the target)

Channel: USB CDC-ACM console `/dev/cu.usbmodem201`.
Commands: `scripts/s10plus-debug-pack/nuxel-live.sh --run` (framed, target-side
SHA of the payload, real exit status) and `tools/s10plus/a29/push-file.sh`
(gzip+base64, 380-char chunks, every chunk acknowledged by reading the cumulative
file length back from the target; decode → SHA-256 → `install` → re-hash of the
installed path). Nothing was flashed; no TWRP; no BOOT/initramfs/kernel write.

Every hash below is the **target-side** value reported by the transfer tool, and
matches the artifact built in the UTM VM (Fedora 43 aarch64, same ABI):

| # | Path on the handset | SHA-256 | Source |
|---|---|---|---|
| 1 | `/usr/bin/seatd` | `d2a0bf9726a09b57235d0d6701dc749c7e9b5d900388fbc7eee9e973735d3e21` | `/usr/bin/seatd` extracted from the UTM VM's Fedora 43 aarch64 (installed but unused — see below) |
| 2 | `/usr/lib/nuxel/nuxel-wl-fb` | `8be06a34db89d481406808a240d169adeed7ac638b3fce1f714695d61b41296b` | `tools/s10plus/a31/nuxel-wl-fb.c` (A31 single-owner handoff) |
| 3 | `/usr/lib/nuxel/nuxel-pwa-host` | `d66cf93cc4692c20467a9cb77ac5962ae6f17067e8ee87687172e70dcce44110` | `tools/s10plus/a31/nuxel-pwa-host.c` (boot-owner signal, permission policy, web-process supervision, input observer) |
| 4 | `/usr/lib/nuxel/libnuxel-libinput-path.so` | `f333421fc68549864bc6d8ccc3671b3e04c9ababd21446536f2328087dce936c` | `tools/s10plus/a31/nuxel-libinput-path.c` |
| 5 | `/usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png` | `6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29` | staged from `/usr/share/nuxel/nuxel-background.png` (already on the device) |
| 6 | `/usr/share/nuxel/pwa/nuxel-home/js/app.js` | `2612bdd004aa1e8c5cd7610316714066e15b74db2d3ad52b73d85bf24945d1dd` | `pwa/nuxel-home/js/app.js` (`?boot=os` splash policy) |
| 7 | `/usr/share/nuxel/pwa/nuxel-home/sw.js` | `816bad131efc727cb8740f03bc2020b90c0f691669128e2027b28d697f631a87` | `pwa/nuxel-home/sw.js` (cache v2 migration + wallpaper precache) |
| 8 | `/etc/systemd/system/seatd.service` | `f99f2aa179742c13adfe6ae06574a6a0083ad6f2678625b45184376c2dae1bda` | `tools/s10plus/a31/seatd.service` |
| 9 | `/etc/systemd/system/nuxel-wayland.service` | `57b6ab526d26e84b73f35db346f8cd7bd51641fe21c463b3127f142a726e42c4` | `tools/s10plus/a31/nuxel-wayland.service` |
| 10 | `/etc/systemd/system/nuxel-wl-fb.service` | `babfed30851888c0564b3dae57dd5dfd3d4c7f0981e68d39bbf7cd1c70f2d5a2` | `tools/s10plus/a31/nuxel-wl-fb.service` |
| 11 | `/etc/systemd/system/nuxel-touch-arm.service` | `4234843a7bf3ac91f4bf01e4b22da8429a90c578e25ab5d7162491729d85a9f3` | `tools/s10plus/a31/nuxel-touch-arm.service` |
| 12 | `/usr/share/nuxel/pwa/nuxel-apps/**` | staged from `/tmp/nuxel-apps-code.tgz` (184 046 B, 646 chunks) | `pwa/nuxel-apps/` (code + icons only; per-app media resolved to the canonical copies) |

Build channel: `tools/s10plus/a31/build-a31.sh` — compiles inside the **live UTM
VM** (`nuxel@192.168.64.3`) with the image's own
`webkit2gtk4.1 2.52.5 / gtk3 3.24.52 / wayland`, so ELF dependencies match by
construction. The podman/gvproxy cross-build path was not used.

## Deliberate deviations, recorded honestly

* **`seatd` is installed but unused.** It was the first attempt at giving phoc a
  backend session, and it cannot work on this handset: the seat is VT-bound and
  the kernel has **no VT at all** (`/dev/tty0`, `/sys/class/vtconsole` absent,
  `/proc/consoles` empty), so wlroots timed out waiting for the seat to activate.
  The unit is left on disk (disabled) as the record of that measurement; the
  active path is `LIBSEAT_BACKEND=noop` + the libinput shim. The `seat` group
  created for it is unused.
* **systemd-udevd stays masked** (A26 policy). This cycle re-measured why: with
  udevd started, `udevadm trigger --subsystem-match=input` took the process count
  from 281 to 544 in seconds. `systemd-udevd.service` was disabled again and the
  helper process killed; the fork storm stopped immediately (back to 281 in 3 s).
* **A deliberate, scoped replacement was required** for both of the above
  (`nuxel-libinput-path.c`): it substitutes *device discovery* only, for
  `/dev/input` direct pointers only, and writes exactly one udev database entry
  per device from that device's own capability data. No event is ever fabricated.

## Deployment-safety notes learned this cycle

* `nuxel-push.py`'s opportunistic block streaming **cannot converge** on this
  link (two defects: it accounted the wrong substring for the expected length —
  `split("'",2)[1]` is `%s`, not the payload — and 32-line blocks are truncated by
  the guest tty buffer). Fixed in the repo; `push-file.sh`'s per-chunk
  acknowledgement is the transport that works.
* The console's `/dev/kmsg` mirror floods the link; `printk 1` quiets it safely.
  **Do not** `SIGSTOP` the `nuxel-console` process to quiet the link: that took the
  handset down via the software watchdog (`softdog.soft_margin=100
  soft_panic=1`) and it came back in charger mode.
* Two host processes must never share the port — both tools take an exclusive
  `flock` and refuse to run concurrently.
