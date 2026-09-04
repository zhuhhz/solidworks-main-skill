# B003 Projection Reference Audit

Status: `REFERENCE_INVALID` → corrected.

The initial top-view reference contained only the two end-extreme hidden supports at X=30 and X=70 mm. A real SolidWorks 2024 SP04 HLV/HLR differential on the reconstructed R10 straight through slot returned four full-depth supports at X=30, 40, 60, and 70 mm. The additional X=40/X=60 supports are the projected tangent boundaries of the two semicircular ends. Front geometry, right-view hidden supports, dimensions, centre and slot semantics remained unchanged.

The original reference is retained as `benchmarks/archive/case_003_straight_slot.reference-invalid.v0.4.json`. The corrected contract is covered by unit tests and Level 2B expected-vs-generated hidden-support matching. No matcher tolerance was changed.
