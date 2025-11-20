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
        """Rebuild data.series + notify JS."""
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
