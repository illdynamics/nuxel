# TOUCHSCREEN IRQ EVIDENCE — A34

## Correlated physical contact

`/proc/interrupts`, line 431 (`sec_ts`):

| Time (UTC) | IRQ count |
|---|---|
| 2026-10-17T10:13Z | 42 |
| 2026-10-17T10:19Z | 92 |
| 2026-10-17T10:27Z | 142 |

`/sys/class/sec/tsp/all_touch_count` read `TTCN=12` at 10:19:39Z, after the
owner's taps. `nuxel-touch-arm` wrote 67 `TOUCH_POINT` records in the same
window (first at 10:13:01Z, last at 10:13:56Z).

## Correlation with the GUI

At exactly `2026-10-17T10:13:01Z` the launcher's diagnostic channel recorded:

```
NUXEL_INPUT EVT pointerdown x=155 y=235 tag=DIV id=app-icon app-category-productivity
NUXEL_INPUT EVT touchstart  x=155 y=235 ...
NUXEL_INPUT EVT touchmove   x=155 y=236 ...   (3 records)
NUXEL_INPUT EVT pointerup   x=155 y=236 ...
NUXEL_INPUT EVT app:launch  id=org.nuxel.Mail name=Mail
NUXEL_INPUT EVT touchend    x=155 y=236 ...
```

So the IRQ count, raw evdev contact, WebKit event and launcher handler all
belong to the same physical finger. This is not an IRQ-only claim.

## Later contacts

The `TOUCH_POINT` records at 10:13:07–09Z and 10:13:54–56Z occurred **after**
Mail had been opened. The launcher diagnostic is injected into the **top frame
only**, so contacts inside the Mail iframe are expected to be absent from
`/run/nuxel-home.state`. They are not evidence of IRQ loss.

## Verdict

T2 **PASS** on this boot. Interrupt delivery is not the blocker.
