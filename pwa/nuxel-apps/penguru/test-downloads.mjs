// Regression checks for the bulk download controls and talkback default.
//
// Run with: node pwa/nuxel-apps/penguru/test-downloads.mjs

import {createLocalEngine, RUNTIMES} from './local-engine.js';
import {talkbackControls} from './talkback.js';
import {formatBytes, sumBytes} from './download-confirm.js';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const engine = createLocalEngine();
const cards = engine.cards();
const variants = cards.flatMap(card => card.variants);
const modelBytes = sumBytes(variants, variant => variant.size_bytes);

assert(cards.length === 8, 'expected eight model cards, got ' + cards.length);
assert(variants.length === 8, 'expected eight downloadable variants, got ' + variants.length);
assert(modelBytes === 9939182620, 'model total changed unexpectedly: ' + modelBytes);
assert(formatBytes(modelBytes) === '9.94 GB', 'unexpected model total label: ' + formatBytes(modelBytes));
assert(formatBytes(0) === '0 B', 'zero byte label is wrong');
assert(formatBytes(1500) === '1.5 KB', 'kilobyte label is wrong');

const installable = RUNTIMES.filter(runtime => !runtime.bundled);
const runtimeBytes = sumBytes(installable, runtime => runtime.size_bytes);
assert(installable.length === 3, 'expected three installable runtimes');
assert(runtimeBytes === 178986326, 'runtime total changed unexpectedly: ' + runtimeBytes);
assert(formatBytes(runtimeBytes) === '179.0 MB', 'unexpected runtime total label: ' + formatBytes(runtimeBytes));

const talkback = talkbackControls();
assert(talkback.state.enabled === true, 'talkback must be enabled by default');

console.log('download controls + talkback defaults PASSED');
console.log('  models:   8 packages, ' + formatBytes(modelBytes));
console.log('  runtimes: 3 packages, ' + formatBytes(runtimeBytes));
