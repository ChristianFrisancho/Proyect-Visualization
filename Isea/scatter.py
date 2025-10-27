# Isea/scatter.py
import anywidget
import traitlets as T
import json
from pathlib import Path
from typing import Optional, Dict, Any

class ScatterBrush(anywidget.AnyWidget):
    """Generic scatter widget with two-way binding and simple API.

    - Keeps the same dataset-agnostic contract (x, y, key, label, color, size)
    - Same selection mechanics (click point, rectangular brush)
    - New inline selection panel options drawn inside the same SVG.
    """
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        data,
        x: Optional[str] = None,
        y: Optional[str] = None,
        color: Optional[str] = None,
        key: Optional[str] = None,
        size: Optional[str] = None,
        label: Optional[str] = None,
        log_x: bool = False,
        log_y: bool = False,
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        palette: Optional[list] = None,
        color_map: Optional[dict] = None,
        legend: bool = True,
        legend_position: str = "right",
        # NEW: inline selection panel (mirrors ParallelEnergy naming)
        margin: Optional[Dict[str, Any]] = None,
        panel_position: str = "right",   # "right" | "bottom"
        panel_width: int = 300,
        panel_height: int = 220,
        **overrides,
    ):
        super().__init__()
        # self._esm = (Path(__file__).parent / "assets" / "scatter.js").read_text()
        p_js = (Path(__file__).parent / "assets" / "scatter.js")
        try:
            self._esm = p_js.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback in case the file has stray bytes; don't crash on Windows cp1252
            self._esm = p_js.read_bytes().decode("utf-8", errors="replace")


        if hasattr(data, "to_dict"):  # DataFrame support
            data = data.to_dict("records")
        # ensure JSON serializable (datetimes -> str)
        self.data = json.loads(json.dumps(data, default=str))

        o = {}
        if x is not None: o["x"] = x
        if y is not None: o["y"] = y
        if key is not None: o["key"] = key
        if label is not None: o["label"] = label
        if color is not None: o["color"] = color
        if size is not None: o["size"] = size

        o["logX"] = bool(log_x)
        o["logY"] = bool(log_y)

        if title is not None:   o["title"] = title
        if x_label is not None: o["xLabel"] = x_label
        if y_label is not None: o["yLabel"] = y_label
        if width is not None:   o["width"] = int(width)
        if height is not None:  o["height"] = int(height)

        if margin is not None:  o["margin"] = margin
        # selection panel config (inside SVG)
        o["panel_position"] = panel_position
        o["panel_width"] = int(panel_width)
        o["panel_height"] = int(panel_height)

        if palette is not None:   o["colors"] = list(palette)
        if color_map is not None: o["colorMap"] = dict(color_map)
        o["legend"] = bool(legend)
        o["legendPosition"] = legend_position

        # allow callers to override anything
        o.update(overrides)

        self.options = o
        self.selection = {}  # {type, keys, rows}

# # Isea/scatter.py
# import anywidget
# import traitlets as T
# import json
# from pathlib import Path

# class ScatterBrush(anywidget.AnyWidget):
#     """Compact scatter widget with two-way binding and simple API."""
#     data = T.List(default_value=[]).tag(sync=True)
#     options = T.Dict(default_value={}).tag(sync=True)
#     selection = T.Dict(default_value={}).tag(sync=True)
#     selected_ids = T.List(default_value=[]).tag(sync=True)   #selection ids

#     # ---- Python helpers ----
#     def selection_df(self):
#         """Return a DataFrame from current JS-provided selection rows."""
#         try:
#             import pandas as pd
#         except Exception:
#             return self.selection.get("rows", [])
#         return pd.DataFrame(self.selection.get("rows", []))

#     def show_selection(self, head=None):
#         """Display selection as a table in the cell (convenience)."""
#         from IPython.display import display
#         df = self.selection_df()
#         display(df.head(head) if head is not None else df)
#         return df


#     def __init__(
#         self,
#         data,
#         x=None, y=None, color=None, key=None,
#         size=None, label=None,         # NEW (optional)
#         log_x=False, log_y=False,      # NEW (optional)
#         title=None, x_label=None, y_label=None,
#         width=None, height=None,
#         palette=None, color_map=None,
#         legend=True, legend_position="right",
#         **overrides,
#     ):
#         super().__init__()
#         self._esm = (Path(__file__).parent / "assets" / "scatter.js").read_text()

#         if hasattr(data, "to_dict"):  # DataFrame support
#             data = data.to_dict("records")
#         self.data = json.loads(json.dumps(data, default=str))

#         o = {}
#         if x is not None: o["x"] = x
#         if y is not None: o["y"] = y
#         if key is not None: o["key"] = key
#         if color is not None: o["color"] = color
#         if size is not None: o["size"] = size
#         if label is not None: o["label"] = label
#         if log_x: o["logX"] = True
#         if log_y: o["logY"] = True

#         if title is not None:   o["title"] = title
#         if x_label is not None: o["xLabel"] = x_label
#         if y_label is not None: o["yLabel"] = y_label
#         if width is not None:   o["width"] = int(width)
#         if height is not None:  o["height"] = int(height)

#         if palette is not None:   o["colors"] = list(palette)
#         if color_map is not None: o["colorMap"] = dict(color_map)
#         o["legend"] = bool(legend)
#         o["legendPosition"] = legend_position

#         o.update(overrides)
#         self.options = o
#         self.selection = {}
