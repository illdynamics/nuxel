# 🐧🌐 NUXEL A51 — OPERATION WI-FI TO WEB (LAUNCHER)

Read **`./NUXEL-A51-WIFI-FLATPAK-LADYBIRD-UBERPROMPT.md`** from the current Nuxel repository root **in full**, then execute its phases sequentially on the actual current repository and connected Samsung Galaxy S10+ running Nuxel.

**First fix the exact NetworkManager error:** `Device.SpecificObjectNotFound: the access point /new was not in the scan list`. The historical `services/nuxel-bridge/src/bridge.py` hardcodes `'/new'` in `AddAndActivateConnection` even though Wi-Fi scanning already obtains real AP D-Bus paths. Verify live code, replace the incorrect contract with secure/stale-safe selected-AP activation, save persistent NetworkManager connection profiles and prove automatic reconnection after owner-approved reboot.

**Then finish actual usable native browsing:** verify HTTPS and DNS, native GTK/Qt/Wayland app launching under Phoc, Flatpak installation/sandbox/portal support on the device's old kernel, and build/install/run genuine Linux AArch64 **Ladybird** as preferred browser if feasible. Ladybird is pre-alpha and its ARM64/Qt requirements must be verified; if blocked, ensure a true WebKitGTK-based native browser is fully functional and integrated into Nuxel Home as a tested fallback. Do not mistake a PWA, launcher icon or Qt build failure for Ladybird completion.

Keep existing working Home, native OSK, Wi-Fi scanning, lockscreen, USB console, A50 performance tuning and splash unchanged. No flashing, kernel replacement, insecure sandbox bypass, or password leaks. Deploy in reversible steps; report verified results and exact remaining blockers, not assumed success.

**BEGIN NOW WITH READ-ONLY LIVE DEVICE PREFLIGHT AND WIFI ROOT-CAUSE TRACE.** 🐧🌐🔥
