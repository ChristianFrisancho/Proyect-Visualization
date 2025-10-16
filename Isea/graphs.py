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


