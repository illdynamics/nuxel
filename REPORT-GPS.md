# GNSS completion report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`BLOCKED_FIRMWARE` (first failing stage: **firmware**). The Broadcom GNSS transport and SPI binding are present (`spi17.0` on `brcm gps spi`, modalias `spi:BCM4773`), but the BBD patch/loader firmware and the vendor Bionic LHD/GPS runtime are missing. `/dev/ttyBCM` is a packet transport, not an NMEA source. No receiver-reported fix exists; GeoClue network location must not be counted as GNSS.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820.
- GNSS: Broadcom BCM4773/BCM47752-family integrated path; live modalias `spi:BCM4773`.
- Confidence: **high** for the SPI transport and node names; **unproved** for firmware revision compatibility.

## 3. What already exists

| Area | Source/path |
|---|---|
| Policy/config | `configs/nuxel/gnss/gnss.json` |
| Bridge/GeoClue | `services/nuxel-bridge/`, `nuxel-geoclue-agent.service`, GeoClue config |
| Diagnostics | `tools/s10plus/a33/nuxel-gnss-diag.sh`, `tests/pwnage65000` |
| Kernel | downstream 4.14.253; `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control`; `brcm gps spi` driver |
| Userspace | no native BBD/LHD decoder in the repo; vendor `/vendor/bin/hw/lhd` and `gpsd` absent from the image |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| `nuxel-gnss-diag.sh status --json` | `state=BLOCKED_FIRMWARE`, `first_failing_stage=firmware` | `PASS_DEVICE_RUNTIME` |
| Device nodes | `/dev/ttyBCM` (`10:90`, group `audio`), `/dev/bbd_patch` (`236:3`), `/dev/bbd_control` (`236:2`) | `PASS_DEVICE_RUNTIME` |
| Driver binding | `bound:/sys/bus/spi/drivers/brcm gps spi/spi17.0` | `PASS_DEVICE_RUNTIME` |
| Firmware stage | `loader-only:/dev/bbd_patch` | `PASS_DEVICE_RUNTIME` |
| Vendor runtime | `missing:lhd,gpsd,android_linker,lhd_config,gps_config,gnss_hidl_impl` | `PASS_DEVICE_RUNTIME` |
| Userspace consumer | `no-consumer` | `PASS_DEVICE_RUNTIME` |
| NMEA stream | `nmea_stream=false` | `PASS_DEVICE_RUNTIME` |
| SSP state | kernel log repeatedly: `[SSP]: ... GPS: false`; `[SSPBBD]: ssp_down == true. returning` | `PASS_DEVICE_RUNTIME` |
| Real fix | none | `BLOCKED_HARDWARE` |

## 5. Full dependency chain

| Stage | Current state |
|---|---|
| GNSS silicon + antenna | physically present on S10+; antenna path not independently proven |
| SPI/SSP transport | `spi17.0` bound to `brcm gps spi` |
| Kernel driver | bound; exposes `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control` |
| BBD patch firmware | **missing**; loader node exists only |
| LHD/BBD protocol | **missing** native decoder; vendor LHD/GPS daemons absent |
| Position provider | no decoded position stream |
| GeoClue | may use network/IP location only; not GNSS |
| Maps/consumer | cannot receive a GNSS fix |

## 6. First failing stage

**Firmware + vendor runtime.** `/dev/bbd_patch` is a loader interface; there is no verified Broadcom sensor-hub/GNSS patch blob and no Bionic `lhd`/`gpsd` runtime. The kernel log shows the SSP is down (`ssp_down == true`) and `GPS: false`, so the receiver never reaches a streaming state. This is not an NMEA parsing problem: do not run NMEA parsers against `/dev/ttyBCM`.

## 7. Why prior attempts have not completed the feature

