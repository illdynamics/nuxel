# PWNAGE-42000 re-run evidence (2026-10-31 20:30–21:04 CET)

Target: Samsung Galaxy S10+ SM-G975F / beyond2lte, kernel
4.14.253-gf7194c1d15ed-dirty. Transport: existing Wi-Fi SSH with
`~/.ssh/wicked_wqn_id_rsa`.

## Root cause and provider proof

| File | Purpose |
|---|---|
| `40-permission-store-root-cause.txt` | `/var/lib/nuxel` 0770 group mismatch, exact ACL repair, bridge-visible policy/grants |
| `41-geoclue-network-location.txt` | Acquire/read a real GeoClue network fix (coordinates redacted) |
| `42-network-location-RESTRICTED.txt` | Owner-only full network fix (mode 0600) |
| `43-gnss-truth.txt` | BCM4773 nodes, SPI driver, SSP `GPS:false`, missing firmware/runtime, diagnostic |
| `49-live-provider-lifecycle.txt` | OFF clears position, GeoClue idle auto-stop, rail remains 0 |

## Build and deployment

| File | Purpose |
|---|---|
| `45-podman-rootfs-build.log` | First full ARM64 build (superseded only for the top-bar binary) |
| `66-podman-rootfs-final-build.log.txt` | Final full ARM64 build including native status-bar glyphs |
| `67-final-image-sha256.txt` | `150a9518984048a85ec0f1c40ab0ec48f1f474e7f875491066f8b677333f6116` |
| `47-deploy-backup.txt`, `48-live-deployed-sha256.txt` | Live backup path and deployed hashes |
| `63-statusbar-backup.txt` | Native status-bar backup path |

## Top-bar visibility

| File | Purpose |
|---|---|
| `50`–`54` | Pre-fix and intermediate compositor captures |
| `55-webkit-computed-style.txt` | Served CSS computed style: blue location mask, green Wi-Fi, white sound |
| `64-statusbar-icons.png` | Native status-bar glyph test with blue location + green Wi-Fi |
| `68-statusbar-final-image.png` | Same binary built into the final image; blue + green pixels present |
| `71-topbar-final-unlocked.png` | Post-reboot live capture with Location OFF: visible green Wi-Fi glyph |

Final native `nuxel-statusbar` sha256:
`f98f5584c6e057d09925a85734f1a3fea18cc9bd841df647689e988fec8385b4`.

Pixel evidence: saturated green `(115,225,153)` for linked Wi-Fi and blue
`(104,184,255)` for an enabled network location. No dark-grey `#666` or
0.45-opacity location glyph remains.

## Tests

| File | Result |
|---|---|
| `57-tests-pytest.txt` | 44 passed |
| `58-tests-geolocation-shim.txt` | all checks PASS |
| `58b-tests-maps-core.txt` | 17 passed |

## Final state

| File | Result |
|---|---|
| `69-final-post-reboot.txt` | services active, policy OFF, rail 0, PWA `v72-p42000` |
| `70-final-topbar-unlocked.txt` | unlock→statusbar shown→lock→statusbar hidden; policy OFF; rail 0 |

Satellite GNSS remains `BLOCKED_FIRMWARE`: no compatible BBD sensor-hub patch
and no Android LHD/gpsd/HIDL runtime were found. No satellite fix is claimed.
