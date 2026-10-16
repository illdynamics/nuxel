// Nuxel SnekByte — engine port of the original Pygame game.
//
// PORT PROVENANCE
//   Upstream: snekbyte-main.zip (see tools/s10plus/a33/snekbyte/UPSTREAM-PROVENANCE.md)
//   This file is a line-for-line behavioural port of the modules the shipped
//   entry point actually uses:
//
//     src/main.py -> src/game_loop.run_game()
//       -> src/game_logic.reset_game_state / update_game_state / _place_item
//       -> src/snake.Snake (reset / turn / move / get_head_position)
//       -> src/food.Food, src/poop.Poop
//       -> src/game_state.GameSettings (speed table, WoNQ toggle)
//       -> src/config (grid, colours, speed table, WoNQ threshold)
//
//   Parity with the original is not asserted by eye: tools/s10plus/a33/snekbyte/
//   gen-parity-fixtures.py runs the REAL upstream modules (with a minimal pygame
//   stub) over scripted input and writes fixtures/parity.json, and
//   tests/test-snek-engine.js replays that script through THIS engine and requires
//   identical state after every tick.
//
//   Deliberate differences from the original (all invisible to game rules):
//     * the RNG is injectable, so a test can pin food placement (the original
//       called random.randint directly);
//     * grid dimensions come from a config object instead of a module constant;
//     * no pygame: rendering lives in snekbyte.js.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SnekEngine = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // src/config.py
  var CONFIG = {
    screenWidth: 800,
    screenHeight: 600,
    gridSize: 20,
    gridWidth: 40,            // SCREEN_WIDTH // GRID_SIZE
    gridHeight: 30,           // SCREEN_HEIGHT // GRID_SIZE
    speedLevels: [5, 8, 12, 16, 20],
    defaultSpeedIndex: 2,
    defaultWonqMode: false,
    wonqModePoopThreshold: 5,
    initialSnakeLength: 1,    // src/snake.py reset(): length = 1
    initialSnakePosition: [20, 15], // (GRID_WIDTH // 2, GRID_HEIGHT // 2)
    initialSnakeDirection: [1, 0],  // RIGHT
    colors: {
      black: [0, 0, 0], white: [255, 255, 255], green: [0, 255, 0], red: [255, 0, 0],
      gray: [128, 128, 128], brown: [139, 69, 19], gold: [255, 215, 0],
      uiBackground: [40, 40, 40], food: [255, 0, 0], grid: [128, 128, 128]
    }
  };

  function cloneConfig(over) {
    var c = JSON.parse(JSON.stringify(CONFIG));
    if (over) Object.keys(over).forEach(function (k) { c[k] = over[k]; });
    if (over && over.gridWidth && over.gridHeight === undefined) c.gridHeight = over.gridHeight || c.gridHeight;
    return c;
  }

  // Deterministic RNG (mulberry32) so the same seed gives the same game.  The
  // original used Python's Mersenne Twister, so a seeded replay across languages
  // is NOT claimed — cross-language parity is proved with an explicit food plan.
  function createRng(seed) {
    var a = (seed >>> 0) || 1;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Food placement.
  //   plan  — an explicit list of [x,y] used first (parity replay / tests);
  //   rng   — otherwise the same reject-sampling as _place_item();
  //   fallback — deterministic first-free-cell scan when a plan or rng cannot
  //              produce a free cell (never reached in practice; documented so
  //              the behaviour is defined instead of looping forever).
  function occupiedKey(list) {
    var m = Object.create(null);
    list.forEach(function (p) { m[p[0] + ',' + p[1]] = true; });
    return m;
  }

  function placeItem(occupied, config, plan, rng) {
    var taken = occupiedKey(occupied);
    while (plan && plan.length) {
      var p = plan.shift();
      if (!taken[p[0] + ',' + p[1]]) return [p[0], p[1]];
    }
    if (rng) {
      for (var attempt = 0; attempt < 1000; attempt++) {
        var x = Math.floor(rng() * config.gridWidth);
        var y = Math.floor(rng() * config.gridHeight);
        if (!taken[x + ',' + y]) return [x, y];
      }
    }
    for (var yy = 0; yy < config.gridHeight; yy++) {
      for (var xx = 0; xx < config.gridWidth; xx++) {
        if (!taken[xx + ',' + yy]) return [xx, yy];
      }
    }
    return null; // the grid is full: the original would loop forever, we stop
  }

  function reset(config, plan, rng) {
    var snake = {
      positions: [[config.initialSnakePosition[0], config.initialSnakePosition[1]]],
      length: config.initialSnakeLength,
      direction: config.initialSnakeDirection.slice()
    };
    var foodPos = placeItem(snake.positions, config, plan, rng);
    return {
      config: config, snake: snake, food: { position: foodPos }, poops: [],
      score: 0, gameOver: false, cause: null, shitCounter: 0, ticks: 0, events: []
    };
  }

  // src/snake.py turn(): a length>1 snake may not reverse into itself.
  function turn(game, dir) {
    var snake = game.snake;
    var d = snake.direction;
    if (snake.length > 1 && (dir[0] * -1 === d[0] && dir[1] * -1 === d[1])) return false;
    snake.direction = [dir[0], dir[1]];
    return true;
  }

  function move(snake) {
    var cur = snake.positions[0];
    var head = [cur[0] + snake.direction[0], cur[1] + snake.direction[1]];
    snake.positions.unshift(head);
    if (snake.positions.length > snake.length) snake.positions.pop();
    return head;
  }

  function same(a, b) { return !!a && !!b && a[0] === b[0] && a[1] === b[1]; }

  // src/game_logic.update_game_state(), statement for statement.
  function step(game, settings) {
    settings = settings || { wonqMode: game.config.defaultWonqMode, foodPlan: null, rng: null };
    if (game.gameOver) return game;
    var config = game.config;
    var snake = game.snake;
    var head = move(snake);

    if (same(head, game.food.position)) {
      snake.length += 1;
      game.score += 1;
      game.events.push({ tick: game.ticks, type: 'eat', at: head.slice(), score: game.score });
      if (settings.wonqMode) {
        game.shitCounter += 1;
        if (game.shitCounter >= config.wonqModePoopThreshold) {
          var poopPos = snake.positions[snake.positions.length - 1];
          game.poops.push({ position: [poopPos[0], poopPos[1]] });
          game.events.push({ tick: game.ticks, type: 'poop', at: [poopPos[0], poopPos[1]] });
          game.shitCounter = 0;
        }
      }
      var occupied = snake.positions.concat(game.poops.map(function (p) { return p.position; }));
      game.food.position = placeItem(occupied, config, settings.foodPlan, settings.rng);
    }

    if (!(head[0] >= 0 && head[0] < config.gridWidth && head[1] >= 0 && head[1] < config.gridHeight)) {
      game.gameOver = true;
      game.cause = 'wall';
      game.events.push({ tick: game.ticks, type: 'wall', at: head.slice() });
    } else if (snake.positions.slice(1).some(function (p) { return same(p, head); })) {
      game.gameOver = true;
      game.cause = 'self';
      game.events.push({ tick: game.ticks, type: 'self', at: head.slice() });
    } else if (settings.wonqMode) {
      for (var i = 0; i < game.poops.length; i++) {
        if (same(game.poops[i].position, head)) {
          game.gameOver = true;
          game.cause = 'poop';
          game.events.push({ tick: game.ticks, type: 'poop', at: head.slice() });
          break;
        }
      }
    }
    game.ticks += 1;
    return game;
  }

  // src/game_state.GameSettings
  function settings(cfg, over) {
    var s = { speedIndex: cfg.defaultSpeedIndex, wonqMode: cfg.defaultWonqMode, foodPlan: null, rng: null };
    if (over) Object.keys(over).forEach(function (k) { s[k] = over[k]; });
    return s;
  }
  function speedOf(cfg, s) { return cfg.speedLevels[s.speedIndex]; }
  function changeSpeed(cfg, s, delta) {
    var n = cfg.speedLevels.length;
    s.speedIndex = ((s.speedIndex + delta) % n + n) % n;
    return s.speedIndex;
  }
  function speedName(cfg, s) {
    // The legacy menu module (src/utils/constants.py) named its own table; the
    // shipped path uses src/config.py where the "speed" is the tick rate.  Names
    // are therefore derived from the rates rather than invented.
    var names = { 5: 'Slowest', 8: 'Slow', 10: 'Slow', 12: 'Normal', 15: 'Normal', 16: 'Fast', 20: 'Fastest', 25: 'Fast', 40: 'Insane' };
    return names[speedOf(cfg, s)] || (speedOf(cfg, s) + ' fps');
  }

  function snapshot(game) {
    return {
      tick: game.ticks, score: game.score, gameOver: game.gameOver, cause: game.cause,
      shitCounter: game.shitCounter,
      snake: { positions: game.snake.positions.map(function (p) { return [p[0], p[1]]; }),
               length: game.snake.length, direction: game.snake.direction.slice() },
      food: game.food.position ? [game.food.position[0], game.food.position[1]] : null,
      poops: game.poops.map(function (p) { return p.position.slice(); })
    };
  }

  return {
    CONFIG: CONFIG, cloneConfig: cloneConfig, createRng: createRng, placeItem: placeItem,
    reset: reset, turn: turn, move: move, step: step, settings: settings,
    speedOf: speedOf, changeSpeed: changeSpeed, speedName: speedName, snapshot: snapshot
  };
}));
