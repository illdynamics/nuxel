# Thermal / Idle Report — PWNAGE-85000

## Conditions

- Device: S10+ Exynos 9820, Fedora 43, kernel 4.14.253.
- Battery 11%, discharging; no charger attached.
- Wi-Fi SSH active; screen off at final sample (`bl_power=4`, brightness 0).
- No governor/thermal/IO tuning applied; `nuxel-perf-tune.service` inactive.

## Readings

| Item | Value |
|---|---:|
| thermal_zone0 | 43.0 °C |
| thermal_zone1 | 41.0 °C |
| thermal_zone2 | 40.0 °C |
| session range | 26.6–43.0 °C |
| memory | 1.3 GiB used / 5.9 GiB available |
| swap | 0 B |
| screen-off WebKit | ~10% |
| screen-off pwa-host | ~2.7% |
| screen-off bridge API | 0.0% (cached indicator projection) |
| screen-off phoc | ~1.3% |
| screen-off wl-fb | ~0.1% |
| screen-off repaint writes | 0 / 6 s |

## Interpretation

The repaint storm was the dominant screen-off heat source (WebKit compositor 74.7% + host ~20%). After the launcher re-entry guard it is ~14% total. The remaining 1 Hz lockscreen-indicator poll is documented; it is a small but nonzero residual. No thermal throttling, governor or watchdog setting was changed. A longer owner soak is still required for a battery-trend claim; this report does not claim one.
