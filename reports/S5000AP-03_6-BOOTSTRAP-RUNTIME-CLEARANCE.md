# S5000AP — Prompt 03.6: Bootstrap Runtime Clearance (Gates B/C2/C3)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged)
**No handset-changing action.**

---

## 0. Headline

The bootstrap **execution path** choice (native Linux loader) is unchanged from
round-03.5, but **one false blocker has been removed**: the `-t` type-string question
is now RESOLVED (`ss310` == correct, see CBD-TYPE-STRING report). The remaining honest
gaps are (a) Bionic-vs-glibc for the stock cbd, and (b) the fact that `nuxel-cpbootd`
is a **dry-run coordinator**, not yet a complete physical loader.

## 1. Stock cbd vs glibc — still INFEASIBLE (unchanged, correct)

`vendor/bin/cbd` (sha256 `c3e869fa…`) is ELF64 AArch64, interpreter
`/system/bin/linker64`, NEEDED `liblog/libcutils/libc++/libc/libm/libdl` (Bionic). Nuxel
is glibc/systemd; porting the entire Bionic surface + Android property server +
`radio_device` SELinux is precisely the Android-framework dependency the mission
forbids. **Verdict unchanged: stock cbd not runnable natively.**

## 2. Kernel ABI — VERIFIED (Gate B)

The ioctl set and struct layout are pinned and re-verified this round:

- `struct modem_firmware` is **28 bytes** (`__packed` verified in kernel
  `modem_prj.h:180-187`; `_Static_assert(sizeof==28)` in `nuxel-cpbootd.c`).
  *Correction note:* round-02's `identity-receipt.json` recorded "sizeof 32" — that was
  an unpadded-layout error; the kernel header is `__packed` = 28 B, and round-03+ is
  correct. No action required beyond this note.
- ioctls `_IO('o',N)`: ON=0x6F19, BOOT_ON=0x6F22, BOOT_OFF=0x6F23, BOOT_DONE=0x6F24,
  STATUS=0x6F27, DL_START=0x6F28, XMIT_BOOT=0x6F40, SECURITY_REQ=0x6F53.
- `CONFIG_LINK_DEVICE_PCIE` not set → PCIe-only ioctls correctly absent.
- Offline tests re-run green (22 + 21 + flash-preflight).

**Gate B = PASS.**

## 3. Bootstrap executable path (Gate C2)

| Candidate | Verdict |
|---|---|
| A: stock Bionic cbd | INFEASIBLE (Bionic deps) |
| B: cpboot_v3 glibc rebuild | INFEASIBLE (Android.bp links Bionic liblog/cutils/libc/selinux; property server) |
| C: minimal native Linux bootstrap (`nuxel-cpbootd`) | **SELECTED** — glibc-only, but current artifact is **dry-run only** |

`nuxel-cpbootd.c` (host+aarch64 builds) enforces:
- excl. ownership `flock(LOCK_EX|LOCK_NB)` over `/dev/umts_boot0`;
- dry-run default opens `O_RDONLY`, issues ONLY `IOCTL_MODEM_STATUS`;
- HW path compiled out unless `-DNUXEL_CPBOOTD_ENABLE_HW=1` **and** `--really-boot`;
- bounded 30 s/stage deadline, abort on `rc<0`/deadline, no auto-retry/loop;
- `_Static_assert` on every ioctl/struct.

**Incomplete (honest):** the two hardware-mutating stages that actually stream the
firmware are stubbed:
- `IOCTL_MODEM_XMIT_BOOT` (0x6F40) — "requires `struct modem_firmware`; NOT auto-built";
- `IOCTL_SECURITY_REQ` (0x6F53) — "requires `modem_sec_req` + smc params; NOT auto-built".

So `nuxel-cpbootd` correctly coordinates a dry-run but does **not** yet contain a
complete, source-backed physical transaction for those two stages. This is the
remaining concrete implementation work — it is purely offline/host work and does NOT
require owner input or device access to complete.

## 4. Firmware source contract (Gate C3)

Now fully established (see INSTALLED-RADIO and CBD-TYPE-STRING reports):

- Stock cbd reads the **installed radio partition** (`-P .../by-name/radio`) → `/dev/
  sda16`, opened read-only. The firmware is streamed to the kernel (which does
  `copy_from_user` per XMIT_BOOT), never a file the kernel opens itself.
- **Installed RADIO = EFUJ2** (`G975FXXSEFUJ2_CL2054966_QB20745891`), model-matched,
  valid ITOC. This is the correct least-invasive boot source.
- The kernel+`shmem_security_request`→`exynos_smc` performs secure verify (TEE), NOT
  the userspace loader.

**Gate C3 = PASS** (the source contract is now unambiguous: installed radio partition,
read-only, kernel-side secure boot).

## 5. What remains to close C2 fully (offline, agent-doable)

Implement the two stubbed stages in `nuxel-cpbootd.c` against the already-pinned ABI:
- XMIT_BOOT: build `struct modem_firmware{binary,size,m_offset,b_offset,mode,len}`
  from the ITOC BOOT/MAIN/VSS/NV entries (§ parse already exists in round-02 analyzer),
  bounds-checked against the firmware window.
- SECURITY_REQ: `struct modem_sec_req{mode,param2,param3,param4}` with the
  source-verified mode sequence (`CP_BOOT_RE_INIT` → `CP_BOOT_MODE_MANUAL` for TOC/VSS
  → `CP_BOOT_MODE_NORMAL` for BOOT/MAIN), plus the SIPC UDL handshake
  (`std_boot_finish_handshake`, channels 215–224).
- Add SIPC5 framing (`sipc5_link_header` = 6 B, already in `s5000ap_uapi.h`) for the
  MAIN download.

This is a bounded offline implementation task; it does not authorize any run, and the
completed loader remains behind the same compile+`--really-boot` fences.

## 6. Verdict

**Gate B = PASS; Gate C2 = PARTIAL (dry-run complete, 2 stages stubbed); Gate C3 = PASS.**
The bootstrap runtime is **not yet a drop-in physical loader**, and is **not claimed**
as ready. No hardware-changing operation is authorized or attempted.
