# S5000AP — Round 02: CP Artifact Acquisition and Integrity (OFFLINE)

**Branch/HEAD:** `cs/mob` @ `03cd910f6c6a3ec600d1286b3265cce917c744e2` (`modem: truthful CP-first state machine + read-only CP status probe`).
**Round window:** `2026-11-23T02:55Z` → `2026-11-23T03:15Z`.
**Handset-changing actions:** **NONE.** No flash, no CP power/reset/download, no `/dev/umts_*` write, no partition read or write, no DT/DTBO/DTS, no reboot. The only handset contact attempted was a **read-only SSH identity probe**, which **failed** (see §1.1).
**Governing documents:** `pwn-mob/00_MASTER_SAFETY_AND_TRUTH.md`, `pwn-mob/02_CP_FIRMWARE_VALIDATION.md`, prior report `reports/S5000AP-01-LIVE-GATES.md`.

Classification vocabulary is the same as round 01: `PROVED_LIVE`, `CAPTURED_LIVE_OLDER`, `OFFLINE_TESTED`, `SOURCE_ONLY`, `DOCUMENTED_ONLY`, `ASSUMPTION`, `UNVERIFIED`, `BLOCKED`.

---

## 0. Headline decision

| Question | Answer | Class |
|---|---|---|
| Is the original CP `.tar.md5` present on this host? | **No.** Zero matches for `*.tar.md5`, `CP_G975F*`, `SAMFW.COM*` across `/` (excluding other volumes). | `PROVED_LIVE` (absence) |
| Exact missing path | `/Users/wicked/x/nuxel/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5` | — |
| Is there a derived, member-consistent workspace? | **Yes**: `/Users/wicked/.local/share/nuxel-s5000ap/G975FXXS9DTK9-CP-20261117` (owner uid 501, created 2026-11-17). LZ4 members decompress byte-for-byte to the stored `.bin`. | `CAPTURED_LIVE_OLDER` (derived) |
| Do the derived members pass structural checks? | **Yes**: TAR.MD5, legacy-LZ4 frame, ITOC bounds + per-part CRC32 (BOOT/MAIN/VSS) for `modem.bin`; ZIP for `modem_debug.bin`. | `OFFLINE_TESTED` |
| Does that prove the image is Samsung-signed and TEE-acceptable? | **No.** Signature authenticity cannot be established offline; metadata carries `SignerVer02` … `NONEmrk`. | `UNVERIFIED` |
| Final gate 02 decision | **`ARCHIVE_MISSING`** for the original; the derived image is **`STRUCTURALLY_VALID_UNAUTHENTICATED_CANDIDATE`**; image/container expectations are now documented for owner agreement. | — |

**No CP was booted. No CP is reported online. No "Samsung-signed accepted" claim is made.**

---

## 1. Procedure adherence and what was actually done

### 1.1 Handset contact (read-only)
SSH to every known ZeroTier endpoint from the owner's `~/.ssh/known_hosts` / config (`10.20.30.22:22`, `10.11.12.22:22`, `10.11.12.222:666`, `10.20.30.16:22|666`) returned **connection refused or timeout**. Round 01's SSH link (`root@<device>` over ZeroTier) is **not reachable in this run**.

Consequence: the read-only CP-partition facts that would ideally be refreshed (live `IOCTL_MODEM_STATUS`, `/dev/umts_boot0` behaviour, `dmesg` CP messages) are **`CAPTURED_LIVE_OLDER`** from round 01, not `PROVED_LIVE` this round.

### 1.2 Original-host search (exhaustive)
Commands run (read-only):
```
find / -xdev -iname '*.tar.md5'            → no results
find / -xdev -iname 'CP_G975F*'            → no results
find / -xdev -iname '*SAMFW.COM*'          → only a Chrome IndexedDB path (browser cache, not firmware)
find /Users/wicked -iname '*G975FXXS9DTK9*'→ three derived workspaces (camera, ssp, s5000ap)
mdfind -name 'CP_G975FXXS9DTK9'            → no archive
```
The owner ZIP in `~/.Trash/NUXEL_S5000AP_MOBILE_RECOVERY_V1.zip` contains **only prompt documents** (`02_CP_FIRMWARE_VALIDATION.md`, `04_CP_BOOT_CONTROLLED_TRIAL.md`, `06_SIM_LTE_MODEMMANAGER.md`); **no CP archive**. This confirms: **the CP archive was never inside the supplied ZIP**, and `mobile.md`'s claim that it "has been found" is **not backed by a present file** on this host today.

