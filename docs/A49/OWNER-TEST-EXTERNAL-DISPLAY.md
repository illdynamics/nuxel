# A49 Owner test — USB-C → HDMI (external display)

**Status: NEEDS_OWNER_TEST, hardware-first. This must never risk the USB console.**

## 1. Preserve recovery first
The S10+ has ONE USB-C port. Before plugging any adapter:
* verify an alternate diagnostic path (powered hub with a working USB data path,
  or reliable wireless admin), or
* run a controlled, owner-supervised test with timed recovery, pre-captured
  `dmesg -w` / `journalctl -f` logs and NO write/boot-critical changes.

## 2. Capability probe (read-only, safe)
```sh
nuxel-typec-diag.sh status --json      # verdict + typec/dp/drm/modules evidence
```
Record the exact adapter/dock chipset and power arrangement. Distinguish
DP Alt Mode vs DisplayLink USB graphics vs passive HDMI conversion — they are
different technologies; do not assume a passive cable works.

## 3. Stages (stop at the first unmet gate)
1. Adapter recognized AND the phone remains recoverable.
2. DP alt-mode negotiation established (or documented as missing) — see
   `/sys/class/typec/...` altmode state in `dmesg`.
3. DRM connector + EDID/modes recognized, or an explicit blocker.
4. Stable real Nuxel pixels visible on the monitor.
5. Correct hotplug/disconnect/power/audio policy + touch unaffected.

A missing `/sys/class/typec` does not itself prove the hardware lacks DP; record
whether vendor interfaces replace the generic class. If drivers/firmware are
missing, produce a researched hardware-enablement plan (source path, kernel
config, DT/driver/PHY gaps, firmware, upstream refs, risk, non-boot-critical
changes) — do NOT modify mux/PMIC/boot regulators experimentally.

Do not claim success without visible HDMI output.
