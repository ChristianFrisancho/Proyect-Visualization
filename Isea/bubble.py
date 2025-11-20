import anywidget
import traitlets as T
from pathlib import Path
import numpy as np

class D3Bubble(anywidget.AnyWidget):
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    
    def __init__(self, data=None, title="Bubble Analysis", width=700, height=500, **kwargs):
        super().__init__()

        js_path = Path(__file__).parent / "assets" / "bubble.js"
        if js_path.exists():
            self._esm = js_path.read_text(encoding="utf-8")
        else:
            self._esm = (
                "export async function render({ model, el }) {"
                "  el.innerHTML = '<div style=\"color:red\">bubble.js not found</div>';"
                "}"
            )

        self.options = {
            "title": title,
            "width": width,
            "height": height,
            "margin": {"top": 50, "right": 50, "bottom": 50, "left": 60},
            "xLabel": kwargs.get("xLabel", "X Axis"),
            "yLabel": kwargs.get("yLabel", "Y Axis"),
            "zLabel": kwargs.get("zLabel", "Size"),
            **kwargs
        }
        
        if data:
            self.set_data(data)

    def set_data(self, records):
        clean = []
        for r in records:
            item = r.copy()
            for k, v in item.items():
                if isinstance(v, (float, np.floating)) and np.isnan(v):
                    item[k] = 0
            clean.append(item)
        self.data = clean