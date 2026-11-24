# Stage 06 Round 37 — CP-NV record format + MD5 integrity + provisioning toolchain

**Firmware:** ./packs SAMFW G975FXXS9DTK9 CP modem.bin (TOC: BOOT/MAIN/VSS/NV/OFFSET)
**Live:** SM-G975F S5000AP via ZeroTier 10.11.12.99; CP ONLINE, SIM READY,
PS REGISTERED_HOME, rmnet0..7 DOWN (no default EPS bearer).
**Branch:** cs/mob-round35-stage06

## 1. Authoritative TOC / memory map (corrected)

modem.bin = 46,062,992 B TOC container. Per 32-byte LE entries (w3=off w4=load w5=size):

| part | file off | load | size |
|---|---|---|---|
| TOC  | 0x0       | 0x40008000 | 0x410 |
| BOOT | 0x420     | 0x40000000 | 0x1e40 |
| MAIN | 0x2260    | 0x40010000 | 0x260c170 |
| VSS  | 0x260e3e0 | 0x47800000 | 0x5df6a0 |
| NV   | —         | 0x45600000 | 0x100000 |
| OFFSET | 0x7aa00 | 0x0       | 0x85600 |

NOTE: MAIN's linear load ends at 0x4026c170, but recovered rodata strings (e.g.
"pal_Security_NV_ITEM_Read" at file 0x210542e → load 0x421131ce) sit ABOVE that,
proving MAIN maps to multiple discontiguous load ranges (code + higher .rodata).
This corrects the round-35 "MAIN @ 0x37000" approximation.

## 2. Proven: NV integrity is MD5, NOT mandatory asymmetric signing

Physical CP EFS `nv.log` (recovered from live /dev/sda3 efs) shows the vendor NvCore
path toggles MD5 at runtime: `current MD5 off` → `MD5 on` → `MD5 off`, plus
`NvCore done` / `NvBackup` markers per domain ([RF]/[WIFI]/[IMEI]/[FINAL]/[none]).

Stored `nv_data.bin.md5` = c665d458…, computed MD5(nv_data.bin) = f9f84707… → a
self-consistent mismatch, i.e. the modem has ALREADY been booting with a stale/
off MD5. There is NO RSA/ECDSA/signing block in the NV path. This closes the
round-3x "private signing key required" blocker as UNSUBSTANTIATED.

## 3. NV container record format (physical evidence)

CP EFS `/dev/sdd1` (cpefs) holds `.nv_core.bak` (546,304 = 0x85600 B, == TOC OFFSET
size). Variable-length records, header:

    [u32 size][u32 name_ptr][u32 type][u32 aux_ptr][ payload … ]

- size     : total record size (observed 0x01,0x46,0x47,0x60,0x7e,0x80)
- name_ptr : CP runtime RAM address of the item-name string (0x4160xxxx data/BSS,
             0x4177xxxx secondary, 0x40fcxxxx text/rodata). These are RESOLVED
             AT CP BOOT only — they are NOT file offsets and NOT CRCs (this
             corrects the round-33 "crc" misreading).
- type     : 0x04 (scalar item), 0x05 (guard), 0x07 (ref), 0x80 (array).
- aux_ptr  : 0x417719cf / 0x40fc3fa9 / 0.

Recovered name pointers occur in a FIXED repeating order (0x4160bdd9, 0x4160c2e1,
0x4160c2f7, 0x4160c22f, 0x4160bb2d, 0x4160d5bf, …) = the CP NV item registry tuple.
No APN string ("internet") is stored in either .nv_core.bak or nv_data.bin → the
persistent initial-attach APN is EMPTY, confirming the round-25..34 root cause.

## 4. Recovery: pal_Security_NV_ITEM_{Read,Write}("Item %d")

Firmware string table (file 0x21053e0…0x2105590) recovers the actual NV item I/O
entry points: `pal_Security_NV_ITEM_Read : Item %d`, `pal_Security_NV_ITEM_Write :
Item %d … Success`, `pal_Security_NV_default`, `pal_Security_NV_Array_ITEM_Read`.
The item is addressed by a NUMERIC id (%d). The id is a proprietary cbd/flash-item
key; it is NOT recovered from name ordering/offsets and is NOT fabricated.

## 5. RFS NV provisioning ops (already recovered, round-30)

CP<->AP RFS (ch 245, /dev/umts_rfs0): 0x01 NV_READ, 0x15 NV_WRITE_ALL, 0x17 NV_RESTORE,
plus the boot marker RFS_UNLINK_FILE("DELETE_ALL_VIS"). Request `[u32 len][u8 op]
[u8 seq][u32 item_id][u32 length]`; response is a fixed 14-byte record.

## 6. Implemented this round (committed) — native provisioning toolchain

New PURE module `nv_items.{c,h}` + tests `test_nv_items.c`:

- `nv_record_parse()` — bound-checked .nv_core record decoder (fail-closed).
- `nv_name_ptr_span()` — name-pointer RAM/BSS/text/VSS classification.
- `nv_md5_hex()` / `nv_md5_verify()` — self-contained RFC-1321 MD5 (no OpenSSL)
  for the ACTUAL integrity path; verified against NIST "abc"/"" vectors.
- `nv_provision_policy()` — fail-closed: read-only backup ALWAYS allowed; a write
  requires (a) known numeric id, (b) non-protected item, (c) verified MD5. Never
  fabricates an id; never touches RF/cal/IMEI.

Wired into build.sh (-Werror). Host suite (12 suites) + 3000-iter fuzzer + ASan/
UBSan + aarch64 aarch64-linux-gnu-gcc cross-compile ALL PASS. The aarch64 binary
was deployed and executed on the live SM-G975F (ALL test_nv_items PASS).

## 7. Remaining single gap (unchanged, specific)

Provisioning NASU.LTE.ATTACH.APN.INFO still requires the numeric cbd/flash-item id
(string→%d) that maps to the pal_Security_NV_ITEM_Write call. Not present in repo,
nv_data.bin, .nv_core.bak, libsec-ril.so, or public source. The toolchain now
exists to safely apply the value the moment that id is established (from stock
cbd, a working identical-device reference, or further MAIN/VSS disasm).

## Safety

No NV/EFS/RADIO/BOOT/DTB/DTBO/IMEI/calibration write. Wi-Fi/ZeroTier/USB/SSH intact.
