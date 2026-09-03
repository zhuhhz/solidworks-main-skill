from __future__ import annotations

from schemas.feature_graph import BaseBlock
from schemas.projection_graph import ProjectionGraph


def infer_base_block(graph: ProjectionGraph) -> BaseBlock:
    return BaseBlock(width=graph.front.horizontal_extent, height=graph.front.vertical_extent, depth=graph.top.vertical_extent)
