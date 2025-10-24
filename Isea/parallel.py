# Isea/parallel.py
import anywidget
import traitlets as T
import pandas as pd
from pathlib import Path
from typing import Sequence, Optional


class ParallelEnergy(anywidget.AnyWidget):
    """
    Parallel coordinates con:
      - Drag para reordenar ejes (líneas se mueven en vivo)
      - Brush vertical por eje
      - Slider de año
      - Click para (de)seleccionar líneas
      - Sync JS->PY en `selection` = {type, keys, rows}

    Métodos:
      - selection_df()           -> DataFrame con lo seleccionado
      - show_selection(head=None)-> imprime DF en la celda
      - new_from_selection(**o)  -> nuevo ParallelEnergy solo con seleccionados
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
        dims: Sequence[str] = ("Solar", "Wind", "Hydro", "Bio", "Fossil"),
        year_start: Optional[str] = None,
        width: int = 1150,
        height: int = 600,
        log_axes: bool = False,
        normalize: bool = False,
        reorder: bool = True,
        # NUEVO:
        margin: Optional[dict] = None,            # dict(top,left,right,bottom) o t,l,r,b
        panel_position: str = "right",            # "right" | "bottom"
        panel_width: int = 340,
        panel_height: int = 260,
    ):
        super().__init__()
        self._esm = (Path(__file__).parent / "assets" / "parallel.js").read_text()

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

        self.data = {"years": list(years), "dims": dims, "records": recs, "label": label_col}

        # opciones base
        self.options = {
            "width": int(width),
            "height": int(height),
            "log_axes": bool(log_axes),
            "normalize": bool(normalize),
            "reorder": bool(reorder),
            "year_start": year_start if (year_start in years) else years[-1],
            # NUEVO layout
            "panel_position": panel_position,
            "panel_width": int(panel_width),
            "panel_height": int(panel_height),
        }
        if margin:
            # admite keys: top/left/right/bottom o t/l/r/b
            self.options["margin"] = {
                "top":    margin.get("top",    margin.get("t", 105)),
                "right":  margin.get("right",  margin.get("r", 260)),
                "bottom": margin.get("bottom", margin.get("b", 40)),
                "left":   margin.get("left",   margin.get("l", 60)),
            }

        # guardar estado para clonar
        self._df_raw = df.copy()
        self._years = list(years)
        self._tech_col = tech_col
        self._label_col = label_col
        self._dims = tuple(dims)

        self.selection = {}

    # ------------ helpers PY ------------
    def selection_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.selection.get("rows", []))

    def show_selection(self, head: Optional[int] = None) -> pd.DataFrame:
        from IPython.display import display
        df = self.selection_df()
        display(df.head(head) if head is not None else df)
        return df

    def new_from_selection(self, **overrides):

        keys = list(map(str, self.selection.get("keys", [])))
        if not keys:
            raise ValueError("No hay selección (keys vacío).")
        sub = self._df_raw[self._df_raw[self._label_col].astype(str).isin(keys)].copy()

        # toma defaults del gráfico actual, y deja que overrides gane
        kw = {
            "tech_col": self._tech_col,
            "label_col": self._label_col,
            "dims": self._dims,
            "year_start": self.options.get("year_start"),
            "width": self.options.get("width"),
            "height": self.options.get("height"),
            "log_axes": self.options.get("log_axes"),
            "normalize": self.options.get("normalize"),
            "reorder": self.options.get("reorder"),
            "margin": self.options.get("margin"),
            "panel_position": self.options.get("panel_position", "right"),
            "panel_width": self.options.get("panel_width", 340),
            "panel_height": self.options.get("panel_height", 260),
        }
        kw.update(overrides)  # overrides manda
        return self.__class__(sub, self._years, **kw)

       
