# 🐧 NUXEL 17000 — OPERATION PENGUIN CONTROL REVIVAL: KICKSTART

Read `./NUXEL-A68-OPERATION-PENGUIN-17000-UBERPROMPT.md` **in full** and execute it against the **actual current Nuxel repository and live Samsung Galaxy S10+** using this Fedora laptop and proven USB Live Console.

I am the owner. This is a focused repair mission; implement and verify rather than only propose. Fix exactly:

1. **Short Back first navigates within the active app** (including browser history, Settings screens, keyboard dismissal). Only after the app reaches root should the next Back background it to true launcher Home. Do not reveal the launcher’s four desktop app icons on top of the still-open app.
2. **Penguin Home works globally**: one tap backgrounds whichever app is foreground and ACTUALLY raises/focuses the Nuxel Home desktop with icons and meters. SnekByte, browser fullscreen and native apps must obey. Global Tabs/app switcher continues to work.
3. **Real speaker audio**, working volume/mute and safe audible volume preview. Trace kernel ASoC/ALSA → UCM → PipeWire/WirePlumber → browser/apps. If hardware playback is unavailable, prove precise blocker; never fake sound.
4. **Real rotation**, correct all seven rotation policies, physical sensor data or honest hardware blockers, compositor/output framebuffer bridge and aligned touchscreen/viewport. Do not update kernel or flash.

Preserve working Internet/DNS/TLS/Nuxel Browser, launcher design, 16000 graphics performance improvements, lockscreen, USB recovery, latest SnekByte and all other working components.

First establish a safe backup/rollback and reproduce the failures, then make reversible targeted fixes, deploy serially, test on the **physical phone**, produce evidence-based results in `docs/a68-17000/`. Do not run alongside any other agent deploying to the phone; request approval for disruptive restarts or reboots.

**GO: BACK → HOME → SOUND → SPIN. 🐧🔊🔄**
