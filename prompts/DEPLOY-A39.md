# Nuxel A39 — Live USB deployment and hardware acceptance

This archive contains a complete source repository plus an isolated userspace A39 payload builder. **No flashing or kernel changes.** The phone is NOT accessible from the patching sandbox, and physical speaker success has NOT been established.

## What's implemented in the source

- Four-icon stationary dock with original JPG/PNG artwork; **BG2 default**, BG1/BG2 thumbnail switcher and persisted preference in `nuxel.homeAppearance`.
- Home Settings: layout lock, configurable desktop count (default 2), battery display style (percentage inside icon / percentage only / live fill only), wallpaper and grid controls.
- Independent desktop page assignment persisted with the existing launcher layout; page indicators, horizontal touch swipes, and an edge-hover drag page switch. Penguin Home returns to Desktop 1.
- All-apps drawer renders registered apps, not only current desktop; long-press provides Add to Home, movement can transition into drag; lock state blocks edits.
- Back requests in-app history/navigation before returning Home; Recents appears above app iframes; thin, noninteractive scroll indicators and reduced touch-move diagnostic overhead.
- S10+ audio remains a **hardware validation blocker**. No undocumented ALSA routes or unsafe amp mixer values were added.

## Deploy safely

1. Read `DEPLOY-A39.md`, confirm active USB console on the **phone** before any file writes; never infer that a local repository path is the live phone path.
2. Back up `/usr/share/nuxel/pwa/nuxel-home/` and the two dock images and capture SHA-256; also save launcher data and config before any reset. Keep the USB console working.
3. Run the offline tests, then build the limited-scope file payload:

   ```sh
   python3 tools/s10plus/a39/tests/test_a39_assets.py
   python3 tools/s10plus/a34/tests/test-icon-assets.py
   python3 tools/s10plus/a34/tests/test-sound-cues.py
   sh tools/s10plus/a39/package-live.sh
   ```

4. Inspect `build/a39/nuxel-a39-home.tar.gz` and its `manifest.tsv`. Transfer it through the established safe USB shell. Validate all paths and check hashes against the manifest **before** any atomic file replacement. Install ONLY userspace assets into the actual root; preserve permissions and rollback copies. The tarball is NOT a flashing image.
5. Restart/reload the launcher and web components only after successful deployment, then invalidate old WebKit service-worker caches carefully (the cache key is `v16-a39-smart-dock`). Never delete layout/localStorage preferences while clearing code caches.
6. Confirm `/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg` and `/pwa/nuxel-home/assets/nuxel-bottom-bar2.png` return HTTP 200 with expected SHA-256. Also check the source image paths `/assets/...` if needed. Confirm running launcher revision and JS bundle.
7. On glass: open Home Settings, check default BG2, switch BG1 then BG2, reload UI and confirm preference persists; confirm 4 dock icons still work, page 2 swipes, wallpaper stays still, Home returns desktop 1, layout lock, add-to-home, battery styles with real level, thin scroll indicators and navigation.
8. Speaker audio remains separately blocked until ALSA/codec/UCM/amp path is traced using existing A37 diagnostics. Use low-volume, verified controls only; never claim audible playback until user confirms.
9. When stable, perform at most one controlled normal reboot and repeat the BG2 persistence, Home navigation and speaker checks. If a regression appears, restore the verified userspace backups and service state immediately.

## Existing A33 legacy tests

Some A33 tests assert that pressing Home **destroys** the active iframe. Newer Nuxel explicitly preserves/backgrounds running apps for Recents. Those tests remain incompatible with A39's desired Home semantics and must not be treated as evidence the newer behavior is wrong. The old A33 Git checkout tests also need a real `.git` repository; a source ZIP alone is not a Git checkout.

## Safety

NO FLASHING • NO PARTITION WRITES • NO KERNEL REPLACEMENT • NO BOOTLOADER WRITES • NO UNVERIFIED AMPLIFIER SETTINGS • NO DESTRUCTIVE RESET.
