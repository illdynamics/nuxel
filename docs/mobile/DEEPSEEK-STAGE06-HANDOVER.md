# DeepSeek Stage 06 handover — read first

## Native mobile internet handover — 2026-11-25

**LTE is restored and survives normal reboot; the complete internet-sharing acceptance contract has NOT passed.** Latest implementation checkpoint `39892d45`. Read [current state](NUXEL-LTE-STATE.md), [physical acceptance](NUXEL-LTE-PRODUCTION-ACCEPTANCE.md), [sharing architecture](NUXEL-INTERNET-SHARING.md), and [benchmark status](NUXEL-LTE-SPEEDTEST.md). Older blocked/NM-ownership descriptions below are historical, not the installed runtime.

Milestones: entry `c6f0c4bc` already contains registration recovery; `f5ba8428` adds reproducible startup and native IPv4 compatibility; `803c7d1b` fixes guard check semantics; `0e0ba871` implements isolated LTE sharing; `ecd1dea4` fixes live bridge/UI integration; `39892d45` fixes hotspot transition status. The later acceptance documentation commit changes no runtime code. Use `git log -1` for that final documentation checkpoint.

Known-good production tuple: attach1/proto ipv4/mode lte/reattach IA0, APN internet. Carrier delivery remains IPv6-only. Native L3 + resolved + carrier-discovered TAYGA CLAT provide actual IPv6 and IPv4 internet. Preserve the validated MTU1500/IPv4-route1480 and the scoped resolver compatibility shim. Do not reinstate the nonactivating generic NM profile: actual rmnet0 is NMDevicePpp. Finish NM integration against real hardware without manufacturing MM objects or introducing a second modem owner.

`NativeRadio` uses private D-Bus with NULL_MAIN_LOOP and no exit-on-disconnect. This fixes the physically reproduced HTTP-bridge exit/segfault. Its sandbox now permits AF_NETLINK for actual route/interface reads. Settings, QS and Home consume the same Radio1/sharing services; stats use real counters. Unavailable signal measurements and serving-operator name stay unknown. APN editing, modem network preferences and fullscreen sharing indicators are not complete.

Sharing workers use the existing USB gadget and dedicated wlan1, per-interface policy tables, carrier-scoped DNS and private firewall/NAT rules. They never start automatically on reboot. Preserve existing VPN kill-switch refusal and management restrictions. Latest reversible sharing deployment backup: `/var/lib/nuxel/sharing-install.p2p3JM/rollback.sh`. Installed hashes match source in the evidence receipt. Do not copy the repository recovery-guard file wholesale onto this device: its existing device-specific executable pin differs; only the check-argument fix was applied to it.

Next physical gates: consenting external Wi-Fi hotspot client; resolve the transient concurrent-sharing USB SSH stall while retaining ZeroTier; two external clients simultaneously; remaining Wi-Fi/VPN/coverage transitions; final saved-password UI action; three speed measurements after explicit allowance confirmation. Both real handset browsers already rendered normal HTTPS on cellular. No benchmark result exists.

Final state at acceptance: mobile ON/ACTIVE, native IPv6 and translated IPv4 HTTPS200, Wi-Fi disabled, hotspot/tether OFF, USB and ZeroTier SSH usable, no owned sharing routes/NAT/DHCP left. The deliberate USB-forwarding deny remains when sharing is off. Preserve unrelated owner RFS edits and untracked notes/evidence.

**DeepSeek owns all remaining SMS, ordinary voice, ABOX call audio, IMS, VoLTE and other telephony work.** None was implemented or exercised here. Existing research below is retained. No merge or push was performed; separate authorization is still required.

---

## Finisher handover — 2026-11-25 (supersedes prior deployment notes)

**Not LTE accepted; not full Stage 06 complete.** Implementation commit `c52726d3`. Read the new
[acceptance receipt](NUXEL-LTE-PRODUCTION-ACCEPTANCE.md) and
[evidence](evidence/finisher-20261125/) first. Existing protocol/SMS/voice
research below is retained.

Implementation: Radio1 owns persisted `/var/lib/nuxel-radio/mobile-data`, bounded
start/reconnect, CID1 release/readback and network-helper lifecycle. Settings
and QS use `network/mobile-data-enabled {enabled: boolean}` and `phone/status`.
The bridge accesses system-bus `nl.nuxel.Radio1`, `/nl/nuxel/Radio1`: only
GetDataSessionState, GetSimState, StartDataSession(su), StopDataSession are
exported there. The full session-bus API is retained and retried if login starts
later. Control is checked using sender credentials; bridge capability checks
remain in force. Unsigned profile conversion is required with introspection off.

