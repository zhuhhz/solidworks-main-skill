# Architecture

`solidworks-main-skill` is the Engineering Brain. Its source of truth is backend-neutral graph and plan data.

```text
Three Views -> Projection Graph -> Feature Hypothesis -> Feature Graph -> Modeling Plan
                                                               |
                                           external backend adapter
                                                               v
                                                        SolidWorks API
                                                               |
SLDPRT <- B-Rep Validation <- Feature Tree <- Drawing regeneration <- Roundtrip Validation
```

The `src/solidworks_main_skill` package owns reconstruction, drawing planning, validation, schemas, and backend compatibility policy. It does not contain copied upstream COM wrappers.
