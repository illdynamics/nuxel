# NUXEL A72 / 21000 — 09-MAPS-VLC-MUSIC-APPS

## Maps (A69-05) — improved this run (deployed + hash-verified)
- One-tap "Use OpenStreetMap standard tiles (go online)" now sets the template AND
  enables downloads, then fetches ONLY the current viewport (no crawl/prefetch).
- Added Nominatim place search (Enter key or Search button): single query per
  action, identifiable UA, © OpenStreetMap contributors, results become pins,
  nothing auto-opens, network position never shown as GPS.
- Auto-fetch visible tiles after pan/zoom (350 ms debounce) when downloads are on.
- SW cache bumped `nuxel-maps-v2` → `nuxel-maps-v3`.
- Verified from the phone: OSM tile `HTTP/2 200` + `access-control-allow-origin:*`;
  Nominatim returns valid JSON (Amsterdam lat/lon + ODbL licence).
- Deployed: index.html 8f356eb7…, maps.js 0f7e2189…, sw.js 99ee8e59… (device==repo).

## VLC + separate music player (A69-09) — gated on dnf5
- Fedora 43 aarch64 has vlc `3.0.21-26` and mpv `0.40.0-3` (verified in GA metadata).
- Install only after the approved dnf5 bootstrap; then register .desktop/MIME and
  test real local MP3/WAV playback with an honest audio-route caveat.
