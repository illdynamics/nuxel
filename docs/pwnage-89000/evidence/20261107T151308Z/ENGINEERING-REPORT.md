# PWNAGE-89000 — Nuxel boot velocity, safe parallelism and sound/clock readiness

**Run:** PWNAGE-89000
**Evidence root:** `docs/pwnage-89000/evidence/20261107T151308Z/`
**Host-side repo:** `/Users/wicked/x/nuxel`
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Device hostname:** `fedora` / DHCP name `2001-1c00-4d09-8a00-162b-e49d-dc7c-4128`
**Remote backup:** `/var/backups/nuxel/p89000-20261107T151308Z/`
**Status:** deployed, automatically tested, repeated on-device boots measured. Physical touch, Bluetooth radio, Flatpak/native app launch and loudspeaker audibility are **not** claimed as physically verified. No kernel, bootloader, device-tree or partition change was made.

---

## 1. Executive result

The supplied `systemd-analyze critical-chain` was a real symptom but not a complete picture: `multi-user.target` was being held open by `nuxel-soundd.service`, whose `ExecStartPre=` waited for the S10+ ABOX/CS35L41 hardware route for roughly 40 seconds. The visible launcher was already on a different path; it was not waiting for soundd. The soundd wait was therefore a real target/background-audio defect, but the `multi-user.target` number alone did not describe time-to-UI.

After the changes:

| Result | Baseline | Final | Change |
|---|---:|---:|---:|
| `multi-user.target` (userspace) | 45.648 s median | **12.547 s median** | **−33.101 s (−72.5%)** |
| Userspace startup (`systemd-analyze time`) | 46.465 s median | **12.547 s median** | **−33.918 s (−73.0%)** |
| Total systemd time | 49.927 s median | **15.965 s median** | **−33.962 s (−68.0%)** |
| soundd control API ready | 49.596 s | **8.825 s median** | **−40.771 s (−82.2%)** |
| Launcher/lockscreen ready | 15.339 s | **13.998 s median** | **−1.341 s (−8.7%)** |
| Launcher display owner / usable-UI proxy | 15.778 s | **14.488 s median** | **−1.290 s (−8.2%)** |
| First Nuxel animation frame | 6.492 s | **6.316 s median** | −0.176 s (−2.7%) |
| soundd pw-cat restarts during boot | 38 in the intermediate pre-fix boot | **0 on boots 2–5** | eliminated |

The largest, repeatable improvement is the removal of the 40+ second soundd/session/route barrier. The visible UI improvement is smaller (about 1.3 s) because the kernel/initramfs/ABOX/Phoc/WebKit path, not soundd, dominates the launcher’s first paint. This report does not pretend otherwise.

Four final boots (2–5) plus one intermediate boot (1) were measured. Boot 5 is the final reboot requested by the owner; the phone was left running afterwards.

---

## 2. Device, repository and access state

### 2.1 Device fingerprint

From `after/boot-5/summary.txt`:

```text
Linux fedora 4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT Sun Nov 1 13:38:15 CET 2026 aarch64 GNU/Linux
Fedora Linux 43 (Forty Three)
systemd 258 (258.11-1.fc43)
default target: multi-user.target
boot id: 9532c9c3-4546-4587-951c-6c9d369d5be4
uid: 0 (root)
```

The historical kernel identified in the prompt is the actual kernel. The machine had no hardware/BIOS bootloader timing exposed by `systemd-analyze`; only kernel + userspace are reported. Kernel/initramfs is therefore the first measured layer, not a power-on-to-kernel measurement.

### 2.2 Access

The repository’s live-SSH helper was tried first:

```text
scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan --status
# wlan UNREACHABLE nuxel@10.20.30.16:22 — tcp connect timed out
```

The owner-supplied address worked:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 \
  root@192.168.178.167
