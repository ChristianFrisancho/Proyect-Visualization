import json, uuid
from IPython.display import HTML, Javascript, display
import pandas as pd

def ScatterBrush(df, x, y, color='origin', width=820, height=480):
    # 1) asegurar tipos numéricos
    df = df.copy()
    for col in (x, y):
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[[x, y, color]].dropna()

    data = df.to_dict(orient="records")
    payload = json.dumps(data, ensure_ascii=False)
    uid = f"sc-{uuid.uuid4().hex[:8]}"

    # 2) contenedor
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Cargando…</div>
<style>
  .vis {{ width: 100%; min-height: 80px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
  .axis path, .axis line {{ shape-rendering: crispEdges; }}
</style>
"""))

    # 3) JS robusto (D3 ESM + fallback de colores + errores visibles)
    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    // D3 como módulo ESM
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = ''; // limpiar por re-ejecución

    const data  = {payload};
    const W={width}, H={height}, m={{top:24,right:16,bottom:36,left:44}};
    const iW = W - m.left - m.right, iH = H - m.top - m.bottom;

    const svg = d3.select(mount).append('svg')
      .attr('width', W).attr('height', H);
    const g = svg.append('g').attr('transform', `translate(${{m.left}},${{m.top}})`);

    const x = d3.scaleLinear()
      .domain(d3.extent(data, d => +d['{x}'])).nice()
      .range([0, iW]);
    const y = d3.scaleLinear()
      .domain(d3.extent(data, d => +d['{y}'])).nice()
      .range([iH, 0]);

    g.append('g').attr('transform', `translate(0,${{iH}})`).call(d3.axisBottom(x));
    g.append('g').call(d3.axisLeft(y));

    const cats = [...new Set(data.map(d => d['{color}']))];
    const color = d3.scaleOrdinal(cats, d3.schemeCategory10);

    const dots = g.selectAll('circle').data(data).join('circle')
      .attr('r', 3.5)
      .attr('cx', d => x(+d['{x}']))
      .attr('cy', d => y(+d['{y}']))
      .attr('fill', d => color(d['{color}']))
      .attr('opacity', 0.95);

    const brush = d3.brush()
      .extent([[0,0],[iW,iH]])
      .on('brush end', (ev) => {{
        const sel = ev.selection;
        if (!sel) {{
          dots.attr('opacity', 0.95).attr('stroke', null);
          status.textContent = 'Tip: arrastra para seleccionar. Doble clic limpia.';
          window._lastSelection = null;
          return;
        }}
        const [[x0,y0],[x1,y1]] = sel;
        let count = 0;
        dots
          .attr('opacity', d => {{
            const hit = (x0 <= x(+d['{x}']) && x(+d['{x}']) <= x1 &&
                         y0 <= y(+d['{y}']) && y(+d['{y}']) <= y1);
            if (hit) count++;
            return hit ? 1 : 0.2;
          }})
          .attr('stroke', d => {{
            const hit = (x0 <= x(+d['{x}']) && x(+d['{x}']) <= x1 &&
                         y0 <= y(+d['{y}']) && y(+d['{y}']) <= y1);
            return hit ? '#111' : null;
          }})
          .attr('stroke-width', d => {{
            const hit = (x0 <= x(+d['{x}']) && x(+d['{x}']) <= x1 &&
                         y0 <= y(+d['{y}']) && y(+d['{y}']) <= y1);
            return hit ? 1.1 : null;
          }});
        status.textContent = `Seleccionados: ${{count}} punto(s).`;
      }});

    const gBrush = g.append('g').attr('class','brush').call(brush);
    svg.on('dblclick', () => gBrush.call(brush.move, null));

    status.textContent = 'Tip: arrastra para seleccionar. Doble clic limpia.';
  }} catch (e) {{
    const msg = (e && e.stack) ? e.stack : (''+e);
    document.getElementById('{uid}-status').textContent = 'Error al renderizar: ' + msg;
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>ScatterBrush listo (#{uid})</small>")
