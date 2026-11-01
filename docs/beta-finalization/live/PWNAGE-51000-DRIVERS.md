# PWNAGE-51000 — device capability recheck

Commands and raw output: `evidence/pwnage-51000/drivers/capability-diagnostics.txt`.

| Subsystem | State | Evidence |
|---|---|---|
| Mobile network | `NOT_SUPPORTED_ON_DEVICE` | No CP host interface, no ModemManager Shannon plugin, no SIM source, `mmcli` absent. |
| Camera | `BLOCKED_FIRMWARE` | FIMC-IS video nodes and sensor names enumerate; no media graph/subdev nodes; expected setfiles and `is-camera*.bin` absent. No frame claimed. |
| NFC | `BLOCKED_FIRMWARE` | `sec-nfc` chardev and kernel subsystem present; firmware and NFC stack absent. |
| Sensors | `PRESENT_UNREADABLE` | 9 IIO/input classes enumerate; 0 readable raw channels; SSP hub down. No synthetic values. |

No firmware was fetched, no proprietary HAL was added, no modem/NV/EFS or
unrelated partition was touched. Settings continues to show the same honest
blockers, now backed by this run’s diagnostics.
