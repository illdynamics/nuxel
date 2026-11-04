# PWNAGE-62000 — Permanent Penguin Chrome, Lockscreen Supremacy, Fast Boot & True Console Presence

**Mission:** PWNAGE-62000  
**Repository:** `illdynamics/nuxel` (live checkout `/x/nuxel`, branch `main`)  
**Device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**Userspace:** Fedora 43 aarch64, kernel `4.14.253-gf7194c1d15ed-dirty`  
**Compositor:** Phoc 0.54 / wlroots 0.19, Wayland headless, `nuxel-wl-fb` sole `/dev/fb0` writer  
**Final deployed boot:** `2479d58b-81b3-49e7-86e4-0cdf8dcfb024`  
**Final deploy backup:** `/var/backups/nuxel/p62000-20261103T080758Z`  
**Report date:** 2026-11-03

> Status vocabulary is used exactly: `IMPLEMENTED`, `OFFLINE_TESTED`, `BUILT_AARCH64`,
> `PACKAGED`, `DEPLOYED`, `OWNER_TESTED`, `VERIFIED_ON_S10PLUS`, `NOT TESTED`.
> A compositor capture plus live state files is used where a photo or physical touch
> was not available; touch-only scenarios remain `NOT TESTED`.

---

## A. What was broken

### A1. Native top bar was absent over native/Flatpak apps

The source contained `tools/s10plus/a45/nuxel-statusbar.c`, but the session explicitly
did **not** start it, `build-a45.sh` did not build it, and the image installed it as
`nuxel-statusbar.disabled`. Over Stremio there was therefore no native layer-shell
top bar; the Home DOM bar was inside a different Wayland toplevel and could not rise
above Stremio.

Fixed by building, packaging and supervising `nuxel-statusbar`, and by showing it only
when a non-Home toplevel is activated.

### A2. Foreign-toplevel protocol was broken in three independent ways

These bugs made both the bar’s foreground detection and compositor-level lock
enforcement unreliable:

1. **`wl_seat` was declared with zero events.** Phoc sends `wl_seat.name` and
   `wl_seat.capabilities`; libwayland aborted dispatch with
   `interface 'wl_seat' has no event 1` before toplevel events were processed. The
   tool reported `WINDOWS=0` while `wlrctl toplevel list` showed `nuxel-pwa-host`.
2. **The foreign-toplevel state enum was off by one.** The protocol values are
   `0=maximized, 1=minimized, 2=activated, 3=fullscreen`. The code mapped `1..4`, so a
   windowed GTK/Flatpak app was never seen as activated.
3. **Regular handle requests passed a non-NULL new-id interface.** libwayland interprets
   a non-NULL `interface` argument as “create a new proxy”. For void requests such as
   `set_maximized`, `set_minimized`, `unset_fullscreen` and `activate`, it returned
   early and **dropped every request**. Receipts claimed enforcement while nothing was
   sent.

Fixed by declaring the real `wl_seat` events and listener, correcting the enum, using
`wl_proxy_get_version()`, and passing `NULL` for regular requests. Live protocol trace
now shows:

```
-> zwlr_foreign_toplevel_handle_v1#...unset_maximized()
-> zwlr_foreign_toplevel_handle_v1#...set_minimized()
-> zwlr_foreign_toplevel_handle_v1#...unset_fullscreen()
-> zwlr_foreign_toplevel_handle_v1#...set_maximized()
-> zwlr_foreign_toplevel_handle_v1#...activate(wl_seat#5)
```

### A3. Bottom dock could disappear over Stremio

The JS → host → FIFO → navdock chain could lose `nav-show` if the FIFO did not yet
exist, and there was no authoritative recovery after a late app map. The dock also had
no state contract telling Home whether it was actually mapped.

Fixed with a persistent request file, bounded host retry/queue, idempotent show,
500 ms authoritative lock reconciliation, state transitions, and supervisor restart.
Home’s DOM nav is hidden while the native dock is proven present (`native-nav-present`)
or while the first readiness check is pending (`native-nav-pending`), so there is never
a persistent duplicate.

