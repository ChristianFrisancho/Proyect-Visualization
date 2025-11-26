# Isea/parallel.py
import anywidget
import traitlets as T
import pandas as pd
from pathlib import Path
from typing import Sequence, Optional


class ParallelEnergy(anywidget.AnyWidget):
    """
    Interactive parallel-coordinates widget for energy-style data.

    This widget renders a parallel-coordinates chart with:

    - Draggable axes (reordering dimensions live).
    - Vertical brushes per axis.
    - A year slider to move across time.
    - Click-to-select / deselect lines.
    - Two-way sync of selections between JavaScript and Python via the
      ``selection`` traitlet.

    Data model
    ----------
    The Python side aggregates a long-format DataFrame into a compact
    package stored in ``self.data`` with the structure:

    .. code-block:: python

        {
            "years": ["2010", "2015", "2020", ...],
            "dims": ["Solar", "Wind", "Hydro", "Bio", "Fossil"],
            "records": [
                {
                    "label": "Netherlands",
                    "Solar": [v_2010, v_2015, v_2020, ...],
                    "Wind":  [ ... ],
                    ...
                },
                ...
            ],
            "label": "Country",  # name of the label column in the source df
        }

    The corresponding JavaScript module (``assets/parallel.js``) reads
    this object and draws the parallel-coordinates view with D3.

    Synced traitlets
    ----------------
    data : dict
        Aggregated records as described above; must be JSON-serialisable.
    options : dict
        Visual and layout configuration (width, height, axes options,
        panel layout, etc.).
    selection : dict
        Populated from the frontend when the user selects lines, with the
        format:

        .. code-block:: python

            {
                "type": "<interaction_type>",  # e.g. "brush", "click"
                "keys": ["Country A", "Country B", ...],
                "rows": [
                    { "Country": "...", "year": ..., "<dim>": ..., ... },
                    ...
                ],
            }

        The exact columns in ``rows`` depend on the JS implementation,
        but typically include the label (e.g. country), year and values
        per dimension for the selected entries.
    """

    data = T.Dict(default_value={}).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        df: pd.DataFrame,
        years: Sequence[str],
        *,
        tech_col: str = "Technology_std",
        label_col: str = "Country",
        dims: Sequence[str] = ("Solar", "Wind", "Hydro", "Bio", "Fossil"),
        year_start: Optional[str] = None,
        width: int = 1150,
        height: int = 600,
        log_axes: bool = False,
        normalize: bool = False,
        reorder: bool = True,
        # NEW:
        margin: Optional[dict] = None,            # dict(top,left,right,bottom) or t,l,r,b
        panel_position: str = "right",            # "right" | "bottom"
        panel_width: int = 340,
        panel_height: int = 260,
    ):
        """
        Construct a parallel-coordinates chart from a long-format DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            Long-format dataset that contains one row per
            (label, technology, ...) and one column per year. It must
            include at least:

            - ``tech_col``: column holding the technology category
              (e.g. "Solar", "Wind", "Fossil").
            - ``label_col``: column holding the label used for lines
              (e.g. "Country").
            - One numeric column per year listed in ``years``. These
              columns are coerced to numeric via
              ``pd.to_numeric(..., errors="coerce")``.

            Example minimal schema:

            - ``Country`` (label_col)
            - ``Technology_std`` (tech_col)
            - ``2010``, ``2015``, ``2020`` (year columns)

        years : Sequence[str]
            List of column names in ``df`` that represent time. The
            constructor filters this list to those present in
            ``df.columns``; if none remain, a ``ValueError`` is raised.

        tech_col : str, default "Technology_std"
            Name of the column in ``df`` that encodes the technology /
            dimension categories. Only rows whose value is in ``dims``
            are used.

        label_col : str, default "Country"
            Name of the column used as the line label (e.g. country
            name). This label appears in the table / selection and is
            stored as ``"label"`` in each aggregated record.

        dims : Sequence[str], default ("Solar", "Wind", "Hydro", "Bio", "Fossil")
            Ordered list of technologies / dimensions to include as axes.
            Each value must correspond to a value in ``df[tech_col]``.
            For each label (e.g. country) the widget creates one record
            with a list of values per dimension across all years.

        year_start : str, optional
            Initial year displayed in the view. Must be one of the
            (filtered) ``years``; otherwise, the last available year is
            used as the starting point.

        width : int, default 1150
            Total width of the SVG drawing area, in pixels.

        height : int, default 600
            Total height of the SVG drawing area, in pixels.

        log_axes : bool, default False
            If True, the frontend uses logarithmic scaling where
            appropriate for the axes; otherwise, linear scales are used.

        normalize : bool, default False
            If True, values are normalised (per dimension) on the
            frontend so different technologies become comparable in
            relative terms.

        reorder : bool, default True
            If True, the user can drag axes to reorder them interactively.

        margin : dict, optional
            Custom margins around the chart. Accepts keys either as
            ``{"top", "right", "bottom", "left"}`` or shorthand
            ``{"t", "r", "b", "l"}``. Missing keys fall back to:

            - top: 10
            - right: 260
            - bottom: 40
            - left: 60

        panel_position : {"right", "bottom"}, default "right"
            Intended layout hint for where an optional side panel
            (e.g. a table or extra view) would be placed relative to the
            main chart.

        panel_width : int, default 340
            Suggested width in pixels for the side panel, if used.

        panel_height : int, default 260
            Suggested height in pixels for the side panel, if used.

        Notes
        -----
        Internally, the constructor:

        1. Filters rows to keep only technologies in ``dims``.
        2. Groups by ``[label_col, tech_col]`` and sums across all
           requested ``years``.
        3. Builds one record per ``label_col`` value, each with one list
           of values per dimension.
        4. Stores the result in ``self.data`` and layout/behaviour
           options in ``self.options``, which the JavaScript code in
           ``assets/parallel.js`` uses to draw the chart.
        """
        super().__init__()
        self._esm = (Path(__file__).parent / "assets" / "parallel.js").read_text()

        years = [c for c in years if c in df.columns]
        if not years:
            raise ValueError("years does not match dataframe columns.")

        dfn = df.copy()
        for y in years:
            dfn[y] = pd.to_numeric(dfn[y], errors="coerce")

        if tech_col not in dfn.columns or label_col not in dfn.columns:
            raise KeyError("Required columns are missing.")

        dims = list(dims)
        agg = (
            dfn[dfn[tech_col].isin(dims)]
            .groupby([label_col, tech_col])[years]
            .sum(min_count=1)
            .reset_index()
        )

        recs = []
        for country, block in agg.groupby(label_col):
            item = {"label": country}
            for t in dims:
                row = block[block[tech_col] == t]
                if row.empty:
                    item[t] = [0.0] * len(years)
                else:
                    r = row.iloc[0]
                    item[t] = [float(r[y]) if pd.notna(r[y]) else 0.0 for y in years]
            recs.append(item)

        self.data = {"years": list(years), "dims": dims, "records": recs, "label": label_col}

        # base options
        self.options = {
            "width": int(width),
            "height": int(height),
            "log_axes": bool(log_axes),
            "normalize": bool(normalize),
            "reorder": bool(reorder),
            "year_start": year_start if (year_start in years) else years[-1],
            # NEW layout
            "panel_position": panel_position,
            "panel_width": int(panel_width),
            "panel_height": int(panel_height),
        }
        if margin:
            # accepts keys: top/left/right/bottom or t/l/r/b
            self.options["margin"] = {
                "top":    margin.get("top",    margin.get("t", 105)),
                "right":  margin.get("right",  margin.get("r", 260)),
                "bottom": margin.get("bottom", margin.get("b", 40)),
                "left":   margin.get("left",   margin.get("l", 60)),
            }

        # save state to clone later
        self._df_raw = df.copy()
        self._years = list(years)
        self._tech_col = tech_col
        self._label_col = label_col
        self._dims = tuple(dims)

        self.selection = {}

    # ------------ helpers PY ------------
    # --- helpers Python-side ---
    def selection_df(self):
        """
        Return the current frontend selection as a pandas DataFrame.

        The JavaScript view writes the current selection into
        ``self.selection`` as a dictionary with keys:

        - ``"type"``: string describing how the selection was made
          (e.g. "brush", "click").
        - ``"keys"``: list of labels (from ``label_col``) that are
          currently selected.
        - ``"rows"``: list of row-like objects representing the selected
          entries in table form.

        This method extracts ``selection["rows"]`` and converts it to a
        :class:`pandas.DataFrame`. If no selection is present or
        ``"rows"`` is missing, an empty DataFrame is returned.

        Returns
        -------
        pandas.DataFrame
            Tabular view of the current selection, ready for further
            filtering, grouping or export from Python.
        """
        import pandas as pd
        return pd.DataFrame(self.selection.get("rows", []))

    def show_selection(self, head=None, *, return_df=False):
        """
        Display the selection DataFrame in the notebook and optionally return it.

        This is a convenience wrapper around :meth:`selection_df` that:

        - Builds the selection DataFrame.
        - Optionally truncates it to the first ``head`` rows.
        - Displays it using IPython's rich display.
        - Optionally returns the DataFrame to the caller.

        Parameters
        ----------
        head : int, optional
            If given, only the first ``head`` rows are displayed (similar
            to ``df.head(head)``). If ``None``, all rows are shown.
        return_df : bool, default False
            If True, the selection DataFrame is returned. If False,
            the function returns ``None`` and only produces visual output.

        Returns
        -------
        pandas.DataFrame or None
            The full selection DataFrame if ``return_df=True``, otherwise
            ``None``.
        """
        from IPython.display import display
        df = self.selection_df()
        if head is not None:
            df = df.head(head)
        display(df)
        return df if return_df else None

    def new_from_selection(self, **overrides):
        """
        Create a new ParallelEnergy widget restricted to the selected labels.

        This helper reads the current ``selection["keys"]`` (a list of
        labels, e.g. country names), filters the original DataFrame that
        was used to build the widget, and constructs a **new** instance
        of :class:`ParallelEnergy` using only those rows.

        The new instance inherits the current configuration, but you can
        override any of the constructor keyword arguments via
        ``**overrides``.

        Parameters
        ----------
        **overrides :
            Keyword arguments that override the defaults inferred from
            the current widget. For example:

            - ``width=900`` to change the chart width.
            - ``normalize=True`` to enable normalisation.
            - ``dims=("Solar", "Wind")`` to restrict to fewer dimensions.

            Internally the function passes:

            .. code-block:: python

                self.__class__(
                    sub_df, self._years,
                    tech_col=self._tech_col,
                    label_col=self._label_col,
                    dims=self._dims,
                    year_start=self.options.get("year_start"),
                    width=self.options.get("width"),
                    height=self.options.get("height"),
                    log_axes=self.options.get("log_axes"),
                    normalize=self.options.get("normalize"),
                    reorder=self.options.get("reorder"),
                    margin=self.options.get("margin"),
                    panel_position=self.options.get("panel_position", "right"),
                    panel_width=self.options.get("panel_width", 340),
                    panel_height=self.options.get("panel_height", 260),
                    **overrides,
                )

        Returns
        -------
        ParallelEnergy
            A new widget instance built from the subset of ``df`` whose
            ``label_col`` values are currently selected.

        Raises
        ------
        ValueError
            If there is no selection (i.e. ``selection["keys"]`` is
            empty).
        """
        keys = list(map(str, self.selection.get("keys", [])))
        if not keys:
            raise ValueError("No selection (keys is empty).")
        sub = self._df_raw[self._df_raw[self._label_col].astype(str).isin(keys)].copy()

        # take defaults from current chart; overrides wins
        kw = {
            "tech_col": self._tech_col,
            "label_col": self._label_col,
            "dims": self._dims,
            "year_start": self.options.get("year_start"),
            "width": self.options.get("width"),
            "height": self.options.get("height"),
            "log_axes": self.options.get("log_axes"),
            "normalize": self.options.get("normalize"),
            "reorder": self.options.get("reorder"),
            "margin": self.options.get("margin"),
            "panel_position": self.options.get("panel_position", "right"),
            "panel_width": self.options.get("panel_width", 340),
            "panel_height": self.options.get("panel_height", 260),
        }
        kw.update(overrides)  # overrides wins
        return self.__class__(sub, self._years, **kw)
