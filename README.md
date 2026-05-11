# Fox Platformer

A small Super-Mario-style 2D platformer built with Python + `pygame-ce`.
The fox runs, jumps, stomps slimes, collects coins, and races for the flag.

## Setup

```sh
pip install -r requirements.txt
```

> The project pins `pygame-ce` (community edition) which has prebuilt wheels
> for current Python versions, including 3.14 on Apple Silicon. The original
> `pygame` package may not.

## Run

```sh
python -m foxgame.main
```

## Controls

- **Move:** ← / → or A / D
- **Jump:** Space, ↑, or W. **Tap = short hop, hold = full-height jump.** Coyote-time and jump-buffer keep timing forgiving.
- **Run:** hold Shift
- **Quit:** Esc

## Goal

Run right, stomp slimes from above, grab coins, reach the flag. Three lives.
There are **ten levels** of escalating difficulty:

1. **Level 1** — gentle intro. Wide platforms, well-spaced enemies. 7 slimes.
2. **Level 2** — tighter spacing, occasional 3-wide pits. 10 slimes.
3. **Level 3** — long, multi-tier. Stair climbs and row-4 reward platforms. 12 slimes.
4. **Level 4 — Bandit's Pass** — narrow platforms, 3-wide pits. 14 slimes.
5. **Level 5 — Cliffhanger** — 100 tiles, **sky-island chasm** mid-level. 15 slimes.
6. **Level 6 — Final Onslaught** — 110 tiles, two chasms, the first really mean level. 20 slimes.
7. **Level 7 — Tightrope Walk** — 115 tiles, mostly 1–2 tile platforms; chasm with zig-zag of single-tile islands at alternating heights. 21 slimes.
8. **Level 8 — Triple Trouble** — 125 tiles, **three back-to-back 10-wide chasms**. Each chasm has a 3-island sky bridge; recovery strips between. 24 slimes (including slimes on the chasm islands themselves).
9. **Level 9 — Slime Swarm** — 125 tiles, enemy density max. Slimes packed in clusters of three on every ground strip. One mid-level breather chasm. 33 slimes.
10. **Level 10 — Master Trial** — 150 tiles, the longest level. Combines every challenge: 12-wide mega-chasm, an 8-wide second chasm, the only **row-3 reward platform** in the game (with its own guardian), and 33 slimes including one right next to the flag.

**Platform-mounted slimes** patrol on top of floating stones too — be careful
when landing on a platform you haven't scouted, especially on chasm islands.

## Level select

The title screen has a level selector. Use **← →** (or **1–9** for direct
jump; level 10 reachable via arrows) to choose a level, then **Enter** to play.
After game-over or completing the final level, you return to the title with
your last choice remembered.

Score and lives carry forward between levels when you clear one normally.
Picking a level from the title gives you a fresh score and 3 lives.

All coins, platforms, and flags are **physics-grounded reachability-validated** —
the validator uses the actual player jump arc (4.48-tile max rise, ~7-tile
max horizontal at run speed) so nothing in any level is impossible to reach.

## Editing levels

Levels are defined declaratively in `build_levels.py`. To tweak or add a
level, edit its `LevelSpec` and rerun the script — it validates reachability
and prints the LEVELS list ready to paste into `foxgame/level.py`. Pass
`--only-new` to emit just L7-L10 (handy when appending).

## Project layout

```
assets/
  spritesheet.png         # the supplied 3x3 sprite sheet
foxgame/
  assets.py               # sheet loader, magenta-key removal with tolerance, auto-trim
  background.py           # procedural sky + parallax hills + clouds
  camera.py               # smooth side-scrolling camera
  entities.py             # Player, Slime, Coin, Flag, AABB collision, animation
  hud.py                  # score, lives, overlay messages
  level.py                # ASCII tile map and parser
  main.py                 # scene loop + headless smoke test
```

## Headless self-test

Used as a correctness gate when no display is available:

```sh
python -m foxgame.main --headless-smoke-test
```

Asserts that all 9 sprites loaded, the player moves right under synthetic input,
and the PLAY scene was entered. Prints `OK: ...` on success.

## Tweaking the feel

Numbers worth playing with live in `foxgame/entities.py`:

- `GRAVITY`, `JUMP_VY` — jump arc weight
- `WALK_SPEED`, `RUN_SPEED` — horizontal movement
- `COYOTE_TIME`, `JUMP_BUFFER` — input forgiveness
- `SLIME_SPEED` — enemy patrol pace

---

## ❤️ Support the project

If you enjoyed the game, consider buying me a coffee!

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal)](https://paypal.me/labsluth/1.9USD)

**››› [paypal.me/labsluth](https://paypal.me/labsluth/1.9USD) ‹‹‹** — suggested tip: **$1.9 USD**
