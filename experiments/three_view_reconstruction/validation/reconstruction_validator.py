from __future__ import annotations

from schemas.feature_graph import FeatureGraph


def validate(feature_graph: FeatureGraph, backend: dict, tolerance_mm: float = 0.05) -> dict:
    geometry = backend.get("geometry", {})
    bbox = geometry.get("envelope_mm") or {}
    base = feature_graph.base_block
    total_depth = base.depth + sum(b.depth for b in feature_graph.bosses)
    checks = [
        {"id": "bbox", "passed": all(abs(float(bbox.get(k, -999))-expected) <= tolerance_mm for k, expected in (("length", base.width), ("width", base.height), ("height", total_depth)))},
        {"id": "feature_tree_base", "passed": any(f.get("name") == "BaseBlock" for f in backend.get("model_summary", {}).get("features", []))},
        {"id": "feature_tree_hole", "passed": any(f.get("name") == "ThroughHole_D20" for f in backend.get("model_summary", {}).get("features", []))},
        {"id": "feature_tree_boss", "passed": not feature_graph.bosses or any(f.get("name") == "TopBoss" for f in backend.get("model_summary", {}).get("features", []))},
        {"id": "hole_geometry", "passed": len(geometry.get("holes", [])) == len(feature_graph.holes) and any(abs(h.get("diameter_mm", 0)-20) <= tolerance_mm for h in geometry.get("holes", []))},
    ]
    return {"status": "PASS" if backend.get("status") == "PASS" and all(c["passed"] for c in checks) else "FAIL", "checks": checks}
