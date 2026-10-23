# A63 implementation changelog

Implementation commits: `6899841` (Home battery/SnekByte integration) and `57f803c` (S10+ web-service network gate).

- Added immediate host-backed battery hydration and removed fabricated bridge fallback data.
- Bumped Home/status/cache revision to `0.6.4-beta` / `v34-a63-runtime`.
- Corrected SnekByte to canonical ID `org.nuxel.SnekByte`, added the supplied icon, and migrated old recents state.
- Removed nonexistent precache/page assets that could break service-worker installation.
- Updated launcher tests for the current background/resume lifecycle.
- Made the optional VM docroot truly optional in `nuxel-web.service`.
- Added the S10+ Android-kernel `inet` group (AID 3003) while keeping the web service unprivileged.

Tests: battery/status truth passes; launcher registry/parity passes with one pre-existing LiveConsole warning; Snek engine 48/48; A58 controls/timing 35/35; Python/JS parity 27/27. Android APK work was deliberately skipped at the owner's request.

Live deployment was userspace-only, hash-verified and atomic. A broad manifest run stopped at a pre-existing empty live `launcher.css` and rolled that file back; the changed A63 files were then deployed narrowly and verified.
