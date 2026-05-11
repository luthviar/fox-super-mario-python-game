"""Procedural sky + parallax hills + clouds.

Drawn from primitives so we don't need extra art. Cached static layers
(gradient sky, hill silhouettes, cloud surfaces) are blitted per frame
with horizontal offsets driven by the camera.
"""

from __future__ import annotations

import math
import random

import pygame


class Background:
    def __init__(self, view_w: int, view_h: int):
        self.view_w = view_w
        self.view_h = view_h
        self.sky = self._make_sky(view_w, view_h)
        self.hills_far = self._make_hills(view_w * 2, view_h, base_y=int(view_h * 0.78), color=(160, 188, 210), bumpiness=24, seed=7)
        self.hills_near = self._make_hills(view_w * 2, view_h, base_y=int(view_h * 0.86), color=(110, 158, 110), bumpiness=40, seed=42)
        self.clouds = self._make_clouds(view_w * 2, int(view_h * 0.5), seed=3)

    def draw(self, surface: pygame.Surface, camera_x: float):
        surface.blit(self.sky, (0, 0))
        # Cloud layer: very slow parallax.
        cw = self.clouds.get_width()
        cx = -int(camera_x * 0.10) % cw
        surface.blit(self.clouds, (cx - cw, 0))
        surface.blit(self.clouds, (cx, 0))
        # Far hills.
        hw = self.hills_far.get_width()
        hx = -int(camera_x * 0.25) % hw
        surface.blit(self.hills_far, (hx - hw, 0))
        surface.blit(self.hills_far, (hx, 0))
        # Near hills.
        hw = self.hills_near.get_width()
        hx = -int(camera_x * 0.5) % hw
        surface.blit(self.hills_near, (hx - hw, 0))
        surface.blit(self.hills_near, (hx, 0))

    def _make_sky(self, w: int, h: int) -> pygame.Surface:
        sky = pygame.Surface((w, h))
        top = (124, 188, 240)        # crisp blue
        bottom = (255, 220, 196)     # warm peach near horizon
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            pygame.draw.line(sky, (r, g, b), (0, y), (w, y))
        return sky

    def _make_hills(self, w: int, h: int, base_y: int, color, bumpiness: int, seed: int) -> pygame.Surface:
        rng = random.Random(seed)
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        # Smooth rolling silhouette via summed sine waves.
        points = [(0, h)]
        step = 8
        phases = [(rng.uniform(0, 2 * math.pi), rng.uniform(60, 180), rng.uniform(8, bumpiness)) for _ in range(4)]
        for x in range(0, w + 1, step):
            y = base_y
            for phase, period, amp in phases:
                y += amp * math.sin((x / period) + phase)
            points.append((x, int(y)))
        points.append((w, h))
        pygame.draw.polygon(layer, color, points)
        # Slight darkening at the bottom edge for depth.
        shade = pygame.Surface((w, h - base_y), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 18))
        layer.blit(shade, (0, base_y), special_flags=pygame.BLEND_RGBA_SUB)
        return layer

    def _make_clouds(self, w: int, h: int, seed: int) -> pygame.Surface:
        rng = random.Random(seed)
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(16):
            cx = rng.randint(0, w)
            cy = rng.randint(20, max(40, h - 40))
            r = rng.randint(18, 36)
            # A cloud is a few overlapping ellipses.
            for dx in (-r, 0, r, r * 2):
                rr = rng.randint(int(r * 0.7), r)
                pygame.draw.ellipse(
                    layer,
                    (255, 255, 255, 220),
                    pygame.Rect(cx + dx - rr, cy - rr // 2, rr * 2, rr),
                )
        return layer
