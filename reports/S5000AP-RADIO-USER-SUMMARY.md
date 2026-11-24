# Nuxel S5000AP radio — user-facing status (honest)

Your Galaxy S10+ now has **real mobile data** over the native Shannon modem:
the modem boots, the SIM is ready, the device registers on KPN LTE, and it gets
a working IPv6 data connection with working DNS and HTTPS — verified with
Wi-Fi turned off so the traffic genuinely went over cellular.

What still does **not** work yet (and is reported honestly):

| Feature | Status |
|---|---|
| Mobile data (LTE) | ✅ Working (verified live) |
| SMS send/receive | ⚠️ Built and host-tested, **not yet tested on the phone** (needs your ok + two test numbers) |
| Phone calls | ⚠️ Call control built and host-tested, but **call audio is not wired yet** and no real call has been made |
| VoLTE / IMS / Wi-Fi calling | ❌ Blocked — needs Samsung's proprietary IMS software and KPN provisioning |

The Phone, Contacts and Messages apps are wired to an honest data layer: if the
modem cannot do something, the app says so instead of pretending. Nothing fakes
a signal bar or an enabled button.

**To move SMS/calls forward I need from you:**
1. Your OK to run a consented SMS test, plus two non-premium test phone numbers.
2. Your OK to run a consented voice test, plus one non-emergency number.

Until then, SMS and voice stay marked "built but not hardware-tested", and
VoLTE stays "blocked" — that is the truthful state.
