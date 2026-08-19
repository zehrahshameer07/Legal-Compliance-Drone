"""
main_pygame.py
--------------------------------------------------------------------
Track 3 : Legal Compliance Drone -- visual runner.

Left  : the airspace grid. Fog until sensed. Green = open airspace,
        Red = restricted / denied, Amber = restricted-but-permitted
        (granted), the drone glyph, and the goal pad.
Right : a live decision log (FOL sense / forward-chain / backward-chain
        query trace) plus a running metrics readout -- this is also
        mirrored to stdout for the "log decision-making in real time"
        requirement.

Controls:
    SPACE  - pause / resume autoplay
    RIGHT  - single-step (also works while paused)
    R      - restart the mission
    ESC / window close - quit
--------------------------------------------------------------------
"""

import sys
import pygame

from drone_kb import GRID_W, GRID_H, START, GOAL, zone_label, is_restricted, has_permit
from simulation import Simulation, S_QUERY, S_DENIED, S_MOVE, S_DONE, S_FAILED

# ------------------------------------------------------------------ #
# Layout / theme
# ------------------------------------------------------------------ #
CELL = 62
GRID_PX_W = GRID_W * CELL
GRID_PX_H = GRID_H * CELL
MARGIN = 24
PANEL_W = 430
WIN_W = MARGIN * 3 + GRID_PX_W + PANEL_W
WIN_H = MARGIN * 2 + GRID_PX_H + 90

BG = (14, 17, 23)
GRID_BG = (24, 28, 38)
FOG = (34, 39, 51)
OPEN_C = (46, 125, 90)
OPEN_LINE = (72, 187, 132)
DENIED_C = (135, 40, 45)
DENIED_LINE = (219, 79, 79)
GRANTED_C = (156, 110, 30)
GRANTED_LINE = (232, 170, 60)
GOAL_C = (60, 90, 200)
PATH_C = (56, 62, 82)
TEXT = (226, 230, 240)
DIM = (140, 148, 165)
ACCENT = (99, 179, 237)
PANEL_BG = (19, 22, 30)
OK_COLOR = (110, 220, 140)
BAD_COLOR = (240, 100, 100)

FONT_NAME = "consolas,menlo,dejavusansmono,monospace"


def cell_rect(x, y):
    return pygame.Rect(MARGIN + x * CELL, MARGIN + 60 + y * CELL, CELL - 2, CELL - 2)