NM: `cellular_nm.py` replaces direct L3/resolver application in the existing
helper entry point. A temporary generic profile UUID
`8ba40bd5-cc4c-4a12-96c5-757170a1d106`, handler `nuxel-cellular`, associates actual
rmnet0/CID1. Only CP-provided usable IP/DNS can create it. NM owns addresses,
routes and DNS; autoconnect is false because Radio1 must establish the bearer
first. Bounded Radio1 reconnect supplies a fresh profile. Old helper journals
are rolled back before migration. No competing modem owner or fake MM device.
Profile syntax passed on installed NM 1.54.3; live bearer integration is untested.
Reference: [NM device handler contract](https://www.networkmanager.dev/docs/api/latest/NetworkManager-dispatcher.html).

Production install (on handset, staged repository root):

```sh
bash services/nuxel-modem/bin/nuxel-modem-install.sh --production-config \
  /etc/nuxel/modem/production.json /usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.production.hw
bash tools/s10plus/s5000ap-05/install.sh --with-ui
```

Installer saves replaced userspace files under `/var/lib/nuxel/radio-install.*`
with `rollback.sh`; restarting affected services is explicit. Native top-bar
build requires installed Wayland/Cairo/Pango development packages. Rootfs
packaging already installs the bridge source directory and PWA tree. Production
CP loader and hash checks remain unchanged. Missing normal-boot EFS input was
fixed by the bounded read-only service; `.device` units are not announced for
this handset's pre-existing block devices, so a verified oneshot mount is used.
No protected-storage content is written. Preserve the original recovery loader.

The corrected enabled reboot reached ONLINE and automatically attempted data;
PS remains UNKNOWN/raw7, CS NOT_REGISTERED, no carrier reject cause, no bearer or
IP. The entry executable matched historical successful build17 (`6893af43…`),
and successful attach environment was retained. Fixing startup did not restore
registration. Do not relabel raw7, bypass registration, repeat RF power cycles,
or infer carrier outage/provisioning failure without evidence.

UI: live handset WebKit clicks exercised QS OFF/ON and Settings OFF/ON after
normal credential unlock. Screenshots and DOM/backend receipts verify the page,
tile and synchronization. An exact-match installer migration replaces only the
shipped obsolete Settings session grant with a persistent first-party network
grant; explicit owner choices and denials are untouched. Signal strength and
serving operator remain unknown; no decoder was fabricated. Final preference ON.
Enabled startup and disabled startup were exercised in separate normal boots;
the first failed reboot exposed the missing mount and is retained as evidence.
Final running/installed radiod SHA256 is `06468e62e3846220edf403d07c65ccda3070115678709db6a2cc2db8281b68e0`,
with zero daemon restarts in the final boot. Current installer rollback is
`/var/lib/nuxel/radio-install.37RKtb/rollback.sh`; earliest entry-file backup is
`/var/lib/nuxel/radio-install.MeZssL/`. Production mount install backup is
`/var/lib/nuxel/modem-production-install.75t5f1/`. Staging/evidence live under
`/var/lib/nuxel/lte-finisher-20261125/`. The enabled-reboot receipt predates the
final SIM-wait timeout/IP-reporting refinements; final code booted with OFF and
subsequently handled both live UI toggles. No enabled internet reboot is claimed.

Existing SMS backend: durable storage and correlated native send/receive exist;
outgoing/incoming physical acceptance remains outstanding. Existing call-control
backend remains intact. Voice still needs ABOX VoiceCall routing, call audio and
physical two-way acceptance. IMS/VoLTE remains unavailable/unimplemented. No SMS,
call, audio or IMS work was performed. Owner `lte.md`, `pers.md`, and existing
RFS policy/test edits are retained outside the implementation commit.

## Latest LTE finalizer handover — 2026-11-25

**BLOCKED: genuine PS registration remains UNKNOWN/raw7 after the verified
NV-capable CP boot. LTE production acceptance is incomplete.** This section
supersedes older runtime/deployment statements below, without replacing the
protocol research. Read [acceptance](NUXEL-LTE-PRODUCTION-ACCEPTANCE.md),
[speed-test status](NUXEL-LTE-SPEEDTEST.md), and the
[physical receipt](evidence/finalizer-20261125/final-state.json).

### Checkpoints and preservation

- Verified entry HEAD `4b95f377a0fe742a103ff7f2a8260e1b3fae8c47`, requested branch.
- `f42c18ef`: installed verified bounded CP production startup and eight tests.
- `483be956`: bounded RFS test fixture join; only this correction was staged.
- `35f673a9`: repeat installation support and competing-owner test (nine startup tests now pass).
- The final documentation commit follows; resolve it with
  `git log -1 --format=%H -- docs/mobile/`.
- Existing uncommitted Settings/QS/top-bar, bridge, mobile_data, radiod,
  serializers, RFS and test changes remain in the tree. They were not replaced,
  deployed or claimed as production acceptance. Entry diff/status are saved in
  private host `/tmp/nuxel-lte-finalizer-20261125/`.
- No merge/push, phone reboot, Wi-Fi disable, SMS, calls or protected writes.

### What was actually reconciled and exercised

The installed/running daemon still hashes to the successful Round43 build17
`6893af43cea0129234ed0adceed55517db5834d5c558f4f3e0bc4e694e76955a`.
The tracked LTE/loader source did not change between `24e61763` and entry HEAD;
changes in that subtree were a receipt and focused call-service code/tests.
The CP loader source is unchanged between `9dc13efd` and `24e61763`.
The later uncommitted policy/UI work is not in the running binary.

The old production loader hash `d963219f…` was confirmed. One controlled CP
boot at 00:12:31 CET used historical verified `530732cb…`, existing read-only
RADIO and verified device-owned NV. It returned ONLINE/exit0. Native OES
transferred 987 bytes and SIM became ready; radio was ON. One subsequent
native StartDataSession ran the successful APN/profile configuration, preserving
all Astra corrections. Service domain read back wire1, preferred mode11,
profile/attach commands returned success; optional mobile-data command returned
0x8003 (unsupported). PS remained raw7/UNKNOWN and the bounded registration
wait failed. No actual bearer/IP/traffic resulted.

This is new counterevidence against the old loader being the **sole** cause.
There is no demonstrated carrier outage or provisioning diagnosis. Do not
rename raw7 to registered, repeat resets, or skip the registration gate.
Native NET_REGIST carries LTE RAT but not actual packet registration.
The old daemon's initial-attach flag remains3, protocol default, auth none,
PDP full, CID1; environment identical to the previously successful build17 path.
The temporary registration-only override was removed and systemd reloaded.
Current running daemon was launched without CLI auto-arm; the bounded session
was explicitly requested and is now FAILED. On its next start the original
persistent `10-data-path.conf` still supplies `--arm-data-path`. This is not a
persisted user preference and remains an unfinished integration task.

### Installed production boot correction

`services/nuxel-modem/bin/nuxel-modem-install.sh --production-config CONFIG LOADER`
now invokes the production installer. It validates the supplied binary hash,
saves prior files, installs the separate production loader/guard/config/unit,
preflights all inputs, and creates `05-production-boot.conf` with Requires/After
for radiod. It reloads systemd but does not restart CP or radio. It leaves the
old Stage04 boot loader/guard/unit unchanged. Failure restores prior files.

Installed paths and identity:

| Artifact | SHA-256 / location |
|---|---|
| Production NV-capable loader | `/usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.production.hw`, `530732cb35614ba9aa8d12a6a5717ef8ea7ff4a6d46039599e9a8e6c42d75b4c` |
| Production guard | `/usr/libexec/nuxel/nuxel-cpbootd-production`, `2566162f4483d33e849745888ea38315c6d92ec75a38a18e8bdb59de25e8bf7c` |
| Existing recovery loader | `d963219f424113a63695c0c2aad583be7ff2cba9ccc22700107f95a1031ba630`, unchanged |
| Production configuration | `/etc/nuxel/modem/production.json`, root0600 |
| Execution manifest | `/var/lib/nuxel/lte-finalizer-20261125/production-manifest.txt` |
| Source staging / logs | `/var/lib/nuxel/lte-finalizer-20261125/` |
| Install rollback backup | `/var/lib/nuxel/modem-production-install.EwaFUS/` (first install); `Nj9ejQ` (repeat install) |

The guard validates SHA256 of binary, firmware and manifest, exact Samsung NV
checksum and size, root-controlled config/artifacts, persistent paths, and
character-device boot endpoint. It waits for the EFS mount via systemd, rejects
existing FMT/RFS owners before an OFFLINE boot, and bounds a single attempt to
60 seconds plus process timeout. ONLINE is a no-op; other states fail without
reset. Production service has Restart=no and 120-second total deadline.
The old loader itself only checks that a manifest argument exists; actual
manifest hashing is now enforced by the wrapper.

Target `--check` passed; `systemd-analyze verify` exited0 with unrelated existing
unit warnings retained in evidence. Starting the service on the ONLINE CP
returned active/exited/ExecMainStatus0 without reset. This proves installation,
input validation and ONLINE skip, **not cold boot or LTE readiness**.

Reproduction on this handset (does not start/restart hardware):

```sh
bash services/nuxel-modem/bin/nuxel-modem-install.sh --production-config \
  /etc/nuxel/modem/production.json \
  /var/lib/nuxel/round43-20261124-fixed-wire/nuxel-cpbootd.aarch64.hw
/usr/libexec/nuxel/nuxel-cpbootd-production --check
```

For another installation, build `tools/s10plus/s5000ap-uapi/build.sh` with the
native/cross toolchain, supply the resulting hardware loader and a root0600
JSON with `loader_sha256`, `firmware`, `firmware_sha256`, `manifest`,
`manifest_sha256`, `nv_image`, `nv_md5`, `deadline_ms`. Use that handset's verified
inputs. A rebuilt loader must be separately accepted; compiler success is not
physical equivalence to the pinned historical executable. No NV/firmware is
redistributed or copied from a different handset. The startup wrapper is
reproducible from this checkpoint; the complete radio/NM/UI install is not done.

Rollback before another startup: stop only `nuxel-cpbootd-production` (its
oneshot has no CP shutdown action); remove the new five paths listed by the
installer's `paths` array, restore numbered backups0..4 where present, and
`systemctl daemon-reload`. For this first install all five were previously
absent. Do not remove the old Stage04 loader or reset CP. Base radiod service
and original drop-ins were also backed up under the finalizer directory.

### Remaining integration and acceptance

- Real MM integration is absent; live MM has only its root object and NM labels
  rmnet0 unmanaged PPP. Existing cellular_link owns Linux addresses/routes;
  do not add a second route manager or fake MM bearer. NM DNS ownership remains
  unfinished. Preserve metric2100/table106/source rules and Wi-Fi preference
  while deciding actual NM/MM integration.
- Existing policy/UI draft is unaccepted. In particular draft mobile_stop treats
  optional 13/29 unsupported0x8003 as a terminal failure, although that result
  was physically observed on this modem. Review this before exposing OFF.
  APN persistence, radio/session-bus startup readiness, full state invalidation,
  stop/reconnect/rapid toggle behavior and actual carrier/signal remain gaps.
- No signal conversion was invented. GetSignalInfo remains unavailable in the
  running daemon. No physical Settings/QS/top-bar acceptance occurred.
- USB SSH is verified at `10.100.10.1:2022`, carrier1; ZeroTier SSH remains at
  `10.11.12.99:22`. Wi-Fi and ZeroTier were preserved, not used as LTE evidence.
- No current IPv4 or IPv6 data service. Historical IPv6-only successes stand.
  No benchmark or reboot-to-internet measurement. Data-allowance confirmation
  was requested but not received. Both normal reboot gates remain unperformed.

Next execution: begin with the fresh failure evidence and a read-only live
state check. Establish the next demonstrated registration-layer defect or
external carrier/SIM condition before any more CP recovery. Finish/test the
existing native policy drafts and actual NM integration; then deploy with
independent USB management, validate real cellular DNS/HTTPS, UI ON/OFF/ON,
Wi-Fi transitions, enabled/disabled normal reboot, and one consented speed test.
Do not count the new boot guard as completion of those gates.

The two previously authorized SMS messages remain unsent. Native SMS physical
acceptance is a separate future task. Voice still needs ABOX VoiceCall routing,
call-audio integration and physical acceptance; IMS limitations remain. No SMS,
telephony or IMS work was performed in this pass.

Regression details: see `evidence/finalizer-20261125/regression.json`. The initial
GCC suite exposed a test-only snprintf truncation warning, corrected without
warning suppression; initial diagnostics retained. Phone pytest/clang were
unavailable. CP tests were run directly with a stdlib function runner. AArch64
GCC sanitizer fuzz failed at runtime allocating its shadow mapping; that
failure is retained, not labeled a parser pass. The full host suite and ASan/UBSan completed with exit0, including both
3,000-case fuzz runs. Nine production guard tests passed on host and handset;
13 CP mock tests and six draft adapter tests passed. The phone sanitizer
failure remains a limitation. No NM/route/DNS/UI/reboot physical tests passed
by implication from these offline suites.

---

Final consolidation audit, 2026-11-24 CET. **Persistent LTE internet is not
physically verified. Mobile-data toggle, Settings, Quick Settings and top-bar
native integration are not complete or physically verified.** No Stage06 or
persistent-LTE completion marker is warranted.

## Immediate situation and stop reason

Astra's LTE breakthrough remains real historical evidence and its implementation
is preserved. However, at this pass's entry the phone had already rebooted
outside the execution. It had CP ONLINE and SIM ready but no registered packet
service, no cellular address and zero rmnet0 traffic. One normal native
`StartDataSession` request timed out at `PS_REGIST_VERIFY` after roughly 36
seconds. A fresh read at **2026-11-24 23:14:31 CET** confirmed the same failure.

The installed CP loader is the old pre-NV binary; the verified NV-capable
loader is only in the Round43 artifacts. The normal boot unit is static/inactive
and its guard still pins the old binary and omits NV arguments. This deployment
mismatch is proven. It is **not a controlled causal diagnosis** of registration
failure. RadioState was `unknown`, which also needs normal readiness handling.
No CP reset or firmware investigation was attempted to recover the baseline.

The mission explicitly requires checkpointing and termination on a substantial
unexpected blocker. This pass applied that rule when the expected live LTE
baseline was absent and the single bounded native retry failed. It completed
the evidence/source handover and regression checks, not a new reverse-engineering
campaign. No production code, installed unit or executable was changed. No
Wi-Fi-off test or reboot occurred. ZeroTier management was preserved; USB had
carrier 0 and direct Wi-Fi SSH was refused. The owner was asked about USB but no
working independent management connection was established during this pass.

## Required reading order

1. [NUXEL-LTE-STATE.md](NUXEL-LTE-STATE.md): current boot/session/network/UI
   implementation, exact failure and missing production pieces.
2. [NUXEL-TELEPHONY-STATE.md](NUXEL-TELEPHONY-STATE.md): call control exists;
   call audio, app integration and physical voice acceptance remain.
3. [NUXEL-SMS-STATE.md](NUXEL-SMS-STATE.md): native codecs/store/service exist;
   native app integration and actual message exchange remain.
4. Original cellular acceptance contract:
   [`../../pwn-mob/06_SIM_LTE_MODEMMANAGER.md`](../../pwn-mob/06_SIM_LTE_MODEMMANAGER.md),
   with `pwn-mob/00_MASTER_SAFETY_AND_TRUTH.md` and the current user's mission.
   The `reports/SSP-05_*STAGE-06*` files concern the separate SSP subsystem;
   do not use those as cellular acceptance contracts.
5. [`../S5000AP-IPC41-DATA.md`](../S5000AP-IPC41-DATA.md), then
   [`../S5000AP-IPC41-SMS.md`](../S5000AP-IPC41-SMS.md).
6. `tools/s10plus/s5000ap-05/src/{radiod,data_session,fmt_tx,fmt_rx,cellular_link,sms_service,sms_store,sms_pdu,fmt_sms,call_service,fmt_call}.c`,
   `scripts/cellular_link.py`, corresponding tests, and
   `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` / tests.

## Astra discoveries that must not regress

| Corrected assumption | Actual source/evidence boundary |
|---|---|
| CS+PS wire encoding | `fmt_tx_set_service_domain`: internal 0 -> wire **1**; internal CS-only 2 -> wire **2**; PS-only -> 3. Current CP readback 1 is correct. Old wire2-as-CS+PS disabled packet service. |
| Registration raw state | `fmt_rx_reg_state`: raw **1 means NOT_REGISTERED**. Raw2 becomes home, raw6 roaming. Generic ACK, camping and signal do not prove registration. |
| Missing NV boot input | `prepare_nv` / `xmit_nv` added verified device-owned NV download before successful CP initialization. Round43 op13 used loader `530732cb…` with unchanged EFS. Production installer/guard still lag. |
| Samsung checksum | `nv_vendor_md5_hex`: MD5(image plus literal `Samsung_Android_RIL`). Integrity only; never authorization to edit protected records. |
| Firmware | CP reports G975FXXSEFUJ2. EFUJ2 was cross-checked against the earlier DTK9 analysis; addresses in DTK9 analysis are not automatically EFUJ2 function addresses. |
| APN metadata | Descriptor indices **220 and 224**, each value size **360 bytes**. Not a physical EFS offset or an instruction to provision NV. |
| Profiles/session | Vendor vectors corrected SET_APN_INFO, initial profile, DEFINE and activation. `ds_step` skips redundant PS attach when NET already registered; GPRS_PS control flags cannot invalidate that evidence. |
| Detach/recovery | Initial attach can use observed already-detached state; explicit own detach is followed by verified state/restoration. Rejections and timeouts stay bounded/visible. |
| Response validation | Full u16 GEN result and expected origin tuple, not low-byte success. Data path currently correlates phase/origin; legacy pending matching lacks ACK sequence. SMS/call paths do sequence matching. Do not overclaim uniform correlation. |
| IP / actual internet | Native `GetIpInfo`, CP IP decode; successful IPv6 DNS + HTTPS on rmnet0 with Wi-Fi off (ops21/22). No invented IPv4 or generalized dual-stack success. |
| OES | Native startup responds using the device's existing certificate and verified chunk layout, without replacing authentication or exposing keys. |
| SMS | Recovered CS-domain SMS wire path, padded SMSC field, durable intent/receive ACK ordering. Submission is not delivery; synthetic fixtures are not incoming network SMS. |
| Voice | Normal-CS control vectors/parser and call FSM exist. LTE data is not VoLTE/IMS or audio proof. |

Historical reports that must not guide new implementation without these
corrections:

- `reports/S5000AP-MOBILE-NETWORKING-FINAL-ACCEPTANCE.md`, sections 6/7 and
  final matrix: its raw-state registration success and persistent-NV-only
  APN blocker are superseded. Preserve its kernel/device-tree history.
- `reports/S5000AP-06-ROUND38-NV-ITEM-ID-RECOVERED.md`, Round38 final review,
  Round39 NV transaction, Round40 stack/metadata reports, Round41 definitive
  stack analysis, and Round42 ultimate-answer/provisioning conclusions predate
  the corrected descriptor interpretation and successful runtime data path.
  They are historical investigation records, not current provisioning tasks.
- Round43 `SET-APN-INFO-CP-TRACE` was amended with successful operations and
  corrected findings; prefer those amendments and the protocol specification.
- `reports/S5000AP-06-ROUND44-RECONCILIATION.md` is an **initial** snapshot
  before build17 completion. Its build15/deployment description is not the
  current binary, and its live rmnet0 counters are historical.
- Round44 commit/changelog claim of daemon-restart reconnection is narrower
  than persisted user policy or normal cold-boot acceptance. The owner's
  uncommitted Round44 changelog entry has been preserved as written.
- Early commentary in this consolidation initially called wire1 CS-only. This
  was immediately corrected against source: wire1 is CS+PS. No code encoding
  change was made.

## Exact repository and deployment identity

Branch: **`cs/mob-round35-stage06`**. Entry/source HEAD:
**`24e617639a9e91236b1d75d72c9bfaf26703e2f1`**. This commits DeepSeek's recovery
of Astra's call and automatic interface work. Predecessors `2c377487` (native
SMS), `9dc13efd` (protocol/verified LTE) and the previous investigation history
are preserved. No uncommitted Astra source implementation existed at entry.

