# S5000AP — Prompt 03.5: CBD Runtime Decision (Blocker B/C)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4`
**No handset-changing action.**

Selects a real, compatible CP-bootstrap execution path (or marks it blocked) with
source-backed evidence. The prior dry-run `nuxel-cpbootd` is acknowledged as a
planning/fence artifact only, NOT a physical bootstrap.

---

## 1. Candidate A — Stock Samsung `cbd` in an isolated compatible runtime

**Measured on the owner-private blob** `/vendor/bin/cbd` (sha256 `c3e869fa2f…`):

| Property | Value |
|---|---|
| Format | ELF 64-bit AArch64 shared object, dynamically linked, stripped |
| Interpreter | `/system/bin/linker64` (Android Bionic dynamic linker) |
| NEEDED libs | `liblog.so`, `libcutils.so`, `libc++.so`, `libc.so` (Bionic), `libm.so`, `libdl.so` |
| Runtime deps (init.rc) | `u:r:cbd:s0` SELinux, groups `radio cache inet misc audio …`, `/mnt/vendor/efs` + `/mnt/vendor/cpefs` ext4 mounts, Android `ro.vendor.multisim.simslotcount` property |

**Verdict: INFEASIBLE without an Android Bionic runtime.** Every NEEDED library and
the dynamic linker are Android-only; none exist on Nuxel's glibc/systemd rootfs.
"An isolated compatibility runtime" would require porting the entire Bionic libc+
liblog+libcutils+libselinux+property server to Nuxel — that **is** introducing the
Android framework dependency the mission forbids, for no ABI benefit (the ioctl
surface is already pinned in round 03). Additionally, `sepolicy/vendor/cbd.te`
grants `radio_device:chr_file rw_file_perms` under Android SELinux, which Nuxel does
not model.

## 2. Candidate B — Reproducible legacy-compatible `cpboot_v3` build

**Pinned source** `android_hardware_samsung_slsi-linaro_exynos` @
`234b138716426c36ed801a71052bc144f7d8d806` (lineage-22.1), `cpboot_v3/Android.bp`:

```
cc_binary { name: "cbd", ...
  shared_libs: ["liblog", "libcutils", "libc", "libselinux"],
  include_dirs: ["bionic/libc/bionic"],
  cflags: [ ... "-DCONFIG_TYPE_MODAP", "-DCONFIG_TYPE_EXT" ] + protocol-select + legacy-ioctl-select,
}
```

- Links Bionic `liblog/libcutils/libc/libselinux` → **no glibc build path exists**.
- `cpboot_v3` did not exist at lineage-18.1 (DTK9 era): line 165 of the 18.1
  `proprietary-files.txt` ships `vendor/bin/cbd` as a **prebuilt**, and the source
  only appears at lineage-20/22.1, targeting a **newer** Android Bionic than DTK9.
- Even a hypothetical glibc port would need the Android property server
  (`/dev/__properties__`) and the `radio_device` SELinux label.

**Verdict: INFEASIBLE natively for the same Bionic-dependency reason as A.** The
`-DLEGACY_SIPC_IOCTL` ABI path (proven correct in round 03) does not change the
link-time Bionic dependency.

## 3. Candidate C — Minimal native Linux bootstrap

**Selected.** This is the only path that (a) satisfies the exact kernel ABI already
pinned and statically asserted in `s5000ap_uapi.h`, (b) introduces zero Android
runtime into Nuxel, and (c) preserves Samsung's secure-boot flow **unchanged** —
because the secure-boot signature check is performed **inside the kernel + TEE**
(`IOCTL_SECURITY_REQ` → `shmem_security_request` → `exynos_smc`), never in the
userspace loader. A native loader only needs to:

1. Open `/dev/umts_boot0` (exclusive) and stream the ITOC BOOT/MAIN stages via
   `IOCTL_MODEM_XMIT_BOOT` with kernel-validated `struct modem_firmware` bounds.
2. Issue the exact ioctl sequence recovered in round 03 §4
   (`POWER_ON → XMIT_BOOT → BOOT_ON → DL_START → MAIN/SIPC download → SECURITY_REQ →
   BOOT_OFF → BOOT_DONE → STATUS`).
3. Never compute or trust the signature (TEE does it).

**Constraint (honest):** the concrete implementation is **NOT complete enough to
declare physical-ready** because the S5000AP `-t` type mapping is unresolved in the
recovered source (the only recovered `-tss310` branch instantiates the WRONG modem
type, `BootDumpModap`, see FIRMWARE-PROVENANCE §5). Until the correct S5000AP boot
type/SIPC framing details are pinned (owner DTK9 runtime or a bounded live trace),
the native loader can only be a **dry-run coordinator with a complete, source-backed
plan** — which is exactly what `nuxel-cpbootd` already is.

## 4. Comparison matrix

| Criterion | A (stock Bionic cbd) | B (cpboot_v3 rebuild) | C (native bootstrap) |
|---|---|---|---|
| Kernel ABI fidelity | High (Bionic, legacy `_IO`) | High under `-DLEGACY_SIPC_IOCTL` | High (pinned, `_Static_assert`) |
| Firmware source compatibility | Reads RADIO partition (correct) | Reads RADIO partition (correct) | must be wired to immutable verified input |
| Required runtime deps | Bionic+selinux+props+efs/cpefs | Bionic+selinux+props | glibc only |
| Reproducibility | N/A (proprietary blob) | N/A (no glibc path) | Full (sources + toolchain in-tree) |
| Maintenance burden | High (Android compat layer) | High | Low (native service) |
| Security | adds Android SELinux/props | adds Android SELinux/props | least-privilege systemd/udev only |
| Implementation completeness | 0% runtime on Nuxel | 0% | dry-run + plan complete |
| Hardware-only uncertainties | `-tss310` type mismatch | `-tss310` type mismatch | same + SIPC framing detail |

## 5. Decision

**Selected path: C (minimal native Linux bootstrap), in dry-run form today.**

A dry-run-only coordinator is **not** a physical bootstrap; the mission requires
that this round NOT claim physical-readiness. The honest state is:

- The **ABI contract and boot sequence are proven** (round 03 + this round's
  re-verification).
- The **executable path is selected** (C) with rationale.
- The **blocking unknown** is the S5000AP `-t` type/section detail, which requires
  owner input (real DTK9 vendor runtime or a bounded live trace) and, for
  installed-image equivalence, physical device access.

The bootstrap is therefore **PARTIAL / BLOCKED on the type-string + provenance**,
not fabricated as ready. No hardware-changing operation is authorized or attempted.
