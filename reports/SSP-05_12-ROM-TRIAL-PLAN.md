# SSP-05_12 — ROM First-Light Trial Plan (executed + result)

**Date:** 2026-11-22/23
**Agent:** DeepSeek-V4-Pro-Thinking

## 1. What was actually executed (authorized)

1. Rebuilt ROM-probe binary on-device (`nuxel_bbd_flash.romprobe`, hash
   `990ed411...`), offline identity check PASS (479 records, entry=0x00800161).
2. Fixed the one-way cold-cycle (patch 0028) and flashed BOOT candidate
   `760c0e44...` (kernel Image `47468a18...`).
3. Ran the bounded cold-cycle + ROM probe on the corrected kernel.

## 2. Exact trial (timestamped)

```
23:00:20Z  baseline: mcu_probe=1 shutdown=1 resetting=0
           echo 0 > mcu_power ; sleep 1 ; echo 1 > mcu_power ; sleep 1
           rail state after cycle: enabled
           /tmp/nuxel_bbd_flash.romprobe --rom-probe
```
Result:
```
autobaud sent (32 x 0x80)   -> no GetVersion reply (packets=0)
autobaud sent (36 x 0x80)   -> no GetVersion reply (packets=0)
exit 3 (ROM_HANDSHAKE_TIMEOUT)
```

## 3. Decisive transport diagnostics

```
[SSPBBD]: DBG SPI @ PZC: rx stat 0xff(PE) avail 114688, (rx_strm_fifo_ovfl)
[SSPBBD]: bcm_ssi_tx @ FD Nread 65535 is h/w overflowed of frame 8187...Fail
[SSPBBD] nuxel diag: host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 tx=80 rx=0
```
MISO all-ones → the BCM47752 SPI slave is NOT driving the bus → the chip is
powered DOWN (GPS_PWR_EN=0), not merely "silent".

## 4. Conclusion

The ROM trial was bounded and completed without valid communication.  Root cause
is a power-gate dependency (`GPS_PWR_EN`), classified `BLOCKED_POWER_SAFETY`.
No firmware write / app-start occurred.
