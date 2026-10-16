// Nuxel Downloader queue engine — offline tests.
//
//   node pwa/nuxel-apps/downloader/tests/test-download-queue.js
//
// Claims pinned here (see docs/beta-finalization/apps/MEDIA-AUTH.md):
// legal gate, no-third-party-service, https-only, resume offsets, retry with a
// strategy change after three identical failures, digest-gated completion.
const fs = require('fs');
const Q = require('../js/download-queue.js');
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

console.log('download queue engine');

// ---- legal gate ----------------------------------------------------------
let store = Q.newStore();
check('a fresh store has no notice acceptance', Q.noticeSatisfied(store) === false);
let r = Q.addItem(store, { url: 'https://example.org/a.mp3' });
check('queueing is refused before the notice is accepted', r.ok === false);
check('the refusal explains the notice requirement', /notice not accepted/.test(r.reason));
check('a refused item is counted, not silently dropped', store.counters.refused === 1);
check('a refused item is not added', store.items.length === 0);
Q.acceptNotice(store);
check('accepting the notice satisfies the gate', Q.noticeSatisfied(store) === true);
store.notice = { version: Q.NOTICE_VERSION - 1, accepted: true };
check('an old notice version does not satisfy a newer notice', Q.noticeSatisfied(store) === false);
Q.acceptNotice(store);

// ---- scheme rules --------------------------------------------------------
check('https is accepted', Q.checkUrl('https://example.org/x.bin').ok === true);
check('plain http is refused', Q.checkUrl('http://example.org/x.bin').ok === false);
check('the http refusal says why', /unauthenticated channel/.test(Q.checkUrl('http://example.org/x.bin').reason));
check('ftp is refused', Q.checkUrl('ftp://example.org/x').ok === false);
check('a bare path is refused', Q.checkUrl('example.org/x').ok === false);
check('an empty string is refused', Q.checkUrl('').ok === false);

// ---- no third-party service ---------------------------------------------
Q.DENY_HOSTS.forEach(function (h) {
  const res = Q.checkUrl('https://' + h + '/thing');
  check('denied host refused: ' + h, res.ok === false, res.reason);
});
check('a subdomain of a denied host is refused too', Q.checkUrl('https://cdn.play.google.com/x').ok === false);
check('the denial names the host', /play\.google\.com/.test(Q.checkUrl('https://play.google.com/x').reason));
check('a lookalike host is NOT refused', Q.checkUrl('https://notgoogle.com/x.bin').ok === true);
check('a host that merely contains a denied name is not refused',
  Q.checkUrl('https://google-analytics.com.evil.example/x').ok === true);
check('the denied list is data that ships with the app', Q.DENY_HOSTS.length >= 10);

// ---- file names ----------------------------------------------------------
check('a name is derived from the URL path', Q.filenameFrom('https://example.org/a/b/song.mp3') === 'song.mp3');
check('query strings do not leak into the name', Q.filenameFrom('https://example.org/song.mp3?token=abc') === 'song.mp3');
check('weird characters are neutralised', /^[A-Za-z0-9._-]+$/.test(Q.filenameFrom('https://example.org/a%20b%3Bc.mp3')));
check('a URL with no file component yields no name', Q.filenameFrom('https://example.org/') === null);
r = Q.addItem(store, { url: 'https://example.org/' });
check('an underivable name is refused', r.ok === false && /derive a file name/.test(r.reason));

// ---- enqueue + counters --------------------------------------------------
r = Q.addItem(store, { url: 'https://ftp.gnu.org/gnu/coreutils/coreutils-9.5.tar.xz', bytes: 6000000 });
check('a valid https item is queued', r.ok === true && r.item.status === 'queued');
check('the item records its host', r.item.host === 'ftp.gnu.org');
check('the item starts with zero attempts', r.item.attempts === 0);
check('the item starts on the direct strategy', r.item.strategy === 'direct');
check('ids are unique', Q.addItem(store, { url: 'https://ftp.gnu.org/gnu/x/x.tar.xz' }).item.id !== r.item.id);

