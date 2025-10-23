# Isea/scatter.py
import anywidget
import traitlets as T
import json
from pathlib import Path

class ScatterBrush(anywidget.AnyWidget):
    """Compact scatter widget with two-way binding and simple API."""
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        data,
        x=None, y=None, color=None, key=None,
        size=None, label=None,         # NEW (optional)
        log_x=False, log_y=False,      # NEW (optional)
        title=None, x_label=None, y_label=None,
        width=None, height=None,
        palette=None, color_map=None,
        legend=True, legend_position="right",
        **overrides,
    ):
        super().__init__()
        self._esm = (Path(__file__).parent / "assets" / "scatter.js").read_text()

        if hasattr(data, "to_dict"):  # DataFrame support
            data = data.to_dict("records")
        self.data = json.loads(json.dumps(data, default=str))

        o = {}
        if x is not None: o["x"] = x
        if y is not None: o["y"] = y
        if key is not None: o["key"] = key
        if color is not None: o["color"] = color
        if size is not None: o["size"] = size
        if label is not None: o["label"] = label
        if log_x: o["logX"] = True
        if log_y: o["logY"] = True

        if title is not None:   o["title"] = title
        if x_label is not None: o["xLabel"] = x_label
        if y_label is not None: o["yLabel"] = y_label
        if width is not None:   o["width"] = int(width)
        if height is not None:  o["height"] = int(height)

        if palette is not None:   o["colors"] = list(palette)
        if color_map is not None: o["colorMap"] = dict(color_map)
        o["legend"] = bool(legend)
        o["legendPosition"] = legend_position

        o.update(overrides)
        self.options = o
        self.selection = {}
