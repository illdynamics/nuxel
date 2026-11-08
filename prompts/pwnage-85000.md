# PWNAGE-85000 — Buttersmooth Penguin: Flatpak Launch & Whole-Device Performance

**Mission:** execute `full-pwnage-85000.md` completely, in the Nuxel repository, against the real Samsung Galaxy S10+ running Nuxel. This is a performance engineering campaign, not a cosmetic-only pass. Find and remove the Flatpak launch stall, improve whole-device responsiveness, and add restrained, beautiful transitions that do not overload the phone.

## 0. Read the complete specification first

Read **all of `full-pwnage-85000.md` before changing anything**. It is the controlling specification for this mission. Inspect the current repository and deployed phone state; do not treat historical documentation as current truth. Build a traceable issue list, baseline, staged implementation, acceptance matrix and rollback plan. Continue through implementation and physical verification; do not stop after writing an audit.

## 1. Connect to the actual phone over Wi-Fi SSH

The owner requires Wi-Fi SSH to the Nuxel root console. Use the existing key:

```bash
~wicked/.ssh/wicked_wqn_id_rsa
```

Use `IdentitiesOnly=yes`, `BatchMode=yes`, a bounded `ConnectTimeout`, and normal host-key verification. Discover the current phone IP using the repository's current Wi-Fi/status helper; do not assume a stale pinned host is reachable. The previous owner-supplied address `192.168.178.167` is only a last-known candidate and must be verified before use. Connect as `root`, verify `id -u` is `0`, and record the selected host and device identity. Do not disable host-key verification, delete known-host entries, expose the key, or ask for a password. Do not place secrets in scripts or evidence.

Example after discovering the current host:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 \
  root@<DISCOVERED_WIFI_HOST>