### 1.3 Private workspace (outside tracked Git)
`/Users/wicked/.local/share/nuxel-s5000ap/S5000AP-02-private/` (mode 0700) contains only **receipts and derived TAR repacks**, never original blobs:

| File | Purpose |
|---|---|
| `receipts/existing-cp-workspace.sha256` | SHA-256 of the derived workspace files |
| `receipts/archive-probe/analysis.json` | `ARCHIVE_MISSING` decision for the documented path |
| `receipts/repack/analysis.json` | Full analyzer output for the derived repack |
| `receipts/identity-receipt.json` | Machine-readable identity/hashes metadata |
| `extract/repack-from-existing.tar.md5` | Repack of the **existing derived** members for tool validation (not the original) |

Nothing proprietary was pasted, committed, or logged in Git. The repack exists only because the original is absent, and it is **explicitly marked** as derived in the receipt.

---

## 2. What the derived artifacts actually are (measured, not assumed)

### 2.1 File identity

| File | Size | SHA-256 | Type |
|---|---|---|---|
| `modem.bin.lz4` | 24,414,752 | `05371984d45f0bc33ebd06e189eaf6f298a468fc7525a479fd60ed320b5eacde` | legacy LZ4 frame (`04 22 4D 18`), independent blocks, content checksum on |
| `modem.bin` | 46,062,992 | `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881` | S5000AP ITOC container |
| `modem_debug.bin.lz4` | 3,535,942 | `816c31160da7790548d64aa5c54d6b31950b4988f59944c72bc0639a1b62b971` | legacy LZ4 frame |
| `modem_debug.bin` | 5,242,880 | `8d1c4e10e57d5b668d08de4aa284a44a145da3c4928a9d60b0206e1acd7d67d2` | **ZIP archive** |
| `stock-cbd/cbd` | 494,000 | `c3e869fa2f78b1e8141cac58602c2a6fb852e31d5c08349ba969c75ef78f7b83` | AArch64 ELF shared object (`/system/bin/linker64`, stripped) |

**Decompression identity proof:** `lz4 -dc members | sha256sum` equals the stored `.bin` hashes exactly (checked in-memory, no temp file). This proves the `.bin` came from *this* `.lz4`, not that the pair came from Samsung's original archive.

### 2.2 `modem.bin` container layout (ITOC)

The decompressed image begins `TOC\0` followed by a fixed 32-byte ITOC entry table (16 entries, 8 × little-endian `u32`). Verified entry layout:

| Part | Offset | Load addr | Size | Stored CRC32 | Computed CRC32 | Match |
|---|---|---|---|---|---|---|
| `TOC` | 0 | `0x40008000` | 1,040 | 0 | (n/a) | — |
| `BOOT` | `0x420` (1,056) | `0x40000000` | 7,744 | `0x49B47D10` | `0x49B47D10` | ✅ |
| `MAIN` | `0x2260` (8,800) | `0x40010000` | 39,895,408 | `0x325CFAED` | `0x325CFAED` | ✅ |
| `VSS` | `0x260E3E0` (39,904,224) | `0x47800000` | 6,157,984 | `0x6AF5BEAE` | `0x6AF5BEAE` | ✅ |
| `NV` | 0 | `0x45600000` | 1,048,576 | 0 | (staging image) | — |
| `OFFSET` | `0x7AA00` (502,272) | 0 | 546,304 | 0 | (n/a) | — |

`VSS` ends at **46,062,208**, which is exactly the start of the appended MBN metadata block — the IB/ITOC partition covers the entire payload, no gaps.

