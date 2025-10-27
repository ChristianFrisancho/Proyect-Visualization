# Isea/scatter.py
import anywidget
import traitlets as T
from pathlib import Path
from typing import Optional, Sequence, Mapping, Any
import json

try:
    import pandas as pd  # optional
except Exception:
    pd = None


class ScatterBrush(anywidget.AnyWidget):
    """
    Compact scatter widget with two-way binding and simple API.
    - Syncs `data` and `options` to JS (assets/scatter.js)
    - Receives JS->PY selections in `selection`
    """
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        data: "pd.DataFrame | Sequence[Mapping[str, Any]]",
        *,
        # encodings
        x: Optional[str] = None,
        y: Optional[str] = None,
        label: Optional[str] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
        key: Optional[str] = None,
        # presentation
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        radius: float = 5.0,
        opacity: float = 0.92,
        grid: bool = True,
        legend: bool = True,
        legend_position: str = "right",  # "right" | "bottom"
        palette: Optional[Sequence[str]] = None,
        color_map: Optional[Mapping[str, str]] = None,
        margin: Optional[Mapping[str, int]] = None,
        x_ticks: Optional[int] = None,
        y_ticks: Optional[int] = None,
        log_x: bool = False,
        log_y: bool = False,
        # dynamic XY candidates via XY_var* kwargs + any other overrides
        **overrides,
    ):
        super().__init__()
        self._esm = (Path(__file__).parent / "assets" / "scatter.js").read_text(encoding="utf-8")

        # ---- data -> list[dict]
        if pd is not None and isinstance(data, pd.DataFrame):
            payload = json.loads(data.to_json(orient="records"))
        else:
            payload = list(data)
        self.data = payload

        # ---- options
        o: dict[str, Any] = {}

        # encodings
        if x is not None:      o["x"] = x
        if y is not None:      o["y"] = y
        if label is not None:  o["label"] = label
        if color is not None:  o["color"] = color
        if size is not None:   o["size"] = size
        if key is not None:    o["key"] = key

        # presentation
        if title is not None:    o["title"] = title
        if x_label is not None:  o["xLabel"] = x_label
        if y_label is not None:  o["yLabel"] = y_label
        if width is not None:    o["width"] = int(width)
        if height is not None:   o["height"] = int(height)
        o["radius"] = float(radius)
        o["opacity"] = float(opacity)
        o["grid"] = bool(grid)
        o["legend"] = bool(legend)
        o["legendPosition"] = legend_position

        # scales / ticks
        o["logX"] = bool(log_x)
        o["logY"] = bool(log_y)
        if x_ticks is not None:  o["xTicks"] = int(x_ticks)
        if y_ticks is not None:  o["yTicks"] = int(y_ticks)

        # colors
        if palette is not None:   o["colors"] = list(palette)
        if color_map is not None: o["colorMap"] = dict(color_map)

        # layout
        if margin is not None:    o["margin"] = dict(margin)

        # ---- NEW: YearMin/YearMax (camelCase to JS) ----
        yr_min = overrides.pop("YearMin", None)
        yr_max = overrides.pop("YearMax", None)
        if yr_min is not None:
            try:
                o["yearMin"] = int(yr_min)
            except Exception:
                pass
        if yr_max is not None:
            try:
                o["yearMax"] = int(yr_max)
            except Exception:
                pass

        # ---- NEW: collect XY_var* -> o["xyVars"] and default x/y
        xy_vars = [
            v for k, v in sorted(overrides.items(), key=lambda kv: kv[0])
            if isinstance(k, str) and k.upper().startswith("XY_VAR") and v
        ]
        if xy_vars:
            o["xyVars"] = xy_vars
            o.setdefault("x", xy_vars[0])
            o.setdefault("y", xy_vars[1] if len(xy_vars) > 1 else o.get("x"))

        # let explicit overrides win (after we’ve popped YearMin/YearMax)
        o.update(overrides)

        self.options = o
        self.selection = {}

    def subset(self, df: "pd.DataFrame"):
        """
        Convenience: return a filtered copy of df using current selection keys.
        Requires `key` (or falls back to `label`) to exist in df.
        """
        if pd is None:
            raise RuntimeError("pandas is required for subset().")
        keys = list(map(str, self.selection.get("keys", [])))
        if not keys:
            return df.iloc[0:0].copy()
        key_col = self.options.get("key") or self.options.get("label")
        if key_col is None:
            raise ValueError("subset(): need `key` or `label` to be set.")
        return df[df[key_col].astype(str).isin(keys)].copy()