```

`id -u` was verified as `0`. Host-key verification was preserved; no `StrictHostKeyChecking=no`, no host-key deletion and no private-key output were used. Wi-Fi SSH remained available before, during and after every reboot.

### 2.3 Repository state

```text
branch: feature/v0.7.8-beta-pwnage-88000
HEAD:   0b55c8baebdbce1cebbebef0e37894fa635285f8
```

The worktree already contained uncommitted PWNAGE-88000/89000 work and unrelated owner files. They were inspected and preserved. This round added the source changes listed in section 6 and did not revert or rewrite unrelated owner work. The modified `pwa/nuxel-apps/nuxtore/...bundle.json` and the many untracked sound assets were pre-existing owner work and are not part of this round.

---

## 3. Baseline evidence

The original baseline was captured at `2026-11-07T13:56:40Z` (directory `baseline/`), before the soundd/route changes were deployed:

```text
Startup finished in 3.461s (kernel) + 46.465s (userspace) = 49.927s
multi-user.target reached after 45.985s in userspace.
```

Three baseline boots were recorded:

| Baseline boot | Kernel | Userspace | multi-user.target |
|---|---:|---:|---:|
| 1 | 3.461 s | 46.465 s | 45.985 s |
| 2 | 3.440 s | 45.565 s | 45.186 s |
| 3 | 3.428 s | 47.394 s | 45.648 s |
| **median** | **3.440 s** | **46.465 s** | **45.648 s** |

Baseline `systemd-analyze blame` top entries:

```text
41.592s nuxel-soundd.service
36.950s nuxel-mic-route.service
27.288s nuxel-abox-firmware-reload.service
15.250s nuxel-boot-sound.service
 8.932s NetworkManager-wait-online.service
 4.882s nuxel-audio-route.service
 4.029s nuxel-fallback.service
 3.007s nuxel-http-bridge.service
```

Baseline critical chain (`baseline/graph/critical-chain-default.target.txt`):

```text
multi-user.target @45.985s
└─nuxel-soundd.service @4.388s +41.592s
  └─nuxel-audio-session.service @39.120s
    └─basic.target @4.339s
      ...
```

Baseline visible-UI markers from `baseline/journal/full-boot.txt`:

| Event | Time |
|---|---:|
| `MP4_FIRST_FRAME_READY` | 6.492 s |
| `MANAGER_READY` (input manager) | 11.862 s |
| `LAUNCHER_READY_ANIMATION_OWNS_PANEL` | 15.339 s |
| `LAUNCHER_DISPLAY_OWNER` | 15.778 s |

The baseline launcher was therefore visible at ~15.8 s even while `multi-user.target` was still blocked until ~45.6 s. This is the key distinction between target completion and UI readiness.

---

## 4. Exact root cause of the 41.592 s soundd activation

The baseline effective unit had:

```ini
After=local-fs.target nuxel-audio-session.service
Wants=nuxel-audio-session.service
Type=simple
ExecStartPre=-/usr/lib/nuxel/nuxel-audio-route.sh --wait 200
ExecStartPre=/usr/libexec/nuxel/install-sound-library
ExecStart=/usr/libexec/nuxel/nuxel-soundd
TimeoutStartSec=240
```

`Type=simple` is not the cause. The service process itself was not the blocker. The activation interval was almost entirely the first `ExecStartPre=` process.

Monotonic baseline journal evidence (`baseline/journal/nuxel-soundd.service.txt`):

```text
[    7.850863] Starting nuxel-soundd.service ...
[    7.911470] nuxel-audio-route: waiting for readiness: Calliope core is not MUB0
...
[   39.205964] nuxel-audio-route: waiting for readiness: Calliope core is not MUB0
[   40.232373] nuxel-audio-route: waiting for readiness: both CS35L41 DSP1 protection DSPs are not booted+running
...
[   45.491828] nuxel-audio-route: verify ABOX RDMA1_EN=0 expected 1
...
[   48.122432] nuxel-audio-route: READY: calliope=MUB0 dsp1=2/2 ...
[   49.426053] install-sound-library[...]: installed 0 supplied sound file(s) ...
[   49.443872] Started nuxel-soundd.service ...
[   49.596825] nuxel-soundd: ready socket=/run/nuxel/soundd.sock
```

Timing breakdown:

| Phase | Observation |
|---|---:|
| Service activation starts | ~7.85 s |
| `nuxel-audio-route.sh --wait 200` begins | ~7.91 s |
| ABOX Calliope not `MUB0` | ~7.91–39.2 s |
| CS35L41 DSP1 not booted/running | ~40.2–45.4 s |
| Route controls applied/verified | ~45.5–48.1 s |
| `install-sound-library` | ~49.4 s |
| soundd process starts and control socket ready | ~49.6 s |
| **Measured activation** | **41.592 s** |

The hardware script was not adding an arbitrary sleep; it was polling real ABOX/CS35L41 readiness. The defect was architectural: a **control-plane daemon was made to wait synchronously for speaker hardware before it could accept any request**. This also held `multi-user.target` open because `nuxel-soundd.service` was wanted by the target.

The audio session was independently restarting during this window because the ABOX firmware was not ready:

```text
[    7.819871] Started nuxel-audio-session.service
[   19.811712] pipewire: spa.alsa: set_hw_params: Invalid argument
[   20.285195] Stopping nuxel-audio-session.service
[   22.743501] State 'final-sigterm' timed out
[   34.671869] Started nuxel-audio-session.service
[   36.307297] Stopping nuxel-audio-session.service
...
[   42.582314] Started nuxel-audio-session.service
```

The old `After=nuxel-audio-session.service` edge, combined with the `ExecStartPre=` wait, made the target inherit that hardware/session retry window.

### 4.1 The clockd placement

The owner-supplied graph showed:

```text
multi-user.target @45.877s
└─nuxel-clockd.service @45.877s
  └─nuxel-soundd.service @4.237s +41.633s