**CRC caveat (important):** the ITOC checksums are Samsung's *own* per-part CRC32. They are **not** a TAR per-member CRC (TAR v7/ustar/gnu/pax has none), and they are **not** signature verification. They prove internal consistency of this decompressed blob only.

### 2.3 Appended MBN metadata block (public strings only)

Located at offset **46,062,208** (784 bytes before EOF):

| Field | Observed value |
|---|---|
| Signer | `SignerVer02` |
| Marker | `QBR` |
| Build tag | `G975FXXS9DTK9_CL1535157_QB17435920201113015242` |
| Model / region | `SM-G975F_EUR_XX_EUR0` |
| unsigned marker | `NONEmrk` |
| inner image name | `modem.bin` |
| signature region | 784 bytes, **not decoded, not validated, not stripped** |

**Authenticity:** the image is labelled `STRUCTURALLY_VALID_UNAUTHENTICATED_CANDIDATE`. Offline we cannot verify RSA/ECDSA chains, cannot check the Samsung certificate, cannot check TEE/RPMB acceptance, and **cannot** claim "Samsung-signed accepted". `NONEmrk` is a metadata field, not proof.

### 2.4 Build identity comparison

| Source | Build / model | Match to SM-G975F, DTK9? |
|---|---|---|
| MBN metadata (this image) | `G975FXXS9DTK9_CL1535157_QB17435920201113015242`, `SM-G975F_EUR_XX_EUR0` | **exact model + exact DTK9 base** |
| Root `mobile.md` target archive filename | `CP_G975FXXS9DTK9_..._CP17435927_CL20034833_QB35905779_REV01_...` | `CL` and `QB` **differ**: `CL1535157` vs `CL20034833`; `QB17435920` vs `QB35905779` |
| AP provenance in repo (`firmware/s10plus/camera-stock-DTK9.json`) | `G975FXXS9DTK9` (AP zip sha256 `bf00219f…`) | base build matches |
| Live device (round 01) | `SM-G975F`, `beyond2lte`, `EXYNOS9820`, `revision=26` | model/SoC match |

**Interpretation:** the derived `modem.bin` is a **DTK9-family image** whose `CL`/`QB` stamp does **not** match the target CP filename quoted in `mobile.md`. This is the concrete evidence that the path quoted in `mobile.md` is **not proved to be the artifact we have**. The difference is consistent with a *different CP component stamp* (AP vs CP release stamps differ in Samsung practice), but absent the original archive we cannot prove that; we therefore mark this **variant identity unresolved** and require owner input (§6).

### 2.5 `modem_debug.bin` is not a modem image

`modem_debug.bin` decompresses to a **ZIP archive** (`PK\x03\x04`), not an ITOC/MBN container. It is correctly excluded from all drop-in candidate paths.

---

## 3. Stock `cbd` and kernel ABI (static `SOURCE_ONLY` / offline inspection)

### 3.1 Stock `cbd` (proprietary, owner-local, not in Git)

`strings` against `/Users/wicked/.local/share/nuxel-s5000ap/G975FXXS9DTK9-CP-20261117/stock-cbd/cbd` shows:

- A **configured** invocation in `init.baseband.rc`:
  `/vendor/bin/cbd -d -tss310 -bm -mm -P platform/13d60000.ufs/by-name/radio`
- Modem-type handlers: `-t ss310`, `-t s5100`, `cmc22x/cmc222` present; **no explicit `s5000`/`s5000ap` string**.
- CP-boot path strings: `IOCTL_MODEM_XMIT_BOOT`, `IOCTL_MODEM_BOOT_ON`, `IOCTL_MODEM_BOOT_DONE`, `IOCTL_MODEM_STATUS`, `IOCTL_MODEM_RESET`, `IOCTL_MODEM_DL_START`, `IOCTL_MODEM_CP_UPLOAD`, `IOCTL_MODEM_DUMP_*`.
- ITOC validation strings: `invalid TOC`, `TOC has no m_offset`, `invalid TOC : There is no NV`, `security check fail for TOC`.
- NV reads from `/mnt/vendor/efs/nv_data.bin`, `fsm_data.bin`, `nv_5g_data.bin`; control node `/sys/class/sec/switch/check_cpboot`.

