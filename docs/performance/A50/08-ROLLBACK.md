# A50 — 08: Rollback

**A50 made no persistent changes, so there is nothing to roll back.** The device
was left in its original state (screen off, all services unchanged, no files
replaced). Evidence:

- No deploy was applied (`tools/beta/live/nuxel-live-deploy.py` not invoked).
- No service was restarted.
- No file under `/usr/lib/nuxel`, `/usr/share/nuxel`, `/etc/nuxel` was written.
- The only live action (reversible `action screen-on` wake) was auto-reverted by
  the 60 s idle timer; verified `DISPLAY_SLEEP display=off capture=stopped`.

## If a future A50 change is deployed, use this rollback surface
1. **Bridge binary**: restore `nuxel-wl-fb.prev` (or `nuxel-wl-fb.prev-a32`) over
   `/usr/lib/nuxel/nuxel-wl-fb` and restart only `nuxel-wl-fb`.
   Live hash to return to: `bc38e12d075ebdd9e7a4cec43740760948a35794ad2d51b303f79d4f6191d123`.
2. **PWA assets**: restore from `docs/A49` off-device backups /
   `deploy-manifest.json` and restart `nuxel-wayland`.
3. **Button manager**: restore `nuxel-button-manager.prev` over
   `/usr/lib/nuxel/nuxel-button-manager`, restart `nuxel-button-manager`.
4. **Rollback helper**: `docs/performance/A50/tools/a50-rollback.sh`
   (documents + verifies the above; it does not auto-apply without review).

## Rollback helper (executable)
`docs/performance/A50/tools/a50-rollback.sh` — restores the known-good live
binaries from their `.prev` siblings only after re-verifying SHA-256, and
restarts the smallest affected service. It refuses any partition/boot/kernel
path and never reboots.
