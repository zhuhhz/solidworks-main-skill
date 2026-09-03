"""Evidence probe only: capture actual SW2024 drawing-view COM responses."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from win32com.client import gencache

UPSTREAM = Path(os.environ["SOLIDWORKS_AUTOMATION_BACKEND_PATH"])
sys.path.insert(0, str(UPSTREAM / "scripts"))
from sw_connect import get_com_member
from sw_session import SolidWorksSession


def main(path: str) -> None:
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    drawing = session.open(path, read_only=True, silent=True)
    # OpenDoc6 returns IModelDoc2.  Querying it as IDrawingDoc through CastTo
    # is unreliable in the dynamic proxy, so bind the generated IDrawingDoc
    # wrapper directly to the same IDispatch pointer.
    module = gencache.GetModuleForCLSID("{83A33D33-27C5-11CE-BFD4-00400513BB57}")
    drawing_doc = module.IDrawingDoc(drawing._oleobj_)
    rows = []
    try:
        # IModelDoc2 exposes the drawing-view chain even where IDrawingDoc's
        # GetCurrentSheet is not surfaced by pywin32's dynamic proxy.
        view = module.IView(drawing_doc.GetFirstView()._oleobj_)  # sheet pseudo-view
        view = view.GetNextView()
        while view is not None:
            view = module.IView(view._oleobj_)
            row = {"name": str(get_com_member(view, "Name")), "outline": list(view.GetOutline()), "position": list(view.Position), "display_mode": getattr(view, "DisplayMode", None)}
            for method, args in (("GetPolyLinesAndCurves", (0,)), ("GetPolyLinesAndCurves", (1,)), ("GetPolylines7", (0,)), ("GetPolylines7", (1,))):
                try:
                    value = getattr(view, method)(*args)
                    if isinstance(value, tuple): value = list(value)
                    row[f"{method}_{args[0]}"] = {"type": type(value).__name__, "length": len(value) if value is not None else None, "sample": list(value)[:40] if value is not None else None}
                except Exception as exc:
                    row[f"{method}_{args[0]}"] = {"error": repr(exc)}
            rows.append(row); view = view.GetNextView()
    finally:
        session.close(model=drawing); session.quit_owned_instance()
    print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__": main(sys.argv[1])
