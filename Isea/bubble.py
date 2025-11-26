import anywidget
import traitlets as T
from pathlib import Path
import numpy as np

class D3Bubble(anywidget.AnyWidget):
    """
    Interactive D3-based bubble chart widget.

    This widget exposes two synchronized traitlets:

    - `data`: a list of records (dict-like objects) that define the points.
    - `options`: a dictionary with all visual and interaction settings.

    The actual rendering logic lives in the JavaScript module
    `assets/bubble.js`, which is loaded into the `_esm` attribute so that
    AnyWidget can connect the Python model to the JavaScript view in
    the notebook or JupyterLab frontend.
    """
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    
    def __init__(self, data=None, title="Bubble Analysis", width=700, height=500, **kwargs):
        """
        Initialise a new D3Bubble widget.

        Parameters
        ----------
        data : list[dict] or None, optional
            Optional initial dataset to display. Each record should contain
            the fields that the JavaScript code expects for the x, y and
            bubble size encodings.
        title : str, default "Bubble Analysis"
            Title text to be passed to the frontend and shown above or near
            the chart.
        width : int, default 700
            Width of the drawing area in pixels.
        height : int, default 500
            Height of the drawing area in pixels.
        **kwargs :
            Additional configuration options that are stored in `self.options`
            and consumed by `bubble.js`. Common examples include:
            
            - ``xLabel``: label for the x-axis.
            - ``yLabel``: label for the y-axis.
            - ``zLabel``: label for the bubble size.
            
            Any extra keys are forwarded unchanged, so the JavaScript side
            can introduce new options without changing the Python API.

        Notes
        -----
        If ``assets/bubble.js`` cannot be found at import time, a small
        inline JavaScript module is used instead that writes an error
        message into the output element. This makes missing assets visible
        during development instead of failing silently.
        """
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
        """
        Set and sanitise the data records for the bubble chart.

        This helper makes a shallow copy of each input record and replaces
        any NaN floating-point values with 0. This is necessary because
        NaN values are not JSON-serialisable and would otherwise cause
        warnings or failures when syncing the data to the frontend.

        records : iterable[dict]
            Collection of dict-like records to be visualised. Each record
            should contain the numeric fields referenced in the chart
            options (for example the x, y and size variables).
        """
        clean = []
        for r in records:
            item = r.copy()
            for k, v in item.items():
                if isinstance(v, (float, np.floating)) and np.isnan(v):
                    item[k] = 0
            clean.append(item)
        self.data = clean