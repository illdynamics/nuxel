# S5000AP Stage-06 — Continuation checkpoint (round 12, ~20:00 CET 2026-11-23)

## Verdict
`STAGE_06_NOT_YET_PASS — strict FSM landed; PDP activation rejection now *observed* via call_state=3; next action is PS/data registration query before activation`

## Git
Branch `cs/mob`, HEAD `abffa27d` (strict FSM + data-reg-state query + tests).

## This round's decisive correction
The FSM previously advanced on generic GEN echoes and claimed progress while the CP
was rejecting the bearer. It now decodes the REAL results:
- GEN echo result byte (payload[3]) → COMMAND_ACCEPTED only.
- `GPRS_CALL_STATUS` (main=13 sub=16) → bearer outcome (state 1/10/11 = connected).
- `GPRS_PDP_CONTEXT` (main=13 sub=4) → context list state.
- Added `fmt_tx_get_data_reg_state()` (9-byte NET_REGIST query, IpcTxNetGetDataRegState @0x335b00).

Live: `data_session_reject phase=DATA_CALL call_state=3` — the definitive rejection.

## Genuine remaining blocker (honest)
PDP activation is rejected (state=3) after the full byte-exact sequence. The CP is CS
registered (PLMN 20416 T-Mobile NL) but PS/data bearer is not granted. Next: read the
CP's own PS/data registration state via `GetDataRegState` before `SetPdpContext`, and
act on the NET_REGIST response.

## Safety
RADIO /dev/sda16 SHA256 unchanged `9ffa1426…66fc7`; binary `3abe998c…`; no protected
partition writes; Wi-Fi/USB/ZeroTier management preserved; rollback binary preserved.
