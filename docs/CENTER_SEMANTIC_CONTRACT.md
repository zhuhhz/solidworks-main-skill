# Center semantic contract

This contract prevents three distinct drawing meanings from being collapsed
into the generic word “centerline”.

| Semantic | Required entity | Typical target | Substitution allowed |
| --- | --- | --- | --- |
| Hole center indication | `CENTERMARK` | Circular projection of a hole | No |
| Axis indication | `CENTERLINE` | Axis inferred from two selected projected entities | No |
| Revolved shaft axis | `CENTERLINE` | Axis of a revolved cylindrical part | No |
| Geometric inference guide | `AXIS` in reasoning data only | Projection matching or symmetry reasoning | Never counted as a drawing annotation |

`CENTERMARK` and `CENTERLINE` are independent SolidWorks annotation objects.
The external backend reads them through separate view traversals. SolidWorks
2024 also exposes separate creation APIs: `IView.AutoInsertCenterMarks2` for
center marks and `IDrawingDoc.InsertCenterLine2` for centerlines selected from
drawing entities. Creating standard views does not constitute a deterministic
request for either annotation; template/document settings can affect what is
present. A backend must therefore request and read back the exact required
entity type.

For B002 the Front circle is the face-on projection of `ThroughHole_D20`.
One `CENTERMARK` satisfies its center indication. The former two crosshair
segments were semantic drawing aids, not two independently required
`CENTERLINE` annotation objects, so the v0.2 reference was invalid. They are
preserved in the archived reference and are not silently reclassified.
