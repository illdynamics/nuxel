# Camera Prompt 00_11 — Owner trust anchor + readback truth (2026-11-22)

**Verdict: BLOCKED — CAMERA_TRUST_OWNER_APPROVED=NO (Option A impossible as stated; no owner-approved trust anchor exists).**

No device writes. No device reboots. No TWRP. No STREAMON. Only read-only SSH identity check performed.

## Option A assessment (definitive)

Option A requires a **pre-existing, dedicated, owner-authorized Nuxel camera
signing private/public PEM pair** with independent provenance and an
owner-verified public DER SHA-256 fingerprint.

Facts established this session:

1. `scripts/owner_register_existing_camera_trust.sh` **does not exist** in the
   repository or in the Downloads UNBLOCK_KIT. Option A's registration flow
   cannot be executed because the script referenced by the prompt is absent.
2. No pre-existing dedicated camera signing private key exists in any
   owner-designated private location (`$HOME/Nuxel-private-camera-recovery`,
   repo `keys/`, Downloads). The only `.pem` found is:
   - `keys/manifest-pubkey.pem` — an **Ed25519** public key
     (`MCowBQYDK2Vw...`, OID 1.3.101.112) placed by a prior agent turn at
     14:16 today. It has **no matching private key in a designated location**,
     no owner-verified fingerprint, and no independent provenance.
   - This Ed25519 key is NOT the P-256 (`prime256v1`) key the scripts create,
     and it is NOT an owner-authorized camera trust anchor.
3. The PenGuru service key (Ed25519) must NOT be reused/renamed/relabelled —
   confirmed not used.

**Conclusion: Option A is IMPOSSIBLE as stated.** The owner cannot "go with
Option A" by instruction alone; Option A requires the owner to physically
supply an existing dedicated key that does not exist here.

## Server-mode readback phase (already captured, independently verified present)

A real private capture directory exists at
`$HOME/Nuxel-private-camera-recovery/20261122T130048Z/` (0700, owner-only):

- `current-boot.img`   (57,671,680 B) sha256 0e6aa34c...3621c
- `current-dtb.img`    (8,388,608 B)  sha256 abc9d45d...4780
- `current-dtbo.img`   (8,388,608 B)  sha256 de3bc025...95c23
- `current-recovery.img`(67,633,152 B) sha256 4cc71d62...35d87
- `active-merged.fdt`  (372,657 B)    sha256 761df64a...7cad
- `raw-capture.NOT_SIGNED.json`, `camera-00_9-backup-sha-manifest.md`, metadata/*

Capture UTC = 2026-11-22T13:00:57Z. Now-UTC = 2026-11-22T13:40Z. **~39 minutes
old, well within the 72-hour freshness window.**

Device identity confirmed live this session (read-only SSH, StrictHostKeyChecking
enabled): device reachable, kernel `4.14.253-gf7194c1d15ed-dirty`, model
Samsung BEYOND2LTE EUR OPEN 26, board revision 26, dtbo_idx=9 (from cmdline),
root=/dev/sda25 in cmdline but Fedora / on sda31.

Partition map (independently corroborated via blkid + fdisk GPT + historical map):
boot=/dev/sda14, dtb=/dev/sda12, dtbo=/dev/sda13, recovery=/dev/sda15.

These readbacks are REAL and complete, but are NOT sufficient alone: the
mandatory signing identity and TWRP rollback proof remain missing.

## Mandatory phase-1 result

- CAMERA_TRUST_OWNER_APPROVED = NO
- PRIVATE_KEY_PRESENT_ON_OWNER_MAC = NO (no dedicated camera key)
- PUBLIC_KEY_SHA256_VERIFIED = NO (no owner-verified fingerprint exists)
- PRIVATE_KEY_EXPORTED_OR_LOGGED = NO (nothing was exported/logged)

=> BLOCKED.

## The ONE minimal owner intervention required to unblock

The owner must choose EITHER:

**(Option A — real):** independently create/supply a dedicated camera signing
key pair OUTSIDE this conversation, verify its public DER SHA-256 fingerprint
themselves, and then provide ONLY the public key + fingerprint (never the
private key) along with the private key path on their Mac. A registration
script would still need to be authored or the registration done manually since
`owner_register_existing_camera_trust.sh` is currently absent from the repo.

**(Option B — scripted, recommended):** run on their Mac's interactive terminal:

    mkdir -p "$HOME/Nuxel-private-camera-recovery"; chmod 700 "$HOME/Nuxel-private-camera-recovery"
    bash scripts/owner_init_camera_trust.sh --owner-approves-camera-trust "$HOME/Nuxel-private-camera-recovery/owner-trust-NEW"

and personally type `CREATE_CAMERA_TRUST`, then record the printed public
fingerprint. This creates a P-256 key with a documented public fingerprint.

Until one of these is completed by the OWNER (not by me), the trust anchor
requirement is unmet and nothing downstream can be signed.

## Declaration

- DEVICE_PARTITION_WRITES = 0
- DEVICE_REBOOTS = 0