// ---- progress / pause / resume ------------------------------------------
const item = Q.byId(store, r.item.id);
Q.start(item);
check('start moves the item to running', item.status === 'running');
Q.progress(item, 1500000, 6000000);
check('progress is a real fraction of the known size', item.progress === 25, String(item.progress));
Q.pause(item);
check('pause records the resume offset', item.resumeFrom === 1500000 && item.status === 'paused');
Q.resume(item);
check('resume returns to running with the offset intact', item.status === 'running' && item.resumeFrom === 1500000);
Q.progress(item, 6000000, 6000000);
check('progress saturates at 100%', item.progress === 100);
Q.cancel(item);
check('cancel is recorded with a reason', item.status === 'cancelled' && /operator/.test(item.error));

// ---- completion requires a digest ---------------------------------------
const good = Q.addItem(store, { url: 'https://example.org/g.mp3', sha256: 'aa'.repeat(32) }).item;
Q.finish(good, 'AA'.repeat(32));
check('a matching digest (case-insensitive) marks the item verified done',
  good.status === 'done' && good.verified === true);
const bad = Q.addItem(store, { url: 'https://example.org/b.mp3', sha256: 'bb'.repeat(32) }).item;
Q.finish(bad, 'cc'.repeat(32));
check('a mismatched digest is a FAILURE, never a warning', bad.status === 'failed');
check('the mismatch error names both digests', /expected bb/.test(bad.error) && /got cc/.test(bad.error));
const nodigest = Q.addItem(store, { url: 'https://example.org/n.mp3' }).item;
Q.finish(nodigest, null);
check('an item with no published digest is done but explicitly unverified',
  nodigest.status === 'done' && nodigest.verified === false);
const summ = Q.summary(store);
check('the summary counts unverified completions separately', summ.unverifiedDone === 1);
check('the summary counts failures', summ.failed === 1);

// ---- three failures, then a different strategy ---------------------------
const flaky = Q.addItem(store, { url: 'https://example.org/f.mp3' }).item;
Q.start(flaky);
Q.fail(flaky, 'timeout');
check('failure 1 leaves the item queued for retry', flaky.status === 'queued' && flaky.attempts === 1);
check('failure 1 keeps the strategy', flaky.strategy === 'direct');
Q.fail(flaky, 'timeout again');
check('failure 2 still queues', flaky.status === 'queued' && flaky.attempts === 2);
Q.fail(flaky, 'timeout once more');
check('failure 3 changes the strategy', flaky.strategy === 'resume-range', flaky.strategy);
check('the error text records the strategy change', /strategy changed direct -> resume-range/.test(flaky.error));
Q.fail(flaky, 'still failing');
Q.fail(flaky, 'still failing');
Q.fail(flaky, 'still failing');
check('a later third identical failure changes strategy again', flaky.strategy === 'manual', flaky.strategy);
check('three failing strategies block the item for a human', flaky.status === 'blocked');
Q.start(flaky);
check('a blocked item cannot be restarted by a stray start()', flaky.status === 'blocked');

// ---- persistence --------------------------------------------------------
const text = Q.serialize(store);
const back = Q.deserialize(text);
check('the queue survives serialisation', back.items.length === store.items.length);
check('the notice acceptance survives serialisation', Q.noticeSatisfied(back) === true);
check('counters survive serialisation', back.counters.enqueued === store.counters.enqueued);
check('corrupt storage degrades to an empty queue, not a crash',
  Q.deserialize('{not json').items.length === 0);
check('items with an unknown state are dropped on load',
  Q.deserialize(JSON.stringify({ items: [{ url: 'https://a/b.mp3', status: 'teleported' }] })).items.length === 0);

// ---- pending bytes ------------------------------------------------------
check('pending bytes only counts unfinished work',
  Q.bytesPending({ items: [
    { status: 'done', bytes: 100, bytesDone: 100 },
    { status: 'queued', bytes: 100, bytesDone: 25 },
    { status: 'cancelled', bytes: 100, bytesDone: 0 }
  ] }) === 75);
check('formatBytes is human readable', Q.formatBytes(6000000) === '5.7 MiB', Q.formatBytes(6000000));

// ---- shipped examples must agree with the engine -------------------------
const ex = JSON.parse(fs.readFileSync(__dirname + '/../samples/queue-examples.json', 'utf8'));
ex.cases.forEach(function (c) {
  const res = Q.checkUrl(c.url);
  const verdict = res.ok ? 'accepted' : 'refused';
  check('documented example agrees with the engine: ' + c.url, verdict === c.expected,
    verdict + ' vs documented ' + c.expected);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
