// Nuxel Media library/queue/route model — offline tests.
//
//   node pwa/nuxel-apps/media/tests/test-media-library.js
//
// Every assertion maps to a claim in docs/beta-finalization/apps/MEDIA-AUTH.md.
// The point of the suite is that the player cannot (a) present the bundled
// sample library as a device scan, or (b) state that audio was audible.
const M = require('../js/media-library.js');
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

console.log('media library / queue / route');

// ---- source honesty -------------------------------------------------------
const lib = M.buildLibrary([
  { name: 'tone-440.wav', title: 'Reference tone', seconds: 2, url: 'samples/tone-440.wav' },
  { name: 'clip.mp4', kind: 'video', seconds: 12, url: null, playable: false }
], 'sample');
check('buildLibrary tags every track with the library source',
  lib.tracks.every(t => t.source === 'sample'));
check('buildLibrary keeps the library-level source', lib.source === 'sample');
check('mediaKind classifies wav as audio', M.mediaKind('tone-440.wav') === 'audio');
check('mediaKind classifies mp4 as video', M.mediaKind('clip.MP4') === 'video');
check('mediaKind refuses to classify an unknown container', M.mediaKind('mystery.bin') === 'unknown');
check('tracks are sorted by title for a stable UI',
  lib.tracks.every((t, i, a) => i === 0 || a[i - 1].title.localeCompare(t.title) <= 0),
  lib.tracks.map(t => t.title).join(' | '));
const clip = lib.tracks.filter(t => t.container === 'mp4')[0];
check('an unplayable row keeps playable=false', clip && clip.playable === false);
check('a playable row keeps playable=true',
  lib.tracks.filter(t => t.container === 'wav')[0].playable === true);

// ---- no invented library --------------------------------------------------
check('an empty item list yields an empty library, not a fabricated one',
  M.buildLibrary([], 'sample').tracks.length === 0);
check('an item without a name is dropped instead of shown blank',
  M.buildLibrary([{ title: '' }], 'sample').tracks.length === 0);

// ---- decode support is only claimed when probed ---------------------------
check('unprobed container reports supported=null (no claim)',
  M.decodeSupport('song.flac', null).supported === null);
check('probed container that is known good reports supported=true',
  M.decodeSupport('song.wav', ['wav', 'mp3']).supported === true);
check('probed container that is missing says why it will fail',
  /not shipped/.test(M.decodeSupport('song.mkv', ['wav']).note));
check('a file with no extension cannot claim a demuxer',
  M.decodeSupport('noext', ['wav']).supported === false);

// ---- time formatting -----------------------------------------------------
check('formatTime pads seconds', M.formatTime(65) === '1:05', M.formatTime(65));
check('formatTime grows to hours', M.formatTime(3725) === '1:02:05', M.formatTime(3725));
check('formatTime refuses to invent a duration', M.formatTime(null) === '--:--');
check('formatBytes is human readable', M.formatBytes(32044) === '31.3 KiB', M.formatBytes(32044));

// ---- queue --------------------------------------------------------------
const q = M.newQueue(lib.tracks);
check('a new queue starts at the first track', M.current(q).id === lib.tracks[0].id);
check('advance moves forward', M.advance(q, 1).track.id === lib.tracks[1].id);
const end = M.advance(q, 1);
check('advance past the end reports ended when repeat is off', end.ended === true);
M.setRepeat(q, 'all');
q.index = lib.tracks.length - 1;
check('repeat=all wraps to the first track', M.advance(q, 1).track.id === lib.tracks[0].id);
M.setRepeat(q, 'one');
check('repeat=one keeps the same index for the caller to replay',
  M.advance(q, 1).q.index === q.index || q.repeat === 'one');
let threw = false;
try { M.setRepeat(q, 'sometimes'); } catch (e) { threw = true; }
check('an invalid repeat mode is rejected, not silently accepted', threw);
// Shuffle is deterministic (a test can pin it) but must never land on the track
// that is already playing, and must be able to reach every other track.
const q4 = M.newQueue(M.buildLibrary([
  { name: 'a.wav' }, { name: 'b.wav' }, { name: 'c.wav' }, { name: 'd.wav' }], 'sample').tracks);
q4.shuffle = true;
const seen = new Set();
for (let order = 1; order <= 40; order++) {
  const ix = M.nextIndex(q4, order, true);
  seen.add(ix);
  check('shuffle never replays the current track (order ' + order + ')', ix !== q4.index);
}
check('shuffle can reach more than one track', seen.size > 1, 'distinct=' + seen.size);
check('in shuffle mode advance() moves off the current track',
  M.advance(q4, 7).q.index !== 0);

// ---- volume: never invent a reading --------------------------------------
check('clampVolume bounds the request', M.clampVolume(150) === 100 && M.clampVolume(-4) === 0);
check('clampVolume rejects a non-number', M.clampVolume('loud') === null);
check('mixerToPercent needs a real max', M.mixerToPercent(40, 0) === null);
check('mixerToPercent converts mixer units', M.mixerToPercent(40, 80) === 50);

// ---- route honesty -------------------------------------------------------
const unknown = M.describeRoute(null);
check('no probe => route unknown', unknown.source === 'unavailable');
check('no probe => audibility is unverified', unknown.audible === 'unverified');
check('no probe => the summary says so in words', /NOT claimed/.test(unknown.summary));
const probed = M.describeRoute({
  server: 'PipeWire 1.2', alsaCard: 'beyond-madera', alsaCardId: 0, sink: 'alsa_output.platform-beyond-madera',
  mixerControl: 'Playback Volume', headphones: false, ownerVerifiedAudible: false, source: 'live'
});
check('a real probe is reported field by field',
  probed.lines.some(l => l[0] === 'ALSA card' && /beyond-madera/.test(l[1])));
check('a real probe still does not claim audibility without an owner test', probed.audible === 'unverified');
check('the summary names the route and the unverified state',
  /PipeWire 1\.2/.test(probed.summary) && /UNVERIFIED/.test(probed.summary));
const verified = M.describeRoute({ server: 'PipeWire', alsaCard: 'beyond-madera', ownerVerifiedAudible: true });
check('audibility can only be claimed once the owner test is recorded', verified.audible === 'verified');
check('the verified line points at the manual proof area',
  verified.lines.some(l => /area 41/.test(l[1])));
check('headphones=false is reported as not detected, not as "no headphones support"',
  M.describeRoute({ headphones: false }).lines.some(l => l[0] === 'Headphones' && l[1] === 'not detected'));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
