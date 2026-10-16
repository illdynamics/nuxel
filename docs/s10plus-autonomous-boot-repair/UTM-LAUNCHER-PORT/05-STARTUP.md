# 05 — AUTOMATIC STARTUP AND THE ANIMATION HANDOFF

## 1. The boot chain, with the launcher as the final stage

```
SAMSUNG BOOTLOADER (S-Boot)
  -> Nuxel ARM64 kernel  (embedded initramfs: /init, anim player, nuxel-ui, console)
  -> the ORIGINAL Nuxel MP4 animation is already playing on the DECON panel
  -> USERDATA -> Fedora 43 ext4 rootfs -> switch_root -> systemd 258 (PID 1)
  -> nuxel-ui.service starts (no ordering: this image's graph needs none, A24)
  -> nuxel-ui takes the single-instance display lock BEFORE opening /dev/fb0
  -> nuxel-ui commits its FIRST frame  (state: PHONE_UI_FRAME_COMMITTED)
  -> ONLY THEN does it ask the animation to stop (anim-stop file + SIGTERM to fb-anim.pid)
  -> the panel is re-asserted (a released DECON can be left unconfigured)
  -> state: PHONE_UI_READY
  -> [A28] the frame the user sees from here on is the NUXEL HOME LAUNCHER
  -> physical touchscreen events drive it (evdev, capability-selected)
```

The order is unchanged from A24/A26 because it is the property that makes the
handoff safe: **the launcher is never asked to appear before it has something on
the glass, and the animation is never stopped before that frame exists.** With
no launcher running, the animation simply keeps looping — the panel is never
black.

## 2. What changed for A28 (and what deliberately did not)

| Item | Change |
|---|---|
| `nuxel-ui` binary | page 0 is now the launcher; the diagnostic pages remain (tapping the title or `page=<p>`) |
| `nuxel-ui.service` | same unit, same `ExecStart=/usr/bin/nuxel-ui`, same empty ordering, same `Restart=always`; only the `Description`/`Documentation` text and the header comment changed (`tools/s10plus/a28/nuxel-ui.service`) |
| `tools/s10plus/a28/nuxel-ui.rev` | `A28-nuxel-home-launcher-1` — the rev the BOOT candidate carries |
| `tools/s10plus/build-a25-initramfs.sh` | now stages `tools/s10plus/a28/nuxel-ui.service` and `.../nuxel-ui.rev` into `/opt/nuxel/` (the initramfs already compiled `tools/s10plus/nuxel-ui.c`) |
| `nuxel-ui-fallback.service` | unchanged: the animation can still be re-run as the guaranteed visible screen |
| `nuxel-firstlight.service` | unchanged, still retired by `/init` (two renderers must never own the DECON) |

## 3. Fallback behaviour (kept, by construction)

| Failure | Behaviour |
|---|---|
| launcher cannot open `/dev/fb0` | exits with a named state (`ui-error`); the animation keeps looping |
| a second instance starts | refused **before** opening the framebuffer (`NUXEL_UI_DISPLAY_OWNER_REFUSED`, flock) — a second fb client powers the AMOLED down (measured A21/A24) |
| the launcher dies later | `Restart=always`, `RestartSec=2`; `nuxel-postboot.sh` also re-starts it; until it returns, the last committed frame stays on the glass |
| the wallpaper asset is missing/corrupt | `WALLPAPER_UNAVAILABLE <reason>`, the PWA's own `background-color` is drawn |
| a tapped app cannot run | the launcher stays up and reports the reason (§04.4); no framebuffer ownership changes hands |
| the touch node disappears | capability re-scan every 3 s; until then the console channel drives the UI |

## 4. Delivery paths (no reflash of the rootfs)

* **Live (preferred):** `scripts/s10plus-debug-pack/nuxel-live-deploy.sh` pushes
  the gzip+base64 payload over the CDC-ACM console with target-side SHA-256
  verification, keeps the previous binary as `/usr/bin/nuxel-ui.prev`, renames it
  into place atomically, and pins the rev in `/usr/lib/nuxel/ui.pinned`:

  ```sh
  scripts/s10plus-debug-pack/nuxel-live-deploy.sh \
      build/out/s10plus/a28/nuxel-ui-a28 \
      --to /usr/bin/nuxel-ui --restart nuxel-ui --pin A28-nuxel-home-launcher-1
  ```

* **BOOT candidate (only if a BOOT-only flash is wanted):** the initramfs carries
  `/opt/nuxel/nuxel-ui` + the unit + the rev; `/init` installs them into the
  Fedora root at boot, keeps the previous binary as `/usr/lib/nuxel/nuxel-ui.prev`,
  and **refuses to overwrite a live-deployed UI** when `ui.pinned` differs
  (`UI_PINNED_KEEP`).

No TWRP, no USERDATA rewrite, no kernel change is involved in either path.