### A4. An already-running app could cover the Home lockscreen

The Home lockscreen was a DOM surface inside `nuxel-pwa-host`; CSS z-index cannot order
one Wayland toplevel above another. The host’s `screen-lock` action also sent an
unsupported `lock` verb to `/run/nuxel-wl-fb.cmd` (the bridge only accepts
`screen-off/screen-on/screen-toggle/status`) and did not drive the DOM lockscreen when
Home was hidden behind an app.

Fixed by:
- correcting `screen-lock` to write `screen-off` and dispatch the Home `lock` action;
- making the persistent foreign-toplevel watcher re-check authoritative lock state
  every 250 ms and re-enforce on lock transitions, non-Home activation, and a bounded
  1 s policy tick;
- un-fullscreening/unmaximizing/minimizing non-Home windows and unminimizing,
  unfullscreening, maximizing and activating Home (never killing the app);
- retaining the fail-closed rule: missing/invalid lock state means locked.

### A5. WLAN console icon represented readiness, not a session

`console_transports()` set `wlan.active = (wifi_status == "AVAILABLE")` and ignored the
reported session count. The old helper also counted global ESTABLISHED TCP/22 sockets
without proving interface, user, shell or PTY.

Fixed with a proof-based `/proc` model requiring **all** of:
- ESTABLISHED TCP/22 on a local IPv4 address belonging to a Wi-Fi interface;
- the owning `sshd` process holding that exact socket inode;
- a live descendant shell owned by uid 1000 (`nuxel`);
- a `/dev/pts` PTY;
- no `-c` command argument (so `ssh -t host true` health checks do not count).

The controller cache was reduced from 5 s to 1 s and the lockscreen refresh to 1 s.
USB CDC-ACM and USB-network remain separate; USB-network stays unavailable/never
active on the known-broken 4.14.253 NCM path. The base penguin is now
`service_armed`/service-ready, independent of transport sessions.

### A6. Preload final-frame hang and config duplication

The controller waited for touch readiness as part of the overlay release gate and kept
mpv’s final frame until readiness or the hard timeout. The session script also supplied
different launcher/map-delay defaults than the JSON.

Fixed by:
- one authoritative JSON timing source; session script no longer injects duplicate
  fallback values;
- splitting `presentation_ready` (launcher document, boot OS, fresh framebuffer/display
  receipt) from `input_ready` (touch armed/known warning);
- releasing at `video-eof-and-presentation-ready`, with a bounded 1.5 s final-frame
  grace when presentation is safe but touch is not;
- a shorter 15 s hard fail-open bound;
- honest receipt fields `presentation_ready`, `input_ready`, `eof_at_s`,
  `final_frame_hold_s`, `reason`.

A cold-boot packaging defect was found during validation: the PWN36000 boot bootstrap
unconditionally overwrote the deployed preload controller with its older staged copy.
The guard now only rolls forward when the staged copy is genuinely newer, and the live
and stage copies are installed identically.

### A7. Reboot black-screen delay

Measured previous-boot evidence showed:
- `nuxel-wayland` consuming its stop timeout because the old `ExecStop` signaled only
  `MAINPID`/direct children; the wrapper exited and Phoc was reparented;
- the display bridge stopping while the compositor still burned that timeout;
- `nuxel-audio-session` burning a full 4 s final-sigterm timeout because PipeWire
  children ignored SIGTERM.

Fixed with unit-specific cgroup stop helpers (`nuxel-wayland-stop.sh`,
`nuxel-audio-stop.sh`), 2 s unit bounds, and a bounded wl-fb reboot hold. No global
timeout, forced reboot or SysRq path is used. Remaining delay after the frame is
blanked is the kernel/PCIe poweroff phase and is documented separately.

### A8. App drawer did not open

WebKit cancels the pointer stream when a vertical touch becomes a native scroll, so the
old pointer-only `pointerup` path never ran on the phone. A passive touch fallback now
mirrors the same bounded gesture on `touchstart/touchend/touchcancel`, resets the
`consumed` flag per gesture, and leaves kinetic scrolling untouched.

