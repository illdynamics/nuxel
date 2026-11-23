# S5000AP Stage-06 — SIM / Registration / LTE data / MM / NM

Truthful radio state machine + ModemManager/NetworkManager integration
determination for the physical S5000AP (Shannon 5185) on the Nuxel S10+.

Layout:
  src/radio_fsm.{h,c}   pure truthful radio/UI state machine (9 required states)
  tests/test_radio_fsm.c offline gate-ladder fixtures (NOT physical results)
  docs/MM_NM_INTEGRATION.md exact MM 1.24.2/NM 1.54.3 ABI + honest determination
  build.sh              reproducible build + unit/ASan tests

Truth contract: state advances ONLY on authenticated kernel/vendor-sourced
signals; it never fabricates SIM/registration/data. See the Stage-06 report in
reports/S5000AP-06-LTE-REAL-LIVE.md for per-gate PASS/BLOCKED and blockers.

SPDX-License-Identifier: GPL-2.0-only (code), CC-BY-SA-4.0 (docs)
