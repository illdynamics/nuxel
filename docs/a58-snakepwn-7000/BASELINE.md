# A58 baseline — 2026-10-22

The full A58 prompt was read before changes. Current Nuxel checkout is
`00422fb5d08c5372a1611de2295cbbc27bdf03b7`; the newer working Android/SnekByte
checkout is `/Users/wicked/x/snekbyte`, revision recorded in
`evidence/snekbyte-initial-git.txt`. Initial dirty files are recorded in evidence;
none of those user files will be overwritten.

## Actual sources

- Canonical working game: `../snekbyte/reference-pwa/nuxel-dropin/pwa/nuxel-apps/snekbyte`.
  A56 mobile UI plus the A57 settings-dialog fix. The Nuxel repository copy is older.
- Physical S10+ USB console responds. `/usr/share/nuxel/pwa/nuxel-apps/snekbyte`
  serves HTTP 200 at port 8000. Its engine SHA256 is
  `f1028ceff2ff923e85b1679c458640b0e4d677388d2b0ee761666efd4a3d7c3e`;
  its UI SHA256 is `7f6b104cfa97d6dac266fa3400a8ca5659faac8cf21f6f31edf1a3efecb22943`
  (A56). Canonical A57 UI is `0738b3629f899e7cab067c07e7af13b330404c07a4c520399a559f282e3c217d`.
- Shared Python rules are in `../snekbyte/src`; original reference also preserved
  at `tools/s10plus/a33/snekbyte/upstream`. No Python gameplay change planned.
- Both engines use 40×30 cells, five rates 5/8/12/16/20 (default 12), wall death,
  delayed growth and tail-cell poop every fifth actual food. Mobile UI defaults WoNQ ON.
- Mobile input: pointerup-only 22px swipes, D-pad click, boolean directionQueued.
  Settings update a saved copy, while tickMs reads activeSettings. Existing loop
  already uses rAF, 120ms frame clamp, 3-step catch-up cap and stops when idle.
- PWA identity `org.nuxel.SnekByte`; cache `nuxel-snekbyte-5000-v1`.
  Existing v2 localStorage key migrates v1, storing highScore with settings.

## Android

Existing Capacitor 7.6.9 / App 7.1.2 project at `../snekbyte/android-app`.
Application ID `com.illdynamics.snekbyte`, activity `.MainActivity`, versionCode 1,
versionName 1.0; origin remains https://localhost. JDK21 and API35 SDK are present
in `.scratch-snakepwn6000/toolchain`. Gradle wrapper 8.11.1, AGP8.7.2, minSdk23,
target35. No INTERNET permission. Android builds inject lifecycle hooks and disable
service workers. Preserve this technology and its native lifecycle bridge.

Existing APK SHA256 `63f8fd2427a2f3cd027be8fa98443e62ea7a54bf2afc538739ed4fd13b692741`.
Verified signer certificate SHA256
`3da42488b06a8b912d30f0afbf7e4d44247294b97b6d6c253bf340a5503e09fb`.
No physical Android ADB device attached at audit; existing emulator is available.
GitHub CI previously generated ephemeral debug keys, so release signer equivalence
must be checked rather than assumed.

## Baseline checks and backups

A57 JS: 48 passed, 0 failed. Older Nuxel JS: 44 passed, 0 failed.
Nuxel Python provenance/parity: 28 passed, 0 failed (3 scenarios/41 ticks).
Original Python pytest collection fails on three pre-existing imports of the
absent `snake_game` package. Tests and source remain preserved.

`dist/a58-rollback/` contains both PWA versions, Android source and actual A57 APK,
with per-file SHA256.json. Live S10+ game will be backed up before deployment.
No physical touch latency or input-to-photon timing measured at baseline.

## Design decisions / order

Retain five validated presets and normal 12 cells/s default. Implement a two-turn
FIFO, reject newest on overflow and reject duplicates/reversals against projected
heading. Clear input on lifecycle transitions. Recognize swipes at 14 CSS px with
1.25 dominant-axis hysteresis; acknowledge accepted commands immediately. Wrap ON
by default; Classic Walls is explicit next-round opt-in for legacy parity.
Speed is live through one setter; reset clock at change to give a full new period,
with no reset of game state. Keep cell rendering, cache the grid, avoid unchanged
HUD writes, and expose bounded software-only diagnostics when explicitly enabled.
