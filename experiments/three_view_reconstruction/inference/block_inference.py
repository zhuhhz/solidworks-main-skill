from __future__ import annotations

from schemas.feature_graph import BaseBlock
from schemas.projection_graph import ProjectionGraph


def infer_base_block(graph: ProjectionGraph) -> BaseBlock:
    # A stepped projection's top/side extent is total height, not necessarily
    # the base extrusion depth.  The benchmark evidence supplies the latter.
    step = (graph.feature_evidence or {}).get("centred_step", {})
    base_depth = float(step.get("base_depth_mm", graph.top.vertical_extent))
    return BaseBlock(width=graph.front.horizontal_extent, height=graph.front.vertical_extent, depth=base_depth)
