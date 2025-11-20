import anywidget
import traitlets as T
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

class D3Heatmap(anywidget.AnyWidget):
    data = T.List(default_value=[]).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)

    def __init__(self, df, title="Heatmap", cmap="viridis", width=600, height=400, **kwargs):
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