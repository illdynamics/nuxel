# REPORT-PWNAGE-102000 — External HDMI blue-overlay fix

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Path:** USB-C DP Alt Mode → DP-to-HDMI adapter → Philips TV  
**Run:** 2026-11-09 19:30–19:35 CET  
**Status:** `FIXED_LIVE`; reboot verification in §E

---

## A. Symptom

The external HDMI picture was correct in geometry, orientation and hotplug
behaviour, but every pixel was pushed strongly blue — as if a constant blue
overlay covered the whole TV.

## B. Root cause

`nuxel-wl-fb-ext` packs each output word as **0xAARRGGBB** (memory bytes
`B,G,R,A`, i.e. `R@16 G@8 B@0 A@24`).  It passed the caller-side DECON format
`DECON_PIXEL_FORMAT_ARGB_8888` (0) to `S3CFB_WIN_CONFIG`.

The vendor kernel does **not** treat that field as already being the IDMA/DPP
format.  `decon_set_win_config()` runs `dpu_translate_fmt_to_dpp()` first:

```
caller ARGB_8888 (0) -> IDMA BGRA_8888 (3)
caller BGRA_8888 (3) -> IDMA ARGB_8888 (0)
caller RGBA_8888 (2) -> IDMA ABGR_8888 (1)
caller ABGR_8888 (1) -> IDMA RGBA_8888 (2)
```

The old code therefore reached **IDMA BGRA_8888**, whose word layout is
`B,G,R,A` / memory bytes `A,R,G,B`.  Our `0xff` alpha byte was read as the blue
channel:

```
caller word 0xAARRGGBB, memory B,G,R,A
IDMA BGRA expects word B,G,R,A, memory A,R,G,B
=> physical R = source G, physical G = source R, physical B = 0xff
```

That is a constant full-blue channel on every pixel — exactly the observed
overlay.  The previous red/orange defect had the same class of error: caller
`ABGR_8888` translated to IDMA `RGBA_8888`, whose memory layout did not match
the `R@0 G@8 B@16` diagnostic packing either.

**Live register proof (external DPP1):**

| State | `DPU_DMA1 IDMA_IN_CON` @ 0x...1008 | IDMA format |
|---|---|---|
| before | `0x02001800` | 3 = BGRA8888 (wrong) |
| after | `0x02000000` | 0 = ARGB8888 (matches 0xAARRGGBB) |

## C. Fix

`services/nuxel-display/bin/nuxel-wl-fb-ext.c`:

- Normal `0xAARRGGBB` (`R@16 G@8 B@0 A@24`) packing now passes caller
  `DECON_PIXEL_FORMAT_BGRA_8888` (3), which the kernel translates to IDMA
  `ARGB_8888` (0).
- Diagnostic `--color-order abgr` `0xAABBGGRR` (`R@0 G@8 B@16 A@24`) packing
  now passes caller `DECON_PIXEL_FORMAT_RGBA_8888` (2), which translates to
  IDMA `ABGR_8888` (1).
- The startup log now states the full mapping, e.g.
  `decon_fmt=BGRA8888->IDMA_ARGB8888(R@16 G@8 B@0 A@24)`.
- No orientation, hotplug, link-watch, timing, scan-out or internal `/dev/fb0`
  code was changed.

## D. Validation before reboot

| Check | Result | Evidence |
|---|---|---|
| On-device rebuild | `BUILD_OK` | `ext.log` |
| `nuxel-wl-fb-ext` | active, `state RUNNING`, frames increasing | `ext.state` |
| IDMA format after fix | `0x02000000` = ARGB8888 (0) | `dump2` → dmesg |
| Colour conversion self-test | `PASS (0 failures)` | `--selftest-colour` |
| Internal AMOLED bridge | `nuxel-wl-fb` active, untouched | service state |
| Orientation / hotplug code | unchanged | source diff |

The software scan-out buffer was also verified against the captured source:
mean RGB of the content area matched the compositor screenshot exactly, so the
remaining error was the DECON/IDMA input format, not the converter.

## E. Reboot verification

Normal `systemctl reboot` completed and the phone returned to Nuxel.  The
HDMI link came back on its own and `nuxel-displayd` auto-restored the external
picture with no manual command:

| Check | Result |
|---|---|
| Boot / reachability | back at `19:35:21 CET`, SSH reachable after ~35 s |
| `nuxel-displayd`, `nuxel-wl-fb-ext`, `nuxel-wayland`, `nuxel-wl-fb` | all `active` |
| DP link | `secdp=1`, `extcon DP=1` |
| Auto-restore | `restore complete generation=1 mode=mirror-portrait in 0.26s` |
| External state | `state RUNNING ... rot=0 ... color=argb`, frames increasing |
| Bridge mapping | `decon_fmt=BGRA8888->IDMA_ARGB8888(R@16 G@8 B@0 A@24)` |
| Live IDMA register after reboot | `0x02000000` at `DPU_DMA1 IDMA_IN_CON` = ARGB8888 (0) |
| Orientation authority | `transform=0`, `effective_orientation=0`, `applied=1` |
| Internal AMOLED | `nuxel-wl-fb` active; untouched |
| Source/binary persistence | source SHA-256 `93df…a701`; binary SHA-256 `295a…1869` |
| Colour converter self-test after reboot | `PASS (0 failures)` |

Raw evidence: `evidence/pwnage-102000/post-reboot.txt` and
`evidence/pwnage-102000/live-after-format-fix.txt`.

## F. Commands used

```sh
# inspect live IDMA format (dump2 writes to dmesg)
cat /sys/kernel/debug/decon/dump2 >/dev/null
dmesg | grep -A2 'DPU_DMA1 SFR DUMP'

# rebuild/restart the bridge
systemctl restart nuxel-wl-fb-ext

# colour converter self-test
/usr/lib/nuxel/nuxel-display/nuxel-wl-fb-ext --selftest-colour
```
