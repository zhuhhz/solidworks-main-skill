"""Conservative initial Drawing QA gates, independent of SolidWorks COM."""
from __future__ import annotations


def validate_view_layout(drawing_structure: dict) -> dict:
    views = drawing_structure.get("views", [])
    overlaps = []
    for index, left in enumerate(views):
        a = left.get("box") or {}
        for right in views[index + 1:]:
            b = right.get("box") or {}
            if a and b and max(a["left"], b["left"]) < min(a["right"], b["right"]) and max(a["bottom"], b["bottom"]) < min(a["top"], b["top"]):
                overlaps.append([left.get("name"), right.get("name")])
    return {"status": "PASS" if views and not overlaps else "FAIL", "view_count": len(views), "overlaps": overlaps}


def validate_dimension_completeness(drawing_structure: dict, required: list[str]) -> dict:
    # This records only directly inspected native dimension text; it does not
    # infer dimensions from model geometry and therefore cannot overclaim.
    actual = {str(item) for item in drawing_structure.get("dimensions", [])}
    missing = [item for item in required if item not in actual]
    return {"status": "PASS" if not missing else "PARTIAL", "required": required, "native_dimensions": sorted(actual), "missing": missing}


def acceptance(drawing_structure: dict, required_dimensions: list[str] | None = None) -> dict:
    layout = validate_view_layout(drawing_structure)
    dimensions = validate_dimension_completeness(drawing_structure, required_dimensions or [])
    return {"technical_success": drawing_structure.get("status") == "pass", "layout": layout, "dimensions": dimensions,
            "engineering_acceptance": "PASS" if layout["status"] == "PASS" and dimensions["status"] == "PASS" else "PARTIAL"}
