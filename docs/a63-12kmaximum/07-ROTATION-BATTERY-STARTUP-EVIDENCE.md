# Rotation, battery and startup evidence

Battery kernel readings were `100` / `Full`; the live phone status API returned the same truth. Home now reads `battery-capacity` and `battery-status` directly from the native host at DOM startup, treats only exact `Charging` as charging, emits `BATTERY_HOST_READY`, and uses unknown—not fake 100%—during bridge failure.

All seven policy names are configured: portrait, reverse portrait, landscape, reverse landscape, auto, auto portrait and auto landscape. The current IIO sensor lacks a usable scale and no compositor transform has been physically proven, so manual/auto rotation and touch mapping remain `BLOCKED`/`NEEDS_OWNER_TEST`.

Startup status-bar diagnostics reported no overlap before this change. New battery timing and all orientation geometries need screenshots/physical observation after normal boot.
