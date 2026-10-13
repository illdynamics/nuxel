# Nuxel Mainline Kernel Engagement Strategy — Google Pixel 10 Pro XL (mustang)

> **Status:** Planning / Engineering
> **Owner:** Nuxel Kernel & Driver Team
> **Last updated:** 2026-08-11
> **Target:** Push the Samsung Tensor G5 (gs501) bring-up drivers upstream to Linux mainline where feasible.

---

## 1. Purpose & Guiding Principles

The goal of Nuxel's kernel engineering effort is a **mainline-first** approach:
wherever possible we use the stock `linux` tree (6.12 LTS) with well-formed
upstream patches, rather than carrying a permanent, unmaintainable out-of-tree
vendor fork. Google already maintains an `android-gs-*` kernel line; Nuxel's
Phase-0 bring-up uses the **`android-gs-mustang-6.12`** vendor tree as the
springboard, with a **documented migration plan to mainline 6.12 LTS**.

This document defines:
- which drivers/subsystems need upstream work,
- which mailing lists and workflows to use,
- the patch review process Nuxel will follow, and
- ABI-stability considerations that gate what can be merged when.

**Guiding principles**
1. **Depend on the real `linux` 6.12 LTS where reviewable**; treat the vendor
   `android-gs` tree as a staging area.
2. **Prefer upstream-merge-ready contributions** over private forks.
3. **Accept binary firmware blobs** (Exynos 5500 modem, BCM4390, PowerVR, DSP)
   but make all kernel drivers above the firmware interface open source.
4. **Coordinate with existing communities** — postmarketOS, mainline-GS,
   ModemManager, PipeWire, Mesa PowerVR, Android-on-Generic — to share the
   maintenance burden and to learn from their patch sets.

---

## 2. Missing Driver / Subsystem Map

### 2.1 Comprehensive driver table

> **Legend — Status:**
> - **Not-in-tree** — driver does not exist anywhere in mainline; requires new code.
> - **Candidate** — driver exists in mainline for a related/similar part; mustang-specific support not yet merged.
> - **Halium-Only** — support currently only exists in Android Halium/LOS vendor trees (not mainline).