### A9. Deployment and rollback integrity defects

Found and fixed while running the real deploy:
- `sha256sum bin/*` failed on the `__pycache__` directory;
- an unescaped `$i` and `$(seq ...)` broke the remote restart block;
- the backup hashed its own in-progress `SHA256SUMS`, producing a false rollback
  mismatch;
- `app.js`/`navigation.js`/CSS were missing from the deploy set;
- the boot bootstrap could revert the preload controller;
- the audio stop drop-in/helper was not in the live deploy or image build set.

All are fixed and covered by regression assertions.

---

## B. What changed

| File | Change |
|---|---|
| `tools/s10plus/a59/nuxel-foreign-toplevel.c` | Correct state enum, real `wl_seat` events/listener, dynamic proxy version, `NULL` new-id interface for regular requests, lock watcher/enforcement |
| `tools/s10plus/a45/nuxel-statusbar.c` | Native OVERLAY top bar, hidden on Home/lock/preload, state contract, foreground watcher, empty input region |
| `tools/s10plus/a45/nuxel-navdock.c` | FIFO retry/queue, idempotent show, authoritative lock reconciliation, readiness/state transitions, bounded tick |
| `tools/s10plus/a45/nuxel-pwa-host.c` | `screen-lock` now sends `screen-off` and drives the DOM lock; nav command queue/retry |
| `tools/s10plus/a45/nuxel-shell-chrome.sh` | Single supervised owner for navdock/statusbar/lock watcher with bounded restart |
| `tools/s10plus/a45/nuxel-security-lock-rpc` | Fixed loopback lock RPC used when an app covers Home |
| `tools/s10plus/a45/nuxel-session.sh` | Starts supervised chrome once; no duplicate statusbar; preload timing JSON-only |
| `pwa/nuxel-home/js/gestures.js` | Passive touch fallback for the app drawer; per-gesture consumed reset |
| `pwa/nuxel-home/js/app.js` | Guarded `requestAnimationFrame`; canonical post-unlock Home; lock/nav behavior |
| `pwa/nuxel-home/index.html`, `sw.js` | `app.js?v=p62000`, cache namespace `v62000-pw62000` |
| `pwa/nuxel-home/css/style.css` | Exactly one nav host; no DOM/native duplicate while readiness is pending |
| `services/nuxel-bridge/src/system_indicators.py` | Proof-based WLAN sessions; readiness/activity separation; 1 s cache |
| `services/nuxel-preload-cinema/nuxel-preload-cinema` | Presentation/input split, final-frame grace, honest receipt, shorter bounds |
| `configs/nuxel/boot/preload-cinema.json` | Single authoritative defaults (4000/1200, 1.5 s grace, 15 s hard bound) |
| `services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh` | Does not revert newer deployed session or preload controller |
| `services/nuxel-s10/bin/nuxel-wayland-stop.sh` | Unit-cgroup TERM→KILL helper |
| `services/nuxel-s10/bin/nuxel-audio-stop.sh` | New unit-cgroup TERM→KILL helper |
| `services/nuxel-s10/systemd/nuxel-wayland.service.d/40-bounded-stop.conf` | `TimeoutStopSec=2`, helper ExecStop |
| `services/nuxel-s10/systemd/nuxel-audio-session.service.d/10-stop-bound.conf` | `TimeoutStopSec=2`, helper ExecStop |
| `services/nuxel-s10/systemd/nuxel-wl-fb.service.d/25-reboot-hold.conf` | Bounded last-frame hold only on owner reboot |
| `images/s10plus/build-phone-rootfs-inside-fedora.sh` | Packages statusbar, supervisor, lock RPC, stop helpers/drop-ins, guarded stage copies |
| `tools/pwnage62000/deploy-pwnage62000.sh` | Backup/build/atomic install/health gate; full PWA set; stage parity |
| `tools/pwnage62000/rollback-pwnage62000.sh` | Exact restore of every mission target |
| `tests/pwnage62000/*` | New shell/chrome, console-session, preload, drawer regression suite |

