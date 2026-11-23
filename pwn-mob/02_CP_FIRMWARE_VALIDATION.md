# 02 — DEEPSEEK PRO THINKING: CP Artifact Acquisition and Integrity, OFFLINE

Apply `00_MASTER_SAFETY_AND_TRUTH.md`; read report from `01`. **No handset-changing action.** You are past the obsolete 'we cannot find modem firmware' blocker, but the artifact is NOT proved valid merely because its pathname appeared in `mobile.md`.

## Candidate from root `mobile.md`

`/Users/wicked/x/nuxel/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`

Members reportedly `modem.bin.lz4` and `modem_debug.bin.lz4`. This CP archive is **NOT inside the supplied ZIP**. Locate on owner's original host, never pretend the ZIP included it. Do not fetch other-phone firmwares or force installed partition replacement.

## Procedure

1. Check original host path exists and file type, user/owner and archive length, SHA-256; validate full TAR structure, Samsung appended MD5 trailer if applicable, and decompression integrity. TAR normally does not use per-member CRC: do not claim CRC proof without format support. Note MD5 consistency is not provenance/authenticity.
2. Copy the original immutable to a private owner-approved workspace outside tracked Git (no public paste, no logging blobs); preserve compressed members byte-for-byte. Decompress in sandbox with resource-size caps; list archive members after rejecting paths that escape destination, symlinks, device entries, duplicate/overlapping members and decompression bombs. Record compressed/decompressed hashes and sizes.
3. Inspect normal `modem.bin` as primary candidate. Extract only safe public metadata (build/model/version/container layout) and compare to **SM-G975F, bootloader compatibility and DTK9** stock provenance, existing kernel and bootloader runtime; no blind assumptions on image generation. Do not use `modem_debug.bin` as drop-in replacement. Don't redistribute firmware or private metadata.
4. Source-check proprietary signing/image container against matching publicly readable `cbd` and pinned kernel UAPI, without stripping signatures, changing offsets or bypassing TEE. Where signature authenticity cannot be established offline, mark `STRUCTURALLY_VALID_UNAUTHENTICATED_CANDIDATE` rather than 'Samsung-signed accepted'.
5. Determine whether the CP currently has an installed firmware partition that must only be read or whether normal cbd loads a primary image from read-only source. **Don't write RADIO/MODEM/CP partition.** User's BOOT/TWRP permission is not CP partition flashing approval.
6. Offline tests for missing/corrupted/truncated/wrong-model/oversized archives and poisoned members. Build a reproducible private hash/identity manifest, excluding the blobs themselves.

## Deliverables

Create `reports/S5000AP-02-CP-FIRMWARE-IDENTITY.md` + owner-private hashes/metadata and source tests. Decision table: ARCHIVE_MISSING, ARCHIVE_VALIDATED, WRONG_VARIANT, CONTAINER_UNKNOWN, MATCHED_SOURCE_CANDIDATE, REQUIRE_OWNER_INPUT. Gate 02 completes only with actual hashes, verified local file and agreement on image/container expectations. NEVER report a booted CP at this stage.

### Delegate to Flash

- Validate TAR/MD5/LZ4 and produce safe hash receipt with no firmware bytes.
- Compare model/build identity metadata and pinned tool sources.
- Test safe extraction hardening, determinism and CI fixtures.

If actual archive absent, give its exact missing path and still complete CBD and kernel ABI static work in round 03 (without fabricated image validation).
