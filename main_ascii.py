"""
main_ascii.py
--------------------------------------------------------------------
Live ASCII-terminal renderer for Track 3 (Legal Compliance Drone).
Allowed by the hackathon rules as an alternative to Tkinter/Pygame/
Matplotlib, and useful as a zero-dependency backup if a grading
machine doesn't have a display or pygame installed.

Run:  python3 main_ascii.py
--------------------------------------------------------------------
"""

import os
import time

from drone_kb import GRID_W, GRID_H, GOAL, is_restricted, has_permit
from simulation import Simulation

CLEAR = "\033c"  # full terminal reset (works in most POSIX terminals)


def render(sim):
    lines = []
    lines.append("=" * 66)
    lines.append(" TRACK 3 : LEGAL COMPLIANCE DRONE  --  FOL Inference Engine")
    lines.append("=" * 66)
    lines.append("")

    for y in range(GRID_H):
        row = ""
        for x in range(GRID_W):
            if (x, y) == sim.pos:
                ch = " D "
            elif (x, y) == GOAL:
                ch = " G "
            elif (x, y) not in sim.sensed:
                ch = " . "
            else:
                granted = sim.granted.get((x, y))
                if granted is False:
                    ch = " X "
                elif is_restricted(x, y) and has_permit(x, y):
                    ch = " P "
                else:
                    ch = " o "
            row += ch
        lines.append(row)

    lines.append("")
    lines.append("Legend: D=drone  G=goal  o=open(granted)  X=denied  "
                  "P=permitted-restricted  .=unsensed")
    lines.append("-" * 66)
    lines.append(f"STATE: {sim.state}")
    lines.append("-" * 66)
    lines.append("Live decision log:")
    for line in sim.log_lines:
        lines.append("  " + line)
    lines.append("-" * 66)
    if sim.finish_time:
        lines.append(sim.summary_line())
    print(CLEAR + "\n".join(lines))


def main():
    sim = Simulation()
    render(sim)
    time.sleep(0.6)
    while not sim.is_terminal():
        sim.tick()
        render(sim)
        time.sleep(0.6)
    render(sim)


if __name__ == "__main__":
    main()