---

## C. Chrome/lock state machine (verified behavior)

| State | Home DOM bar | Native top bar | Back/Home/Tabs dock | Lock UI |
|---|---|---|---|---|
| Home unlocked | visible | hidden | native dock visible; DOM nav hidden | hidden |
| Stremio/Flatpak foreground unlocked | hidden behind app | **visible above app** | **visible above app** | hidden |
| GTK/native foreground unlocked | hidden behind app | visible above app | visible above app | hidden |
| App dialog/popover | hidden behind app | visible, input pass-through | visible/usable | hidden |
| Locked, app was foreground | hidden | hidden | hidden | **above app** |
| App activation attempt while locked | hidden | hidden | hidden | **stays above app** |
| Unlock succeeds | visible | hidden until non-Home app | restored | hidden |

Lock authority remains `/run/nuxel/security/lock-state.json`, written only by
`security_provider.py`. Missing/invalid state is locked.

---

## D. Console indicator truth table (verified)

| Live Console service | USB serial session | USB network session | Wi-Fi SSH interactive session | Base penguin | Serial icon | USB-net icon | WLAN icon |
|---|---|---|---|---|---|---|---|
| stopped | no | no | no | off | off | off | off |
| running/ready | no | no | no | **on** | off | off | off |
| running | yes | no | no | on | **on** | off | off |
| running | no | unavailable | yes | on | off | off | **on** |
| running | no | unavailable | multiple | on | off | off | **on** |
| running | no | unavailable | last closes | on | off | off | **off** |

Live verification on the final boot:

```
zero sessions: {"available": true, "live": true, "serial": false, "usb": false,
                "wlan": false, "sessions": 0}
one PTY:       {"available": true, "live": true, "sessions": 1, "wlan": true,
                "source": "wlan:interactive-pty-session"}
two PTYs:      {"sessions": 2, "wlan": true}
close one:     {"sessions": 1, "wlan": true}
close last:    {"sessions": 0, "wlan": false,
                "source": "INACTIVE:no-interactive-ssh-session"}
```

---

## E. Measured timings

### E1. Preload / cold boot (final boot `2479d58b…`)

Final receipt:

```
elapsed_s=6.405
eof_at_s=6.386
final_frame_hold_s=0.0
final_frame_grace_ms=1500
hard_timeout_ms=15000
presentation_ready=true
input_ready=true
reason=video-eof-and-presentation-ready
verdict=PLAYED
```

This is the intended behavior: at EOF the real locked UI was already
presentation-ready and touch was ready, so there was **no post-EOF final-frame hold**.

Remaining cold-boot limitation (measured, not hidden):

```
Startup finished in 3.447s (kernel) + 49.527s (userspace) = 52.974s
multi-user.target reached after 48.612s
40.908s nuxel-mic-route.service
```

The locked UI/preload handoff is ~6.4 s after the controller starts; the 40.9 s
`nuxel-mic-route` path is a separate pre-existing boot-stage delay, not a frozen video
or blank screen. It remains `NOT TESTED`/unfixed by this mission.

### E2. Reboot / shutdown

First validated reboot (before the audio-stop repair):
- old boot `da176b4d…` → new `87a27ad2…`; observed SSH outage 63.40 s
- `nuxel-wayland` stop: 0.58 s (no timeout)
- `nuxel-wl-fb`: 2.04 s last-frame hold
- `nuxel-audio-session`: **4.15 s final-sigterm timeout** (remaining blocker found)
- journal stopped at monotonic 24810.8 (kernel/PCIe messages continue after systemd)

Second validated reboot (after the audio-stop repair; final boot `2479d58b…`):

```
188.236 Stopping nuxel-audio-session
188.322 Stopped  nuxel-audio-session      (0.086 s)
188.322 Stopping nuxel-wl-fb
190.527 Stopped  nuxel-wl-fb              (2.205 s bounded hold)
190.749 Stopping nuxel-wayland
191.325 Stopped  nuxel-wayland            (0.576 s, no timeout)
191.757 Reached target reboot.target
191.884 systemd-shutdown
192.014 Journal stopped
```

