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
    Interactive 2D scatterplot widget with brushing, tooltips and two-way binding.

    This widget is a thin Python wrapper around a D3 scatterplot defined in
    ``assets/scatter.js``. It synchronises three traitlets with the frontend:

    - ``data``: list of records (one per point).
    - ``options``: configuration dictionary controlling encodings and layout.
    - ``selection``: object describing the current selection, written by JS.

    Typical usage
    -------------
    You pass a pandas DataFrame or a list of dicts as ``data`` and specify
    which columns should be used for the x/y axes and encodings:

    .. code-block:: python

        w = ScatterBrush(
            df,
            x="EV_sales_share",
            y="EV_stock_share",
            color="Region",
            size="EV_stock_total",
            label="Country",
            key="id",
            title="EV sales vs stock",
            x_label="Sales share (%)",
            y_label="Stock share (%)",
        )

    On the frontend you get:

    - Zooming & panning.
    - Rectangle brush selection.
    - Legend (colour encoding).
    - Point hover tooltips.
    - Two-way binding of the selection state back into Python via
      ``self.selection``.

    The companion JavaScript reads:

    - ``model.get("data")`` for the point list.
    - ``model.get("options")`` for encodings and layout.
    - Writes into ``model.set("selection", ...)`` and ``model.save_changes()``
      whenever the selection changes.
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
        """
        Create a scatterplot from a DataFrame or list of records.

        Parameters
        ----------
        data :
            Either:

            - A :class:`pandas.DataFrame` with one row per point, or
            - A sequence of dict-like records (e.g. ``[{"x": ..., "y": ...}, ...]``).

            If a DataFrame is provided, it is converted to a list of JSON-like
            dicts using ``data.to_json(orient="records")``. All values must be
            JSON serialisable (numbers, strings, booleans, ``None``).

        x, y : str, optional
            Column names / keys to use for the x- and y-coordinates. If you
            omit them, the JavaScript side falls back to its own defaults
            (``"x"`` and ``"y"``).

        label : str, optional
            Name of the field used as a human-readable label (e.g. country
            name). This is shown in tooltips and exported selection.

        color : str, optional
            Name of the categorical or numeric field used for colour
            encoding. For categorical fields, the legend shows one entry
            per unique value.

        size : str, optional
            Name of the numeric field used to scale marker radius.

        key : str, optional
            Stable identifier for each point. This is what the selection
            returns in ``selection["keys"]`` and what :meth:`subset` uses
            to filter a DataFrame. If omitted, the widget can still render,
            but :meth:`subset` will fall back to ``label``.

        title : str, optional
            Title displayed above the chart.

        x_label, y_label : str, optional
            Axis labels; if omitted, the JS side may derive labels from
            the field names.

        width, height : int, optional
            Pixel dimensions of the SVG. If left as ``None``, the JS code
            uses its internal defaults (around 720×420).

        radius : float, default 5.0
            Base marker radius; combined with ``size`` if a size field is
            provided.

        opacity : float, default 0.92
            Marker opacity between 0 (invisible) and 1 (fully opaque).

        grid : bool, default True
            Whether to draw grid lines aligned with the axes.

        legend : bool, default True
            Whether to show a legend for the colour encoding.

        legend_position : {"right", "bottom"}, default "right"
            Location of the legend relative to the scatter area.

        palette : Sequence[str], optional
            Custom list of colour codes (e.g. hex strings). Overrides the
            default categorical palette in the JS implementation.

        color_map : Mapping[str, str], optional
            Explicit mapping from category value → colour string. This takes
            precedence over ``palette`` for the matching categories.

        margin : Mapping[str, int], optional
            Custom margins around the plot. The JS code expects keys
            ``"t"``, ``"r"``, ``"b"``, ``"l"`` (top/right/bottom/left) as
            pixel integers, for example:

            .. code-block:: python

                margin={"t": 28, "r": 24, "b": 56, "l": 70}

        x_ticks, y_ticks : int, optional
            Desired number of ticks on the x- or y-axis. If not provided,
            ticks are chosen automatically by D3.

        log_x, log_y : bool, default False
            If True, the corresponding axis uses a logarithmic scale where
            possible; if False, a linear scale is used.

        **overrides :
            Extra options forwarded directly into ``self.options``. Two
            special patterns are recognised:

            - ``YearMin`` / ``YearMax``: if present, they are popped from
              ``overrides`` and stored as integers in ``options["yearMin"]``
              and ``options["yearMax"]``. The JS code can then use these to
              highlight or filter a specific year range.

            - ``XY_var*`` keys: any keyword whose name starts with
              ``"XY_var"`` (case-insensitive) and has a truthy value is
              collected into ``options["xyVars"]`` as an ordered list of
              variable names. If this list is non-empty, the first element
              becomes default ``x``, and the second (if any) becomes default
              ``y``. This is how you drive a variable-selector UI from Python:

              .. code-block:: python

                  w = ScatterBrush(
                      df,
                      XY_var1="EV_sales_share",
                      XY_var2="EV_stock_share",
                      XY_var3="Charging_points_per_100k",
                  )

        Notes
        -----
        - ``self.data`` is always a plain list of dicts in "records" form.
        - ``self.options`` is a flat dict consumed entirely by
          ``assets/scatter.js``.
        - ``self.selection`` starts as an empty dict and is updated by the
          frontend when the user selects points.
        """
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
        Return a filtered copy of ``df`` based on the current selection keys.

        This helper is meant to be called after the user has interacted with
        the widget. The JavaScript code writes a list of selected point IDs
        into ``self.selection["keys"]`` (as strings). ``subset`` then:

        1. Reads ``keys = self.selection["keys"]``.
        2. Determines which column in ``df`` should be used for matching:
           first ``self.options["key"]`` if present, otherwise
           ``self.options["label"]``.
        3. Filters ``df`` to rows where that column, converted to string,
           is in ``keys``.

        Parameters
        ----------
        df : pandas.DataFrame
            Source DataFrame that contains at least one of the following
            columns:

            - The column whose name you passed as ``key`` when constructing
              the widget, or
            - If no key was specified, the column passed as ``label``.

            The values in that column must match the identifiers stored in
            ``self.selection["keys"]`` (typically strings).

        Returns
        -------
        pandas.DataFrame
            - If there is an active selection: a new DataFrame containing
              only the selected rows.
            - If there is no selection (``keys`` is empty): an empty DataFrame
              with the same columns as ``df``.

        Raises
        ------
        RuntimeError
            If pandas is not available (the module ``pd`` could not be
            imported).
        ValueError
            If neither a ``key`` nor a ``label`` encoding was configured
            in ``self.options``.

        Examples
        --------
        In a notebook:

        .. code-block:: python

            w = ScatterBrush(df, x="x", y="y", key="CountryCode")
            display(w)

            # After selecting some points in the plot:
            selected = w.subset(df)
            selected.head()
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