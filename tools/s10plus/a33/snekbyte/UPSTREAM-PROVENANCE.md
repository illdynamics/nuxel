# SnekByte — upstream provenance and port record

> Everything in this directory exists so that the claim "we ported the original
> SnekByte game" can be checked by a stranger with no phone, no network and no
> trust in this repository's prose.

## 1. Where the code came from

| Field | Value |
|-------|-------|
| Archive | `snekbyte-main.zip` |
| Archive size | 22,448 bytes |
| Archive SHA-256 | `97f27d12942c708a7840ea403ebb4d2b9879ba0c6f02040dfaddc799c001f387` |
| Second copy | `snekbyte-main (1).zip` — **byte-identical** (same SHA-256), so it is the same artefact, not a variant |
| Located at | `~/Downloads/` on the build host, verified by direct filesystem inspection before use |
| Imported on | 2026-10-16 |
| Imported by | `import-snekbyte.sh` (re-runnable; refuses an archive whose members do not match the recorded hashes) |
| Members | 28 files, hashes recorded in `upstream-manifest.json` |

The archive was **present** on this machine at import time. It was extracted, each
member was hashed, and the hashes were written to `upstream-manifest.json`. The
imported tree lives verbatim in `upstream/` and `tests/test-snek-parity.py` fails
if a single byte of it changes.

## 2. Licence position (stated, not glossed over)

**The upstream archive contains no `LICENSE`, no `COPYING` and no per-file SPDX
headers.** `README.md` says only that the project is a pygame snake game with a
"WoNQ mode" twist. There is therefore **no licence text to preserve**, and this
document is the record of that fact rather than a claim that a licence was kept.

Consequences that are enforced in this repository:

* `pwa/nuxel-apps/snekbyte/` is a **re-implementation** of the game rules, not a
  copy of upstream source files; upstream `.py` files are not shipped to the
  device.
* `pwa/nuxel-apps/snekbyte/catalog entry` carries the licence string
  *"original SnekByte sources shipped without a licence file — see
  UPSTREAM-PROVENANCE.md"* rather than an invented SPDX identifier.
* If the owner later supplies a licence, update this file, the catalog entry in
  `pwa/nuxel-apps/nuxtore/catalog/package-sources.json` and the PWA footer, and
  the parity suite will still pass (it checks the statement, not the wording).

## 3. What was actually ported

The shipped entry point of the original is:

```
main.py  ->  src/main.py  ->  src/game_loop.run_game()
```

`src/config.py` is the configuration module that path actually uses (grid
geometry, speed table, WoNQ threshold, colours). `snekbyte.py` and
`src/utils/constants.py` are an **older, unused menu implementation** in the same
archive: `snekbyte.py` even has a broken relative import (`from .utils import …`)
that cannot run as a script, and it defines a *second, different* speed table
(10/15/25/40 fps, grid 20×20, 30 px cells). The port follows the **shipped path**
(40×30 grid, 20 px cells, speed table 5/8/12/16/20 fps, default index 2 =
12 fps) and records the dead code so nobody "fixes" the port toward it by mistake.

| Rule (original) | Location upstream | Port |
|-----------------|-------------------|------|
| Snake resets to **length 1** at grid centre, direction RIGHT | `src/snake.py:reset()` | `snek-engine.js:reset()` |
| A length>1 snake may not reverse (`turn()` silently refuses) | `src/snake.py:turn()` | `snek-engine.js:turn()` (returns `false`, callers ignore it exactly as the original does) |
| Movement inserts a head and pops the tail only when over length | `src/snake.py:move()` | `snek-engine.js:move()` |
| Eating: `length += 1`, `score += 1`, then new food on a free cell | `src/game_logic.py:update_game_state()` | `snek-engine.js:step()` |
| WoNQ: every 5th food drops a persistent poop **at the tail cell**, counter resets | `src/game_logic.py` | `snek-engine.js:step()` |
| Game over precedence: wall → self → poop | `src/game_logic.py` | `snek-engine.js:step()` (recorded as `cause`) |
| Speed = tick rate from `SPEED_LEVELS`, default index 2 | `src/config.py`, `src/game_state.py` | `snek-engine.js:CONFIG`, `speedOf()` |
| Menus: main menu (Play / Settings / Quit) + game-over (Retry / Main Menu) | `src/game_loop.py`, `src/ui.py` | `pwa/nuxel-apps/snekbyte/js/snekbyte.js` |

Deliberate differences, all invisible to the rules:

1. the RNG is **injectable** (the original called `random.randint` directly), so a
   test can pin food placement;
2. grid geometry comes from a config object instead of module constants;
3. there is no pygame — rendering is a canvas in `snekbyte.js`;
4. the tick counter and the game-over `cause` are explicit state (the original
   recomputes neither), which is what makes cross-language comparison possible.

## 4. How parity is proved

```
python3 gen-parity-fixtures.py          # runs the REAL upstream modules
node parity-run.js                      # replays the fixture through the port
python3 tests/test-snek-parity.py       # both, plus provenance checks
```

`gen-parity-fixtures.py` imports `upstream/src/*.py` unmodified and drives them
through scripted input that is written to hit every rule: eat + grow + tail trim,
wall collision, self collision, and a WoNQ poop drop followed by a poop collision.
Because the original places food with `random.randint`, the script *states* the
food cell at every tick — a legal game state the player cannot distinguish — so
both languages consume identical input.

`fixtures/parity.json` holds the script **and** the state after every tick, as
produced by the original. `parity-run.js` requires the JS port to match every
field of every tick (score, snake positions, length, direction, food cell, poop
cells, WoNQ counter, game-over flag **and** the cause of death).

Measured result at record time (pygame 2.6.1 present, so the real upstream code ran):

```
eat-grow-trim-wall                20 ticks  score 3  gameOver true  cause wall
self-collision                     7 ticks  score 4  gameOver true  cause self
wonq-poop-drop-and-collision      14 ticks  score 5  gameOver true  cause poop
parity OK: 3 scenarios, 41 ticks, every field identical
```

## 5. Upstream test suite — honest assessment

The archive's own `tests/` directory is **not a working suite for the shipped
code**: `test_core.py`, `test_rendering.py` and `test_input_handling.py` are
placeholders that import a package named `snake_game`, which does not exist in the
archive at all. They are preserved verbatim in `upstream/tests/` (so the archive
is complete) and they are **not** cited as evidence of anything. The evidence is
the parity fixture above, generated from the code the game actually runs.

## 6. What is *not* claimed

* Rendering parity is not claimed: the port draws on a canvas, the original drew
  with pygame. Only the **rules and state** are proved identical.
* Nothing here has been run on the S10+ panel. The acceptance for this briQ is
  `OFFLINE_TESTED`; the on-device verdict needs the owner (manual proof area 34,
  games) and is not asserted.