```

In the checked-in baseline, `nuxel-clockd.service` was already independent:

```text
nuxel-clockd.service @4.364s
└─basic.target @4.339s
```

and its effective unit had only:

```ini
After=local-fs.target
Wants=nuxel-soundd.service
```

with **no** `After=nuxel-soundd.service`. The supplied chain therefore reflects an older/different transaction edge (clockd ordered after soundd), not the checked-in unit measured at 13:56Z. I did not remove an `After=` edge that did not exist. The reproducible 41.6 s penalty was soundd’s `ExecStartPre=`, and the clockd scheduler was verified to remain early and independent of audio hardware.

The same pattern applied to two other background consumers: `nuxel-mic-route.service` spent 36.950 s and `nuxel-boot-sound.service` spent 15–32 s waiting for the same route. They were also removed from the boot transaction and made event-driven.

---

## 5. Final architecture

### 5.1 Fast sound control plane

`nuxel-soundd.service` now has:

```ini
After=local-fs.target
Wants=nuxel-audio-session.service
Type=notify
NotifyAccess=main
TimeoutStartSec=30
ExecStartPre=/usr/libexec/nuxel/install-sound-library
ExecStart=/usr/libexec/nuxel/nuxel-soundd
```

No `nuxel-audio-route.sh --wait` in `ExecStartPre=`. The daemon:

1. loads assignments and durable alarm/timer cues;
2. binds `/run/nuxel/soundd.sock`, listens, and only then sends `READY=1`;
3. starts its worker asynchronously;
4. waits for the PipeWire socket and the applied ABOX route before spawning `pw-cat`;
5. reports `backend_ready`/`audio_route_ready` separately from `control_ready`;
6. accepts and persists alarm/timer cues while the backend is not ready.

Measured final boot 5:

```text
nuxel-soundd: control API READY in 10.5 ms  (absolute 9.020 s)
nuxel-soundd: persistent pw-cat stream started at 44.262 s, only after route READY
```

The control plane is ready ~40.6 s earlier than the baseline; the speaker backend still waits for real hardware. That is the intended separation.

### 5.2 Durable alarm/timer queue

Clockd no longer calls a fire-and-forget player from its scheduler thread. Each occurrence has:

- `cue_state`: `pending`, `sending`, `accepted`, `dismissed`;
- `cue_attempts`, `cue_next_attempt_ms`, `cue_last_error`;
- the stable occurrence `token` used for deduplication;
- `soundd_instance` for restart reconciliation.

Clockd’s cue worker retries with bounded backoff (`250 ms, 500 ms, 1 s, 2 s, 5 s, 10 s`), re-arms on daemon restart, and periodically reconciles accepted cues against soundd health. Soundd deduplicates a repeated token, persists alarm/timer cues in `/var/lib/nuxel/sound/durable-queue.json`, and resumes them after a soundd restart.

The scheduler (`clockd`) remains independent of soundd and the audio hardware. A due alarm is never silently dropped because audio is late; it remains `ringing` with a pending cue until accepted, dismissed, or snoozed.

### 5.3 Event-driven route consumers

`nuxel-audio-route.sh` publishes a separate receipt only after all checks pass:

```text
/run/nuxel-audio-route.ready
  ready=1
  card=0
  sink=alsa_output.hw_0_1
  at=...
