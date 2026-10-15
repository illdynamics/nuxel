# BOOT-STAGES (cycle 2)

| Stage | State | Evidence |
|---|---|---|
| A — Samsung S-Boot | **WORKS for BOOT-partition loads (7/7 accepted)** | S-Boot records: `load_kernel: loading boot image from 218112` -> `kernel size = 0xf4a000, ramdisk size = 0x5be800` -> `Starting kernel...` -> `BOOTING TIME` |
| A2 — image format handoff | **WORKING (recovery)** | TWRP record: same path from `330752`, `kernel size = 0x2ac3800`, then a full kernel log |
| B — ARM64 kernel entry | **NOT OBSERVED** | zero console bytes on 7 Nuxel boots, while the same buffer captures TWRP's kernel log |
| C — initramfs `/init` | **NOT OBSERVED** | no `nuxel-init:` console lines, no `/nuxel-boot-diag.log`, empty BOOT diag slot |
| D — Fedora systemd | not reached | — |
| E — display / Phosh | not reached | — |

## Ram-console semantics used for the Stage-B decision
* S-Boot's cmdline (which replaces the boot-image cmdline entirely — TWRP's own
  `buildvariant=eng` is absent from `/proc/cmdline`) sets `console=ram`,
  `loglevel=4`, `sec_debug.level=0`, `androidboot.debug_level=0x4f4c`.
* `loglevel=4` filters normal boot chatter, but **panic/oops text is level 0–3 and
  would pass the filter**, and writes to `/dev/console` from PID 1 (our
  `nuxel-init:` `echo`s) bypass the printk level filter altogether.
* Therefore "no output at all" is a meaningful negative result: it excludes
  "kernel booted and panicked", and excludes "`/init` ran and printed".
* Caveat recorded honestly: it does **not** by itself distinguish "kernel never
  executed" from "kernel died before the ram console was registered".
