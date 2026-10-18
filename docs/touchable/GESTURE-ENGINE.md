# Gesture engine

Pending basic physical clickability repair/retest. Existing launcher has
independent pointer handling and passive touchstart/touchend horizontal detection;
status-bar.js recognizes a down pull only from the status bar. No global vertical
workspace navigation or shared app gesture layer exists yet. Native Terminal is
an independent WebKit/GTK surface; launcher-only DOM listeners cannot reach it.

Do not implement gestures over the unresolved icon activation defect. The next
phase must unify ownership/cancel/axis/deduplication and preserve app scrolling
and multitouch. Source and physical tests must remain distinct.