Incremental consolidation checkpoints:

| Commit | Scope |
|---|---|
| `aaa1ed90` | Immediate four-document recovery skeleton |
| `92307de3` | Live registration failure, deployment mismatch and verified backups |
| `95f6ce7b` | Full LTE lifecycle/network/UI audit |
| `91f246aa` | Telephony and SMS source/evidence audits |

The final documentation/evidence/changelog commit follows these; obtain its
exact hash from `git log -1 --format=%H -- docs/mobile/`.
The final response records that hash. This avoids embedding a self-referential
commit hash in its own tree.

Only mission changes: the four `docs/mobile/*.md` files, redacted evidence
under `docs/mobile/evidence/consolidation-20261124/`, and this pass's scoped
CHANGELOG entry. Production source is unchanged. Initial owner changes:
`CHANGELOG.md` Round44 entry and untracked `astra-kurwa.md`. They remain
uncommitted and byte-preserved apart from insertion of this pass's separate
changelog entry. No merge or push.

| Artifact | SHA-256 |
|---|---|
| Installed and running `/usr/libexec/nuxel/nuxel-radiod`, Round43 build17; freshly reproduced AArch64 build | `6893af43cea0129234ed0adceed55517db5834d5c558f4f3e0bc4e694e76955a` |
| Installed `/usr/libexec/nuxel/nuxel-cellular-link`, identical to repository script | `05619ace0149123f51b8f4f0f289e887ce63f78b342394ecb3e6c42e27054e39` |
| Installed **old** `/usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.aarch64.hw` | `d963219f424113a63695c0c2aad583be7ff2cba9ccc22700107f95a1031ba630` |
| Historically verified NV-capable loader in Round43 backup | `530732cb35614ba9aa8d12a6a5717ef8ea7ff4a6d46039599e9a8e6c42d75b4c` |
| Freshly compiled CP loader this pass, **never run or installed** | `ce65bf9df20343325ceb491e2482fdf735a1a690e1491dd08d2d5b1423bb67df` |
| Audited `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` source | `1fcd2ed3c698c990a9e925c39561898d6ff955362b56a33e4536081393f5f6d8` |

