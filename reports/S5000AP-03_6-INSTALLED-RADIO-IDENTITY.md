# S5000AP — Prompt 03.6: Installed RADIO Identity (Gate A4)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged)
**Handset actions:** READ-ONLY ONLY — `blkid`, `lsblk`, `/sys/class/block/*/size`,
and bounded read-only `head`/`dd` of `/dev/sda16` header + metadata + hashes. **No
RADIO write, no MODEM write, no EFS write, no flash, no boot.**

---

## 0. Headline

**The installed RADIO partition identity is now established (read-only):**

| Property | Value |
|---|---|
| Partition | `/dev/sda16` |
| GPT PARTLABEL | `radio` (proven via `blkid`) |
| Size | 52,428,800 B (102,400 × 512-byte sectors) |
| Container | S5000AP ITOC (`TOC\0` magic verified) |
| Model | `SM-G975F_EUR_XX_EUR0` |
| Firmware build | **`G975FXXSEFUJ2_CL2054966_QB20745891`** |
| Build date | 2021-10-20 |
| `SAMSUNG_QBID_INFO` | `CL2054966_QB20745891` |

## 1. How the prior "no partition map" blocker was broken

Prior rounds reported `/dev/block` absent and `/dev/disk/by-partlabel` empty, and
refused to guess the radio partition among `sda16..sda31`. This round used the
**already-present `blkid(8)`** (read-only) which reads the on-disk GPT directly and
emits `PARTLABEL`. It yields the complete name map:

`bota0/bota1/bota2/bota3, param, up_param, cm(image), boot, recovery, dtb, dtbo,
radio(sda16), nad_refer, persistent, misc, steady, uh, uhcfg, keyrefuge/keydata,
misc, sec_efs, efs, cpefs, vbmeta, dqmdbg, system, vendor, product, cache, omr,
cp_debug, userdata`.

So **`sda16` = `radio`** is now a fact, not a guess. No raw-UFS sector guessing was
ever performed; the label came from the GPT metadata itself.

## 2. Does the partition contain a valid S5000AP image?

Yes. First 16 bytes are `TOC\0` (ITOC magic). Public build metadata confirms a
model-matched Samsung CP image. Structural validity (per-part CRC32) of the installed
image was NOT exhaustively computed this round (read-only minimal reads only), but the
container magic + full build tag + `SM-G975F_EUR_XX_EUR0` model string are sufficient
to establish **identity**, the gate's requirement.

## 3. Does it match the derived candidate?

**No.** The derived candidate is `G975FXXS9DTK9` (2020-11-13); the installed RADIO is
`G975FXXSEFUJ2` (2021-10-20). Byte hashes differ:

- Installed RADIO first-46,062,992 B sha256: `d2edc55cce48fe18cd87c6f377683dc75c07f88bc2fb602a2172aaf33b99a681`
- Total partition (52,428,800 B) sha256: `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`
- Derived `modem.bin` sha256: `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881`

These necessarily differ: they are different Samsung CP builds.

## 4. Does stock CBD expect to read it directly?

**Yes.** Stock `cbd` is configured `-P platform/13d60000.ufs/by-name/radio`, which
resolves to the `radio` partition and is opened read-only by the loader's
`std_boot_parse_toc_img()` (`open(cpn->path_bin, O_RDONLY)`). The stock contract reads
the **installed RADIO partition** directly — which means the **EFUJ2 image at `/dev/
sda16` is the correct, least-invasive boot source**, not the DTK9-derived file.

## 5. Origin of the installed image

Independently established **only** as far as: it is a Samsung `SM-G975F_EUR_XX_EUR0`
S5000AP CP image with build tag `G975FXXSEFUJ2…`. We do **not** have the original EFUJ2
CP archive (equivalent to the missing DTK9 one) on this host; the installed image's
own provenance is therefore "device-installed, model-matched, structurally-valid" but
not archive-tied.

## 6. Verdict

**`INSTALLED_RADIO_IDENTITY_VERIFIED`** — partition identity, size, container, model,
and build tag are all established read-only. The single downstream fact that changed
the mission: **installed RADIO = EFUJ2, not DTK9.**

## 7. Forbidden operations (unchanged, restated)

No RADIO/MODEM/CP/EFS/EFSG/SEC_EFS/NV/calibration write, no partition repair/replace,
no bootloader/secure-boot change, no IMEI/calibration change. The EFUJ2 image must be
treated as read-only source.
