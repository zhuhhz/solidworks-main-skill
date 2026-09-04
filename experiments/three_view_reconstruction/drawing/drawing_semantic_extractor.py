"""Build a provenance-bearing DrawingPrimitiveGraph without semantic guesses."""
from __future__ import annotations


def _annotations(drawing_structure: dict) -> dict:
    professional = drawing_structure.get("professional_annotations", {})
    return {
        "center_marks": [
            {"geometry_type": "ANNOTATION", "semantic": "CENTERMARK",
             "source": "DrawingAnnotation", "confidence": 1.0,
             "view": mark.get("view"), "semantic_view": mark.get("semantic_view"),
             "geometry": {"size_m": mark.get("size_m"), "show_lines": mark.get("show_lines")}}
            for mark in professional.get("center_marks", [])
        ],
        "center_lines": professional.get("center_lines", []),
        "dimensions": drawing_structure.get("dimensions", []),
        "callouts": professional.get("hole_callouts", []),
    }


def extract(projected: dict, drawing_structure: dict | None = None,
            semantic_evidence: dict | None = None) -> dict:
    drawing_structure = drawing_structure or {}
    annotations = _annotations(drawing_structure)
    evidence_ok = bool(semantic_evidence and semantic_evidence.get("status") == "PASS"
                       and semantic_evidence.get("differential", {}).get("semantic_provenance") == "HLV_MINUS_HLR")
    evidence_views = semantic_evidence.get("differential", {}).get("views", []) if evidence_ok else []
    hlr_views = semantic_evidence.get("hlr", {}).get("post_reopen", []) if evidence_ok else []
    views = []
    unknown_count = 0
    for index, view in enumerate(projected.get("views", [])):
        projected_geometry = {"visible": [], "hidden": [], "unknown": []}
        if evidence_ok and index < len(hlr_views) and index < len(evidence_views):
            projected_geometry["visible"] += [
                {"geometry_type": "LINE", "semantic": "VISIBLE", "source": "HLR_CAPTURE",
                 "confidence": 1.0, "geometry": line}
                for line in hlr_views[index].get("lines", [])
            ]
            projected_geometry["visible"] += [
                {"geometry_type": "CIRCLE", "semantic": "VISIBLE", "source": "HLR_CAPTURE",
                 "confidence": 1.0, "geometry": circle}
                for circle in hlr_views[index].get("circles", [])
            ]
            projected_geometry["visible"] += [
                {"geometry_type": "ARC", "semantic": "VISIBLE", "source": "HLR_CAPTURE",
                 "confidence": 1.0, "geometry": arc}
                for arc in hlr_views[index].get("arcs", [])
            ]
            projected_geometry["hidden"] += evidence_views[index].get("hidden_supports", [])
            projected_geometry["hidden"] += evidence_views[index].get("hidden_circles", [])
        else:
            projected_geometry["unknown"] += [
                {"geometry_type": "LINE", "semantic": "UNKNOWN", "source": "IView.GetPolyLinesAndCurves",
                 "confidence": 0.0, "geometry": line}
                for line in view.get("visible_segments", [])
            ]
            projected_geometry["unknown"] += [
                {"geometry_type": "CIRCLE", "semantic": "UNKNOWN", "source": "IView.GetPolyLinesAndCurves",
                 "confidence": 0.0, "geometry": circle}
                for circle in view.get("circles", [])
            ]
            projected_geometry["unknown"] += [
                {"geometry_type": "ARC", "semantic": "UNKNOWN", "source": "IView.GetPolyLinesAndCurves",
                 "confidence": 0.0, "geometry": arc}
                for arc in view.get("arcs", [])
            ]
        unknown_count += len(projected_geometry["unknown"])
        view_annotations = {
            key: [item for item in values if not isinstance(item, dict) or item.get("view") in (None, view.get("name"))]
            for key, values in annotations.items()
        }
        views.append({"name": view.get("name"), "semantic_view": view.get("semantic_view"),
                      "orientation": view.get("orientation"), "projected_geometry": projected_geometry,
                      "annotations": view_annotations})
    status = "PASS" if evidence_ok and unknown_count == 0 else "PARTIAL"
    return {"status": status, "views": views, "annotations": annotations,
            "semantic_provenance": "HLV_MINUS_HLR" if evidence_ok else "SEMANTIC_PROVENANCE_UNAVAILABLE",
            "unknown_projected_primitive_count": unknown_count,
            "limitations": [] if status == "PASS" else ["Projected visibility remains UNKNOWN without a successful matched HLV/HLR run."]}
