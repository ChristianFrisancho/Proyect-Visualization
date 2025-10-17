# graphs.py
import json, uuid
from IPython.display import HTML, Javascript, display
import pandas as pd
import numpy as np

# ========== Helpers ==========
def _to_numeric_cols(df, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns and not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _display_container(uid, min_h):
    html = f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Cargando…</div>
<style>
  .vis {{ width: 100%; min-height: {min_h}px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
  .axis path, .axis line {{ shape-rendering: crispEdges; }}
</style>
"""
    display(HTML(html))

def ScatterBrush(
    df,
    x,
    y,
    color=None,          # columna categórica para colorear + leyenda
    size=None,           # (opcional) columna numérica para tamaño
    label=None,          # (opcional) columna mostrada en tooltip
    width=900,
    height=560,
    zero_filter=True,    # filtra puntos (0,0)
    log_x=False,
    log_y=False,
):
    """
    Scatter D3 sin brush con:
      - tooltip (label + x/y + size)
      - leyenda de color
      - títulos de ejes y grilla
      - (opcional) tamaño ~ size y escalas log
    """
    import json, uuid
    import pandas as pd
    from IPython.display import HTML, Javascript, display

    # Validación
    cols = [x, y] + ([color] if color else []) + ([size] if size else []) + ([label] if label else [])
    miss = [c for c in cols if c and c not in df.columns]
    if miss:
        raise KeyError(f"Faltan columnas {miss}. Disponibles: {list(df.columns)}")

    # Limpieza mínima
    df = df.copy()
    for c in [x, y, size]:
        if c and not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=[x, y])
    if zero_filter:
        df = df.loc[~((df[x]==0) & (df[y]==0))]
    if log_x:
        df = df.loc[df[x] > 0]
    if log_y:
        df = df.loc[df[y] > 0]
    if df.empty:
        return display(HTML("<em>No hay datos para graficar (revisa filtros/columnas).</em>"))

    payload  = json.dumps(df.to_dict(orient="records"), ensure_ascii=False)
    XCOL     = json.dumps(x)
    YCOL     = json.dumps(y)
    CCOL     = json.dumps(color or "")
    SCOL     = json.dumps(size or "")
    LCOL     = json.dumps(label or "")

    uid = f"sc-{uuid.uuid4().hex[:8]}"

    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Renderizando…</div>
<style>
  .vis {{ width: 100%; min-height: 80px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
</style>
"""))

    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    const data     = {payload};
    const XCOL     = {XCOL};
    const YCOL     = {YCOL};
    const COLORCOL = {CCOL};
    const SIZECOL  = {SCOL};
    const LABELCOL = {LCOL};

    const W = {width}, H = {height};
    const hasLegend = !!COLORCOL;
    const m = hasLegend ? {{top: 28, right: 140, bottom: 56, left: 64}} : {{top: 28, right: 24, bottom: 56, left: 64}};
    const iW = W - m.left - m.right, iH = H - m.top - m.bottom;

    const svg = d3.select(mount).append('svg').attr('width', W).attr('height', H);
    const g   = svg.append('g').attr('transform', `translate(${{m.left}},${{m.top}})`);

    const useLogX = {str(log_x).lower()};
    const useLogY = {str(log_y).lower()};

    const xVals = data.map(d => +d[XCOL]).filter(v => Number.isFinite(v) && (!useLogX || v > 0));
    const yVals = data.map(d => +d[YCOL]).filter(v => Number.isFinite(v) && (!useLogY || v > 0));
    const x = (useLogX ? d3.scaleLog() : d3.scaleLinear())
      .domain(useLogX ? [Math.max(1e-6, d3.min(xVals)), d3.max(xVals)] : d3.extent(xVals)).nice()
      .range([0, iW]);
    const y = (useLogY ? d3.scaleLog() : d3.scaleLinear())
      .domain(useLogY ? [Math.max(1e-6, d3.min(yVals)), d3.max(yVals)] : d3.extent(yVals)).nice()
      .range([iH, 0]);

    const cats = COLORCOL ? [...new Set(data.map(d => d[COLORCOL]))].filter(d => d!==undefined && d!==null) : null;
    const color = cats ? d3.scaleOrdinal(cats, d3.schemeTableau10) : null;

    const size = SIZECOL
      ? d3.scaleSqrt().domain(d3.extent(data, d => +d[SIZECOL] || 0)).range([3, 12])
      : null;

    // Grilla
    g.append('g')
      .attr('transform', `translate(0,${{iH}})`)
      .call(d3.axisBottom(x).ticks(8, useLogX ? "~g" : undefined).tickSize(-iH).tickFormat(() => ""))
      .selectAll('line').attr('stroke', '#e5e7eb');
    g.append('g')
      .call(d3.axisLeft(y).ticks(8, useLogY ? "~g" : undefined).tickSize(-iW).tickFormat(() => ""))
      .selectAll('line').attr('stroke', '#e5e7eb');

    // Ejes
    g.append('g').attr('transform', `translate(0,${{iH}})`).call(d3.axisBottom(x).ticks(8, useLogX ? "~g" : undefined));
    g.append('g').call(d3.axisLeft(y).ticks(8, useLogY ? "~g" : undefined));

    // Títulos
    g.append('text').attr('x', iW/2).attr('y', iH + 40).attr('text-anchor','middle')
      .style('font','12px sans-serif').text(XCOL);
    g.append('text').attr('transform','rotate(-90)').attr('x', -iH/2).attr('y', -46).attr('text-anchor','middle')
      .style('font','12px sans-serif').text(YCOL);

    // Tooltip
    const tip = document.createElement('div');
    Object.assign(tip.style, {{
      position: 'fixed', zIndex: 9999, pointerEvents: 'none',
      background: 'rgba(17,24,39,.92)', color: '#fff',
      padding: '8px 10px', borderRadius: '8px', font: '12px sans-serif',
      boxShadow: '0 4px 16px rgba(0,0,0,.25)', opacity: 0, transition: 'opacity .12s ease-out'
    }});
    document.body.appendChild(tip);
    const fmt = d3.format(",.0f");

    function showTip(event, d) {{
      const lbl = LABELCOL ? (d[LABELCOL] ?? "") : "";
      const s   = SIZECOL  ? "<div><strong>"+SIZECOL+"</strong>: "+fmt(+d[SIZECOL]||0)+"</div>" : "";
      tip.innerHTML =
        (lbl ? "<div style='font-weight:600;margin-bottom:4px'>"+lbl+"</div>" : "") +
        "<div><strong>"+XCOL+"</strong>: "+fmt(+d[XCOL]||0)+"</div>" +
        "<div><strong>"+YCOL+"</strong>: "+fmt(+d[YCOL]||0)+"</div>" + s;
      tip.style.opacity = 1;
      const x = event.clientX, y = event.clientY;
      tip.style.left = (x + 14) + "px";
      tip.style.top  = (y + 14) + "px";
    }}
    function hideTip() {{ tip.style.opacity = 0; }}

    // Puntos
    g.selectAll('circle')
      .data(data)
      .join('circle')
      .attr('cx', d => x(+d[XCOL]))
      .attr('cy', d => y(+d[YCOL]))
      .attr('r', d => size ? size(+d[SIZECOL]||0) : 4)
      .attr('fill', d => color ? color(d[COLORCOL]) : '#4f46e5')
      .attr('opacity', 0.95)
      .on('mousemove', showTip)
      .on('mouseleave', hideTip)
      .on('mouseover', function() {{ d3.select(this).attr('stroke','#111').attr('stroke-width',1.2); }})
      .on('mouseout',  function() {{ d3.select(this).attr('stroke',null).attr('stroke-width',null); }});

    // Leyenda
    if (cats && cats.length) {{
      const lg = svg.append('g').attr('transform', `translate(${{W - m.right + 16}},${{m.top}})`);
      const row = lg.selectAll('g').data(cats).join('g')
        .attr('transform', (d,i) => `translate(0,${{i*20}})`);
      row.append('rect').attr('width',12).attr('height',12).attr('rx',2).attr('fill', d => color(d));
      row.append('text').attr('x',16).attr('y',6).attr('dy','.35em').style('font','12px sans-serif').text(d => String(d));
    }}

    status.textContent = 'Listo. Pasa el mouse sobre los puntos para ver detalles.';
  }} catch (e) {{
    status.textContent = 'Error: ' + (e && e.stack ? e.stack : e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>Scatter listo (#{uid})</small>")

# ========== 2) Sunburst ==========
def Sunburst(df, path_columns, value_column, width=720, height=720):
    """
    Sunburst jerárquico sumando valores por camino.
    """
    df = df.copy()
    if not pd.api.types.is_numeric_dtype(df[value_column]):
        df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    df = df.dropna(subset=path_columns + [value_column])

    # Construir árbol acumulando sumas
    root = {{ "name": "root", "children": [] }}
    def add_path(node, keys, val):
        if not keys:
            node["value"] = node.get("value", 0) + float(val)
            return
        name = str(keys[0])
        for child in node.get("children", []):
            if child["name"] == name:
                add_path(child, keys[1:], val)
                break
        else:
            new_child = {{ "name": name, "children": [] }}
            node.setdefault("children", []).append(new_child)
            add_path(new_child, keys[1:], val)

    for _, row in df.iterrows():
        keys = [str(row[c]) for c in path_columns]
        add_path(root, keys, row[value_column])

    payload = json.dumps(root, ensure_ascii=False)
    uid = f"sun-{uuid.uuid4().hex[:8]}"

    _display_container(uid, height)

    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    const data = {payload};
    const W={width}, H={height};
    const R = Math.min(W, H)/2 - 4;

    const svg = d3.select(mount).append('svg').attr('width', W).attr('height', H);
    const g   = svg.append('g').attr('transform', `translate(${{W/2}},${{H/2}})`);

    const root = d3.partition()
      .size([2*Math.PI, 1])(
        d3.hierarchy(data).sum(d => d.value || 0).sort((a,b)=>b.value - a.value)
      );

    const arc = d3.arc()
      .startAngle(d=>d.x0).endAngle(d=>d.x1)
      .innerRadius(d=>d.y0 * R).outerRadius(d=>Math.max(d.y0*R, d.y1*R - 2));

    const color = d3.scaleOrdinal(d3.schemeCategory10);

    g.selectAll('path')
      .data(root.descendants().filter(d=>d.depth))
      .join('path')
      .attr('d', arc)
      .attr('fill', d => color(d.ancestors().map(a=>a.data.name).slice(-2,-1)[0]))
      .attr('stroke', '#fff')
      .style('cursor','pointer')
      .style('opacity', .9)
      .on('mouseover', function(event, d){{
        d3.select(this).style('opacity', 1);
        const pct = ((d.value / root.value) * 100).toFixed(1);
        status.textContent = d.ancestors().map(a=>a.data.name).reverse().slice(1).join(' / ') + 
                             `: ${{d.value.toLocaleString()}} ( ${{pct}}% )`;
      }})
      .on('mouseout', function(){{
        d3.select(this).style('opacity', .9);
        status.textContent = 'Hover sobre segmentos para ver detalles';
      }})
      .append('title')
      .text(d => d.ancestors().map(a=>a.data.name).reverse().slice(1).join(' / ') + 
                 `\\n${{d.value?.toLocaleString() ?? ''}}`);

    status.textContent = 'Hover sobre segmentos para ver detalles';
  }} catch (e) {{
    document.getElementById('{uid}-status').textContent = 'Error: ' + (e?.stack || e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>Sunburst listo (#{uid})</small>")

# ========== 3) StreamGraph ==========
def StreamGraph(df, x_column, y_column, category_column, width=900, height=500):
    """
    StreamGraph apilado por categoría sobre eje X.
    """
    df = df.copy()
    if not pd.api.types.is_numeric_dtype(df[y_column]):
        df[y_column] = pd.to_numeric(df[y_column], errors="coerce")
    df = df.dropna(subset=[x_column, y_column, category_column])

    grouped = df.groupby([x_column, category_column], dropna=False)[y_column].sum().reset_index()

    xs = grouped[x_column].unique().tolist()
    try:
        xs_sorted = sorted(xs, key=lambda v: int(str(v)))
    except Exception:
        xs_sorted = sorted(xs, key=lambda v: str(v))

    pivot_df = grouped.pivot(index=x_column, columns=category_column, values=y_column).fillna(0.0)
    pivot_df = pivot_df.reindex(xs_sorted)

    data = []
    for x_val, row in pivot_df.iterrows():
        entry = {{ "x": str(x_val) }}
        for cat in pivot_df.columns:
            entry[str(cat)] = float(row[cat])
        data.append(entry)

    categories = [str(c) for c in pivot_df.columns]
    payload = json.dumps(data, ensure_ascii=False)
    cats_json = json.dumps(categories)
    uid = f"stream-{uuid.uuid4().hex[:8]}"

    _display_container(uid, height)

    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    const data = {payload};
    const categories = {cats_json};
    const W={width}, H={height};
    const m={{top:20,right:120,bottom:48,left:44}};
    const w = W - m.left - m.right, h = H - m.top - m.bottom;

    const svg = d3.select(mount).append('svg').attr('width', W).attr('height', H);
    const g   = svg.append('g').attr('transform', `translate(${{m.left}},${{m.top}})`);

    const stack = d3.stack().keys(categories).offset(d3.stackOffsetWiggle);
    const series = stack(data);

    const x = d3.scalePoint().domain(data.map(d => d.x)).range([0, w]);
    const y = d3.scaleLinear()
      .domain([
        d3.min(series, s => d3.min(s, d => d[0])),
        d3.max(series, s => d3.max(s, d => d[1]))
      ])
      .range([h, 0]);

    const color = d3.scaleOrdinal(categories, d3.schemeCategory10);

    const area = d3.area()
      .x(d => x(d.data.x))
      .y0(d => y(d[0]))
      .y1(d => y(d[1]))
      .curve(d3.curveBasis);

    g.selectAll('path.layer')
      .data(series)
      .join('path')
      .attr('class','layer')
      .attr('d', area)
      .attr('fill', d => color(d.key))
      .attr('opacity', .85)
      .on('mouseover', function(event, d){{
        d3.select(this).attr('opacity', 1).attr('stroke', '#333').attr('stroke-width', 1.5);
        const total = d3.sum(d, p => p.data[d.key] || 0);
        status.textContent = `${{d.key}} — Total: ${{d3.format(",.0f")(total)}}`;
      }})
      .on('mouseout', function(){{
        d3.select(this).attr('opacity', .85).attr('stroke', 'none');
        status.textContent = 'Hover sobre streams para ver totales';
      }});

    g.append('g')
      .attr('transform', `translate(0,${{h}})`)
      .call(d3.axisBottom(x).tickValues(
        data.map(d => d.x).filter((_, i) => i % Math.max(1, Math.ceil(data.length/10)) === 0)
      ))
      .selectAll('text')
      .attr('transform','rotate(-45)')
      .style('text-anchor','end');

    const legend = g.append('g').attr('transform', `translate(${{w+10}},0)`);
    legend.selectAll('g')
      .data(categories)
      .join('g')
      .attr('transform', (d,i)=>`translate(0,${{i*20}})`)
      .call(sel => {{
        sel.append('rect').attr('width', 12).attr('height', 12).attr('fill', d => color(d));
        sel.append('text').attr('x', 16).attr('y', 6).attr('dy','.35em').style('font-size','11px').text(d => d);
      }});

    status.textContent = 'Hover sobre streams para ver totales';
  }} catch (e) {{
    document.getElementById('{uid}-status').textContent = 'Error: ' + (e?.stack || e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>StreamGraph listo (#{uid})</small>")

# ========== 4) Radar ==========
def RadarChart(df, features=None, name_col=None, width=700, height=700):
    """
    Radar/Spider para comparar múltiples variables por fila.
    """
    df = df.copy()
    if features is None:
        features = df.select_dtypes(include=["number"]).columns.tolist()
    df = _to_numeric_cols(df, features)
    df = df.dropna(subset=features)

    data = df.to_dict(orient="records")
    payload = json.dumps(data, ensure_ascii=False)
    feats_json = json.dumps(features)
    name_expr = f"d['{name_col}']" if name_col else "'Serie ' + i"
    uid = f"radar-{uuid.uuid4().hex[:8]}"

    _display_container(uid, height)

    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    const data = {payload};
    const features = {feats_json};
    const W={width}, H={height};
    const m={{top:40,right:100,bottom:40,left:100}};
    const w = W - m.left - m.right, h = H - m.top - m.bottom;
    const R = Math.min(w, h)/2;

    const svg = d3.select(mount).append('svg').attr('width', W).attr('height', H);
    const g   = svg.append('g').attr('transform', `translate(${{W/2}},${{H/2}})`);

    const angle = (i) => (2*Math.PI) * i / features.length - Math.PI/2;

    const maxValue = d3.max(data, d => d3.max(features, f => +d[f] || 0)) || 1;
    const r = d3.scaleLinear().domain([0, maxValue]).range([0, R]);
    const color = d3.scaleOrdinal(d3.schemeCategory10);

    [0.2,0.4,0.6,0.8,1.0].forEach(t => {{
      g.append('polygon')
        .attr('points', features.map((_,i)=>[r(maxValue*t)*Math.cos(angle(i)), r(maxValue*t)*Math.sin(angle(i))].join(',')).join(' '))
        .attr('fill','none').attr('stroke','#e5e7eb');
    }});

    const axis = g.append('g');
    features.forEach((f,i) => {{
      axis.append('line')
        .attr('x1',0).attr('y1',0)
        .attr('x2', r(maxValue*1.05)*Math.cos(angle(i)))
        .attr('y2', r(maxValue*1.05)*Math.sin(angle(i)))
        .attr('stroke','#cbd5e1');
      axis.append('text')
        .attr('x', r(maxValue*1.12)*Math.cos(angle(i)))
        .attr('y', r(maxValue*1.12)*Math.sin(angle(i)))
        .attr('text-anchor','middle').attr('dominant-baseline','middle')
        .style('font-size','11px')
        .text(f);
    }});

    const series = data.map((d,i) => features.map((f,idx) => ({{ k: idx, v: +d[f] || 0, name: {name_expr} }})));
    const line = d3.lineRadial().radius(d => r(d.v)).angle(d => (2*Math.PI)*d.k/features.length).curve(d3.curveLinearClosed);

    g.selectAll('path.area')
      .data(series)
      .join('path')
      .attr('class','area')
      .attr('d', d => line(d))
      .attr('fill', (_,i) => color(i))
      .attr('fill-opacity', .22)
      .attr('stroke', (_,i) => color(i))
      .attr('stroke-width', 2)
      .on('mouseover', function(){{ d3.select(this).attr('fill-opacity', .45); }})
      .on('mouseout',  function(){{ d3.select(this).attr('fill-opacity', .22); }});

    series.forEach((arr, i) => {{
      g.selectAll(`.pt-${{i}}`)
        .data(arr)
        .join('circle')
        .attr('class', `pt-${{i}}`)
        .attr('r', 3)
        .attr('cx', d => r(d.v)*Math.cos(angle(d.k)))
        .attr('cy', d => r(d.v)*Math.sin(angle(d.k)))
        .attr('fill', color(i));
    }});

    const legend = svg.append('g').attr('transform', `translate(${{W - m.right + 6}},${{m.top}})`);
    legend.selectAll('g')
      .data(data)
      .join('g')
      .attr('transform', (d,i)=>`translate(0,${{i*18}})`)
      .call(sel => {{
        sel.append('rect').attr('width', 12).attr('height', 12).attr('fill', (_,i)=>color(i));
        sel.append('text').attr('x', 16).attr('y', 6).attr('dy','.35em').style('font-size','11px')
          .text((d,i) => {name_expr});
      }});

    status.textContent = 'Radar renderizado correctamente.';
  }} catch (e) {{
    document.getElementById('{uid}-status').textContent = 'Error: ' + (e?.stack || e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>RadarChart listo (#{uid})</small>")

# ========== 5) BubblePack (nuevo) ==========
def BubblePack(df, label, size, group=None, width=800, height=600):
    """
    Bubble Pack (circle packing). Si 'group' se provee, crea un pack jerárquico:
      root -> group -> items(label, value).
    Si no hay 'group', hace un pack plano (root -> items).
    - df: DataFrame
    - label: columna texto para la etiqueta del círculo
    - size: columna numérica para el tamaño (radio ~ sqrt(size))
    - group: columna categórica (opcional)
    """
    df = df.copy()
    if not pd.api.types.is_numeric_dtype(df[size]):
        df[size] = pd.to_numeric(df[size], errors="coerce")
    df = df.dropna(subset=[label, size] + ([group] if group else []))

    if group:
        root = {{ "name": "root", "children": [] }}
        for g, gdf in df.groupby(group):
            node = {{ "name": str(g), "children": [] }}
            for _, r in gdf.iterrows():
                node["children"].append({{ "name": str(r[label]), "value": float(r[size]) }})
            root["children"].append(node)
    else:
        root = {{ "name": "root", "children": [
            {{ "name": str(r[label]), "value": float(r[size]) }} for _, r in df.iterrows()
        ] }}

    payload = json.dumps(root, ensure_ascii=False)
    group_name = json.dumps(group or "")
    uid = f"bubble-{uuid.uuid4().hex[:8]}"

    _display_container(uid, height)

    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    const data = {payload};
    const groupCol = {group_name};
    const W={width}, H={height};
    const svg = d3.select(mount).append('svg').attr('width', W).attr('height', H);

    const root = d3.hierarchy(data).sum(d => d.value || 0).sort((a,b)=>b.value - a.value);
    d3.pack().size([W, H]).padding(4)(root);

    const groups = groupCol
      ? root.children?.map(c => c.data.name) ?? []
      : ["All"];

    const color = d3.scaleOrdinal(groups, d3.schemeCategory10);

    const node = svg.selectAll('g.node')
      .data(root.leaves())
      .join('g')
      .attr('class','node')
      .attr('transform', d => `translate(${{d.x}},${{d.y}})`);

    node.append('circle')
      .attr('r', d => d.r)
      .attr('fill', d => {{
        const grp = d.parent?.data?.name ?? "All";
        return color(grp);
      }})
      .attr('opacity', .9)
      .attr('stroke', '#fff');

    node.append('title')
      .text(d => `${{d.data.name}}\\n${{d3.format(",.2f")(d.data.value)}}`);

    node.append('text')
      .attr('text-anchor','middle')
      .attr('dominant-baseline','middle')
      .style('font-size','11px')
      .style('pointer-events','none')
      .text(d => {{
        const n = d.data.name;
        return n.length > 12 ? n.slice(0,10) + '…' : n;
      }});

    // Leyenda (si hay grupos)
    if (groups.length > 1) {{
      const legend = svg.append('g').attr('transform', `translate(${{W-120}}, 12)`);
      legend.selectAll('g')
        .data(groups)
        .join('g')
        .attr('transform', (d,i)=>`translate(0,${{i*18}})`)
        .call(sel => {{
          sel.append('rect').attr('width', 12).attr('height', 12).attr('fill', d => color(d));
          sel.append('text').attr('x', 16).attr('y', 6).attr('dy','.35em').style('font-size','11px').text(d => d);
        }});
    }}

    status.textContent = 'BubblePack renderizado.';
  }} catch (e) {{
    document.getElementById('{uid}-status').textContent = 'Error: ' + (e?.stack || e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>BubblePack listo (#{uid})</small>")
