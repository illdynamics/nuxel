# Wi-Fi and browser evidence

Sanitized live evidence:

- `wlan0` state: connected; access point on 5 GHz with a saved profile.
- IPv4 default route: present; IPv6 data also present.
- DNS lookup for `google.nl`: pass.
- real remote `https://www.google.nl`: HTTP 200, TLS verification result 0.
- NetworkManager boot journal shows scan, secrets, association, four-way handshake, DHCP and activation.
- Firefox and the native Nuxel WebKitGTK browser are installed; Nuxel Browser is the viable native path under the current compositor.

Secrets, SSID and addresses are intentionally omitted. Status is `FUNCTIONAL_WITH_LIMITATION`: browser UI typing/back/result navigation, wrong-password UI, five disconnect/reconnect trials and cold-boot persistence still need owner interaction after touch returns.