The new CP build is not byte-identical to the historically verified executable;
compilation success does not authorize replacing that known-good binary or
claim physical validation of the new artifact.

Installed radiod configuration: enabled base unit in `/etc/systemd/system`,
`10-data-path.conf` replaces ExecStart with `nuxel-radiod --write-enable
--arm-data-path`; environment ATTACH_CID=1, PROTO=default, AUTH=none,
PDP_TYPE=full, ATTACH_FLAG=3. No NETWORK_MODE override, therefore auto mask11.
`20-sms-storage.conf` makes `/var/lib/nuxel-radio` writable. The installed base
unit lacks the repository's StateDirectory stanza and the runtime directory
needed for helper journaling is not explicitly provisioned writable. Installed
CP service remains Stage04-only; the current owner instruction authorizes
production consolidation, but preserving the existing verification gates is
still required. Do not simply remove guard checks.

## Exact final physical state

Redacted receipt:
[`evidence/consolidation-20261124/live-state.json`](evidence/consolidation-20261124/live-state.json).

| Layer | Observed state, 23:14:31 CET |
|---|---|
| Kernel | `4.14.253-gf7194c1d15ed-dirty`, AArch64 |
| CP / SIM | ONLINE / native `ready` |
| Radio power | Radio1 `RadioState=unknown`; do not infer ON from ONLINE |
| Service domain / preferred mode | Wire1 CS+PS; mode11 LTE/WCDMA/GSM auto readback |
| Registration | PS NOT_REGISTERED, CS DENIED; reported RAT UMTS; no registered carrier claimed |
| Session | FAILED, failure phase PS_REGIST_VERIFY; no attachment or configured IP |
| rmnet0 | DOWN; RX/TX packets 0/0, errors/drops 0; no global cellular IP |
| Routing | No cellular table106 default or 30600/30601 rules; main/local rules remain |
| Address family | None currently; historical internet proven over IPv6 only |
| DNS | NetworkManager-generated resolver; native cellular DNS ownership absent |
| Wi-Fi | Enabled and functioning for management; not disabled during pass |
| Management | ZeroTier SSH reachable; USB carrier0; no verified independent path |
| Services | radiod, NetworkManager, ZeroTier and sshd active; CP boot static/inactive |
| ModemManager | Active daemon, only root object; no exposed modem |
| Recovery timers | No active matching rollback/restore/radio/cpboot timer found; unrelated timers untouched |
| Voice/SMS | Native status available, no calls/messages attempted; SMS storage/SMSC ready, delivery unverified |

