# A52 Photos & Media Storage

## Canonical locations

| Media | Path |
|---|---|
| Photos | `/var/lib/nuxel/media/pictures/Nuxel Camera/` |
| Videos | `/var/lib/nuxel/media/videos/Nuxel Camera/` |
| Index cache | `/var/lib/nuxel/media/media-index.json` |

`NUXEL_MEDIA_DIR` overrides the root (default `/var/lib/nuxel/media`), so the
host test-suite and the device share one layout. The bridge service user owns
the files (`0640`), which are outside the browser's ephemeral storage — media
survives app/browser restart and reboot, and is never silently lost to a
`localStorage` quota.

## Storage guarantees

- **Atomic write:** temp file in the same directory → `fsync` → `rename`; a
  crash/out-of-space can never leave a half file indexed as finished.
- **Collision-safe naming:** `nuxel-<ISO-UTC>-<sha256:10>.jpg` (+ numeric suffix
  on collision); canonical id = filename.
- **Extension honesty:** photos → `.jpg`/`.png`/`.webp` by mime; videos →
  `.webm`/`.mp4` by mime (never `.mp4` on non-MP4 bytes).
- **Bounded payloads:** photo ≤ 16 MiB, video ≤ 512 MiB; `camera.open` inline
  return ≤ 32 MiB (larger video shows metadata + path, not a fabricated player).
- **Rebuildable index:** `media-index.json` is a cache; `list()` reconciles by
  scanning the directories, so the index is rebuilt after crash/partial write.
- **Delete removes the real file + index entry** (never an index-only delete).
- **No base64 in list:** the list verb returns metadata only; pixel data is
  lazy-loaded per visible item.

## Photos app behaviour (file-backed)

- Grid (newest first), lazy thumbnail load via `IntersectionObserver` +
  `camera.open`; search/filter; album-by-date; fullscreen viewer with swipe
  prev/next; real metadata pane (dimensions, type, taken, size, duration, camera,
  path); video playback via `<video>`; delete with confirmation; index export.
- Honest empty / permission-denied / offline / corrupt states.

## Migration from historical `localStorage`

The historical `nuxel-camera-photos` and `nuxel-photos-index` localStorage keys
are **no longer authoritative**. A migration step (to be run once on a
maintenance window, owner-approved) will parse parseable owner-created entries,
write them as real files through `media_store.save`, and keep the original
localStorage as a backup — media is **never deleted** during migration.
