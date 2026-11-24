# DeepSeek Stage 06 handover

Initial recovery checkpoint: 2026-11-24. Consolidation in progress.

Baseline branch `cs/mob-round35-stage06`, HEAD `24e617639a9e91236b1d75d72c9bfaf26703e2f1`.
Astra implementation is committed, including DeepSeek reconciliation. Owner changes in
`CHANGELOG.md` and untracked `astra-kurwa.md` are preserved. Local private recovery
checkpoint: `/tmp/nuxel-lte-consolidation/`; prior artifacts: `/tmp/nuxel-round43/`.

Historical LTE/IPv6 and cellular-only HTTPS success is preserved as evidence;
this pass has not yet verified reboot, UI, or preference persistence.
No modem restart or protected NV modification performed.

## Live reconciliation checkpoint (23:07–23:10 CET)

The historical working bearer is **not active at entry**. CP ONLINE; native SIM
READY; packet registration NOT_REGISTERED; CS registration DENIED; rmnet0 DOWN
with zero packets. The phone had already rebooted before this execution.
Installed/running radiod matches build17 (`6893af43…`); installed CP loader
is still old `d963219f…`, whereas Astra's NV-capable verified loader is
`530732cb…` in the Round43 backup. This is an installation mismatch; the cause
of the current registration failure has not been experimentally established.

Service-domain wire 1 is correct CS+PS. Wire 2 is CS-only. An early commentary
misstatement in this pass was corrected by inspecting fmt_tx_set_service_domain.
No encoding change is needed. Mode readback 11 is LTE/WCDMA/GSM auto.

Private device backup `/var/lib/nuxel/lte-consolidation-20261124/` contains
binaries, checksums and configuration archive; all five checksum checks passed.
Host copies are in `/tmp/nuxel-lte-consolidation/`. The archive contains private
configuration and must not be committed. The original Round43 EFS backup remains.

One bounded native StartDataSession attempt is in progress. No CP reset,
service restart, Wi-Fi disable, reboot, call or SMS transmission was performed.
ZeroTier SSH works; direct Wi-Fi SSH is refused; USB carrier is 0. No independent
management route is verified. No mobile-data persisted policy exists in radiod;
StopDataSession only disarms the FSM. Full source/evidence audit follows.
