# NUXEL A73 — Bluetooth Status (honest)

## Hardware / kernel reality (measured on the S10+)
| item | value |
|---|---|
| BlueZ | `bluez-5.87+1.git8750129efca8-1.fc43.aarch64` (bluetoothd running) |
| `bluetoothctl` / `btmgmt` | installed (`/usr/sbin/…`) |
| rfkill | `0: bcm43xx Bluetooth` — **soft-blocked: yes**, hard-blocked: no |
| `/sys/class/bluetooth/` | **empty** — no `hci0` |
| kernel config | `CONFIG_BT_BREDR=y`, `CONFIG_BT_LE=y`, **`CONFIG_BT_BCM43XX=y`**; `CONFIG_BT_HCIUART/…BTUSB/…BTSDIO` not set; 0 loadable modules |
| dmesg | no BT/HCI/bcm43xx controller registration lines at all |

## Root cause of the blocker
The kernel carries the Broadcom 43xx BT controller driver (`CONFIG_BT_BCM43XX=y`),
but **no `hci0` is ever registered** — the controller transport/firmware
(BCM43xx HCD load path) is not completing. The rfkill device exists (power
rail) but there is no adapter for BlueZ to manage. This matches the A69/A72
finding and is a **firmware/transport boundary**, not a missing package (BlueZ
is present) and not something userspace can invent.

## Live backend readback (deployed bridge)
```
state: service_unavailable
adapter_present: false
rfkill_present: true, rfkill_soft_blocked: true, rfkill_hard_blocked: false
kernel_bt_driver: bcm43xx
detail: "no hci0 registered (no BlueZ adapter); kernel BT controller driver:
        bcm43xx (controller never registers hci0: firmware/transport);
        rfkill soft-blocked"
```

## Tile behaviour
- Tap → `bluetooth.set-powered` → BlueZ `Adapter1.Powered` write + rfkill
  unblock attempt → **actual readback**. With no adapter it returns
  `success:false`, `error:NO_ADAPTER` — the tile never claims ON.
- Status states are typed: `hardware_blocked` / `service_unavailable` / `off` /
  `on` / `unsupported`. The QS tile shows **"Bluetooth · no radio"** and a
  long-press title with the exact blocker, replacing the old
  `unavailable on this build` placeholder.
- Capability: `bluetooth:manage` (portal-gated, one-time consent).

## Pairing / A2DP
**BLOCKED_HARDWARE / BLOCKED_FIRMWARE.** No adapter ⇒ no discovery/pairing/A2DP
is possible on this kernel until an owner-supplied, licence/provenance-verified
BCM43xx HCD firmware + working transport registers `hci0`. Audio routing
(A2DP→ALSA) is a further, separate step even after `hci0` exists.

## Honest conclusion
The Bluetooth Quick Setting now has a **real status + control path** that reads
and writes BlueZ/rfkill and reports the concrete `no hci0` blocker. It is
**not** a hardware PASS: `BLOCKED_FIRMWARE` for the radio, with the exact next
dependency recorded.
