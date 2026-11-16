# PWNAGE-SSP — Test results (measured on hardware)

**Live kernel:** `#48` (`4.14.253-gf7194c1d15ed-dirty`), image
`boot-ssp-v14.img` SHA256 `7ad5183acbfeb88c0f2232c5ebbcaaa3c087039a04be51f94bb5417b27505e2a`
**Evidence:** `evidence/pwnage-ssp-20261113/`

Statuses: PASS / PARTIAL / FAIL / NOT TESTED / UNSUPPORTED.

| # | Test | Status | Measured output |
|---|---|---|---|
| 1 | Nuxel boots on the delivered image | **PASS** | no ADB recovery device after reboot; SSH login, `uname -r` returns the built kernel |
| 2 | Hub identified at probe | **PASS** | `mcu_name=BCM47752KUB1G`, `mcu_rev=BR0121080900,BR010` |
| 3 | Hub answers scanning info at probe | **PASS** | `sensor_state=0x3feff` (accel+gyro bits set) in `nuxel_hub_diag` |
| 4 | Native bring-up reaches the hub | **PARTIAL** | AP→MCU frame delivered (`Nuxel peer tx hdr=0f len=1 … -> 11`), SPI TX/RX performed (`DBG SPI @ TX: <255B = 1`), hub returns nothing |
| 5 | MCU chip-ID handshake | **FAIL** | `get_chipid … completion is timeout`, `reading ID = -1` on every attempt |
| 6 | Hub SSI stream alive | **FAIL** | `PZC: rx stat 0xff(PE)` — MISO idle high, protocol error |
| 7 | Accelerometer live data | **FAIL** | `accelerometer_sensor/raw_data` = `0,0,0` |
| 8 | Gyroscope live data | **FAIL** | `gyro_sensor/raw_data` = `0,0,0` |
| 9 | Sensor service (bridge) starts and owns the ABI | **PASS** | opens `bbd_sensor`+`ttyBCM`, relays frames, exits non-zero only on real errors |
| 10 | Sensor service produces orientation | **PARTIAL** | daemon live, `auto_state=fixed`, correctly refuses Auto with no sample |
| 11 | Display transform accepted | **PASS** | `wlr-randr --transform 270` then `normal`, read back each time |
| 12 | Display rotates from physical motion | **FAIL** | needs test 7 |
| 13 | 3× portrait→landscape→portrait | **NOT TESTED — OPERATOR REQUIRED** | no live sensor |
| 14 | Landscape in both directions | **NOT TESTED — OPERATOR REQUIRED** | — |
| 15 | Touch mapping under rotation | **NOT TESTED — OPERATOR REQUIRED** | — |
| 16 | Per-app firewall: unprivileged userns | **PASS** | `unshare -U/-Ur` as `nuxel` rc=0; `kernel.unprivileged_userns_clone=1` |
| 17 | Per-app firewall: nftables classid | **PASS** | `meta cgroup 16973825 accept` loads (live re-check at 13:15, rc=0) |
| 18 | Per-app firewall: full ruleset apply | **PARTIAL** | tool fails closed because `tun0` does not exist in this container; ruleset itself rejected at the VPN-masquerade line, no partial load |
| 19 | NFC / location / Wi-Fi icons hide when off | **PASS (source)** | `pwa/nuxel-home/js/status-bar.js`; live check NOT TESTED |
| 20 | Notification sound `nuxel-pow.mp3` + edge FX | **PASS (source)** | existing implementation |
| 21 | Edge FX screen on/off + lock/unlock toggles | **PASS (source)** | existing implementation |
| 22 | Per-app rotation Force checkbox | **PASS (source)** | `pwa/nuxel-apps/settings/apps-permissions-settings.js` |

## Raw measurements (copied from the device)

```
# nuxel_hub_diag
mcu_probe=1 shutdown=1 resetting=0 sensor_state=0x3feff enable=0x0 shub_irq=443
# accelerometer_sensor/raw_data
0,0,0
# gyro_sensor/raw_data
0,0,0
# dmesg (bring-up)
[SSPBBD] Nuxel bring-up target registered (ssp probe=1)
[SSP] MCU device ID = 85, reading ID = -1
[SSPBBD] Nuxel bring-up: initialize_mcu -> -1
[SSPBBD] Nuxel bring-up: retrying after MCU power-cycle
[SSPBBD] Nuxel bring-up: vdd_mcu_1p8 re-enabled -> 0 (enabled=1)
[SSPBBD] Nuxel peer tx hdr=0f len=1 opt=0000 payload=0 -> 11
[SSPBBD]: DBG SPI @ TX: <255B = 1, <1K = 0, …
[SSPBBD]: DBG SPI @ RX: <255B = 1, <1K = 0, …
[SSPBBD]: DBG SPI @ PZC: rx stat 0xff(PE) avail 114688, (rx_strm_fifo_ovfl)
```
