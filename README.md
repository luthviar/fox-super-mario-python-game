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
There are **six levels** of escalating difficulty:

1. **Level 1** — gentle intro. Wide platforms, well-spaced enemies. 7 slimes.
2. **Level 2** — tighter spacing, occasional 3-wide pits. 10 slimes.
3. **Level 3** — long, multi-tier. Stair climbs and row-4 reward platforms. 12 slimes.
4. **Level 4 — Bandit's Pass** — narrow platforms, 3-wide pits. 14 slimes.
5. **Level 5 — Cliffhanger** — 100 tiles, **sky-island chasm** in the middle (cols 40–60 have no floor — cross by jumping platform to platform; one slip and you fall). 15 slimes.
6. **Level 6 — Final Onslaught** — 110 tiles, two chasms, eight platform-mounted slimes, and a slime guarding the flag. 20 slimes.

**Platform-mounted slimes** patrol on top of floating stones too, not just the
ground — so be careful when landing on a platform you haven't scouted.

## Level select

The title screen has a level selector. Use **← →** (or **1–6**) to choose a
level, then **Enter** to play. After game-over or completing the final level,
you return to the title with your last choice remembered.

Score and lives carry forward between levels when you clear one normally.
Picking a level from the title gives you a fresh score and 3 lives.

All coins, platforms, and flags are **reachability-validated** — nothing in
any level is impossible to reach.

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
