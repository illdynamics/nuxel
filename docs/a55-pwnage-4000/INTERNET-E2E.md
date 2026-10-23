# A55 Internet End-to-End (Wi-Fi → DNS → TLS → real browser)

Measured live on the S10+ this cycle:

1. `wlan0` connected (NetworkManager state `connected`), IPv4 `192.168.178.167/24`
   + global IPv6.
2. Default route present via gateway `192.168.178.1` (dhcp, metric 600).
3. DNS: `getent ahosts www.google.nl` resolves.
4. TLS: `curl https://www.gstatic.com/generate_204` → 204;
   `curl -L https://www.google.nl` → 200 (CA bundle validated, clock correct).
5. Nuxel browser (native WebKitGTK): loaded `https://www.google.nl/` to
   `load-changed=FINISHED`, spawned a real WebKitWebProcess, and rendered a
   94.4%-white composited frame (Google page) captured on-device.

## Reboot persistence
NOT_TESTED this cycle (cold-boot requires owner approval). Hot `nuxel-wayland`
restart kept the console alive and all units active.
