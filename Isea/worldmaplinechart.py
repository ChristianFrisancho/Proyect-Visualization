# ===============================================================
# WorldMapLineChart — EV-WIDE VERSION with METRIC SWITCHING
# ===============================================================

import json
import re
import pandas as pd
import anywidget
import traitlets as T
from pathlib import Path
from importlib.resources import files

# ---------------------------------------------------------------
# ISO3 mapping
# ---------------------------------------------------------------
ISO3_MAP = {
    "Australia": "AUS",
    "Austria": "AUT",
    "Belgium": "BEL",
    "Brazil": "BRA",
    "Bulgaria": "BGR",
    "Canada": "CAN",
    "Chile": "CHL",
    "China": "CHN",
    "Colombia": "COL",
    "Costa Rica": "CRI",
    "Croatia": "HRV",
    "Cyprus": "CYP",
    "Czech Republic": "CZE",
    "Denmark": "DNK",
    "Estonia": "EST",
    "Finland": "FIN",
    "France": "FRA",
    "Germany": "DEU",
    "Greece": "GRC",
    "Hungary": "HUN",
    "Iceland": "ISL",
    "India": "IND",
    "Indonesia": "IDN",
    "Ireland": "IRL",
    "Israel": "ISR",
    "Italy": "ITA",
    "Japan": "JPN",
    "Korea": "KOR",                 # your dataset uses "Korea"
    "Latvia": "LVA",
    "Lithuania": "LTU",
    "Luxembourg": "LUX",
    "Mexico": "MEX",
    "Netherlands": "NLD",
    "New Zealand": "NZL",
    "Norway": "NOR",
    "Poland": "POL",
    "Portugal": "PRT",
    "Rest of the world": "ROW",     # synthetic code
    "Romania": "ROU",
    "Russia": "RUS",
    "Saudi Arabia": "SAU",
    "Seychelles": "SYC",
    "Singapore": "SGP",
    "Slovakia": "SVK",
    "Slovenia": "SVN",
    "South Africa": "ZAF",
    "Spain": "ESP",
    "Sweden": "SWE",
    "Switzerland": "CHE",
    "Turkiye": "TUR",               # FIXED spelling
    "United Arab Emirates": "ARE",
    "United Kingdom": "GBR",
    "USA": "USA",                   # FIXED (dataset uses "USA")
}


