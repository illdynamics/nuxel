# Superseded analyzer records — kept OUT of the capture bundle on purpose

These are the `nuxel-touch-trace.py --analyze` records that the bundle
`docs/beta-finalization/live/evidence/touch-20261016T193756+0200-cycl001-p0probe-live-run/`
used to carry, next to the fresh ones. They are kept here for audit and deliberately
**not** inside the bundle.

| File | Provenance (measured) | What it says |
|---|---|---|
| `verdict.pre-rename.txt` | byte-identical to the file git tracked as `…-p0probe-live-run/verdict.pre-rename.txt` (blob `b7c7e86a…`); it is the analyzer's stdout from the run taken **while the capture directory was still named `…-p0probe`**. This was the bundle's `verdict.txt` in the revision the inspeQtor reviewed. | `FIRST_FAIL_LAYER=1 NAME=driver STATE=blocked` (charger/LPM boot). Every `EVIDENCE=` / `JSON_OUT=` path inside it names `…-p0probe`, a directory that no longer exists — the paths do **not** resolve. |
| `analysis.pre-rename.json` | byte-identical to the file git tracked as `…-p0probe-live-run/analysis.pre-rename.json` (blob `6229c5c7…`); the paired `--json-out` document. | the same honest all-`blocked` verdict (`FIRST_FAIL_LAYER=1`); its `root` is the stored `…-p0probe-live-run` directory |

The bundle's own `verdict.txt` and `analysis.json` were therefore **re-generated** with
`--analyze` against the stored directory. Every `EVIDENCE=` / `JSON_OUT=` path in them
now names a file that exists, and the finding is unchanged
(`FIRST_FAIL_LAYER=1 NAME=driver STATE=blocked`, charger/LPM boot).

## Why these may not sit inside the bundle

`analysis.json` (the analyzer's own output) is excluded from evidence **by file name**:
that JSON carries no structural marker of its own (`looks_like_own_verdict()` detects
`LAYER=1 NAME=…` text or the `"tool": "nuxel-touch-trace"` tag, and the `--json-out`
document has neither). A copy of it under any *other* name is therefore not recognised
as a conclusion, and the analyzer will grade its own previous sentence as device
evidence — the layer-6 self-grading bug of `PIPELINE-TRACE.md` §6c.

Measured, this cycle: with a copy named `analysis.pre-rename.json` inside the bundle, a
re-run produced

```
LAYER=6 NAME=wayland STATE=ok EVIDENCE=analysis.pre-rename.json DETAIL=wl_touch present in the compositor protocol capture
```

— a layer-6 *pass* manufactured out of the word `wl_touch` inside the tool's own old
JSON, on a boot where no touch device exists. `tests/test-touch-trace.py` grades exactly
this capture and asserts `"wl_touch present" not in out`, so it fails in that
arrangement and passes with these copies outside the bundle (verified both ways).
