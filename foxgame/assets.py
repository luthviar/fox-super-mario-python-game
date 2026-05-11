"""Sprite-sheet loading.

The supplied sheet is a 3x3 grid of sprites surrounded by a thin white border
and separated/padded by a magenta backdrop (~RGB(234, 65, 246)) with mild
JPEG-style color fringing along sprite edges. We:

  1. Detect the magenta region (skipping the white border).
  2. Walk pixels and clear any close to magenta to alpha=0 (handles fringing).
  3. Slice into a 3x3 grid and trim each cell to its sprite bounding box.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import pygame

# Reference magenta from the sheet (sampled).
_MAGENTA = (234, 65, 246)
# Tight Manhattan-distance threshold: only used for *bbox detection* where
# we want to be sure a pixel is the pure backdrop, not part of a sprite.
_TOL = 90

# 3x3 grid layout of the sheet.
SPRITE_NAMES = [
    ["fox_idle", "fox_run1", "fox_run2"],
    ["fox_jump", "slime", "coin"],
    ["flag", "tile_grass", "tile_stone"],
]


@dataclass(frozen=True)
class Sprites:
    images: Dict[str, pygame.Surface]

    def get(self, name: str) -> pygame.Surface:
        return self.images[name]


def _is_magenta(r: int, g: int, b: int) -> bool:
    """Tight pure-backdrop test (used for bounding-box detection)."""
    return (
        abs(r - _MAGENTA[0]) + abs(g - _MAGENTA[1]) + abs(b - _MAGENTA[2])
    ) <= _TOL


def _is_magentaish(r: int, g: int, b: int) -> bool:
    """Wide test that catches the antialiased fringe too.

    A magenta-fringe pixel has high red, high blue, and low green relative
    to red/blue. Real sprite colors here (orange fox, gold coin, red flag,
    green slime, brown dirt, gray stone) all violate at least one of these,
    so this is safe to apply broadly.
    """
    return r > 140 and b > 140 and g < min(r, b) - 35


def _strip_magenta(surface: pygame.Surface) -> pygame.Surface:
    """Return a new surface with the magenta backdrop and its antialiased
    fringe replaced by alpha=0, then bleed neighboring sprite color into
    the now-transparent edge so smoothscale doesn't pull dark halos."""
    out = surface.convert_alpha()
    w, h = out.get_size()

    # Pass 1: wipe magenta-ish pixels.
    out.lock()
    try:
        for y in range(h):
            for x in range(w):
                r, g, b, _a = out.get_at((x, y))
                if _is_magentaish(r, g, b):
                    out.set_at((x, y), (0, 0, 0, 0))
    finally:
        out.unlock()

    # Pass 2: alpha bleed. For each fully transparent pixel adjacent to an
    # opaque one, copy that neighbor's RGB (keeping alpha=0). This way when
    # the image is later smoothscaled, the interpolation between opaque and
    # transparent pixels picks up *the sprite's* edge color, not black.
    out.lock()
    try:
        for y in range(h):
            for x in range(w):
                r, g, b, a = out.get_at((x, y))
                if a != 0:
                    continue
                # Look at 4-neighbors for an opaque sample.
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        nr, ng, nb, na = out.get_at((nx, ny))
                        if na > 200 and not _is_magentaish(nr, ng, nb):
                            out.set_at((x, y), (nr, ng, nb, 0))
                            break
    finally:
        out.unlock()

    return out


def _detect_magenta_bbox(surface: pygame.Surface) -> pygame.Rect:
    """Find the bounding box of the magenta region (the sheet's interior).

    The screenshot has a thin near-white border outside the magenta canvas.
    Sprites occupy parts of the inner area, so we cannot probe a single line.
    Instead, for each row/column we count magenta pixels and find the first
    row/column where magenta dominates — that's the inside of the border.
    """
    w, h = surface.get_size()

    def row_is_mostly_magenta(y: int) -> bool:
        n = 0
        for x in range(0, w, 4):  # stride for speed
            r, g, b, _ = surface.get_at((x, y))
            if _is_magenta(r, g, b):
                n += 1
        return n > (w // 4) * 0.5  # >50% of sampled pixels

    def col_is_mostly_magenta(x: int) -> bool:
        n = 0
        for y in range(0, h, 4):
            r, g, b, _ = surface.get_at((x, y))
            if _is_magenta(r, g, b):
                n += 1
        return n > (h // 4) * 0.5

    top = 0
    for y in range(h):
        if row_is_mostly_magenta(y):
            top = y
            break
    bottom = h - 1
    for y in range(h - 1, -1, -1):
        if row_is_mostly_magenta(y):
            bottom = y
            break
    left = 0
    for x in range(w):
        if col_is_mostly_magenta(x):
            left = x
            break
    right = w - 1
    for x in range(w - 1, -1, -1):
        if col_is_mostly_magenta(x):
            right = x
            break
    return pygame.Rect(left, top, right - left + 1, bottom - top + 1)


def _trim_to_content(surface: pygame.Surface) -> pygame.Surface:
    """Crop a sprite to its non-transparent bounding box."""
    bbox = surface.get_bounding_rect(min_alpha=8)
    if bbox.width <= 0 or bbox.height <= 0:
        return surface
    cropped = pygame.Surface(bbox.size, pygame.SRCALPHA)
    cropped.blit(surface, (0, 0), bbox)
    return cropped


def load_sprites(path: str | Path) -> Sprites:
    raw = pygame.image.load(str(path))
    sheet = _strip_magenta(raw)
    inner = _detect_magenta_bbox(raw)  # bbox in raw coords == coords in `sheet`
    cell_w = inner.width // 3
    cell_h = inner.height // 3
    images: Dict[str, pygame.Surface] = {}
    for row in range(3):
        for col in range(3):
            name = SPRITE_NAMES[row][col]
            cell_rect = pygame.Rect(
                inner.left + col * cell_w,
                inner.top + row * cell_h,
                cell_w,
                cell_h,
            )
            cell = pygame.Surface(cell_rect.size, pygame.SRCALPHA)
            cell.blit(sheet, (0, 0), cell_rect)
            images[name] = _trim_to_content(cell)
    return Sprites(images=images)


def scale_to_height(surface: pygame.Surface, target_h: int) -> pygame.Surface:
    w, h = surface.get_size()
    if h == target_h:
        return surface
    new_w = max(1, round(w * target_h / h))
    return pygame.transform.smoothscale(surface, (new_w, target_h))


def scale_to_size(surface: pygame.Surface, size: Tuple[int, int]) -> pygame.Surface:
    return pygame.transform.smoothscale(surface, size)
