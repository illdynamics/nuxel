# S5000AP — Prompt 03.5: CP First-Boot Proposal (Blocker F)

**Status:** PROPOSAL ONLY — **NOT authorization**. Do not execute.
**Prepared:** `2026-11-23` by engineering (owner approval PENDING).
**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4`

---

## REVISION (Prompt 03.6) — 2026-11-23

This proposal is UPDATED by Prompt 03.6 to reflect three material corrections:

1. **CBD `-t` type string RESOLVED** (retraction of prior §17.2 error): source-proven
   in cpboot_v3 @ `234b1387…` that `-t ss310` (with `protocol=sipc` +
   `use_legacy_sipc_ioctl=true`, the exynos9820-common setting) resolves to
   `SEC_SS310` = the **correct S5000AP path**. There is **no** separate `s5000ap` type
   string; `ss310` is Samsung's userspace name for Shannon 310 = S5000AP. The prior
   "`ss310` → ModAP/SIT = WRONG modem" claim was **incorrect** and is superseded by
   `reports/S5000AP-03_6-CBD-TYPE-STRING-VERIFICATION.md`.
2. **Installed RADIO identity RESOLVED** (retraction of prior §17.3 error): `blkid`
   establishes `sda16` = `radio` (52,428,800 B). Its contents are
   **`G975FXXSEFUJ2_CL2054966_QB20745891`** / `SM-G975F_EUR_XX_EUR0` — a **different
   (newer) build than the DTK9 candidate**, not byte-identical. See
   `reports/S5000AP-03_6-INSTALLED-RADIO-IDENTITY.md` and `...-CL-QB-IDENTITY-ANALYSIS.md`.
3. **Least-invasive boot source is now the installed EFUJ2 image read-only from
   `/dev/sda16`** (the stock cbd `-P .../by-name/radio` contract), NOT the DTK9-derived
   `modem.bin` file. The DTK9 candidate remains a model-compatible but different-build,
   unproven-provenance artifact (`STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`).

No change is made to the proposal's *authorization boundary*: this remains a review
document; no CP boot is authorized by this revision.

---

## 1. Exact physical device identity

- Model: Samsung Galaxy S10+ `SM-G975F` (`beyond2lte`, Exynos 9820).
- Board: `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`.
- cmdline: `androidboot.em.model=SM-G975F`, `androidboot.revision=26` (A-only, no slot).
- Kernel: `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT` (gcc 15.2.0).
- Live CP: `OFFLINE (0)` (PROVED_LIVE this round).

## 2. Git commit and worktree status

- HEAD = `45b9097f3c989347ebc8572d733ca4e3a72f63e4`, branch `cs/mob`, ahead of
  `origin/cs/mob` by 2 commits.
- Worktree dirty: `pwn-mobile/*` deleted (migrated to byte-identical `pwn-mob/*`,
  uncommitted), plus untracked round-02 tooling + reports. No staging performed this
  round; no historical report overwritten.

## 3. Firmware source / hashes / provenance / compatibility

- Primary image `modem.bin` = 46,062,992 B, sha256 `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881`.
- Container: S5000AP ITOC; BOOT/MAIN/VSS CRC32 pass; model `SM-G975F_EUR_XX_EUR0`,
  base `G975FXXS9DTK9`.
- **Provenance verdict: `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`.** Signature region
  not decoded; `NONEmrk` present; `CL1535157/QB17435920` ≠ documented
  `CL20034833/QB35905779`; original `.tar.md5` absent.
- This proposal **cannot** proceed to execution on provenance alone (gate A).

## 4. Selected CBD implementation and executable hash

- **Selected architecture: minimal native Linux bootstrap** (path C). The stock
  Bionic cbd (sha256 `c3e869fa2f…`) and cpboot_v3 rebuild are both infeasible
  natively (Bionic-linked; see CBD-RUNTIME-DECISION).
- Current native artifact is **dry-run only** (`nuxel-cpbootd`), no HW path compiled.
- Physical-ready loader hash: **not yet producible** — blocked on the S5000AP `-t`
  type/section detail (unresolved in recovered source) and installed-RADIO
  equivalence (no partition map on this boot).

## 5. Verified kernel ABI revision and header hash

- Kernel base: `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (verified: kernel checkout
  HEAD == this SHA).
- Verified UAPI header: `tools/s10plus/s5000ap-uapi/s5000ap_uapi.h`.
- `struct modem_firmware` = 28 B; `sipc5_link_header` = 6 B; `modem_sec_req` = 16 B;
  ioctl `0x6F27/0x6F22/0x6F28/0x6F40/0x6F24/0x6F53`; enum order pinned. All
  re-verified this round (21 pytest + `_Static_assert` cross-compiles).

## 6. Dependency / runtime manifest

- Native loader: glibc only (present on Nuxel) + pinned `s5000ap_uapi.h`.
- No Bionic, no Android property server, no Android SELinux `radio_device` label, no
  EFS/CPEFS mounts required (these are stock-cbd-only).
- Exclusive owner of `/dev/umts_boot0` via `flock(LOCK_EX|LOCK_NB)`.

## 7. Exact proposed operations (source-backed)

Recovered from round-03 §4 + kernel `modem_v1` handlers. **NOT to be executed now.**

| # | Operation | ioctl | Source proof |
|---|---|---|---|
| 0 | open `/dev/umts_boot0` + `umts_ipc0` | — | node exists (PROVED_LIVE) |
| 1 | STATUS read | 0x6F27 | `modem_io_device.c` returns `phone_state` |
| 2 | POWER_ON | 0x6F19 | `s5000ap_on` (`modem_ctrl_s5000ap.c`) |
| 3 | XMIT_BOOT (BOOT 7,744 B) | 0x6F40 | `shmem_xmit_boot` bounds-checked copy |
| 4 | BOOT_ON | 0x6F22 | `s5000ap_boot_on` polls cp_status ≤2 s |
| 5 | DL_START | 0x6F28 | `dload_start` + `modem_boot_confirm` |
| 6 | MAIN download (39,895,408 B) | SIPC ch 215–224 | `std_udl` frames |
| 7 | SECURITY_REQ | 0x6F53 | `shmem_security_request` → `exynos_smc` (TEE) |
| 8 | BOOT_OFF (init_cmpl ≤15 s) | 0x6F23 | `s5000ap_boot_off` (MIF_INIT_TIMEOUT) |
| 9 | BOOT_DONE confirm | 0x6F24 | `s5000ap_boot_done` (no-op) |
| 10 | STATUS == ONLINE | 0x6F27 | re-read `phone_state` |

**No guessed offset/section; secure boot is kernel+TEE-side only.**

## 8. Required privileges and device endpoints

- `root` (device nodes are `crw------- root root`, no group world).
- `/dev/umts_boot0` (boot write path), `/dev/umts_ipc0` (SIPC), `/dev/umts_rfs0`
  (may be needed later, NOT for boot), `/dev/umts_ipc1`, `/dev/umts_router`.
- Requires the deleted `/dev/block/*/by-name/radio` be resolvable to the actual
  `sdaN` radio partition OR an immutable verified file-backed source.

## 9. Expected CP state transitions

`OFFLINE(0) → BOOTING(3) [during BOOT_ON] → LOADER_DONE(6) [optional] → ONLINE(4)`.
`NV_REBUILDING(5)` is possible; `SIM_ATTACH/DETACH` only after online+SIM.

## 10. Per-stage deadlines and abort conditions

- Each stage ≤30 s (tunable `--deadline-ms`, default 30 000).
- Abort on first `rc<0`, unexpected errno (`-EFAULT/-EINVAL/-EACCES/-EAGAIN`),
  deadline expiry, signature failure (`SECURITY_REQ`), or `MIF_INIT_TIMEOUT` (15 s).
- No blind retry of other offsets/binaries/stages. Quiesce and preserve evidence on
  abort.

## 11. Read-only observations to capture

- Before/after `IOCTL_MODEM_STATUS`, journal `mif:`/`s5000ap` lines, `dmesg` modem
  excerpt, `/dev/umts_*` perms, `rmnet*` state, no-SIM `sim.json` age/provenance,
  systemd health, per-stage return codes/timestamps (redacted).

## 12. Privacy and logging restrictions

- Redact IMSI/ICCID/IMEI/MSISDN/PIN/PUK/messages/carrier APN. No raw SIPC/RFS dumps.
- No SIM/carrier state presented unless from a live authenticated API.

## 13. Network / SSH / USB preservation plan

- Keep Wi-Fi (management) and USB up throughout; do NOT disable Wi-Fi from the sole
  SSH route. Capture route table before/after. No RF-on beyond the CP boot itself.

## 14. Recovery plan and verified known-good artifacts

- Live `sda14` (boot) = `1be1ded8…` == host `boot-0029-candidate.img` (verified).
- dtb `abc9d45d…`, dtbo `de3bc025…`, recovery(sda15) `4cc71d62…` all baseline-equal.
- Rollback: `boot-0028` `760c0e44…`, `boot-0020…` `9805d519…` on host.
- No protected-partition write in the trial; BOOT-only rollback path is pre-verified.

## 15. Expected PASS criteria

- CP `OFFLINE → ONLINE` on real `IOCTL_MODEM_STATUS`, repeated ≥2×, with matching
  kernel boot-confirm log; Nuxel still booted; DT/DTBO unchanged; BOOT hash equal.

## 16. Expected FAIL criteria

- Any `rc<0`, TEE signature failure, `MIF_INIT_TIMEOUT`, unexpected state, kernel
  panic, or Nuxel/TWRP regression → `CP_BOOT_FAILED_<FIRST_STAGE>`; preserve evidence;
  do NOT loop. Note: `modem-nosim`/`modem-ready` diag fixtures currently FAIL on a
  stale-state-file fixture (documented, unrelated to live gates; see BUILD-RECEIPT §3).

## 17. Unresolved risks

1. Firmware provenance (`STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`; `CL/QB` mismatch).
2. ~~S5000AP `-t` type~~ **RESOLVED 03.6**: `-t ss310` is correct (SIPC build). See revision header.
3. ~~Installed RADIO identity unreadable~~ **RESOLVED 03.6**: `sda16`=`radio`=`G975FXXSEFUJ2` (≠ DTK9). See revision header.
4. TEE secure-boot acceptance only provable by the trial itself.

## 18. Explicit owner approval request

**Required before any execution (all three):**

1. Provide the original `CP_G975FXXS9DTK9_..._tar.md5` **or** confirm the derived
   `.lz4` pair under `/Users/wicked/.local/share/nuxel-s5000ap/G975FXXS9DTK9-CP-20261117/`
   are authoritative; resolve the `CL/QB` stamp mismatch.
2. Authorize a bounded read (TWRP-side or via a recovery-context name map) of the
   RADIO/modem partition to hash-verify it equals the derived `modem.bin`, and
   authorize the specific reviewed Trial (Prompt 04) with the above operations.
3. ~~Confirm `-t` type string~~ **RESOLVED 03.6** (`ss310` per cpboot_v3 source) — no
   owner input needed for the type string; the source is now the installed EFUJ2 radio.

This proposal is a review document only. **No CP boot, reset, or energization has
been or will be performed without explicit owner approval of the exact reviewed
trial in a separate interaction.**

---

## Final GO/NO-GO matrix

| Gate | Required | Result | Evidence | Remaining blocker | Owner input? | Device access? |
|---|---|---|---|---|---|---|
| A — Firmware provenance | Compatible, authenticated source | **UNKNOWN** (structurally valid, provenance unknown) | FIRMWARE-PROVENANCE.md | missing `.tar.md5`; `CL/QB` mismatch | **YES** | no |
| B — Kernel ABI | Verified | **PASS** | 21 pytest + `_Static_assert` re-run | — | no | no |
| C — Bootstrap implementation | Compatible executable path | **PARTIAL** (path C selected; dry-run only) | CBD-RUNTIME-DECISION.md | S5000AP `-t` type + RADIO equivalence | **YES** | **YES** (RADIO hash) |
| D — Offline build/tests | Passing | **PASS** | BUILD-RECEIPT (22+21+17 green) | — | no | no |
| E — Recovery readiness | Verified vs device | **PASS** | LIVE-RECOVERY-PREFLIGHT (all 4 hashes match) | — | no | no |
| F — Owner approval | Explicitly granted | **PENDING** | §18 | — | **YES** | — |

**Decision: `NOT_READY`** for physical CP execution (gates A unresolved + F pending).
`READY_FOR_OWNER_REVIEW` for the proposal itself (B–E pass + complete proposal).

**`AUTHORIZED_FOR_04` requires owner approval of this exact reviewed trial in a
separate interaction. No automatic progression to Prompt 04.**