- userspace stop-to-journal: **3.778 s**
- display frame end → journal stop: **1.487 s**
- observed SSH outage: **82.60 s** (WiFi reconnect variance; not a visual black-screen
  measurement)
- normal `systemctl --no-block reboot`, no `--force`, no SysRq

The remaining post-journal kernel/poweroff interval is not timestamped by journald;
it is marked `NOT TESTED`/hardware-bound rather than claimed fixed.

---

## F. Tests and exact results

### Offline / regression (all pass)

```sh
python3 tests/pwnage62000/test_console_sessions.py          # ALL PASS
python3 tests/pwnage62000/test_preload_readiness.py         # ALL PASS
python3 tests/pwnage62000/test_shell_chrome.py              # ALL PASS
node    tests/pwnage62000/test_drawer_gesture.js            # ALL PASS
python3 tests/pwnage31000/test_preload_cinema.py            # rc=0
python3 tests/pwnage31000/test_preload_packaging.py         # rc=0
python3 tests/pwnage52000/test_lockscreen_privacy.py        # rc=0
python3 tests/pwnage52000/test_lpm_boot.py                  # rc=0
python3 services/nuxel-bridge/test-system-indicators.py     # ALL PASS
python3 tools/s10plus/a45/test-lockscreen-indicators.py     # ALL PASS
node    tools/s10plus/a45/test-lockscreen-indicators.js     # ALL PASS
node    tools/s10plus/a45/test-lockscreen-layout.js         # ALL PASS
node    tools/s10plus/a45/test-lockscreen-unlock.js         # ALL PASS (66/66)
```

Static checks: `sh -n`/`bash -n` on every changed shell script, `py_compile` on every
changed Python file, `node --check` on every changed JS file, JSON validation,
`git diff --check`, and `systemd-analyze verify` all succeeded (verify emitted unrelated
Fedora warnings but returned 0).

### AArch64 build (on the S10+ target)

Built with the target cross/shipping toolchain and Wayland/Cairo/Pango/GTK/WebKit libs:

```
nuxel-navdock          AArch64  OK
nuxel-statusbar        AArch64  OK  (libwayland-client, libcairo, libpango)
nuxel-foreign-toplevel AArch64  OK
nuxel-pwa-host         AArch64  OK  (GTK3/WebKitGTK 4.1)
nuxel-button-manager   AArch64  OK
```

Final installed hashes are in `evidence/pwnage62000/installed-sha256.txt`.

### Live S10+ evidence

- Stremio active: `WIN title=Stremio app_id=com.stremio.Stremio ... act=1`;
  statusbar `visible:true foreground_app_id=com.stremio.Stremio`; navdock
  `visible:true mapped:true`.
- Final compositor capture: `evidence/pwnage62000/stremio-final-chrome.png`
  (720×1520). OCR reads Stremio content plus the Nuxel top strip.
- Lock while Stremio foreground: Home `act=1`, Stremio `act=0`; statusbar/navdock
  hidden; lock receipt `home_raised:true hidden_non_home:1`.
- Locked capture: `evidence/pwnage62000/locked-over-stremio-live.png`; OCR reads
  “swipe up to unlock”, not Stremio content.
- Locked activation attempt: project `focus` verb requested Stremio while locked;
  after the watcher tick Home remained `act=1`, Stremio `act=0`.
- WLAN session proof: 1 → active; 2 → active; close one → 1/active; close last →
  0/inactive; availability remained true.
- Preload receipt and shutdown timelines: `evidence/pwnage62000/`.

---

## G. Live status matrix

