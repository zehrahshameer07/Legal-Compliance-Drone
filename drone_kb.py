"""
drone_kb.py
--------------------------------------------------------------------
Track 3 : Legal Compliance Drone  (Unit 4 - First-Order Logic Agent)

Defines the urban airspace grid (ground truth, hidden from the agent
until sensed) and builds the FOL knowledge base of universally
quantified rules the agent reasons with:

    R1:  Restricted(z) AND NOT HasPermit(Drone, z)  =>  NOT FlyOver(Drone, z)
    R2:  NOT Restricted(z)                          =>  FlyOver(Drone, z)
    R3:  Restricted(z) AND HasPermit(Drone, z)       =>  FlyOver(Drone, z)

('?z' is a universally quantified variable ranging over every grid
cell / airspace-zone constant, and 'Drone' is a constant referring to
this specific agent -- exactly the FOL formulation asked for in the
question paper.)
--------------------------------------------------------------------
"""

from fol_engine import KnowledgeBase

GRID_W = 10
GRID_H = 7

START = (0, 3)
GOAL = (9, 3)

DRONE = "Drone"


def zone(x, y):
    """Grid coordinate -> FOL constant symbol."""
    return f"Z_{x}_{y}"


def coords_of(z):
    _, x, y = z.split("_")
    return int(x), int(y)


# -------------------------------------------------------------- #
# GROUND TRUTH airspace map (unknown to the KB until sensed).
# label is purely cosmetic, used in the UI / logs.
# -------------------------------------------------------------- #
# Restricted, NO permit  -> the drone must be legally denied entry.
RESTRICTED_NO_PERMIT = {
    (3, 1): "Govt Building No-Fly Zone",
    (3, 2): "Govt Building No-Fly Zone",
    (3, 3): "Govt Building No-Fly Zone",
    (3, 4): "Govt Building No-Fly Zone",
    (3, 5): "Govt Building No-Fly Zone",
    (6, 0): "Stadium Event Restriction",
    (6, 1): "Stadium Event Restriction",
}

# Restricted, but the drone HOLDS a valid permit -> legally allowed.
RESTRICTED_WITH_PERMIT = {
    (6, 4): "Hospital Emergency Corridor (Permit)",
    (6, 5): "Hospital Emergency Corridor (Permit)",
    (6, 6): "Hospital Emergency Corridor (Permit)",
}


def zone_label(x, y):
    if (x, y) in RESTRICTED_NO_PERMIT:
        return RESTRICTED_NO_PERMIT[(x, y)]
    if (x, y) in RESTRICTED_WITH_PERMIT:
        return RESTRICTED_WITH_PERMIT[(x, y)]
    return "Open Airspace"


def is_restricted(x, y):
    return (x, y) in RESTRICTED_NO_PERMIT or (x, y) in RESTRICTED_WITH_PERMIT


def has_permit(x, y):
    return (x, y) in RESTRICTED_WITH_PERMIT


# -------------------------------------------------------------- #
# Build a fresh KB pre-loaded with the universal FOL rules only.
# No facts are told yet -- those arrive as the drone SENSES cells,
# which is what drives the forward-chaining KB updates.
# -------------------------------------------------------------- #
def build_kb():
    kb = KnowledgeBase()

    kb.tell_rule(
        [("Restricted", "?z"), ("NOT_HasPermit", DRONE, "?z")],
        ("NOT_FlyOver", DRONE, "?z"),
    )
    kb.tell_rule(
        [("NOT_Restricted", "?z")],
        ("FlyOver", DRONE, "?z"),
    )
    kb.tell_rule(
        [("Restricted", "?z"), ("HasPermit", DRONE, "?z")],
        ("FlyOver", DRONE, "?z"),
    )
    return kb


def sense_cell(kb, x, y):
    """The drone's onboard sensor inspects a cell's real airspace status
    and TELLs the KB the corresponding ground FOL facts. Returns True if
    any new fact was actually added (i.e. this cell wasn't already known)."""
    z = zone(x, y)
    added = False
    if is_restricted(x, y):
        added |= kb.tell_fact(("Restricted", z))
        if has_permit(x, y):
            added |= kb.tell_fact(("HasPermit", DRONE, z))
        else:
            added |= kb.tell_fact(("NOT_HasPermit", DRONE, z))
    else:
        added |= kb.tell_fact(("NOT_Restricted", z))
    return added
