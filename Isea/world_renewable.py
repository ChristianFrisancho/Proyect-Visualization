import json
import math
from pathlib import Path
import pandas as pd
import anywidget
import traitlets as T
from importlib.resources import files

class WorldRenewable(anywidget.AnyWidget):
    data = T.Dict(default_value={}).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        df,
        year_cols=None,
        country_col="Country",
        iso3_col="ISO3",
        tech_col="Technology_std",
        start_year=None,
        width=1200,
        height=660,
        normalize=False,
    ):
        super().__init__()

        # 1) Detect year columns (e.g., F2000..F2023)
        if year_cols is None:
            year_cols = [c for c in df.columns if isinstance(c, str) and c.startswith("F")]
        if not year_cols:
            raise ValueError("No year columns found (expected F2000..F2023).")

        # 2) Ensure numeric
        df = df.copy()
        for c in year_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # 3) Keep only five technologies
        tech_keep = ["Solar", "Wind", "Hydro", "Bio", "Fossil"]
        d = df[df[tech_col].isin(tech_keep)][[country_col, iso3_col, tech_col] + year_cols].copy()

        # 4) Aggregate by country + tech
        agg = d.groupby([country_col, iso3_col, tech_col])[year_cols].sum(min_count=1).reset_index()

        # 5) Build records per country with per-tech arrays (for the table) and renewable shares
        countries = agg[[country_col, iso3_col]].drop_duplicates().values.tolist()
        years = list(year_cols)
        if start_year is None or start_year not in years:
            start_year = years[-1]

        records = []
        for name, iso3 in countries:
            block = agg[agg[iso3_col] == iso3]
            vals = {}
            for t in tech_keep:
                r = block[block[tech_col] == t]
                if r.empty:
                    vals[t] = {y: 0.0 for y in years}
                else:
                    s = r.iloc[0][years].to_dict()
                    vals[t] = {y: float(s.get(y, 0.0)) if pd.notna(s.get(y, None)) else 0.0 for y in years}

            shares = []
            for y in years:
                ren = vals["Solar"][y] + vals["Wind"][y] + vals["Hydro"][y] + vals["Bio"][y]
                tot = ren + vals["Fossil"][y]
                shares.append((ren / tot) if (tot and not math.isclose(tot, 0.0)) else None)

            rec = {
                "iso3": iso3,
                "name": name,
                "shares": shares,
                "Fossil": [vals["Fossil"][y] for y in years],
                "Solar":  [vals["Solar"][y]  for y in years],
                "Wind":   [vals["Wind"][y]   for y in years],
                "Hydro":  [vals["Hydro"][y]  for y in years],
                "Bio":    [vals["Bio"][y]    for y in years],
            }
            records.append(rec)

        idx_now = years.index(start_year)

        # 6) Load world.geojson from package
        try:
            world_text = (files("Isea.assets") / "world.geojson").read_text(encoding="utf-8")
            world_obj = json.loads(world_text)
        except Exception as e:
            raise FileNotFoundError(
                "Missing Isea/assets/world.geojson. Place it under Isea/assets/ and include 'Isea/assets/**' in pyproject.toml."
            ) from e

        self.data = {
            "years": years,
            "records": records,
            "world": world_obj,
        }

        self.options = {
            "width": width,
            "height": height,
            "idx_now": idx_now,
            "normalize": normalize,
        }

        # Front-end ESM
        self._esm = (Path(__file__).parent / "assets" / "worldrenewable.js").read_text()