def draw_drone(surf, cx, cy, color=(230, 230, 240)):
    r = CELL * 0.30
    pygame.draw.circle(surf, (10, 12, 16), (cx, cy), int(r * 1.35))
    pts = [(cx, cy - r), (cx + r, cy + r * 0.7), (cx, cy + r * 0.35), (cx - r, cy + r * 0.7)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.circle(surf, ACCENT, (cx, cy), 3)


def main():
    pygame.init()
    pygame.display.set_caption("Track 3 - Legal Compliance Drone (FOL Inference Engine)")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(FONT_NAME, 15)
    font_small = pygame.font.SysFont(FONT_NAME, 12)
    font_title = pygame.font.SysFont(FONT_NAME, 20, bold=True)
    font_big = pygame.font.SysFont(FONT_NAME, 26, bold=True)

    sim = Simulation()
    autoplay = True
    STEP_MS = 550          # pacing between reasoning steps (tune for video length)
    acc = 0

    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    autoplay = not autoplay
                elif event.key == pygame.K_RIGHT:
                    if not sim.is_terminal():
                        sim.tick()
                elif event.key == pygame.K_r:
                    sim = Simulation()
                    autoplay = True
                    acc = 0

        if autoplay and not sim.is_terminal():
            acc += dt
            if acc >= STEP_MS:
                acc = 0
                sim.tick()

        # ---------------------------------------------------------- #
        screen.fill(BG)

        # header
        title = font_big.render("LEGAL COMPLIANCE DRONE", True, TEXT)
        screen.blit(title, (MARGIN, 14))
        sub = font_small.render(
            "FOL Inference Engine  |  Unit 4 - First-Order Logic Agent  |  Track 3",
            True, DIM)
        screen.blit(sub, (MARGIN, 40))

        # grid background
        grid_rect = pygame.Rect(MARGIN, MARGIN + 60, GRID_PX_W, GRID_PX_H)
        pygame.draw.rect(screen, GRID_BG, grid_rect, border_radius=6)

        for gy in range(GRID_H):
            for gx in range(GRID_W):
                r = cell_rect(gx, gy)
                sensed = (gx, gy) in sim.sensed
                if not sensed:
                    pygame.draw.rect(screen, FOG, r, border_radius=4)
                else:
                    granted = sim.granted.get((gx, gy))
                    if granted is False:
                        pygame.draw.rect(screen, DENIED_C, r, border_radius=4)
                        pygame.draw.rect(screen, DENIED_LINE, r, 2, border_radius=4)
                    elif is_restricted(gx, gy) and has_permit(gx, gy):
                        pygame.draw.rect(screen, GRANTED_C, r, border_radius=4)
                        pygame.draw.rect(screen, GRANTED_LINE, r, 2, border_radius=4)
                    else:
                        pygame.draw.rect(screen, OPEN_C, r, border_radius=4)
                        pygame.draw.rect(screen, OPEN_LINE, r, 1, border_radius=4)

                if sensed and is_restricted(gx, gy):
                    lock = font_small.render("\u26d4", True, (255, 255, 255))
                    screen.blit(lock, (r.x + 3, r.y + 2))

        # goal pad
        gr = cell_rect(*GOAL)
        pygame.draw.rect(screen, GOAL_C, gr, border_radius=4)
        pygame.draw.rect(screen, (140, 170, 255), gr, 2, border_radius=4)
        gtxt = font_small.render("GOAL", True, (255, 255, 255))
        screen.blit(gtxt, (gr.centerx - gtxt.get_width() // 2, gr.centery - 7))

        # planned path preview (thin line of dots)
        for cell in sim.path[1:]:
            r = cell_rect(*cell)
            pygame.draw.circle(screen, PATH_C, r.center, 4)

        # drone
        dr = cell_rect(*sim.pos)
        draw_drone(screen, dr.centerx, dr.centery)

        # state badge under grid
        badge_y = MARGIN + 60 + GRID_PX_H + 10
        state_color = {
            S_QUERY: ACCENT, S_DENIED: BAD_COLOR, S_MOVE: OK_COLOR,
            S_DONE: OK_COLOR, S_FAILED: BAD_COLOR,
        }.get(sim.state, DIM)
        state_txt = font.render(f"STATE: {sim.state}", True, state_color)
        screen.blit(state_txt, (MARGIN, badge_y))
        hint = font_small.render(
            "SPACE pause/resume   \u2192 step   R restart   ESC quit"
            + ("   (PAUSED)" if not autoplay else ""),
            True, DIM)
        screen.blit(hint, (MARGIN, badge_y + 20))

        # ---------------------------------------------------------- #
        # Right panel: legend + live log + metrics
        px = MARGIN * 2 + GRID_PX_W
        panel_rect = pygame.Rect(px, MARGIN, PANEL_W, WIN_H - MARGIN * 2)
        pygame.draw.rect(screen, PANEL_BG, panel_rect, border_radius=8)

        py = MARGIN + 14
        screen.blit(font_title.render("Legend", True, TEXT), (px + 16, py))
        py += 28
        legend_items = [
            (OPEN_C, "Open airspace \u2192 FlyOver GRANTED"),
            (DENIED_C, "Restricted, no permit \u2192 DENIED"),
            (GRANTED_C, "Restricted, has permit \u2192 GRANTED"),
            (FOG, "Not yet sensed"),
        ]
        for color, label in legend_items:
            pygame.draw.rect(screen, color, (px + 16, py, 16, 16), border_radius=3)
            screen.blit(font_small.render(label, True, DIM), (px + 40, py))
            py += 22

        py += 10
        screen.blit(font_title.render("FOL Rule Base", True, TEXT), (px + 16, py))
        py += 26
        rules = [
            "R1: Restricted(z) \u2227 \u00acHasPermit(Drone,z)",
            "      \u21d2 \u00acFlyOver(Drone,z)",
            "R2: \u00acRestricted(z) \u21d2 FlyOver(Drone,z)",
            "R3: Restricted(z) \u2227 HasPermit(Drone,z)",
            "      \u21d2 FlyOver(Drone,z)",
        ]
        for line in rules:
            screen.blit(font_small.render(line, True, (170, 190, 220)), (px + 16, py))
            py += 17

        py += 14
        screen.blit(font_title.render("Live Decision Log", True, TEXT), (px + 16, py))
        py += 26
        log_area_top = py
        log_area_bottom = panel_rect.bottom - 110
        for line in sim.log_lines:
            wrapped = wrap_text(line, font_small, PANEL_W - 32)
            for wline in wrapped:
                if py > log_area_bottom:
                    break
                color = TEXT
                if "DENIED" in wline or "\u2717" in wline:
                    color = BAD_COLOR
                elif "GRANTED" in wline or "\u2713" in wline:
                    color = OK_COLOR
                elif wline.strip().startswith(("QUERY", "SENSOR", "PLANNER", "REPLAN")):
                    color = ACCENT
                screen.blit(font_small.render(wline, True, color), (px + 16, py))
                py += 15

        # metrics footer
        my = panel_rect.bottom - 96
        pygame.draw.line(screen, (50, 55, 68), (px + 16, my - 6), (px + PANEL_W - 16, my - 6))
        screen.blit(font_title.render("Metrics", True, TEXT), (px + 16, my))
        my += 24
        metrics = [
            f"Steps moved: {sim.steps_moved}",
            f"FOL queries executed: {sim.queries_run}",
            f"Denials / Replans: {sim.denials} / {sim.replans}",
            f"BFS nodes expanded (total): {sim.nodes_expanded_total}",
        ]
        for m in metrics:
            screen.blit(font_small.render(m, True, DIM), (px + 16, my))
            my += 17

        pygame.display.flip()

        if sim.state == S_FAILED:
            pass  # stays on screen; console already logged the reason

    pygame.quit()
    sys.exit()


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


if __name__ == "__main__":
    main()
