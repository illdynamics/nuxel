# S5000AP — Prompt 03.6: CBD Type-String Verification (Gate C1)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged)
**No handset-changing action. Source-only + binary-metadata evidence.**

---

## 0. Headline — PRIOR ROUND-03.5 CONCLUSION WAS WRONG

Round 03.5 (§5 of FIRMWARE-PROVENANCE, §3 of CBD-RUNTIME-DECISION) concluded that
`-t ss310` "names the wrong modem generation" and maps to "Shannon 310 (ModAP/SIT),
NOT the S5000AP." **This is incorrect.** The correct conclusion, established here from
the pinned cpboot_v3 source, is:

> **`-t ss310` is the correct type string for the S5000AP when cbd is built with
> `protocol=sipc` + `use_legacy_sipc_ioctl=true` — exactly the configuration the
> exynos9820-common device tree sets.**

## 1. Source evidence (pinned, re-verified this round)

- cpboot_v3 repo: `android_hardware_samsung_slsi-linaro_exynos` @
  `234b138716426c36ed801a71052bc144f7d8d806` (lineage-22.1).
- Device config: `android_device_samsung_exynos9820-common` @ `38af956a…`
  (lineage-23.2) `BoardConfigCommon.mk:154-155`:
  ```
  $(call soong_config_set,cbd,protocol,sipc)
  $(call soong_config_set_bool,cbd,use_legacy_sipc_ioctl,true)
  ```

## 2. What `-t` actually selects

`Container.cpp:100-125`:
```cpp
case 't':
    cmd = optarg;
#ifdef CONFIG_TYPE_MODAP
    if (!strncmp(cmd, "modap_sit", 9) || !strncmp(cmd, "ss310", 5))
        bootdump = new BootDumpModap();
#endif
#ifdef CONFIG_TYPE_EXT
    if (!strncmp(cmd, "s5100sit", 8) || !strncmp(cmd, "s5100", 5))
        bootdump = new BootDumpExt();
#endif
    if (!bootdump) { cbd_info("Unknown modem"); return ERROR; }
```

So `-t` selects the **BootDump concrete class** (`BootDumpModap` vs `BootDumpExt`),
NOT the wire protocol. The protocol (SIPC vs SIT) is a **compile-time** flag
(`protocol=sipc`), independent of `-t`.

## 3. The key correction: SIT vs SIPC is compile-time, not `-t`-time

`BootDumpModap::setCbdArgs()`:
```cpp
#ifdef CONFIG_PROTOCOL_SIT
    cbd_args->type = SEC_MODAP_SIT;      // only when -DCONFIG_PROTOCOL_SIT
    ...
#else
    cbd_info("SS310 modem\n");
    cbd_args->type = SEC_SS310;          // SIPC build takes THIS branch
    cbd_args->cpn.num_stages = 5;        // toc, boot, main, vss, nv
#endif
```

With `protocol=sipc` (the exynos9820 setting), `CONFIG_PROTOCOL_SIT` is **NOT** defined,
so `-t ss310` → **`SEC_SS310` with SIPC framing** (5 stages). This is the exact S5000AP
path. The `modap_sit`/`SEC_MODAP_SIT` branch (which round-03.5 wrongly cited) only
activates for a `protocol=sit` build.

## 4. Is there a separate "s5000ap" type string? No.

`grep -rni 's5000' cpboot_v3/` → **zero matches.** The cbd modem-type enum is only
`SEC_SS310 / SEC_S5100 / SEC_MODAP_SIT / SEC_S5100_SIT`. The string `s5000ap` exists
only in the **kernel** (`modem_variation` → `modem_ctrl_s5000ap.c`), not in userspace
cbd. In Samsung's naming, **`SS310` is the userspace name of the S5000AP/Shannon 310
modem.**

## 5. Answers to the 5 sub-questions

1. **What `-t` selects:** the BootDump class (`BootDumpModap` for `ss310`). Protocol is
   compile-time, not `-t`.
2. **Correct type for SM-G975F/S5000AP:** **`ss310`** (with `protocol=sipc` +
   `legacy_sipc_ioctl=true`).
3. **Is `ss310` correct?** **YES** — proven above (§2–4).
4. **Does type affect memory map/boot/firmware/secure-verify?** The *type* fixes
   `node_boot=/dev/umts_boot0`, `lnk_boot/lnk_main=SHMEM`, `num_stages=5`,
   `path_bin=/dev/block/by-name/modem…` (or the `-P` override → radio). The *protocol*
   (SIPC-vs-SIT) controls framing/secure-verify (`-DCONFIG_SEC_CP_VERIFYING_ALL`). For
   S5000AP: SIPC + SHMEM, 5 stages, secure verify via kernel/`exynos_smc` TEE.
5. **Is the executable compatible with the historical kernel ABI?** The stock
   `vendor/bin/cbd` is Bionic-linked (NOT runnable on Nuxel glibc — see BOOTSTRAP
   report). The **ioctl ABI** it uses is the `_IO('o',N)` legacy form
   (`LEGACY_SIPC_IOCTL`), which **matches** the pinned `s5000ap_uapi.h` exactly
   (verified round 03: `0x6F19/0x6F22/0x6F24/0x6F27/0x6F28/0x6F40/0x6F53`).

## 6. Boot sequence (source-verified, `LEGACY_SIPC_IOCTL` + SIPC)

From `BootDumpModap.cpp::boot()` + `BootDump.cpp`, the `LEGACY_SIPC_IOCTL` path is:

1. open `/dev/umts_boot0` (O_RDWR) + open `radio` partition (O_RDONLY).
2. `std_boot_parse_toc_img` → read+validate TOC (BOOT/MAIN/VSS/NV/OFFSET entries).
3. `std_boot_power_on` → `IOCTL_MODEM_ON` (0x6F19).
4. `std_boot_start_cp_bootloader` → `IOCTL_MODEM_BOOT_ON` (0x6F22).
5. `IOCTL_MODEM_DL_START` (0x6F28).
6. SIPC UDL handshake (`std_boot_finish_handshake`, `ProtocolSipc` `0x9000/0xA000`
   frames, stage channels 215–224).
7. `std_boot_complete_normal_bootup` → `IOCTL_COMPLETE_NORMAL_BOOTUP` +
   `IOCTL_CLR_CP_BOOTLOG`.

(**Note:** this is the SIPC/legacy-ioctl sequence. Secure verify happens inside the
kernel/`shmem_security_request` → `exynos_smc` during the SIPC download handshake; the
userspace loader never computes the signature.)

## 7. Verdict

**`CBD_TYPE_STRING_VERIFIED`** — the correct S5000AP type string is **`ss310`**
(source-proven), and the prior "wrong modem generation" claim is **retracted** and
corrected.