# ---------------------------------------------------------------
class WorldMapLineChart(anywidget.AnyWidget):
    """
    Linked world map + line chart for EV metrics with year slider and metric switch.

    This widget shows:

    - A **choropleth world map** where colour indicates a selected EV metric
      for the current year (e.g. EV stock share, EV sales share).
    - A **time-series line chart** for the selected countries, with a Y-axis
      that adapts to the full time series of the selected set.
    - A **selection table** listing the selected countries and their value
      at the current year.

    Data model (Python → JS)
    ------------------------
    The widget expects a long-ish “wide-by-year” DataFrame and converts it
    into a compact structure stored in ``self.data``:

    .. code-block:: python

        self.data = {
            "years": ["F2010", "F2015", ...],   # for JS labels
            "years_num": [2010, 2015, ...],     # numeric years
            "records": [
                {
                    "iso3": "NLD",
                    "name": "Netherlands",
                    "values": [v_2010, v_2015, ...],
                },
                ...
            ],
            "world": <GeoJSON dict>,            # loaded from Isea.assets/world.geojson
        }

    The JavaScript module in ``assets/worldmaplinechart.js`` reads this
    structure and:

    - Colours each country via ``records[*].values[idx_now]``.
    - Draws one line per selected country using the **full** ``values`` list.
    - Uses ``years_num`` and ``years`` for the x-axis and labels.

    Synced traitlets
    ----------------
    data : dict
        Data package as described above.
    options : dict
        Frontend configuration, including at least:

        - ``metric``: name of the current metric (string).
        - ``width``, ``height``: overall layout size in pixels.
        - ``idx_now``: index of the currently selected year in ``years``.
        - ``title``: main title string.
        - ``subtitle``: optional subtitle string.

        The JS code reads these values to initialise the layout and
        respond to metric changes.

    selection : dict
        Written from the frontend when the user selects countries on
        the map. The structure is:

        .. code-block:: python

            {
                "iso3s": ["NLD", "NOR", ...],
                "year": 2023,
                "rows": [
                    {"Country": "Netherlands", "Value": 12.3},
                    {"Country": "Norway", "Value": 88.1},
                    ...
                ],
            }

        When the selection is cleared, JS resets it to an empty dict
        (``{}``). You can turn this into a DataFrame or use it to filter
        the original data.
    """

    data = T.Dict(default_value={}).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    # ================================
    # INIT
    # ================================
    def __init__(
        self,
        df: pd.DataFrame,
        metric: str,
        region_col="region",
        label_col="label",
        id_col="id",
        iso3_col=None,
        year_prefix="__F",
        width=1150,
        height=650,
        title="",
        subtitle="",
        **kwargs
    ):
        """
        Build a world map + line chart from a wide-by-year EV DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            Source table containing one row per country (or region) and
            one column per metric-year combination. It must include:

            - ``region_col`` (default ``"region"``):
              human-readable country/region name, e.g. "Netherlands",
              "Norway", "United States".
            - ``label_col`` (default ``"label"``):
              label used in the UI and selection table. Often identical
              to ``region_col`` but can be more user-friendly names.
            - ``id_col`` (default ``"id"``):
              arbitrary identifier column; kept mainly for completeness.
            - One column per **year** for each metric you want to use,
              following the pattern::

                  f"{metric}{year_prefix}{YYYY}"

              For example, if ``metric="EV_stockshare_total"`` and
              ``year_prefix="__F"``, valid column names would be:

              - ``"EV_stockshare_total__F2010"``
              - ``"EV_stockshare_total__F2015"``

              and so on. :meth:`_rebuild_records` will scan the columns
              using this pattern.

        metric : str
            Prefix of the metric to visualise (e.g. ``"EV_stockshare_total"``).
            This is stored in ``self.metric`` and used to find the relevant
            year columns when calling :meth:`_rebuild_records`. You can
            later change it using :meth:`set_metric`.

        region_col : str, default "region"
            Name of the DataFrame column that contains the country/region
            name used to derive ISO3 codes if ``iso3_col`` is not provided.

        label_col : str, default "label"
            Column used as the human-readable label in the JS UI and in
            the selection table (appears as ``"Country"`` in selection rows).

        id_col : str, default "id"
            Generic identifier column. It is stored on the Python side
            but is not strictly required by the JS view in this version.

        iso3_col : str or None, default None
            If provided, this column must contain ISO3 codes (e.g. "NLD",
            "NOR"). If ``None``, the constructor will:

            - Map ``df[region_col]`` to ISO3 using the built-in ``ISO3_MAP``.
            - Store the result in a temporary column ``"_iso3"``.
            - Use that as ``self.iso3_col`` for the rest of the widget.

            Any region names not found in ``ISO3_MAP`` are mapped to
            ``"UNK"`` and will not match countries in the world GeoJSON.

        year_prefix : str, default "__F"
            Separator between the metric name and the 4-digit year in the
            column names. For example, with ``metric="EV_stockshare_total"``
            and ``year_prefix="__F"``, columns are expected to look like
            ``"EV_stockshare_total__F2010"``.

        width : int, default 1150
            Overall width of the composed layout (map + line + table).

        height : int, default 650
            Overall height of the layout in pixels.

        title : str, optional
            Main title text; if empty, the metric name is used instead.

        subtitle : str, optional
            Subtitle or explanatory text displayed under the main title.

        **kwargs :
            Additional keyword arguments forwarded to ``anywidget.AnyWidget``,
            such as ``_model_name`` or internal traits. They are passed to
            ``super().__init__(**kwargs)`` unchanged.

        Behaviour
        ---------
        The constructor:

        1. Copies ``df`` internally (``self.df``) and stores column
           name parameters as attributes.
        2. If ``iso3_col`` is ``None``, maps ``region_col`` to ISO3 codes
           using ``ISO3_MAP``.
        3. Calls :meth:`_rebuild_records(self.metric)` to build the
           ``records`` list and the sorted list of numeric years.
        4. Loads the world GeoJSON from ``Isea.assets/world.geojson``.
        5. Stores the result in ``self.data`` and sets initial options
           in ``self.options`` (metric, width/height, current year index,
           title, subtitle).
        6. Loads the JavaScript implementation from
           ``assets/worldmaplinechart.js`` into ``self._esm`` (stripping
           a UTF-8 BOM if present).
        """
        super().__init__(**kwargs)

        self.df = df.copy()
        self.region_col = region_col
        self.label_col = label_col
        self.id_col = id_col
        self.year_prefix = year_prefix

        if iso3_col is None:
            self.df["_iso3"] = self.df[region_col].map(ISO3_MAP).fillna("UNK")
            self.iso3_col = "_iso3"
        else:
            self.iso3_col = iso3_col

        self.metric = metric
        self.width = width
        self.height = height
        self.title = title or metric
        self.subtitle = subtitle

        # Build initial records
        data_dict, years = self._rebuild_records(self.metric)

        # Load world geojson
        world_text = (files("Isea.assets") / "world.geojson").read_text()
        world_obj = json.loads(world_text)

        # Push to JS
        self.data = {
            "years": [f"F{y}" for y in years],
            "years_num": years,
            "records": data_dict,
            "world": world_obj,
        }

        self.options = {
            "metric": self.metric,
            "width": width,
            "height": height,
            "idx_now": len(years) - 1,
            "title": self.title,
            "subtitle": self.subtitle,
        }

        js_path = Path(__file__).parent / "assets" / "worldmaplinechart.js"
        # Read JS and strip a possible UTF-8 BOM so anywidget doesn't choke on it
        js_text = js_path.read_text(encoding="utf-8")
        if js_text.startswith("\ufeff"):
            js_text = js_text.lstrip("\ufeff")
        self._esm = js_text


    # ============================================================
    # INTERNAL: Rebuild records for a given metric
    # ============================================================
    def _rebuild_records(self, metric):
        """
        Internal helper to build records + year list for a given metric.

        This function inspects the columns of ``self.df`` and selects
        those that match the pattern::

            f"{metric}{self.year_prefix}{YYYY}"

        where ``YYYY`` is a 4-digit year. It then:

        1. Extracts all matching years into a sorted list.
        2. For each row in ``self.df``, builds a record:

           .. code-block:: python

               {
                   "iso3": <ISO3 code from self.iso3_col>,
                   "name": <label from self.label_col>,
                   "values": [v_YYYY1, v_YYYY2, ...],
               }

           where each value is:

           - ``float(v)`` if the cell is not NaN.
           - ``None`` if the cell is missing or NaN, so it can be safely
             serialised to JSON and handled as “no data” in the frontend.

        Parameters
        ----------
        metric : str
            Metric prefix to search for in the column names, typically the
            same string passed to :class:`WorldMapLineChart` at init time
            or via :meth:`set_metric`.

        Returns
        -------
        tuple[list[dict], list[int]]
            A pair ``(records, years)`` where:

            - ``records`` is the list of dicts described above.
            - ``years`` is the sorted list of integer years extracted from
              the column names.

        Raises
        ------
        ValueError
            If no columns in ``self.df`` match the metric/year pattern.
        """
        pat = re.compile(rf"^{metric}{self.year_prefix}(\d{{4}})$")
        years = []

        for col in self.df.columns:
            m = pat.match(str(col))
            if m:
                years.append(int(m.group(1)))

        years = sorted(years)
        if not years:
            raise ValueError(f"No columns found for metric: {metric}")

        records = []
        for _, row in self.df.iterrows():
            iso3 = str(row[self.iso3_col])
            name = str(row[self.label_col])

            values = []
            for y in years:
                col = f"{metric}{self.year_prefix}{y}"
                v = row.get(col, None)
                values.append(None if v is None or pd.isna(v) else float(v))

            records.append({
                "iso3": iso3,
                "name": name,
                "values": values
            })

        return records, years

    # ============================================================
    # PUBLIC: UPDATE METRIC (called by dropdown)
    # ============================================================
    def set_metric(self, new_metric):
        """
        Switch the active metric and rebuild data for the JS view.

        This method lets you reuse the same widget to show a different
        metric, provided the underlying DataFrame has the corresponding
        columns with the same ``year_prefix`` pattern.

        It:
        1. Updates ``self.metric`` to ``new_metric``.
        2. Calls :meth:`_rebuild_records(new_metric)` to compute a new
           set of records and years.
        3. Updates ``self.data["records"]`` and the ``"years"`` fields,
           keeping the already loaded world GeoJSON unchanged.
        4. Updates ``self.options["metric"]`` and ``self.options["idx_now"]``
           so the JS code can adjust the legend and Y-axis appropriately.

        Parameters
        ----------
        new_metric : str
            Name of the new metric prefix to visualise, following the same
            column naming convention as described in :meth:`__init__`. For
            example, switching from ``"EV_stockshare_total"`` to
            ``"EV_salesshare_total"`` (assuming both exist in the DataFrame).

        Notes
        -----
        - This method does **not** change the width, height, title or
          subtitle options; those remain whatever was set at construction
          time (or manually edited via ``self.options``).
        - The selection state is not reset here; the JS side will redraw
          the lines and map colours based on the new metric but using the
          same selection of countries until the user changes it.
        """
        self.metric = new_metric

        records, years = self._rebuild_records(new_metric)

        # Update data for JS
        self.data = {
            "years": [f"F{y}" for y in years],
            "years_num": years,
            "records": records,
            "world": self.data["world"],  # unchanged
        }

        # Update JS options
        self.options = {
            **self.options,   # keep title, width, height
            "metric": new_metric,
            "idx_now": len(years) - 1,
        }
