"""
simulation.py 
--------------------------------------------------------------------
Drives the agent loop for Track 3 (Legal Compliance Drone). This module
contains ZERO rendering code on purpose: main_pygame.py and
main_ascii.py both import this file and just draw whatever state it
reports, so the reasoning logic is identical (and independently
testable) no matter which visualiser is running.

Per-cell agent cycle, matching the deliverable spec exactly:
    1. SENSE   - onboard sensor reads the real airspace status of the
                 next cell and TELLs the KB the ground facts.
    2. FORWARD CHAIN - propagate those facts through the rule base so
                 every derivable FlyOver/NOT_FlyOver fact is materialised.
    3. QUERY   - backward-chain the goal FlyOver(Drone, z)? (this is the
                 "pause and execute an FOL query" moment).
    4. DECIDE  - GRANTED -> move in.  DENIED -> mark blocked & replan.
--------------------------------------------------------------------
"""

import time
from collections import deque

from drone_kb import (
    GRID_W, GRID_H, START, GOAL, DRONE,
    zone, zone_label, is_restricted, has_permit,
    build_kb, sense_cell,
)
from fol_engine import atom_to_str

# agent states
S_PLAN = "PLAN"
S_SENSE = "SENSE"
S_QUERY = "QUERY"
S_MOVE = "MOVE"
S_DENIED = "DENIED"
S_DONE = "DONE"
S_FAILED = "FAILED"


def bfs_path(start, goal, blocked, w=GRID_W, h=GRID_H):
    """Shortest 4-connected path avoiding `blocked` cells (BFS).
    Unknown / not-yet-sensed cells are treated as optimistically free.
    Returns (path_list_or_None, nodes_expanded)."""
    if start == goal:
        return [start], 0
    q = deque([start])
    came_from = {start: None}
    expanded = 0
    while q:
        cur = q.popleft()
        expanded += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cur[0] + dx, cur[1] + dy)
            if not (0 <= nxt[0] < w and 0 <= nxt[1] < h):
                continue
            if nxt in blocked or nxt in came_from:
                continue
            came_from[nxt] = cur
            if nxt == goal:
                # reconstruct
                path = [nxt]
                while came_from[path[-1]] is not None:
                    path.append(came_from[path[-1]])
                path.reverse()
                return path, expanded
            q.append(nxt)
    return None, expanded


class Simulation:
    def __init__(self):
        self.kb = build_kb()
        self.pos = START
        self.goal = GOAL
        self.blocked = set()
        self.sensed = {}          # (x,y) -> True once sensor has inspected it
        self.granted = {}         # (x,y) -> True/False decision result, for display
        self.path = []
        self.state = S_PLAN
        self.log_lines = []       # rolling log for the UI panel
        self.full_log = []        # complete console-style log
        self.next_cell = None
        self.last_trace = []
        self.start_time = time.time()
        self.finish_time = None

        # metrics
        self.steps_moved = 0
        self.queries_run = 0
        self.denials = 0
        self.replans = 0
        self.nodes_expanded_total = 0

        self._emit(f"MISSION START: {DRONE} at {zone(*self.pos)} -> "
                    f"goal {zone(*self.goal)}")

    # ------------------------------------------------------------ #
    def _emit(self, line):
        self.full_log.append(line)
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-9:]   # keep panel short
        print(line)

    def _plan(self):
        path, expanded = bfs_path(self.pos, self.goal, self.blocked)
        self.nodes_expanded_total += expanded
        if path is None:
            self.state = S_FAILED
            self._emit("PLANNER: no legal route exists to the goal. Mission aborted.")
            return
        self.path = path
        self.replans += 1
        self._emit(f"PLANNER: route computed ({len(path)-1} hops, "
                    f"{expanded} nodes expanded) -> "
                    + " -> ".join(zone(*c) for c in path))
        self.state = S_SENSE

    def _sense(self):
        if len(self.path) < 2:
            self.state = S_DONE
            return
        self.next_cell = self.path[1]
        x, y = self.next_cell
        newly = sense_cell(self.kb, x, y)
        label = zone_label(x, y)
        tag = "NEW" if newly else "known"
        self._emit(f"SENSOR ({tag}): inspected {zone(x,y)} \u2192 \"{label}\"")
        derived = self.kb.forward_chain()
        for d in derived:
            self._emit(f"  \u21b3 forward-chained: {atom_to_str(d)}")
        self.state = S_QUERY

    def _query(self):
        x, y = self.next_cell
        goal_atom = ("FlyOver", DRONE, zone(x, y))
        self._emit(f"QUERY: backward-chaining  FlyOver({DRONE}, {zone(x,y)})?")
        result, trace = self.kb.ask(goal_atom)
        self.last_trace = trace
        self.queries_run += 1
        for t in trace:
            self._emit("    " + t)
        if result:
            self._emit(f"  \u2713 GRANTED \u2014 legally clear to fly over {zone(x,y)}")
            self.granted[(x, y)] = True
            self.state = S_MOVE
        else:
            self._emit(f"  \u2717 DENIED \u2014 not legally permitted over {zone(x,y)}")
            self.granted[(x, y)] = False
            self.denials += 1
            self.state = S_DENIED

    def _move(self):
        self.pos = self.next_cell
        self.sensed[self.pos] = True
        self.steps_moved += 1
        self.path.pop(0)
        if self.pos == self.goal:
            self.finish_time = time.time()
            self._emit(f"ARRIVED at goal {zone(*self.pos)}. Mission complete.")
            self._emit(self.summary_line())
            self.state = S_DONE
        else:
            self.state = S_SENSE

    def _denied(self):
        self.blocked.add(self.next_cell)
        self.sensed[self.next_cell] = True
        self._emit(f"REPLANNING around {zone(*self.next_cell)} ...")
        self.state = S_PLAN

    def summary_line(self):
        elapsed = (self.finish_time or time.time()) - self.start_time
        return (f"METRICS: steps={self.steps_moved} | FOL queries={self.queries_run} "
                f"| denials={self.denials} | replans={self.replans} "
                f"| BFS nodes expanded={self.nodes_expanded_total} "
                f"| wall-clock={elapsed:.2f}s")

    # ------------------------------------------------------------ #
    def tick(self):
        """Advance the state machine by exactly one step."""
        if self.state == S_PLAN:
            self._plan()
        elif self.state == S_SENSE:
            self._sense()
        elif self.state == S_QUERY:
            self._query()
        elif self.state == S_MOVE:
            self._move()
        elif self.state == S_DENIED:
            self._denied()
        return self.state

    def is_terminal(self):
        return self.state in (S_DONE, S_FAILED)