Historical interface addresses, DNS, PLMN and packet counts must never become
production constants. The earlier 5,030 RX / 8,221 TX observation belongs to a
different boot/session and is not contradicted by current zero counters.

## Recovery checkpoints and bounded next action

Private host directory: `/tmp/nuxel-lte-consolidation/`, mode0700. It includes
initial Git diff/reflog/HEAD, owner-file copies, raw live observations, deployed
executables, configuration archive, test receipts and scripts. Private device
backup: `/var/lib/nuxel/lte-consolidation-20261124/`. Five SHA256SUMS checks
passed for the copied radio/helper/guard/loader/config archive. Preserve this
archive locally; it includes private configuration and SMS store state and must
not enter Git. The first archive attempt hit an absent `/run/nuxel-radio`;
it was rebuilt successfully with the optional runtime directory handled.

Original artifacts remain intact:
`/tmp/nuxel-round43/`, `/var/lib/nuxel/round43-20261124-fixed-wire/`, its
`efs.before.tar.gz`, `restore-check/`, `round44-checkpoint/`, build directories,
operation manifests and rollback scripts. Historical kernel/BOOT recovery is
covered by `pwn-mob/09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`; no firmware/DT change
is indicated by this pass. `hw-mob-run.log` exists; its final 120KB were
inspected alongside operation/deployment logs. This was a targeted recovery
audit, not an exhaustive reread of all 67MB.

