# PWNAGE-104A00 — kickstart (Nuxel UI shell)

Read and follow the complete specification in **`full-pwnage-104A00.md`**.

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

## Mission in one sentence

Keep the Nuxel UI shell coherent on the real panel: Home, status bar/safe zones,
navigation gestures, Quick Settings and OSK — in portrait and landscape, without
double input or dead zones.

## Current facts

- Phoc HEADLESS-1 720x1520 @ scale 2 (360x760 logical); PWA host and shell chrome
  are running.
- Auto-rotation is blocked by the SSP runtime; manual/locked modes work.
- The system clock is wrong (see `full-pwnage-104300.md`), which affects the status bar.

## Start here

1. Read `full-pwnage-104A00.md`, `full-pwnage-103000.md`, `REPORT-ROTATION.md`.
2. Capture baseline screens in both orientations.
3. Fix layout/gesture/input regressions; verify on the panel via `grim`.

## Hard limits

- Don't change panel geometry or weaken sandboxing/portals.
- Don't add a competing gesture handler.

## Done means

`FULLY_DONE` only with a verified gesture matrix and clean rendering in both
orientations, plus `REPORT-PWNAGE-104A00.md`.