**Open questions for round 03 (not guessed here):** does `-tss310` internally route to the S5000AP path, or does the S5000AP require a distinct type string? The proprietary binary's dispatch table is not resolvable from `strings` alone. This is flagged `CONTAINER_UNKNOWN` in §5.

### 3.2 Kernel ABI (pinned source)

`kernel/s10plus/.build/src.polluted.case-insensitive/drivers/misc/modem_v1/modem_prj.h`:

| ioctl | Encoding |
|---|---|
| `IOCTL_MODEM_ON` | `_IO('o',0x19)` = `0x6F19` |
| `IOCTL_MODEM_BOOT_ON` | `_IO('o',0x22)` = `0x6F22` |
| `IOCTL_MODEM_BOOT_DONE` | `_IO('o',0x24)` = `0x6F24` |
| `IOCTL_MODEM_STATUS` | `_IO('o',0x27)` = `0x6F27` |
| `IOCTL_MODEM_XMIT_BOOT` | `_IO('o',0x40)` = `0x6F40` |
| `IOCTL_MODEM_DL_START` | `_IO('o',0x28)` |

`struct modem_firmware` (`modem_prj.h:180`) is `{u64 binary; u32 size; u32 m_offset; u32 b_offset; u32 mode; u32 len;} __packed` → 32 bytes on AArch64.

`enum modem_state` order (verified): `OFFLINE=0, CRASH_RESET=1, CRASH_EXIT=2, BOOTING=3, ONLINE=4, NV_REBUILDING=5, LOADER_DONE=6, SIM_ATTACH=7, SIM_DETACH=8, CRASH_WATCHDOG=9`.

`modem_io_device.c` handlers show:
- `IOCTL_MODEM_XMIT_BOOT` copies `struct modem_firmware` from user, validates `size/len/m_offset` against the CP memory window, then `copy_from_user` into `v_base + m_offset`. **No file-path open.**
- `IOCTL_MODEM_STATUS` returns the kernel `mc->phone_state`.

This is the ABI the stock `cbd` must match, and it is now pinned.

### 3.3 Source of the CP image at boot

The kernel modem driver **does not open `modem.bin` from a file path**. The image is supplied by userspace through `IOCTL_MODEM_XMIT_BOOT`. Stock `cbd` is configured with `-P platform/13d60000.ufs/by-name/radio`, which resolves to **`/dev/block/platform/13d60000.ufs/by-name/radio`** — i.e. the **radio partition**, which the `cbd` daemon opens and streams. So the CP currently has an **installed firmware partition that stock `cbd` reads**; the derived `modem.bin` is the **partition image payload**, not a runtime file to be dropped into `/vendor/firmware`.

**Consequence (safety):** any future "use this image" step refers to the **radio partition contents**, and **must not** be done by writing `radio`, `RADIO`, `MODEM`, `CP`, `cpefs`, or `efs`. Nothing in this round touches those partitions.

---

## 4. Offline hardening tests and CI

New tooling (committed on `cs/mob`):

| Path | Purpose |
|---|---|
| `tools/s10plus/cp-firmware/analyze_cp_artifact.py` | Read-only TAR.MD5 / LZ4 / ITOC / MBN-metadata analyzer; never writes the input, never prints bytes |
| `tools/s10plus/cp-firmware/tests/test_analyze_cp_artifact.py` | **22 unit tests**, synthetic fixtures only |
| `tools/s10plus/tests/test-cp-firmware-identity-offline.py` | CI discoverable wrapper |

Verification commands and results:

```
python3 tools/s10plus/tests/test-cp-firmware-identity-offline.py
  → Ran 22 tests in 0.017s  OK
python3 -m py_compile tools/s10plus/cp-firmware/analyze_cp_artifact.py ...
  → COMPILE_OK
analyze_cp_artifact.py <real derived repack> --out <private>
  → {"decision": "ARCHIVE_VALIDATED", "checks": 11}
analyze_cp_artifact.py <documented archive path> --out <private>
  → {"decision": "ARCHIVE_MISSING"}
```

