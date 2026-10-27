# PWNAGE 27000 — real Maps tile cache evidence

Pulled from the phone at 2026-10-27 16:19 (Europe/Amsterdam) from the WebKit
WebsiteDataManager IndexedDB database of the running Maps app:

`/root/.local/share/nuxel-pwa-host/databases/indexeddb/v1/http_127.0.0.1_8000/6D5DE9D5061F685A359B79DEE5376EBF27B70BED519B1F012B1F2CF0930B84F1/`

The IndexedDB object store is `tiles`; the records are:

| key | blob | bytes | SHA-256 | decoded |
|---|---|---|---|---|
| `7/65/42` | `1.blob` | 41567 | `c07fa9e13e75ba308befe3371cfdb3d7c6aab5c72717950fbb3d0cced6ba9de3` | PNG 256x256 |
| `7/66/43` | `2.blob` | 55519 | `1930541d24cc00b00da5b01c9d7704dc6f9824cd7efb7b17896f455f05a6a736` | PNG 256x256 |
| `7/65/43` | `3.blob` | 52561 | `871837316b5db83ba03181d1893047824e4a18836330ce3fe1d626bde4e17c8d` | PNG 256x256 |
| `7/66/42` | `4.blob` | 55094 | `141865d4031df06ba0f0858b9999991a2a723c3ce3875e8ab261bf6d37ee239b` | PNG 256x256 |

Verification against the live OSM service on 2026-10-27:

- `7/65/42` and `7/65/43` were byte-identical to `https://tile.openstreetmap.org/<key>.png`.
- `7/66/43` and `7/66/42` were valid 256x256 PNGs with a slightly newer OSM
  revision (55535/55088 bytes remote vs 55519/55094 cached).

This proves the real WebKit app requested, decoded and stored OSM tiles through
the configured source and the IndexedDB cache. It does not prove a visual
screenshot: the display was off and the device locked at capture time, so the
lockscreen was deliberately not bypassed.
