# NUXEL A74 / 23000 — USB detach sequence (real event path)

```
physical cable pull
   │
   ├─ Type-C / CCIC (max77705-usbc) : CC detach IRQ → data_role [device]→[none]
   │      (safe sysfs: /sys/class/typec/port0/data_role)
   │
   ├─ DWC3 gadget controller (10c00000.dwc3): disconnect event; FSYS0 power
   │      domain (pd-fsys0a) is powered OFF, controller runtime-suspended.
   │      UDC gadget state may stay "configured" (stale) on Samsung 4.14.
   │
   ├─ power_supply: usb/ac `online` → 0 (charging input lost)
   │
   ├─ nuxel-console (initramfs, PIDs 3525/3526): holds /dev/ttyGS0; the tty
   │      read may block/EOF but the daemon NEVER reboots; no teardown path.
   │
   ├─ nuxel-pwa-host (lockscreen host): 250ms indicator timer + uevent handler
   │      → ind_pc_connected_ex()
   │         → ind_udc_configured()            (sysfs, safe)
   │         → ind_typec_device_role()         (sysfs, safe)
   │         → ind_dwc3_link_on()  ✘ REMOVED   (debugfs register read → SLVERR)
   │
   ├─ nuxel-http-bridge (api.py) 15s poll → system_indicators.usb_connection()
   │         → _dwc3_link_on()    ✘ REMOVED
   │
   └─ KERNEL: concurrent debugfs read of 0x10C0C000 while FSYS0 is power-gated
              → synchronous external abort / ITMON SLVERR
              → "Watchdog detected hard LOCKUP on cpu 0"
              → s3c2410-wdt reset after 5 s
              → REBOOT  (boot ID changes)
```

### Ownership and risk per hop
| hop | owner | synchronous? | teardown risk |
|---|---|---|---|
| CC detach | max77705-usbc IRQ | kernel IRQ | none |
| FSYS0 power gate | DWC3/PM | kernel workqueue | none |
| UDC stale state | gadget framework | kernel | stale `configured` |
| power_supply online | charger driver | kernel | none |
| ttyGS0 EOF | nuxel-console | userspace | none (no reboot) |
| indicator read | nuxel-pwa-host / bridge | userspace | **debugfs register read** (removed) |

The repaired path reads only sysfs/proc; no hop dereferences a power-gated
register block.
