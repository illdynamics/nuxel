# 04 — Physical pass matrix (on-device evidence)

| Gate | Result | Evidence |
|---|---|---|
| A64-P1 FIRST FRAME | **PASS_PHYSICAL** | `launcher.css` 12764 B served; framebuffer capture `evidence/after-home-fixed.png` shows 4-column grid + status bar; `STATUSBAR_OVERLAP_CHECK overlaps=none`. |
| A64-P2 STATUS | **PASS_PHYSICAL** | `STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none` repeated after reload; no raw GPU/VRAM text in status layer. |
| A64-P3 NAV | **PASS_PHYSICAL (partial)** | Real `touchmove/pointerup` on `lockscreen-handle`; `HOST_ACTION unlock`; app lifecycle `BACKGROUND/CLOSING` recorded. Home/Back repeated 10× not independently counted — needs owner thumb run. |
| A64-P4 ICON LAUNCH | **PASS_PHYSICAL** | `app:launch id=nuxel-settings`, `LAUNCH app_id=org.nuxel.SnekByte via launcher registry`, `state=ACTIVE`. |
| A64-P5 SCROLL | **NOT_TESTED** | Requires owner finger on the real grid; no scroll injection performed. |
| A64-P6 ROTATION | **NOT_TESTED** | Orientation policy service active; physical rotate not exercised this run. |
| A64-P7 LOCK | **PASS_PHYSICAL** | Real penguin-drag unlock reached threshold and completed: `unlock:complete locked=0 visible=0`. |
| A64-P8 RESTART | **NOT_TESTED** | No reboot performed (mission forbids unapproved reboot); hot reload used. |
| A64-P9 NONREGRESSION | **PASS_PHYSICAL (sampled)** | Wi-Fi/browser/camera services untouched; SnekByte and Settings launched post-repair; pre-existing kernel D-state load documented separately. |

`PASS_PHYSICAL` here means an on-device receipt or framebuffer capture, not a
host-only mock. Items marked `NOT_TESTED` require the owner's finger/rotation and
are not claimed as passing.
