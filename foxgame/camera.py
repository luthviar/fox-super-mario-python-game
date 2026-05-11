"""Side-scrolling camera that keeps the player roughly centered."""

from __future__ import annotations

import pygame


class Camera:
    def __init__(self, view_w: int, view_h: int, world_w: int, world_h: int):
        self.view_w = view_w
        self.view_h = view_h
        self.world_w = world_w
        self.world_h = world_h
        self.x = 0.0
        self.y = 0.0

    def follow(self, target_rect: pygame.Rect):
        # Center on target horizontally, but lock vertically to the world
        # (level fits in view height, so no vertical scrolling needed).
        target_x = target_rect.centerx - self.view_w / 2
        # Smooth lerp so the camera doesn't snap.
        self.x += (target_x - self.x) * 0.15
        # Clamp.
        self.x = max(0.0, min(self.x, self.world_w - self.view_w))
        # Anchor camera so the world's bottom aligns with the view's bottom.
        self.y = max(0.0, self.world_h - self.view_h)

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-int(self.x), -int(self.y))

    def apply_xy(self, x: int, y: int) -> tuple[int, int]:
        return x - int(self.x), y - int(self.y)
