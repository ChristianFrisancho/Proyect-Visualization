import json
import uuid
import pandas as pd
import numpy as np
import traitlets as T
import anywidget
from pathlib import Path

from typing import Optional, List, Dict, Any


class RadialStackedBar(anywidget.AnyWidget):
    """
    Radial Stacked Bar Chart con widgets anywidget.
    """
    
    # ========== IMPORTANTE: Cargar JavaScript ==========
    _esm = Path(__file__).parent / "assets" / "radial_stacked_bar.js"
    
    # ========== Traits (sincronizados con JS) ==========
    data = T.Dict(default_value={}).tag(sync=True)
    options = T.Dict(default_value={}).tag(sync=True)
    selection = T.Dict(default_value={}).tag(sync=True)
    
    # ========== Atributos internos (no sincronizados) ==========
    _df_raw: pd.DataFrame = None
    _group_col: str = None
    _category_col: str = None
    _year_cols: List[str] = None
    _year_start: str = None
    _agg: str = 'sum'
    
    def __init__(
        self,
        df: pd.DataFrame,
        group_col: str,
        category_col: str,
        year_cols: Optional[List[str]] = None,
        year_start: Optional[str] = None,
        agg: str = 'sum',
        width: int = 900,
        height: int = 900,
        inner_radius: int = 200,
        pad_angle: float = 0.015,
        color_scheme: str = 'schemeSpectral',
        sort_on_click: bool = True,
        title: Optional[str] = None,
        custom_colors: Optional[List[str]] = None,
        **kwargs
    ):
        """Inicializa RadialStackedBar."""
        super().__init__(**kwargs)
        
        # Guardar referencias
        self._df_raw = df.copy()
        self._group_col = group_col
        self._category_col = category_col
        self._agg = agg
        
        # Detectar años si no se proporciona
        if year_cols is None:
            year_cols = [c for c in df.columns if isinstance(c, str) and c.startswith("F")]
        
        if not year_cols:
            raise ValueError("No se encontraron columnas de año (Fxxxx).")
        
        self._year_cols = year_cols
        
        # Detectar año inicial
        if year_start is None or year_start not in year_cols:
            year_start = year_cols[-1]
        
        self._year_start = year_start
        
        # ========== Preparar datos ==========
        self._prepare_data()
        
        # ========== Configurar options ==========
        self.options = {
            "year_start": year_start,
            "width": width,
            "height": height,
            "inner_radius": inner_radius,
            "pad_angle": pad_angle,
            "color_scheme": color_scheme,
            "sort_on_click": sort_on_click,
            "title": title or category_col,
            "custom_colors": custom_colors,
        }
    
    def _prepare_data(self) -> None:
        """Prepara datos en formato esperado por JS."""
        
        df = self._df_raw.copy()
        
        # Asegurar columnas numéricas
        for col in self._year_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Limpiar
        df = df.dropna(subset=[self._group_col, self._category_col])
        
        # ✅ NUEVO: Filtrar años con datos
        valid_years = [
            y for y in self._year_cols 
            if y in df.columns and df[y].notna().any()
        ]
        
        if not valid_years:
            raise ValueError(f"No hay datos en las columnas de año: {self._year_cols}")
        
        # Agregar por grupo y categoría
        grouped = df.groupby([self._group_col, self._category_col])[valid_years].agg(
            self._agg
        ).reset_index()
        
        # ✅ NUEVO: Eliminar filas donde TODOS los años son 0 o NaN
        grouped["_total"] = grouped[valid_years].sum(axis=1)
        grouped = grouped[grouped["_total"] > 0].drop(columns=["_total"])
        
        if grouped.empty:
            raise ValueError("No hay datos después de filtrar valores cero.")
        
        # Construir records
        records = []
        categories = sorted(df[self._category_col].dropna().unique())
        groups = sorted(df[self._group_col].dropna().unique())
        
        for group in groups:
            record = {"group": str(group)}
            has_data = False
            
            for category in categories:
                subset = grouped[
                    (grouped[self._group_col] == group) &
                    (grouped[self._category_col] == category)
                ]
                
                if subset.empty:
                    record[str(category)] = [0.0] * len(valid_years)
                else:
                    row = subset.iloc[0]
                    values = [
                        float(row[y]) if pd.notna(row[y]) else 0.0
                        for y in valid_years
                    ]
                    record[str(category)] = values
                    if sum(values) > 0:
                        has_data = True
            
            # ✅ NUEVO: Solo agregar si el grupo tiene AL MENOS algo de datos
            if has_data:
                records.append(record)
        
        if not records:
            raise ValueError("No hay grupos con datos después de filtrar.")
        
        # Actualizar trait data
        self.data = {
            "years": valid_years,
            "categories": [str(c) for c in categories],
            "records": records,
        }
    
    def selection_df(self) -> pd.DataFrame:
        """Retorna DataFrame con datos seleccionados."""
        rows = self.selection.get("rows", [])
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)
    
    def show_selection(self, head: Optional[int] = None) -> pd.DataFrame:
        """Muestra tabla de selección."""
        from IPython.display import display
        
        df_sel = self.selection_df()
        
        if df_sel.empty:
            print("ℹSin selección. Haz clic en segmentos del gráfico para seleccionar.")
            return df_sel
        
        print(f"✅ Selección: {len(df_sel)} puntos")
        display(df_sel.head(head) if head else df_sel)
        
        return df_sel
    
    def new_from_selection(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        **overrides
    ) -> "RadialStackedBar":
        """Crea nuevo RadialStackedBar con datos seleccionados."""
        
        keys = self.selection.get("keys", [])
        
        if not keys:
            raise ValueError(
                "No hay selección. "
                "Haz clic en segmentos del gráfico para seleccionar grupos."
            )
        
        sub_df = self._df_raw[
            self._df_raw[self._group_col].astype(str).isin(keys)
        ].copy()
        
        if sub_df.empty:
            raise ValueError(f"No hay datos para los grupos seleccionados: {keys}")
        
        config = {
            "group_col": self._group_col,
            "category_col": self._category_col,
            "year_cols": self._year_cols,
            "year_start": self._year_start,
            "agg": self._agg,
            "width": width or self.options.get("width", 900),
            "height": height or self.options.get("height", 900),
            "inner_radius": self.options.get("inner_radius", 200),
            "pad_angle": self.options.get("pad_angle", 0.015),
            "color_scheme": self.options.get("color_scheme", "schemeSpectral"),
            "sort_on_click": self.options.get("sort_on_click", True),
            "title": self.options.get("title", "Drill-down"),
            "custom_colors": self.options.get("custom_colors"),
        }
        
        config.update(overrides)
        
        return self.__class__(sub_df, **config)
    
    def clear_selection(self) -> None:
        """Limpia la selección."""
        self.selection = {"type": "", "keys": [], "rows": []}
    
    def get_groups(self) -> List[str]:
        """Retorna lista de grupos."""
        if not self.data or not self.data.get("records"):
            return []
        return [r.get("group") for r in self.data["records"]]
    
    def get_categories(self) -> List[str]:
        """Retorna lista de categorías."""
        return self.data.get("categories", [])
    
    def get_years(self) -> List[str]:
        """Retorna lista de años."""
        return self.data.get("years", [])


__all__ = ["RadialStackedBar"]