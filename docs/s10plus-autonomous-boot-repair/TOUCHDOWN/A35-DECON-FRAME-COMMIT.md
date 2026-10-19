# A35 — S10+ command-mode DECON live-frame commit repair (offline patch)

**Status: patched source and offline tests PASS; physical handset deployment/visual acceptance PENDING.**

## New owner observation

A physical tap on an app icon changes UI/app state, but the visible screen does
not update until a Power off/on cycle. The same delayed visual update affects
volume overlays and button actions. After boot, the launcher may remain hidden
until the same Power cycle. Screen-off reduces brightness but does not fully
blank the AMOLED.

## Root cause and evidence

The current A34 bridge (`tools/s10plus/a34/nuxel-wl-fb.c`) continually receives
Wayland screencopy frames and writes them into the mapped `/dev/fb0`, but
**previously issued no `FBIOPAN_DISPLAY` after normal frame blits**. Samsung
DECON in this downstream kernel is command-mode: a memory write is not a
hardware frame commit. Earlier proven code paths *do* pan after every frame:
`tools/s10plus/nuxel-anim-player.c` and `tools/s10plus/nuxel-ui.c`.
The recorded `docs/s10plus-autonomous-boot-repair/DEVICE-OBSERVATIONS.md`
notes that `FBIOPAN_DISPLAY` returns success and DECON `FRAME_DONE` follows.

A31 correctly removed expensive periodic `FBIOPUT_VSCREENINFO` mode resets,
but it accidentally removed the lightweight per-frame `FBIOPAN_DISPLAY` that
is required to commit on this vendor panel. That explains why invoking the
Power-key wake/reassert sequence could suddenly expose already-processed taps.
This is a **strong source-level diagnosis**; live verification is still required.

## Source repair

- `tools/s10plus/a34/nuxel-wl-fb.c` now commits each newly blitted compositor
  frame with `FBIOPAN_DISPLAY` at x/y offsets 0. It does **not** reconfigure
  display mode on each frame.
- The first launcher frame is explicitly committed after animation ownership
  transfer, and `bl_power`/brightness are restored proactively. This should
  eliminate the need for two Power presses at boot.
- Failed PAN calls are counted in `FRAMES_OK ... decon_pan_ok=...
  decon_pan_failed=...`. Repeated failures trigger the existing bounded DECON
  reassert path, rather than masking a malfunctioning panel.
- Explicit screen-off adds `FBIOBLANK(FB_BLANK_POWERDOWN)` following
  `bl_power=4` / brightness 0, to request an actually unlit AMOLED instead of
  only lowering the backlight. Wake uses the existing measured
  UNBLANK → FBIOPUT_VSCREENINFO → PAN recovery sequence, then subsequent
  committed compositor frames. It retains the framebuffer FD and sole owner.
- The standard S10+ Fedora rootfs builder compiles this patched source at
  `images/s10plus/build-phone-rootfs-inside-fedora.sh`; existing A34 service
  and binary paths are preserved.

## Offline verification performed

- `gcc -std=gnu11 -fsyntax-only` with the supplied Wayland headers: PASS.
- `tools/s10plus/a34/tests/run-decon-tests.sh` with supplied Wayland headers:
  PASS mocked PAN success/failure, blank ioctl and integration source contract.
- `tools/s10plus/a34/tests/run-a34-tests.sh`: PASS (existing touch, gesture,
  button FSM, terminal, and source integration tests).

These tests cannot prove DECON frame latching, real AMOLED blanking, or boot
animation handoff on physical hardware.

## Safe live deployment instructions (for the owner's MacBook agent)

1. Take a fresh read-only baseline via `scripts/s10plus-debug-pack/nuxel-live.sh`.
   Confirm actual console node; the phone must be on a normal boot with the
   live gadget console reachable. Record `cat /run/nuxel-wl-fb.state`,
   `cat /var/lib/nuxel/display`, `systemctl is-active nuxel-wl-fb`, and hashes
   of `/usr/lib/nuxel/nuxel-wl-fb`.
2. Build **only** the changed `nuxel-wl-fb` executable from the patched A34
   source, inside a compatible Linux AArch64 build environment with Wayland
   dev files and the generated screencopy protocol source. Verify ELF AArch64,
   shared dependencies and existing service compatibility. Do not deploy any
   macOS Mach-O executable. If using the A34 cross builder, ensure its sysroot
   and toolchain are valid before reusing its output.
3. Run `tools/s10plus/a34/tests/run-a34-tests.sh` and the mock DECON test.
4. Back up the installed bridge and preserve the original SHA-256. Use the
   existing verified framed serial deployment tool, e.g.:

   ```sh
   bash scripts/s10plus-debug-pack/nuxel-live-deploy.sh \
      build/out/s10plus/a34/nuxel-wl-fb \
      --to /usr/lib/nuxel/nuxel-wl-fb \
      --restart nuxel-wl-fb
   ```

   The shown binary path is an example **only if that build produced it**.
   Never substitute a stale locally cached binary for the patched source.
5. Confirm target-side SHA-256 and service activity. Read latest state and
   verify `decon_pan_ok` increases when the phone is visibly awake, and
   `decon_pan_failed` stays at zero. Capture `journalctl -u nuxel-wl-fb`.
6. Request an owner physical test: without Power presses, tap Settings,
   return Home, adjust Volume, swipe Quick Settings. All changes must be
   visible immediately. Then short-press Power once and confirm the AMOLED
   fully goes dark; press again and verify screen wake, UI visible, and touch
   still works. Finally, authorize a normal Nuxel reboot and check that Home
   becomes visible on its own. Collect pass/fail rather than inventing results.
7. If display goes dark permanently, `decon_pan_failed` grows, service loops,
   or the console remains reachable but the image stops changing, roll back
   the verified `.prev` binary using an atomic rename, restart only
   `nuxel-wl-fb`, and capture the device logs. Do **not** flash anything.

## Boundaries

The repaired source and tests ship in the replacement repository ZIP; a
cross-built AArch64 ELF is **not** bundled, because the MacBook's target
sysroot, Fedora libraries and device are unavailable here. The external
90-second physical test is required for a final verdict.
