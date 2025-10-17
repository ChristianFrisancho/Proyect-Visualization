# Isea/medias.py
import pandas as pd

TECH_MAP = {
    "Hydropower (excl. Pumped Storage)": "Hydro",
    "Solar energy": "Solar",
    "Wind energy": "Wind",
    "Bioenergy": "Bio",
    "Fossil fuels": "Fossil",
}

def detect_year_cols(df):
    cols = [c for c in df.columns if isinstance(c, str) and c.startswith("F") and df[c].notna().any()]
    if not cols:
        raise ValueError("No se encontraron columnas anuales Fxxxx con datos.")
    return cols

def prepare_energy(df):
    """
    Devuelve un paquete con:
      - df_filtrado (solo Installed Capacity / MW + Technology_std)
      - year_cols
      - year_default (último)
      - piv (Country×tech con valores del año default)
      - column set ['Solar','Wind','Hydro','Bio','Fossil']
    """
    df = df.copy()
    if {"Indicator","Unit"}.issubset(df.columns):
        df = df[(df["Indicator"]=="Electricity Installed Capacity") & (df["Unit"]=="Megawatt (MW)")].copy()

    if "Technology_std" not in df.columns:
        df["Technology_std"] = df["Technology"].map(TECH_MAP).fillna(df["Technology"])

    year_cols = detect_year_cols(df)
    year_default = "F2023" if "F2023" in year_cols else year_cols[-1]

    # pivot por año_default para cosas rápidas (ej. scatter/bubble)
    tech_keep = ["Solar","Wind","Hydro","Bio","Fossil"]
    piv = (df.pivot_table(index=["Country","ISO3"], columns="Technology_std",
                          values=year_default, aggfunc="sum")
             .reindex(columns=tech_keep)
             .fillna(0.0)
             .reset_index())

    return dict(
        df=df,
        year_cols=year_cols,
        year_default=year_default,
        tech_keep=["Solar","Wind","Hydro","Bio","Fossil"],
        piv=piv,
    )
