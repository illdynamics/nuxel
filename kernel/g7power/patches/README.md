# Nuxel G7 Power Kernel Patches (SDM632 / msm8953)

This directory holds Nuxel patches for the `linux-postmarketos-qcom-msm8953`
kernel tree (`master` branch of `msm8953-mainline/linux`).

`kernel/g7power/build-kernel.sh` applies every `*.patch` in this directory
**non-fatally**: if a patch fails to apply, the build continues and prints a
WARN pointing at the matching `NNNN-name.README` hint (see
`patches/0001-nuxel-phone-features.README`). A patch that does not apply is
treated as "not yet ported", never as a build failure.

## What msm8953-mainline already provides

The `msm8953-mainline` tree is a close-to-mainline Snapdragon 632 / msm8953
kernel and already carries mainline drivers for the G7 Power's core
peripherals, so most Nuxel driver work is *not* needed here:

- **Touch** — Ilitek ILI2117 hardware on the mainline `ili210x` driver
  (`CONFIG_TOUCHSCREEN_ILI210X`, i2c_3 @ 0x41, inverted-x). There is no
  `CONFIG_TOUCHSCREEN_ILI210X` symbol anywhere in the tree: `ili210x.c`
  matches `compatible = "ilitek,ili2117"` -> `ili211x_chip`.
- **GPU / display** — mainline freedreno `CONFIG_DRM_MSM` (Adreno 506) plus
  `CONFIG_DRM_PANEL_SIMPLE` and `CONFIG_BACKLIGHT_TI_LM3697`.
- **WiFi / BT** — mainline `wcn36xx` + `CONFIG_QCOM_WCNSS_PIL` for WCN3680B
  (not ath10k, not brcmfmac) and `hci_qca` for Bluetooth.
- **Sensors** — mainline `CONFIG_BMI160_I2C` (Bosch BMI160 accel+gyro).

Consequently the Nuxel patches here are primarily the **`drivers/nuxel/`
boot-param and phone-feature additions** (`CONFIG_NUXEL` /
`CONFIG_NUXEL_PHONE` / `CONFIG_NUXEL_BOOT_PARAM`), not driver backports.

## Port status of `0001-nuxel-phone-features.patch`

The original patch lives in `kernel/google-pixel-10-pro-xl/patches/` (Pixel
10 Pro XL, Tensor G5, 6.12 GKI tree) and is a DOC-ONLY cross-reference —
nothing from the Pixel tree is copied here. It adds `drivers/nuxel/` with the
three `CONFIG_NUXEL*` symbols and parses `nuxel.boot=1` / `nuxel.device=` on
the kernel command line.

Per-hunk analysis for the msm8953 tree:

1. `drivers/Kconfig` hunk — inserts `source "drivers/nuxel/Kconfig"` between
   the `opp`/`siox` context lines.
   - The `opp`/`siox` lines are long-standing in mainline, so this hunk *may*
     apply to the msm8953 tree as-is — but the msm8953 branch has its own
     `drivers/Kconfig` history and its Kconfig symbol set diverged from the
     6.12 GKI tree years ago. **Verify with `git apply --check` after
     `--clone`**; if it fuzzes, re-base by hand (the change itself is
     trivial).
2. `drivers/Makefile` hunk — inserts `obj-$(CONFIG_NUXEL) += nuxel/` after
   `obj-$(CONFIG_DPLL) += dpll/`. Same context-dependent caveat.
3. `drivers/nuxel/Kconfig`, `drivers/nuxel/Makefile`,
   `drivers/nuxel/nuxel-core.c` — new files. The C file uses:
   - `struct proc_ops` — mainline since v5.6 (the msm8953 tree is a 5.x-era
     close-to-mainline tree, so this is expected to be available);
   - `saved_command_line` — exported by `init/do_mounts.c` in every mainline
     kernel of the last decade;
   - plain `module_init` / `proc_mkdir` / `proc_create` — ancient, stable API.
   So the driver itself is expected to compile on the msm8953 tree once the
   two wiring hunks apply.
4. Mustang coupling inside the patch that must be generalized on port:
   - Kconfig help text of `NUXEL_BOOT_PARAM` says it parses
     `nuxel.device=mustang`;
   - `nuxel-core.c` header comment and `MODULE_DESCRIPTION` say "for mustang".
   The port must make `nuxel.device=` accept `g7power` in addition to
   `mustang`, and keep the module device-agnostic.

**Verdict:** the patch is *probably* portable with small context fixes (its C
code does not use GKI-only or 6.12-only APIs), but this cannot be claimed as
fact until it is checked against the real msm8953 tree. Until then the stub in
this directory stands.

### How the operator verifies the port (after `--clone`)

```sh
# From the repo root, against the cloned msm8953 tree:
git -C kernel/g7power/.build/src apply --check \
    kernel/g7power/patches/0001-nuxel-phone-features.patch

# Equivalent when already inside the kernel source tree:
git apply --check kernel/g7power/patches/0001*.patch
```

Exit code 0 means the patch applies cleanly. Any output means context
mismatch — re-base the two wiring hunks by hand, generalize the `mustang`
references to `g7power`, then re-check.

## Stub patch — `0001-nuxel-phone-features.patch`

`patches/0001-nuxel-phone-features.patch` is a STUB: it contains only a
documentation header and deliberately no diff hunks, so `git apply` reports
"No valid patches" instead of a false success. The build wrapper's WARN path
points to `patches/0001-nuxel-phone-features.README`.

## If a hunk fails — `0001-nuxel-phone-features.patch.TODO`

`patches/0001-nuxel-phone-features.patch.TODO` holds the unported sections
with a comment explaining the missing upstream symbol/context: the msm8953
tree has no `drivers/nuxel/` directory and no `CONFIG_NUXEL` /
`CONFIG_NUXEL_PHONE` / `CONFIG_NUXEL_BOOT_PARAM` Kconfig symbols, and the
wiring-hunk context lines are not guaranteed to match the 6.12 tree. Once the
port is done, delete the `.TODO` file, replace the stub `.patch` with the real
patch, and uncomment the Nuxel symbols in `kernel/g7power/defconfig`.

## Port checklist (tracked in the stub file too)

- [ ] `drivers/nuxel/Kconfig` — keep `NUXEL`, `NUXEL_PHONE`, `NUXEL_BOOT_PARAM`;
      update help text: `nuxel.device=` accepts `g7power` (and `mustang`).
- [ ] `drivers/nuxel/Makefile` — `obj-$(CONFIG_NUXEL) += nuxel-core.o`.
- [ ] `drivers/nuxel/nuxel-core.c` — generalize `nuxel.device=` parsing;
      keep it independent of any vendor-only driver.
- [ ] `drivers/Kconfig` — `source "drivers/nuxel/Kconfig"` (re-base hunk).
- [ ] `drivers/Makefile` — `obj-$(CONFIG_NUXEL) += nuxel/` (re-base hunk).
- [ ] `git apply --check` passes (command above).
- [ ] `kernel/g7power/defconfig`: uncomment `CONFIG_NUXEL=y` /
      `CONFIG_NUXEL_PHONE=y` / `CONFIG_NUXEL_BOOT_PARAM=y` once the port
      compiles; keep them commented with TODO until then.

## How to add a patch here

1. Drop `NNNN-description.patch` into this directory.
2. Add a `NNNN-description.README` next to it with the rationale and the
   `git apply --check` command (the build wrapper's WARN path references it).
3. The build wrapper applies all `*.patch` files non-fatally; a patch that
   fails to apply never aborts the build.
