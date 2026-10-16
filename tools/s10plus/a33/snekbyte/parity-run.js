#!/usr/bin/env node
// Replay the SnekByte parity fixture through the SHIPPED JavaScript engine.
//
//   node tools/s10plus/a33/snekbyte/parity-run.js [--fixture path] [--quiet]
//
// Reads fixtures/parity.json (generated from the REAL upstream Python game by
// gen-parity-fixtures.py), replays every scenario through
// pwa/nuxel-apps/snekbyte/js/snek-engine.js and requires the state after every
// single tick to be identical — score, snake positions, length, direction, food
// cell, poop cells, WoNQ counter and the game-over flag.
//
// Exit codes: 0 = identical, 1 = divergence (details on stdout), 2 = bad input.
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const args = process.argv.slice(2);
function arg(name, dflt) {
  const i = args.indexOf('--' + name);
  return i === -1 ? dflt : args[i + 1];
}
const fixturePath = arg('fixture', path.join(HERE, 'fixtures', 'parity.json'));
const quiet = args.indexOf('--quiet') !== -1;
const ENGINE = path.join(HERE, '..', '..', '..', '..', 'pwa', 'nuxel-apps', 'snekbyte', 'js', 'snek-engine.js');
const E = require(ENGINE);

const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const config = E.cloneConfig({
  gridWidth: fixture.config.gridWidth,
  gridHeight: fixture.config.gridHeight,
  gridSize: fixture.config.gridSize,
  screenWidth: fixture.config.screenWidth,
  screenHeight: fixture.config.screenHeight,
  speedLevels: fixture.config.speedLevels,
  defaultSpeedIndex: fixture.config.defaultSpeedIndex,
  wonqModePoopThreshold: fixture.config.wonqThreshold,
  initialSnakeLength: fixture.config.initialLength,
  initialSnakePosition: fixture.config.initialPosition,
  initialSnakeDirection: fixture.config.initialDirection
});

// Key order is irrelevant to game state (the fixture is written with sorted keys,
// the engine emits its own order), so comparison is done on a canonical form.
function canon(v) {
  if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']';
  if (v && typeof v === 'object') {
    return '{' + Object.keys(v).sort().map(function (k) { return JSON.stringify(k) + ':' + canon(v[k]); }).join(',') + '}';
  }
  return JSON.stringify(v === undefined ? null : v);
}
function deepEqual(a, b) { return canon(a) === canon(b); }

let failures = 0, ticks = 0;
fixture.scenarios.forEach(function (sc) {
  const game = E.reset(config, [], null);   // food comes from the script
  const settings = E.settings(config, { wonqMode: !!sc.wonqMode, foodPlan: [], rng: null });
  sc.steps.forEach(function (step, i) {
    if (step.turn) E.turn(game, step.turn);
    if (step.food) game.food.position = step.food.slice();
    E.step(game, settings);
    ticks++;
    const got = E.snapshot(game);
    const want = step.tick;
    if (!deepEqual(got, want)) {
      failures++;
      console.log('DIVERGENCE  scenario=' + sc.name + '  step=' + i + '  tick=' + want.tick);
      if (!quiet) {
        console.log('  expected: ' + JSON.stringify(want));
        console.log('  got     : ' + JSON.stringify(got));
      }
    }
  });
  const last = sc.steps[sc.steps.length - 1].tick;
  if (!quiet) {
    console.log('  ' + (failures ? 'FAIL' : 'ok  ') + '  ' + sc.name.padEnd(34, ' ') +
      sc.steps.length + ' ticks  score ' + last.score + '  gameOver ' + last.gameOver +
      '  poops ' + last.poops.length);
  }
});

if (failures) {
  console.log('\n' + failures + ' diverging tick(s) out of ' + ticks + ' — the JS port does NOT match the original');
  process.exit(1);
}
console.log('parity OK: ' + fixture.scenarios.length + ' scenarios, ' + ticks + ' ticks, every field identical' +
  ' (fixture generated with ' + fixture.pygameUsed + ')');
