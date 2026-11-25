# Physical native internet evidence — 2026-11-25

Runtime checkpoint: `39892d45`; installed source identities in deployed-identities.json. These are actual handset/client results, not host simulation.

- final-acceptance.json: final registered LTE, cellular-only IPv6 and translated IPv4 HTTPS, DNS, routes, timestamps and traffic counters.
- enabled-reboot.json / disabled-reboot.txt: separate normal-boot acceptance cases. The disabled receipt is an early boot snapshot, not an assertion of eventual SIM readiness while disabled.
- qs-off-complete.txt / settings-off.txt / after-ui-on.json: real widget actions, native lifecycle and restored internet. ui-off-state.txt includes an intermediate connecting state, not a disconnected final state.
- usb-final-dhcp.json: actual laptop DHCP exchange without changing its system configuration. usb-settings-start.json: external client DNS/HTTPS after Settings activation. usb-reconnected.json and usb-upstream-restored-complete.json cover return paths.
- sharing-final-start.txt / upstream-off.txt / sharing-final-cleanup.txt: concurrent services, real upstream loss and scoped cleanup. final-cleanup.txt is the last cleanup state. Remaining USB forwarding denial is intentional.
- hotspot-final-code.txt: actual AP plus DHCP running with zero clients, followed by cleanup. This is NOT external hotspot internet acceptance.
- settings-connected.png / qs-topbar-fixed.png: real handset UI, public addresses masked. Toasts/status describe unverified sharing honestly. Browser screenshots are actual native applications rendering normal HTTPS, NOT speed-test results.
- zerotier-cellular.txt: independent management during cellular-only routing.

The screenshot settings-mobile.png from the private scratch directory was a lock screen and is deliberately not included as an acceptance image. No credentials, subscriber identities, public carrier addresses or generated executables are committed. Public test endpoint addresses are also redacted in text receipts. Interface names and private management addresses remain for reproducibility.

The latest saved-password control needs physical verification. No external Wi-Fi client connected; no speed benchmark ran. The transient concurrent-sharing USB SSH stall remains an open reliability issue. See ../../NUXEL-LTE-PRODUCTION-ACCEPTANCE.md for the full limits.