```

## 2. Primary known issue: Flatpak launch is taking ~30.7 seconds

The latest owner-provided PWNAGE-84000 report measured Flatpak sandbox initialization at approximately **30.7 seconds in three repeated runs**, described as a fixed delay in the post-context / D-Bus-proxy phase. Native GTK process spawn was approximately **0.48 seconds**. Treat those as the supplied recent measurements, not as proof of the exact blocking component. Reproduce and timestamp the entire path from launcher activation to first visible frame and first accepted input.

A critical repository clue: the Flatpak provider in the supplied repository's `services/nuxel-bridge/src/flatpak_provider.py` forces all Flatpak launches to inherit software-renderer settings (`LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`, `MESA_LOADER_DRIVER_OVERRIDE=llvmpipe`, `GSK_RENDERER=cairo`). Verify whether this remains in the current source and live deployment. It may be required for a particular app on this phone's graphics stack, but it must not be assumed appropriate for every app. Separate sandbox startup latency from post-launch rendering performance. Implement a **per-application, verified renderer policy**; never blindly remove the safe fallback or globally force software rendering.

Instrument the sequence separately: UI tap → bridge request → app registry lookup → systemd transient-unit submission/start (if used) → Flatpak CLI start → bwrap/user/mount namespace creation → D-Bus proxy/session-bus setup → runtime entry → app process start → Wayland surface mapped → first presented frame → first responsive input. Locate the exact ~30-second wait. Use bounded `flatpak run --verbose`, `flatpak info`, override inspection, `systemd-analyze`, `busctl`, logs and `strace`/`perf` only when available. Preserve the Flatpak sandbox, bwrap, user namespaces, portal permissions, and correct `nuxel` user/session context.

## 3. Whole-phone performance

Measure before and after: boot-to-interactive, native GTK/PWA/Flatpak launch, app drawer, desktop switching, Settings, scrolling, keyboard, touch-to-visible feedback, frame pacing/jank, CPU per process, memory/RSS/pressure, storage I/O, service startup dependencies, thermals and screen-off idle. The device is an Exynos 9820 S10+ on the 4.14.253 aarch64 vendor kernel with Phoc/Wayland and the Nuxel fbdev presentation path in the latest report. Re-probe the actual running renderer, framebuffer owner, GPU/EGL availability, resolution and deployed binary hashes. Historical A50 evidence describes an all-software pixman/WebKit/fbdev path and a 74–79 ms changed-frame cost, but that is old evidence; **remeasure the live state**.

Audit `nuxel-app-prewarm` and `nuxel-perf-tune` as deployed, not merely as repository files. Prewarming is not a root-cause fix: measure its startup benefit, resident memory, CPU wakeups, screen-off cost and effect on first/cold launch. Keep only useful, bounded caching/prewarm behavior. Do not sacrifice idle battery or memory headroom for cosmetic benchmark wins.

## 4. Smooth, restrained Nuxel transitions

Add subtle, consistent transitions for app open/close, app drawer, desktop switching, panels, menus, widgets and keyboard. Prefer small-surface `transform` and `opacity` transitions with short easing (roughly 140–220 ms), and press feedback around 70–110 ms. On this software-heavy graphics architecture, test the real paint/compositor cost; transforms are not guaranteed to be GPU accelerated. Avoid full-screen animated layers, backdrop blur, animated shadows, large filters, geometry/layout animation, permanent `will-change`, heavy spring loops, continuous decorative motion and large animated assets. Keep Nuxel's crisp pixel-art identity and visual clarity. Honor reduced-motion and provide a low-motion/performance mode. Preserve the existing no-blur / limited-shadow performance test contract unless an experimentally proven exception is justified.

## 5. Safety and execution rules

- Make a timestamped evidence directory and full backup before deployment. Record source commit, dirty state, live hashes, package versions, services and active renderer/session environment.
- Do not flash or replace the kernel, bootloader, DTB, initramfs or partitions. No governor/thermal throttling bypass, overclock, global SELinux/AppArmor/polkit disable, setuid bwrap, unprivileged sandbox bypass, `--no-sandbox`, `--filesystem=host`, or broad `--device=all`.
- Preserve the current single `/dev/fb0` writer and deployed `nuxel-wl-fb` behavior. Never rebuild from stale source over a newer deployed binary. Recover and match exact source first; otherwise leave that binary untouched.
- Preserve Mali/EGL, Phoc, touch, display/screen-off behavior, audio, clockd, soundd, microphone, Wi-Fi SSH and existing app state.
- Do not change many variables at once. Use one-factor experiments, A/B evidence, explicit promotion gates and per-change rollback.
- Do not claim “faster”, “GPU accelerated”, “smooth”, or “fixed” without measurements and a physical check.

## 6. Deliverables and finish line

Implement the highest-value safe fixes, not just a report. Produce:

1. `docs/pwnage-85000/evidence/<timestamp>/ENGINEERING-REPORT.md` with baseline, root cause, implementation, exact before/after results, remaining blockers and rollback.
2. Machine-readable timing data (JSON/CSV) and raw sanitized traces/logs.
3. Flatpak launch timeline for representative apps, including cold/warm p50/p95 and first-input timing.
4. Per-app renderer decision table showing tested environment, renderer, successful window presentation, CPU/RSS and reason for the policy.
5. Whole-device before/after performance matrix and thermal/idle results.
6. Animation/performance test coverage, reduced-motion test and owner physical acceptance matrix.
7. Source changes, service/unit changes and deployment manifest with SHA-256 hashes.
8. Verified rollback instructions and exact backup location.

**Flatpak acceptance:** eliminate the unexplained ~30-second wait. Target a warm launch-to-first-interactive-frame of ≤5 seconds for a lightweight representative Flatpak app where hardware/runtime conditions permit, or achieve at least a 70% measured reduction and document any remaining app-specific floor. No sandbox weakening. Measure cold and warm launches independently. Preserve correctness, user ownership, portal behavior, Wayland input and notifications.

**Whole-phone acceptance:** demonstrate lower p50/p95 app-start and interaction latency, fewer long frame stalls, no new memory pressure, no screen-off busy loops, no thermal regressions, and no loss of existing functionality. A measured regression blocks promotion.

Read the full prompt now and carry out the entire campaign. Do not stop at diagnosis or prewarming; do not hide a blocker behind a spinner or benchmark claim. Make Nuxel feel genuinely fast and buttery while keeping it lean, safe and reliable.