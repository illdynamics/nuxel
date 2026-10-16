# `configs/nuxel/gnss/` — GPS/GNSS and offline OpenStreetMap (area 25)

| File | Install to | Purpose |
|---|---|---|
| `gnss.json` | `/etc/nuxel/gnss/gnss.json` | Evidence sources, stage order, verdicts, owner fix procedure |
| `osm-tiles.json` | `/etc/nuxel/gnss/osm-tiles.json` | Shared offline-first map contract (tile layout, attribution, offline rules) |

## Honest boundaries

* The GNSS path is reported **stage by stage** (`device_node → module →
  firmware → stream → fix`) with the first failing stage named. A device node is
  not a fix; a fix cannot be observed **indoors**.
* **No coordinate is ever fabricated.** `monitor` prints only what it decodes
  from the real NMEA stream, and the offline map contract carries
  `no_fixed_coordinate_in_repo: true`.
* The offline map ships the **layout and attribution**, not map data. A cached
  area must render with the radio off; an online-only map must be labelled as
  such in the UI.
* No flashing surface of any kind.

## Commands

```sh
nuxel-gnss-diag.sh status [--json]    # per-stage evidence + first failing stage + verdict
nuxel-gnss-diag.sh firmware           # firmware candidate inventory
nuxel-gnss-diag.sh stream [secs]      # bounded NMEA sample (counts, no fabrication)
nuxel-gnss-diag.sh monitor [secs]     # bounded fix monitor; prints a decoded fix only if observed
nuxel-gnss-diag.sh map                # offline-map contract summary
nuxel-gnss-diag.sh selftest
```

Owner procedure: `docs/beta-finalization/manual-proof/13-gps.md`.