```

The pending/deferred state document is no longer treated as readiness. The receipt is removed on pending/deferred and atomically recreated after `state=applied`, `calliope=MUB0`, `dsp1=2/2`, sink/default/rate/volume verification.

- `nuxel-mic-route.path` watches the receipt with `PathChanged=`. The oneshot no longer runs `nuxel-mic-route.sh --wait 180` inside the boot transaction.
- `nuxel-boot-sound.path` watches the same receipt. The boot cue is no longer a 30+ s wayland-wanted oneshot. A `/run/nuxel-boot-sound.played` marker prevents a later route re-apply from replaying the cue. The path unit uses `PathChanged` rather than persistent `PathExists` to avoid the trigger-limit loop observed during the first live deployment test.
- `nuxel-mic-route.service` and `nuxel-boot-sound.service` remain available for manual/systemd use but are not direct `multi-user.target` or `nuxel-wayland.service` wants.

### 5.4 Safe parallelism changes on the UI path

- `nuxel-web.service` still `Wants=nuxel-http-bridge.service`, but no longer has `After=nuxel-http-bridge.service`. The static PWA document is served immediately; the bridge is pulled in concurrently. The former ordering cost ~3.2 s before first paint.
- `nuxel-interface-state.service` no longer has `Before=nuxel-wayland.service`. Bluetooth/NFC/GNSS state restore remains in `multi-user.target` and still runs after NetworkManager/Wi-Fi, but it no longer serializes the compositor behind Wi-Fi association.
- `nuxel-device-permissions.service` no longer has `Before=nuxel-wayland.service`. The compositor and its root helpers open their real devices directly; the user launcher does not touch `/dev` nodes. The policy still runs `Before=nuxel-audio-route.service nuxel-bluetooth.service`.
- `nuxel-audio-session.service` is no longer directly enabled into `multi-user.target`; soundd’s `Wants=` pulls it in, and the ABOX path owns its restart lifecycle. The old target symlink was already gone; the unit file now reflects that.
- `nuxel-audio-route.service` remains a Wayland-session background want, not a target want.
- The rootfs builder was updated so a fresh image installs/enables the new path units and does not recreate the removed direct wants.

### 5.5 Final critical chain

The final `multi-user.target` critical chain no longer contains soundd, mic-route, boot-sound, audio-session, clockd or ABOX:

```text
multi-user.target @10.898s
└─avahi-daemon.service @10.642s +24ms
  └─network-online.target @10.640s
    └─NetworkManager-wait-online.service @6.586s +4.052s
      └─NetworkManager.service @4.336s +2.245s
        └─dbus-daemon.service @4.208s
          └─basic.target @4.204s
            ...
```

This is an honest remaining bottleneck: `NetworkManager-wait-online.service` (4.05–7.99 s across final boots) is a true `network-online.target` consumer path through `avahi-daemon.service`. It was not removed because Avahi is a network service and the mission forbids removing a true network-online dependency merely to improve a number. It affects target completion more than first UI; the launcher is on a separate path.

Final ordering facts:

```text
nuxel-wayland After=nuxel-touch-arm nuxel-bootmode-oneshot seatd
               nuxel-device-permissions nuxel-web
nuxel-web     After=tmp.mount -.mount systemd-tmpfiles-setup
              Wants=nuxel-http-bridge   (no After)
nuxel-boot-sound After=nuxel-wayland nuxel-wl-fb sound.target
                 nuxel-button-manager nuxel-boot-sound.path
nuxel-soundd   After=local-fs.target
               Wants=nuxel-audio-session
nuxel-clockd   After=local-fs.target
               Wants=nuxel-soundd
