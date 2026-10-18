# USB-C HOST CAPABILITY — A34

Read-only audit (`nuxel-usb-input-audit.sh`) at 2026-10-17T10:27:11Z:

```
typec port0/data_role    = host [device]      ← current role is DEVICE
typec port0/power_role   = source [sink]      ← current role is SINK
typec port0/port_type    = [dual] source sink
typec port0/vconn_source = no
power_supply/otg/online  = 0
UDC 10c00000.dwc3        = configured
gadget UDC               = 10c00000.dwc3
xhci-hcd bound devices   = (none)
```

Kernel boot evidence:

* `usb_notifier: ccic_usb_handle_notification: Turn On Device(UFP)` when the
  laptop cable is attached.
* `dwc3 10c00000.dwc3: Turn on gadget dwc3-gadget`.
* `exynos-dwc3 10c00000.usb: dwc3_exynos_rsw_work`.
* No `xhci-hcd` device registration and no `usb 1-1` enumeration.

Interpretation:

1. The Type-C controller and the DWC3 driver **advertise** a dual-role port.
2. The running configuration is **device/peripheral**, because the live console
   gadget is bound to the only UDC.
3. `/sys/class/typec/port0/data_role` is mode `0644` (root read-only); there is
   no `/sys/class/usb_role` and no writable role switch exposed.
4. `xhci-hcd` exists as a driver but has **no bound device**, so a USB keyboard
   or mouse cannot enumerate in the current state.
5. Whether the max77705 CCIC automatically switches to DFP/host when a
   A-to-C adapter with the right CC termination is inserted is **UNPROVEN**.
   The owner's adapter has not yet been tested with persistent dmesg capture.

## Safe test plan (no flashing, no permanent role change)

1. Keep the current console working.
2. Unplug the Fedora cable; plug the mouse/adapter for ~20 s; unplug it;
   reconnect the Fedora cable.
3. Read `/var/log/kern.log` / `dmesg` for `Turn On Host(DFP)`, `xhci-hcd`
   registration, `usb 1-1` enumeration, or a `dwc3` role-switch failure.
4. Repeat with the Keychron in wired mode.
5. If the log shows `Turn On Device(UFP)` for the adapter and no xHCI bind, the
   blocker is the kernel/role-switch integration, not the adapter.

## Verdict

**USB_HOST_UNPROVEN.** A source patch is not justified until the adapter test
shows the CCIC action. No USB role change was made in this session.
