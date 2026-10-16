// Nuxel Downloader — the queue engine (pure, no DOM, no network of its own).
//
// DESIGN RULES (all asserted by tests/test-download-queue.js):
//   1. LEGAL GATE.  Nothing can be queued until the operator has accepted the
//      legal-use notice.  The acceptance is explicit and versioned; a bumped
//      notice version invalidates an old acceptance.
//   2. NO THIRD-PARTY SERVICE.  Telemetry/analytics/storefront hosts are refused
//      outright, so this tool cannot become a covert client for somebody's
//      cloud.  The refusal list is data, and a test proves it is enforced.
//   3. OFFLINE-FIRST.  The queue is a persistent list; it does work when a
//      network happens to exist and reports honestly when it does not.  A
//      transfer is only ever `done` when a digest was verified — or when the
//      source published none, in which case the item is marked
//      `verified: false` and the UI says so.
//   4. THREE FAILURES, THEN A DIFFERENT STRATEGY.  Same-mode repeats are the
//      documented failure mode; after three identical failures the engine
//      changes the retry mode and says which mode it moved to.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DownloadQueue = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var SCHEMA_VERSION = 1;
  var NOTICE_VERSION = 2;
  var NOTICE_TEXT = [
    'I will use this downloader only for material I have the right to download:',
    'material I own, material published under a licence that permits it, or',
    'material whose publisher has authorised the download.',
    'I understand nothing here bypasses DRM, paywalls or access controls,',
    'and that the Nuxel project ships no third-party download service.'
  ].join(' ');
  var MAX_ATTEMPTS = 3;

  // Hosts this tool must never contact.  These are service endpoints, not CDNs:
  // the point is that the downloader never authenticates to, or reports to, a
  // Google/Apple/Android/Meta service.
  var DENY_HOSTS = [
    'google-analytics.com', 'analytics.google.com', 'play.google.com', 'dl.google.com',
    'googlevideo.com', 'gstatic.com', 'googleapis.com', 'apple.com', 'itunes.apple.com',
    'mzstatic.com', 'android.com', 'googleplay.com', 'facebook.com', 'graph.facebook.com',
    'doubleclick.net', 'crashlytics.com', 'firebase.io', 'app-measurement.com'
  ];

  var STATES = ['blocked', 'queued', 'running', 'paused', 'done', 'failed', 'cancelled'];

  function acceptNotice(store, version) {
    store.notice = { version: version === undefined ? NOTICE_VERSION : version, accepted: true };
    return store.notice;
  }

  function noticeSatisfied(store) {
    return !!(store && store.notice && store.notice.accepted && store.notice.version === NOTICE_VERSION);
  }

  function hostOf(url) {
    var m = /^([a-z][a-z0-9+.-]*):\/\/([^/?#]+)/i.exec(String(url || '').trim());
    if (!m) return null;
    var host = m[2].toLowerCase().replace(/^[^@]*@/, '').replace(/:\d+$/, '');
    return { scheme: m[1].toLowerCase(), host: host };
  }

  function deniedHost(host) {
    var h = String(host || '').toLowerCase();
    return DENY_HOSTS.some(function (d) { return h === d || h.endsWith('.' + d); });
  }

  function checkUrl(url) {
    var parts = hostOf(url);
    if (!parts) return { ok: false, reason: 'not a URL with a scheme (expected https://…)' };
    if (parts.scheme !== 'https' && parts.scheme !== 'http') {
      return { ok: false, reason: 'scheme “' + parts.scheme + '” is not allowed; only http/https are fetched' };
    }
    if (parts.scheme === 'http') {
      return { ok: false, reason: 'plain http is refused: a downloaded file cannot be integrity-checked over an unauthenticated channel' };
    }
    if (deniedHost(parts.host)) {
      return { ok: false, reason: '“' + parts.host + '” is on the no-third-party-service list (Google/Apple/Android/Meta endpoints are refused)' };
    }
    return { ok: true, scheme: parts.scheme, host: parts.host };
  }

  function filenameFrom(url) {
    var m = /^[^?#]*\/([^/?#]+)$/.exec(String(url || '').split('#')[0].split('?')[0]);
    if (!m || !m[1]) return null;
    var name = decodeURIComponent(m[1]);
    if (!/[.]/.test(name)) return null;
    return name.replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 120);
  }

  function newStore() { return { schemaVersion: SCHEMA_VERSION, notice: null, items: [], counters: { enqueued: 0, refused: 0, done: 0 } }; }

  function addItem(store, raw) {
    if (!noticeSatisfied(store)) {
      store.counters.refused++;
      return { ok: false, reason: 'legal-use notice not accepted — nothing may be queued before it is' };
    }
    var url = String(raw && raw.url || '').trim();
    var v = checkUrl(url);
    if (!v.ok) {
      store.counters.refused++;
      return { ok: false, reason: v.reason };
    }
    var name = raw.name || filenameFrom(url);
    if (!name) {
      store.counters.refused++;
      return { ok: false, reason: 'cannot derive a file name from that URL — supply one explicitly' };
    }
    var item = {
      id: 'dl-' + (store.counters.enqueued + 1) + '-' + Math.abs(hash(url)).toString(36),
      url: url, host: v.host, name: name,
      bytes: typeof raw.bytes === 'number' ? raw.bytes : null,
      sha256: raw.sha256 || null,
      status: 'queued', progress: 0, attempts: 0, strategy: 'direct',
      bytesDone: 0, resumeFrom: 0, verified: null, error: null, addedAt: raw.addedAt || null
    };
    store.items.push(item);
    store.counters.enqueued++;
    return { ok: true, item: item };
  }

  // Small deterministic string hash for stable ids in tests (not security).
  function hash(s) {
    var h = 5381;
    for (var i = 0; i < String(s).length; i++) h = ((h * 33) ^ String(s).charCodeAt(i)) | 0;
    return h;
  }

  function byId(store, id) {
    return (store.items || []).filter(function (i) { return i.id === id; })[0] || null;
  }

  function start(item) {
    if (!item) return null;
    if (item.status === 'blocked' || item.status === 'done') return item;
    item.status = 'running';
    item.error = null;
    return item;
  }

  function pause(item) { if (item && item.status === 'running') { item.status = 'paused'; item.resumeFrom = item.bytesDone || 0; } return item; }
  function resume(item) { if (item && item.status === 'paused') { item.status = 'running'; } return item; }
  function cancel(item) { if (item) { item.status = 'cancelled'; item.error = 'cancelled by the operator'; } return item; }

  function progress(item, bytesDone, total) {
    if (!item) return null;
    item.bytesDone = Math.max(0, bytesDone | 0);
    if (total) item.bytes = total;
    item.progress = item.bytes ? Math.min(100, Math.round((item.bytesDone / item.bytes) * 100)) : (item.status === 'done' ? 100 : 0);
    return item;
  }

  // A transfer may only be recorded as done when its digest checked out, or when
  // no digest was ever published (then verified stays false and the UI must say
  // "unverified download" rather than showing a green tick it did not earn).
  function finish(item, digestHex) {
    if (!item) return null;
    if (item.sha256) {
      if (!digestHex || digestHex.toLowerCase() !== String(item.sha256).toLowerCase()) {
        item.verified = false;
        item.status = 'failed';
        item.error = 'sha256 mismatch: expected ' + item.sha256 + ', got ' + (digestHex || 'nothing');
        return item;
      }
      item.verified = true;
    } else {
      item.verified = false;
    }
    item.status = 'done';
    item.progress = 100;
    item.error = null;
    return item;
  }

  function fail(item, reason) {
    if (!item) return null;
    item.attempts++;
    item.error = reason || 'transfer failed';
    if (item.attempts >= MAX_ATTEMPTS) {
      var before = item.strategy;
      item.strategy = before === 'direct' ? 'resume-range' : (before === 'resume-range' ? 'single-connection-retry-later' : 'manual');
      item.status = 'failed';
      item.error = reason + ' (after ' + item.attempts + ' identical failures: strategy changed ' + before + ' -> ' + item.strategy + ')';
      if (item.strategy === 'manual') {
        item.status = 'blocked';
        item.error += ' — three strategies failed; the item is blocked and needs a human decision';
      }
    } else {
      item.status = 'queued';
    }
    return item;
  }

  function pending(store) {
    return (store.items || []).filter(function (i) { return i.status === 'queued' || i.status === 'running'; });
  }

  function bytesPending(store) {
    return (store.items || []).reduce(function (n, i) {
      if (i.status === 'done' || i.status === 'cancelled') return n;
      return n + Math.max(0, (i.bytes || 0) - (i.bytesDone || 0));
    }, 0);
  }

  function summary(store) {
    var out = { queued: 0, running: 0, paused: 0, done: 0, failed: 0, cancelled: 0, blocked: 0, unverifiedDone: 0 };
    (store.items || []).forEach(function (i) { if (out[i.status] !== undefined) out[i.status]++; });
    out.unverifiedDone = (store.items || []).filter(function (i) { return i.status === 'done' && i.verified === false; }).length;
    return out;
  }

  function serialize(store) { return JSON.stringify({ schemaVersion: SCHEMA_VERSION, notice: store.notice, items: store.items, counters: store.counters }); }

  function deserialize(text) {
    try {
      var doc = JSON.parse(text);
      if (!doc || typeof doc !== 'object' || !Array.isArray(doc.items)) return newStore();
      var s = newStore();
      s.notice = doc.notice || null;
      s.items = doc.items.filter(function (i) { return i && i.url && STATES.indexOf(i.status) !== -1; });
      s.counters = doc.counters || s.counters;
      return s;
    } catch (e) { return newStore(); }
  }

  function formatBytes(n) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    var u = ['B', 'KiB', 'MiB', 'GiB', 'TiB'], i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return (i ? n.toFixed(1) : String(n)) + ' ' + u[i];
  }

  return {
    SCHEMA_VERSION: SCHEMA_VERSION, NOTICE_VERSION: NOTICE_VERSION, NOTICE_TEXT: NOTICE_TEXT,
    DENY_HOSTS: DENY_HOSTS, STATES: STATES, MAX_ATTEMPTS: MAX_ATTEMPTS,
    acceptNotice: acceptNotice, noticeSatisfied: noticeSatisfied, checkUrl: checkUrl,
    filenameFrom: filenameFrom, newStore: newStore, addItem: addItem, byId: byId,
    start: start, pause: pause, resume: resume, cancel: cancel, progress: progress,
    finish: finish, fail: fail, pending: pending, bytesPending: bytesPending,
    summary: summary, serialize: serialize, deserialize: deserialize, formatBytes: formatBytes
  };
}));
