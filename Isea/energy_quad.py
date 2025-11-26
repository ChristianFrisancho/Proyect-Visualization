# Isea/energy_quad.py
import anywidget
import traitlets as T
import pandas as pd
from pathlib import Path
from typing import Sequence, Optional


class EnergyQuad(anywidget.AnyWidget):
    """
    Linked 2×2 energy dashboard widget built on top of a pandas DataFrame.

    This widget renders four coordinated D3 views for the same dataset:
      - Top-left: main parallel coordinates view.
      - Bottom-left: selection table.
      - Top-right: line chart with percentage contribution per technology.
      - Bottom-right: mini parallel view that mirrors the main interactions.

    All four views are synchronised by a single year slider. The Python side
    prepares an aggregated data structure from a long-format DataFrame, while
    the JavaScript code (in ``assets/energy_quad.js``) handles all drawing
    and interaction.

    Model traitlets
    ---------------
    data : dict
        Aggregated data passed to the frontend with the structure:

        .. code-block:: python

            {
                "years": [<year_col_1>, <year_col_2>, ...],
                "dims": ["Fossil", "Solar", ...],
                "records": [
                    {
                        "label": "<country_label>",
                        "<dim_1>": [v_year_1, v_year_2, ...],
                        "<dim_2>": [...],
                        ...
                    },
                    ...
                ],
                "label": "<name_of_label_column>",
            }

        All values are plain Python types (lists, floats, strings) so they
        can be JSON-serialised.

    options : dict
        Layout and behaviour options used by the D3 code, including:
        width/height of the panels, starting year, log/linear axes, whether
        to normalise values and whether reordering of axes is allowed.

    selection : dict
        Object populated from the JavaScript side when the user selects
        countries in either parallel view. Its structure is:

        .. code-block:: python

            {
                "type": "<interaction_type>",
                "keys": ["Country A", "Country B", ...],
                "rows": [
                    { "Country": "...", "Year": <int>, "<dim>": <value>, ... },
                    ...
                ],
            }

        The helpers :meth:`selection_df` and :meth:`show_selection` give a
        convenient tabular view of ``selection["rows"]`` for analysis in
        Python.
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
        dims: Sequence[str] = ("Fossil", "Solar", "Hydro", "Wind", "Bio"),
        year_start: Optional[str] = None,
        # Layout
        width: int = 1200,
        left_width: Optional[int] = None,  # si None => width - right_width - 12
        left_height: int = 460,
        table_height: int = 180,
        right_width: int = 420,
        insight_height: int = 230,
        mini_height: int = 260,
        # Opciones ejes
        log_axes: bool = False,
        normalize: bool = False,
        reorder: bool = True,
    ):
        """
        Build the EnergyQuad dashboard from a long-format energy DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            Long-format table with one row per (country, technology, …)
            and one column per year. At minimum it must contain:

            - ``tech_col`` (default ``"Technology_std"``): technology name
              for each row (e.g. "Fossil", "Solar").
            - ``label_col`` (default ``"Country"``): country label used in
              the UI (e.g. "Netherlands", "Germany").
            - One numeric column per year, whose column names are listed in
              ``years`` (e.g. "2010", "2015", "2020"). These will be coerced
              to numeric via ``pd.to_numeric(..., errors="coerce")``.

            The values in those year columns represent the magnitude used in
            the parallel views (for example TWh per technology and country).

        years : Sequence[str]
            List of column names in ``df`` that should be treated as time
            steps. Only names that actually exist in ``df.columns`` are kept;
            if none remain, a ``ValueError`` is raised. These values are
            passed unchanged to the frontend in ``data["years"]``.

        tech_col : str, default "Technology_std"
            Name of the column in ``df`` that identifies the technology
            category (e.g. "Fossil", "Solar", "Wind"). Only rows whose
            value is in ``dims`` are used.

        label_col : str, default "Country"
            Name of the column used as the main label for each record
            (for example the country name). This label is stored in
            ``"label"`` in the aggregated records and is also exposed to
            the frontend.

        dims : Sequence[str], default ("Fossil", "Solar", "Hydro", "Wind", "Bio")
            Ordered list of technology categories to include in the
            dashboard. These must correspond to values in ``df[tech_col]``.
            For every label (e.g. country), the widget builds one record
            containing one list of values per dimension across all years.

        year_start : str, optional
            Initial year shown when the dashboard loads. Must be one of the
            values in ``years``; if not, the last year in ``years`` is used
            as the starting point.

        width : int, default 1200
            Total width in pixels of the composed dashboard.

        left_width : int or None, default None
            Width in pixels of the left column (main parallel + table). If
            ``None``, it is computed as ``width - right_width - 12``.

        left_height : int, default 460
            Height in pixels of the top-left parallel coordinates view.

        table_height : int, default 180
            Height in pixels of the bottom-left selection table.

        right_width : int, default 420
            Width in pixels of the right column (insight + mini parallel).

        insight_height : int, default 230
            Height in pixels of the top-right insight line chart.

        mini_height : int, default 260
            Height in pixels of the bottom-right mini parallel view.

        log_axes : bool, default False
            If True, the frontend uses logarithmic scaling for axes where
            applicable.

        normalize : bool, default False
            If True, the frontend normalises values per dimension so that
            technologies become comparable even if they differ in absolute
            scale.

        reorder : bool, default True
            If True, the frontend allows the user to reorder axes in the
            parallel views.

        Notes
        -----
        Internally, the constructor:

        1. Filters ``df`` to keep only rows whose ``tech_col`` value is in
           ``dims``.
        2. Groups by ``[label_col, tech_col]`` and sums across the selected
           ``years``.
        3. Builds one record per label (e.g. country), where each dimension
           holds a list of values across all ``years``.
        4. Stores the result in ``self.data`` and layout/options in
           ``self.options``. These are then consumed by ``energy_quad.js``.
        """  
        super().__init__()
        self._esm = (Path(__file__).parent / "assets" / "energy_quad.js").read_text()

        years = [c for c in years if c in df.columns]
        if not years:
            raise ValueError("years no coincide con columnas del dataframe.")

        dfn = df.copy()
        for y in years:
            dfn[y] = pd.to_numeric(dfn[y], errors="coerce")

        if tech_col not in dfn.columns or label_col not in dfn.columns:
            raise KeyError("Faltan columnas requeridas.")

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

        self.data = {
            "years": list(years),
            "dims": list(dims),
            "records": recs,
            "label": label_col,
        }

        self.options = {
            "year_start": year_start if (year_start in years) else years[-1],
            "width": int(width),
            "left_width": int(left_width) if left_width is not None else None,
            "left_height": int(left_height),
            "table_height": int(table_height),
            "right_width": int(right_width),
            "insight_height": int(insight_height),
            "mini_height": int(mini_height),
            "log_axes": bool(log_axes),
            "normalize": bool(normalize),
            "reorder": bool(reorder),
        }

        # para helpers Python
        self._df_raw = df.copy()
        self._years = list(years)
        self._dims = tuple(dims)
        self._label_col = label_col

        self.selection = {}

    # -------- Helpers Python --------
    def selection_df(self) -> pd.DataFrame:
        """
        Return the current frontend selection as a pandas DataFrame.

        The JavaScript code stores the current selection in ``self.selection``
        with the structure:

        .. code-block:: python

            {
                "type": "<interaction_type>",
                "keys": ["Country A", "Country B", ...],
                "rows": [
                    { "Country": "...", "Year": <int>, "<dim>": <value>, ... },
                    ...
                ],
            }

        This method extracts ``selection["rows"]`` and converts it into a
        DataFrame. If there is no selection yet, an empty DataFrame is
        returned.

        Returns
        -------
        pandas.DataFrame
            Tabular view of the selected rows, suitable for further
            analysis, filtering or exporting from Python.
        """
        return pd.DataFrame(self.selection.get("rows", []))

    def show_selection(self, head: Optional[int] = None) -> pd.DataFrame:
        """
        Display the current selection as a DataFrame in the notebook.

        This is a convenience wrapper around :meth:`selection_df` that both
        *returns* the DataFrame and *displays* it using IPython's rich
        display.

        Parameters
        ----------
        head : int, optional
            If provided, only the first ``head`` rows of the selection are
            shown (similar to ``df.head(head)``). If ``None``, all selected
            rows are displayed.

        Returns
        -------
        pandas.DataFrame
            The full selection DataFrame (not just the truncated view),
            so it can be captured and reused in subsequent cells.
        """
        from IPython.display import display
        df = self.selection_df()
        display(df.head(head) if head is not None else df)
        return df
