# FIRST-LIGHT → PHONE-UI HANDOFF (Phase 4/5 design + A17 groundwork)

A16 proves the panel can be driven from the very start of the boot and that the
renderer can hold the screen indefinitely. That is exactly what we want early in
bring-up — and exactly what must eventually stop, cleanly, with something else
owning the framebuffer.

**The penguin must never be killed on a timer.** A fixed timeout either kills it
while the UI is still coming up (black screen) or keeps it alive over the UI's
output (the animation overwrites the compositor). Both failure modes are worse
than the current state.

## 1. The state machine

```
FIRST_LIGHT  ──► SYSTEM_STARTING ──► PHONE_UI_STARTING ──► PHONE_UI_READY ──► ANIMATION_STOPPED
    │                  │                     │                    │
    │                  │                     │                    └─ animator stops drawing; compositor owns fbdev
    │                  │                     └─ a UI process exists AND has committed a frame
    │                  └─ systemd is up, real services start running
    └─ paint + hold, 2 s after kernel entry (A16, hardware-proven)
```

Transitions must be **observed**, never assumed:

| Transition | Evidence required |
|---|---|
| → `SYSTEM_STARTING` | systemd PID 1 replying on D-Bus |
| → `PHONE_UI_STARTING` | UI unit *active*, its process alive in the unit cgroup |
| → `PHONE_UI_READY` | the UI committed a frame (`FBIO*`/DRM succeeded) **and** stayed alive N seconds |
| → `ANIMATION_STOPPED` | the animator acknowledged the stop signal |

If the graphical session fails, the machine must not fall through to a black
screen: it returns to `FIRST_LIGHT` (penguin + a diagnostic strip). A visible
"I am still alive and here is my last error" screen is worth far more than an
honest black one.

## 2. A17 groundwork (implemented, not yet exercised)

* The hold PID is now captured and published instead of being discarded
  (`A16` logged `FIRSTLIGHT hold started pid=` — empty):

  ```
  NUXEL_MARKER ANIMATION_HOLD_PID=<pid>
  /var/lib/nuxel/fb-hold.pid
  ```

* A machine-readable boot-stage record is written into the real root before
  handoff, so the animator and the future UI read the *same* state instead of
  guessing:

  ```
  /var/lib/nuxel/boot-stage     STAGE=SYSTEM_STARTING
  /var/lib/nuxel/animation      ANIM_STAGE=FIRST_LIGHT
  /var/lib/nuxel/boot-context   root=... device=... slot=...
  ```

* `NUXEL_MARKER BOOT_STAGE_SYSTEM_STARTING` is emitted on the boot channel.

The intended stop channel is a **signal to the hold PID** (`SIGUSR1`) rather than
a file poll, because the animator's filesystem view is the initramfs and the
rootfs's `/run` is a different mount once systemd mounts its tmpfs. The PID file
lives in `/var/lib/nuxel` (ext4, not tmpfs), which both sides can see.

## 3. Display backend decision (Phase 5)

The S10+ kernel is **Samsung Linux 4.14.253 with `# CONFIG_DRM is not set`** and
a downstream DECON/DSIM fbdev path. `/dev/fb0` is real and driven; there is no
`/dev/dri/card*`, so **Phoc (wlroots) cannot start on this kernel today** — it
needs DRM/KMS with atomic modesetting.

Two parallel paths, in order of cost:

* **Path B (deliver first) — a transitional fbdev-native Nuxel phone UI.**
  Reuse the A16 renderer's proven display path (fbdev + DECON commit ioctls) and
  the same freestanding aarch64 build. Deliver: a real interactive screen
  (status bar, clock, battery, log viewer), touch input via `/dev/input/event*`,
  and controlled launch paths. This is honestly a *transitional native Linux
  phone interface*, not Phosh, and it will be documented as such.

* **Path A (parallel, longer) — bring up DRM/KMS.** Enabling `CONFIG_DRM=y`
  alone proves nothing: Samsung's downstream MIPI/DSIM/panel stack on this tree
  is fbdev-based, so this is a driver-porting project, not a config flag. It must
  not disturb: UFS boot, DTB/DTBO compatibility, AMOLED init, early logging,
  recovery key combos, power management. A16's fbdev first-light stays as the
  regression test throughout.

Until a UI can commit a frame, **`PHONE_UI_READY` must not be claimed** and the
animator must keep the panel alive.

## 3b. Input has a boot-mode prerequisite (measured, see DEVICE-OBSERVATIONS.md)

`sec_ts_init()` (and the fingerprint and wacom drivers) return `-ENODEV` when
`lpcharge == 1`, i.e. when S-Boot marks the boot `androidboot.mode=charger`
("Low power charging mode", set by `__setup` in `drivers/samsung/misc/sec_batt.c`).
A16 booted that way (its own log line at t = 0 proves it), which is why the input
list contains no touchscreen at all.

Therefore: **reboot with USB detached, confirm
`sec_bat_is_lpm_check: Low power charging mode: 0`, then attach USB after boot.**
Any UI/input test run from an LPM boot measures nothing about the hardware.

## 4. Explicit non-claims

```
PHONE_UI_READY            = NOT PROVEN
PHOC                      = NOT PROVEN (no DRM/KMS on this kernel)
PHOSH                     = NOT PROVEN
TOUCHSCREEN               = NOT PROVEN
INTERACTIVE NUXEL UI      = NOT PROVEN
```