| Item | Status |
|---|---|
| Foreign-toplevel protocol + lock enforcement | `IMPLEMENTED`, `OFFLINE_TESTED`, `BUILT_AARCH64`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (compositor state/capture) |
| Native top bar over Stremio | `IMPLEMENTED`, `OFFLINE_TESTED`, `BUILT_AARCH64`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (state + capture/OCR) |
| Native dock over Stremio | `IMPLEMENTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (state + capture) |
| Lockscreen above Stremio | `IMPLEMENTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (state + capture/OCR) |
| Locked app activation attempt | `IMPLEMENTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (compositor request + state) |
| WLAN readiness ≠ session | `IMPLEMENTED`, `OFFLINE_TESTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (real PTYs) |
| Base vs transport indicators | `IMPLEMENTED`, `OFFLINE_TESTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` |
| App drawer touch fallback | `IMPLEMENTED`, `OFFLINE_TESTED`, `DEPLOYED`; physical swipe `NOT TESTED` |
| Preload presentation/input split | `IMPLEMENTED`, `OFFLINE_TESTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (receipt) |
| Preload config precedence | `IMPLEMENTED`, `OFFLINE_TESTED` |
| Reboot stop repair | `IMPLEMENTED`, `DEPLOYED`, `VERIFIED_ON_S10PLUS` (journal, 2 reboots) |
| Fresh rootfs image artifact | `PACKAGED` source/manifest only; full image build `NOT RUN` in this session |
| 10× cold boot / 10× reboot statistics | `NOT TESTED` |
| Physical touch unlock/rotation/dialog tests | `NOT TESTED` |
| GTK app / dialog over native chrome | `NOT TESTED` (Stremio Flatpak live-tested) |
| USB serial console attach/detach | `NOT TESTED` (no CDC-ACM gadget present) |
| USB-network SSH | `NOT TESTED`/explicitly unavailable on 4.14.253 NCM |

---

## H. Remaining issues / blockers

1. **Physical touch scenarios** (drawer swipe, unlock gesture, rotation hitboxes,
   long-press Back, app dialogs) were not executed by a human/robot finger. They remain
   `NOT TESTED` even though the relevant JS/C tests and deployed assets pass.
2. **GTK app/dialog** was not available as a live test in this run; Stremio Flatpak was
   live-tested.
3. **Only 2 of the requested 10 cold boots / 10 reboots** were performed. Timings above
   are measurements, not median/p95.
4. **`nuxel-mic-route.service` still costs ~40.9 s** and delays `multi-user.target`.
   The lockscreen is visible at ~6.4 s, so this is not a frozen preload frame, but total
   userspace boot remains ~49.5 s.
5. **Kernel/PCIe poweroff after journald stops is not measured**; it is hardware-bound
   and was not forced or shortened.
6. **Fresh rootfs image was not built**; the image build manifest now packages every
   changed component, and the live deploy path was used. Mark the image artifact
   `NOT BUILT`.
7. **`tools/beta/reboot-policy.sh pre --run` executes prose checklist labels** as shell
   commands and reports false failures; plan mode passes. The USB-serial live verifier
   correctly returns `BLOCKED_EXTERNAL_RESOURCE` because no CDC-ACM gadget exists. WiFi
   SSH reachability was used and verified instead.
8. **`wlrctl toplevel focus` segfaulted** during one lock-attempt test; the project’s
   fixed foreign-toplevel `focus` verb was used instead and the watcher held Home.
9. The worktree already contained substantial uncommitted PWNAGE work before this run;
   this report distinguishes what was verified/repaired here and does not claim those
   pre-existing changes were authored from scratch.

---

## PWNAGE 60000–65000 completion addendum (2026-11-04)

Live revalidation: all shell/compositor services active; lock state fails closed
(`locked=true`, `home_raised=true`, 4 non-Home windows hidden); navdock
mapped=false while locked with `fifo_ready=true`; no GPU fallback marker;
`FRAMES_OK` and one `/dev/fb0` writer. `tests/pwnage62000` 4 passed; the 46000
WLAN-console contract test now asserts the 62000 session-count rule
(`wlanTransport.active && wlanSessions > 0`) and passes (13/13). Touch,
rotation and suspend remain physical owner checks.