### 4.1 Test coverage (each case asserted)

| Case | Assertion |
|---|---|
| Valid archive (2 members, ITOC + ZIP) | `ARCHIVE_VALIDATED`; hashes equal known values |
| MD5 trailer mismatch | `ARCHIVE_VALIDATED_FAILED` (`samsung_md5_trailer` false) |
| Truncated archive | `ARCHIVE_VALIDATED_FAILED` |
| Corrupted LZ4 payload | `ARCHIVE_VALIDATED_FAILED` (`lz4_decompress` false) |
| ITOC part CRC mismatch | `ARCHIVE_VALIDATED_FAILED` (`itoc_part_crc32` false) |
| Trailing garbage after MD5 | `ARCHIVE_VALIDATED_FAILED` |
| Not a TAR | `ARCHIVE_VALIDATED_FAILED` |
| Wrong member name | `ARCHIVE_VALIDATED` but name preserved (no guessing) |
| Path traversal member (`../evil`) | rejected |
| Absolute path member (`/etc/passwd`) | rejected |
| Symlink / hardlink member | rejected |
| Device / FIFO member | rejected |
| Duplicate member name | rejected |
| Oversized member (> cap) | rejected before buffering |
| No members | rejected |
| Zero-block TAR padding | tolerated before MD5 |
| Member size ≠ LZ4 frame length | rejected |
| Extra bytes after LZ4 frame | rejected |
| Analyzer does not modify source | SHA256 before/after equal |
| Determinism (repeat analysis) | byte-identical JSON minus volatile file metadata |
| ITOC bounds overflow | rejected |

A PASS here is `OFFLINE_TESTED` and is not a phone capability.

---

## 5. Decision table

| Decision | Meaning in this round | Evidence |
|---|---|---|
| **`ARCHIVE_MISSING`** | **FINAL for the original.** The documented `.tar.md5` does not exist on this host. | exhaustive `find` + analyzer `ARCHIVE_MISSING` receipt |
| **`ARCHIVE_VALIDATED`** | Achieved **only** for the derived repack, proving the tooling works on the real member bytes. **Does not** mean the original archive was validated. | `receipts/repack/analysis.json` |
| **`WRONG_VARIANT`** | **Not established** but **unresolved**: MBN metadata build `CL1535157 / QB17435920` does not match `mobile.md` target `CL20034833 / QB35905779`. Model (`SM-G975F_EUR_XX_EUR0`) and DTK9 base **do** match. | §2.4 |
| **`CONTAINER_UNKNOWN`** | Signature authenticity **unknown**; `cbd` `-tss310` → S5000AP dispatch **unproven**. | §2.3, §3.1 |
| **`MATCHED_SOURCE_CANDIDATE`** | The derived image is a **structural + model-level** candidate for stock `cbd` on the radio partition; it is **not** a proven boot candidate. | §2, §3 |
| **`REQUIRE_OWNER_INPUT`** | Yes: exact original archive (or explicit confirmation that the derived pair is the authoritative one), plus agreement on image/container expectations. | §6 |

**Gate 02 does not complete as proven: hash-verified original local file is absent.** It does complete all offline work possible without it: structural validation, container decoding, model/build identity, ABI pinning, and source-of-image determination.

---

## 6. Owner input required (exact, minimal)

1. **Provide the original archive** at the exact path, *or* confirm that `/Users/wicked/.local/share/nuxel-s5000ap/G975FXXS9DTK9-CP-20261117/{modem.bin.lz4,modem_debug.bin.lz4}` are the authoritative extraction of it. If providing it, no need to re-share bytes publicly; the private workspace already exists and is owner-only.
2. **Confirm the `CL`/`QB` stamp expectation:** the image carries `CL1535157 / QB17435920`; `mobile.md` names `CL20034833 / QB35905779`. This is the one unresolved identity gap.
3. **Agree on image/container expectations:** that the CP source is the **radio partition**, passed to the kernel via `IOCTL_MODEM_XMIT_BOOT`, and that the derived `.bin` is a 46,062,992-byte terminal ITOC MBN — not a `/vendor/firmware` file.

