import anywidget
import traitlets as T
from pathlib import Path
import numpy as np

class D3TrendLine(anywidget.AnyWidget):
    """
    Interactive multi-series trend line widget with optional predictions.

    This widget renders several time series as lines, each with:

    - A **history** segment (past data).
    - An optional **prediction** segment (future or modelled values).
    - A legend entry with colour and a click-to-hide toggle.
    - A shared x-axis (typically years) and y-axis (any numeric metric).
    - Tooltips that show the current value per series at the hovered x.

    Data flow
    ---------
    - On the Python side, you call :meth:`set_data` with a list of
      series dictionaries (see that method for the exact format).
    - The widget converts them into a JSON-serialisable list where each
      series has:

      .. code-block:: python

          {
              "id": "<series_label>",
              "color": "<CSS_color_or_None>",
              "history": [{"x": <num>, "y": <num>}, ...],
              "prediction": [{"x": <num>, "y": <num>}, ...],
          }

    - The JavaScript module in ``assets/trendline.js`` reads
      ``model.get("data")`` and ``model.get("options")`` to draw the
      chart with D3, including axes, legend, tooltips and series toggling.

    Synced traitlets
    ----------------
    data : list[dict]
        Cleaned list of series objects as shown above. All values must be
        plain Python types (floats, ints, strings, ``None``) so they can
        be serialised to JSON.
    options : dict
        Visual configuration passed to the frontend, including:

        - ``title``: chart title.
        - ``width`` / ``height``: total SVG size in pixels.
        - ``margin``: dict with ``top``, ``right``, ``bottom``, ``left``.
        - ``xLabel``: label for the x-axis (e.g. "Year").
        - ``yLabel``: label for the y-axis (e.g. "TWh").

        Any extra keys supplied via ``**kwargs`` in ``__init__`` are
        forwarded unchanged and can be used to extend the JS API.
    """
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    
    def __init__(self, data=None, title="Trend Analysis", width=800, height=400, **kwargs):
        """
        Initialise a D3TrendLine widget and optionally load time series data.

        Parameters
        ----------
        data : iterable[dict] or None, optional
            Optional list of **series definitions**. Each element in
            ``data`` is expected to be a dict-like object that can be
            indexed with ``.get()`` using at least the following keys:

            - ``"history_x"``: sequence of x-values for the historical
              segment (typically years or time indices).
            - ``"history_y"``: sequence of y-values (numeric) of the same
              length as ``history_x``.
            - ``"pred_x"``: sequence of x-values for the prediction
              segment (may be empty or ``None``).
            - ``"pred_y"``: sequence of y-values (numeric) matching
              ``pred_x`` in length.
            - ``"label"``: string label for the series (used in legend
              and tooltips).
            - ``"color"``: optional CSS colour string (e.g. ``"#1f77b4"``,
              ``"steelblue"``). If omitted, the JS side picks a colour.

            The x/y arrays can be plain Python lists, NumPy arrays or
            pandas Series; :meth:`set_data` will convert them to lists and
            drop any points where ``y`` is NaN.

            If ``data`` is provided, :meth:`set_data` is called
            immediately to populate ``self.data``. If ``None``, the
            widget starts empty and you can call :meth:`set_data` later.

        title : str, default "Trend Analysis"
            Title displayed at the top of the chart.

        width : int, default 800
            Total width of the SVG, in pixels.

        height : int, default 400
            Total height of the SVG, in pixels.

        **kwargs :
            Additional configuration options forwarded to ``self.options``.
            Typical keys include:

            - ``xLabel`` (str): x-axis label (default "Year").
            - ``yLabel`` (str): y-axis label (default "Value").
            - Any other JS-exposed options you want to experiment with.

        Notes
        -----
        - The JavaScript code is loaded from ``assets/trendline.js`` into
          the internal ``_esm`` attribute. If the file is missing, a
          small inline script is used to display an error message instead
          of silently failing.
        - You normally construct this widget with precomputed series
          (e.g. after fitting models or grouping data in pandas) rather
          than giving it a raw DataFrame.
        """
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
        """
        Prepare and assign the time series data for the trend line chart.

        This method takes a list of **raw series definitions** and
        converts them into the clean structure expected by the frontend
        (history + prediction segments with ``x``/``y`` pairs).

        Parameters
        ----------
        series_list : iterable[dict]
            Each element must be a dict-like object with at least the
            following keys:

            - ``"history_x"``: 1D array-like of x-values for the
              historical segment (e.g. years).
            - ``"history_y"``: 1D array-like of numeric y-values for the
              historical segment.
            - ``"pred_x"``: 1D array-like of x-values for the prediction
              segment (can be empty or ``None`` if there is no forecast).
            - ``"pred_y"``: 1D array-like of numeric y-values for the
              prediction segment (same length as ``pred_x`` when present).
            - ``"label"``: string label for the series (used as ``"id"``).
            - ``"color"``: optional CSS colour string.

            The x/y arrays may be:

            - Python lists,
            - NumPy arrays,
            - pandas Series,
            - or any iterable. 

            Internally they are converted to lists via a small helper
            that first tries ``.tolist()`` and otherwise wraps with
            ``list(...)``. For each segment, points where ``y`` is NaN
            (according to :func:`numpy.isnan`) are dropped.

        Behaviour
        ---------
        For every series ``s`` in ``series_list`` this method builds:

        .. code-block:: python

            hist = [
                {"x": x, "y": y}
                for x, y in zip(history_x, history_y)
                if not np.isnan(y)
            ]

            pred = [
                {"x": x, "y": y}
                for x, y in zip(pred_x, pred_y)
                if not np.isnan(y)
            ]

            clean_data.append({
                "id": s.get("label", "Unknown"),
                "color": s.get("color"),
                "history": hist,
                "prediction": pred,
            })

        and finally assigns ``self.data = clean_data``.

        Notes
        -----
        - Only y-values are checked for NaN; x-values are kept as-is.
        - After calling this method, ``self.data`` is ready to be
          consumed by the D3 code in ``trendline.js`` without further
          transformation.
        """
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