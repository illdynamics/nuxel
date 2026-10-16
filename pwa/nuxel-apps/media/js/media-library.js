// Nuxel Media — library, queue and honest-route model (pure, no DOM).
//
// This module is the only place that decides what the player is allowed to say
// about playback.  Two rules, asserted by tests/test-media-library.js:
//
//   1. NO INVENTED LIBRARY.  Tracks come either from the bridge (`source: live`)
//      or from the bundled offline sample library (`source: sample`).  The UI
//      renders the source, so a VM smoke test can never look like a real scan of
//      the phone's storage.
//   2. NO INVENTED SOUND.  `audio.play()` resolving means the pipeline accepted
//      the stream — it is NOT evidence that anything was audible.  The route
//      model therefore reports `audible: 'unverified'` until an owner test has
//      been recorded, and says so in words.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MediaLibrary = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var SCHEMA_VERSION = 1;

  // Matroska/WebM and MP4 are the two container families the WebKitGTK/GStreamer
  // build in the VM and on the handset can decode; anything else is listed but
  // marked as needing a codec the image does not ship.
  var AUDIO_EXT = ['mp3', 'm4a', 'aac', 'ogg', 'opus', 'flac', 'wav', 'oga'];
  var VIDEO_EXT = ['mp4', 'm4v', 'webm', 'mkv', 'mov'];
  var UNSUPPORTED_NOTE = 'container/codec not shipped in this image — will show an honest decode error';

  function ext(name) {
    var m = /\.([A-Za-z0-9]+)$/.exec(String(name || ''));
    return m ? m[1].toLowerCase() : '';
  }

  function mediaKind(name) {
    var e = ext(name);
    if (VIDEO_EXT.indexOf(e) !== -1) return 'video';
    if (AUDIO_EXT.indexOf(e) !== -1) return 'audio';
    return 'unknown';
  }

  function decodeSupport(name, supported) {
    // `supported` is the list the caller probed with HTMLMediaElement.canPlayType.
    var e = ext(name);
    if (!e) return { supported: false, note: 'no file extension — cannot pick a demuxer' };
    if (supported && supported.length) {
      if (supported.indexOf(e) !== -1) return { supported: true, note: 'probed as playable by this build' };
      return { supported: false, note: UNSUPPORTED_NOTE };
    }
    return { supported: null, note: 'not probed — playback will report honestly if it fails' };
  }

  function formatTime(seconds) {
    if (seconds === null || seconds === undefined || isNaN(seconds) || seconds < 0) return '--:--';
    var s = Math.floor(seconds), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
    var mm = (h ? (m < 10 ? '0' + m : m) : m);
    var pad = function (n) { return n < 10 ? '0' + n : String(n); };
    return (h ? h + ':' + pad(m) : mm) + ':' + pad(ss);
  }

  function formatBytes(n) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    var u = ['B', 'KiB', 'MiB', 'GiB', 'TiB'], i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return (i ? n.toFixed(1) : String(n)) + ' ' + u[i];
  }

  function normaliseTrack(raw, source) {
    if (!raw) return null;
    var name = raw.name || raw.title || raw.path || '';
    if (!name) return null;
    var kb = mediaKind(name);
    return {
      id: raw.id || (String(raw.path || name).replace(/[^A-Za-z0-9]+/g, '-').toLowerCase()),
      name: name,
      title: raw.title || name.replace(/\.[A-Za-z0-9]+$/, '').replace(/_/g, ' '),
      artist: raw.artist || 'Unknown artist',
      album: raw.album || null,
      seconds: typeof raw.seconds === 'number' ? raw.seconds : null,
      bytes: typeof raw.bytes === 'number' ? raw.bytes : null,
      url: raw.url || raw.path || null,
      art: raw.art || null,
      kind: raw.kind || (kb === 'unknown' ? 'audio' : kb),
      container: ext(name),
      playable: raw.playable === undefined ? true : !!raw.playable,
      note: raw.note || null,
      source: source || raw.source || 'sample'
    };
  }

  function buildLibrary(items, source) {
    var out = [];
    (items || []).forEach(function (raw) {
      var t = normaliseTrack(raw, source);
      if (t) out.push(t);
    });
    out.sort(function (a, b) { return a.title.localeCompare(b.title); });
    return { schemaVersion: SCHEMA_VERSION, source: source || 'sample', tracks: out };
  }

  function search(lib, query) {
    var q = String(query || '').trim().toLowerCase();
    var tracks = (lib && lib.tracks) || [];
    if (!q) return tracks.slice();
    return tracks.filter(function (t) {
      return (t.title + ' ' + t.artist + ' ' + (t.album || '') + ' ' + t.name).toLowerCase().indexOf(q) !== -1;
    });
  }

  /* ---------- queue ---------- */

  function newQueue(tracks) {
    return { tracks: (tracks || []).slice(), index: 0, repeat: 'off', shuffle: false };
  }

  function current(q) {
    if (!q || !q.tracks.length) return null;
    return q.tracks[Math.min(Math.max(q.index, 0), q.tracks.length - 1)];
  }

  function nextIndex(q, order, forward) {
    if (!q.tracks.length) return 0;
    if (q.shuffle) {
      if (q.tracks.length === 1) return 0;
      var candidate = q.index;
      // Deterministic pseudo-shuffle: derive from `order` so a test can pin it.
      while (candidate === q.index) candidate = (candidate + (order % (q.tracks.length - 1)) + 1) % q.tracks.length;
      return candidate;
    }
    var i = q.index + (forward ? 1 : -1);
    if (i >= q.tracks.length) {
      if (q.repeat === 'all') return 0;
      return q.tracks.length - 1;
    }
    if (i < 0) return q.repeat === 'all' ? q.tracks.length - 1 : 0;
    return i;
  }

  function advance(q, order) {
    var wasLast = q.index >= q.tracks.length - 1;
    if (wasLast && q.repeat === 'off' && !q.shuffle) {
      return { q: q, ended: true, track: current(q) };
    }
    q.index = nextIndex(q, order === undefined ? 1 : order, true);
    return { q: q, ended: false, track: current(q) };
  }

  function setRepeat(q, mode) {
    if (['off', 'all', 'one'].indexOf(mode) === -1) throw new Error('repeat mode must be off|all|one');
    q.repeat = mode;
    return q;
  }

  /* ---------- honest route ---------- */

  // probe: what the bridge/host actually reported, or null when it did not answer.
  function describeRoute(probe) {
    if (!probe) {
      return {
        source: 'unavailable',
        audible: 'unverified',
        lines: [
          ['Output route', 'not reported — the Nuxel bridge did not answer'],
          ['Why', 'the player can decode audio without a mixer, but it cannot see the route'],
          ['What is still true', 'nothing about audibility is claimed']
        ],
        summary: 'route unknown (bridge did not answer) — audibility NOT claimed'
      };
    }
    var lines = [];
    lines.push(['ALSA card', probe.alsaCard ? probe.alsaCard + (probe.alsaCardId ? ' (card ' + probe.alsaCardId + ')' : '') : 'not reported']);
    lines.push(['Sound server', probe.server ? probe.server : 'not reported']);
    lines.push(['Default sink', probe.sink || 'not reported']);
    lines.push(['Mixer control', probe.mixerControl || 'not reported']);
    lines.push(['Headphones', probe.headphones === true ? 'detected' : probe.headphones === false ? 'not detected' : 'not reported']);
    var audible = probe.ownerVerifiedAudible === true ? 'verified' : 'unverified';
    lines.push(['Audible output', audible === 'verified'
      ? 'recorded by the owner in manual proof area 41'
      : 'NOT verified — no owner listening test has been recorded for this build']);
    return {
      source: probe.source || 'live',
      audible: audible,
      lines: lines,
      summary: 'route ' + (probe.server || 'unknown server') + ' -> ' + (probe.alsaCard || 'unknown card')
        + ' — audible output ' + (audible === 'verified' ? 'verified by owner test' : 'UNVERIFIED')
    };
  }

  // Volume is expressed in the mixer's own units.  The app never invents a
  // percentage it did not read: unreadable volumes stay null and the UI says so.
  function clampVolume(percent) {
    var n = Number(percent);
    if (isNaN(n)) return null;
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  function mixerToPercent(raw, max) {
    if (raw === null || raw === undefined || !max) return null;
    return clampVolume((Number(raw) / Number(max)) * 100);
  }

  return {
    SCHEMA_VERSION: SCHEMA_VERSION,
    AUDIO_EXT: AUDIO_EXT,
    VIDEO_EXT: VIDEO_EXT,
    mediaKind: mediaKind,
    decodeSupport: decodeSupport,
    formatTime: formatTime,
    formatBytes: formatBytes,
    normaliseTrack: normaliseTrack,
    buildLibrary: buildLibrary,
    search: search,
    newQueue: newQueue,
    current: current,
    advance: advance,
    nextIndex: nextIndex,
    setRepeat: setRepeat,
    describeRoute: describeRoute,
    clampVolume: clampVolume,
    mixerToPercent: mixerToPercent
  };
}));