```

---

## 6. Changed files

All final deployed hashes are in `final/deployed-hashes-and-cats.txt`; local source hashes are in `final/hashes-local.txt`. The deployed bytes and the evidence copies match.

| File | Change and reason |
|---|---|
| `services/nuxel-sound/nuxel-soundd.service` | Removed `ExecStartPre=-.../nuxel-audio-route.sh --wait 200`; removed `After=nuxel-audio-session`; `Type=notify`; `TimeoutStartSec=30`. Control socket is the readiness contract. |
| `services/nuxel-sound/nuxel-soundd.py` | Control-plane readiness before backend; durable alarm/timer queue; token dedupe; backend/route health; no `pw-cat` spawn until PipeWire socket + applied ABOX route; bounded stream backoff; no boot restart storm. |
| `services/nuxel-clock/nuxel-clockd.py` | Durable cue worker; bounded retry/reconcile; restart re-arm; occurrence cue state; no scheduler dependency on audio. |
| `services/nuxel-clock/nuxel-clockd.service` | Keeps `After=local-fs.target`, `Wants=nuxel-soundd`; explicitly documents why no soundd ordering edge is allowed. |
| `services/nuxel-s10/bin/nuxel-audio-route.sh` | Publishes atomic `/run/nuxel-audio-route.ready` only after verified route; removes it on pending/deferred. |
| `services/nuxel-s10/systemd/nuxel-mic-route.service` | Removed `--wait 180`; now event-triggered. |
| `services/nuxel-s10/systemd/nuxel-mic-route.path` | New/updated path unit watching `PathChanged=/run/nuxel-audio-route.ready`. |
| `services/nuxel-session/systemd/nuxel-boot-sound.service` | Event-triggered; requires applied-route receipt; one-shot marker; no direct Wayland want. |
| `services/nuxel-session/systemd/nuxel-boot-sound.path` | New path unit watching `PathChanged=/run/nuxel-audio-route.ready`. |
| `services/nuxel-s10/systemd/nuxel-audio-session.service` | Removed direct `WantedBy=multi-user.target`; soundd pulls it in as a background dependency. |
| `services/nuxel-s10/systemd/nuxel-interface-state.service` | Removed `Before=nuxel-wayland.service`; radio restore no longer gates the compositor. |
| `services/nuxel-s10/systemd/nuxel-device-permissions.service` | Removed `Before=nuxel-wayland.service`; retained ordering before audio-route and Bluetooth. |
| `services/nuxel-web.service` | Removed `After=nuxel-http-bridge.service`; retained `Wants=` for concurrent bridge startup. |
| `images/s10plus/build-phone-rootfs-inside-fedora.sh` | Installs/enables the new path units; removes direct multi-user wants for audio-session, mic-route and boot-sound; keeps audio-route as a Wayland-session want. |
| `tests/pwnage89000/test_boot_readiness.py` | Offline contracts for fast truthful soundd readiness, durable cue queue, clockd retry/re-arm, applied-route path triggers, boot-cue one-shot, no web/interface/device-permission barriers, and no pw-cat spawn without backend readiness. |

Pre-existing but relevant dirty files from the earlier PWNAGE-88000/89000 work (not reverted): `services/nuxel-clock/nuxel-clockd.py`, `services/nuxel-clock/nuxel-clockd.service`, `services/nuxel-sound/nuxel-soundd.py`, `services/nuxel-sound/nuxel-soundd.service`, `services/nuxel-s10/systemd/nuxel-audio-session.service`, `services/nuxel-s10/systemd/nuxel-mic-route.service`. All were reviewed and deployed as one coherent contract.

---

## 7. Readiness contracts and guarantees

### 7.1 soundd

| State | Contract |
|---|---|
| Process launched | Python process started |
| `control_ready=true` | `/run/nuxel/soundd.sock` bound and listening; `READY=1` sent |
| `queue_depth` | number of durable alarm/timer cues persisted |
| `audio_route_ready=true` | `/run/nuxel-audio-route.state` says `state=applied` and `calliope=MUB0` |
| `backend_ready=true` | `pw-cat` stream alive and no last error |
| `pending_token` / `active_token` | stable occurrence token currently queued/playing |

`Type=notify` is truthful: systemd considers soundd started only after the control socket/queue are usable. It does **not** claim speaker hardware is ready. Hardware readiness is reported separately through `health`/`status`.

### 7.2 clockd

Clockd reports `scheduler ready alarms=N timer=...` immediately after loading state and starting its API/cue threads. It does not wait for soundd, PipeWire or ABOX. A due occurrence:

1. is persisted with `state=ringing` and `cue_state=pending`;
2. triggers haptics and the notification immediately;
3. is handed to the cue worker;
4. remains pending with bounded retries if soundd/audio is unavailable;
5. is marked `accepted` only after soundd acknowledges the stable token;
6. is re-armed if soundd restarts or loses the stream;
7. is dismissed/snoozed only by explicit user/API action.

### 7.3 Boot cue

The boot cue is cosmetic and never blocks the boot target. It fires once when the applied-route receipt appears, records `/run/nuxel-boot-sound.played`, and skips later route re-applies. The cue process still performs its own read-only route check immediately before playback. Audibility is not claimed without a physical listening test.

---

## 8. Measurements

### 8.1 Required comparison table

See `boot-table.md` / `boot-table.json`. The median baseline uses three baseline boots; final median uses boots 2–5.

| Metric | Baseline median | Final median | Final min | Final max | Delta | Delta % |
|---|---:|---:|---:|---:|---:|---:|
| Kernel/initramfs (s) | 3.440 | 3.442 | 3.397 | 3.475 | +0.002 | +0.06% |
| Userspace startup (s) | 46.465 | 12.547 | 10.904 | 14.830 | −33.918 | −73.00% |
| Total systemd time (s) | 49.927 | 15.965 | 14.379 | 18.278 | −33.962 | −68.02% |
| `multi-user.target` in userspace (s) | 45.648 | 12.547 | 10.898 | 14.830 | −33.101 | −72.51% |
| `multi-user.target` absolute (s) | 49.088 | 15.964 | 14.373 | 18.277 | −33.124 | −67.48% |
| First Nuxel animation frame (s) | 6.492 | 6.316 | 6.235 | 6.472 | −0.176 | −2.71% |
| Launcher/lockscreen ready (s) | 15.339 | 13.998 | 13.940 | 14.296 | −1.341 | −8.74% |
| Launcher display owner / usable-UI proxy (s) | 15.778 | 14.488 | 14.445 | 14.863 | −1.290 | −8.18% |
| Input manager ready (s) | 11.862 | 9.832 | 9.778 | 10.022 | −2.030 | −17.11% |
| soundd control API ready (s) | 49.596 | 8.825 | 8.731 | 9.021 | −40.771 | −82.21% |

Additional final measurements:

| Metric | Final result |
|---|---:|
| clockd scheduler ready | 8.101 s (boot 5) |
| audio route hardware ready | ~45.26 s (boot 5; hardware/firmware layer) |
| soundd pw-cat stream started | 44.262 s (boot 5; immediately after route) |
| boot cue delivery latency | 70.23 ms (boot 5); 8.49–86.33 ms across boots 2–5 |
| soundd restarts | 0 on boots 2–5 |
| normal volume cue latency | 6.48 ms (boot 4 test) |
| normal timer cue latency | 3.86 ms (boot 4 test) |
| alarm end-to-end cue latency | 11.13 ms (boot 4 test) |
| failed units at final boot | 0 |

### 8.2 Per-boot data

```text
boot 2: userspace 14.830  target 14.830  launcher 14.004  display-owner 14.483
        first-frame 6.472  soundd-API 8.872  cue 65.32 ms  restarts 0