No hardware-changing approval is being requested in round 02.

---

## 7. What was intentionally NOT done

- **No `RADIO`/`MODEM`/`CP` partition read or write.**
- **No `/dev/umts_*`, `/dev/block/*`, or `/sys/class/sec/*` write.**
- **No `cbd` execution** (no CP boot trial).
- **No signature stripping, offset patching, TEE bypass, or key extraction.**
- **No `modem_debug.bin` promotion** to a drop-in path.
- **No DT/DTBO/DTS/DTC/overlay/fdtput/repack**, no kernel config or patch.
- **No redistribution** of proprietary firmware or `cbd`.

---

## 8. Per-round mandatory reply (contract §7)

1. **HEAD/branch/clean state:** `cs/mob` @ `03cd910f…`; worktree dirty with round-01 pre-existing changes plus new `tools/s10plus/cp-firmware/` and the CI wrapper. Live kernel/boot/DT/CP state: **not re-probed this round** (SSH endpoints refused/timed out). Last known: kernel `4.14.253-gf7194c1d15ed-dirty`, BOOT `1be1ded8…` (`CAPTURED_LIVE_OLDER`), CP **OFFLINE (0)** (`CAPTURED_LIVE_OLDER`, 2026-11-23T01:34–01:35Z).
2. **Files/source studied:** `pwn-mob/00`, `pwn-mob/02`, `reports/S5000AP-01-LIVE-GATES.md`, root `mobile.md`, owner-local `stock-cbd` strings + `init.baseband.rc`, pinned `modem_v1` (`modem_prj.h`, `modem_io_device.c`, `link_device_shmem.c`, `modem_ctrl_s5000ap.c`). First failing gate is still **`cp_status` = OFFLINE** on the live device; for gate 02 specifically, the first failing check is **`ARCHIVE_MISSING`**.
3. **Smallest source changes + verified builds:** new read-only analyzer (stdlib + `python-lz4`), 22-test suite, CI wrapper. All commands above pass. No production code path (diag, probe, policy) was changed this round.
4. **Staged files / installations / rollback / flash:** no device installation; no flash; no rollback needed. Host-only private receipts in `S5000AP-02-private/` (not committed). Stray `"echo ok"` file accidentally created by a mistyped shell command was removed.
5. **Hardware vs simulation:** §1.1 (no successful handset contact), §2 (derived artifacts), §4 (offline). Everything real is hashed; everything simulated is labelled.
6. **Capability matrix:** LTE **BLOCKED**, SMS **BLOCKED**, Voice **BLOCKED**, IMS/VoLTE **BLOCKED** — unchanged from round 01 (CP offline; firmware not proven).
7. **Next highest-value task / blocker:** round 03 offline work is **not blocked** — pin `cbd` source revision against the now-measured ABI, diff `modem_prj.h` / `struct modem_firmware` / ioctl set, and resolve the `-tss310` → S5000AP dispatch from public source. Blockers for first CP boot remain: original archive absent (or owner confirmation), CP offline, no authorized CP trial.

---

## 9. Reproducible commands

```bash
# 1. Confirm original absence (read-only)
find / -xdev -iname 'CP_G975F*' 2>/dev/null
python3 tools/s10plus/cp-firmware/analyze_cp_artifact.py \
  "/Users/wicked/x/nuxel/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5" \
  --out /Users/wicked/.local/share/nuxel-s5000ap/S5000AP-02-private/receipts/archive-probe
#   → {"decision":"ARCHIVE_MISSING"}

# 2. Exercise the analyzer on the derived member bytes
python3 tools/s10plus/cp-firmware/analyze_cp_artifact.py \
  /Users/wicked/.local/share/nuxel-s5000ap/S5000AP-02-private/extract/repack-from-existing.tar.md5 \
  --out /Users/wicked/.local/share/nuxel-s5000ap/S5000AP-02-private/receipts/repack
#   → {"decision":"ARCHIVE_VALIDATED","checks":11}

# 3. Offline test suite
python3 tools/s10plus/tests/test-cp-firmware-identity-offline.py
#   → Ran 22 tests ... OK
```
