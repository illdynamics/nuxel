# PWNAGE-89000 — BOOT VELOCITY KICKSTARTER

You are executing **FULL-PWNAGE-89000.md**. Read that entire document first and follow it as the authoritative implementation specification. This is a hands-on source + physical-device engineering task: optimize Nuxel boot time and safely parallelize systemd startup without breaking the phone.

## Mission

The supplied `systemd-analyze critical-chain` shows:

```text
multi-user.target @45.877s
└─nuxel-clockd.service @45.877s
  └─nuxel-soundd.service @4.237s +41.633s
    └─nuxel-audio-session.service @38.923s
```

Do not assume every service starts sequentially. `Wants=`/`Requires=` pull units into the transaction; `After=`/`Before=` impose ordering. Inspect the real graph. Find exactly why soundd spends 41.633 seconds activating and why clockd appears at the end of this critical path. The likely architectural opportunity is to make clock scheduling and the sound control API ready independently of the slower audio hardware/session initialization, while retaining reliable alarm playback.

## Required access

1. Inspect the real repository at `~/x/nuxel`, its branch, dirty files, uncommitted changes and existing PWNAGE evidence. Do not overwrite owner work.
2. Discover the current phone host using the repository's Wi-Fi live-SSH helper where available; do not trust an old pinned IP.
3. Connect to the Nuxel **root console** over Wi-Fi using:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  root@<DISCOVERED_PHONE_HOST>
```

Preserve host-key verification. Never use `StrictHostKeyChecking=no`, delete host keys, or expose private-key contents. Verify `id -u == 0`.

## Execution order

1. **Baseline first:** capture device/kernel/systemd versions, default target, `systemd-analyze time`, `blame`, critical chains for `default.target`, `multi-user.target`, `graphical.target` and actual Nuxel lockscreen/session units, `systemd-analyze plot`, dependency DOT, service properties, and monotonic journals.
2. **Back up:** create `/var/backups/nuxel/p89000-<UTC_TIMESTAMP>/` with exact unit files, drop-ins, symlinks, scripts, configs, metadata and checksums. Prepare a tested rollback path before editing.
3. **Root-cause soundd:** inspect `Type=`, readiness notification, `ExecStartPre/ExecStart/ExecStartPost`, scripts, D-Bus/PipeWire/ALSA waits, timeouts, device discovery, retries and actual `After`/`Wants`/`Requires` edges. Explain the 41.633 seconds with evidence.
4. **Fix readiness architecture:** start clockd's scheduler without waiting for the entire audio stack. Make soundd's control/queue interface ready as soon as it can safely accept requests. Initialize `nuxel-audio-session` concurrently/asynchronously where the real code contract permits. Queue due alarm/timer cues durably and idempotently until a valid output route is ready; do not lose or duplicate alarms.
5. **Audit all services:** map boot-critical, independent, session-required, background and on-demand services. Remove only proven unnecessary ordering barriers. Pay special attention to unnecessary `network-online.target`, long oneshots, synchronous `systemctl start` calls, prewarm, metadata refresh and other noncritical work.
6. **Parallelize safely:** use `Wants=` for optional pull-in and `After=` only for actual ordering/readiness requirements. Keep true device, filesystem, D-Bus, logind, input, display and session prerequisites. Do not flatten the graph blindly or turn everything into `Type=simple`.
7. **Protect responsiveness:** move optional work out of the lockscreen critical path, but limit background CPU/I/O/memory pressure so the Exynos 9820 stays responsive. Preserve Phoc/Wayland, Mali/EGL and the sole `nuxel-wl-fb` `/dev/fb0` writer.
8. **Deploy carefully:** validate unit files with the installed `systemd-analyze verify`, inspect the final graph, deploy atomically, `daemon-reload`, restart only what is safe, retain SSH access, then perform controlled reboots.
9. **Prove it:** at least three final measured boots (preferably five), same baseline conditions, median/range. Measure kernel/userspace/targets separately from first visible frame, lockscreen-ready and first usable touch. Test sound, alarms/timers, clockd, Wi-Fi SSH, Bluetooth, display, input, launcher and Flatpak/native app launch.
10. **Report:** write `docs/pwnage-89000/evidence/<UTC_TIMESTAMP>/ENGINEERING-REPORT.md` with exact root cause, original/final dependency graphs, all changed files, before/after measurements, per-boot data, regression results, remaining bottlenecks and exact rollback commands.

## Hard safeguards

- Do not edit kernel, bootloader, device tree or partitions in this userspace/systemd round unless evidence proves it necessary and a separately safe recovery plan exists.
- Do not disable essential services, add arbitrary sleeps, remove all dependencies, fake `READY=1`, or weaken security.
- Do not move clock scheduling to a late graphical session.
- Do not sacrifice alarm reliability to make boot look faster.
- Do not claim `multi-user.target` means the UI is usable.
- Do not declare victory based only on `systemd-analyze blame` or one reboot.
- Do not report visual/physical tests as passed unless actually performed.

**Success means Nuxel visibly and interactively boots faster, independent services truly start in parallel, sound becomes ready without blocking the clock scheduler, alarms still ring reliably, and repeated on-device measurements prove the improvement.**

Now execute `FULL-PWNAGE-89000.md` completely. Do not stop after writing an analysis or suggesting changes; implement, deploy, test, measure, and provide the evidence report, while honestly marking anything that could not be physically verified.
