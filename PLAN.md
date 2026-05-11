# Fox Platformer — Implementation Plan

A Super-Mario-style 2D platformer in Python + pygame, using the supplied 3×3 sprite sheet (fox hero, slime enemy, coin, flag, grass + stone tiles).

## 1. Project setup
- Create directory layout:
  ```
  supermario-custom/
    assets/
      spritesheet.png        # copied from your screenshot
    foxgame/
      __init__.py
      main.py                # entry point, game loop, scenes
      assets.py              # sprite-sheet loader + slicer + color-key
      level.py               # tile map definition + parser
      entities.py            # Player, Slime, Coin, Flag classes
      camera.py              # side-scrolling camera
      hud.py                 # score / lives / messages
    requirements.txt         # pygame
    README.md                # how to run
  ```
- `requirements.txt` pins `pygame-ce` (community edition — actively maintained, drop-in for pygame, works on Python 3.14).

## 2. Sprite extraction
- Copy `Screenshot 2026-05-11 at 12.59.12.png` → `assets/spritesheet.png`.
- The sheet is a 3×3 grid of tiles on a magenta backdrop. Loader:
  - Loads the PNG with `pygame.image.load`.
  - Samples the top-left pixel to detect the exact magenta key (rather than hard-coding `#FF00FF` — the screenshot might be `#E536FF` or similar). Falls back to nearest-magenta within a small RGB tolerance to handle JPEG-style fringing.
  - Calls `surface.set_colorkey(key)` so blits are transparent.
  - Auto-detects each sprite's bounding box inside its grid cell (trims the magenta padding) so sprites aren't surrounded by dead space.
  - Returns a dict:
    ```
    fox_idle, fox_run1, fox_run2, fox_jump,
    slime, coin, flag, tile_grass, tile_stone
    ```

## 3. Game systems
- **Tile size:** 48 px. Window: 960×540 (20×11 tiles visible). Internal logical resolution scaled with `pygame.transform.scale` if needed.
- **Physics:** simple AABB. Gravity ≈ 1800 px/s², jump impulse ≈ 650 px/s, walk speed 220 px/s, run (shift) 340 px/s. Coyote time 80 ms and jump-buffer 100 ms for forgiving feel.
- **Collision:** sweep X then Y against tile grid; ground flag set when Y collision pushes upward.

## 4. Entities
- **Player (fox):**
  - States: `idle`, `run` (2-frame anim, 8 fps), `jump/fall` (uses fox_jump).
  - Controls: ←/→ or A/D move, Space/Up/W jump, Shift run.
  - Sprite flips horizontally based on facing.
  - 3 lives. Dies on falling out of world or touching slime side-on.
- **Slime:** patrols left/right between edges or until it hits a wall. Stomp from above kills it (+100 score, small bounce). Side-contact = player loses a life and respawns at last checkpoint.
- **Coin:** static, spins via simple horizontal-scale wobble; +50 score on pickup.
- **Flag:** end-of-level goal. Touching it triggers WIN scene.

## 5. Level
- Hand-authored ASCII map (~60 tiles wide) in `level.py`:
  ```
  G = grass tile, S = stone tile, C = coin, E = slime, F = flag, P = player spawn
  ```
- Includes a few floating platforms, a small pit to jump, two slime enemies, a row of coins, ramp of stone blocks up to the flag.

## 6. Background
- Procedurally drawn each frame:
  - Vertical sky gradient (light blue → soft peach near horizon).
  - 2 layers of parallax: distant rolling hills (slow) + clouds (faster). Drawn with `pygame.draw` primitives — no extra assets.

## 7. Scenes & HUD
- Scenes: `TITLE` ("Fox Platformer — press Enter") → `PLAY` → `WIN` or `GAME_OVER` → back to TITLE.
- HUD: top-left score + lives icon (use `coin` sprite scaled small).

## 8. README
- Two-step run instructions:
  ```
  pip install -r requirements.txt
  python -m foxgame.main
  ```

## 9. Verification
- I cannot launch a window in this sandboxed environment to visually QA, so I'll:
  - Add a `--headless-smoke-test` flag that runs ~2 s of the game loop with a virtual surface, asserts sprites loaded, no crashes, player moves on synthetic input. Run that as my correctness gate.
  - Tell you explicitly that visual feel (jump weight, level pacing) needs your eyes — easy to tweak the constants in `entities.py` after you try it.

## What I'll need permission for
- `pip install pygame-ce` (one-time).
- `cp` the screenshot from `/Volumes/ssd1tblq/.TemporaryItems/...` into `assets/`.
- Running the headless smoke test once at the end.