| Driver / Subsystem | Target upstream subsystem | Current status | CONFIG in kernel/defconfig (Phase 0) | Notes / owner |
|---|---|---|---|---|
| **PowerVR GPU** (Imagination DXT-72-2304) | `drivers/gpu/drm/imagination` (PowerVR DRM) | In-tree (base) / mustang-specific DXT variant **Not-in-tree** | `CONFIG_DRM_POWERVR=y` (upstream base); `CONFIG_DRM_POWERVR_DXT` absent (vendor/Not-in-tree) | Base PowerVR DRM + Rogue landed in mainline (6.5+, `CONFIG_DRM_POWERVR`). The **DXT core + firmware needs validation** because mainline only carries the base/ROGUE variant — `CONFIG_DRM_POWERVR_DXT` is not a real upstream 6.12 symbol and is commented out as ASPIRATIONAL in `kernel/defconfig`. Huge userspace effort via **Mesa powervr** (`mesa-powervr` gallium + `vulkan-powervr`). |
| **Samsung AMB655X LTPO panel** | `drivers/gpu/drm/panel` (`CONFIG_DRM_PANEL_SAMSUNG_AMB655X`) | **Not-in-tree** | `CONFIG_DRM_PANEL_SAMSUNG_AMB655X` absent (vendor/Not-in-tree) | New panel; not a real upstream 6.12 symbol (`CONFIG_DRM_PANEL_SAMSUNG_AMB655X is not set` — ASPIRATIONAL in `kernel/defconfig`). Needs DT + panel init seq + LTPO/backlight timings from vendor. |
| **Samsung S6SY791 touchscreen** | `drivers/input/touchscreen/` (`CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791`) | **Not-in-tree** | `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791` absent (vendor/Not-in-tree) | Vendor driver; not a real upstream 6.12 symbol (`CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791 is not set` — ASPIRATIONAL in `kernel/defconfig`). Needs I2C + compatible string; multi-touch 10pt; firmware update path. |
| **Exynos 5500 modem** (Samsung; PCIe/MHI v2) | `drivers/net/mhi` + `drivers/bus/mhi` (+ `net/qrtr`/`net/ipa`) | Core MHI **In-tree**; vendor plugin **Not-in-tree** / Halium-Only | `CONFIG_MHI_BUS_PCI_GENERIC=y` (upstream); `CONFIG_MHI_SAMSUNG_EXYNOS5500` absent (vendor/Halium-only) | Mainline has `CONFIG_MHI_BUS_PCI_GENERIC` (`=y` in `kernel/defconfig`) + QRTR + IPA net. The Samsung `CONFIG_MHI_SAMSUNG_EXYNOS5500` glue is **not a real upstream 6.12 symbol** and is commented out as ASPIRATIONAL in `kernel/defconfig`; upstreaming is a multi-cycle effort. |
| **CS35L45 speaker amp** (Cirrus Logic) | `sound/soc/codecs` (`CONFIG_SND_SOC_CS35L45`) | **Candidate** (vendor-only in Phase-0 defconfig; upstreaming pending) | `CONFIG_SND_SOC_CS35L45 is not set` (ASPIRATIONAL, vendor-only in mustang) | NOT active in `kernel/defconfig`: `# CONFIG_SND_SOC_CS35L45 is not set` marked ASPIRATIONAL (vendor-only in `kernel/defconfig`). Upstream symbol is vendor/Halium-only in Phase 0; upstreaming pending. CS35L41 is mainline; CS35L45 is not yet enabled. Validate mustang smart-amp tuning + DAPM routing when upstreamed. |
| **CS42L43 audio codec** (Cirrus Logic) | `sound/soc/codecs` (`CONFIG_SND_SOC_CS42L43`) | **Candidate** (vendor-only in Phase-0 defconfig; upstreaming pending) | `CONFIG_SND_SOC_CS42L43 is not set` (ASPIRATIONAL, vendor-only in mustang) | NOT active in `kernel/defconfig`: `# CONFIG_SND_SOC_CS42L43 is not set` marked ASPIRATIONAL (vendor-only in `kernel/defconfig`). Upstream symbol is vendor/Halium-only in Phase 0; upstreaming pending. Mustang wiring + UCM profiles needed (ALSA UCM2, PipeWire/WirePlumber profiles are in Nuxel configs). |
| **brcmfmac BCM4390 WiFi** (Broadcom, WiFi 7) | `drivers/net/wireless/broadcom/brcm80211` (`CONFIG_BRCMFMAC`) | **Candidate** — BCM4390 support not yet mainlined | `CONFIG_BRCMFMAC=y` (upstream core enabled); BCM4390-specific support absent | PCIe device ID `0x4490`, vendor `0x14e4`; upstream core `CONFIG_BRCMFMAC=y` in `kernel/defconfig`. BCM4390-specific device/FW surface is not yet mainlined. Firmware `brcmfmac4390.bin` from vendor. Need DT + `brcmfmac` new-device addition + FW API surface (MLO / 6GHz / VLP for regional compliance). |
| **BT BCM4390** (BT 5.4) | `net/bluetooth` + `drivers/bluetooth` (HCI UART) | **Candidate** | (generic) `CONFIG_BT_HCIUART_BCM` exists upstream; no mustang-specific entry | `CONFIG_BT_HCIUART_BCM` exists; mustang variant/power sequencing needed. |
| **NXP SN220 NFC** | `drivers/nfc/nxp` (`CONFIG_NFC_NXP_SN220`) | **Not-in-tree** | `CONFIG_NFC_NXP_SN220` absent (vendor/Not-in-tree) | New NCI controller; needs driver + I2C + NCI config. |
| **Sensors (BMI270, LSM6DSV, TCS3710)** | `drivers/iio/imu`, `drivers/iio/light` (`CONFIG_IIO_*`) | **Candidate** | (generic) upstream `CONFIG_IIO_*` for BMI270/LSM6DSV; TCS3710 absent | BMI270 (bosch) + LSM6DSV (ST) have mainline st/imu support — validate compatible; TCS3710 ALS is new. |
| **Goodix GF3636 fingerprint** | `drivers/input` / cryptom (fprintd userspace) | **Not-in-tree** / Halium-Only | no Nuxel `kernel/defconfig` entry (vendor userspace) | Sensor needs vendor init + libfprint/userspace; fingerprint drivers are typically hard to upstream. |
| **Maxim PMIC / charger / fuel gauge** | `drivers/mfd`, `drivers/power/supply` | **Candidate** | (generic) upstream `CONFIG_MFD_*` / power-supply core exists; mustang mapping needed | MAX77729/MAX77826 PMIC, BQ2597x charger, MAX1720x fuel gauge — mainline-core exists for many, mustang mapping needed. |
| **Samsung AMB655X display / DSC** (handled in panel) | `drivers/gpu/drm/display` (DSC), panel | **Candidate** | up to `CONFIG_DRM_PANEL_SAMSUNG_AMB655X` (absent — see panel row) | DSC support in drm core; integrate with panel + command mode. |
| **IPA / QRTR modem data plane** | `net/qrtr`, `drivers/net/ipa` | **In-tree** (core) | `CONFIG_QRTR`/`CONFIG_IPA` absent (no upstream enablement in `kernel/defconfig` yet) | QRTR/IPA are upstream mainline subsystems, but no `CONFIG_QRTR`/`CONFIG_IPA` entry exists in `kernel/defconfig` (Phase 0 has them not enabled). Exynos 5500-specific config absent; Nuxel data-path goal — vendor Exynos 5500 QRTR service + IPA config may need vendor patches before mainlinable. |

