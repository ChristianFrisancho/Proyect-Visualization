# Proyect-Visualization
OPTION 1:

STEP 1: Run this commands on terminal:

pip install -U pip

pip install anywidget traitlets

pip install -e .

run P6_deliverable_final.ipynb

OPTION 2(more easy):

Step 1 — Open Colab

1. Go to 👉 [https://colab.research.google.com](https://colab.research.google.com)

2. Create a new collab

3. Run this commands on collab:

!pip install -q isea-vis==0.1.1

!pip install pycountry_convert

!pip install country_converter

Step 2 — Upload and load the dataset

You must upload your data file to Colab.  
Assume your dataset is called `Global_EV_clean.csv`:

1. In the left sidebar in Colab, open the Files tab.  
2. Click the "upload icon" and select your local CSV file.  
3. Verify that the file appears under `/content` in the file list.

Now create a new cell in Colab and paste:


Load the dataset
```python
import pandas as pd
import re
df = pd.read_csv("Renewable_Energy.csv")
```

Check that it was loaded correctly
```python
print(" File loaded successfully loaded:", df.shape)
df.head()
```

Step 3 — Basic exploratory analysis

Create another cell and paste:

```python
df.info()
print("\nMissing values per column:")
print(df.isnull().sum())
df.describe()
```

This gives you a quick overview of the structure and quality of your data.

Step 4 — making the dataset ready to be used

Configuration of the dataset for a correct run:

```python
f = df
iso2_clean = f["ISO2"].astype(str).str.strip()
f = f[iso2_clean.ne("") & f["ISO2"].notna()].copy()
year_cols = sorted([c for c in f.columns if re.fullmatch(r"F\d{4}", c)])
for c in year_cols:
    f[c] = pd.to_numeric(f[c], errors="coerce")
tech_map = {
    "Hydropower (excl. Pumped Storage)": "Hydro",
    "Solar energy": "Solar",
    "Wind energy": "Wind",
    "Bioenergy": "Bio",
    "Fossil fuels": "Fossil",
}
f["Technology_std"] = f["Technology"].map(tech_map).fillna(f["Technology"])

def extract_abbr(unit: str):
    if not isinstance(unit, str):
        return None
    m = re.search(r"\b(MW|GWh)\b", unit, flags=re.IGNORECASE)
    return m.group(1).upper() if m else None
f["UnitAbbr"] = f["Unit"].apply(extract_abbr)
f = f[f["UnitAbbr"].notna()].copy()
f["TechUnit"] = f["Technology_std"].astype(str).str.strip() + " (" + f["UnitAbbr"] + ")"
def add_continent_from_iso2(df: pd.DataFrame) -> pd.DataFrame:
    s = df["ISO2"].astype(str).str.strip().str.upper().replace({"": None, "NA": None, "NAN": None})
    import country_converter as coco
    cc = coco.CountryConverter()
    cont_list = cc.convert(names=s.tolist(), src="ISO2", to="continent", not_found=None)
    cont_series = pd.Series(cont_list, index=df.index)
    df["Continent"] = cont_series.fillna("Unknown")
    return df

    
    from pycountry_convert import (
        country_alpha2_to_continent_code as a2_to_cc,
        convert_continent_code_to_continent_name as cc_to_name,
    )
    def conv(a2):
      return cc_to_name(a2_to_cc(a2))

    cont_series = s.map(conv).fillna("Unknown")
    df["Continent"] = cont_series
    return df
f = add_continent_from_iso2(f)
if "ObjectId" not in f.columns:
    f["ObjectId"] = range(1, len(f) + 1)


agg = f.groupby(["Country","Continent","TechUnit"], as_index=False)[year_cols].sum()   
long = agg.melt(id_vars=["Country","Continent","TechUnit"],                             
                value_vars=year_cols, var_name="YearCol", value_name="Value")
long["col"] = long["TechUnit"] + "__" + long["YearCol"]
wide = (long.pivot_table(index=["Country","Continent"], columns="col",             
                         values="Value", aggfunc="sum")
            .reset_index()
            .fillna(0.0))

df_wide = wide  
tech_options = sorted(f["TechUnit"].unique().tolist()) 
xy_kwargs = {f"XY_var{i+1}": t for i, t in enumerate(tech_options)} 

print(f"Wide shape: {df_wide.shape}  | TechUnits: {len(tech_options)}  | Years: {len(year_cols)}")

continent_colors = {
    "Asia": "#1f77b4",
    "Europe": "#ff7f0e",
    "Africa": "#2ca02c",
    "Oceania": "#d62728",
    "America": "#9467bd",
}

df_wide

```

Step 5 — Scatter visualization with isea-vis

```python
from Isea.scatter import ScatterBrush
import re


years_int = sorted({int(m.group(1)) for c in df_wide.columns
                    for m in [re.search(r"__F(\d{4})$", str(c))] if m})
year_min, year_max = years_int[0], years_int[-1]


xy_kwargs = {f"XY_var{i+1}": t for i, t in enumerate(tech_options, start=1)}

rows = df_wide.to_dict("records")   

w_scatter = ScatterBrush(
    data=rows,
    x=tech_options[1], y=tech_options[3],
    color="Continent",
    colorMap=continent_colors,
    label="Country",    
    key="Country",      
    width=1200, height=500,
    panel_position="right", panel_width=320, panel_height=220,
    YearMin=year_min, YearMax=year_max,
    **xy_kwargs,
)
display(w_scatter)
```
If you want the same graph but with countries selected you can use this:
```python

opts = getattr(w_scatter, "options", {}) or {}
x_col = getattr(w_scatter, "x", None) or opts.get("x")
y_col = getattr(w_scatter, "y", None) or opts.get("y")
label_col = getattr(w_scatter, "label", None) or opts.get("label") or "Country"
color_col = getattr(w_scatter, "color", None) or opts.get("color") or "Continent"
key_col   = getattr(w_scatter, "key", None)   or opts.get("key")   or "Country"
xy_kwargs = {f"XY_var{i+1}": t for i, t in enumerate(tech_options, start=1)}
w_scatter_sel = ScatterBrush(
    data=pd.DataFrame([], columns=[label_col, color_col, key_col]).to_dict("records"),
    x=x_col, y=y_col,
    color=color_col,colorMap=continent_colors,
    label=label_col, key=key_col,
    width=900, height=450, panel_position="right", panel_height=160,
    YearMin=year_min, YearMax=year_max,
    **xy_kwargs,
)
display(w_scatter_sel)
df_selected = pd.DataFrame(columns=df_wide.columns)


def _link_selection_to_second(change):
    global df_selected
    sel = change.get("new") or {}
    rows = sel.get("rows") or []
    countries = [r.get("Country") or r.get(label_col) or r.get(key_col) for r in rows]
    countries = [c for c in countries if isinstance(c, str)]

    if countries:
        df_selected = df_wide[df_wide["Country"].isin(countries)].copy()
    else:
        df_selected = pd.DataFrame(columns=df_wide.columns)
    cur_x = getattr(w_scatter, "x", None) or opts.get("x")
    cur_y = getattr(w_scatter, "y", None) or opts.get("y")
    w_scatter_sel.data = (
        df_selected.assign(key=lambda d: d["Country"], label=lambda d: d["Country"])
                   .to_dict("records")
    )
    if cur_x and cur_y:
        w_scatter_sel.x = cur_x
        w_scatter_sel.y = cur_y
    w_scatter_sel.selection = {"type": None, "keys": [], "rows": [], "epoch": int(__import__("time").time()*1000)}

w_scatter.observe(_link_selection_to_second, names="selection")
```
Step 6 — “World Line Chart” map

Create a new cell and paste:

```python
from Isea import WorldRenewable
from IPython.display import display

df_world = df
year_cols = [c for c in df_world.columns if c.startswith("F")]
for c in year_cols:
    df_world[c] = pd.to_numeric(df_world[c], errors="coerce")

tech_map = {
    "Hydropower (excl. Pumped Storage)": "Hydro",
    "Solar energy": "Solar",
    "Wind energy": "Wind",
    "Bioenergy": "Bio",
    "Fossil fuels": "Fossil",
}
df_world["Technology_std"] = df_world["Technology"].map(tech_map).fillna(df_world["Technology"])
world_widget = WorldRenewable(
    df=df_world,
    year_cols=year_cols,
    country_col="Country",
    iso3_col="ISO3",
    tech_col="Technology_std",
    start_year="F2023", 
    width=1200,
    height=660,
    normalize=False
)

display(world_widget)
print(" WorldRenewable widget created successfully!")

def on_world_selection(change):
    sel = change["new"]
    if sel and sel.get("iso3"):
        year = sel.get('year', 'N/A')
        value = sel.get('value')
        value_str = f"{value:.1%}" if value is not None else "N/A"
        print(f"Selected: {sel['name']} ({sel['iso3']}) - Year {year} - Renewable: {value_str}")

world_widget.observe(on_world_selection, names="selection")
```

With this , you can create 2 interactive visualizations and we and if you liked it, we invite you to see the other graphics that are on our ipynb page on our GitHub.

