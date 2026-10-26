# NUXEL A72 / 21000 — 12-POST-REBOOT-REGRESSIONS

Status: no agent-initiated reboot this run (per policy). The only post-change check
performed is a launcher reload after the Maps deploy:
- Internet unchanged (T36 re-verified).
- Launcher: STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none; HOST_STATUS ok.
- Processes: phoc, nuxel-pwa-host, nuxel-navdock, nuxel-wl-fb running.
- USB Live Console reachable throughout.

3 owner-approved cold boots (T34/T47) remain, to confirm: automatic Wi-Fi reconnect,
lockscreen battery at first paint, single nav, and USB console recovery across reboots.
