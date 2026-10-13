# Nuxel VoLTE Carrier Strategy for Google Pixel 10 Pro XL (mustang)

> **Status:** Planning / Research
> **Owner:** Nuxel Telephony & Carrier Integration
> **Last updated:** 2026-08-11
> **Target device:** Google Pixel 10 Pro XL (mustang), Samsung Exynos 5500 modem, Linux 6.12 LTS mainline bring-up

---

## 1. Executive Summary

VoLTE (Voice over LTE) — also written as ViLTE in its video variant — is a
prerequisite for any modern phone to place and receive high-quality
carrier-grade voice calls on LTE networks. Voice on most European and US
mobile networks has migrated (or is actively migrating) to IMS/VoLTE, and the
legacy CS (circuit-switched) fallback that POST/4G-capable devices once relied
on is being decommissioned by carriers (Vodafone UK, T-Mobile US 3G shutdown,
etc.).

Nuxel's VoLTE target is the Samsung **Exynos 5500** modem connected over
PCIe Gen3 using **MHI v2** (PCIe vendor ID `0x144d`, device ID `0xa800`). The
high-level software path is:

```
Exynos 5500 (MHI v2)  →  Kernel (MHI / IPA-QRTR data plane)
  →  ModemManager (or oFono) telephony daemon
  →  ModemManager Voice API (call.voice + call object)
  →  oFono / IMS stack for SIP/RTP IMS registration
  →  Carrier IMS APN (e.g. vzwims / ims) with carrier IMS config
  →  Carrier network acceptance (provisioning, handset approval)
```

**Key finding: VoLTE is not a kernel-driver problem, it is a user-space IMS
stack + carrier-approval problem.** Mainline Linux today does not ship a
complete, carrier-compliant IMS client. ModemManager 1.20+ exposes a Voice
call API (`mmcli -m 0 --voice-create-call`) but that API drives the modem's
native AT-based voice bearer over LTE — which does **not** implement the
full IMS SIP/RTP stack required by carriers, and works only for a small
subset of operators (mostly operators with generic voice bearers). For
broad carrier support, Nuxel needs either:

1. **oFono + oFono-IMS / ModemManager Voice** for operators that support a
   modem-native IMS via AT commands, or
