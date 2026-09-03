"""Canonical tolerance-based matching for Level-2 primitives."""
from __future__ import annotations
import math

POSITION_TOLERANCE_MM = 0.10
RADIUS_TOLERANCE_MM = 0.05

def _canonical_line(line):
    a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
    return (a, b) if a <= b else (b, a)

def _line_match(a, b):
    a1, a2, b1, b2 = *_canonical_line(a), *_canonical_line(b)
    return math.dist(a1, b1) <= POSITION_TOLERANCE_MM and math.dist(a2, b2) <= POSITION_TOLERANCE_MM

def _circle_match(a, b):
    return math.dist((a["x"], a["y"]), (b["x"], b["y"])) <= POSITION_TOLERANCE_MM and abs(a["diameter"] - b["diameter"]) / 2 <= RADIUS_TOLERANCE_MM

def match(expected, actual, kind):
    predicate = _line_match if kind == "line" else _circle_match
    used, pairs = set(), []
    for i, source in enumerate(expected):
        found = next((j for j, target in enumerate(actual) if j not in used and predicate(source, target)), None)
        if found is not None: used.add(found); pairs.append((i, found))
    return {"expected": len(expected), "actual": len(actual), "matched": len(pairs), "missing": len(expected)-len(pairs), "extra": len(actual)-len(pairs), "precision": len(pairs)/len(actual) if actual else (1.0 if not expected else 0.0), "recall": len(pairs)/len(expected) if expected else 1.0, "pairs": pairs}
