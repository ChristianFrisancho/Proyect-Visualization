import anywidget
import traitlets as T
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

class D3Heatmap(anywidget.AnyWidget):
    """
    Interactive D3-based heatmap widget driven by a pandas DataFrame.

    The Python side prepares a tidy table of cells with three fields:

    - ``row_id``: category on the y-axis (typically the DataFrame index).
    - ``col_id``: category on the x-axis (the DataFrame column names).
    - ``value``: numeric value for each (row_id, col_id) combination.

    These records are stored in ``self.data`` and consumed by the
    JavaScript code in ``assets/heatmap.js``, which renders the actual
    heatmap using D3.

    Synced traitlets
    ----------------
    data : list[dict]
        One dict per cell with keys ``row_id``, ``col_id`` and ``value``.
        Missing values (NaN) are converted to ``None`` so they can be
        serialised to JSON and are shown as “empty” cells in the frontend.
    options : dict
        Visual configuration passed to the JS view, including:

        - ``title``: title text drawn above the chart.
        - ``width`` / ``height``: total SVG size in pixels.
        - ``margin``: padding object with ``top/right/bottom/left``.
        - ``cmap``: colour map name (``"viridis"`` or ``"coolwarm"``).
        - ``xDomain``: ordered list of column labels.
        - ``yDomain``: ordered list of row labels.

        The JavaScript fallback logic uses ``xDomain`` / ``yDomain`` if
        present; otherwise it derives them from the data.
    """
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)

    def __init__(self, df, title="Heatmap", cmap="viridis", width=600, height=400, **kwargs):
        """
        Create a heatmap from a 2D pandas DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            2D table of values to visualise.

            - The **index** of ``df`` provides the y-axis categories and
              becomes the ``yDomain`` (and ``row_id`` values).
            - The **columns** of ``df`` provide the x-axis categories and
              become the ``xDomain`` (and ``col_id`` values).
            - The **cell values** should be numeric or convertible to
              numeric; missing values (NaN) are allowed and are rendered
              as grey, “no data” cells in the heatmap.

            Example shape:

                index: technologies, rows, countries, etc.
                columns: years, metrics, or any other discrete categories.

        title : str, default "Heatmap"
            Title text displayed above the heatmap in the notebook.

        cmap : {"viridis", "coolwarm"}, default "viridis"
            Name of the colour map used in the JS view:

            - ``"viridis"`` → continuous Viridis scale between min/max.
            - ``"coolwarm"`` → diverging RdBu scale, centred on zero.

        width : int, default 600
            Total width of the SVG in pixels (including margins).

        height : int, default 400
            Total height of the SVG in pixels (including margins).

        **kwargs :
            Extra visual options merged into ``self.options``. These are
            forwarded directly to the JS layer and can be used to tweak
            margins or extend the configuration in future versions.

        Notes
        -----
        The constructor:

        1. Loads ``assets/heatmap.js`` into ``self._esm`` (or displays an
           error message if the file is missing).
        2. Calls :meth:`set_data` to convert ``df`` into a list of
           ``{row_id, col_id, value}`` records.
        3. Sets up default ``options`` including size, title, colour map
           and a margin suited for rotated x-axis labels.
        """
        super().__init__()

        js_path = Path(__file__).parent / "assets" / "heatmap.js"
        if js_path.exists():
            self._esm = js_path.read_text(encoding="utf-8")
        else:
            self._esm = (
                "export async function render({ model, el }) {"
                "  el.innerHTML = '<div style=\"color:red\">heatmap.js not found</div>';"
                "}"
            )

        self.set_data(df)
        self.options = {
            "title": title,
            "width": width,
            "height": height,
            "cmap": cmap,
            "margin": {"top": 50, "right": 50, "bottom": 100, "left": 100},
            **kwargs,
        }

    def set_data(self, df):
        """
        Convert a pandas DataFrame into the internal heatmap data format.

        This method is responsible for reshaping the 2D input table into
        the cell-wise records expected by the D3 renderer.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame to visualise. Requirements:

            - Each **row index** label becomes a ``row_id`` (y-axis).
            - Each **column name** becomes a ``col_id`` (x-axis).
            - Each cell value is used as ``value`` for that
              (row_id, col_id) pair.

            The method makes a copy of the DataFrame, resets the index
            into a column named ``"row_id"``, and then uses
            :meth:`DataFrame.melt` to create a long-form table.

        Behaviour
        ---------
        - All records are stored in ``self.data`` as:

          .. code-block:: python

              {
                  "row_id": <index_label>,
                  "col_id": <column_name>,
                  "value": <numeric_or_None>,
              }

        - Any value for which ``pandas.isna(value)`` is true is converted
          to ``None`` so that JSON serialisation works and the frontend
          can treat it as missing data.
        - ``self.options["xDomain"]`` is set to the original list of
          column names, and ``self.options["yDomain"]`` to the original
          list of index labels. These domains control the ordering of
          rows and columns in the JS heatmap.
        """
        if pd is None:
            raise ImportError("Pandas es necesario para D3Heatmap")
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame")

        df_clean = df.copy()
        df_clean.index.name = "row_id"
        df_clean = df_clean.reset_index()

        melted = df_clean.melt(id_vars="row_id", var_name="col_id", value_name="value")
        records = melted.to_dict(orient="records")
        for r in records:
            if pd.isna(r["value"]):
                r["value"] = None

        self.data = records
        self.options = {
            **self.options,
            "xDomain": list(df.columns),
            "yDomain": list(df.index),
        }