2. a **user-space IMS/VoNR client** (e.g. an adapted *sipdroid-style* /
   open-source IMS stack such as `pmtel-daemon` from the postmarketOS/LineageOS
   community, or Samsung's `ims` RIL blob) talking to the modem's LTE/IP data
   bearer and registering with the carrier IMS core.

For the production Nuxel phone, we anticipate needing to **carry an IMS
client** (whether Samsung's proprietary IMS stack from the vendor firmware or a
community-maintained open IMS daemon) and to **obtain carrier provisioning and
handset approval** per operator. The strategy below documents the paths, the
carrier-specific IMS APN settings, the config-table model, the mmcli voice
call flow, an implementation plan, and the likely blockers.

---

## 2. Modem / IMS Overview

### 2.1 The Samsung Exynos 5500 modem

- Connected over **PCIe Gen3 using MHI (Modem Host Interface) v2**.
- Exposed to `ModemManager` through the **Samsung plugin** (`mm-plugin-samsung`),
  which speaks the Samsung-AT dialect.
- Data plane requires the kernel **MHI bus generic PCIe driver**
  (`CONFIG_MHI_BUS_PCI_GENERIC`) plus the Exynos 5500 MHI vendor glue
  (`CONFIG_MHI_SAMSUNG_EXYNOS5500`).
- Modem firmware (`modem.bin`, ~200 MB) is closed-source and must be extracted
  from the factory **modem partition**. Nuxel **accepts this binary blob** and
  focuses open-source effort above the firmware interface.
- The modem natively supports a Samsung-AT "voice call over IMS" channel on
  some firmware revisions, which ModemManager's `+CGAODE`/`+CLIP`-style AT can
  bridge — but **full IMS registration typically requires carrier-specific
  firmware configuration** the OEM must approve.

### 2.2 IMS in the Linux user-space ecosystem

| Layer | Technology | VoLTE role | Mainline status |
|---|---|---|---|
| Telephony daemon | ModemManager | Modem control, bearer data, voice call API | ✅ Active |
| Telephony daemon (alt) | oFono | Modem control, IMS awareness | ✅ Active |
| Voice call API | ModemManager Voice (Call) | `mmcli -m 0 --voice-create-call` + audio | ✅ 1.20+ |
| IMS stack | oFono IMS plugin / `ims` | SIP/RTP over LTE | ⚠️ Partial |
| IMS stack (Samsung) | Vendor `ims` binary | Carrier-compliant VoLTE | ✅ Vendor blobs |
| Carrier config | CarrierConfig / MOBIWIRE | APN + IMS feature flags | Nuxel-specific |
| Call UI | Phosh Call UI / nuxel-dialer | User interface | Nuxel / Phosh |

**ModemManager vs oFono:** Nuxel's primary stack today is **ModemManager**
(it is the daemon wired into nuxel-dialer, nuxel-messages and the telephony
portal). For VoLTE we keep ModemManager for modem control/SMS/data and plan an
oFono-based IMS companion (or a vendor IMS client) for the IMS registration
plane. We treat the two as complementary, not competing, for the mustang
VoLTE bring-up.

---

## 3. Carrier-Specific Configuration Model

Nuxel stores per-carrier VoLTE/IMS settings as **CarrierConfig-style data**
mirroring the Android model, so that a single telephony architecture applies
across EU and US operators. The data lives in `/etc/nuxel/carrier/` and is keyed
by a normalized Mobile Network Code / Mobile Country Code (MCC-MNC) plus the
carrier's SPN.

### 3.1 Config fields (CarrierConfig-compatible) for VoLTE

| Field | Description | Example (vzw) |
|---|---|---|
| `mccmnc` | Network identity | `311480` (Verizon) |
| `carrier_spn` | Display name | `Verizon` |
| `ims_apn` | IMS APN | `vzwims` |
| `ims_apn_user` / `ims_apn_password` | Often empty for IMS | `(empty)` |
| `ims_apn_protocol` | IPv4 vs IPv6 | `IPv4v6` |
| `ims_sip_endpoint` | IMS core proxy (left to network discovery) | `(auto)` |
| `ims_auth_mode` | IMPI/IMPU handling | `sip-digest` / `aka` |
| `ims_emergency_support` | e911/e112 over IMS | `true` |
| `volte_enabled` | Feature flag | `1` |
| `volte_preferred` | Prefer VoLTE over CS fallback | `1` |
| `volte_wifi_calling_vowifi` | Wi-Fi calling over IMS | `0`
| `rat_allow_volte` | LTE radio technology gating | `LTE` |
| `carrier_wants_ims` | Carrier expects IMS registration | `true` |
| `audio_route` | VoLTE audio profile (UCM) | `VoiceCall` |

### 3.2 Config example (Verizon)

```ini
# /etc/nuxel/carrier/311480.ini
[mccmnc]
mcc = 311
mnc = 480
carrier_spn = Verizon

[ims]
ims_apn = vzwims
ims_apn_user =
ims_apn_password =
ims_apn_protocol = IPv4v6
ims_apn_auth = pap_chap
ims_sip_endpoint = auto
ims_emergency_support = true
ims_sip_transport = UDP

[volte]
volte_enabled = 1
volte_preferred = 1
rat_allow_volte = LTE
```

---

## 4. Config Table (Carrier → IMS APN → VoLTE Status → Notes)

> **Legend — VoLTE status:**
> - ✅ **Likely** = carrier publishes an IMS APN and VoLTE is widely deployed; highest priority.
> - ⚠️ **Conditional** = VoLTE supported but requires IMS client / provisioning / handset approval.
> - ❌ **Not yet** = no confirmed IMS APN or VoLTE unavailable without proprietary stack.
>
> IMS APNs listed are the publicly documented / widely reported values; always verify
> against the current carrier portal or OEM config at implementation time.

### 4.1 EU carriers (primary launch market — Netherlands, DE, FR, UK, etc.)

| Carrier | MCC-MNC | IMS APN | VoLTE status | Notes |
|---|---|---|---|---|
| KPN (NL) | 204-08 | `ims` | ⚠️ Conditional | IMS APN `ims` with chap auth; VoLTE deployed; requires IMS client + handset approval. Postpaid preferred for bring-up. |
| Vodafone NL | 204-04 | `ims` | ⚠️ Conditional | VF Group IMS; APN `ims`; group-wide VoLTE + VoWiFi; requires VG certification. |
| odido (NL) — successor brand of former T-Mobile NL, network identity 204-16 retained | 204-16 | `ims` | ⚠️ Conditional | DT/Telekom group IMS; APN `ims`; strong developer ecosystem (baseline). Former T-Mobile NL network identity 204-16 carried over in the rebrand; verify APN in carrier portal at bring-up. |
| Deutsche Telekom (DE) | 262-01 | `ims` | ⚠️ Conditional | Largest EU carrier; APN `ims`; fully VoLTE by default; certifies new devices. |
| Vodafone DE | 262-02 | `ims` | ⚠️ Conditional | IMS APN `ims`; VG certification. |
| Telefónica / O2 DE | 262-03 | `ims` | ⚠️ Conditional | O2 APN `ims`; VoLTE generally on for certified handsets. |
| Orange FR | 208-01 | `ims` | ⚠️ Conditional | Orange group IMS APN `ims`; APN type `ims`; strong EU footprint. |
| SFR FR | 208-10 | `ims` | ⚠️ Conditional | APN `ims`; VoLTE deployed; requires IMS client. |
| Bouygues FR | 208-20 | `ims.lte` | ⚠️ Conditional | Reported IMS APN `ims.lte`; verify per-modern config. |
| Vodafone UK | 234-15 | `ims` | ⚠️ Conditional | IMS APN `ims`; 3G sunset; VoLTE is **required** for voice — high priority. |
| EE (BT) UK | 234-30 | `ims` | ⚠️ Conditional | IMS APN `ims`; EE certifies; bandwidth-rich VoLTE. |
| O2 UK | 234-10 | `ims` | ⚠️ Conditional | APN `ims`; VoLTE for certified devices. |
| TIM (IT) | 222-01 | `ims` | ⚠️ Conditional | APN `ims`; VoLTE deployed. |
| Vodafone IT | 222-10 | `ims` | ⚠️ Conditional | VG IMS APN `ims`; certification required. |
| Proximus (BE) | 206-01 | `ims` | ⚠️ Conditional | APN `ims`; VoLTE for certified. |
| Telenor (SE/NO/DK) | 240-01 / 242-01 / 238-01 | (varies) | ⚠️ Conditional | Telenor/VoLTE group; check per-country APN. |
| Telia (SE/FI/NO/DK) | 240-01 / 244-91 / 242-01 / 238-01 | (varies) | ⚠️ Conditional | Telia group; per-country IMS APN. |

### 4.2 US carriers

| Carrier | MCC-MNC | IMS APN | VoLTE status | Notes |
|---|---|---|---|---|
| Verizon | 311-480 (also 310-000/310-004) | `vzwims` | ⚠️ Conditional | Public `vzwims` IMS APN; Verizon strictly certifies handsets and requires CDMA-less provisioning; historically locks VoLTE via carrier config. **Highest-value US target but hardest certification.** |
| T-Mobile US | 310-260 | `ims` | ⚠️ Conditional | APN `ims`; T-Mobile is developer-friendly and generally VoLTE-by-default; realistic first US bring-up. |
| AT&T | 310-410 | `ims` | ❌ Not yet | APN `ims` (historically `ims` with `ipv4v6`); AT&T **whitelists** phones for VoLTE — a significant blocker for bring-your-own OS. Moves to ⚠️ Conditional only after OpenDevelopment / IMS whitelist approval for the Nuxel device. |
| US Cellular | 312-470 | `usccims` | ⚠️ Conditional | Reported IMS APN `usccims`; niche. |
| Mint Mobile / Metro (TMO MVNOs) | inherit TMO | `ims` | ⚠️ Conditional | MVNOs ride T-Mobile VoLTE. |

**Note on AT&T/Verizon:** AT&T prohibits (contractually and via IMS whitelist)
non-approved devices from VoLTE; Nuxel should expect AT&T postpaid VoLTE to be
a **later-phase** milestone. AT&T (and, via Open Development certification, Verizon)
move from ❌ Not yet to ⚠️ Conditional only after OpenDevelopment / whitelist
approval for the Nuxel device. Verizon requires the device be provisioned on the
CDMA-LESS network element and pass Open Development certification. T-Mobile US
is the recommended **first US VoLTE bring-up** because it does not hard-whitelist
IMS registration the way AT&T/Verizon do.

---

## 5. The `mmcli` Voice Call Flow

ModemManager exposes a Voice call API on the call object. Illustrative flow for
the mustang bring-up (adjust device index as needed):

### 5.1 Verify modem + enable voice setup

```bash
# List modems
mmcli -L

# Examine modem capabilities / supported modes
mmcli -m 0

# Refresh the modem, enable the RF / packet service
mmcli -m 0 --enable
mmcli -m 0 --set-allowed-modes=4g

# Ensure the modem is registered on LTE (network will be the IMS-capable carrier)
mmcli -m 0 --3gpp-scan
mmcli -m 0 --status

# Create the voice bearer (Voice domain via IMS requires carrier IMS config)
mmcli -m 0 --voice-create-call --number "+31612345678"
# → allocates a <call-index>, e.g. /org/freedesktop/ModemManager1/Call/0

# Place the call
mmcli -c 0 --start

# Observe call state (unknown / dialing / ringing / active / terminated)
mmcli -c 0 --monitor
```

### 5.2 Accompanying data bearer (IMS needs an LTE data context)

IMS media runs over the LTE data plane, so the device must attach a data
bearer on the carrier network first:

```bash
mmcli -m 0 --create-bearer \
  --apn ims \
  --ip-type ipv4v6 \
  --allow-roaming yes
mmcli -m 0 --attach-bearer <bearer-index>

# For data-capable plans use the "default" APN next to the ims APN:
mmcli -m 0 --create-bearer --apn default.vodafone.nl ...
```

### 5.3 Audio routing (ALSA UCM / PipeWire)

VoLTE audio must be routed to the same codec path as regular calls. The
`configs/alsa-ucm/GoogleMustang/VoiceCall.conf` UCM profile (already scaffolded)
maps the call audio to the CS42L43 codec so both CS and VoLTE calls use the
speaker/mic path. In PipeWire, route the `nuxel-dialer` call stream to this UCM
verb.

---

## 6. Implementation Plan (Phases)

### Phase A — Telephony foundation (no IMS yet)
- [ ] Confirm Exynos 5500 registered on LTE with attached data bearer.
- [ ] Wire `nuxel-dialer` → ModemManager `Call` API for CS calls + SMS.
- [ ] Add ALSA UCM `VoiceCall` routing and PipeWire call-audio profile.
- **Exit criterion:** CS voice call + SMS work on an LTE-registered SIM.

### Phase B — IMS APN + modem-native voice bearer
- [ ] Implement carrier-config loader (`/etc/nuxel/carrier/*.ini`) and match by MCC-MNC.
- [ ] Create the `ims` data bearer alongside the default bearer.
- [ ] Test ModemManager Voice call object on the IMS-capable network (see mmcli flow).
- **Exit criterion:** mmcli-given call on LTE reaches the carrier network via the
  modem-native IMS/vendor voice bearer **for at least one test carrier** (e.g. T-Mobile NL/DE or T-Mobile US).

### Phase C — Carrier-compliant IMS client
- [ ] Evaluate and integrate an open IMS client (oFono IMS, _pmtel-daemon_,
  or a community Enosium/ims fork) for SIP/RTP IMS registration.
- [ ] If no community client meets carrier compliance, design the vendor-IMS
  bridge: run Samsung's `ims` binary under the Nuxel userspace with the
  `nuxel-bridge` IPC (kernel/network namespaces as-is; IMS over the wwan0 data
  bearer).
- [ ] Implement VoLTE emergency call (e112/e911 over IMS) handling.
- **Exit criterion:** ModemManager/oFono shows an IMS-registered state and a
  SIP call to a landline/another IMS device completes.

### Phase D — Carrier config distribution & approval
- [ ] Build a CarrierConfig bundle updated OTA (`images/rauc`).
- [ ] Per-carrier bring-up matrix (this doc) is the source of truth.
- [ ] Contact carriers for hardware approval / IMS provisioning (see Risks).
- **Exit criterion:** VoLTE + VoWiFi work on ≥2 EU carriers and ≥1 US carrier.

---

## 7. Risks & Blockers

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| **Carrier IMS approval / whitelisting** (AT&T, Verizon) | 🔴 High | High | Launch VoLTE on T-Mobile US + EU carriers (KPN/DT/VF) first; document whitelist steps; treat AT&T/Vz as later milestones. |
| **IMS config signing / carrier config signing** | 🔴 High | Medium | Some carriers sign IMS config; obtain signing flow or use carrier-approved defaults; keep a config-override escape hatch. |
| **Exynos 5500 IMS capability is closed/firmware-gated** | 🟠 Medium | Medium | Vendor firmware provides IMS via Samsung-AT; verify on-device; may need vendor `ims` blob → bridge. |
| **No mature open-source IMS client** | 🟠 Medium | Medium | oFono-IMS is partial; evaluate _pmtel-daemon_ / Enosium; fall back to vendor IMS bridge. |
| **ModemManager Voice API not supported by this firmware revision** | 🟠 Medium | Low–Med | Firmware revision check; upstream ModemManager Samsung plugin fix. |
| **VoLTE audio routing / codec negotiation (AMR-WB)** | 🟡 Low | Medium | UCM `VoiceCall` verb + PipeWire profile covers the CS42L43 path; test AMR-WB on wire. |
| **Emergency-call (e112/e911) liability** | 🟡 Low | Medium | Ship with working CS/IMs emergency + eSIM; document per-carrier e911 qualifiers. |
| **Regulatory / spectrum device approval** (CE + FCC/PTCRB) | 🟡 Low | Medium | Radio module already GSM-certified in factory device; Nuxel reuse keeps certificates. |

**Top blockers to call out explicitly:**
1. **Carrier approval / IMS provisioning** — the single hardest non-technical gate.
2. **IMS config signing** — carriers may require signed config blobs Nuxel cannot self-sign.
3. **Modem IMS capability exposure** — depends on closed Samsung firmware.

---

## 8. References

- kernel.org Linux 6.12 LTS; `CONFIG_MHI_BUS_PCI_GENERIC`, `CONFIG_MHI_SAMSUNG_EXYNOS5500`
- Freedesktop **ModemManager** Voice API docs — `mmcli -m 0 --voice-help`
- oFono project (`ofono.org`) — IMS plugin / telephony daemon
- postmarketOS `pmtel-daemon` / Enosium community IMS discussion
- Google Pixel factory images — `modem` partition firmware (`modem.bin`)
- Android `Telephony / CarrierConfig` data model — adapted for Nuxel `carrier/*.ini`
- phosh / GNOME Call UI integration notes; `configs/alsa-ucm/GoogleMustang/VoiceCall.conf`
- Nuxel driver tracking: `docs/driver-status.md`, `docs/roadmap.md` (telephony rows)

---

*This document is a living strategy; carrier APNs and VoLTE status must be
re-verified against each operator's current documentation at bring-up time.*
