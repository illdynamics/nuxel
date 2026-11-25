# Nuxel native LTE internet sharing

Implementation checkpoint `39892d45` (2026-11-25). **USB external-client internet passed. Wi-Fi hotspot external-client internet remains unverified.** This is not full production acceptance.

| Responsibility | Owner |
|---|---|
| Cellular preference, SIM/registration, CID1, retry/release | Native Radio1 / nuxel-radiod |
| Cellular IP/routes | Journaled native cellular link helper; NM generic profile cannot activate actual PPP-type rmnet0 |
| Host DNS | systemd-resolved, carrier DNS scoped to rmnet0; NM retains Wi-Fi DNS |
| Native IPv4 compatibility | TAYGA CLAT, carrier-validated DNS64/NAT64; no native carrier IPv4 assignment |
| Wi-Fi station | NetworkManager on wlan0 |
| AP | nuxel-hotspot service, hostapd/nl80211 on wlan1 |
| USB | nuxel-usb-tether service on existing usb0; gadget composition and management address unchanged |
| Sharing DHCP/DNS/policy routing | shared sharing_link module, one scoped dnsmasq per downstream |
| UI | Existing authenticated bridge, shared provider state, Settings and Quick Settings |

## Routing and isolation

USB uses existing 10.100.10.1/24, DHCP .20–.60, policy table108/iif priority30508. The owner management host remains static .2. Hotspot uses 10.42.0.1/24, DHCP .20–.60, table107/priority30507. Both use actual native IPv4 upstream if available, otherwise the working nuxclat translator. Every downstream table retains an unreachable default when LTE is lost, preventing fallback into handset Wi-Fi, USB upstream or VPN exits. Carrier DNS forwarding is explicitly bound to rmnet0.

Private nft input/forward isolation works alongside narrow tagged allowances in the existing app firewall. The installed kernel cannot create nft NAT, so private legacy iptables NAT chains supply masquerading. No unrelated rules are flushed. AP clients cannot reach privileged handset services; USB SSH2022 is restricted to management source .2 plus existing key authentication. Client IPv6 is not forwarded: **downstream IPv6 is unsupported by this implementation**, although the upstream is native IPv6. IPv4 sharing works through verified carrier NAT64, not IPv4 NAT alone.

The VPN kill switch is respected: activation is refused while its table is present. No control suggests disabling it. Sharing sysctl ownership is journaled and locked: stopping one share leaves the other's requirements; stopping the last restores original forwarding/rp_filter. Cleanup removes owned DHCP, policy routes, addresses and NAT rules. An intentional USB forwarding-deny table remains when tethering is off, because pre-existing broad USB forwarding permission would otherwise leak traffic.

## AP capability, credentials and state

The physical driver advertises AP and interface combinations; wlan0 station plus wlan1 AP ran concurrently. The worker waits for NM/wpa_supplicant to relinquish wlan1, then starts hostapd with WPA2-PSK/CCMP, configured NL regulatory domain and a supported fixed channel. 2.4GHz channel6 was physically tested. 5GHz channel36 is configurable but not accepted with a client; WPA3 is not implemented. Country/channel behavior outside this configured regulatory domain is not accepted.

Default password is generated with secrets.token_urlsafe(18), persisted root0600 at `/var/lib/nuxel/hotspot/config.json`; SSID/password inputs reject control characters. Credentials are absent from Git, status polling and evidence. An explicit authenticated Settings action can reveal the saved password; the deployed control still needs its final physical UI verification. Sharing activation is never persisted across boot. Previous Wi-Fi radio state is restored after AP shutdown.

State distinguishes startup/shutdown, configured service, missing upstream and failure. `internet_verified` remains false until an actual external test; a running AP is not internet proof. Client count uses actual `iw station dump` and stays unavailable on read failure. Zero clients was observed; changes with a real client remain unverified. DHCP or AP process failure must not appear as successful sharing.

## Physical evidence and limitations

The laptop performed actual USB DHCP DISCOVER/OFFER/REQUEST/ACK, then DNS through Nuxel and TLS-verified HTTPS through LTE. Interface en12 and a single scoped test-destination route excluded its own Wi-Fi without changing its global networking. Cellular/NAT counters increased. Tests after Settings start, USB reconnect and LTE upstream return also passed. See [acceptance](NUXEL-LTE-PRODUCTION-ACCEPTANCE.md) and [receipts](evidence/internet-final-20261125/).

Settings and QS started/stopped sharing; real hostapd AP readiness was observed. AP and USB workers ran together and USB internet worked, but no external Wi-Fi client authenticated or obtained internet. No simultaneous two-client pass is claimed. A transient USB SSH stall during combined-sharing UI work remains unexplained; independent ZeroTier remained reachable and stopping sharing restored USB. Resolve this before claiming production reliability.

## Installation and recovery

On the handset, run the staged repository's `services/nuxel-network/install-sharing.sh`; it checks native dependencies, saves replaced userspace files and creates a rollback script. Restart nuxel-http-bridge explicitly afterward. The installer disables sharing boot activation and never edits the gadget, kernel or protected partitions. Latest successful backup is `/var/lib/nuxel/sharing-install.p2p3JM/rollback.sh`. A missing staged CSS file triggered rollback during deployment; after supplying it, installation succeeded and source/installed hashes match.

The native data installer owns the carrier compatibility prerequisites. Do not apply an unrelated modem/firmware reset to repair sharing. Final acceptance leaves LTE ON, sharing OFF, USB management and ZeroTier present, and removes the laptop's scoped test route. Future work must finish full NM integration and the missing physical gates without replacing accurate state with optimistic success.
