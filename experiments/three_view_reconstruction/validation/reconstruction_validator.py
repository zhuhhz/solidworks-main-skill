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
        {"id": "feature_tree_hole", "passed": not feature_graph.holes or any(f.get("name") == "ThroughHole_D20" for f in backend.get("model_summary", {}).get("features", []))},
        {"id": "feature_tree_boss", "passed": not feature_graph.bosses or any(f.get("name") == "TopBoss" for f in backend.get("model_summary", {}).get("features", []))},
        {"id": "hole_geometry", "passed": not feature_graph.holes or (len(geometry.get("holes", [])) == len(feature_graph.holes) and all(any(abs(h.get("diameter_mm", 0)-expected.diameter) <= tolerance_mm for h in geometry.get("holes", [])) for expected in feature_graph.holes))},
    ]
    for slot in feature_graph.slots:
        candidates = geometry.get("slot_arc_candidates", [])
        slot_op = next((op.get("evidence", {}) for op in backend.get("operations", []) if op.get("operation") == "cut_extrude_through_slot"), {})
        tree = backend.get("model_summary", {}).get("features", [])
        arcs = [face for face in candidates if abs(face.get("diameter_mm", 0)/2-slot.radius_mm) <= tolerance_mm]
        centres = [face.get("position_mm", []) for face in arcs]
        centre_spacing = abs(centres[0][0]-centres[1][0]) if len(centres) >= 2 and slot.major_axis == "X" else (abs(centres[0][1]-centres[1][1]) if len(centres) >= 2 else -1)
        # Upstream's axial_length divides a semicylindrical area by a full
        # circumference, so its value is half the physical cut depth.
        axial = all(abs(2*float(face.get("axial_length_mm", -999))-base.depth) <= tolerance_mm for face in arcs)
        ownership = slot_op.get("through") is True and any(f.get("name") == "ThroughSlot_L40_W20" for f in tree)
        planar = geometry.get("slot_planar_side_candidates", [])
        transverse = 1 if slot.major_axis == "X" else 0
        plane_positions = sorted({round(float(face.get("origin_mm", [0,0])[transverse]), 6) for face in planar})
        plane_spacing = plane_positions[-1]-plane_positions[0] if len(plane_positions) >= 2 else -1
        checks += [
            {"id": "slot_two_cylindrical_end_walls", "passed": len(arcs) == 2, "actual": len(arcs)},
            {"id": "slot_equal_radius_R10", "passed": len(arcs) == 2 and all(abs(a.get("diameter_mm", 0)/2-slot.radius_mm) <= tolerance_mm for a in arcs)},
            {"id": "slot_end_center_spacing", "passed": abs(centre_spacing-(slot.overall_length_mm-slot.width_mm)) <= tolerance_mm, "actual_mm": centre_spacing},
            {"id": "slot_overall_extent", "passed": abs(centre_spacing+2*slot.radius_mm-slot.overall_length_mm) <= tolerance_mm, "actual_mm": centre_spacing+2*slot.radius_mm},
            {"id": "slot_internal_geometry", "passed": len(arcs) == 2 and all(a.get("measurement_source") == "B-Rep internal cylindrical face" for a in arcs)},
            {"id": "slot_axis_and_axial_extent", "passed": len(arcs) == 2 and axial},
            {"id": "slot_two_planar_side_walls", "passed": len(plane_positions) == 2 and abs(plane_spacing-slot.width_mm) <= tolerance_mm,
             "actual_positions_mm": plane_positions, "spacing_mm": plane_spacing},
            {"id": "slot_through_multi_evidence", "passed": ownership and axial,
             "evidence": {"creation_through": slot_op.get("through"), "feature_tree": ownership, "brep_axial_extent": axial}},
        ]
    return {"status": "PASS" if backend.get("status") == "PASS" and all(c["passed"] for c in checks) else "FAIL", "checks": checks}