> **Reading the CONFIG column:** `CONFIG_*=y` / `CONFIG_*=n` mirror the
> Phase-0 `kernel/defconfig` state. Symbols marked *absent* (or commented out as
> **ASPIRATIONAL**) are **not** real upstream 6.12 Kconfig options and exist only
> in the vendor/Halium tree — their driver row status reflects that accordingly.

### 2.2 Priority ordering (engineering effort vs. dependency)

| Priority | Workstream | Why |
|---|---|---|
| P0 | Display + touch (AMB655X + S6SY791) | Phosh cannot boot without them. |
| P0 | PowerVR DRM + Mesa gallium/Vulkan | Required for a usable GPU-accelerated UI and to avoid software-rendering pain on Phosh. |
| P1 | brcmfmac BCM4390 (WiFi) | Connectivity is the primary Nuxel data path on mustang. |
| P1 | CS35L45 + CS42L43 audio | Calls + sound depend on the codecs (already scaffolded UCM/PipeWire). |
| P1 | MHI / Exynos 5500 modem data plane | LTE data + ModemManager; VoLTE depends on it (see `volte-carrier-strategy.md`). |
| P2 | NFC, BT profiles, fingerprint, sensors, PMIC/charging | Feature completeness; batchable after P0/P1 boot is stable. |

---

## 3. Mailing Lists & Where to Send Patches

| Target | Mailing list / channel | Notes |
|---|---|---|
| ARM core + Exynos/GS SoC | **linux-arm-kernel** (`linux-arm-kernel@lists.infradead.org`) | Default list for ARM Device Tree, clock, pinctrl, SoC bring-up. Prefix: `[RFC PATCH]` for design review. |
| Storage / UFS / block | **linux-mtd** (`linux-mtd@lists.infradead.org`) for MTD; **linux-scsi** for UFS | UFS bring-up and any flash/partition work. |
| Network drivers | **netdev** (`netdev@vger.kernel.org`) | brcmfmac (Wireless via `linux-wireless@vger.kernel.org`), MHI/QRTR/IPA data plane. |
| Device Tree / bindings | **devicetree-spec** + `devicetree@vger.kernel.org` | Every new node needs a YAML binding + review here. |
| Sound/ASoC | **alsa-devel** (`alsa-devel@alsa-project.org`) | CS35L45/CS42L43 codec + machine-driver changes. |
| Display/DRM | **dri-devel** (`dri-devel@lists.freedesktop.org`) | Panel, DSI/DP, DSC, PowerVR DRM. |
| Input subsystem | **linux-input** (`linux-input@vger.kernel.org`) | Touchscreen + fingerprint. |
| IIO (sensors) | **linux-iio** (`linux-iio@vger.kernel.org`) | IMU/ALS drivers. |
| Wireless/bluetooth | **linux-wireless** + **linux-bluetooth** | BCM4390 FW enablement + profiles. |
| Telephony userspace (not kernel, but coordinating) | **ModemManager-devel**, **oFono-devel**, **postmarketOS** IRC/Matrix | Userspace that depends on MHI/QRTR/IPA. |
| BSP staging | **postmarketOS mainline-gs**, **linux-pixel-phone / Gentoo Pixel** group | Pre-existing GS mainlining efforts to reuse. |

**Process notes**
- Always generate patches against a recent `linux` master, keep the commit
  series small and bisectable, and use `./scripts/checkpatch.pl`.
- Add `include/dt-bindings` YAML bindings with `robots`-verified examples and
  include them in the first commits of any DT series.
- Tag `devicetree@vger.kernel.org` on every DT patch; a binding maintainer must
  Ack it before the driver can be merged.

---

## 4. Patch Review Process (Nuxel workflow)

1. **Downstream staging:** Develop against the `android-gs-mustang-6.12` vendor
   tree to reach a booting milestone quickly (Phase 0).
2. **Split and refine:** Extract the Nuxel-specific changes into logical series:
   bindings first, DT, then drivers. Remove any vendor-black-box or
   license-problematic code before any upstream submission.
3. **Internal review:** CI (`ci/`) runs `checkpatch`, compile-test for
   `ARCH=arm64`, and build-boot sanity checks for every patch. Have at least
   one external Maintainer-mentor review before sending.
4. **Upstream RFC:** Post the series to the relevant list with
   `[RFC PATCH n/m]` and a cover letter; incorporate feedback.
5. **Revert / resend until clean:** Iterate the `PATCH` revision until Acked;
   track revision history in a `patches/` manifest.
