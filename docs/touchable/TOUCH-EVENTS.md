# Physical touch evidence

Current boot: `2efd316a-3c15-441d-ae9d-54cd9b30aacd`, Linux 4.14.253 aarch64.
Normal boot with registered `sec_touchscreen` event2, INPUT_PROP_DIRECT and
MT X/Y/TRACKING_ID capabilities. Phoc and nuxel-touch-arm each hold event2.
The libinput path shim accepted sec_touchscreen. Only nuxel-wl-fb holds fb0.

First trial: `evidence/tap-before-20261018t2307/events.jsonl`, `timeline.jsonl`,
`before.json`, `after.json`, `receipt.json`. Actual EV_ABS contacts, not hardware
buttons, supply the 11 down/up pairs. Kernel timestamps and receive monotonic
timestamps are saved for correlation; start/end device clocks are recorded.

Capture does not grab input or change input routing. Diagnostic exit 4 means
the first trial did not observe DOM events. Its old verdict text
EVENTS_RECORDED_BUT_NOT_FORWARDED overstated the conclusion; it is retained as
original evidence. New recorder reports DOM_NOT_OBSERVED and records axis ranges.
Iframe coverage was absent in the installed launcher. No physical acceptance yet.

Direct per-event libinput and wl_touch protocol traces are not yet enabled;
acceptance state/process fds are not misrepresented as such traces.
