#!/usr/bin/env node
// Nuxel SnekByte — offline engine tests.
//
//   node pwa/nuxel-apps/snekbyte/tests/test-snek-engine.js
//
// Two independent jobs:
//   1. the engine's own rules (turn/tail, eat/grow, wall/self/poop endings,
//      WoNQ counter, speed table, determinism, food placement, environment
//      independence) — the asserts a reader can check by hand;
//   2. a replay of tools/s10plus/a33/snekbyte/fixtures/parity.json, the recording
//      produced by running the REAL upstream Python game, requiring the state
//      after every single tick to be identical.
//
// Every assertion maps to a claim in docs/beta-finalization/apps/SNEKBYTE.md.
// A green run is OFFLINE_TESTED — it is not a claim about any physical phone.
'use strict';
const fs = require('fs');
const path = require('path');
const E = require(path.join(__dirname, '..', 'js', 'snek-engine.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail !== undefined ? '  — ' + detail : '')); }
}
const cfg = E.cloneConfig({});
const S = (o) => E.settings(cfg, Object.assign({ wrapWalls: false }, o || {}));

console.log('SnekByte engine — rules');
// ---- config mirrors src/config.py -----------------------------------------
check('grid is 40x30 cells of 20 px (800x600)', cfg.gridWidth === 40 && cfg.gridHeight === 30 && cfg.gridSize === 20);
check('speed table is the original five rates', String(cfg.speedLevels) === '5,8,12,16,20', String(cfg.speedLevels));
check('default speed index is 2 (12 fps)', cfg.defaultSpeedIndex === 2 && E.speedOf(cfg, S()) === 12);
check('WoNQ poop threshold is 5', cfg.wonqModePoopThreshold === 5);
check('the snake starts length 1 at (20,15) heading right',
  cfg.initialSnakeLength === 1 && String(cfg.initialSnakePosition) === '20,15' && String(cfg.initialSnakeDirection) === '1,0');
check('speed names come from the real rates, not an invented table',
  E.speedName(cfg, S()) === 'Normal', E.speedName(cfg, S()));
check('changeSpeed wraps around the table', E.changeSpeed(cfg, { speedIndex: 4 }, 1) === 0);

// ---- reset ----------------------------------------------------------------
let g = E.reset(cfg, [], null);
check('reset(): one segment, score 0, no poops, not over',
  g.snake.positions.length === 1 && g.score === 0 && g.poops.length === 0 && g.gameOver === false);
check('reset(): food comes from the plan when one is given',
  E.reset(cfg, [[7, 3]], null).food.position.join(',') === '7,3');
check('reset(): never leaves food unplaced', E.reset(cfg, [], null).food.position !== null);

// ---- turn -----------------------------------------------------------------
g = E.reset(cfg, [], null);
check('a length-1 snake may reverse', E.turn(g, [-1, 0]) === true && g.snake.direction.join(',') === '-1,0');
g.snake.length = 2; g.snake.direction = [1, 0];
check('a growing snake may NOT reverse into itself (upstream rule)',
  E.turn(g, [-1, 0]) === false && g.snake.direction.join(',') === '1,0');
check('a perpendicular turn is always allowed', E.turn(g, [0, 1]) === true);

// ---- eating and growth ----------------------------------------------------
g = E.reset(cfg, [], null);
g.food.position = [21, 15];
E.step(g, S());
check('eating the food grows the snake and scores one',
  g.score === 1 && g.snake.length === 2, 'score=' + g.score + ' len=' + g.snake.length);
// Upstream quirk the fixture records: the new segment materialises on the NEXT
// move, so on the eating tick `positions` still holds one cell while `length`
// is already 2.  The parity fixture (tick 1: positions [[21,15]], length 2)
// pins this, and the port must not "fix" it.
check('the extra segment appears on the next move (upstream behaviour, fixture-pinned)',
  g.snake.positions.length === 1 && (E.step(g, S()), g.snake.positions.length === 2));
check('eating places the next food on a free cell', String(g.food.position) !== '21,15' && !!g.food.position);
check('an eat is recorded as an event', g.events.some(e => e.type === 'eat'));

// ---- ending caused by the wall -------------------------------------------
g = E.reset(cfg, [], null);
g.food.position = [0, 0];                    // far away, out of the path
for (let i = 0; i < 40 && !g.gameOver; i++) E.step(g, S());
check('running off the grid ends the game with cause=wall',
  g.gameOver === true && g.cause === 'wall', 'cause=' + g.cause + ' at ' + JSON.stringify(g.snake.positions[0]));
check('the wall tick is recorded as an event', g.events.some(e => e.type === 'wall'));

// ---- ending caused by biting yourself -------------------------------------
// A U-shaped body whose tail is NOT the cell the head lands on, so the tail
// move cannot hide the collision.
g = E.reset(cfg, [], null);
g.snake.length = 7;
g.snake.positions = [[5, 5], [6, 5], [6, 4], [5, 4], [4, 4], [4, 5], [3, 5]];
g.snake.direction = [-1, 0];
g.food.position = [30, 20];
E.step(g, S());
check('biting your own body ends the game with cause=self',
  g.gameOver === true && g.cause === 'self', 'cause=' + g.cause);

// ---- WoNQ mode -----------------------------------------------------------
const wonq = S({ wonqMode: true });
g = E.reset(cfg, [], null);
const meals = [[21, 15], [22, 15], [23, 15], [24, 15], [25, 15]];
meals.forEach((m) => { g.food.position = m.slice(); E.step(g, wonq); });
const tailCell = String(g.snake.positions[g.snake.positions.length - 1]);
check('WoNQ: the fifth meal drops one poop', g.poops.length === 1, JSON.stringify(g.poops));
check('WoNQ: the poop lands on the tail cell', g.poops.length === 1 && String(g.poops[0].position) === tailCell,
  String(g.poops[0] && g.poops[0].position) + ' vs tail ' + tailCell);
check('WoNQ: the poop-o-meter resets after dropping', g.shitCounter === 0);
check('WoNQ: the poop drop is recorded as an event', g.events.some(e => e.type === 'poop'));

g = E.reset(cfg, [], null);
g.poops = [{ position: [21, 15] }];          // exactly where the head will land
g.food.position = [0, 0];
E.step(g, S({ wonqMode: true }));
check('WoNQ: stepping on a poop ends the game with cause=poop',
  g.gameOver === true && g.cause === 'poop', 'cause=' + g.cause);

g = E.reset(cfg, [], null);
g.poops = [{ position: [21, 15] }];
g.food.position = [0, 0];
E.step(g, S({ wonqMode: false }));
check('WoNQ off: a poop cell is inert (matches the original)',
  g.gameOver === false && g.cause === null, 'cause=' + g.cause);

// ---- no step once the game is over ---------------------------------------
const over = E.reset(cfg, [], null);
over.food.position = [0, 0];
for (let i = 0; i < 40 && !over.gameOver; i++) E.step(over, S());
const before = JSON.stringify(E.snapshot(over));
E.step(over, S());
check('a finished game does not advance further',
  over.gameOver === true && JSON.stringify(E.snapshot(over)) === before);

// ---- determinism ---------------------------------------------------------
function seededRun(seed) {
  const gg = E.reset(cfg, [], E.createRng(seed));
  const ss = S({ rng: E.createRng(seed ^ 0x5bf03635) });
  const out = [];
  for (let i = 0; i < 25 && !gg.gameOver; i++) { E.step(gg, ss); out.push(E.snapshot(gg)); }
  return JSON.stringify(out);
}
check('the same seed replays the same game (deterministic engine)', seededRun(4242) === seededRun(4242));
check('a different seed gives a different game', seededRun(4242) !== seededRun(99));

// ---- food placement edge cases -------------------------------------------
const tiny = E.cloneConfig({ gridWidth: 1, gridHeight: 1 });
check('a full grid yields no food cell instead of looping forever', E.placeItem([[0, 0]], tiny, [], null) === null);
check('a plan is consumed in order', String(E.placeItem([], cfg, [[1, 1], [2, 2]], null)) === '1,1');
check('a plan cell that is occupied is skipped', String(E.placeItem([[1, 1]], cfg, [[1, 1], [2, 2]], null)) === '2,2');

// ---- environment independence --------------------------------------------
const src = fs.readFileSync(path.join(__dirname, '..', 'js', 'snek-engine.js'), 'utf8');
const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
check('the engine makes no network call', !/fetch\s*\(|XMLHttpRequest|WebSocket/.test(code));
check('the engine requires no native/node module', !/require\s*\(|process\.|__dirname/.test(code));
check('the engine does not depend on pygame or Emscripten (code, not comments)',
  !/pygame|emscripten|SDL/i.test(code));
check('the engine exposes exactly the documented API',
  ['reset', 'turn', 'step', 'settings', 'snapshot', 'speedOf', 'changeSpeed', 'speedName', 'placeItem', 'cloneConfig', 'createRng']
    .every(k => typeof E[k] === 'function'));

// ---- parity against the export of the REAL upstream game ------------------
const fxPath = path.join(__dirname, '..', '..', '..', '..', 'tools', 's10plus', 'a33', 'snekbyte', 'fixtures', 'parity.json');
console.log('SnekByte engine — parity fixture replay');
if (!fs.existsSync(fxPath)) {
  check('upstream parity fixture is present', false, fxPath + ' missing — run gen-parity-fixtures.py');
} else {
  const fx = JSON.parse(fs.readFileSync(fxPath, 'utf8'));
  const pcfg = E.cloneConfig({
    gridWidth: fx.config.gridWidth, gridHeight: fx.config.gridHeight, gridSize: fx.config.gridSize,
    screenWidth: fx.config.screenWidth, screenHeight: fx.config.screenHeight,
    speedLevels: fx.config.speedLevels, defaultSpeedIndex: fx.config.defaultSpeedIndex,
    wonqModePoopThreshold: fx.config.wonqThreshold, initialSnakeLength: fx.config.initialLength,
    initialSnakePosition: fx.config.initialPosition, initialSnakeDirection: fx.config.initialDirection
  });
  const canon = (v) => Array.isArray(v) ? '[' + v.map(canon).join(',') + ']'
    : (v && typeof v === 'object')
      ? '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}'
      : JSON.stringify(v === undefined ? null : v);
  let ticks = 0, diverged = 0;
  fx.scenarios.forEach((sc) => {
    const game = E.reset(pcfg, [], null);
    const st = E.settings(pcfg, { wrapWalls: false, wonqMode: !!sc.wonqMode, foodPlan: [], rng: null });
    sc.steps.forEach((step) => {
      if (step.turn) E.turn(game, step.turn);
      if (step.food) game.food.position = step.food.slice();
      E.step(game, st);
      ticks++;
      if (canon(E.snapshot(game)) !== canon(step.tick)) diverged++;
    });
  });
  check('the port reproduces the recorded upstream game tick for tick',
    diverged === 0 && ticks >= 30, diverged + ' divergence(s) over ' + ticks + ' ticks');
  check('the fixture covers the three endings the original can have',
    new Set(fx.scenarios.map(s => s.steps[s.steps.length - 1].tick.cause)).size === 3,
    fx.scenarios.map(s => s.steps[s.steps.length - 1].tick.cause).join(','));
}

// ---- the PWA shell actually wires this engine -----------------------------
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const ui = fs.readFileSync(path.join(__dirname, '..', 'js', 'snekbyte.js'), 'utf8');
check('index.html loads the engine and the UI in order',
  html.indexOf('js/snek-engine.js') !== -1 && html.indexOf('js/snek-engine.js') < html.indexOf('js/snekbyte.js'));
check('index.html declares the registry app id', /name="nuxel-app-id"\s+content="org\.nuxel\.SnekByte"/.test(html));
check('index.html ships touch controls and all live bindings',
  html.indexOf('<canvas') !== -1 &&
  ['screen','playfield','overlay','score','best','speed','status','meter','meter-count',
   'meter-progress','settings-button','settings-panel','settings-close','settings-done',
   'speed-setting','wonq-setting','grid-setting','help-button','help-panel','help-close',
   'help-done','back-button','pause-button','toast'].every(id=>html.includes('id="'+id+'"')) &&
   ['up','down','left','right'].every(id=>html.includes('data-dir="'+id+'"')));
check('UI contains a five-segment poo meter',
  (html.match(/class="segments"/) || []).length===1 && /aria-valuemax="5"/.test(html));
check('WoNQ default is enabled in phone shell without changing core defaults',
  /cfg\.defaultWonqMode\s*=\s*true/.test(ui) && E.cloneConfig({}).defaultWonqMode===false);
check('UI pauses on lock, home or background',
  ui.includes('visibilitychange') && ui.includes('pagehide') && ui.includes('setPause(true)'));
check('UI prevents continuous animation frames while idle',
  /view\.mode==='playing' && !view\.paused && !view\.dialog/.test(ui));
check('the UI drives the canvas and talks only to the engine module',
  /getContext/.test(ui) && /SnekEngine/.test(ui));
check('the UI never claims successful on-device verification', !/PHYSICAL_TEST_PASSED|ON_DEVICE_VERIFIED/.test(html + ui));
check('the UI has no leftover reference to a removed canvas provenance state',
  !/STATE\.PROVENANCE|drawProvenance/.test(ui));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