6. **Local backport:** Maintain a curated `kernel/patches/` set for the mustang
   production tree (autogen/manifest-tracked) so the shipped kernel is a merge
   of upstream-merged patches + the few still-out-of-tree pieces.
7. **Long-term:** As pieces land upstream, drop them from the local patch
   set, shrinking Nuxel's out-of-tree delta each LTS.

**License / provenance gate:** before any submission, verify every file's source
is GPL-2.0-compatible and has a clean provenance (no re-export of
closed-source vendor code). The `LICENSE` (Apache-2.0) project license applies
to Nuxel userspace; kernel patches must be GPL-2.0.

---

## 5. ABI-Stability Concerns

| Concern | Detail | Mitigation |
|---|---|---|
| **PSTO / stable-ABI** | Kernel internal ABIs (module params, `struct` layouts) are not frozen; some downstream userspace depends on them. | Keep Nuxel kernel modules paired tightly with the built tree; do not promise stable module ABIs across the vendor/mainline split. |
| **MHI / QRTR ABI** | ModemManager and vendor userspace may expect the QRTR/`qrtr-ns` + probe service names/ABIs. | Track QRTR/`qrtr` namespaces; adapt ModemManager Samsung plugin to the mainlined ABI. |
| **brcmfmac firmware ABI** | FW interface (firmware to driver protocol) is not wholly stable in upstream brcmfmac. | Pair the driver commit with the `brcmfmac4390.bin` FW build; document the compatibility matrix in `firmware/`. |
| **uAPI for DRM (PowerVR)** | The PowerVR DRM uAPI may differ from vendor expectations; userspace (Mesa powervr) must match kernel uAPI revision exactly. | Build both kernel + Mesa `mesa-powervr` from the same tagged source in `images/`; lock the uAPI ABI in the release manifest. |
| **Userspace out-of-tree** | Out-of-tree modules (vendor GPU/ISP) can break across kernel bumps. | Goal: no out-of-tree modules on production mustang; everything lands in `linux` tree or a clearly-scoped Nuxel DTO. |

---

## 6. Migration Plan (Vendor `android-gs` → Mainline 6.12 LTS)

### Phase 0 (current, Phase 0 of overall roadmap)
Use **`android-gs-mustang-6.12`** as bring-up kernel. Build with
`gs501_defconfig`, a real initramfs and real boot.img + dtbo.img (replacing
zero-filled stubs). Do **not** block on mainlining yet.

### Phase 1 (immediately after boot.exe works)
- Port the minimal mustang DT + drivers as a **local patch series** on top of
  mainline 6.12 LTS.
- Bring up display + touch + basic audio + WiFi on the **mainline** tree in
  parallel with the vendor tree.
- Begin RFC submission of bindings + the easiest drivers (input/panel, codec).

### Phase 2
- Target full mainline boot on mustang with parity to the vendor-tree milestone.
- Move modem data plane (MHI + QRTR + Exynos 5500 plugin) and PowerVR DRM +
  Mesa powervr onto mainline.

### Phase 3 (lifetime)
- Switch Nuxel's shipped kernel fully to the mainline 6.12 LTS (and then the
  next LTS — GPL-2.0 `linux` maintained by LTS + distro backports).
- Vendor `android-gs` tree retired except as a firmware/reference source for
  opaque registers and 0-day bring-up.
- Track the shrinking `<nuxel patches !== upstream-merged>` set in
  `kernel/patches/`.

---

## 7. Community Coordination

- **Mainline-GS / postmarketOS / Gentoo-Pixel:** already drive Samsung GS
  towards mainline; share DTs, QRC bits, firmware extraction tooling.
- **ModemManager / oFono:** the telephony userspace depends on the MHI/QRTR
  data plane; coordinate the Exynos 5500 plugin with fdo and the Samsung plugin
  maintainer.
- **Mesa (powervr):** the Imagination powervr gallium + Vulkan live in Mesa;
  coordinate GPU uAPI with the Mesa team so the kernel + userspace land together.
- **Phosh / d-bus pipe:** Nuxel's PWA↔HTTP↔bridge↔portal↔PhoshAgent chain rides
  on Freedesktop D-Bus + session services already maintained upstream.

---

## 8. References

- Linux 6.12 LTS; `android-gs-mustang-6.12` vendor tree (google code review
  `android.googlesource.com/kernel/gs`).
- Documentation/rust/kconfig etc. None required; see `kernel/README-toolchain.md`,
  `kernel/build-kernel.sh`, `kernel/defconfig`.
- Imagination `mesa-powervr` + `linux` PowerVR DRM (`drivers/gpu/drm/imagination`).
- Nuxel driver tracking: `docs/driver-status.md`.
- Nuxel device bring-up: `docs/hardware-bringup-prep.md` (bg-07), `docs/wifi-bcm4390-status.md`.
- VoLTE dependency: `docs/volte-carrier-strategy.md`.
