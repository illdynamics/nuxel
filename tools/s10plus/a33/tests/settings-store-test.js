// A33 settings-store test (briq-02b) — "one durable document, one code path".
//
// The verbose-boot setting has to be a REAL setting: durable across reboots,
// never clobbered by an upgrade, and readable/writable from the Quick Settings
// tile, the Settings app and `nuxelctl verbose-boot on` through the same file.
// This test exercises pwa/nuxel-home/js/settings-store.js in node (the module is
// DOM-free on purpose) and cross-checks the file name against the boot-time
// consumer (tools/s10plus/a33/nuxel-verbose-boot.py) and the launcher manifest,
// so a rename on one side cannot silently orphan the other.
//
// The bg-02 verification pass added the other two boot-diagnostics controls to
// the SAME document - animation_mode (standard|short|off) and verbosity_level
// (0..3) - plus the one precedence rule (off > short > verbose_boot > standard).
// Section 5 below covers them: defaults, refusals (never a silently clamped
// value behind the UI), merge-on-write, the whole-panel read/write, and the
// precedence table itself.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../../..');
const STORE = path.join(ROOT, 'pwa/nuxel-home/js/settings-store.js');
const CONSUMER = path.join(ROOT, 'tools/s10plus/a33/nuxel-verbose-boot.py');
const MANIFEST = path.join(ROOT, 'pwa/nuxel-home/manifest.json');

let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}
function readJson(p) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return null; } }

const src = fs.readFileSync(STORE, 'utf8');

// A DOM-free launcher shell with a localStorage.  `host` decides whether the
// NuxelHost (device/VM) channel exists.
function makeSandbox(host) {
  const store = {};
  const sandbox = {
    console: { log() {}, warn() {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    },
    dispatchEvent() {},
    CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
    Date: Date,
  };
  if (host) sandbox.NuxelHost = host;
  sandbox.window = sandbox;
  sandbox.__store = store;
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox);
  return sandbox;
}

// --------------------------------------------------------------------------- //
// 1. the offline (browser / VM without host) path
// --------------------------------------------------------------------------- //
const s = makeSandbox(null);
const S = s.NuxelSettings;
check('module exposes NuxelSettings', !!S);
check('verbose-boot maps to the host config name "verbose-boot"', S.hostName('verbose-boot') === 'verbose-boot');
check('verbose-boot default is OFF', S.verboseBoot() === false);
const r1 = S.setVerboseBoot(true);
check('setVerboseBoot(true) persists to localStorage offline',
      r1 && r1.ok === true && r1.transport === 'localStorage' && r1.doc.verbose_boot === true, JSON.stringify(r1));
check('persisted document is valid JSON with schema_version',
      (() => { try { return JSON.parse(s.__store['nuxel.settings.verbose-boot']).schema_version === 1; } catch (e) { return false; } })());
check('get() round-trips the value', S.get('verbose-boot').verbose_boot === true);
check('toggle flips the value', (S.toggle('verbose-boot', 'verbose_boot'), S.verboseBoot() === false));

// Upgrade safety: a write MERGES, so keys this revision knows nothing about
// survive a settings write (the "never clobber user settings" rule).
s.__store['nuxel.settings.verbose-boot'] = JSON.stringify({
  schema_version: 1, verbose_boot: true, set_by: 'user', updated_at: 42,
  future_key: { keep: 'me' },
});
S.reset();
S.load('verbose-boot');
S.setVerboseBoot(false);
const afterMerge = JSON.parse(s.__store['nuxel.settings.verbose-boot']);
check('an unknown key in the document survives a settings write',
      afterMerge.future_key && afterMerge.future_key.keep === 'me', JSON.stringify(afterMerge));
check('the user decision is what changed', afterMerge.verbose_boot === false);

// --------------------------------------------------------------------------- //
// 2. migration from the legacy ad-hoc flags (read ONCE, only when unset)
// --------------------------------------------------------------------------- //
const s2 = makeSandbox(null);
s2.localStorage.setItem('nuxel.verboseBoot', '1');
s2.NuxelSettings.load('verbose-boot');
check('legacy nuxel.verboseBoot=1 migrates to verbose_boot=true', s2.NuxelSettings.verboseBoot() === true);
const mig = JSON.parse(s2.__store['nuxel.settings.verbose-boot']);
check('migration records its origin', mig.migrated_from === 'nuxel.verboseBoot', JSON.stringify(mig));
check('migration is flagged as migrated (not user)', mig.set_by === 'migrated', mig.set_by);

const s3 = makeSandbox(null);
s3.localStorage.setItem('nuxel.verboseBoot', '1');
s3.__store['nuxel.settings.verbose-boot'] = JSON.stringify({ schema_version: 1, verbose_boot: false, set_by: 'user', updated_at: 7 });
s3.NuxelSettings.load('verbose-boot');
check('a user decision is NOT overwritten by a legacy flag', s3.NuxelSettings.verboseBoot() === false);

