# Isea/energy_dashboard.py (VERSIÓN FINAL, FUNCIONAL)
from pathlib import Path
from IPython.display import HTML, display
import pandas as pd
import json


def _load_energy_data():
    """
    Load the cleaned energy dataset and reshape it to a row-per-year format.

    This helper looks for a CSV file named ``Energy_clean.csv`` in the same
    folder as this module. The file is expected to have one row per
    (country, technology, energy type) and one column per year with names
    such as ``F2000``, ``F2001``, … up to ``F2023``. Typical columns are:

    - ``ISO3``: three-letter country code (e.g. "NLD").
    - ``Country``: human-readable country name.
    - ``Technology``: generation technology or fuel type.
    - ``Energy_Type``: high-level energy category.
    - ``FYYYY``: numeric value for that year (e.g. "F2015").

    The function converts these wide year columns into a list of records,
    one record per (row, year) combination, with the following keys:

    - ``ISO3``
    - ``Country``
    - ``Technology``
    - ``Energy_Type``
    - ``year`` (plain integer, e.g. 2015)
    - ``Energy_Value`` (float; non-numeric values are coerced to 0)

    Returns
    -------
    dict
        A dictionary with two keys:

        - ``"rows"``: list of per-year records as described above.
        - ``"years"``: sorted list of all year values found in the file.

    Notes
    -----
    This function is primarily intended for internal use by the dashboard,
    but can be reused if you keep the same input CSV structure.
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
    """Load CSS and JavaScript assets for the energy dashboard UI.

    The assets are expected in a subfolder named ``assets`` next to
    this Python file. The function:

    - Reads ``style.css`` into a single CSS string (if it exists).
    - Concatenates the contents of several JavaScript modules in
      the following order, if they exist:

      ``theme.js``, ``bubble_map.js``, ``sunburst.js``,
      ``country_panel.js``, ``main.js``.

    Returns
    -------
    tuple[str, str]
        A pair ``(css, js)`` where ``css`` is the full stylesheet
        and ``js`` is a single string with all JavaScript sources
        concatenated in order.
    """
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
    """Construct the full HTML document for the energy dashboard.

    This function pulls in the CSS and JavaScript assets via
    :func:`_load_assets` and the processed energy data via
    :func:`_load_energy_data`. It then embeds everything into a single
    HTML string that can be rendered inside a Jupyter notebook.

    The resulting HTML:

    - Inlines the CSS in a ``<style>`` block.
    - Creates the overall page layout (header, map, sunburst, panel).
    - Injects the energy data as a global ``window.__ENERGY_DATA`` object
      in a ``<script>`` tag.
    - Loads D3 and TopoJSON from public CDNs.
    - Appends the concatenated JavaScript modules that implement the
      interactive behaviour on the client side.

    Returns
    -------
    str
        A complete HTML document as a string, ready to be passed to
        :class:`IPython.display.HTML` or written to a standalone file.
    """
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
    """Display the interactive energy dashboard inside a Jupyter notebook.

    This is the main entry point for end users. Calling this function in
    a notebook cell will:

    - Load the energy data from ``Energy_clean.csv`` (using
      :func:`_load_energy_data`).
    - Load the CSS and JavaScript assets from the local ``assets`` folder.
    - Build the full HTML document with :func:`_build_html`.
    - Render the dashboard inline via :func:`IPython.display.HTML`.

    The function does not accept any parameters; it relies entirely on the
    presence and structure of the CSV file and asset files on disk.
    """
    display(HTML(_build_html()))
