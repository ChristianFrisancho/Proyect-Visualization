# Isea/worldmaplinechart.py
import json
import math
from pathlib import Path
import pandas as pd
import anywidget
import traitlets as T
from importlib.resources import files

class WorldMapLineChart(anywidget.AnyWidget):
    data = T.Dict(default_value={}).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        df: pd.DataFrame,
        year_cols=None,
        country_col="Country",
        iso3_col="ISO3",
        tech_col="Technology",
        value_is_numeric=True,
        tech_keep=None,
        tech_map=None,
        share_numerator=None,
        share_denominator=None,
        start_year=None,
        width=1200,
        height=660,
        normalize=False,
        title="Share over time by country",
        subtitle="Move the year slider. Click countries to compare.",
        share_label="Share",
    ):
        super().__init__()

        # --- 1) detect year columns ---
        if year_cols is None:
            year_cols = [c for c in df.columns if isinstance(c, str) and c.startswith("F")]
        if not year_cols:
            raise ValueError("No year columns found (expected F2000..FYYYY).")

        dfin = df.copy()
        if value_is_numeric:
            for c in year_cols:
                dfin[c] = pd.to_numeric(dfin[c], errors="coerce")

        # --- 2) setup buckets ---
        if tech_keep is None:
            tech_keep = ["Solar", "Wind", "Hydro", "Bio", "Fossil"]
        tech_keep = list(tech_keep)

        tech_map = tech_map or {}

        def bucket_of(src):
            tgt = tech_map.get(src, src)
            return tgt if tgt in tech_keep else None

        cols_needed = [country_col, iso3_col, tech_col] + year_cols
        missing = [c for c in cols_needed if c not in dfin.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        dfin["_bucket_"] = dfin[tech_col].map(bucket_of)
        d = dfin[dfin["_bucket_"].notna()][[country_col, iso3_col, "_bucket_"] + year_cols].copy()
        d.rename(columns={"_bucket_": "_bucket"}, inplace=True)

        # --- 3) aggregate ---
        agg = d.groupby([country_col, iso3_col, "_bucket"])[year_cols].sum(min_count=1).reset_index()

        # --- 4) prepare metadata ---
        countries = agg[[country_col, iso3_col]].drop_duplicates().values.tolist()
        years = list(year_cols)
        if start_year is None or start_year not in years:
            start_year = years[-1]
        idx_now = years.index(start_year)

        if share_numerator is None:
            share_numerator = [b for b in tech_keep if b != tech_keep[-1]]
        if share_denominator is None:
            share_denominator = list(tech_keep)

        # ---- NEW: detect absolute-value mode
        # If numerator and denominator buckets are identical, treat values as ABSOLUTE (no division).
        abs_mode = set(share_numerator) == set(share_denominator)

        # --- 5) build records ---
        records = []
        for name, iso3 in countries:
            block = agg[agg[iso3_col] == iso3]
            vals = {}
            for b in tech_keep:
                r = block[block["_bucket"] == b]
                if r.empty:
                    vals[b] = {y: 0.0 for y in years}
                else:
                    s = r.iloc[0][years].to_dict()
                    vals[b] = {y: float(s.get(y, 0.0)) if pd.notna(s.get(y, None)) else 0.0 for y in years}

            series = []
            for y in years:
                num = sum(vals[b][y] for b in share_numerator)
                if abs_mode:
                    # absolute numbers (e.g., totals or per-capita values already computed upstream)
                    v = num
                else:
                    den = sum(vals[b][y] for b in share_denominator)
                    v = (num / den) if (den and not math.isclose(den, 0.0)) else None
                series.append(v)

            rec = {"iso3": iso3, "name": name, "shares": series}  # 'shares' now means "values to map"
            for b in tech_keep:
                rec[b] = [vals[b][y] for y in years]
            records.append(rec)

        # --- 6) load world map ---
        world_text = (files("Isea.assets") / "world.geojson").read_text(encoding="utf-8")
        world_obj = json.loads(world_text)

        # --- 7) push to frontend ---
        self.data = {
            "years": years,
            "records": records,
            "world": world_obj,
            "techs": tech_keep,
        }
        self.options = {
            "width": width,
            "height": height,
            "idx_now": idx_now,
            "normalize": normalize,
            "title": title,
            "subtitle": subtitle,
            "share_label": share_label,
            "is_absolute": abs_mode,   # expose to JS (optional)
        }

        # --- 8) attach JS frontend ---
        self._esm = (Path(__file__).parent / "assets" / "worldmaplinechart.js").read_text()
