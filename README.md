# Track 3 — Legal Compliance Drone
### AI Express Hackathon · Unit 4 — First-Order Logic Agent

An urban delivery drone that **queries a First-Order Logic knowledge base before
entering every grid zone**, and only flies over a zone once its FOL inference
engine proves it is legally permitted to.

---

## 1. Scenario

The drone flies across a `10 × 7` city grid from a start pad to a delivery goal.
Some cells are **restricted airspace** (government buildings, stadium events).
A few restricted cells are covered by a **standing permit** (a hospital
emergency corridor). The drone doesn't know any of this in advance — it only
learns a cell's legal status when its sensor inspects it, exactly like a real
compliance system checking a live airspace registry.

Before moving into any new cell the drone **pauses and runs an FOL query**:

```
FlyOver(Drone, z)?
```

If the query fails, the drone is legally **DENIED** entry, marks that cell as
blocked, and **automatically replans** a new route around it. If the query
succeeds, the drone is **GRANTED** entry and flies through.

---

## 2. First-Order Logic formulation

**Constants:** `Drone`, and one zone constant `Z_x_y` per grid cell.
**Variable:** `?z` (universally quantified over every zone).

**Rule base (Horn-clause KB):**

```
R1:  Restricted(z) ∧ ¬HasPermit(Drone, z)   ⇒   ¬FlyOver(Drone, z)
R2:  ¬Restricted(z)                         ⇒    FlyOver(Drone, z)
R3:  Restricted(z) ∧ HasPermit(Drone, z)    ⇒    FlyOver(Drone, z)
```

**Ground facts** are asserted only as each zone is *sensed* — e.g. sensing a
restricted cell with no permit tells the KB `Restricted(Z_3_3)` and
`¬HasPermit(Drone, Z_3_3)`.

**Inference engine (`fol_engine.py`)** is a real unification-based engine, not
a hardcoded `if/else`:

- **Forward chaining** — after every sensor read, the engine re-applies every
  rule to the fact base until fixpoint, materialising any new `FlyOver` /
  `¬FlyOver` conclusions and logging each derivation.
- **Backward chaining** — the movement query `FlyOver(Drone, z)?` is answered
  with an AIMA-style `FOL-BC-ASK`: it recursively unifies the goal against
  known facts and rule conclusions, printing the full proof trace (which
  facts matched, which rules fired, with which substitution).

---

## 3. Files

| File | Purpose |
|---|---|
| `fol_engine.py` | Generic FOL engine: unification, substitution, forward chaining, backward chaining. |
| `drone_kb.py` | Grid/world definition, ground-truth airspace map, and the 3 FOL rules. |
| `simulation.py` | Agent state machine: **Sense → Forward-chain → Backward-chain query → Move / Deny+Replan**. Renderer-agnostic. |
| `main_pygame.py` | Primary visual runner (grid + drone + live log/metrics panel). |
| `main_ascii.py` | Zero-dependency live ASCII terminal fallback (same simulation engine). |
| `SUMMARY.pdf` | 1-page technical summary for submission. |

---

## 4. Setup & running

```bash
pip install -r requirements.txt

# Visual (primary submission)
python3 main_pygame.py

# Terminal fallback (no pygame needed)
python3 main_ascii.py
```

**Controls (pygame window):**

| Key | Action |
|---|---|
| `SPACE` | Pause / resume autoplay |
| `→` | Single-step (works while paused too — good for screen recording narration) |
| `R` | Restart the mission |
| `ESC` | Quit |

The decision log (sensing, forward-chaining derivations, backward-chaining
proof trace, GRANTED/DENIED verdicts, replans) is printed to **both** the
on-screen panel and stdout in real time, satisfying the "log decision-making
in real time" requirement.

---

## 5. PEAS

| | |
|---|---|
| **Performance measure** | Zero illegal airspace incursions, shortest legal path length, mission time |
| **Environment** | 10×7 partially-observable urban grid; static airspace-restriction map; sensed incrementally |
| **Actuators** | Move (N/E/S/W), sensor sweep, FOL query execution |
| **Sensors** | Local zone inspector (reveals restriction/permit status of the next cell) |

---

## 6. Complexity

- **Unification:** O(n) in term size per call.
- **Forward chaining:** O(r · f<sup>p</sup>) worst case per pass (r rules,
  f known facts, p premises per rule) — here p ≤ 2 and the fact base is
  small, so each pass is effectively linear in facts sensed so far.
- **Backward chaining (FOL-BC-ASK):** bounded by rule-base depth × branching
  factor; here rule depth ≤ 2, so each query resolves in O(1) rule
  applications.
- **Path planning (BFS on the grid):** O(V + E) = O(W·H) per (re)plan; observed
  ~45–60 nodes expanded per plan on the 70-cell grid, 3–5 replans typical.
- **Space:** O(cells sensed) for facts + O(path length) for the frontier.

Observed run: **15 moves, 18 FOL queries, 3 denials, 4 replans, ~220 total BFS
nodes expanded, < 0.05s compute time** (see console output / `SUMMARY.pdf`).

---

## 7. Team

| Register Number | Member |
|---|---|
| 2441657| *Simran Rao* |
| 2441663 | *Zehrah Shameer* |
| 2441652 | *Sasha Alwin* |

Course: *(fill in course code)* — Group ID: *(fill in)*
