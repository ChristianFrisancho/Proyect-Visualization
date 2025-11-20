import anywidget
import traitlets as T
from pathlib import Path
import numpy as np

class D3TrendLine(anywidget.AnyWidget):
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    
    def __init__(self, data=None, title="Trend Analysis", width=800, height=400, **kwargs):
        super().__init__()

        js_path = Path(__file__).parent / "assets" / "trendline.js"
        if js_path.exists():
            self._esm = js_path.read_text(encoding="utf-8")
        else:
            self._esm = (
                "export async function render({ model, el }) {"
                "  el.innerHTML = '<div style=\"color:red\">trendline.js not found</div>';"
                "}"
            )

        self.options = {
            "title": title,
            "width": width,
            "height": height,
            "margin": {"top": 50, "right": 150, "bottom": 50, "left": 60},
            "yLabel": kwargs.get("yLabel", "Value"),
            "xLabel": kwargs.get("xLabel", "Year"),
            **kwargs
        }
        
        if data:
            self.set_data(data)

    def set_data(self, series_list):
        def to_list(arr):
            if hasattr(arr, "tolist"):
                return arr.tolist()
            return list(arr) if arr is not None else []

        clean_data = []
        for s in series_list:
            hist = [{"x": x, "y": y} for x, y in zip(to_list(s.get("history_x")), to_list(s.get("history_y"))) if not np.isnan(y)]
            pred = [{"x": x, "y": y} for x, y in zip(to_list(s.get("pred_x")), to_list(s.get("pred_y"))) if not np.isnan(y)]
            clean_data.append({
                "id": s.get("label", "Unknown"),
                "color": s.get("color"),
                "history": hist,
                "prediction": pred
            })
        self.data = clean_data