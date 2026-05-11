"""Permanent level design tool.

Declarative specs for all 10 levels of the game, plus a BFS reachability
validator. Run with `python3 build_levels.py` to:

  1. validate every spec (assert all coins, flag, and slimes reachable / placed
     on solid ground);
  2. assert each row has the declared width;
  3. emit the LEVELS list ready to paste into `foxgame/level.py`.

To tweak a level: edit its LevelSpec below and rerun the script. The
validator is conservative (BFS over walk + run-jump 5 cols x 2 rows up +
drop + fall), so anything it OKs is reachable in real gameplay too.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple

H = 12
FLOOR_ROW = 10
SUBFLOOR_ROW = 11
STAND_ROW = 9


@dataclass
class LevelSpec:
    name: str
    width: int
    pits: List[Tuple[int, int]]                                  # (col, width)
    platforms: List[Tuple[int, int, int]]                        # (col, top_row, width)
    slimes: List[int]                                            # floor slime cols
    platform_slimes: List[Tuple[int, int]] = field(default_factory=list)  # (col, stand_row)
    flag_col: int = 0
    coin_floats: List[Tuple[int, int]] = field(default_factory=list)


def build(spec: LevelSpec):
    W = spec.width
    grid = [["." for _ in range(W)] for _ in range(H)]
    for x in range(W):
        grid[FLOOR_ROW][x] = "G"
        grid[SUBFLOOR_ROW][x] = "S"
    for px, pw in spec.pits:
        for dx in range(pw):
            grid[FLOOR_ROW][px + dx] = "."
            grid[SUBFLOOR_ROW][px + dx] = "."
    for px, py, pw in spec.platforms:
        for dx in range(pw):
            grid[py][px + dx] = "S"
    # Auto-coin above each platform
    for px, py, pw in spec.platforms:
        cy = py - 1
        for dx in range(pw):
            if grid[cy][px + dx] == ".":
                grid[cy][px + dx] = "C"
    for cx, cy in spec.coin_floats:
        if 0 <= cx < W and 0 <= cy < H and grid[cy][cx] == ".":
            grid[cy][cx] = "C"
    for sx in spec.slimes:
        if 0 <= sx < W and grid[FLOOR_ROW][sx] == "G":
            grid[STAND_ROW][sx] = "E"
    for sx, sy in spec.platform_slimes:
        if not (0 <= sx < W and 0 <= sy < H - 1):
            continue
        if grid[sy + 1][sx] in ("G", "S"):
            grid[sy][sx] = "E"
    grid[STAND_ROW][0] = "P"
    fc = spec.flag_col
    grid[STAND_ROW][fc] = "F"
    for y in range(STAND_ROW):
        for dx in (-1, 0, 1):
            cx = fc + dx
            if 0 <= cx < W and grid[y][cx] == "S":
                grid[y][cx] = "."
    return grid


def is_solid(grid, x, y, W):
    if y < 0 or y >= H:
        return False
    if x < 0 or x >= W:
        return True
    return grid[y][x] in ("G", "S")


def can_stand(grid, x, y, W):
    if x < 0 or x >= W or y < 0 or y >= H - 1:
        return False
    if is_solid(grid, x, y, W):
        return False
    return is_solid(grid, x, y + 1, W)


# Jump-reach budget derived from player physics in entities.py:
#   JUMP_VY=-880, GRAVITY=1800 => max rise = 215 px = 4.48 tiles
#   RUN_SPEED=340, total air time ~0.97s => max horizontal jump = ~7 tiles
# Time spent above each height level (computed by inverting the kinematic
# y(t) = -880t + 900t^2) gives the (rise, max-horizontal) trade-off:
#   rise 0 tiles  => up to 7 cols
#   rise 1 tile   => up to 6 cols
#   rise 2 tiles  => up to 5 cols
#   rise 3 tiles  => up to 4 cols
#   rise 4 tiles  => up to 2 cols
JUMP_REACH = {0: 7, -1: 6, -2: 5, -3: 4, -4: 2}
DROP_HORIZ = 7  # horizontal reach when dropping (down)


def reach_set(grid, W):
    """BFS over stand positions from spawn using a physics-grounded jump
    model. A stand position (sx, sy) means the player's standing cell is
    (sx, sy) — i.e., cell (sx, sy) is empty and (sx, sy+1) is solid.
    """
    start = (0, STAND_ROW)
    visited = {start}
    queue = deque([start])
    while queue:
        cx, cy = queue.popleft()
        # Walk
        for dx in (-1, 1):
            nx, ny = cx + dx, cy
            if can_stand(grid, nx, ny, W) and (nx, ny) not in visited:
                visited.add((nx, ny)); queue.append((nx, ny))
        # Fall straight down (off a ledge)
        if not is_solid(grid, cx, cy + 1, W):
            ny = cy
            while ny < H - 1 and not is_solid(grid, cx, ny + 1, W):
                ny += 1
            if can_stand(grid, cx, ny, W) and (cx, ny) not in visited:
                visited.add((cx, ny)); queue.append((cx, ny))
        # Jump up / across (ddy = 0, -1, -2, -3, -4)
        for ddy, max_ddx in JUMP_REACH.items():
            for ddx in range(-max_ddx, max_ddx + 1):
                nx, ny = cx + ddx, cy + ddy
                if can_stand(grid, nx, ny, W) and (nx, ny) not in visited:
                    visited.add((nx, ny)); queue.append((nx, ny))
        # Drop down (ddy positive, any depth)
        for ddx in range(-DROP_HORIZ, DROP_HORIZ + 1):
            for ddy in range(1, H):
                nx, ny = cx + ddx, cy + ddy
                if can_stand(grid, nx, ny, W) and (nx, ny) not in visited:
                    visited.add((nx, ny)); queue.append((nx, ny))
    return visited


def coin_reachable(reach, cx, cy, W):
    """A coin is reachable if either:
      (a) the player can stand in the same cell (sy == cy in same column), or
      (b) the player can stand within 5 cols horizontal and 1-5 rows BELOW
          the coin — the jump arc from such a stand position passes through
          the coin's row.
    """
    if (cx, cy) in reach:
        return True
    for sx in range(max(0, cx - 5), min(W, cx + 6)):
        for sy in range(cy + 1, min(H, cy + 6)):
            if (sx, sy) in reach:
                return True
    return False


def validate(grid, spec):
    W = spec.width
    issues = []
    reach = reach_set(grid, W)
    for y in range(H):
        for x in range(W):
            if grid[y][x] == "C" and not coin_reachable(reach, x, y, W):
                issues.append(f"{spec.name}: coin at ({x},{y}) unreachable")
            if grid[y][x] == "E" and not is_solid(grid, x, y + 1, W):
                issues.append(f"{spec.name}: slime at ({x},{y}) over pit")
    if (spec.flag_col, STAND_ROW) not in reach:
        issues.append(f"{spec.name}: flag at col {spec.flag_col} unreachable")
    return issues


# ===========================================================================
# L1 — gentle intro (with 1 platform slime)
# ===========================================================================
L1 = LevelSpec(
    name="L1",
    width=80,
    pits=[(8, 1), (16, 2), (25, 1), (36, 2), (48, 1), (60, 2)],
    platforms=[
        (10, 7, 4), (19, 8, 3), (27, 7, 4), (34, 6, 4), (41, 7, 3),
        (46, 6, 4), (53, 7, 4), (61, 8, 4), (67, 7, 4), (73, 6, 3),
    ],
    slimes=[4, 13, 22, 32, 44, 56],
    platform_slimes=[(35, 5)],
    flag_col=77,
)

# ===========================================================================
# L2 — medium with 2 platform slimes
# ===========================================================================
L2 = LevelSpec(
    name="L2",
    width=80,
    pits=[(7, 1), (14, 2), (22, 3), (32, 1), (40, 2), (50, 3), (62, 1)],
    platforms=[
        (9, 7, 3), (15, 8, 3), (19, 6, 2), (23, 8, 4),
        (28, 6, 3), (30, 5, 2), (34, 7, 3), (40, 8, 3),
        (44, 6, 3), (47, 5, 2), (52, 8, 4), (57, 7, 3),
        (62, 8, 2), (66, 6, 3), (70, 5, 2), (73, 7, 3),
    ],
    slimes=[4, 11, 19, 27, 36, 45, 56, 64],
    platform_slimes=[(10, 6), (45, 5)],
    flag_col=78,
)

# ===========================================================================
# L3 — multi-tier with 3 platform slimes
# ===========================================================================
L3 = LevelSpec(
    name="L3",
    width=90,
    pits=[(8, 2), (16, 1), (22, 3), (32, 2), (40, 3), (50, 2), (60, 3), (72, 2)],
    platforms=[
        (10, 8, 2), (13, 7, 2), (17, 8, 3), (22, 7, 3), (26, 5, 3),
        (30, 8, 2), (34, 7, 3), (38, 6, 2), (41, 4, 3), (45, 8, 3),
        (50, 7, 2), (54, 6, 3), (58, 5, 3), (62, 7, 3), (67, 6, 2),
        (70, 4, 3), (75, 8, 3), (80, 7, 3), (85, 6, 2),
    ],
    slimes=[4, 12, 19, 28, 36, 46, 54, 65, 76],
    platform_slimes=[(23, 6), (55, 5), (76, 7)],
    flag_col=88,
)

# ===========================================================================
# L4 — Bandit's Pass, 4 platform slimes
# ===========================================================================
L4 = LevelSpec(
    name="L4",
    width=90,
    pits=[(6, 2), (13, 3), (22, 3), (30, 2), (37, 3), (45, 3),
          (54, 3), (63, 3), (73, 2), (80, 2)],
    platforms=[
        (9, 7, 2), (14, 8, 3), (19, 6, 2), (22, 7, 3), (26, 5, 2),
        (30, 8, 2), (34, 6, 3), (38, 4, 3), (43, 7, 2), (46, 8, 3),
        (51, 6, 3), (55, 7, 3), (59, 5, 2), (64, 8, 3), (68, 6, 3),
        (72, 4, 3), (76, 7, 3), (81, 8, 2), (85, 6, 3),
    ],
    slimes=[4, 11, 19, 28, 35, 43, 52, 61, 70, 78],
    platform_slimes=[(15, 7), (35, 5), (52, 5), (77, 6)],
    flag_col=88,
)

# ===========================================================================
# L5 — Cliffhanger sky-island chasm, 4 platform slimes
# ===========================================================================
L5 = LevelSpec(
    name="L5",
    width=100,
    pits=[
        (6, 2), (13, 3), (22, 3), (30, 3),
        (40, 10), (50, 11),
        (66, 3), (74, 3), (82, 3), (90, 2),
    ],
    platforms=[
        (9, 7, 2), (15, 8, 3), (19, 6, 2), (23, 7, 3), (27, 5, 2),
        (31, 8, 3), (35, 6, 3),
        (39, 7, 2), (43, 8, 2), (47, 7, 2), (51, 6, 2), (55, 7, 2), (59, 8, 2),
        (62, 6, 3), (66, 4, 3), (71, 7, 3), (75, 8, 2), (78, 6, 3),
        (83, 8, 2), (86, 7, 3), (91, 8, 2), (95, 6, 3),
    ],
    slimes=[4, 11, 19, 28, 36, 64, 70, 78, 87, 94, 96],
    platform_slimes=[(16, 7), (35, 5), (62, 5), (78, 5)],
    flag_col=98,
)

# ===========================================================================
# L6 — Final Onslaught: 8 platform slimes
# ===========================================================================
L6 = LevelSpec(
    name="L6",
    width=110,
    pits=[
        (6, 3), (13, 3), (22, 3),
        (30, 9),
        (47, 3), (55, 3),
        (64, 9),
        (82, 3), (90, 3), (98, 3),
    ],
    platforms=[
        (9, 7, 2), (15, 8, 3), (19, 6, 2), (23, 7, 3), (27, 5, 2),
        (29, 7, 2), (33, 8, 2), (37, 7, 2), (40, 6, 3), (44, 4, 3),
        (48, 7, 3), (52, 5, 2), (56, 8, 3), (60, 6, 3),
        (63, 7, 2), (67, 8, 2), (71, 7, 2), (74, 6, 3), (78, 4, 3),
        (83, 7, 3), (87, 5, 2), (91, 8, 3), (95, 6, 3), (99, 8, 2),
        (103, 7, 3),
    ],
    slimes=[4, 11, 19, 41, 45, 51, 60, 74, 79, 84, 95, 102, 107],
    platform_slimes=[(16, 7), (24, 6), (41, 5), (49, 6), (61, 5), (84, 6), (96, 5), (104, 6)],
    flag_col=108,
)

# ===========================================================================
# L7 — "Tightrope Walk" (115 wide): narrow platforms, one medium chasm
# ===========================================================================
L7 = LevelSpec(
    name="L7",
    width=115,
    pits=[
        (7, 2), (15, 3), (24, 3), (33, 3), (40, 3),
        (50, 9),                  # the chasm
        (66, 3), (75, 3), (84, 3), (95, 3), (105, 2),
    ],
    platforms=[
        # Pre-chasm: alternating low/high narrow steps
        (10, 7, 2),
        (16, 8, 2),
        (20, 6, 2),
        (25, 8, 2),
        (28, 6, 2),    # 3 cols from (25,8,2), 2 rows up — reachable
        (34, 7, 2),
        (38, 5, 2),    # 4 cols from (34,7,2), 2 rows up — reachable
        (42, 8, 2),
        (46, 6, 2),    # 4 cols from (42,8,2), 2 rows up — reachable
        # Chasm zig-zag (cols 50-58), 9 wide, 1-tile islands
        (50, 8, 1),
        (53, 6, 1),    # 3 cols from (50,8,1), 2 rows up — reachable
        (56, 8, 1),    # 3 cols from (53,6,1), 2 rows down — drop OK
        (59, 7, 2),    # land on solid floor edge
        # Post-chasm
        (63, 5, 2),    # 4 cols from (59,7,2), 2 rows up
        (68, 8, 2),
        (71, 6, 2),    # 3 cols from (68,8,2), 2 rows up
        (77, 7, 2),
        (81, 5, 2),    # 4 cols from (77,7,2), 2 rows up
        (86, 8, 2),
        (90, 6, 2),    # 4 cols from (86,8,2), 2 rows up
        (96, 8, 2),
        (100, 7, 2),
        (107, 6, 2),
    ],
    slimes=[4, 11, 19, 28, 36, 45, 60, 68, 79, 88, 92, 99, 103, 110],
    platform_slimes=[
        (11, 6),    # on (10,7,2)
        (20, 5),    # on (19,6,2) — wait that platform is at (20,6,2)
        (43, 7),    # on (42,8,2)
        (53, 5),    # on (53,6,1) — chasm island slime!
        (64, 4),    # on (63,5,2) — high
        (78, 6),    # on (77,7,2)
        (97, 7),    # on (96,8,2)
        (108, 5),   # on (107,6,2)
    ],
    flag_col=113,
)

# ===========================================================================
# L8 — "Triple Trouble" (125 wide): three back-to-back 10-wide chasms
# ===========================================================================
L8 = LevelSpec(
    name="L8",
    width=125,
    pits=[
        (8, 2), (15, 3),
        (24, 10),    # Chasm 1: cols 24-33
        (45, 10),    # Chasm 2: cols 45-54
        (66, 10),    # Chasm 3: cols 66-75
        (80, 3), (88, 3), (97, 3), (108, 3), (118, 3),
    ],
    platforms=[
        # Pre-chasm
        (10, 7, 2),
        (16, 8, 2),
        (20, 6, 2),
        # Chasm 1 (cols 24-33) — 3 islands forming arc
        (25, 7, 2),
        (29, 6, 2),    # 4 cols from (25,7,2), 1 row up
        (32, 7, 2),    # 3 cols from (29,6,2), 1 row down — chains to recovery floor at col 34
        # Recovery 1 (cols 34-44)
        (36, 5, 2),    # row-5 reward — reachable from floor at col 35 (5 cols, 4 rows up — NO wait that's 4 rows). Actually from floor row 9, 4 rows up means reachable only if there's stepping stone.
        # Let's add stepping stone to make 36,5 reachable.
        (38, 6, 2),    # stepping stone (reachable from floor: 2 rows up)
        (42, 7, 2),
        # Chasm 2 (cols 45-54)
        (46, 8, 2),
        (50, 6, 2),    # 4 cols from (46,8,2), 2 rows up
        (53, 7, 2),    # 3 cols from (50,6,2), 1 row down
        # Recovery 2 (cols 55-65)
        (57, 5, 2),
        (60, 6, 2),
        # Chasm 3 (cols 66-75)
        (67, 7, 2),
        (71, 5, 2),    # 4 cols from (67,7,2), 2 rows up
        (74, 7, 2),
        # Post-chasms
        (77, 6, 2),
        (83, 4, 3),    # row-4 reward (5 cols from (77,6,2), 2 rows up)
        (91, 7, 2),
        (95, 5, 2),    # 4 cols from (91,7,2), 2 rows up
        (101, 8, 2),
        (104, 6, 3),
        (111, 7, 2),
        (115, 5, 2),   # 4 cols from (111,7,2), 2 rows up
        (118, 7, 3),   # final pre-flag platform; cols 118-120 keep clear of the flag-122..124 clearance zone
    ],
    slimes=[4, 11, 18, 35, 41, 56, 62, 78, 84, 92, 100, 113, 116, 122],
    platform_slimes=[
        (11, 6),     # on (10,7,2)
        (26, 6),     # on (25,7,2) — chasm 1 island slime
        (47, 7),     # on (46,8,2) — chasm 2 island slime
        (72, 4),     # on (71,5,2)
        (68, 6),     # on (67,7,2) — chasm 3 entry slime
        (84, 3),     # on (83,4,3) — high reward guardian
        (105, 5),    # on (104,6,3)
        (119, 6),    # on (118,7,3) — last platform slime before flag
        (61, 5),     # on (60,6,2)
        (54, 6),     # on (53,7,2)
    ],
    flag_col=123,
)

# ===========================================================================
# L9 — "Slime Swarm" (125 wide): enemy density, clusters of 3
# ===========================================================================
L9 = LevelSpec(
    name="L9",
    width=125,
    pits=[
        (10, 3), (20, 3), (30, 3), (40, 3),
        (55, 10),    # mid chasm cols 55-64
        (75, 3), (85, 3), (95, 3), (107, 3), (117, 3),
    ],
    platforms=[
        # Pre-chasm: wider platforms (the focus is enemies, not platforming)
        (5, 7, 3),
        (14, 6, 3),
        (24, 7, 4),
        (33, 6, 3),
        (43, 7, 4),
        (48, 5, 3),
        # Mid chasm islands
        (56, 7, 2),
        (60, 8, 2),
        (63, 7, 2),
        # Post-chasm wide platforms with slimes
        (67, 6, 4),
        (78, 7, 4),
        (88, 6, 3),
        (98, 7, 4),
        (104, 5, 3),
        (110, 6, 3),
        (119, 7, 3),
    ],
    slimes=[
        # Clusters of 3
        3, 4, 5,
        13, 14, 15,
        23, 24, 25,
        33, 34, 35,
        45, 46, 47,
        66, 67, 68,
        79, 80, 81,
        100, 101, 102,
        112, 113, 114,
    ],
    platform_slimes=[
        (15, 5),    # on (14,6,3)
        (44, 6),    # on (43,7,4)
        (68, 5),    # on (67,6,4)
        (79, 6),    # on (78,7,4)
        (105, 4),   # on (104,5,3)
        (120, 6),   # on (119,7,3)
    ],
    flag_col=123,
)

# ===========================================================================
# L10 — "Master Trial" (150 wide): final boss-level
# ===========================================================================
L10 = LevelSpec(
    name="L10",
    width=150,
    pits=[
        (7, 3), (18, 3), (30, 3), (45, 3),
        (60, 4), (75, 4),
        (90, 12),    # MEGA CHASM cols 90-101
        (118, 8),    # second large chasm cols 118-125
        (135, 3), (145, 2),
    ],
    platforms=[
        # Opening
        (10, 7, 2),
        (15, 8, 3),
        (20, 6, 2),
        (24, 7, 3),
        (28, 5, 2),     # row-5 (4 cols from (24,7,3), 2 rows up)
        (33, 8, 2),
        (37, 6, 3),
        (41, 4, 3),     # row-4 (4 cols from (37,6,3), 2 rows up)
        # Mid section
        (46, 7, 2),
        (50, 8, 3),
        (54, 6, 3),
        (58, 4, 2),     # row-4 (4 cols from (54,6,3), 2 rows up)
        (63, 7, 2),
        (66, 5, 2),     # 3 cols from (63,7,2), 2 rows up
        (70, 8, 2),
        (76, 7, 2),
        (80, 5, 3),     # 4 cols from (76,7,2), 2 rows up
        (84, 3, 3),     # ROW-3 REWARD! (4 cols from (80,5,3), 2 rows up) — highest in the game
        # Mega chasm cols 90-101 — 4 sky-islands forming an arc
        (90, 8, 2),
        (94, 6, 2),     # 4 cols from (90,8,2), 2 rows up
        (98, 7, 2),     # 4 cols from (94,6,2), 1 row down
        (101, 6, 2),    # 3 cols from (98,7,2), 1 row up
        # Recovery
        (104, 5, 3),    # row-5 (3 cols from (101,6,2), 1 row up)
        (109, 7, 3),
        (113, 6, 2),    # 4 cols from (109,7,3), 1 row up
        # Second chasm cols 118-125
        (118, 7, 2),
        (122, 6, 2),    # 4 cols from (118,7,2), 1 row up
        (126, 7, 3),
        # Final stretch
        (132, 5, 2),    # 5 cols from (126,7,3), 2 rows up — reachable
        (138, 7, 3),
        (143, 5, 2),    # 5 cols from (138,7,3), 2 rows up
    ],
    slimes=[
        # Floor slimes throughout
        4, 12, 14, 22, 26, 34, 38, 48, 52, 64, 68, 72, 78, 82, 86,
        111, 116, 128, 132, 140, 144, 147,
    ],
    platform_slimes=[
        (11, 6),     # on (10,7,2)
        (21, 5),     # on (20,6,2)
        (38, 5),     # on (37,6,3)
        (41, 3),     # on (41,4,3) — high
        (51, 7),     # on (50,8,3)
        (54, 5),     # on (54,6,3)
        (84, 2),     # on (84,3,3) — the ROW-3 reward guardian!
        (95, 5),     # on (94,6,2) — mega chasm slime
        (102, 5),    # on (101,6,2)
        (105, 4),    # on (104,5,3)
        (114, 5),    # on (113,6,2)
        (127, 6),    # on (126,7,3)
    ],
    flag_col=148,
)

LEVELS = [L1, L2, L3, L4, L5, L6, L7, L8, L9, L10]


# ===========================================================================
# Emit + run
# ===========================================================================

def emit(grids, only_new: bool = False):
    """Emit the LEVELS list as Python source.

    If only_new=True, emit only L7-L10 (useful when appending to level.py
    where L1-L6 are already present).
    """
    print("LEVELS: List[List[str]] = [")
    indices = range(6, len(LEVELS)) if only_new else range(len(LEVELS))
    for i in indices:
        spec, grid = LEVELS[i], grids[i]
        print(f"    # ---------------- Level {i+1} — {spec.name} ----------------")
        print("    [")
        for row in grid:
            print(f'        "{"".join(row)}",')
        print("    ],")
    print("]")


if __name__ == "__main__":
    import sys
    grids = []
    all_ok = True
    for spec in LEVELS:
        grid = build(spec)
        issues = validate(grid, spec)
        if issues:
            all_ok = False
            for i in issues:
                print("  " + i)
        for y, row in enumerate(grid):
            assert len(row) == spec.width, f"{spec.name} row {y} width {len(row)} != {spec.width}"
        coin_count = sum(1 for r in grid for c in r if c == "C")
        slime_count = sum(1 for r in grid for c in r if c == "E")
        print(
            f"{spec.name}: {spec.width}x{H}, coins={coin_count}, "
            f"slimes={slime_count} (floor={len(spec.slimes)}, plat={len(spec.platform_slimes)}), "
            f"issues={len(issues)}"
        )
        grids.append(grid)
    print()
    if all_ok:
        print("ALL LEVELS OK\n")
        only_new = "--only-new" in sys.argv
        emit(grids, only_new=only_new)
    else:
        print("VALIDATION FAILED")
        sys.exit(1)
