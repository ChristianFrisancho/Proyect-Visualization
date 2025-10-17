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

def Sunburst(df, path_columns, value_column, width=800, height=800, color_scheme='schemeCategory10'):
    """
    Diagrama Sunburst para visualizar datos jerárquicos en formato circular.
    
    Args:
        df: DataFrame con los datos
        path_columns: Lista de columnas que definen la jerarquía (de más general a más específico)
        value_column: Columna numérica que determina el tamaño de cada segmento
        width: Ancho del gráfico
        height: Alto del gráfico
        color_scheme: Esquema de colores D3
    """
    df = df.copy()
    
    # Convertir value_column a numérico
    if not pd.api.types.is_numeric_dtype(df[value_column]):
        df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    
    df = df.dropna(subset=[value_column])
    
    # Construir jerarquía
    hierarchy = {"name": "root", "children": []}
    
    for _, row in df.iterrows():
        current_level = hierarchy
        for col in path_columns:
            value = str(row[col])
            # Buscar si ya existe este nodo
            found = False
            for child in current_level.get("children", []):
                if child["name"] == value:
                    current_level = child
                    found = True
                    break
            
            if not found:
                new_node = {"name": value, "children": []}
                if "children" not in current_level:
                    current_level["children"] = []
                current_level["children"].append(new_node)
                current_level = new_node
        
        # Agregar el valor en el nodo hoja
        current_level["value"] = row[value_column]
    
    payload = json.dumps(hierarchy, ensure_ascii=False)
    uid = f"sunburst-{uuid.uuid4().hex[:8]}"
    
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Cargando Sunburst…</div>
<style>
  .vis {{ width: 100%; min-height: {height}px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
</style>
"""))
    
    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3 = mod.default ?? mod;
    
    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';
    
    const data = {payload};
    const W = {width}, H = {height};
    const radius = Math.min(W, H) / 2;
    
    const svg = d3.select(mount)
      .append('svg')
      .attr('width', W)
      .attr('height', H)
      .append('g')
      .attr('transform', `translate(${{W/2}}, ${{H/2}})`);
    
    const color = d3.scaleOrdinal(d3.{color_scheme} || d3.schemeCategory10);
    
    const root = d3.hierarchy(data)
      .sum(d => d.value || 0)
      .sort((a, b) => b.value - a.value);
    
    const partition = d3.partition()
      .size([2 * Math.PI, radius]);
    
    partition(root);
    
    const arc = d3.arc()
      .startAngle(d => d.x0)
      .endAngle(d => d.x1)
      .innerRadius(d => d.y0)
      .outerRadius(d => d.y1);
    
    const segments = svg.selectAll('path')
      .data(root.descendants().filter(d => d.depth > 0))
      .enter()
      .append('path')
      .attr('d', arc)
      .style('fill', d => color(d.data.name))
      .style('stroke', '#fff')
      .style('stroke-width', '2px')
      .style('opacity', 0.8)
      .on('mouseover', function(event, d) {{
        d3.select(this)
          .style('opacity', 1)
          .style('stroke-width', '3px');
        
        const percent = ((d.value / root.value) * 100).toFixed(1);
        status.textContent = `${{d.data.name}}: ${{d.value.toFixed(2)}} (${{percent}}%)`;
      }})
      .on('mouseout', function() {{
        d3.select(this)
          .style('opacity', 0.8)
          .style('stroke-width', '2px');
        status.textContent = 'Hover sobre segmentos para ver detalles';
      }});
    
    svg.selectAll('text')
      .data(root.descendants().filter(d => d.depth > 0 && (d.x1 - d.x0) > 0.1))
      .enter()
      .append('text')
      .attr('transform', d => {{
        const angle = (d.x0 + d.x1) / 2;
        const radius = (d.y0 + d.y1) / 2;
        const x = Math.cos(angle - Math.PI / 2) * radius;
        const y = Math.sin(angle - Math.PI / 2) * radius;
        return `translate(${{x}},${{y}})`;
      }})
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .style('font-size', '10px')
      .style('fill', '#fff')
      .style('font-weight', 'bold')
      .style('pointer-events', 'none')
      .text(d => d.data.name.length > 15 ? d.data.name.substring(0, 12) + '...' : d.data.name);
    
    status.textContent = 'Hover sobre segmentos para ver detalles';
  }} catch (e) {{
    const msg = (e && e.stack) ? e.stack : (''+e);
    document.getElementById('{uid}-status').textContent = 'Error: ' + msg;
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>Sunburst listo (#{uid})</small>")


def StreamGraph(df, x_column, y_column, category_column, width=900, height=500, color_scheme='schemeCategory10'):
    """
    Stream Graph (gráfico de flujo) para visualizar datos temporales apilados.
    """
    df = df.copy()
    
    if not pd.api.types.is_numeric_dtype(df[y_column]):
        df[y_column] = pd.to_numeric(df[y_column], errors="coerce")
    
    df = df.dropna(subset=[x_column, y_column, category_column])
    
    grouped = df.groupby([x_column, category_column])[y_column].sum().reset_index()
    pivot_df = grouped.pivot(index=x_column, columns=category_column, values=y_column).fillna(0)
    
    data = []
    for x_val in pivot_df.index:
        row_data = {"x": str(x_val)}
        for cat in pivot_df.columns:
            row_data[str(cat)] = float(pivot_df.loc[x_val, cat])
        data.append(row_data)
    
    categories = [str(c) for c in pivot_df.columns]
    
    payload = json.dumps(data, ensure_ascii=False)
    categories_json = json.dumps(categories)
    uid = f"stream-{uuid.uuid4().hex[:8]}"
    
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Cargando Stream Graph…</div>
<style>
  .vis {{ width: 100%; min-height: {height}px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
</style>
"""))
    
    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3 = mod.default ?? mod;
    
    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';
    
    const data = {payload};
    const categories = {categories_json};
    const W = {width}, H = {height};
    const margin = {{ top: 20, right: 120, bottom: 40, left: 40 }};
    const w = W - margin.left - margin.right;
    const h = H - margin.top - margin.bottom;
    
    const svg = d3.select(mount)
      .append('svg')
      .attr('width', W)
      .attr('height', H)
      .append('g')
      .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
    
    const stack = d3.stack()
      .keys(categories)
      .offset(d3.stackOffsetWiggle)
      .order(d3.stackOrderInsideOut);
    
    const series = stack(data);
    
    const x = d3.scalePoint()
      .domain(data.map(d => d.x))
      .range([0, w]);
    
    const y = d3.scaleLinear()
      .domain([
        d3.min(series, s => d3.min(s, d => d[0])),
        d3.max(series, s => d3.max(s, d => d[1]))
      ])
      .range([h, 0]);
    
    const color = d3.scaleOrdinal(d3.{color_scheme} || d3.schemeCategory10);
    
    const area = d3.area()
      .x(d => x(d.data.x))
      .y0(d => y(d[0]))
      .y1(d => y(d[1]))
      .curve(d3.curveBasis);
    
    svg.selectAll('.stream')
      .data(series)
      .enter()
      .append('path')
      .attr('class', 'stream')
      .attr('d', area)
      .style('fill', d => color(d.key))
      .style('opacity', 0.7)
      .on('mouseover', function(event, d) {{
        d3.select(this)
          .style('opacity', 1)
          .style('stroke', '#333')
          .style('stroke-width', '2px');
        
        const total = d3.sum(d, p => p.data[d.key]);
        status.textContent = `${{d.key}}: Total = ${{total.toFixed(2)}}`;
      }})
      .on('mouseout', function() {{
        d3.select(this)
          .style('opacity', 0.7)
          .style('stroke', 'none');
        status.textContent = 'Hover sobre streams para ver detalles';
      }});
    
    svg.append('g')
      .attr('transform', `translate(0,${{h}})`)
      .call(d3.axisBottom(x).tickValues(
        data.map(d => d.x).filter((d, i) => i % Math.ceil(data.length / 10) === 0)
      ))
      .selectAll('text')
      .attr('transform', 'rotate(-45)')
      .style('text-anchor', 'end');
    
    const legend = svg.selectAll('.legend')
      .data(categories)
      .enter()
      .append('g')
      .attr('class', 'legend')
      .attr('transform', (d, i) => `translate(${{w + 10}}, ${{i * 20}})`);
    
    legend.append('rect')
      .attr('width', 15)
      .attr('height', 15)
      .style('fill', d => color(d));
    
    legend.append('text')
      .attr('x', 20)
      .attr('y', 7.5)
      .attr('dy', '.35em')
      .style('font-size', '11px')
      .text(d => d.length > 12 ? d.substring(0, 10) + '...' : d);
    
    status.textContent = 'Hover sobre streams para ver detalles';
  }} catch (e) {{
    const msg = (e && e.stack) ? e.stack : (''+e);
    document.getElementById('{uid}-status').textContent = 'Error: ' + msg;
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>StreamGraph listo (#{uid})</small>")


def RadarChart(df, features=None, name_col='name', width=700, height=700, color_scheme='schemeCategory10'):
    """
    Gráfico de Radar/Spider para comparar múltiples variables.
    
    Args:
        df: DataFrame con los datos
        features: Lista de columnas numéricas para usar como ejes (si es None, usa todas las numéricas)
        name_col: Nombre de la columna que identifica cada serie
        width: Ancho del gráfico
        height: Alto del gráfico
        color_scheme: Esquema de colores D3 (ej: 'schemeCategory10', 'schemeSet3')
    """
    df = df.copy()
    
    # Si no se especifican features, usar todas las columnas numéricas
    if features is None:
        features = df.select_dtypes(include=['number']).columns.tolist()
    
    # Asegurar que name_col no esté en features
    if name_col in features:
        features.remove(name_col)
    
    # Convertir a numérico
    for col in features:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Preparar datos
    data = df.to_dict(orient="records")
    payload = json.dumps(data, ensure_ascii=False)
    features_json = json.dumps(features)
    uid = f"radar-{uuid.uuid4().hex[:8]}"
    
    # HTML container
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Cargando Radar Chart…</div>
<style>
  .vis {{ width: 100%; min-height: {height}px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
</style>
"""))
    
    # JavaScript con D3
    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3 = mod.default ?? mod;
    
    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';
    
    const data = {payload};
    const features = {features_json};
    const W = {width}, H = {height};
    const margin = {{ top: 50, right: 100, bottom: 50, left: 100 }};
    const w = W - margin.left - margin.right;
    const h = H - margin.top - margin.bottom;
    const radius = Math.min(w, h) / 2;
    
    const svg = d3.select(mount)
      .append('svg')
      .attr('width', W)
      .attr('height', H)
      .append('g')
      .attr('transform', `translate(${{W/2}}, ${{H/2}})`);
    
    const angleSlice = (Math.PI * 2) / features.length;
    
    // Escala radial
    const maxValue = d3.max(data, d => d3.max(features, f => +d[f]));
    const rScale = d3.scaleLinear()
      .domain([0, maxValue])
      .range([0, radius]);
    
    const colorScale = d3.scaleOrdinal(d3.{color_scheme} || d3.schemeCategory10);
    
    // Dibujar círculos de niveles
    const levels = 5;
    for (let i = 1; i <= levels; i++) {{
      const levelRadius = (radius / levels) * i;
      
      svg.append('circle')
        .attr('r', levelRadius)
        .style('fill', 'none')
        .style('stroke', '#CDCDCD')
        .style('stroke-dasharray', '3,3');
      
      svg.append('text')
        .attr('x', 5)
        .attr('y', -levelRadius)
        .attr('dy', '0.4em')
        .style('font-size', '10px')
        .style('fill', '#737373')
        .text(Math.round((maxValue / levels) * i));
    }}
    
    // Dibujar ejes radiales
    const axis = svg.selectAll('.axis')
      .data(features)
      .enter()
      .append('g')
      .attr('class', 'axis');
    
    axis.append('line')
      .attr('x1', 0)
      .attr('y1', 0)
      .attr('x2', (d, i) => rScale(maxValue * 1.1) * Math.cos(angleSlice * i - Math.PI/2))
      .attr('y2', (d, i) => rScale(maxValue * 1.1) * Math.sin(angleSlice * i - Math.PI/2))
      .style('stroke', '#999')
      .style('stroke-width', '1px');
    
    // Etiquetas de características
    axis.append('text')
      .attr('x', (d, i) => (rScale(maxValue * 1.25)) * Math.cos(angleSlice * i - Math.PI/2))
      .attr('y', (d, i) => (rScale(maxValue * 1.25)) * Math.sin(angleSlice * i - Math.PI/2))
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .style('font-size', '12px')
      .style('font-weight', 'bold')
      .text(d => d);
    
    // Generador de líneas para el radar
    const radarLine = d3.lineRadial()
      .radius(d => rScale(d.value))
      .angle((d, i) => i * angleSlice)
      .curve(d3.curveLinearClosed);
    
    // Preparar datos del radar
    const radarData = data.map(item => 
      features.map(f => ({{ axis: f, value: +item[f] }}))
    );
    
    // Dibujar áreas del radar
    svg.selectAll('.radar-area')
      .data(radarData)
      .enter()
      .append('path')
      .attr('class', 'radar-area')
      .attr('d', radarLine)
      .style('fill', (d, i) => colorScale(i))
      .style('fill-opacity', 0.2)
      .style('stroke', (d, i) => colorScale(i))
      .style('stroke-width', '2px')
      .on('mouseover', function() {{
        d3.select(this).style('fill-opacity', 0.5);
      }})
      .on('mouseout', function() {{
        d3.select(this).style('fill-opacity', 0.2);
      }});
    
    // Puntos en los vértices
    radarData.forEach((item, idx) => {{
      svg.selectAll(`.radar-circle-${{idx}}`)
        .data(item)
        .enter()
        .append('circle')
        .attr('class', `radar-circle-${{idx}}`)
        .attr('r', 4)
        .attr('cx', (d, i) => rScale(d.value) * Math.cos(angleSlice * i - Math.PI/2))
        .attr('cy', (d, i) => rScale(d.value) * Math.sin(angleSlice * i - Math.PI/2))
        .style('fill', colorScale(idx))
        .style('fill-opacity', 0.8);
    }});
    
    // Leyenda
    const legend = svg.selectAll('.legend')
      .data(data)
      .enter()
      .append('g')
      .attr('class', 'legend')
      .attr('transform', (d, i) => `translate(${{radius + 30}}, ${{-radius + i * 25}})`);
    
    legend.append('rect')
      .attr('width', 18)
      .attr('height', 18)
      .style('fill', (d, i) => colorScale(i));
    
    legend.append('text')
      .attr('x', 24)
      .attr('y', 9)
      .attr('dy', '.35em')
      .style('font-size', '12px')
      .text(d => d['{name_col}'] || 'Sin nombre');
    
    status.textContent = 'Radar Chart renderizado correctamente.';
  }} catch (e) {{
    const msg = (e && e.stack) ? e.stack : (''+e);
    document.getElementById('{uid}-status').textContent = 'Error: ' + msg;
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>RadarChart listo (#{uid})</small>")


def RadialStackedBar(
    df,
    group_col,
    category_col,
    value_col,
    *,
    agg='sum',
    width=928,
    height=928,
    inner_radius=180,
    pad_angle=0.015,
    color_scheme='schemeSpectral',
    sort_on_click=True,
    title=None
):
    df = df.copy()

    if not pd.api.types.is_numeric_dtype(df[value_col]):
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    
    df = df.dropna(subset=[group_col, category_col, value_col])

    if agg not in ('sum', 'mean'):
        agg = 'sum'
    
    grouped = df.groupby([group_col, category_col])[value_col].agg(agg).reset_index()
    pivot_df = grouped.pivot(index=group_col, columns=category_col, values=value_col).fillna(0)
    pivot_df = pivot_df.sort_index()

    categories = [str(c) for c in pivot_df.columns]
    data = []
    for g in pivot_df.index:
        obj = {"group": str(g)}
        for c in pivot_df.columns:
            obj[str(c)] = float(pivot_df.loc[g, c])
        data.append(obj)

    payload = json.dumps(data, ensure_ascii=False)
    categories_json = json.dumps(categories)
    title_json = json.dumps(title if title else value_col)
    uid = f"radialstack-{uuid.uuid4().hex[:8]}"

    display(HTML(f"""
<div id="{uid}-container" style="display: flex; justify-content: center; align-items: center; margin-top: 20px;">
  <div id="{uid}" style="position: relative;"></div>
</div>
<div id="{uid}-status" style="text-align: center; font-size: 12px; color: #666; margin: 12px 0;">
  Cargando visualización...
</div>
"""))

    js = f"""
(async () => {{
  const status = document.getElementById('{uid}-status');
  try {{
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3 = mod.default ?? mod;

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    let data = {payload};
    const keys = {categories_json};
    const title = {title_json};
    
    const W = {width};
    const H = {height};
    const innerRadius = {inner_radius};
    const outerRadius = Math.min(W, H) / 2 - 60;
    const padAngle = {pad_angle};

    let sorted = false;

    const svg = d3.select(mount)
      .append('svg')
      .attr('width', W)
      .attr('height', H)
      .attr('viewBox', [-W / 2, -H / 2, W, H])
      .style('width', '100%')
      .style('height', 'auto')
      .style('font', '10px sans-serif');

    const x = d3.scaleBand()
      .domain(data.map(d => d.group))
      .range([0, 2 * Math.PI])
      .align(0);

    const yMax = d3.max(data, d => d3.sum(keys, k => +d[k]));
    const y = d3.scaleRadial()
      .domain([0, yMax])
      .range([innerRadius, outerRadius]);

    let colorRange;
    const numColors = keys.length;
    
    if ('{color_scheme}' === 'schemeSpectral') {{
      colorRange = numColors <= 3 ? d3.schemeSpectral[3] : 
                   numColors <= 11 ? d3.schemeSpectral[numColors] : 
                   d3.schemeSpectral[11];
    }} else if ('{color_scheme}'.startsWith('scheme')) {{
      try {{
        colorRange = d3['{color_scheme}'][Math.max(Math.min(numColors, 12), 3)] || d3.schemeCategory10;
      }} catch (e) {{
        colorRange = d3.schemeCategory10;
      }}
    }} else {{
      colorRange = d3.schemeCategory10;
    }}

    const color = d3.scaleOrdinal()
      .domain(keys)
      .range(colorRange);

    const formatValue = d3.format(",.1f");

    const arc = d3.arc()
      .innerRadius(d => y(d[0]))
      .outerRadius(d => y(d[1]))
      .startAngle(d => x(d.data.group))
      .endAngle(d => x(d.data.group) + x.bandwidth())
      .padAngle(padAngle)
      .padRadius(innerRadius);

    const g = svg.append('g');

    function render(animate = false) {{
      const series = d3.stack().keys(keys)(data);
      
      x.domain(data.map(d => d.group));

      const barGroups = g.selectAll('.series-group')
        .data(series, d => d.key);
      
      barGroups.exit().remove();
      
      const barGroupsEnter = barGroups.enter()
        .append('g')
        .attr('class', 'series-group')
        .attr('fill', d => color(d.key));
      
      const allBarGroups = barGroupsEnter.merge(barGroups);
      
      allBarGroups.each(function(seriesData) {{
        const paths = d3.select(this).selectAll('path')
          .data(seriesData.map(d => ({{...d, key: seriesData.key}})));
        
        paths.exit().remove();
        
        paths.transition()
          .duration(animate ? 750 : 0)
          .attr('d', arc);
        
        paths.enter()
          .append('path')
          .attr('d', animate ? d => {{
            const arcStart = d3.arc()
              .innerRadius(innerRadius)
              .outerRadius(innerRadius)
              .startAngle(d => x(d.data.group))
              .endAngle(d => x(d.data.group) + x.bandwidth())
              .padAngle(padAngle)
              .padRadius(innerRadius);
            return arcStart(d);
          }} : arc)
          .attr('stroke', '#fff')
          .attr('stroke-width', 1)
          .style('opacity', 0.85)
          .transition()
          .duration(animate ? 750 : 0)
          .attr('d', arc)
          .on('end', function() {{
            d3.select(this)
              .on('mouseover', function(event, d) {{
                d3.select(this)
                  .style('opacity', 1)
                  .style('stroke', '#333')
                  .style('stroke-width', 2);
                
                const total = d3.sum(keys, k => d.data[k]);
                const value = d.data[d.key];
                const percentage = (value / total * 100).toFixed(1);
                
                status.textContent = `${{d.data.group}} – ${{d.key}}: ${{formatValue(value)}} (${{percentage}}%)`;
              }})
              .on('mouseout', function() {{
                d3.select(this)
                  .style('opacity', 0.85)
                  .style('stroke', '#fff')
                  .style('stroke-width', 1);
                
                status.textContent = sorted ? 
                  'Visualización ordenada por tamaño. Clic para restaurar orden original.' : 
                  'Clic en el gráfico para ordenar por tamaño total.';
              }})
              .append('title')
              .text(d => `${{d.data.group}} - ${{d.key}}: ${{formatValue(d.data[d.key])}}`);
          }});
      }});
    }}

    const yTicks = y.ticks(5).slice(1);
    
    g.append('g')
      .selectAll('circle')
      .data(yTicks)
      .join('circle')
      .attr('r', y)
      .style('fill', 'none')
      .style('stroke', '#ddd')
      .style('stroke-dasharray', '2,4')
      .style('stroke-width', 0.5);

    g.append('g')
      .attr('text-anchor', 'middle')
      .selectAll('text')
      .data(yTicks)
      .join('text')
      .attr('y', d => -y(d))
      .attr('dy', '-0.35em')
      .attr('fill', '#666')
      .attr('stroke', '#fff')
      .attr('stroke-width', 3)
      .attr('stroke-linejoin', 'round')
      .attr('paint-order', 'stroke')
      .style('font-size', '9px')
      .text(d => d3.format('~s')(d))
      .clone(true)
      .attr('stroke', 'none')
      .attr('fill', '#666');

    const labels = g.append('g')
      .selectAll('g')
      .data(data)
      .join('g')
      .attr('text-anchor', 'middle')
      .attr('transform', d => {{
        const angle = ((x(d.group) + x.bandwidth() / 2) * 180 / Math.PI) - 90;
        return `rotate(${{angle}})translate(${{outerRadius + 10}},0)`;
      }});
    
    labels.append('line')
      .attr('x1', 0)
      .attr('x2', 0)
      .attr('y1', 0)
      .attr('y2', 7)
      .attr('stroke', '#999')
      .attr('stroke-width', 1);
    
    labels.append('text')
      .attr('transform', d => {{
        const angle = (x(d.group) + x.bandwidth() / 2);
        return ((angle + Math.PI / 2) % (2 * Math.PI) < Math.PI) ? 
          'rotate(90)translate(10,-2)' : 
          'rotate(-90)translate(-10,-2)';
      }})
      .style('font-size', '9px')
      .style('font-weight', data.length > 30 ? 'normal' : 'bold')
      .style('fill', '#333')
      .text(d => d.group);

    const legendG = svg.append('g')
      .attr('class', 'legend')
      .attr('text-anchor', 'start');
    
    if (keys.length > 1) {{
      legendG.append('rect')
        .attr('x', -innerRadius * 0.9)
        .attr('y', -innerRadius * 0.7)
        .attr('width', innerRadius * 1.8)
        .attr('height', Math.min(keys.length * 22 + 40, innerRadius * 1.4))
        .attr('rx', 10)
        .attr('ry', 10)
        .attr('fill', '#fff')
        .attr('opacity', 0.7);
    }}
    
    legendG.append('text')
      .attr('x', 0)
      .attr('y', -innerRadius * 0.5)
      .attr('text-anchor', 'middle')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text(title);

    const legendItems = legendG.selectAll('.legend-item')
      .data(keys)
      .join('g')
      .attr('class', 'legend-item')
      .attr('transform', (d, i) => {{
        const itemsPerColumn = Math.min(Math.ceil(keys.length / 2), 6);
        const column = Math.floor(i / itemsPerColumn);
        const row = i % itemsPerColumn;
        const x = (column === 0 ? -innerRadius * 0.6 : 20);
        const y = -innerRadius * 0.3 + row * 22 + (column === 1 ? 0 : 0);
        return `translate(${{x}},${{y}})`;
      }});

    legendItems.append('rect')
      .attr('width', 16)
      .attr('height', 16)
      .attr('fill', d => color(d))
      .attr('stroke', '#999')
      .attr('stroke-width', 0.5)
      .attr('rx', 2);

    legendItems.append('text')
      .attr('x', 22)
      .attr('y', 9)
      .attr('dy', '0.32em')
      .attr('font-size', '11px')
      .style('font-family', 'sans-serif')
      .text(d => d);

    render(true);

    if ({sort_on_click}) {{
      svg.style('cursor', 'pointer')
        .on('click', () => {{
          sorted = !sorted;
          
          if (sorted) {{
            data.sort((a, b) => d3.descending(
              d3.sum(keys, k => +a[k]),
              d3.sum(keys, k => +b[k])
            ));
            status.textContent = 'Visualización ordenada por tamaño. Clic para restaurar orden original.';
          }} else {{
            data = {payload};
            status.textContent = 'Clic en el gráfico para ordenar por tamaño total.';
          }}
          
          render(true);
        }});
    }}

    status.textContent = 'Clic en el gráfico para ordenar por tamaño total.';

  }} catch (e) {{
    console.error(e);
    status.textContent = 'Error: ' + (e.message || e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>Radial Stacked Bar Chart listo (#{uid})</small>")