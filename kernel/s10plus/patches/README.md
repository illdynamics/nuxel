# Nuxel S10+ Kernel Patches (Exynos 9820)

This directory holds Nuxel patches for the `linux-postmarketos-exynos9820`
kernel tree (branch `exynos9820` of `postmarketOS/linux-postmarketos`).

`kernel/s10plus/build-kernel.sh` applies every `*.patch` in this directory
**non-fatally**: if a patch fails to apply, the build continues and prints a
WARN pointing at the matching `NNNN-name.README` hint (see
`patches/0001-nuxel-phone-features.README`). A patch that does not apply is
treated as "not yet ported", never as a build failure.

## Port analysis of the mustang Nuxel patch

Reference tree (DOC-ONLY cross-reference — the S10+ kernel is a different
tree and no mustang patch is copied here): `kernel/google-pixel-10-pro-xl/patches/`.

| mustang patch | Ports cleanly to exynos9820? | Reason (analysis of the actual patch body) |
|---|---|---|
| `0001-nuxel-phone-features.patch` (drivers/nuxel: `NUXEL` / `NUXEL_PHONE` / `NUXEL_BOOT_PARAM`) | NOT VERIFIED — stub provided until `git apply --check` passes against the cloned tree | See the per-hunk analysis below. The C code is NOT 6.12-only, but the wiring hunks are context-dependent and the patch hardcodes the mustang device. |

Per-hunk analysis of `0001-nuxel-phone-features.patch` (mustang / Tensor G5,
6.12 GKI tree):

1. `drivers/Kconfig` hunk — inserts `source "drivers/nuxel/Kconfig"` between
   `source "drivers/opp/Kconfig"` and `source "drivers/siox/Kconfig"`.
   - The `opp`/`siox` context lines are long-standing in mainline, so this
     hunk *may* apply to the exynos9820 tree as-is, but the exynos9820 branch
     has its own `drivers/Kconfig` history — **verify with `git apply --check`
     after cloning**; if it fuzzes, re-base by hand (the change itself is
     trivial).
2. `drivers/Makefile` hunk — inserts `obj-$(CONFIG_NUXEL) += nuxel/` after
   `obj-$(CONFIG_DPLL) += dpll/`. Same context-dependent caveat.
3. `drivers/nuxel/Kconfig`, `drivers/nuxel/Makefile`,
   `drivers/nuxel/nuxel-core.c` — new files. The C file uses:
   - `struct proc_ops` — mainline since v5.6 (not 6.12-specific);
   - `saved_command_line` — exported by `init/do_mounts.c` in every mainline
     kernel of the last decade (not 6.12-specific);
   - plain `module_init` / `proc_mkdir` / `proc_create` — ancient, stable API.
   So the driver itself is expected to compile on the exynos9820 tree once the
   two wiring hunks apply.
4. Mustang coupling inside the patch that must be generalized on port:
   - Kconfig help text of `NUXEL_BOOT_PARAM` says it parses
     `nuxel.device=mustang`;
   - `nuxel-core.c` header comment and `MODULE_DESCRIPTION` say "for mustang".
   The port must make `nuxel.device=` accept `s10plus` in addition to
   `mustang`, and keep the module device-agnostic.

**Verdict:** the patch is *probably* portable with small context fixes (it
does not use GKI-only or 6.12-only APIs), but this cannot be claimed as fact
until it is checked against the real exynos9820 tree. Until then the stub in
this directory stands. If the wiring hunks do NOT apply, treat the patch as
6.12-only and keep the stub with the TODO below.

## Stub patch — 0001-nuxel-phone-features.patch

`patches/0001-nuxel-phone-features.patch` is a STUB: it contains only a
documentation header and deliberately no diff hunks, so `git apply` reports
"No valid patches" instead of a false success. The build wrapper's WARN path
points to `patches/0001-nuxel-phone-features.README`.

### How the operator verifies the port (after `--clone`)

```sh
# From the repo root, against the cloned exynos9820 tree:
git -C kernel/s10plus/.build/src apply --check \
    kernel/s10plus/patches/0001-nuxel-phone-features.patch

# Equivalent when already inside the kernel source tree:
git apply --check kernel/s10plus/patches/0001*.patch
```

Exit code 0 means the patch applies cleanly. Any output means context
mismatch — re-base the two wiring hunks by hand, generalize the mustang
references to `s10plus`, then re-check.

### Port checklist (tracked in the stub file too)

- [ ] `drivers/nuxel/Kconfig` — keep `NUXEL`, `NUXEL_PHONE`, `NUXEL_BOOT_PARAM`;
      update help text: `nuxel.device=` accepts `s10plus` (and `mustang`).
- [ ] `drivers/nuxel/Makefile` — `obj-$(CONFIG_NUXEL) += nuxel-core.o`.
- [ ] `drivers/nuxel/nuxel-core.c` — generalize `nuxel.device=` parsing;
      keep it independent of any vendor-only driver.
- [ ] `drivers/Kconfig` — `source "drivers/nuxel/Kconfig"` (re-base hunk).
- [ ] `drivers/Makefile` — `obj-$(CONFIG_NUXEL) += nuxel/` (re-base hunk).
- [ ] `git apply --check` passes (command above).
- [ ] `kernel/s10plus/defconfig`: uncomment `CONFIG_NUXEL=y` /
      `CONFIG_NUXEL_PHONE=y` / `CONFIG_NUXEL_BOOT_PARAM=y` once the port
      compiles; keep them commented with TODO until then.

## How to add a patch here

1. Drop `NNNN-description.patch` into this directory.
2. Add a `NNNN-description.README` next to it with the rationale and the
   `git apply --check` command (the build wrapper's WARN path references it).
3. The build wrapper applies all `*.patch` files non-fatally; a patch that
   fails to apply never aborts the build.
