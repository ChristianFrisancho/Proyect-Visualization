# Isea/energy_quad.py
import anywidget
import traitlets as T
import pandas as pd
from pathlib import Path
from typing import Sequence, Optional


class EnergyQuad(anywidget.AnyWidget):
    """
    Dashboard 2x2 enlazado (solo D3):
      - Parallel principal (izquierda arriba)
      - Tabla de selección (izquierda abajo)
      - Insight líneas % por tecnología (derecha arriba)
      - Parallel mini (derecha abajo) con MISMAS interacciones
    Un único slider de año sincroniza todo.
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
        return pd.DataFrame(self.selection.get("rows", []))

    def show_selection(self, head: Optional[int] = None) -> pd.DataFrame:
        from IPython.display import display
        df = self.selection_df()
        display(df.head(head) if head is not None else df)
        return df