Next agent should first re-read live state. If still failed, verify supported
radio-power and automatic-selection readiness through existing Radio1 APIs;
`SetRadioEnabled` is distinct from mobile data. Do not assume the old loader is
the only possible cause. If a controlled CP initialization is required, use
Astra's exact verified loader/input/manifest/recovery arrangement, preflight
unchanged device-owned NV and known-good recovery, and preserve independent
management. Do not use an old-loader-only rollback as proof of LTE recovery.
No need to roll back this pass: it changed no production deployment.

## Remaining acceptance matrix

“Historical pass” is not current persistence acceptance. Every physical item
below needs a timestamped receipt after the relevant implementation lands.

| Criterion | Status / evidence | Relevant files | Exact next task and required acceptance |
|---|---|---|---|
| Native CP boot/NV | Historical pass; production mismatch | `s5000ap-uapi/nuxel-cpbootd.c`, modem guard/unit/installer | Verified permanent inputs, mounts, manifest/hash validation and bounded boot; physically ONLINE after normal reboot |
| SIM/power/registration | SIM pass; registration failed, radio unknown | `radiod.c`, `fmt_rx.c`, `fmt_tx.c` | Establish supported radio readiness without guesses; actual home/roaming PS registration, not raw1 |
| Automatic bearer/IP | Implemented, historical Round44 evidence | `data_session.c`, `cellular_link.c`, helper | Restore baseline, validate actual CP dynamic IP and helper under final systemd sandbox |
| Mobile-data ON/OFF | Missing policy; Stop only disarms | `radiod.c`, `data_session.c` | Persist one desired state; confirmed release, route/DNS removal, no CP power-off; physical ON/OFF/ON |
| Rapid toggles/restarts | Not accepted; start resets current FSM | Same + new policy tests | Serialized desired-state generations, stale-response handling, recovery of helper journal; repeated/opposite requests and service restart |
| Automatic reconnect | Historical daemon restart only | `data_session_tick`, policy owner | Bounded reconnect after loss, disabled preference prevents reconnect; failure stays explicit |
| Resolver / ordinary apps | Missing native NM DNS path | `cellular_link.py`, `network_manager.py` | Dynamic session DNS through actual owner, cleanup; unbound DNS and HTTPS with Wi-Fi off |
| Routes/fallback | Historical table106/source/oif success | `Link.apply/verify/down` | Verify route preference, both policy rules, address replacement, removal, Wi-Fi loss/restoration and no stale DNS |
| IPv4/IPv6 | Historical IPv6 only | `fmt_rx_ip`, helper | Record real assignment; test IPv6 plus IPv4-only application limitation; no dual-stack claim without proof |
| Settings | Diagnostics only | Settings model/index/driver-diagnostics | Shared preference/status/APN/mode UI, unsupported controls explicit; physically synchronized state |
| Quick Settings | Mobile toggle unavailable | `pwa/nuxel-home/js/qs.js` | One provider, busy/error states, no duplicate requests; physical cross-surface toggle |
| Top bar | No native state provider/signal | `status-bar.js`, API status, `method_get_signal` | Separate registration/RAT/signal validity/data; no invented bars/operator; physical enabled/disabled/search/restart cases |
| Enabled reboot persistence | Not tested; old startup path | Units/installers/policy | Reinstall, controlled normal reboot, auto-connect without a manual StartDataSession; cellular-only HTTPS and UI |
| Disabled reboot persistence | Missing preference | Same | Offline tests plus physical disabled reboot when recovery permits; restore owner-intended state |
| Negative radio cases | Original contract outstanding | `pwn-mob/06_SIM_LTE_MODEMMANAGER.md` | No-SIM, radio-off/airplane recovery, carrier unavailable, DNS failure, service loss; no unrelated hardware changes |
| SMS end to end | Native implementation, no actual exchange | SMS state document | Native app/notification adapter then authorized recipient delivery/incoming proof, Unicode/multipart/persistence |
| Voice end to end | Control only, audio missing | Telephony state document | Native dialer/history/audio then authorized outgoing/incoming/two-way speech and data recovery |
| IMS/VoLTE | Unimplemented | Voice status/capabilities | Keep false/unavailable; assess separately only if a real required voice dependency |
| Full regression | Partial; detailed receipts below | Existing suites | Fix existing native-suite compiler issue, add policy/network/UI tests when implementing; distinguish hardware tests |
| Stage06 completion | Not achieved | All above + original contract | All required original LTE/SMS/voice/persistence gates must have physical evidence |