boot 3: userspace 12.355  target 12.355  launcher 13.992  display-owner 14.494
        first-frame 6.293  soundd-API 8.731  cue 86.33 ms  restarts 0
boot 4: userspace 12.739  target 12.739  launcher 13.940  display-owner 14.445
        first-frame 6.235  soundd-API 8.777  cue 8.49 ms   restarts 0
boot 5: userspace 10.904  target 10.898  launcher 14.296  display-owner 14.863
        first-frame 6.338  soundd-API 9.021  cue 70.23 ms  restarts 0
```

The userspace/target range is 3.93 s, dominated by `NetworkManager-wait-online` (4.05–7.99 s). The launcher/display-owner range is only 0.42 s; the visible UI is substantially more stable than the target metric.

Boot 1 was an intermediate measurement taken after the soundd/web/interface-state fixes but before the final route gating and device-permission barrier removal. It is retained as evidence but excluded from the final median.

### 8.3 Resource pressure

Final boot 5:

```text
Mem: 7420 MB total, 1269 MB used, 5364 MB free, 6150 MB available
Swap: 0
systemctl --failed: 0 loaded units
```

No swap/zram pressure and no restart storm were observed. The pre-fix boot had 38 `pw-cat` restarts and a broken-pipe stream loop while the ABOX route was unavailable; the final boots have 0 restarts.

---

## 9. Functional test matrix

### Boot and core session

| Test | Result | Evidence |
|---|---|---|
| Cold/warm reboot completes without rescue/emergency | **PASS** | 5 controlled reboots; `after/boot-*/summary.txt` |
| Correct boot animation first frame | **PASS** | `MP4_FIRST_FRAME_READY` 6.235–6.472 s |
| No new failed essential units | **PASS** | final `systemctl --failed`: 0; `after/boot-5/resources.txt` |
| Nuxel launcher visible after animation | **PASS (visual capture/OCR)** | `after/boot-5/lockscreen-settled.png`, OCR in report evidence; shows Signal, Caprine, Teams, ZapZap, Ferdium, Telegram, Vesktop, “i think. build. nuxel” |
| Separate lockscreen overlay visible/unlock flow | **NOT TESTED** | Remote capture shows launcher/home, not a separate lock overlay; no physical unlock performed |
| Touch/input device path opened | **PASS (event path)** | `MANAGER_READY key=/dev/input/event1 touch=/dev/input/event2` at 9.78–10.02 s |
| Physical touch interaction | **NOT TESTED** | No physical finger test; synthetic pointer was not used |
| Display bridge / sole `/dev/fb0` writer | **PASS (service/visual)** | `nuxel-wl-fb` active; `LAUNCHER_DISPLAY owner=nuxel-wl-fb`; no second writer added |
| Phoc/Wayland and Mali/EGL path | **PASS (process/log)** | phoc running; EGL/kbase/panfrost log lines; composited screenshot captured via `grim` |
| Orientation | **NOT PHYSICALLY TESTED** | `nuxel-orientationd` active; no physical rotation test |
| Wi-Fi SSH after every reboot | **PASS** | all measurement commands used the owner key over Wi-Fi |

### Services and recovery

| Test | Result | Evidence |
|---|---|---|
| No failed essential units after final boot | **PASS** | `systemctl --failed`: 0 |
| systemd/D-Bus responsive | **PASS** | all `systemctl`, `systemd-analyze`, clockd/soundd socket calls succeeded |
| soundd control API ready early | **PASS** | 8.731–9.021 s; `READY=1` after socket |
| soundd backend handled ABOX restart | **PASS** | final `backend_ready=true`, `restarts=0` |
| Clockd independent scheduler | **PASS** | ready at ~8.1 s, no soundd ordering edge |
| `nuxel-mic-route` applied after route receipt | **PASS** | `/run/nuxel-mic-route.state` `state=applied`, `route=uaif0-nsrc0-sifm0-wdma1`; journal 45.27 s |
| Boot cue path event-driven and one-shot | **PASS** | boot cue queued at 47.24 s, latency 70.23 ms, marker present; second receipt change skipped |
| Wi-Fi SSH retained | **PASS** | final host reachable at 192.168.178.167 |
| Bluetooth radio | **NOT PHYSICALLY TESTED** | persisted desired OFF, soft-blocked, service inactive; state preserved, no toggle test |
| NFC/GNSS | **NOT PHYSICALLY TESTED** | persisted OFF; interface-state reports OFF |

### Audio, clock and alarms

| Test | Result | Evidence |
|---|---|---|
| Timer fires and plays once | **PASS** | 3 s timer; cue accepted attempt 1, latency 3.86 ms; `after/boot-4/timer-normal*` |
| Alarm fires and plays once | **PASS** | one-off alarm at 16:30; cue accepted attempt 1, latency 11.13 ms; `after/boot-4/alarm-e2e.txt` |
| Alarm/timer cue queued while soundd down | **PASS** | soundd stopped; timer became `ringing`, cue stayed `pending`, attempts 3; `after/boot-4/sound-outage-test.txt`, `outage-clock-down.json` |
| Cue accepted after soundd restart | **PASS** | accepted after 2 s, attempt 5, no duplicate; `outage-clock-poll.json`, `outage-soundd-health.json` |
| No lost/duplicate test alarm | **PASS** | test occurrence dismissed; no `p89000` active occurrence/alarm remained |
| Volume cue | **PASS** | 6.48 ms latency; `after/boot-4/p89000-volume-*` |
| Dismiss/stop semantics | **PASS** | timer stop and alarm dismiss produced no active `p89000` occurrence |
| Microphone capture route applied | **PASS (route state)** | state applied; actual recorded audio not physically tested |
| Loudspeaker audibility | **NOT TESTED** | cue delivery/ASoC route verified; no physical listening test |
| Boot cue audibility | **NOT TESTED** | queued and delivered at 70 ms; cold-boot warmup logged `speaker DAPM path did not power up` at 14.2 s because route was not applied yet |

### Apps and performance

| Test | Result | Evidence |
|---|---|---|
| Static launcher document served | **PASS** | HTTP 200 for `/pwa/nuxel-home/index.html` |
| HTTP bridge/app registry responsive | **PASS** | HTTP 200 for `/api/v1/apps/registry` |
| Native GTK app launch | **NOT TESTED** | no physical app launch performed |
| Flatpak app launch | **NOT TESTED** | no physical app launch performed |
| No memory pressure/swap storm | **PASS** | 6.1 GB available, no swap, 0 failed units |
| No soundd restart storm | **PASS** | 0 restarts on boots 2–5 vs 38 in the intermediate pre-fix boot |

---

## 10. Remaining bottlenecks and layer

| Layer | Remaining observation |
|---|---|
| Kernel/initramfs | ~3.40–3.48 s to kernel userspace; untouched in this round. |
| Bootloader/firmware | Not exposed by this kernel/systemd; not modified. |
| Systemd/network | `NetworkManager-wait-online.service` 4.05–7.99 s is the final `multi-user.target` critical chain via Avahi/`network-online.target`; left intact because Avahi is a real network consumer. |
| ABOX/CS35L41 firmware | Audio route remains hardware-bound at ~45.26 s. It is now a background path and no longer blocks the scheduler, target, boot cue path or lockscreen. |
| Audio session | PipeWire/ABOX restarts remain possible during firmware bring-up; soundd now treats them as backend state, queues durable cues and does not restart `pw-cat` until the route is applied. |
| Device permissions | ~0.9–1.3 s service; no longer gates Wayland. |
| Compositor/UI | Wayland starts ~7.6–7.7 s, `nuxel-wl-fb` active ~9.1–9.2 s, launcher ready ~13.94–14.30 s. Phoc/WebKit/PWA startup is the main visible-UI cost after the kernel/initramfs. Not changed in this round to protect display/EGL correctness. |
| Boot cue warm-up | `nuxel-audio-warmup` still runs once before the route is applied and logs a DAPM failure on cold boot; the cue still plays after the route becomes ready. A future change could defer warmup until the applied receipt without moving the cue into the boot transaction. |

---

## 11. Backup and rollback

### 11.1 Backup

Created before editing:

```text
/var/backups/nuxel/p89000-20261107T151308Z/
```

Contents:

```text
systemd-units.tar     # /etc/systemd/system and /usr/lib/systemd/system
nuxel-scripts.tar     # soundd, clockd, audio-route, mic-route, audio-session, installer
nuxel-state.tar       # /var/lib/nuxel/clock and /var/lib/nuxel/sound
checksums-before.txt  # exact sha256 of every touched deployed file
/etc/*.cat.txt        # systemctl cat snapshots
/etc/*.show.txt       # systemctl show snapshots
graph/                # baseline analyze/plot/dot outputs
journal/              # baseline boot and per-unit journals
ROLLBACK.sh           # restore script
MANIFEST.sha256       # backup manifest
```

A local copy is in `backup/` under this evidence directory.

Rollback validation (did not execute the full rollback, to avoid reverting the verified deployment; extraction and checksums were tested in a temporary directory):

```text
rollback_syntax=OK
systemd_tar_list=OK
scripts_tar_list=OK
state_tar_list=OK
rollback_files_ok=61 rollback_files_bad=0
```

See `rollback-validation.txt`.

### 11.2 Rollback commands

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes \
  -o BatchMode=yes root@192.168.178.167 \
  'sh /var/backups/nuxel/p89000-20261107T151308Z/ROLLBACK.sh'
```

The script restores the exact unit/script tarballs, daemon-reloads, re-enables the original key units and restarts soundd/clockd. The original enablement symlinks are inside `systemd-units.tar`; `ROLLBACK.sh` also re-asserts the original key unit enablement and disables the new path unit. Verify with:

```bash
ssh ... 'systemctl --failed --no-pager; systemctl is-active nuxel-soundd nuxel-clockd nuxel-wayland nuxel-wl-fb; systemd-analyze critical-chain multi-user.target --no-pager'
```

---

## 12. Truthful completion statement

**Deployed:** yes. The final units/scripts are installed at the exact paths reported in `final/deployed-hashes-and-cats.txt`, and the deployed hashes match the local source copies. The final boot 5 is running on the phone.

**Automatically tested:** yes. `systemd-analyze verify` accepted all staged units; four final boots were measured with repeated `systemd-analyze time`, critical chains, blame, unit properties, journals, screencaptures and service health checks. Alarm, timer, outage/retry, volume cue, HTTP launcher, registry and SSH checks passed.

**Physically verified:** visual launcher presentation is supported by a real `grim` screencapture and OCR of the composited Wayland output. Physical finger touch, Bluetooth radio toggling, loudspeaker audibility, orientation and Flatpak/native app launch were **not** physically performed and are explicitly marked NOT TESTED.

The successful, repeatable result is: the 41.6 s soundd hardware-wait barrier is gone, the clock scheduler and sound control API are independent of the ABOX hardware, alarm/timer cues are durable and retried, `multi-user.target` is ~72% faster, and the visible launcher is ~1.3 s faster. A faster target number was not obtained by faking readiness or by removing required device/session dependencies.