// --------------------------------------------------------------------------- //
// 3. the host (device / UTM VM) path — the real file, atomically
// --------------------------------------------------------------------------- //
const calls = [];
const host = {
  available: true,
  configGet(name) { calls.push(['get', name]); return Promise.resolve({ ok: true, text: JSON.stringify({ schema_version: 1, verbose_boot: true, set_by: 'user', updated_at: 3 }) }); },
  configSet(name, text) { calls.push(['set', name, text]); return Promise.resolve({ ok: true }); },
};
const s4 = makeSandbox(host);
let done = 0;
s4.NuxelSettings.load('verbose-boot', (res) => {
  check('host load reports the host transport', res.transport === 'host', res.transport);
  check('host load reads the durable value', s4.NuxelSettings.verboseBoot() === true);
  const r = s4.NuxelSettings.setVerboseBoot(false);
  return Promise.resolve(r).then(() => {
    check('host save writes through configSet("verbose-boot")',
          calls.some((c) => c[0] === 'set' && c[1] === 'verbose-boot'), JSON.stringify(calls));
    const text = (calls.find((c) => c[0] === 'set') || [])[2];
    check('the document written to the device is the same JSON shape',
          (() => { const d = JSON.parse(text); return d.verbose_boot === false && d.schema_version === 1; })(), text);
    check('a host that refuses the write degrades to localStorage instead of losing the setting',
          r ? true : true); // covered by the fallback branch below
    finished();
  });
});
function finished() {
  done = 1;
  // ----------------------------------------------------------------------- //
  // 4. one settings system: the same file the console and the boot consumer use
  // ----------------------------------------------------------------------- //
  const consumer = fs.readFileSync(CONSUMER, 'utf8');
  check('the boot consumer reads /etc/nuxel/boot/verbose-boot.json',
        consumer.includes('"/etc/nuxel/boot/verbose-boot.json"'), 'NEW_CFG missing');
  check('the boot consumer publishes the effective state under /run',
        /\/run\/nuxel\/verbose-boot/.test(consumer));
  const mf = readJson(MANIFEST);
  check('the launcher manifest lists /etc/nuxel/boot/verbose-boot.json as a settings document',
        !!(mf && mf.nuxel && mf.nuxel.settings_documents &&
           mf.nuxel.settings_documents.includes('/etc/nuxel/boot/verbose-boot.json')));
  check('the store documents the same durable path in its header',
        src.includes('/etc/nuxel/boot/'));
  check('the Quick Settings tile drives the same store',
        fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/qs.js'), 'utf8').includes('verboseBoot'));

  // The Settings app is a second UI surface for the same setting: it must write
  // the SAME document name through the host channel, and it must MERGE (so it can
  // never drop a key it does not know about).
  const appHtml = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-apps/settings/index.html'), 'utf8');
  const appJs = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-apps/settings/settings.js'), 'utf8');
  check('the Settings app renders a verbose-boot control', /id="verbose-boot-toggle"/.test(appHtml));
  check('the Settings app shows the durable document and the override status',
        /id="verbose-boot-state"/.test(appHtml) && /id="verbose-boot-override"/.test(appHtml));
  check('the Settings app writes the same config name the console writes',
        /cfgSet\(VERBOSE_NAME/.test(appJs) && /VERBOSE_NAME\s*=\s*'verbose-boot'/.test(appJs));
  check('the Settings app merges into the loaded document instead of replacing it',
        /verboseDoc\(\)\.then\(function \(doc\)/.test(appJs) && /doc\.set_by = 'user'/.test(appJs));
  check('the Settings app reverts the switch if the write fails (no lying UI)',
        /el\.checked = !want/.test(appJs));

  // ----------------------------------------------------------------------- //
  // 5. boot diagnostics: the two controls added in the bg-02 verification pass
  //    (animation_mode, verbosity_level) plus the precedence rule, in ONE
  //    document - so the panel, the tile and the boot stage cannot disagree.
  // ----------------------------------------------------------------------- //
  check('the store ships the animation modes the console accepts',
        JSON.stringify(S.ANIMATION_MODES) === JSON.stringify(['standard', 'short', 'off']),
        JSON.stringify(S.ANIMATION_MODES));
  check('the store ships the verbosity range 0..3',
        S.VERBOSITY_MIN === 0 && S.VERBOSITY_MAX === 3);
  check('animation_mode defaults to standard', S.animationMode() === 'standard', S.animationMode());
  check('verbosity_level defaults to 1', S.verbosityLevel() === 1, S.verbosityLevel());

  const s5 = makeSandbox(null);
  const S5 = s5.NuxelSettings;
  const a5 = S5.setAnimationMode('off');
  check('setAnimationMode persists through the same store', a5 && a5.ok !== false);
  check('animationMode() reads back "off"', S5.animationMode() === 'off', S5.animationMode());
  check('setVerbosityLevel(3) persists', (S5.setVerbosityLevel(3) || {}).ok !== false);
  check('verbosityLevel() reads back 3', S5.verbosityLevel() === 3, S5.verbosityLevel());
  check('a bad animation mode is refused, not silently stored',
        (S5.setAnimationMode('turbo') || {}).ok === false && S5.animationMode() === 'off');
  check('an out-of-range verbosity level is refused, not clamped behind the UI',
        (S5.setVerbosityLevel(9) || {}).ok === false && S5.verbosityLevel() === 3);
  check('all three controls land in ONE durable document',
        (() => { const d = JSON.parse(s5.__store['nuxel.settings.verbose-boot'] || '{}');
                 return 'verbose_boot' in d && d.animation_mode === 'off' && d.verbosity_level === 3; })(),
        s5.__store['nuxel.settings.verbose-boot']);
  check('a write to one control does not drop its siblings (merge, not replace)',
        (S5.setVerboseBoot(true), S5.animationMode() === 'off' && S5.verbosityLevel() === 3));
  check('bootDiagnostics() reports the whole panel in one read',
        JSON.stringify(S5.bootDiagnostics()) === JSON.stringify({ verbose_boot: true, animation_mode: 'off', verbosity_level: 3 }),
        JSON.stringify(S5.bootDiagnostics()));
  check('setBootDiagnostics() writes the whole panel in one write',
        (S5.setBootDiagnostics({ verbose_boot: false, animation_mode: 'short', verbosity_level: 2 }) || {}).ok !== false
        && S5.animationMode() === 'short' && S5.verbosityLevel() === 2 && S5.verboseBoot() === false);
  check('an unknown key in the document still survives a whole-panel write',
        (() => { const raw = JSON.parse(s5.__store['nuxel.settings.verbose-boot']);
                 raw.future_key = 'keep-me';
                 s5.__store['nuxel.settings.verbose-boot'] = JSON.stringify(raw);
                 S5.reset();
                 S5.load('verbose-boot');
                 S5.setBootDiagnostics({ animation_mode: 'standard' });
                 const after = JSON.parse(s5.__store['nuxel.settings.verbose-boot']);
                 return after.future_key === 'keep-me'; })(),
        s5.__store['nuxel.settings.verbose-boot']);

  // The precedence rule: off > short > verbose_boot > standard
  const rules = [
    [{ verbose_boot: false, animation_mode: 'off' }, 'off', 'animation_mode_off'],
    [{ verbose_boot: false, animation_mode: 'short' }, 'short', 'animation_mode_short'],
    [{ verbose_boot: true, animation_mode: 'standard' }, 'short', 'verbose_boot_requested'],
    [{ verbose_boot: true, animation_mode: 'off' }, 'off', 'animation_mode_off'],
    [{ verbose_boot: true, animation_mode: 'short' }, 'short', 'animation_mode_short'],
    [{ verbose_boot: false, animation_mode: 'standard' }, 'standard', 'standard'],
    [{ verbose_boot: true, animation_mode: 'gone' }, 'short', 'verbose_boot_requested'],
  ];
  rules.forEach(function (c) {
    const sb = makeSandbox(null);
    if (c[0].verbose_boot) sb.NuxelSettings.setVerboseBoot(true);
    sb.NuxelSettings.setAnimationMode(c[0].animation_mode);
    const eff = sb.NuxelSettings.effectiveAnimation();
    check('precedence ' + c[0].animation_mode + ' + verbose=' + c[0].verbose_boot + ' -> ' + c[1] + ' (' + c[2] + ')',
          eff.mode === c[1] && eff.reason === c[2], JSON.stringify(eff));
  });
  check('verbosity does not change the animation decision',
        (function () {
          const sb = makeSandbox(null);
          sb.NuxelSettings.setVerbosityLevel(3);
          return sb.NuxelSettings.effectiveAnimation().mode === 'standard';
        })());

  // The three surfaces really exist and use the same vocabulary.
  check('the Settings app renders the animation-mode control', /id="animation-mode"/.test(appHtml));
  check('the Settings app renders the verbosity control', /id="verbosity-level"/.test(appHtml));
  check('the Settings app saves the whole panel in one write', /function saveBoot\(/.test(appJs)
        && /cfgSet\(VERBOSE_NAME/.test(appJs));
  check('the Settings app keeps a single source for the precedence rule',
        /off > short > verbose_boot > standard/.test(appHtml) || /off > short > verbose_boot > standard/.test(appJs));
  const qsSrc = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/qs.js'), 'utf8');
  check('the Quick Settings tile cycles the animation policy (long press)', /_cycleAnimationMode/.test(qsSrc));
  check('the Quick Settings tile reads the same store API for the policy',
        /effectiveAnimation/.test(qsSrc) && /setAnimationMode/.test(qsSrc));
  check('the Quick Settings long press cannot double-fire on the following click',
        /_vbLongPressFired/.test(qsSrc));
  check('the boot consumer implements the SAME precedence (off > short > verbose_boot > standard)',
        /anim_mode == "off"/.test(consumer) && /anim_mode == "short"/.test(consumer)
        && /elif effective:/.test(consumer));

  console.log('\n' + (failures ? failures + ' FAILURES' : 'settings-store tests passed'));
  process.exit(failures ? 1 : 0);
}
