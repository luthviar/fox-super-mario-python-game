"""HUD: score, lives, and centered overlay messages."""

from __future__ import annotations

import pygame


class HUD:
    def __init__(self, font: pygame.font.Font, big_font: pygame.font.Font, life_icon: pygame.Surface):
        self.font = font
        self.big_font = big_font
        self.life_icon = life_icon

    def draw(self, surface: pygame.Surface, score: int, lives: int, level_number: int | None = None, level_total: int | None = None):
        # Drop-shadowed text for legibility against the sky.
        score_text = f"SCORE  {score:05d}"
        self._draw_shadow(surface, self.font, score_text, (16, 12))

        # Center: level indicator.
        if level_number is not None and level_total is not None:
            level_text = f"LEVEL  {level_number}/{level_total}"
            level_surf = self.font.render(level_text, True, (255, 255, 255))
            cx = surface.get_width() // 2 - level_surf.get_width() // 2
            self._draw_shadow(surface, self.font, level_text, (cx, 12))

        # Lives icons (coin) on the right.
        x = surface.get_width() - 16
        for i in range(lives):
            icon = self.life_icon
            x -= icon.get_width() + 4
            surface.blit(icon, (x, 12))

    def title_screen(self, surface: pygame.Surface, selected_level: int, total_levels: int):
        """Title overlay with a level selector."""
        sw, sh = surface.get_size()
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 130))
        surface.blit(dim, (0, 0))

        # Game title (top third)
        title = "FOX PLATFORMER"
        ts = self.big_font.render(title, True, (255, 235, 140))
        tshadow = self.big_font.render(title, True, (20, 20, 20))
        tx = sw // 2 - ts.get_width() // 2
        ty = int(sh * 0.20)
        surface.blit(tshadow, (tx + 3, ty + 3))
        surface.blit(ts, (tx, ty))

        # Level selector row: < 1 . 2 . 3 . 4 . 5 . 6 >
        # The selected number is bigger and bright; others are dim.
        ly = int(sh * 0.50)
        # Compute total width of the row to center it.
        num_w = 70
        chevron_w = 60
        total_w = chevron_w * 2 + num_w * total_levels
        start_x = sw // 2 - total_w // 2

        # Left chevron
        left = "<"
        ls = self.big_font.render(left, True, (255, 255, 255))
        lsh = self.big_font.render(left, True, (20, 20, 20))
        cx = start_x + (chevron_w - ls.get_width()) // 2
        surface.blit(lsh, (cx + 3, ly + 3))
        surface.blit(ls, (cx, ly))

        # Numbers
        for i in range(total_levels):
            n = str(i + 1)
            if i == selected_level:
                color = (255, 220, 60)
                font = self.big_font
            else:
                color = (200, 200, 200)
                font = self.font
            ns = font.render(n, True, color)
            nsh = font.render(n, True, (20, 20, 20))
            nx = start_x + chevron_w + i * num_w + (num_w - ns.get_width()) // 2
            # Center vertically relative to the big chevrons.
            ny = ly + (ls.get_height() - ns.get_height()) // 2
            surface.blit(nsh, (nx + 2, ny + 2))
            surface.blit(ns, (nx, ny))
            # Underline the selected one.
            if i == selected_level:
                ux = start_x + chevron_w + i * num_w + 8
                uy = ly + ls.get_height() + 6
                pygame.draw.rect(surface, (255, 220, 60), (ux, uy, num_w - 16, 4))

        # Right chevron
        right = ">"
        rs = self.big_font.render(right, True, (255, 255, 255))
        rsh = self.big_font.render(right, True, (20, 20, 20))
        rx = start_x + chevron_w + total_levels * num_w + (chevron_w - rs.get_width()) // 2
        surface.blit(rsh, (rx + 3, ly + 3))
        surface.blit(rs, (rx, ly))

        # Instructions
        lines = [
            "<- ->  or  1-{}  to select level     Enter to play".format(total_levels),
            "Arrows / WASD move     Space jump (hold = higher)     Shift run     Esc quit",
        ]
        ty = int(sh * 0.78)
        for line in lines:
            ls_ = self.font.render(line, True, (240, 240, 240))
            lsh_ = self.font.render(line, True, (20, 20, 20))
            x = sw // 2 - ls_.get_width() // 2
            surface.blit(lsh_, (x + 2, ty + 2))
            surface.blit(ls_, (x, ty))
            ty += ls_.get_height() + 6

    def message(self, surface: pygame.Surface, big: str, small: str = ""):
        sw, sh = surface.get_size()
        # Dim the screen.
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 110))
        surface.blit(dim, (0, 0))
        big_surf = self.big_font.render(big, True, (255, 255, 255))
        big_shadow = self.big_font.render(big, True, (20, 20, 20))
        cx = sw // 2 - big_surf.get_width() // 2
        cy = sh // 2 - big_surf.get_height() // 2
        surface.blit(big_shadow, (cx + 3, cy + 3))
        surface.blit(big_surf, (cx, cy))
        if small:
            small_surf = self.font.render(small, True, (240, 240, 240))
            small_shadow = self.font.render(small, True, (20, 20, 20))
            sx = sw // 2 - small_surf.get_width() // 2
            sy = cy + big_surf.get_height() + 14
            surface.blit(small_shadow, (sx + 2, sy + 2))
            surface.blit(small_surf, (sx, sy))

    def _draw_shadow(self, surface, font, text, pos):
        x, y = pos
        shadow = font.render(text, True, (20, 20, 20))
        body = font.render(text, True, (255, 255, 255))
        surface.blit(shadow, (x + 2, y + 2))
        surface.blit(body, (x, y))
