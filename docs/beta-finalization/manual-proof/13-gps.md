# Area 25 — GPS / GNSS and OpenStreetMap (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for config + diagnostic).
Owner action required? **Yes** — a position fix can only be observed **outdoors**
with a clear sky view.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820): the GNSS path is integrated in the SoC and normally needs vendor userspace
assistance. Which of device node / driver module / firmware / readable NMEA
stream are present is **enumerated per stage** by `nuxel-gnss-diag.sh`, and the
**first failing stage** is named. A device node is **not** a fix, and **no
coordinate is ever fabricated**.

---

## 1. Feature

* `configs/nuxel/gnss/gnss.json` — evidence sources, stage order
  (`device_node → module → firmware → stream → fix`), verdicts and the owner fix
  procedure (cold/warm start timeouts, accuracy threshold).
* `configs/nuxel/gnss/osm-tiles.json` — the **offline-first** OpenStreetMap
  contract shared with the Maps app: tile layout, attribution, offline rules,
  `no_fixed_coordinate_in_repo: true`.
* `tools/s10plus/a33/nuxel-gnss-diag.sh` — `status`, `firmware`, bounded `stream`,
  bounded `monitor`, `map`, `report`, `selftest`.

## 2. Why this matters

Location feeds the map, camera geotagging and time zone handling, and it is the
subsystem most likely to be *claimed* from a device node that never produced a
sentence. The mission forbids that: the diagnostic counts real NMEA sentences,
prints a position only when a real fix sentence arrived, and reports `NO_FIX`
(an honest, expected indoor result) rather than an invented coordinate.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode.
2. **A clear view of the sky** — go outdoors, or to a large window; a metal or
   glass roof makes a fix impossible and the result meaningless.
3. Console/SSH or the on-device terminal (the monitor must keep running while you
   hold the phone).
4. Optional but recommended: an area of offline OSM tiles so the coordinate can be
   cross-checked without the network
   (`nuxel-gnss-diag.sh map` prints where they are searched for).
5. Snapshot first:

   ```sh
   nuxel-gnss-diag.sh status          # per-stage evidence + first failing stage + verdict
   nuxel-gnss-diag.sh status --json
   nuxel-gnss-diag.sh firmware        # firmware candidate inventory
   nuxel-gnss-diag.sh map             # offline-map contract + whether tiles exist
   ```

   * `BLOCKED_KERNEL` (stage `device_node`/`stream`) → no receiver path on this
     kernel: offline driver work, not a retry loop.
   * `BLOCKED_FIRMWARE` → deploy the blob into `/lib/firmware/gnss`
     (repository-only; **never** a partition write).
   * `BLOCKED_EXTERNAL_RESOURCE` → kernel GNSS up but no consumer: run
     `monitor` (which reads the node directly) before giving up.

## 4. Exact action

1. **Sample the stream (indoors is fine):** `nuxel-gnss-diag.sh stream 10` → it
   prints **counts** of NMEA sentence types it actually saw. Zero counts mean no
   stream, not a fix problem.
2. **Outdoors, cold start:** stand outside, hold the phone with a clear sky view,
   and run `nuxel-gnss-diag.sh monitor 300` (or 60 s if the receiver is warm from
   a recent fix). It prints a decoded `$..GGA` position **only** when a real fix
   sentence with a non-empty latitude/longitude and fix quality ≥ 1 appears.
3. **Read the result:**
   * a decoded sentence → record the coordinate, the reported accuracy and the
     time-to-first-fix;
   * `NO_FIX` → record how long you waited and where you stood. **Indoors it is
     always NO_FIX and that is not a repository failure.**
4. **Cross-check on the offline map:** open the Nuxel Maps app with the network
   **off** and compare the coordinate with the cached area. The map must render
   from cached tiles; a blank grid without an "offline" message is a map bug, not
   a GNSS success.
5. **Accuracy check:** the fix passes when the reported accuracy is ≤ 50 m and the
   coordinate agrees with the map within that accuracy (`max_accuracy_m_for_pass`
   in `gnss.json`).
6. Save the evidence: `nuxel-gnss-diag.sh report` plus the monitor output and the
   dmesg lines from §7.

## 5. Expected result

* `status` prints each stage's real evidence and the first failing stage;
  `stream` prints non-zero sentence counts for at least one NMEA type.
* `monitor 300` outdoors eventually prints a decoded position sentence with a
  non-empty latitude/longitude; the coordinate matches the offline map within the
  reported accuracy (≤ 50 m).
* Indoors, `monitor` prints `NO_FIX` and no coordinate — the **honest** result.
* The offline map renders the cached area with the radio off.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `device_node : absent` → `BLOCKED_KERNEL` | No GNSS node/module: offline driver work. Never fabricate a coordinate. |
| `module : none-loaded` with a node present → `PARTIAL` | A node without a bound driver; capture `ls -l /dev/gnss*` and `dmesg | grep -i gnss`. |
| `firmware : missing` → `BLOCKED_FIRMWARE` | Deploy the blob into `/lib/firmware/gnss` (repository-only); never a flash. |
| `stream` shows zero sentences | No data path. Report the node and `cat` return, then stop — a driver/firmware problem. |
| `NO_FIX` outdoors after 300 s | Cold start can be slow, but **after three same-mode attempts change strategy** (antenna position, assisted-data availability, another location) — never loop. |
| Fix quality 0 / empty lat/lon in a sentence | The receiver has no fix: report `NO_FIX`, not PASS. |
| Coordinates jump wildly between reads | Poor sky view or a decode bug: record the raw sentences and report FAIL. |
| Map is blank offline | Offline-first regression in the Maps app: report the tile search paths from `nuxel-gnss-diag.sh map`. |

## 7. Diagnostic command / log path

* `nuxel-gnss-diag.sh status | firmware | stream [secs] | monitor [secs] | map | report`
  (`tools/s10plus/a33/nuxel-gnss-diag.sh`)
* Evidence log: `/var/log/nuxel/gnss-diag.log`
* Kernel side: `dmesg | grep -i -E 'gnss|gps|nmea|s5p_gnss'`;
  `ls -l /dev/gnss* 2>/dev/null`; `cat /proc/modules | grep -i gnss`
* Stream: `cat /dev/gnss0 | head` (raw sentences are the only real evidence)
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py`
  and `nuxel-gnss-diag.sh selftest` (4 fixtures: absent / no-firmware /
  node-without-module / stream-ready).

## 8. PASS / FAIL

* **PASS** — steps 1–6 all hold: a real NMEA stream, a decoded position with fix
  quality ≥ 1 and accuracy ≤ 50 m, agreeing with the offline map, with the
  time-to-first-fix recorded.
* **FAIL** — any of: a missing stage (`BLOCKED_*`), zero sentences, `NO_FIX`
  outdoors after three attempts at different locations, or a coordinate that does
  not agree with the map. Record the **exact verdict string, the first failing
  stage, the raw sentence and the times** — never a coordinate you did not read.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-gnss-diag.sh selftest` → 4/4 fixtures PASS
  (`fixtures/gnss-absent`, `gnss-nofw`, `gnss-partial`, `gnss-ready`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py` → all checks
  PASS (stage/verdict logic, no fabricated coordinate in `stream`/`monitor`,
  bounding, offline-map contract, faked-root safety, fragment completeness).
* A real fix: **not claimed** — every `status --json` emits
  `"fix_verified": false`, and the capability manifest keeps GNSS at
  `NEEDS_OWNER_TEST` with the default derived from the real stages found.
