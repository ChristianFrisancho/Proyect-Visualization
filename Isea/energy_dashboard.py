# Isea/energy_dashboard.py (VERSIÓN FINAL, FUNCIONAL)
from pathlib import Path
from IPython.display import HTML, display
import pandas as pd
import json


def _load_energy_data():
    """
    Carga Energy_clean.csv y transforma columnas F2000..F2023 en filas.
    Devuelve dict:
       { "rows": [...], "years": [...] }
    """
    here = Path(__file__).parent
    csv_path = here / "Energy_clean.csv"

    if not csv_path.exists():
        print("ERROR: No se encontró Energy_clean.csv")
        return {"rows": [], "years": []}

    df = pd.read_csv(csv_path)

    # Encontrar columnas F2000..F2023
    year_cols = [c for c in df.columns if c.startswith("F")]

    all_years = sorted([int(c[1:]) for c in year_cols])

    rows = []
    for _, r in df.iterrows():
        iso3 = str(r.get("ISO3", "")).upper()
        country = r.get("Country", "")
        tech = r.get("Technology", "")
        etype = r.get("Energy_Type", "")

        for col in year_cols:
            year = int(col[1:])
            val = r[col]
            try:
                val = float(val)
            except:
                val = 0

            rows.append({
                "ISO3": iso3,
                "Country": country,
                "Technology": tech,
                "Energy_Type": etype,
                "year": year,
                "Energy_Value": val
            })

    return {
        "rows": rows,
        "years": all_years
    }


def _load_assets():
    """Carga style.css y JS desde assets."""
    here = Path(__file__).parent
    assets = here / "assets"

    css = ""
    css_path = assets / "style.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")

    js_parts = []
    for name in [
        "theme.js",
        "bubble_map.js",
        "sunburst.js",
        "country_panel.js",
        "main.js",
    ]:
        p = assets / name
        if p.exists():
            js_parts.append(p.read_text(encoding="utf-8"))

    return css, "\n\n".join(js_parts)


def _build_html():
    css, js = _load_assets()
    data = _load_energy_data()

    # Serializamos la data para JS
    data_json = json.dumps(data, ensure_ascii=False)

    html = f"""
<style>
{css}
</style>

<div class="app-root">
  <header class="topbar">
    <div>
      <h1 class="title">Global Energy Dashboard</h1>
      <p>Explora energía renovable y no renovable por país y tecnología.</p>
    </div>

    <div class="topbar-right">
      <label class="year-control">
        <span>Año:</span>
        <input id="yearRange" type="range" min="2000" max="2023" step="1" value="2023" />
        <span id="yearLabel">2023</span>
      </label>
      <button id="playPause" class="btn">▶️</button>
      <button id="clearSelection" class="btn">🧹 Limpiar selección</button>
      <button id="theme-toggle" class="btn">Dark</button>
    </div>
  </header>

  <main class="layout">
    <section class="layout-main">
      <div id="bubble-map" class="panel panel-map"></div>
      <div id="sunburst"   class="panel panel-sunburst"></div>
    </section>

    <aside id="countryPanel" class="side-panel"></aside>
  </main>

  <div id="statusbar" class="statusbar"></div>
  <div id="tooltip"   class="tooltip"></div>
</div>

<!-- LIBRERÍAS -->
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://unpkg.com/topojson-client@3"></script>

<!-- DATA GLOBAL (clave para que funcione todo) -->
<script>
window.__ENERGY_DATA = {data_json};
window.__SELECTED_ISOS = [];
window.__CURRENT_YEAR = 2023;
</script>

<!-- SCRIPTS -->
<script>
{js}
</script>
"""

    return html


def show_energy_dashboard():
    display(HTML(_build_html()))
