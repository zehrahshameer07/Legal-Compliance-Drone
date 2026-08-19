"""
fol_engine.py
--------------------------------------------------------------------
A small, genuine First-Order Logic inference engine supporting:
  - Unification of atoms with variables
  - Forward chaining  (data-driven: derive all new facts from KB)
  - Backward chaining (goal-driven: prove a query, AIMA-style FOL-BC-ASK)

This is NOT a hardcoded if/else dressed up as "logic" -- predicates,
variables and substitutions are handled generically, exactly like the
FOL-FC-ASK / FOL-BC-ASK algorithms in Russell & Norvig (AIMA), so it
generalizes to any Horn-clause KB you give it.

Term representation
--------------------------------------------------------------------
- Constant : a plain string, e.g. "Drone", "Z_2_3"
- Variable : a string starting with '?'  e.g. "?x", "?z"
- Atom     : a tuple  (Predicate, arg1, arg2, ...)
             e.g. ("Restricted", "?z")
- Rule     : (premises: list[Atom], conclusion: Atom)
             premises = [] means it's a plain fact.
--------------------------------------------------------------------
"""

from itertools import count

TRACE = []  # global list of log lines from the last inference run


def log(msg):
    TRACE.append(msg)


def is_var(term):
    return isinstance(term, str) and term.startswith("?")


def is_negated(atom):
    return atom[0].startswith("NOT_")


def negate(atom):
    if is_negated(atom):
        return (atom[0][4:],) + atom[1:]
    return ("NOT_" + atom[0],) + atom[1:]


# ---------------------------------------------------------------- #
# Unification
# ---------------------------------------------------------------- #
def unify(x, y, theta=None):
    """Unify atoms/terms x and y. Returns a substitution dict, or None."""
    if theta is None:
        theta = {}
    if theta is None:
        return None
    if x == y:
        return theta
    if is_var(x):
        return unify_var(x, y, theta)
    if is_var(y):
        return unify_var(y, x, theta)
    if isinstance(x, tuple) and isinstance(y, tuple):
        if len(x) != len(y):
            return None
        for a, b in zip(x, y):
            theta = unify(a, b, theta)
            if theta is None:
                return None
        return theta
    return None


def unify_var(var, x, theta):
    if var in theta:
        return unify(theta[var], x, theta)
    if is_var(x) and x in theta:
        return unify(var, theta[x], theta)
    new_theta = dict(theta)
    new_theta[var] = x
    return new_theta


def substitute(atom, theta):
    if is_var(atom):
        return theta.get(atom, atom)
    if isinstance(atom, tuple):
        return tuple(substitute(a, theta) for a in atom)
    return atom


def atom_to_str(atom):
    if not isinstance(atom, tuple):
        return str(atom)
    neg = ""
    pred = atom[0]
    if pred.startswith("NOT_"):
        neg = "\u00ac"
        pred = pred[4:]
    args = ", ".join(str(a) for a in atom[1:])
    return f"{neg}{pred}({args})"


def rule_to_str(rule):
    premises, conclusion = rule
    if not premises:
        return atom_to_str(conclusion)
    body = " \u2227 ".join(atom_to_str(p) for p in premises)
    return f"{body}  \u21d2  {atom_to_str(conclusion)}"


# ---------------------------------------------------------------- #
# Knowledge Base
# ---------------------------------------------------------------- #
class KnowledgeBase:
    def __init__(self):
        self.facts = set()      # ground atoms known true
        self.rules = []         # (premises, conclusion) Horn clauses

    def tell_fact(self, atom, quiet=False):
        if atom not in self.facts:
            self.facts.add(atom)
            if not quiet:
                log(f"  [KB+] added fact  {atom_to_str(atom)}")
            return True
        return False

    def tell_rule(self, premises, conclusion):
        self.rules.append((tuple(premises), conclusion))

    # -------------------------------------------------------------- #
    # Forward chaining: derive every fact entailed by rules + facts
    # -------------------------------------------------------------- #
    def forward_chain(self):
        """Apply every rule until no new facts are derived (fixpoint)."""
        added_any = True
        newly_derived = []
        while added_any:
            added_any = False
            for premises, conclusion in self.rules:
                for theta in self._match_premises(premises, {}):
                    new_fact = substitute(conclusion, theta)
                    if "?" in atom_to_str(new_fact):
                        continue  # unbound rule, skip
                    if new_fact not in self.facts:
                        self.facts.add(new_fact)
                        newly_derived.append(new_fact)
                        log(f"  [FC]  {rule_to_str((premises, conclusion))}"
                            f"   with {theta}  =>  derived {atom_to_str(new_fact)}")
                        added_any = True
        return newly_derived

    def _match_premises(self, premises, theta):
        """Yield every substitution that satisfies a conjunction of premises
        against the known facts (simple backtracking join)."""
        if theta is None:
            return
        if not premises:
            yield theta
            return
        first, rest = premises[0], premises[1:]
        for fact in list(self.facts):
            theta2 = unify(first, fact, theta)
            if theta2 is not None:
                yield from self._match_premises(rest, theta2)

    # -------------------------------------------------------------- #
    # Backward chaining (goal directed) -- AIMA FOL-BC-ASK
    # -------------------------------------------------------------- #
    def backward_chain(self, goal, theta=None, depth=0, trail=None):
        if theta is None:
            theta = {}
        if trail is None:
            trail = []
        indent = "  " * (depth + 1)
        goal_s = substitute(goal, theta)
        log(f"{indent}? trying to prove {atom_to_str(goal_s)}")

        # 1) does it already match a known fact?
        for fact in self.facts:
            theta2 = unify(goal, fact, theta)
            if theta2 is not None:
                log(f"{indent}\u2713 matched known fact {atom_to_str(fact)}")
                yield theta2

        # 2) try every rule whose conclusion unifies with the goal
        for premises, conclusion in self.rules:
            theta2 = unify(conclusion, goal, theta)
            if theta2 is None:
                continue
            log(f"{indent}\u2192 applying rule: {rule_to_str((premises, conclusion))}")
            yield from self._bc_and(premises, theta2, depth + 1)

    def _bc_and(self, premises, theta, depth):
        if not premises:
            yield theta
            return
        first, rest = premises[0], premises[1:]
        for theta1 in self.backward_chain(first, theta, depth):
            yield from self._bc_and(rest, theta1, depth)

    def ask(self, goal):
        """Return True/False (closed-world) + capture the trace for a query,
        e.g. ask(("FlyOver", "Drone", "Z_3_2"))"""
        TRACE.clear()
        results = list(self.backward_chain(goal))
        return (len(results) > 0), list(TRACE)
