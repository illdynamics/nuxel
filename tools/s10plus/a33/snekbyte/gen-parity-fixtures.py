#!/usr/bin/env python3
"""Generate the SnekByte parity fixture from the ORIGINAL upstream game logic.

WHAT THIS PROVES
    The Nuxel SnekByte PWA is not a lookalike: it is a re-implementation that must
    reproduce the original's state evolution tick for tick.  This script runs the
    REAL upstream modules (upstream/src/*.py, imported unmodified) over a scripted
    input sequence that is deliberately written to hit every rule:

      * food eaten            (score, growth, new food)
      * tail trimming         (a longer snake moves without growing)
      * WoNQ mode poop drop   (one poop per 5 foods, at the tail cell)
      * wall collision        (leaving the grid ends the game)
      * self collision        (the head entering its own body ends the game)
      * poop collision        (in WoNQ mode, stepping on a poop ends the game)

    It writes fixtures/parity.json containing the script AND the resulting state
    after every tick.  tools/s10plus/a33/snekbyte/parity-run.js replays the same
    script through the JavaScript engine in pwa/nuxel-apps/snekbyte/js/snek-engine.js
    and tests/test-snek-parity.py fails if a single tick differs.

WHY THE SCRIPT IS EXPLICIT
    The original calls random.randint() for food placement, so two languages'
    PRNGs cannot be compared.  Instead the script states where the food is at each
    tick (a legal game state — the player cannot tell the difference) and both
    implementations consume the identical script.

USAGE
    python3 gen-parity-fixtures.py [--out fixtures/parity.json] [--check]
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "upstream"))

import pygame_stub  # noqa: E402

USED_STUB = pygame_stub.install()

from src import config, game_logic, game_state  # noqa: E402
from src.snake import Snake  # noqa: E402
from src.food import Food  # noqa: E402
from src.poop import Poop  # noqa: E402

RIGHT, LEFT, UP, DOWN = (1, 0), (-1, 0), (0, -1), (0, 1)


def why_over(game_data):
    """Why the game ended, using the SAME precedence as game_logic: wall, then
    self, then poop.  The JS engine records this as `cause`, and a divergence in
    the cause is a divergence in the rules, so it is part of the compared state."""
    if not game_data["game_over"]:
        return None
    head = game_data["snake"].get_head_position()
    if not (0 <= head[0] < config.GRID_WIDTH and 0 <= head[1] < config.GRID_HEIGHT):
        return "wall"
    if head in game_data["snake"].positions[1:]:
        return "self"
    for poop in game_data["poops"]:
        if head == poop.position:
            return "poop"
    return "unknown"


def snapshot(game_data):
    """The exact state both engines must agree on after every tick."""
    return {
        "tick": game_data["tick"],
        "cause": why_over(game_data),
        "score": game_data["score"],
        "gameOver": bool(game_data["game_over"]),
        "shitCounter": game_data["shit_counter"],
        "snake": {
            "positions": [[p[0], p[1]] for p in game_data["snake"].positions],
            "length": game_data["snake"].length,
            "direction": list(game_data["snake"].direction),
        },
        "food": list(game_data["food"].position) if game_data["food"].position else None,
        "poops": [[p.position[0], p.position[1]] for p in game_data["poops"]],
    }


class Harness(object):
    """Runs the upstream logic with a deterministic food plan."""

    def __init__(self, wonq):
        self.settings = game_state.GameSettings()
        self.settings.wonq_mode = wonq
        self.plan = []
        game_logic._place_item = self.place_item      # deterministic placement
        self.game = game_logic.reset_game_state(self.settings)
        self.game["tick"] = 0
        self.events = []

    def place_item(self, occupied):
        while self.plan:
            p = self.plan.pop(0)
            if p not in occupied:
                return p
        for y in range(config.GRID_HEIGHT):
            for x in range(config.GRID_WIDTH):
                if (x, y) not in occupied:
                    return (x, y)
        raise SystemExit("grid full")

    def queue_food(self, pos):
        self.plan.append(pos)

    def set_food(self, pos):
        self.game["food"].position = pos

    def turn(self, d):
        self.game["snake"].turn(d)

    def tick(self):
        # The tick counter is part of the state both engines compare.  The engine
        # increments it only when the tick actually did something: update_game_state
        # returns early once the game is over, and a tick after death must not
        # advance the counter (that is what the JS engine does, and what the
        # "no-op after death" scenario pins).
        was_over = self.game["game_over"]
        game_logic.update_game_state(self.game, self.settings)
        if not was_over:
            self.game["tick"] += 1
        return snapshot(self.game)

    # ---- scripted scenarios ------------------------------------------------

    def scenario_eat_and_grow(self, steps):
        """Eat `steps` times in a straight line, queueing food in front of the head."""
        for _ in range(steps):
            head = self.game["snake"].get_head_position()
            ahead = (head[0] + self.game["snake"].direction[0], head[1] + self.game["snake"].direction[1])
            self.queue_food(ahead)
            self.set_food(ahead)
            steps_out = {"turn": None, "food": list(ahead), "tick": self.tick()}
            self.events.append(("eat", steps_out["tick"]["score"]))
            yield steps_out

    def scenario_wander(self, ticks):
        """Move without eating; the tail must trim once the snake has grown."""
        for _ in range(ticks):
            # put the food far away so nothing is eaten
            self.set_food((0, 0) if self.game["snake"].get_head_position() != (0, 0) else (1, 0))
            yield {"turn": None, "food": list(self.game["food"].position), "tick": self.tick()}

    def scenario_wall(self):
        """Head for the right wall until the game ends."""
        for _ in range(config.GRID_WIDTH + 2):
            self.set_food((0, 0))
            snap = {"turn": None, "food": list(self.game["food"].position), "tick": self.tick()}
            yield snap
            if self.game["game_over"]:
                return

    def scenario_self(self):
        """Grow, then loop back into the body."""
        # grow to length 5 while walking right
        for _ in range(4):
            head = self.game["snake"].get_head_position()
            ahead = (head[0] + self.game["snake"].direction[0], head[1] + self.game["snake"].direction[1])
            self.queue_food(ahead)
            self.set_food(ahead)
            yield {"turn": None, "food": list(ahead), "tick": self.tick()}
        # now turn up, left, down: the head meets its own body
        for d in (UP, LEFT, DOWN):
            self.turn(d)
            self.set_food((0, 0))
            yield {"turn": list(d), "food": list(self.game["food"].position), "tick": self.tick()}
            if self.game["game_over"]:
                return

    def scenario_poop(self):
        """Drop a poop, then walk the head onto it."""
        # five eats drop one poop at the tail cell
        for _ in range(5):
            head = self.game["snake"].get_head_position()
            ahead = (head[0] + self.game["snake"].direction[0], head[1] + self.game["snake"].direction[1])
            self.queue_food(ahead)
            self.set_food(ahead)
            yield {"turn": None, "food": list(ahead), "tick": self.tick()}
        if not self.game["poops"]:
            raise SystemExit("scripted WoNQ run did not drop a poop — the scenario is wrong")
        target = self.game["poops"][0].position
        # Walk towards the poop, one axis at a time, WITHOUT ever asking for an
        # illegal reversal: the original's snake.turn() silently refuses a 180°
        # turn when length > 1, so a naive chase would sail into the wall instead
        # of reaching the obstacle.  When the wanted direction is the reverse of
        # the current one, step sideways first (the direction with more room).
        for _ in range(4 * (config.GRID_WIDTH + config.GRID_HEIGHT)):
            head = self.game["snake"].get_head_position()
            if head == target:
                break
            if head[0] != target[0]:
                want = RIGHT if target[0] > head[0] else LEFT
            else:
                want = DOWN if target[1] > head[1] else UP
            cur = self.game["snake"].direction
            if want == (-cur[0], -cur[1]):
                if cur[0] != 0:
                    want = UP if head[1] > 2 else DOWN
                else:
                    want = RIGHT if head[0] < config.GRID_WIDTH - 3 else LEFT
            if want != cur:
                self.turn(want)
            self.set_food((0, 0))
            yield {"turn": list(want), "food": list(self.game["food"].position), "tick": self.tick()}
            if self.game["game_over"]:
                return
        else:
            raise SystemExit("scripted run never reached the poop cell")

    def scenario_noop_after_death(self):
        """Ticks after a game over must be inert (update_game_state returns early)."""
        for _ in range(3):
            yield {"turn": None, "food": list(self.game["food"].position) if self.game["food"].position else None,
                   "tick": self.tick()}


def build():
    random.seed(20261016)     # the plan is explicit; seeding only keeps it stable
    scenarios = []

    h = Harness(wonq=False)
    steps = list(h.scenario_eat_and_grow(3)) + list(h.scenario_wander(6)) + list(h.scenario_wall())
    scenarios.append({"name": "eat-grow-trim-wall", "wonqMode": False, "steps": steps,
                      "expectedEvents": ["eat", "eat", "eat", "wall"]})

    h = Harness(wonq=False)
    steps = list(h.scenario_self())
    scenarios.append({"name": "self-collision", "wonqMode": False, "steps": steps,
                      "expectedEvents": ["eat", "eat", "eat", "eat", "self"]})

    h = Harness(wonq=True)
    steps = list(h.scenario_poop()) + list(h.scenario_noop_after_death())
    scenarios.append({"name": "wonq-poop-drop-and-collision", "wonqMode": True, "steps": steps,
                      "expectedEvents": ["eat", "eat", "eat", "eat", "eat", "poop", "poop-collision"]})

    # assert the script really exercised what it claims
    for sc in scenarios:
        names = [e[0] for e in sc["expectedEvents"]]
        got = [e["tick"]["score"] for e in sc["steps"] if e["tick"]["score"] > 0]
        if "eat" in names and not got:
            raise SystemExit("scenario %s never ate" % sc["name"])
    poop_sc = scenarios[2]
    if not any(s["tick"]["poops"] for s in poop_sc["steps"]):
        raise SystemExit("WoNQ scenario never dropped a poop")
    if not any(s["tick"]["poops"] for s in poop_sc["steps"]):
        raise SystemExit("WoNQ scenario never dropped a poop")
    if poop_sc["steps"][-1]["tick"]["cause"] != "poop":
        raise SystemExit("WoNQ scenario ended with cause=%r, not a poop collision — the script is wrong"
                         % (poop_sc["steps"][-1]["tick"]["cause"],))
    if scenarios[1]["steps"][-1]["tick"]["cause"] != "self":
        raise SystemExit("self-collision scenario ended with cause=%r"
                         % (scenarios[1]["steps"][-1]["tick"]["cause"],))
    if scenarios[0]["steps"][-1]["tick"]["cause"] != "wall":
        raise SystemExit("wall scenario ended with cause=%r"
                         % (scenarios[0]["steps"][-1]["tick"]["cause"],))
    if not scenarios[1]["steps"][-1]["tick"]["gameOver"]:
        raise SystemExit("self-collision scenario did not end the game")
    if scenarios[0]["steps"][-1]["tick"]["gameOver"] is not True:
        raise SystemExit("wall scenario did not end the game")

    fixture = {
        "fixtureSchema": 1,
        "generator": "tools/s10plus/a33/snekbyte/gen-parity-fixtures.py",
        "upstream": "snekbyte-main.zip (see UPSTREAM-PROVENANCE.md)",
        "pygameUsed": "real pygame" if not USED_STUB else "pygame stub (no pygame in this environment)",
        "config": {
            "gridWidth": config.GRID_WIDTH, "gridHeight": config.GRID_HEIGHT, "gridSize": config.GRID_SIZE,
            "screenWidth": config.SCREEN_WIDTH, "screenHeight": config.SCREEN_HEIGHT,
            "speedLevels": list(config.SPEED_LEVELS), "defaultSpeedIndex": config.DEFAULT_SPEED_INDEX,
            "wonqThreshold": config.WONQ_MODE_POOP_THRESHOLD,
            "initialLength": Snake().length, "initialPosition": list(Snake().positions[0]),
            "initialDirection": list(Snake().direction),
        },
        "scenarios": scenarios,
    }
    return fixture


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "fixtures", "parity.json"))
    ap.add_argument("--check", action="store_true", help="compare with the committed fixture, write nothing")
    args = ap.parse_args()

    fixture = build()
    text = json.dumps(fixture, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not os.path.exists(args.out):
            print("MISSING fixture %s" % args.out)
            return 1
        # `pygameUsed` records what this HOST happened to provide; the game
        # rules never consume pygame.  Comparing it verbatim made the parity
        # check fail on a host without pygame even though all 41 ticks were
        # byte-identical.  Compare the rules/state only and report the host
        # fact separately.
        old_doc = json.load(open(args.out))
        old_cmp = {k: v for k, v in old_doc.items() if k != "pygameUsed"}
        new_cmp = {k: v for k, v in fixture.items() if k != "pygameUsed"}
        if old_cmp != new_cmp:
            print("DRIFT: the committed fixture no longer matches a fresh run of the upstream logic")
            return 1
        print("fixture matches a fresh run of the upstream logic (%d scenarios, %d ticks)"
              % (len(fixture["scenarios"]), sum(len(s["steps"]) for s in fixture["scenarios"])))
        print("fixture's recorded pygame: %s (this host: %s; not part of the rule comparison)"
              % (old_doc.get("pygameUsed"), fixture["pygameUsed"]))
        return 0
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(text)
    print("wrote %s (%d scenarios, %d ticks, pygame=%s)"
          % (args.out, len(fixture["scenarios"]),
             sum(len(s["steps"]) for s in fixture["scenarios"]), fixture["pygameUsed"]))
    for s in fixture["scenarios"]:
        print("  %-32s %3d steps  last score %d  gameOver %s  poops %d"
              % (s["name"], len(s["steps"]), s["steps"][-1]["tick"]["score"],
                 s["steps"][-1]["tick"]["gameOver"], len(s["steps"][-1]["tick"]["poops"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
