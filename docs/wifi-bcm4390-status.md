# Nuxel WiFi — BCM4390 (mustang) brcmfmac status

This file documents the honest bring-up state of the **Broadcom BCM4390**
WiFi 7 controller in the Google Pixel 10 Pro XL (mustang).

## 1. Driver stack

| Piece                    | Mainline Linux 6.12                  | Status |
|--------------------------|---------------------------------------|:------:|
| `brcmfmac` SDIO/PCIe     | Supported (SDIO + PCIe)               | ✅      |
| BCM4390 / BCM4391 chip   | **Not in upstream quirks**            | ❌      |
| Firmware blob            | Vendor-only (`brcmfmac4390{,-pcie}.bin`) | ⬜      |
| WiFi 7 (802.11be)        | Requires new firmware + chip config  | ❌      |

**Bottom line:** the `brcmfmac` driver supports Broadcom SDIO/PCIe chips in
general, but **BCM4390/4391 needs firmware shipped from the vendor** (from the
Google `vendor` partition) and a chip-quirk entry. It is **not** a matter of
flipping `CONFIG_BRCMFMAC`; you cannot claim "WiFi working" on mustang without
the firmware and a brcmfmac change.

## 2. Firmware requirements (from `firmware/manifest.yml`)

The following blobs must be extracted from the stock factory image's `vendor`
partition (see `firmware/install-firmware.sh`):

| Blob                          | Dest path                                     | Required |
|-------------------------------|-----------------------------------------------|:--------:|
| `brcmfmac4390.bin`            | `/lib/firmware/brcm/brcmfmac4390.bin`         | yes      |
| `brcmfmac4390-pcie.bin`       | `/lib/firmware/brcm/brcmfmac4390-pcie.bin`    | yes*     |
| `brcmfmac4390-pcie.clm_blob`  | `/lib/firmware/brcm/brcmfmac4390-pcie.clm_blob` | yes*  |
| `brcmfmac4390.nvm`            | `/lib/firmware/brcm/brcmfmac4390.nvm`         | yes      |
| `BCM4390.hcd` (Bluetooth 5.4) | `/lib/firmware/brcm/BCM4390.hcd`              | yes      |

\* The PCIe-specific firmware is what brings the WiFi 7 radio up; the SRC
`brcmfmac4390.bin` is the SDIO variant. mustang uses the PCIe interface.

> **Manifest verification:** `firmware/manifest.yml` now lists placeholders for
> `brcmfmac4390-pcie.bin` and `brcmfmac4390-pcie.clm_blob`. `firmware/verify-firmware.sh`
> checks those paths exist and their sha256 matches the manifest `checksum`
> values once filled in after extraction.

## 3. Verification workflow

```bash
# 1. Extract blobs from the factory image (or copy from vendor):
./firmware/install-firmware.sh mustang-factory.zip --install --no-modem

# 2. Verify presence + hashes:
./firmware/verify-firmware.sh            # expects exit 0 when all blobs valid
#    Place blob sha256 values into firmware/manifest.yml under each file's
#    checksum first, or the verifier will flag them "unknown hash".

# 3. Check the radio comes up:
ip link set wlan0 up
iw dev wlan0 info           # expect type managed
iw dev wlan0 scan           # expect APs if regulatory CLM is correct
```

## 4. Steps still pending for mustang

1. Extract vendor firmware (blocked: no factory image on hand / no device).
2. Add BCM4390 PCIe quirk to downstream `brcmfmac` (out-of-tree patch;
   upstream has no BCM4390 entry).
3. Wire the device-tree overlay to declare the WiFi PCIe device.
4. Validate 6 GHz + 802.11be after regulatory CLM.

Until these land, **WiFi is NOT "Complete"** on mustang; the `docs/driver-status.md`
row is corrected accordingly.

## 5. Related

* `docs/driver-status.md` — authoritative, corrected state table.
* `firmware/manifest.yml`, `firmware/verify-firmware.sh`, `firmware/install-firmware.sh`.
