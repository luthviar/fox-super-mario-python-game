"""Game entities: Player, Slime, Coin, Flag.

All movement is in floating-point pixels per second; collision is AABB
against the tile grid in level.py. We sweep X then Y to avoid corner
wedging.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import pygame

from .assets import Sprites, scale_to_height
from .level import LevelData, TILE


# --- Tunables ---------------------------------------------------------------
GRAVITY = 1800.0          # px/s^2
MAX_FALL = 900.0          # px/s
WALK_SPEED = 220.0        # px/s
RUN_SPEED = 340.0         # px/s
JUMP_VY = -880.0          # px/s (negative = up). Max height = 880^2/(2*1800) ~= 215 px ~= 4.5 tiles, enough to clear our 4-tile-tall floating platforms.
JUMP_CUT_VY = -260.0      # If the player releases jump while ascending faster than this, clip to it (Mario-style variable jump).
STOMP_BOUNCE_VY = -480.0  # bounce after squashing a slime
COYOTE_TIME = 0.08        # seconds the player can still jump after walking off
JUMP_BUFFER = 0.10        # seconds an early jump press is remembered
SLIME_SPEED = 60.0        # px/s

PLAYER_HEIGHT = 64        # render height in pixels (sprite is scaled to this)
SLIME_HEIGHT = 44
COIN_HEIGHT = 36
FLAG_HEIGHT = 84

# Collision box is narrower than the visual sprite to feel fair.
PLAYER_BOX_W = 36
PLAYER_BOX_H = 56


# --- Helpers ----------------------------------------------------------------

def _collide_x(rect: pygame.Rect, vx: float, level: LevelData) -> float:
    """Move rect by vx pixels along X, clamping against solid tiles.
    Returns the actual delta applied (so caller can know if a wall was hit)."""
    if vx == 0:
        return 0.0
    new_x = rect.x + vx
    test = rect.copy()
    test.x = int(round(new_x))
    if vx > 0:
        # Moving right; check rightmost column.
        right_edge = test.right - 1
        col = right_edge // TILE
        top_row = test.top // TILE
        bot_row = (test.bottom - 1) // TILE
        for ty in range(top_row, bot_row + 1):
            if level.is_solid(col, ty):
                test.right = col * TILE
                break
    else:
        left_edge = test.left
        col = left_edge // TILE
        top_row = test.top // TILE
        bot_row = (test.bottom - 1) // TILE
        for ty in range(top_row, bot_row + 1):
            if level.is_solid(col, ty):
                test.left = (col + 1) * TILE
                break
    delta = test.x - rect.x
    rect.x = test.x
    return delta


def _collide_y(rect: pygame.Rect, vy: float, level: LevelData):
    """Move rect by vy along Y. Returns (delta, hit_ground, hit_ceiling)."""
    if vy == 0:
        return 0.0, False, False
    new_y = rect.y + vy
    test = rect.copy()
    test.y = int(round(new_y))
    hit_ground = False
    hit_ceiling = False
    if vy > 0:
        bot_edge = test.bottom - 1
        row = bot_edge // TILE
        left_col = test.left // TILE
        right_col = (test.right - 1) // TILE
        for tx in range(left_col, right_col + 1):
            if level.is_solid(tx, row):
                test.bottom = row * TILE
                hit_ground = True
                break
    else:
        top_edge = test.top
        row = top_edge // TILE
        left_col = test.left // TILE
        right_col = (test.right - 1) // TILE
        for tx in range(left_col, right_col + 1):
            if level.is_solid(tx, row):
                test.top = (row + 1) * TILE
                hit_ceiling = True
                break
    delta = test.y - rect.y
    rect.y = test.y
    return delta, hit_ground, hit_ceiling


# --- Entities ---------------------------------------------------------------

@dataclass
class Player:
    rect: pygame.Rect
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    facing_right: bool = True
    coyote_timer: float = 0.0
    jump_buffer: float = 0.0
    anim_time: float = 0.0
    invuln_timer: float = 0.0  # short i-frames after losing a life
    spawn: pygame.Rect = field(default=None)  # type: ignore

    @classmethod
    def at_tile(cls, tx: int, ty: int) -> "Player":
        # Place rect so its bottom sits at the tile's bottom edge.
        x = tx * TILE + (TILE - PLAYER_BOX_W) // 2
        y = (ty + 1) * TILE - PLAYER_BOX_H
        rect = pygame.Rect(x, y, PLAYER_BOX_W, PLAYER_BOX_H)
        p = cls(rect=rect)
        p.spawn = rect.copy()
        return p

    def respawn(self):
        self.rect = self.spawn.copy()
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.invuln_timer = 1.2

    def update(
        self,
        dt: float,
        keys,
        jump_pressed: bool,
        jump_held: bool,
        level: LevelData,
    ):
        # Horizontal input.
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = RUN_SPEED if running else WALK_SPEED
        target_vx = (1 if right else 0) - (1 if left else 0)
        target_vx *= speed
        # Snappy ground accel, slightly floatier in air.
        accel = 2400.0 if self.on_ground else 1500.0
        if target_vx > self.vx:
            self.vx = min(target_vx, self.vx + accel * dt)
        elif target_vx < self.vx:
            self.vx = max(target_vx, self.vx - accel * dt)

        if right and not left:
            self.facing_right = True
        elif left and not right:
            self.facing_right = False

        # Jump buffer & coyote time.
        if jump_pressed:
            self.jump_buffer = JUMP_BUFFER
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)

        if self.jump_buffer > 0 and self.coyote_timer > 0:
            self.vy = JUMP_VY
            self.jump_buffer = 0.0
            self.coyote_timer = 0.0
            self.on_ground = False

        # Variable jump: if the player let go of jump while still rising,
        # clip upward velocity so a tap = short hop, a hold = full jump.
        if not jump_held and self.vy < JUMP_CUT_VY:
            self.vy = JUMP_CUT_VY

        # Gravity.
        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)

        # Move.
        _collide_x(self.rect, self.vx * dt, level)
        _, hit_ground, hit_ceiling = _collide_y(self.rect, self.vy * dt, level)
        if hit_ground:
            self.on_ground = True
            self.vy = 0.0
        else:
            self.on_ground = False
        if hit_ceiling:
            self.vy = 0.0

        if self.invuln_timer > 0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)

        if abs(self.vx) > 1.0:
            self.anim_time += dt

    def stomp(self):
        self.vy = STOMP_BOUNCE_VY

    def fell_off_world(self, level: LevelData) -> bool:
        return self.rect.top > level.height_px + 200


@dataclass
class Slime:
    rect: pygame.Rect
    vx: float = -SLIME_SPEED
    vy: float = 0.0
    alive: bool = True
    death_timer: float = 0.0  # squashed visual lasts a beat

    @classmethod
    def at_tile(cls, tx: int, ty: int) -> "Slime":
        w, h = 40, 32
        x = tx * TILE + (TILE - w) // 2
        y = (ty + 1) * TILE - h
        return cls(rect=pygame.Rect(x, y, w, h))

    def update(self, dt: float, level: LevelData):
        if not self.alive:
            self.death_timer = max(0.0, self.death_timer - dt)
            return
        # Gravity.
        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
        # Move X first; if we'd walk off an edge, flip direction.
        delta_x = _collide_x(self.rect, self.vx * dt, level)
        if abs(delta_x) < abs(self.vx * dt) - 0.1:
            # Hit a wall.
            self.vx = -self.vx
        else:
            # About to walk off a ledge? Look at the tile under our forward foot.
            foot_y = (self.rect.bottom) // TILE  # one tile below our feet
            forward_x = (self.rect.right) // TILE if self.vx > 0 else (self.rect.left - 1) // TILE
            if not level.is_solid(forward_x, foot_y):
                self.vx = -self.vx
        _, hit_ground, _ = _collide_y(self.rect, self.vy * dt, level)
        if hit_ground:
            self.vy = 0.0

    def kill(self):
        self.alive = False
        self.death_timer = 0.25


@dataclass
class Coin:
    rect: pygame.Rect
    collected: bool = False
    spin: float = 0.0  # 0..2pi for the squash-and-stretch wobble

    @classmethod
    def at_tile(cls, tx: int, ty: int) -> "Coin":
        size = 32
        x = tx * TILE + (TILE - size) // 2
        y = ty * TILE + (TILE - size) // 2
        return cls(rect=pygame.Rect(x, y, size, size))

    def update(self, dt: float):
        self.spin = (self.spin + dt * 4.0) % (2 * math.pi)


@dataclass
class Flag:
    rect: pygame.Rect          # used for drawing the flag image
    trigger: pygame.Rect       # generous WIN hitbox; the player sprite overhangs its collision box by ~12px on each side, so we pad accordingly

    @classmethod
    def at_tile(cls, tx: int, ty: int) -> "Flag":
        # Visual rect: spans two tiles vertically, anchored at ty's bottom.
        w, h = 40, 80
        x = tx * TILE + (TILE - w) // 2
        y = (ty + 1) * TILE - h
        rect = pygame.Rect(x, y, w, h)
        # Trigger zone: full tile wide plus half a tile of slack on each side,
        # tall enough to catch a player who lands on top of the flag too.
        trigger = pygame.Rect(
            tx * TILE - TILE // 2,
            (ty - 1) * TILE,
            TILE * 2,
            TILE * 2,
        )
        return cls(rect=rect, trigger=trigger)


# --- Rendering helpers ------------------------------------------------------

class Renderer:
    """Holds scaled, oriented sprite copies for fast blits."""

    def __init__(self, sprites: Sprites):
        self.tile_grass = pygame.transform.smoothscale(sprites.get("tile_grass"), (TILE, TILE))
        self.tile_stone = pygame.transform.smoothscale(sprites.get("tile_stone"), (TILE, TILE))

        idle = scale_to_height(sprites.get("fox_idle"), PLAYER_HEIGHT)
        run1 = scale_to_height(sprites.get("fox_run1"), PLAYER_HEIGHT)
        run2 = scale_to_height(sprites.get("fox_run2"), PLAYER_HEIGHT)
        jump = scale_to_height(sprites.get("fox_jump"), PLAYER_HEIGHT)
        # Right-facing originals (they appear right-facing in the sheet) and
        # left-facing flipped copies.
        self.fox = {
            ("idle", True): idle,
            ("idle", False): pygame.transform.flip(idle, True, False),
            ("run1", True): run1,
            ("run1", False): pygame.transform.flip(run1, True, False),
            ("run2", True): run2,
            ("run2", False): pygame.transform.flip(run2, True, False),
            ("jump", True): jump,
            ("jump", False): pygame.transform.flip(jump, True, False),
        }
        self.slime = scale_to_height(sprites.get("slime"), SLIME_HEIGHT)
        self.slime_squashed = pygame.transform.smoothscale(
            self.slime, (self.slime.get_width(), max(8, SLIME_HEIGHT // 3))
        )
        self.coin = scale_to_height(sprites.get("coin"), COIN_HEIGHT)
        self.flag = scale_to_height(sprites.get("flag"), FLAG_HEIGHT)

    def player_image(self, player: Player) -> pygame.Surface:
        if not player.on_ground:
            key = ("jump", player.facing_right)
        elif abs(player.vx) > 8:
            frame = "run1" if (int(player.anim_time * 8) % 2 == 0) else "run2"
            key = (frame, player.facing_right)
        else:
            key = ("idle", player.facing_right)
        return self.fox[key]
