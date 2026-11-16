# GNSS repository audit — findings that should be fixed before the reflash gate

## 1. Runtime is not implemented in this checkout

The repository provides inventory/configuration, GeoClue wiring, a diagnostic script, reports, and test fixtures. It does not contain the target `lhd`, `gpsd`, Samsung GNSS HIDL service, compatible native BBD decoder, or authenticated sensor-hub patch.

The path `tools/s10plus/a33/tests/hw-subsystems/fixtures/gnss-ready/lib/firmware/gnss/bcm4773_sensorhub.patch` is a **2-byte fixture**, not real firmware. It must never be copied into an image or used as evidence of firmware readiness.

## 2. The current inventory cannot authenticate firmware

`services/nuxel-bridge/src/gnss_inventory.py` has an empty `VERIFIED_PATCH_SHA256` mapping. It can recognize a candidate filename, but no patch can pass hash-based identity verification until that allowlist is populated with a verified, device/build-specific digest. A file called `SensorHub.patch` is not proof of a BCM4773-compatible image.

## 3. The diagnostic readiness gate is weaker than the documented contract

`tools/s10plus/a33/nuxel-gnss-diag.sh` can promote to `READY_FOR_SKY` based on the presence of a plausible firmware filename, vendor paths, and transport nodes. That does not prove that:

- the firmware is the correct one for SM-G975F / the exact sensor-hub revision;
- the patch has been accepted by the loader;
- the BBD handshake succeeded;
- an LHD/GNSS provider is alive and exchanging valid packets;
- a position solution was emitted or a receiver-reported fix was achieved.

Tighten the state machine so file inventory cannot satisfy runtime stages. `FIX_VALID` should require a parsed receiver-originated location with valid timestamp/accuracy/quality fields. Keep `READY_FOR_SKY` as a pre-fix state only after confirmed patch-load + handshake.

## 4. `LhePatch` is being conflated with a firmware file path

The fetched `lhd.conf` excerpt in `34-vendor-binary-analysis.txt` is:

```ini
PortName=tcp:127.0.0.1:300; LheName=bbd; LhePatch=/dev/bbd_patch; LheBbdPacket=/dev/ttyBCM
```

Here `LhePatch` points at the **kernel loader character device** `/dev/bbd_patch`; it is not a pathname for a patch payload. The `gnss.json` documentation's separate `/system/bin/bcm_sensorhub_a1.patch` assumption is not established by that excerpt. Trace exact init/config references from the stock G975F image before selecting a payload path.

## 5. Artifact type label is misleading

The diagnostic contract labels a firmware artefact as a `character-device payload`; the patch itself should be modelled as a regular firmware file with provenance/hash, while `/dev/bbd_patch` is the character-device loader endpoint. Keep these distinct in data structures and logs.

## 6. The protocol boundary must remain explicit

The repo correctly recognizes `broadcom-bbd-lhd-rpc` and avoids treating `/dev/ttyBCM` as an NMEA stream. Preserve that. Do not attach gpsd's NMEA reader to `/dev/ttyBCM` unless the exact hardware/driver exposes a separate, proven NMEA endpoint.

## 7. Fixture tests are not hardware tests

The `gnss-ready` fixture includes a two-byte file named `bcm4773_sensorhub.patch`; passing fixture tests only demonstrates filename/state classifier behavior. It does not test hardware, firmware loading, ABI, or real GPS output. Add integration tests for hash rejection, wrong model, wrong chip generation, failed patch load, failed handshake, malformed BBD frames, stale fix, and GNSS-vs-network source labelling.

## 8. Diagnostic performance deserves attention

During this audit, `nuxel-gnss-diag.sh selftest` did not finish within a 120-second bound, and a fixture status invocation exceeded a 5-second bound. The script appears to spawn repeated Python subprocesses in its policy/firmware scans. Profile and consolidate those calls before making it part of boot-time or release gating.

## 9. Exact hardware identity must stay strict

Current live target evidence says `OF_COMPATIBLE_0=ssp,BCM4773` and `MODALIAS=spi:BCM4773`. Use that identifier as the current source-of-truth for the target driver path. Do not silently widen compatibility to BCM47752, BCM47765, Pixel firmware, or unrelated Broadcom patches based only on family naming.
