# A59 — Network and HTTPS (Phase 1)

## Status: `PASS_PHYSICAL` (already healthy; re-verified this session)

- Device: Samsung Galaxy S10+ `beyond2lte`, Fedora 43 aarch64, kernel 4.14.253.
- NetworkManager: `wlan0` ACTIVE, SSID `Ziggo5501109` (secret redacted from all
  commands/logs/commits), IPv4 `192.168.178.167/24`, default route via
  `192.168.178.1`, DNS `62.179.104.196` / `213.46.228.196` (+IPv6).
- On-device validated TLS: `https://www.google.nl` → HTTP/2 200,
  `https://www.eff.org` → HTTP/2 200, `ssl_verify_result=0` (certificate
  verified; no bypass). Clock correct (Europe/Amsterdam CEST).
- Root cause of any browser-only failure is therefore NOT L3/L4/network.

## USB console recovery path (guaranteed before any service restart)
- CDC-ACM live console `/dev/cu.usbmodem201` (115200 8N1) remained reachable
  across every userspace service restart (http-bridge, nuxel-wayland).
- A LAN HTTP PUT channel (Mac `192.168.178.251` → device `192.168.178.167:8092`)
  was used for verified byte-exact file deployment (each file sha256-verified
  on the target), avoiding the kmsg-flooded serial console for bulk transfer.

## Evidence artifacts
- Sanitised network state captured in this session's console logs.
- No Wi-Fi password, PSK, token or account credential appears in any command,
  log, screenshot or commit.