- `configs/nuxel/gnss/gnss.json` documents the BBD/LHD RPC design and explicitly warns that `/dev/ttyBCM` is not NMEA.
- Historical diagnostics stopped at “loader-only” and “vendor runtime missing.”
- Virtual/network GeoClue sources can make location appear to work while the GNSS receiver remains unavailable; those are different states.

## 8. Best recommended architecture

**Primary:** a lawful native BBD/LHD RPC implementation that loads the correct patch into the BCM4773, performs the sensor-hub handshake, decodes the position stream, and exports it through a GeoClue provider. This is the only route that keeps a pure Nuxel userspace.

**Fallback:** an isolated vendor runtime (Bionic `lhd`/`gpsd` + HIDL adapter) only if the required libraries are lawfully redistributable, the ABI can be isolated, and the security model is understood. This is harder to maintain and should not be the default.

**Not recommended:** treating SPI presence, raw bytes, `AT` responses, or a network IP estimate as a GNSS fix.

## 9. Required work inventory

| Area | Work |
|---|---|
| Firmware | Obtain and verify the exact BCM4773/BCM47752 patch for this board; document revision/hash/license |
| Kernel/DT | Confirm SSP/BBD control ABI, power/reset, IRQ, firmware path, suspend/resume |
| Userspace | Native BBD/LHD transport, handshake, patch loader, message decoder, timestamp/accuracy |
| Service/API | GeoClue provider, permission agent, cold/warm start, assistance policy |
| UI | Maps location source must show “GNSS” vs “network” truthfully |
| Tests | outdoor cold/warm TTFF, repeated fixes, airplane mode, suspend/resume, privacy deny |

## 10. Source/upstream research

- Broadcom BBD/LHD is a vendor sensor-hub RPC stack; no upstream mainline GNSS driver for this exact path.
- The repo has no native BBD decoder; only the policy and diagnostic exist.
- Vendor `/vendor/bin/hw/lhd` and `gpsd` are Android/Bionic and not installed in the Nuxel rootfs.

## 11. Buildability

- A native decoder can be built from public sources if the protocol is documented or reverse-engineered lawfully.
- The patch firmware and vendor runtime are not in the repo; they require owner-supplied vendor files or OEM authorization.
- No modem/GNSS partition writes are authorized.

## 12. Risks and constraints

- Wrong patch → sensor-hub/GNSS instability or a non-booting subsystem.
- Antenna/outdoor test is physically required; indoor “fixes” may be network-assisted.
- Privacy: location is sensitive; do not log coordinates or identifiers.
- GNSS and rotation share the Broadcom SSP/BBD path; coordinate ownership.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Capture a bounded BBD handshake trace; confirm patch revision | No position claim |
| 1 | Load correct patch; reach `GPS: true`/streaming | Kernel + userspace evidence |
| 2 | Decode first receiver-reported fix | Outdoor, timestamp/accuracy |
| 3 | Cold/warm TTFF and repeated fixes | Outdoor matrix |
| 4 | GeoClue provider integration | Maps shows GNSS source |
| 5 | Assistance/privacy policy and suspend/resume | Owner acceptance |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Receiver fix | fresh coordinate, timestamp, accuracy, source=GNSS, outdoors |
| TTFF | credible cold/warm times |
| Repeated fixes | stable stream over ≥10 minutes |
| Airplane/offline | no fake fix; truthful unavailable state |
| Suspend/resume | stream resumes |
| Privacy | deny → no location; source visible |

## 15. Owner inputs required

- Exact BCM4773/BCM47752 patch firmware for this board and permission to use it.
- Outdoor test session.
- Decision on whether an isolated vendor runtime is acceptable if native decoding is not feasible.

## 16. Confidence and gaps

- **Proved:** SPI binding, BBD nodes, missing firmware/vendor runtime, SSP down, no NMEA, no fix.
- **Inferred:** native BBD/LHD implementation is the cleanest long-term route.
- **Unknown:** exact patch revision, protocol details, antenna performance, assistance requirements.
