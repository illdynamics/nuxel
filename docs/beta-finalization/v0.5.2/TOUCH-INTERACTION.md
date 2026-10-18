# Touch interaction

A34 proves sec_ts → evdev → libinput → Phoc → WebKit pointer/touch events and
two physical app activations. v0.5.2 preserves SYN_REPORT coordinate assembly
and removes stale surfaces that made later taps appear ineffective. The extended
Settings/Calendar/Quick Settings/Terminal sequence remains `NEEDS_OWNER_TEST`;
synthetic tests are not counted as physical evidence.
