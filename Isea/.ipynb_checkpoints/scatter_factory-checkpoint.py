# Isea/scatter_factory.py
import anywidget
import traitlets as T
import json
from pathlib import Path

def ScatterBrush2(data, **options):
    w = anywidget.AnyWidget()
    w.add_traits(
        data=T.List(default_value=[]).tag(sync=True),
        options=T.Dict(default_value={}).tag(sync=True),
        selection=T.Dict(default_value={}).tag(sync=True),
    )
    w._esm = (Path(__file__).parent / "assets" / "scatter.js").read_text()

    # ✅ ensure JSON-safe list-of-dicts (works for DataFrame, numpy, etc.)
    w.data = json.loads(json.dumps(getattr(data, "to_dict", lambda *_: data)("records") if hasattr(data, "to_dict") else data, default=str))
    w.options = options
    w.selection = {}
    return w
