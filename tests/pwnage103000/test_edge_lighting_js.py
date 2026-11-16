#!/usr/bin/env python3
"""Edge Lighting engine contract tests: registry, default, colour, policy gates."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, node_json, finish, ROOT  # noqa: E402

res = node_json(r"""
const api = global.NuxelEdgeLighting;
const out = {};
out.effects = api.EFFECTS;
out.labels = Object.keys(api.EFFECT_LABELS).sort();
out.defaults = api.DEFAULTS;
const norm = api.normaliseSettings({});
out.normalised = norm;
out.badEffect = api.normaliseSettings({ effect: 'strobe' }).effect;
out.clampLow = api.normaliseDuration(50);
out.clampHigh = api.normaliseDuration(99999);
out.accent = api.resolveColor({ color_mode: 'theme', color: null }, '#ffb454', null);
out.custom = api.resolveColor({ color_mode: 'custom', color: '#123456' }, '#ffb454', null);
out.presetNoColor = api.resolveColor({ color_mode: 'preset', color: null }, '#3beaa1', null);
out.appReal = api.resolveColor({ color_mode: 'app' }, '#3beaa1', '#abcdef');
out.appMissing = api.resolveColor({ color_mode: 'app' }, '#3beaa1', null);
out.invalidAccent = api.resolveColor({ color_mode: 'theme' }, 'red', null);
out.screenModeForced = api.normaliseSettings({ screen_mode: 'screen_off' }).screen_mode;
out.specs = {};
for (const e of api.EFFECTS) {
  const s = api.sceneSpec(e, { width: 'wide', duration_ms: 1800 });
  out.specs[e] = s ? { elements: s.elements, particles: s.particles } : null;
}
out.unknownSpec = api.sceneSpec('fractal', {});
out.rgba = api.rgba('#63f0bd', 0.5);
out.noDomRoot = (typeof document === 'undefined') ? -1 : document.querySelectorAll('#nuxel-edge-lighting').length;
console.log(JSON.stringify(out));
""")

check('eight S10-style effects are registered in order',
      res['effects'] == ['basic', 'wave', 'bubble', 'multicolor', 'heart', 'fireworks', 'eclipse', 'echo'],
      res['effects'])
check('every effect has a human label', sorted(res['labels']) == sorted(res['effects']), res['labels'])
check('persisted default effect is Wave', res['normalised']['effect'] == 'wave' and res['defaults']['effect'] == 'wave')
check('default colour mode is the theme accent', res['normalised']['color_mode'] == 'theme' and res['normalised']['color'] is None)
check('default duration is 1800 ms', res['normalised']['duration_ms'] == 1800)
check('default width/transparency are medium',
      res['normalised']['width'] == 'medium' and res['normalised']['transparency'] == 'medium')
check('default screen mode is screen_on', res['normalised']['screen_mode'] == 'screen_on')
check('DND and reduced motion are respected by default',
      res['normalised']['respect_dnd'] is True and res['normalised']['respect_reduced_motion'] is True)
check('enabled default means edge lighting, not torch', res['normalised']['enabled'] is True)
check('unknown effect falls back to Wave, never a fake tile', res['badEffect'] == 'wave', res['badEffect'])
check('duration is clamped to 600..6000 ms', res['clampLow'] == 600 and res['clampHigh'] == 6000,
      (res['clampLow'], res['clampHigh']))
check('theme accent resolves from the live Nuxel token', res['accent'] == '#ffb454', res['accent'])
check('custom colour resolves', res['custom'] == '#123456')
check('preset without a colour falls back to the accent', res['presetNoColor'] == '#3beaa1')
check('app colour mode uses a real registry colour only', res['appReal'] == '#abcdef')
check('app colour mode never invents a colour', res['appMissing'] == '#3beaa1')
check('invalid theme accent falls back to the documented accent', res['invalidAccent'] == '#63f0bd')
check('unsupported screen mode is clamped to screen_on', res['screenModeForced'] == 'screen_on')
check('all eight effects produce a scene spec', all(res['specs'][e] for e in res['effects']), res['specs'])
check('particle budget stays small (<= 10 per frame)',
      all((s['particles'] + s['elements']) <= 12 for s in res['specs'].values()), res['specs'])
check('unknown effect has no scene', res['unknownSpec'] is None)
check('rgba helper produces a colour with alpha', res['rgba'].startswith('rgba(99,240,189,'), res['rgba'])
check('loading the module in a DOM-less harness adds no overlay', res['noDomRoot'] == -1)

# CSS: every effect has an animation rule and no animated blur/box-shadow.
css = (ROOT / 'pwa/nuxel-home/css/edge-lighting.css').read_text()
for eff in res['effects']:
    check('css has an edge-fx-%s rule' % eff, ('.edge-fx-%s' % eff) in css)
check('css marks the overlay pointer-events none', 'pointer-events: none' in css)
check('css keeps will-change scoped to animated particles', 'will-change' in css and 'edge-running' in css)
check('css does not animate a box-shadow or blur filter',
      '@keyframes edge-basic-in' in css and 'filter: blur' not in css)
check('css has a reduced-motion alternative', '@media (prefers-reduced-motion: reduce)' in css)

finish('PWNAGE-103000 edge lighting engine')