## Regression receipts and reproduction

All committed receipts live in
[`evidence/consolidation-20261124/`](evidence/consolidation-20261124/README.md).
They contain no private modem payloads, identities, credentials or messages.

| Command/test group | Actual result |
|---|---|
| `bash tools/s10plus/s5000ap-05/build.sh` | Exit **0**. 22 ordinary C suites, 3,000 ordinary fuzz inputs, 3,000 ASan/UBSan fuzz inputs, 12 sanitizer component suites. Both fuzz gates: 0 crashes, 0 timeouts. |
| Compile host cpboot + `python3 -m pytest -q tools/s10plus/s5000ap-uapi/tests` | Exit **0**, **34 passed**. Includes exact NV checksum, size/corruption rejection, TOC and boot mocks. |
| CP boot ASan/UBSan build and all test functions from `test_mock_boot_transcript.py` using that binary | Exit **0**, **13 cases passed**. Mock backend only, no physical loader run. |
| Native full ordinary build/test prefix (`native-tests.sh`) | Exit **1** at existing `rfs_policy.c` format/string truncation warnings under GCC `-Werror`; not a full native pass. |
| Native production radiod build, 12 core suites, hardware-enabled CP loader build (`native-core.sh`) | Compiles/tests completed; wrapper exit **127** at missing `file` utility after builds. Preserve that exit, do not rewrite it as zero. |
| Follow-up native `readelf -h` / SHA256 identification | Exit **0**; both ELF64 AArch64. Radio executable byte-identical to live install. CP binary compiled only. |
| `bash shell/nuxel-shell/nuxel-phone-data/run-tests.sh` on macOS | Exit **1**, test-source `mkdtemp` declaration under strict C11; no test assertions executed. |
| New persisted-policy / UI / network lifecycle suites | **Not implemented or run**; corresponding production functionality is missing. |
| Physical acceptance A | Entry baseline failed; one normal retry failed at registration. |
| Physical acceptance B–F | **Not performed**. No current ON/OFF/ON, cellular-only HTTPS, transitions or controlled reboot acceptance. |

