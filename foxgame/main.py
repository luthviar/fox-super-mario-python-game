"""Game entry point: scene loop (Title -> Play -> Win/GameOver) and the
headless smoke-test mode used as a correctness gate.

Run normally:
    python -m foxgame.main

Run smoke test (no window):
    python -m foxgame.main --headless-smoke-test
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import pygame

from .assets import load_sprites, scale_to_height
from .background import Background
from .camera import Camera
from .entities import (
    COIN_HEIGHT,
    Coin,
    Flag,
    Player,
    Renderer,
    Slime,
    TILE,
)
from .hud import HUD
from .level import LevelData, level_count, parse


VIEW_W = 960
VIEW_H = 540
FPS = 60
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

TITLE = "TITLE"
PLAY = "PLAY"
WIN = "WIN"          # level cleared, more levels remain
COMPLETE = "COMPLETE"  # last level cleared
GAMEOVER = "GAMEOVER"


class World:
    """Mutable per-attempt state: player, enemies, coins, score, lives.

    Score and lives carry across levels when `initial_score`/`initial_lives`
    are passed (so finishing a level doesn't reset progress).
    """

    def __init__(self, level: LevelData, initial_score: int = 0, initial_lives: int = 3):
        self.level = level
        self.player = Player.at_tile(*level.player_spawn)
        self.slimes = [Slime.at_tile(tx, ty) for tx, ty in level.slimes]
        self.coins = [Coin.at_tile(tx, ty) for tx, ty in level.coins]
        self.flag = Flag.at_tile(*level.flag)
        self.score = initial_score
        self.lives = initial_lives
        self.won = False

    def update(self, dt: float, keys, jump_pressed: bool, jump_held: bool) -> str:
        """Returns next scene id (PLAY / WIN / GAMEOVER)."""
        self.player.update(dt, keys, jump_pressed, jump_held, self.level)

        for slime in self.slimes:
            slime.update(dt, self.level)

        for coin in self.coins:
            if not coin.collected:
                coin.update(dt)
                if self.player.rect.colliderect(coin.rect):
                    coin.collected = True
                    self.score += 50

        # Player vs slime.
        for slime in self.slimes:
            if not slime.alive:
                continue
            if not self.player.rect.colliderect(slime.rect):
                continue
            # Stomp if the player is moving downward and is mostly above.
            player_bottom = self.player.rect.bottom
            if self.player.vy > 0 and player_bottom - slime.rect.top < 24:
                slime.kill()
                self.player.stomp()
                self.score += 100
            else:
                if self.player.invuln_timer <= 0:
                    self._lose_life()
                    if self.lives <= 0:
                        return GAMEOVER

        # Fell off the world.
        if self.player.fell_off_world(self.level):
            self._lose_life()
            if self.lives <= 0:
                return GAMEOVER

        # Reached the flag.
        if self.player.rect.colliderect(self.flag.trigger):
            self.won = True
            return COMPLETE if self.level.is_last else WIN

        return PLAY

    def _lose_life(self):
        self.lives -= 1
        self.player.respawn()


# --- Rendering --------------------------------------------------------------

def draw_world(surface: pygame.Surface, world: World, camera: Camera, renderer: Renderer, background: Background):
    background.draw(surface, camera.x)

    # Tiles: only draw tiles that are inside the camera view.
    cam_left = int(camera.x)
    cam_right = cam_left + VIEW_W
    first_col = max(0, cam_left // TILE - 1)
    last_col = min(world.level.width_tiles - 1, cam_right // TILE + 1)
    for ty in range(world.level.height_tiles):
        for tx in range(first_col, last_col + 1):
            t = world.level.tile_at(tx, ty)
            if t == "G":
                surface.blit(renderer.tile_grass, camera.apply_xy(tx * TILE, ty * TILE))
            elif t == "S":
                surface.blit(renderer.tile_stone, camera.apply_xy(tx * TILE, ty * TILE))

    # Flag.
    surface.blit(renderer.flag, camera.apply(world.flag.rect))

    # Coins.
    for coin in world.coins:
        if coin.collected:
            continue
        # Wobble the coin horizontally (squash & stretch) for life.
        scale = 0.7 + 0.3 * abs(math.cos(coin.spin))
        if scale < 0.95:
            img = pygame.transform.smoothscale(
                renderer.coin,
                (max(4, int(renderer.coin.get_width() * scale)), renderer.coin.get_height()),
            )
        else:
            img = renderer.coin
        rect = img.get_rect(center=coin.rect.center)
        surface.blit(img, camera.apply(rect))

    # Slimes.
    for slime in world.slimes:
        if not slime.alive and slime.death_timer <= 0:
            continue
        img = renderer.slime if slime.alive else renderer.slime_squashed
        rect = img.get_rect(midbottom=slime.rect.midbottom)
        surface.blit(img, camera.apply(rect))

    # Player (with i-frame flicker).
    player = world.player
    if player.invuln_timer > 0 and int(player.invuln_timer * 20) % 2 == 0:
        pass  # blink off
    else:
        pimg = renderer.player_image(player)
        prect = pimg.get_rect(midbottom=player.rect.midbottom)
        surface.blit(pimg, camera.apply(prect))


# --- Game loop --------------------------------------------------------------

def run(headless: bool = False, smoke_seconds: float = 2.0):
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    pygame.init()
    pygame.display.set_caption("Fox Platformer")
    flags = 0
    screen = pygame.display.set_mode((VIEW_W, VIEW_H), flags)

    sprites = load_sprites(ASSETS_DIR / "spritesheet.png")
    renderer = Renderer(sprites)
    life_icon = scale_to_height(sprites.get("coin"), 24)
    font = pygame.font.SysFont("Helvetica,Arial", 22, bold=True)
    big_font = pygame.font.SysFont("Helvetica,Arial", 64, bold=True)
    hud = HUD(font, big_font, life_icon)
    background = Background(VIEW_W, VIEW_H)

    current_level_idx = 0
    selected_level_idx = 0  # used on the TITLE screen
    level = parse(current_level_idx)
    world = World(level)
    camera = Camera(VIEW_W, VIEW_H, level.width_px, level.height_px)
    camera.follow(world.player.rect)
    camera.x = max(0.0, world.player.rect.centerx - VIEW_W / 2)

    scene = TITLE
    clock = pygame.time.Clock()
    elapsed = 0.0

    def _start_level(idx: int, carry_score: int = 0, carry_lives: int = 3):
        """Load level `idx` and reset world/camera. Returns (level, world, camera)."""
        lvl = parse(idx)
        w = World(lvl, initial_score=carry_score, initial_lives=carry_lives)
        cam = Camera(VIEW_W, VIEW_H, lvl.width_px, lvl.height_px)
        cam.follow(w.player.rect)
        cam.x = max(0.0, w.player.rect.centerx - VIEW_W / 2)
        return lvl, w, cam

    # Smoke-test bookkeeping.
    smoke = {
        "frames": 0,
        "start_x": world.player.rect.x,
        "scenes_seen": {scene},
        "auto_start_done": False,
    }

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        # Cap dt so a long pause doesn't tunnel the player through tiles.
        dt = min(dt, 1 / 30)
        elapsed += dt

        jump_pressed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if scene == TITLE:
                    # Level selector: arrow keys + number keys.
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        selected_level_idx = (selected_level_idx - 1) % level_count()
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        selected_level_idx = (selected_level_idx + 1) % level_count()
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        n = event.key - pygame.K_1
                        if n < level_count():
                            selected_level_idx = n
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        current_level_idx = selected_level_idx
                        level, world, camera = _start_level(current_level_idx)
                        scene = PLAY
                        smoke["scenes_seen"].add(scene)

                elif scene == WIN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Advance to next level, carrying score and lives.
                    current_level_idx += 1
                    level, world, camera = _start_level(
                        current_level_idx,
                        carry_score=world.score,
                        carry_lives=world.lives,
                    )
                    scene = PLAY
                    smoke["scenes_seen"].add(scene)

                elif scene in (COMPLETE, GAMEOVER) and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Return to title for level select.
                    selected_level_idx = 0 if scene == COMPLETE else current_level_idx
                    scene = TITLE
                    smoke["scenes_seen"].add(scene)

                if scene == PLAY and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    jump_pressed = True

        keys = pygame.key.get_pressed()
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]

        if headless and scene == TITLE and not smoke["auto_start_done"]:
            scene = PLAY
            smoke["auto_start_done"] = True
            smoke["scenes_seen"].add(scene)

        # In headless smoke test, simulate "hold right + jump occasionally".
        if headless and scene == PLAY:
            class _FakeKeys:
                def __getitem__(self, k):
                    if k == pygame.K_RIGHT:
                        return True
                    return False
            keys = _FakeKeys()
            if int(elapsed * 4) % 2 == 0 and smoke["frames"] % 30 == 0:
                jump_pressed = True
                jump_held = True

        if scene == PLAY:
            scene = world.update(dt, keys, jump_pressed, jump_held)
            camera.follow(world.player.rect)
            smoke["scenes_seen"].add(scene)

        # Draw.
        draw_world(screen, world, camera, renderer, background)
        hud.draw(screen, world.score, world.lives, level.number, level_count())

        if scene == TITLE:
            hud.title_screen(screen, selected_level_idx, level_count())
        elif scene == WIN:
            next_n = level.number + 1
            hud.message(
                screen,
                f"LEVEL {level.number} CLEAR!",
                f"Score {world.score}.  Press Enter for Level {next_n}.",
            )
        elif scene == COMPLETE:
            hud.message(
                screen,
                "ALL LEVELS COMPLETE!",
                f"Final score {world.score}.  Press Enter to play again from Level 1.",
            )
        elif scene == GAMEOVER:
            hud.message(
                screen,
                "GAME OVER",
                f"Level {level.number}.  Press Enter to try again from Level 1.",
            )

        pygame.display.flip()
        smoke["frames"] += 1

        if headless and elapsed >= smoke_seconds:
            running = False

    if headless:
        # Assertions for the correctness gate.
        sprite_count = len(sprites.images)
        assert sprite_count == 9, f"expected 9 sprites, got {sprite_count}"
        moved = world.player.rect.x - smoke["start_x"]
        assert moved > 30, f"player did not move right under synthetic input (moved {moved}px)"
        assert PLAY in smoke["scenes_seen"], "never entered PLAY scene"
        print(f"OK: sprites={sprite_count} moved_right={moved}px frames={smoke['frames']} scenes={sorted(smoke['scenes_seen'])}")

    pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless-smoke-test", action="store_true", help="Run a 2s headless self-test and exit.")
    parser.add_argument("--smoke-seconds", type=float, default=2.0)
    args = parser.parse_args()
    run(headless=args.headless_smoke_test, smoke_seconds=args.smoke_seconds)


if __name__ == "__main__":
    main()
