# S5000AP — Prompt 03.5: Offline Build & Test Receipt (Blocker B/D)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4`
**No handset-changing action. All results below are OFFLINE (host) re-runs.**

Confirms the round-01..03 suites and all ABI/build artifacts are still green, and
records the selected architecture (native Linux bootstrap, dry-run today).

---

## 1. Re-verified build artifacts (hashes + provenance)

| Artifact | Path |
|---|---|
| Verified UAPI header | `tools/s10plus/s5000ap-uapi/s5000ap_uapi.h` |
| ABI check fixture | `tools/s10plus/s5000ap-uapi/nuxel-s5000ap-uapi-check.c` (+ `.aarch64`, `.host`) |
| Read-only status probe | `tools/s10plus/s5000ap-uapi/s5000ap-status.c` |
| Dry-run CP coord | `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` |
| FW analyzer | `tools/s10plus/cp-firmware/analyze_cp_artifact.py` |
| Dependencies manifest | `tools/s10plus/s5000ap-uapi/dependencies.json` |

Pinned upstream (unchanged from round 03, re-confirmed this round):

| Item | Revision |
|---|---|
| Kernel ABI source | `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (linux 4.14.253) — **HEAD of kernel checkout == this exact SHA** |
| cpboot_v3 (reference) | `android_hardware_samsung_slsi-linaro_exynos` @ `234b1387…` (lineage-22.1) |
| cbd device config | `android_device_samsung_exynos9820-common` @ line 154-155 (sipc + legacy-sipc-ioctl=true) |

## 2. Toolchains

| Tool | Version |
|---|---|
| `aarch64-linux-gnu-gcc` | 15.2.0 (homebrew aarch64-unknown-linux-gnu) — matches device kernel gcc 15.2.0 |
| `/usr/bin/gcc` | Apple clang 17.0.0 (host LP64 layout check) |
| `python3` | 3.11.9 |
| `aarch64-linux-gnu-readelf` | GNU binutils (stock cbd NEEDED analysis) |

## 3. Test results (all re-run this round)

```
# Round 02 — firmware analyzer
python3 tools/s10plus/tests/test-cp-firmware-identity-offline.py
  → Ran 22 tests … OK                    [PASS]

# Round 03 — kernel ABI / layout / bounds / ioctl
python3 -m pytest tools/s10plus/s5000ap-uapi/tests/ -v
  → 21 passed                            [PASS]

# Round 01 — flash denylist preflight
python3 tools/s10plus/tests/test-flash-preflight-offline.py
  → all checks PASS                      [PASS]
```

**Total offline tests: 22 + 21 + (17 flash checks) — all PASS.**

### modem-diag selftest (honest disclosure)

```
bash tools/s10plus/a33/nuxel-modem-diag.sh selftest
  → 9/11 PASS; 2 FAIL: modem-nosim, modem-ready
```

The 2 FAILs are a **fixture-age coherence issue, NOT a regression and NOT this
round's change**. Root cause: the `sim.json` fixture files carry mtime `02:29:37Z`
while the test ran at `03:40`, i.e. age ≈ 4200 s > `sim.state_file_max_age_s=3600`,
so the diag correctly reports `sim_source=state_file-stale` + `sim_ready=unknown`,
contradicting the fixtures' `EXPECTED sim_ready=no|yes`. This is the **truthful
stale-state behavior** designed in round 01 (§4.1) working as intended; the fixtures
simply assume a fresh state file. It does not touch gates A–E. Not masked; disclosed
here and in the proposal §16.

## 4. Compile-time safety pins (re-confirmed)

- `struct modem_firmware` == 28 bytes (`_Static_assert`).
- `struct sipc5_link_header` == 6 bytes; `struct modem_sec_req` == 16 bytes.
- ioctl literals `0x6F27/0x6F22/0x6F28/0x6F40/0x6F24/0x6F53` pinned.
- `STATE_OFFLINE==0, BOOTING==3, ONLINE==4, CRASH_WATCHDOG==9`.
- `CONFIG_LINK_DEVICE_PCIE` not set → PCIe-only ioctls correctly absent.

## 5. Runtime dependency manifest (selected path C)

Native bootstrap depends ONLY on glibc (already present on Nuxel) + the pinned
`s5000ap_uapi.h`. It does **not** depend on Bionic `liblog/libcutils/libc++/
libselinux`, the Android property server, Android SELinux labels, or the EFS/CPEFS
ext4 mounts that stock cbd requires. This is the core maintainability/security
argument for path C over A/B (see CBD-RUNTIME-DECISION report).

## 6. Safety receipt (re-affirmed)

- HW-mutating ioctl path stays behind `-DNUXEL_CPBOOTD_ENABLE_HW=1` + runtime
  `--really-boot`; the shipped binaries are dry-run only.
- `nuxel-cpbootd --really-boot` on the dry-run build exits 2 with the refusal message
  (negative proof verified round 03, unchanged).
- Exclusive `flock(LOCK_EX|LOCK_NB)`; no automatic retry; no CP power-on at startup.
- No firmware byte, private key, or `cbd` blob committed or logged.

## 7. Offline bootstrap completeness (honest)

Complete today: ABI pinning, ioctl/struct verification, exclusive-ownership, error
reporting, bounds validation, negative tests, dry-run no-HW guarantee.

NOT complete today (correctly NOT claimed): the physical S5000AP boot transaction
executable, because the `-t` modem-type/section detail is unresolved in recovered
source and the installed RADIO image cannot be correlated on the current boot. These
are documented as exact owner/device blockers, not fabrications.
