# A55 Status-bar Layout

A54 fix preserved: single right-hand cluster (signal + Wi-Fi + battery + percent)
inside `.status-right`; grid `1fr auto`; fixed non-shrinking cells; on-device
collision detector `STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none`.
- Gate: **STATUS PASS_INTEGRATION** (measured cells, zero overlaps on-device).
- Startup/rotation visual overlap check remains owner-observable.
