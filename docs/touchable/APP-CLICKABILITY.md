# App clickability

Proven source defect: `Launcher._onPointerDown` returned for every dock icon;
there was no dock click listener. **Settings is docked.** Grid icons had a
pointerup path, explaining why Calendar could open while Settings did nothing.
New behavioral tests reproduced this plus cancelled/wrong-target/secondary
pointer releases launching apps. The minimal launcher patch passes all eight.

Physical trial `tap-before-20261018t2307`: 11 actual sec_touchscreen down/up pairs,
87 SYN_REPORT, zero SYN_DROPPED, 90.002821 monotonic seconds. Top-document DOM
trace was empty. This is NOT proof of dropped input: the pre-trial log ended in
Calendar activation, the installed app.js lacked iframe observation, and a
post-trial compositor snapshot showed Calendar's New Event form. The installed
fullscreen iframe and top-right close glyph covered Home/status/navigation; the
glyph overlaps Calendar Save. The existing newer Home bar and iframe observation
were not deployed. Evidence: `evidence/after-trial1/` and the baseline hash drift.

Mac WebKit browser tests now perform five sequential Settings/Calendar/Notes
taps, confirm ACTIVE + changed pixels, hit the visible Home bar, and check all
frames/status/navigation surfaces are removed. Synthetic coverage only.

Native registry entries still need an installed-binary/activation audit. Their
existing launcher path only displays an unavailable toast. No native placeholder
is accepted as a successful app launch.