The 12 core suites: fmt_tx, fmt_rx, data_session, rfs_nv, efs_nv, oes_cert,
fmt_sms, sms_pdu, sms_store, sms_service, fmt_call, call_service. The ordinary
build script also includes transport/RFS/cmdmap/MBIM/QBR/NV suites. No warnings
were disabled to manufacture a green native result. No new mock test was
substituted for physical acceptance.

## DeepSeek execution order

1. **Preserve/recover verified LTE first.** Keep source, recovered loader,
   device-owned NV and management. Resolve normal radio readiness / production
   boot mismatch with a bounded, evidence-backed action, not new NV theories.
2. **Finish outstanding LTE integration.** Verified startup and writable runtime,
   one persisted data policy, real disconnect/reconnect, actual resolver
   integration, Settings/QS/top bar; normal installer must contain every file.
3. **Complete remaining SMS.** Native application adapter and notifications,
   uncertainty/retry UI, then explicitly authorized real bidirectional exchange.
4. **Complete remaining telephony.** Native dialer/history, supported call audio,
   then explicitly authorized calls and two-way speech. IMS remains separate.
5. **Combined regression/persistence.** Data before/after messages/calls, policy
   OFF does not power off telephony, Wi-Fi transitions, unbound DNS/TLS,
   enabled/disabled reboot and normal reinstall. Use an independent management
   path for Wi-Fi-off testing; ZeroTier over Wi-Fi alone is not independent.
6. **Acceptance documentation/checkpoint.** Update these state documents with
   actual receipts, preserve owner changes, commit; no merge/push without
   authorization and no Stage07/unrelated subsystem expansion.

### Ready-to-use continuation prompt

> Read docs/mobile/DEEPSEEK-STAGE06-HANDOVER.md first, then its required reading
> order. Continue on cs/mob-round35-stage06 from the final documentation
> checkpoint. Preserve owner CHANGELOG.md edits and astra-kurwa.md. Astra's
> historical IPv6 cellular DNS/HTTPS breakthrough is real, but the last live
> session was FAILED at PS_REGIST_VERIFY after an earlier reboot; CP ONLINE,
> SIM ready, RadioState unknown, correct CS+PS wire1, auto mode11, rmnet0 DOWN.
> A single retry failed. Installed radiod equals build17; installed CP loader
> is still old d963219f…, while verified NV loader 530732cb… is in the Round43
> backup. Do not assume that mismatch alone proves the failure cause. Check
> current state and ordinary radio readiness, then fix verified production
> startup without reopening NV-offset/provisioning theories. Preserve checksum,
> TOC, authentication and recovery gates. Implement one persisted mobile-data
> policy, real disconnect/reconnect, NM DNS and synchronized Settings/QS/top
> bar. StopDataSession currently only disarms; GetSignalInfo is unavailable.
> Keep signal unknown rather than invent bars. Establish independent management
> before Wi-Fi-off/reboot acceptance. Complete native SMS app integration and
> authorized real message tests, then native calls/audio and authorized physical
> voice tests. No billable recipient is authorized by this prompt. No kernel,
> DT, EFS or firmware speculation. Commit incrementally, report actual exits and
> physical vs mock results, and withhold completion markers until all criteria
> are independently met.
