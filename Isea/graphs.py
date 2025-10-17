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
    color=None,          # col categórica -> colores + leyenda
    size=None,           # col numérica -> tamaño burbuja (opcional)
    label=None,          # col texto -> nombre en tooltip (opcional)
    width=900,
    height=560,
    zero_filter=True,    # quita (0,0) para que no se amontonen
    log_x=False,
    log_y=False,
):
    import json, uuid
    import pandas as pd
    from IPython.display import HTML, Javascript, display

    # --- Validación y limpieza mínima ---
    need = [x, y] + ([color] if color else []) + ([size] if size else []) + ([label] if label else [])
    miss = [c for c in need if c and c not in df.columns]
    if miss:
        raise KeyError(f"Faltan columnas {miss}. Disponibles: {list(df.columns)}")

    df = df.copy()
    for c in [x, y, size]:
        if c and not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=[x, y])
    if zero_filter:
        df = df.loc[~((df[x] == 0) & (df[y] == 0))]
    if log_x:
        df = df.loc[df[x] > 0]
    if log_y:
        df = df.loc[df[y] > 0]
    if df.empty:
        return display(HTML("<em>No hay datos para graficar.</em>"))

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
    const useLogX  = {str(log_x).lower()};
    const useLogY  = {str(log_y).lower()};

    const W = {width}, H = {height};
    const hasLegend = !!COLORCOL;
    const m = hasLegend ? {{top: 28, right: 160, bottom: 56, left: 70}} : {{top: 28, right: 24, bottom: 56, left: 70}};
    const iW = W - m.left - m.right, iH = H - m.top - m.bottom;

    const svg = d3.select(mount).append('svg').attr('width', W).attr('height', H);
    const g   = svg.append('g').attr('transform', `translate(${{m.left}},${{m.top}})`);

    // --- Escalas ---
    const xVals = data.map(d => +d[XCOL]).filter(v => Number.isFinite(v) && (!useLogX || v > 0));
    const yVals = data.map(d => +d[YCOL]).filter(v => Number.isFinite(v) && (!useLogY || v > 0));
    const x = (useLogX ? d3.scaleLog() : d3.scaleLinear())
      .domain(useLogX ? [Math.max(1e-6, d3.min(xVals)), d3.max(xVals)] : d3.extent(xVals)).nice()
      .range([0, iW]);
    const y = (useLogY ? d3.scaleLog() : d3.scaleLinear())
      .domain(useLogY ? [Math.max(1e-6, d3.min(yVals)), d3.max(yVals)] : d3.extent(yVals)).nice()
      .range([iH, 0]);

    const cats = COLORCOL ? [...new Set(data.map(d => d[COLORCOL]))].filter(v => v!==undefined && v!==null) : null;
    const color = cats ? d3.scaleOrdinal(cats, d3.schemeTableau10) : null;

    const size = SIZECOL
      ? d3.scaleSqrt().domain(d3.extent(data, d => +d[SIZECOL] || 0)).range([3, 16])
      : null;

    // --- Grilla ---
    g.append('g')
      .attr('transform', `translate(0,${{iH}})`)
      .call(d3.axisBottom(x).ticks(8, useLogX ? "~g" : undefined).tickSize(-iH).tickFormat(() => ""))
      .selectAll('line').attr('stroke', '#e5e7eb');
    g.append('g')
      .call(d3.axisLeft(y).ticks(8, useLogY ? "~g" : undefined).tickSize(-iW).tickFormat(() => ""))
      .selectAll('line').attr('stroke', '#e5e7eb');

    // --- Ejes + títulos ---
    g.append('g').attr('transform', `translate(0,${{iH}})`).call(d3.axisBottom(x).ticks(8, useLogX ? "~g" : undefined));
    g.append('g').call(d3.axisLeft(y).ticks(8, useLogY ? "~g" : undefined));
    g.append('text').attr('x', iW/2).attr('y', iH + 40).attr('text-anchor','middle').style('font','12px sans-serif').text(XCOL);
    g.append('text').attr('transform','rotate(-90)').attr('x', -iH/2).attr('y', -54).attr('text-anchor','middle').style('font','12px sans-serif').text(YCOL);

    // --- Tooltip (incluye todas las tecnologías si existen) ---
    const tip = document.createElement('div');
    Object.assign(tip.style, {{
      position:'fixed', zIndex:9999, pointerEvents:'none',
      background:'rgba(17,24,39,.92)', color:'#fff', padding:'8px 10px',
      borderRadius:'8px', font:'12px sans-serif', boxShadow:'0 4px 16px rgba(0,0,0,.25)', opacity:0, transition:'opacity .12s'
    }});
    document.body.appendChild(tip);
    const fmt = d3.format(",.0f");
    const techKeys = ["Solar","Wind","Hydro","Bio","Fossil"];
    function tipHTML(d){{
      const lbl = LABELCOL ? (d[LABELCOL] ?? "") : "";
      let lines = "";
      techKeys.forEach(k => {{ if (k in d) lines += `<div>${{k}}: <strong>${{fmt(+d[k]||0)}}</strong></div>`; }});
      const sz = SIZECOL ? `<div>Total: <strong>${{fmt(+d[SIZECOL]||0)}}</strong></div>` : "";
      return (lbl ? `<div style="font-weight:600;margin-bottom:4px">${{lbl}}</div>` : "")
           + `<div>${{XCOL}}: <strong>${{fmt(+d[XCOL]||0)}}</strong></div>`
           + `<div>${{YCOL}}: <strong>${{fmt(+d[YCOL]||0)}}</strong></div>`
           + (lines ? `<hr style="border:none;border-top:1px solid #374151;margin:6px 0"/>`+lines : "")
           + sz;
    }}
    function showTip(event,d){{ tip.innerHTML = tipHTML(d); tip.style.opacity = 1; tip.style.left=(event.clientX+14)+'px'; tip.style.top=(event.clientY+14)+'px'; }}
    function hideTip(){{ tip.style.opacity = 0; }}

    // --- Puntos ---
    const dots = g.selectAll('circle').data(data).join('circle')
      .attr('cx', d => x(+d[XCOL]))
      .attr('cy', d => y(+d[YCOL]))
      .attr('r', d => size ? size(+d[SIZECOL]||0) : 5)
      .attr('fill', d => color ? color(d[COLORCOL]) : '#4f46e5')
      .attr('opacity', 0.92)
      .on('mousemove', showTip)
      .on('mouseleave', hideTip)
      .on('mouseover', function(){{ d3.select(this).attr('stroke','#111').attr('stroke-width',1.2); }})
      .on('mouseout',  function(){{ d3.select(this).attr('stroke',null).attr('stroke-width',null); }});

    // --- Leyenda con toggle ---
    if (cats && cats.length) {{
      let active = new Set(cats);
      const lg = svg.append('g').attr('transform', `translate(${{W - m.right + 24}},${{m.top}})`);
      const row = lg.selectAll('g').data(cats).join('g')
        .attr('cursor','pointer')
        .attr('transform', (d,i) => `translate(0,${{i*22}})`)
        .on('click', (ev,cat) => {{
          if (active.has(cat)) active.delete(cat); else active.add(cat);
          row.selectAll('rect').attr('opacity', d => active.has(d)?1:0.25);
          row.selectAll('text').attr('opacity', d => active.has(d)?1:0.35);
          dots.attr('opacity', d => (!COLORCOL || active.has(d[COLORCOL])) ? 0.92 : 0.08);
        }});
      row.append('rect').attr('width',12).attr('height',12).attr('rx',2).attr('fill', d => color(d));
      row.append('text').attr('x',16).attr('y',6).attr('dy','.35em').style('font','12px sans-serif')
        .text(d => d);
    }}

    status.textContent = 'Listo. Pasa el mouse para ver detalles. Click en la leyenda para filtrar.';
  }} catch (e) {{
    status.textContent = 'Error: ' + (e && e.stack ? e.stack : e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>Scatter listo (#{uid})</small>")


########
def ParallelEnergy(
    df,
    years,
    tech_col="Technology_std",   # columnas con 'Solar','Wind','Hydro','Bio','Fossil'
    label_col="Country",
    dims=("Solar","Wind","Hydro","Bio","Fossil"),
    year_start=None,             # ej. "F2023"; si None, toma el último de 'years'
    width=1150,
    height=600,
    log_axes=False,
    normalize=False,             # normaliza cada eje por año (0-1) para comparar “forma”
    reorder=True,
):
    """
    Paralelas interactivas por AÑO (slider):
      - df: tabla larga con columnas: [Country, Technology_std, F2000..F2023]
      - years: lista de columnas de año (["F2000",...,"F2023"])
      - dims: orden inicial de tecnologías a mostrar
    """
    import json, uuid
    import pandas as pd
    from IPython.display import HTML, Javascript, display

    # --- sanity ---
    years = [c for c in years if c in df.columns]
    if not years:
        raise ValueError("La lista 'years' está vacía o no coincide con las columnas del dataframe.")

    dims = list(dims)
    miss_req = [c for c in [tech_col, label_col] if c not in df.columns]
    if miss_req:
        raise KeyError(f"Faltan columnas requeridas {miss_req}")

    # quedarnos solo con las 5 tecnologías de 'dims'
    d = df[df[tech_col].isin(dims)].copy()

    # a números
    for y in years:
        d[y] = pd.to_numeric(d[y], errors="coerce")

    # agrega por país+tecnología (por si hay desgloses)
    agg = d.groupby([label_col, tech_col])[years].sum(min_count=1).reset_index()

    # construyo un “cubo”: por país, vector anual por tecnología
    countries = agg[label_col].unique().tolist()
    recs = []
    for c in countries:
        block = agg[agg[label_col] == c]
        item = {"label": c}
        for t in dims:
            row = block[block[tech_col] == t]
            if row.empty:
                item[t] = [0.0]*len(years)
            else:
                vals = []
                r = row.iloc[0]
                for y in years:
                    v = float(r[y]) if pd.notna(r[y]) else 0.0
                    vals.append(v)
                item[t] = vals
        recs.append(item)

    payload = {
        "years": years,
        "dims": dims,
        "records": recs,
        "label": label_col,
    }

    uid = f"parY-{uuid.uuid4().hex[:8]}"
    jsdata = json.dumps(payload, ensure_ascii=False)
    start_year = year_start if (year_start in years) else years[-1]

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

    // ===== Datos base =====
    const pack = {jsdata};
    let DIMS   = pack.dims.slice();            // orden de ejes (arrastrable)
    const YEARS = pack.years;
    const R = pack.records;

    const W = {width}, H = {height};
    const m = {{ top: 92, right: 260, bottom: 40, left: 80 }};
    const iW = W - m.left - m.right, iH = H - m.top - m.bottom;

    const useLog = {str(log_axes).lower()};
    const normalize = {str(normalize).lower()};
    const allowReorder = {str(reorder).lower()};

    // colores coherentes con el resto de la lib
    const color = d3.scaleOrdinal(
      ["Fossil","Hydro","Wind","Solar","Bio"],
      ["#60a5fa","#f59e0b","#ef4444","#2dd4bf","#9b59b6"]
    );

    // ===== helpers =====
    function datasetFor(idxYear) {{
      const yearName = YEARS[idxYear];
      return R.map(r => {{
        const obj = {{ Country: r.label }};
        // valores por tecnología ese año
        let bestDim = DIMS[0], bestVal = +r[DIMS[0]][idxYear] || 0;
        for (const dim of DIMS) {{
          const v = +r[dim][idxYear] || 0;
          obj[dim] = v;
          if (v > bestVal) {{ bestVal = v; bestDim = dim; }}
        }}
        obj.DominantTech = bestDim;
        return obj;
      }});
    }}

    function normalizeByDim(data) {{
      // normaliza 0-1 por cada dim para ese año
      const ext = {{}};
      for (const d of DIMS) {{
        const vals = data.map(x => +x[d]).filter(Number.isFinite);
        const mn = d3.min(vals), mx = d3.max(vals);
        ext[d] = (mx>mn) ? [mn,mx] : [0,1];
      }}
      return data.map(row => {{
        const o = {{ Country: row.Country, DominantTech: row.DominantTech }};
        for (const d of DIMS) {{
          const [mn,mx] = ext[d];
          const v = +row[d]||0;
          o[d] = (mx>mn) ? (v-mn)/(mx-mn) : 0;
        }}
        return o;
      }});
    }}

    // ===== UI =====
    const root = d3.select("#{uid}");
    root.html("");

    const title = root.append("div")
      .style("margin","0 0 6px 6px")
      .style("font","600 16px/1.3 sans-serif")
      .style("color","#e5e7eb");

    root.append("div")
      .style("margin","0 0 8px 6px")
      .style("font","12px/1.35 sans-serif")
      .style("color","#94a3b8")
      .text("Paralelas por año: cada eje es una tecnología (MW). Una línea = país. Color = tecnología dominante. Izquierda: slider de año; Arrastra el nombre del eje para reordenarlo; usa brush para filtrar.");

    // Controles
    const controls = root.append("div").style("display","flex").style("gap","10px").style("align-items","center").style("margin","6px 0 8px 6px");
    controls.append("span").style("color","#cbd5e1").style("font","12px sans-serif").text("Año:");
    const slider = controls.append("input").attr("type","range")
      .attr("min", 0).attr("max", YEARS.length-1)
      .attr("value", YEARS.indexOf({json.dumps(start_year)}))
      .style("width","320px");
    const yearLabel = controls.append("span").style("color","#e5e7eb").style("font","12px sans-serif").text({json.dumps(start_year)});

    const svg = root.append("svg").attr("width", W).attr("height", H);
    const g = svg.append("g").attr("transform", `translate(${{m.left}},${{m.top}})`);

    let idxYear = YEARS.indexOf({json.dumps(start_year)});
    let DATA = datasetFor(idxYear);
    if (normalize) DATA = normalizeByDim(DATA);

    title.text(`Capacidad instalada por país — ${{YEARS[idxYear]}}`);

    // Escalas
    const x = d3.scalePoint().domain(DIMS).range([0, iW]).padding(0.5);
    const y = {{}};
    function buildY(){{
      for (const k of DIMS) {{
        const vals = DATA.map(d => +d[k]).filter(v => Number.isFinite(v) && (!useLog || v>0));
        y[k] = (useLog ? d3.scaleLog() : d3.scaleLinear())
          .domain(useLog ? [Math.max(1e-6, d3.min(vals)), d3.max(vals)] : d3.extent(vals)).nice()
          .range([iH, 0]);
      }}
    }}
    buildY();

    const line = d3.line().defined(([,v]) => Number.isFinite(v));
    const path = d => line(DIMS.map(k => [x(k), y[k](+d[k])]));

    // tooltip
    const tip = document.createElement('div');
    Object.assign(tip.style, {{
      position:'fixed', zIndex:9999, pointerEvents:'none',
      background:'rgba(17,24,39,.95)', color:'#fff', padding:'10px 12px',
      borderRadius:'10px', font:'12px/1.35 sans-serif',
      boxShadow:'0 8px 24px rgba(0,0,0,.35)', opacity:0, transition:'opacity .12s'
    }});
    document.body.appendChild(tip);
    const fmt = d3.format(",.0f");
    function tipHTML(d){{
      return `<div style="font-weight:700;margin-bottom:6px">${{d.Country}}</div>` + 
             DIMS.map(k => `<div>${{k}}: <strong>${{fmt(+d[k]||0)}}</strong>${{normalize?'':' MW'}}</div>`).join("");
    }}
    function showTip(ev,d){{ tip.innerHTML = tipHTML(d); tip.style.opacity=1; tip.style.left=(ev.clientX+14)+'px'; tip.style.top=(ev.clientY+14)+'px'; }}
    function hideTip(){{ tip.style.opacity=0; }}

    // capa de líneas
    const layer = g.append("g").attr("fill","none");
    let paths = layer.selectAll("path").data(DATA).join("path")
      .attr("d", path)
      .attr("stroke", d => color(d.DominantTech || "Solar"))
      .attr("stroke-opacity", .85)
      .attr("stroke-width", 1.2)
      .on("mousemove", showTip).on("mouseleave", hideTip)
      .on("mouseover", function(){{ d3.select(this).attr("stroke-width",2); }})
      .on("mouseout",  function(){{ d3.select(this).attr("stroke-width",1.2); }});

    // ejes
    let axis = g.selectAll(".axis").data(DIMS, d=>d).join(
      enter => {{
        const a = enter.append("g").attr("class","axis").attr("transform", d => `translate(${{x(d)}},0)`);
        a.each(function(d){{ d3.select(this).call(d3.axisLeft(y[d]).ticks(6, useLog ? "~g" : undefined)); }});
        a.append("text").attr("class","axis-title").attr("y",-10).attr("text-anchor","middle")
          .style("font","12px sans-serif").style("fill","#e5e7eb").text(d=>d);
        return a;
      }},
      update => update,
      exit => exit.remove()
    );

    // brushes
    const bw = Math.min(36, Math.max(24, iW / DIMS.length * 0.5));
    function addBrushes(){{
      axis.selectAll(".brush").remove();
      axis.append("g").attr("class","brush").attr("transform", `translate(${{-bw/2}},0)`)
        .each(function(dim){{
          d3.select(this).call(d3.brushY().extent([[0,0],[bw,iH]]).on("brush end", brushed));
        }});
    }}
    const filters = {{}};
    function brushed(){{
      g.selectAll(".brush").each(function(dim){{
        const s = d3.brushSelection(this);
        if (s) {{
          const y0 = y[dim].invert(s[1]); const y1 = y[dim].invert(s[0]);
          filters[dim] = [Math.min(y0,y1), Math.max(y0,y1)];
        }} else delete filters[dim];
      }});
      const keys = Object.keys(filters);
      paths.style("display", d => {{
        for(const k of keys){{ const v=+d[k]||0; const [a,b]=filters[k]; if(v<a||v>b) return "none"; }}
        return null;
      }});
      const visible = paths.filter(function(){{return d3.select(this).style("display")!=="none"}}).size();
      status.textContent = `Año: ${{YEARS[idxYear]}} · Filtrado: ${{visible}} / ${{DATA.length}} países.`;
    }}
    addBrushes();

    // drag reorder en títulos
    if (allowReorder){{
      const dragging = {{}};
      function position(d) {{ return dragging[d] ?? x(d); }}
      const drag = d3.drag()
        .on("start",(ev,dim)=>{{ dragging[dim]=x(dim); }})
        .on("drag",(ev,dim)=>{{
          dragging[dim]=Math.max(0,Math.min(iW,ev.x));
          DIMS.sort((a,b)=>position(a)-position(b));
          x.domain(DIMS);
          axis.order().attr("transform", d => `translate(${{position(d)}},0)`);
          paths.attr("d", d => d3.line()(DIMS.map(k => [position(k), y[k](+d[k])])));
        }})
        .on("end",(ev,dim)=>{{ delete dragging[dim]; axis.transition().duration(200).attr("transform", d => `translate(${{x(d)}},0)`); paths.transition().duration(200).attr("d", d => d3.line()(DIMS.map(k => [x(k), y[k](+d[k])]))) }});
      axis.select("text.axis-title").style("cursor","grab").call(drag);
    }}

    // leyenda clicable
    const cats = ["Fossil","Hydro","Wind","Solar","Bio"];
    let active = new Set(cats);
    const lg = svg.append("g").attr("transform", `translate(${{W - m.right + 16}},${{m.top}})`);
    lg.append("text").text("Dominant").style("font","12px sans-serif").attr("fill","#e5e7eb");
    const row = lg.append("g").attr("transform","translate(0,16)").selectAll("g").data(cats).join("g")
      .attr("cursor","pointer").attr("transform",(d,i)=>`translate(0,${{i*22}})`)
      .on("click",(ev,cat)=>{{
        if(active.has(cat)) active.delete(cat); else active.add(cat);
        row.selectAll("rect").attr("opacity", d => active.has(d)?1:0.25);
        row.selectAll("text").attr("opacity", d => active.has(d)?1:0.35);
        paths.attr("stroke-opacity", d => active.has(d.DominantTech)? .85 : .06);
      }});
    row.append("rect").attr("width",12).attr("height",12).attr("rx",2).attr("fill", d=>color(d));
    row.append("text").attr("x",16).attr("y",6).attr("dy",".35em").style("font","12px sans-serif").attr("fill","#e5e7eb").text(d=>d);

    // ===== actualización por año =====
    function updateYear(newIdx){{
      idxYear = newIdx;
      yearLabel.text(YEARS[idxYear]);
      title.text(`Capacidad instalada por país — ${{YEARS[idxYear]}}`);
      DATA = datasetFor(idxYear);
      if (normalize) DATA = normalizeByDim(DATA);

      // y & ejes
      buildY();
      axis.each(function(d){{ d3.select(this).call(d3.axisLeft(y[d]).ticks(6, useLog ? "~g" : undefined)); }});

      // limpiar filtros y brushes (para evitar rangos inválidos)
      Object.keys(filters).forEach(k=>delete filters[k]);
      addBrushes();

      // paths
      paths = layer.selectAll("path").data(DATA, d => d.Country).join("path")
        .attr("stroke", d => color(d.DominantTech || "Solar"))
        .attr("stroke-opacity", .85)
        .attr("fill","none")
        .attr("stroke-width", 1.2)
        .on("mousemove", showTip).on("mouseleave", hideTip)
        .on("mouseover", function(){{ d3.select(this).attr("stroke-width",2); }})
        .on("mouseout",  function(){{ d3.select(this).attr("stroke-width",1.2); }})
        .transition().duration(250)
        .attr("d", d => d3.line()(DIMS.map(k => [x(k), y[k](+d[k])])));
      status.textContent = `Año: ${{YEARS[idxYear]}} · Filtrado: ${{DATA.length}} / ${{DATA.length}} países.`;
    }}

    slider.on("input", (ev)=> updateYear(+ev.target.value));
    // arranque
    updateYear(idxYear);

  }} catch(e) {{
    status.textContent = "Error: " + (e && e.stack ? e.stack : e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>ParallelEnergyByYear listo (#{uid})</small>")

####
def BeeSwarmCapacity(df, year_col, tech_col="Technology_std", country_col="Country",
                     width=960, height=560, log_y=True):
    """
    Un punto = 1 fila país–tecnología del año dado.
    X = tecnología (categoría con jitter); Y = capacidad (MW).
    Leyenda clicable + tooltip con país, tecnología y valor.
    """
    import json, uuid
    from IPython.display import HTML, Javascript, display
    import pandas as pd

    if year_col not in df.columns:
        raise KeyError(f"{year_col} no existe en df")
    for col in [tech_col, country_col]:
        if col not in df.columns:
            raise KeyError(f"{col} no existe en df")

    d = df[[country_col, tech_col, year_col]].dropna(subset=[year_col]).copy()
    if d.empty:
        return display(HTML("<em>Sin datos para ese año.</em>"))

    d[year_col] = pd.to_numeric(d[year_col], errors="coerce")
    d = d.dropna(subset=[year_col])
    payload = json.dumps(d.to_dict(orient="records"), ensure_ascii=False)

    uid = f"sw-{uuid.uuid4().hex[:8]}"
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Renderizando BeeSwarm…</div>
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

    const raw  = {payload};
    const tech = {json.dumps(tech_col)};
    const name = {json.dumps(country_col)};
    const val  = {json.dumps(year_col)};
    const useLog = {str(log_y).lower()};

    const W = {width}, H = {height};
    const m = {{top: 24, right: 24, bottom: 60, left: 70}};
    const iW = W - m.left - m.right, iH = H - m.top - m.bottom;

    const svg = d3.select('#{uid}').append('svg').attr('width', W).attr('height', H);
    const g   = svg.append('g').attr('transform', `translate(${{m.left}},${{m.top}})`);

    const cats = [...new Set(raw.map(d => d[tech]))];
    const x = d3.scaleBand().domain(cats).range([0, iW]).padding(0.25);
    const v = raw.map(d => +d[val]).filter(Number.isFinite);
    const y = (useLog ? d3.scaleLog() : d3.scaleLinear())
      .domain(useLog ? [Math.max(1e-6, d3.min(v)), d3.max(v)] : d3.extent(v)).nice()
      .range([iH, 0]);
    const color = d3.scaleOrdinal(cats, d3.schemeTableau10);

    // Ejes
    g.append('g').attr('transform', `translate(0,${{iH}})`).call(d3.axisBottom(x));
    g.append('g').call(d3.axisLeft(y).ticks(8, useLog ? "~g" : undefined));
    g.append('text').attr('x', iW/2).attr('y', iH+48).attr('text-anchor','middle').style('font','12px sans-serif').text(tech);
    g.append('text').attr('transform','rotate(-90)').attr('x', -iH/2).attr('y', -54).attr('text-anchor','middle').style('font','12px sans-serif').text(val + " (MW)");

    // Tooltip
    const tip = document.createElement('div');
    Object.assign(tip.style, {{
      position:'fixed', zIndex:9999, pointerEvents:'none',
      background:'rgba(17,24,39,.92)', color:'#fff', padding:'8px 10px',
      borderRadius:'8px', font:'12px sans-serif', boxShadow:'0 4px 16px rgba(0,0,0,.25)', opacity:0, transition:'opacity .12s'
    }});
    document.body.appendChild(tip);
    const fmt = d3.format(",.0f");
    function showTip(event,d){{ tip.innerHTML = `<div style='font-weight:600'>${{d[name]}}</div><div>${{d[tech]}}: <strong>${{fmt(+d[val]||0)}}</strong> MW</div>`; tip.style.opacity=1; tip.style.left=(event.clientX+14)+'px'; tip.style.top=(event.clientY+14)+'px'; }}
    function hideTip(){{ tip.style.opacity=0; }}

    // Puntos con jitter horizontal dentro de cada categoría
    const r = 4;
    const nodes = raw.map(d => ({{
      x: x(d[tech]) + x.bandwidth()/2 + (Math.random()-0.5) * x.bandwidth()*0.6,
      y: y(+d[val]),
      c: d[tech],
      d
    }}));

    // Colisión simple (relaja un poco)
    for (let k=0; k<2; k++) {{
      for (let i=0; i<nodes.length; i++) {{
        for (let j=i+1; j<nodes.length; j++) {{
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.hypot(dx,dy);
          const min = r*2 + 0.5;
          if (dist < min) {{
            const ux = dx / (dist||1), uy = dy / (dist||1);
            const shift = (min - dist)/2;
            nodes[i].x -= ux * shift; nodes[i].y -= uy * shift;
            nodes[j].x += ux * shift; nodes[j].y += uy * shift;
          }}
        }}
      }}
    }}

    const dots = g.selectAll('circle').data(nodes).join('circle')
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)
      .attr('r', r)
      .attr('fill', d => color(d.c))
      .attr('opacity', 0.9)
      .on('mousemove', (ev,d) => showTip(ev,d.d))
      .on('mouseleave', hideTip);

    // Leyenda clicable
    let active = new Set(cats);
    const lg = svg.append('g').attr('transform', `translate(${{W - m.right - 100}},${{m.top}})`);
    const row = lg.selectAll('g').data(cats).join('g')
      .attr('cursor','pointer')
      .attr('transform', (d,i) => `translate(0,${{i*22}})`)
      .on('click', (ev,cat) => {{
        if (active.has(cat)) active.delete(cat); else active.add(cat);
        row.selectAll('rect').attr('opacity', d => active.has(d)?1:0.25);
        row.selectAll('text').attr('opacity', d => active.has(d)?1:0.35);
        dots.attr('opacity', d => active.has(d.c)?0.9:0.06);
      }});
    row.append('rect').attr('width',12).attr('height',12).attr('rx',2).attr('fill', d => color(d));
    row.append('text').attr('x',16).attr('y',6).attr('dy','.35em').style('font','12px sans-serif').text(d => d);

    status.textContent = 'Listo. Un punto = país–tecnología; X=tecnología, Y=MW.';
  }} catch (e) {{
    status.textContent = 'Error: ' + (e && e.stack ? e.stack : e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>BeeSwarm listo (#{uid})</small>")

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
    title=None,
    custom_colors=None
):
    """
    Radial stacked bar chart mejorado con ordenamiento animado.
    
    Args:
        df: DataFrame en formato largo
        group_col: columna para cada barra alrededor del círculo
        category_col: columna para capas apiladas
        value_col: valores numéricos
        agg: 'sum' o 'mean'
        width/height: dimensiones SVG
        inner_radius: radio interno (espacio para leyenda)
        pad_angle: espaciado angular
        color_scheme: esquema de colores D3 (ej: 'schemeSpectral')
        sort_on_click: permite ordenar al hacer clic (True por defecto)
        title: título opcional para el gráfico
        custom_colors: lista de colores personalizados (hexadecimal)
    """
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
    
    # Procesar colores personalizados
    if custom_colors is not None:
        if isinstance(custom_colors, set):  # Convertir set a lista si es necesario
            custom_colors = list(custom_colors)
        colors_json = json.dumps(custom_colors)
        use_custom_colors = "true"
    else:
        colors_json = "null"
        use_custom_colors = "false"
    
    uid = f"radialstack-{uuid.uuid4().hex[:8]}"

    display(HTML(f"""
<div id="{uid}-container" style="display: flex; justify-content: center; align-items: center; margin-top: 20px;">
  <div id="{uid}" style="position: relative;"></div>
</div>
<div id="{uid}-toolbar" style="text-align: center; margin: 10px 0;">
  <button id="{uid}-sort-btn" style="padding: 8px 15px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; font-weight: bold;">
    Ordenar por tamaño
  </button>
  <button id="{uid}-reset-btn" style="padding: 8px 15px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; margin-left: 10px;">
    Restaurar orden
  </button>
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

    // Asegurarse que D3 está cargado
    console.log("D3 cargado correctamente:", d3.version);

    // Referencias a los botones
    const sortBtn = document.getElementById('{uid}-sort-btn');
    const resetBtn = document.getElementById('{uid}-reset-btn');
    
    if (!sortBtn || !resetBtn) {{
      console.error("Botones no encontrados:", {{sortBtn, resetBtn}});
      throw new Error("No se pudieron encontrar los botones de ordenamiento");
    }}

    const mount = document.getElementById('{uid}');
    mount.innerHTML = '';

    // Datos originales como texto JSON para poder restaurarlos después
    const originalDataJson = '{payload}';
    let data = JSON.parse(originalDataJson);
    const keys = {categories_json};
    const title = {title_json};
    const customColors = {colors_json};
    const useCustomColors = {use_custom_colors};
    
    const W = {width};
    const H = {height};
    const innerRadius = {inner_radius};
    const outerRadius = Math.min(W, H) / 2 - 60;
    const padAngle = {pad_angle};

    // Estado de ordenamiento
    let sorted = false;
    
    // SVG con viewBox para mejor responsividad
    const svg = d3.select(mount)
      .append('svg')
      .attr('width', W)
      .attr('height', H)
      .attr('viewBox', [-W / 2, -H / 2, W, H])
      .style('width', '100%')
      .style('height', 'auto')
      .style('font', '11px sans-serif');
      
    // Grupo principal
    const g = svg.append('g');

    // Escala angular (alrededor del círculo)
    const x = d3.scaleBand()
      .domain(data.map(d => d.group))
      .range([0, 2 * Math.PI])
      .align(0);

    // Escala radial (desde el centro hacia afuera)
    const yMax = d3.max(data, d => d3.sum(keys, k => +d[k]));
    const y = d3.scaleRadial()
      .domain([0, yMax])
      .range([innerRadius, outerRadius]);

    // Configuración de colores
    let colorScale;
    
    if (useCustomColors) {{
      // Usar colores personalizados
      colorScale = d3.scaleOrdinal()
        .domain(keys)
        .range(customColors);
    }} else {{
      // Usar esquema de colores de D3
      const numColors = keys.length;
      let colorRange;
      
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
      
      colorScale = d3.scaleOrdinal()
        .domain(keys)
        .range(colorRange);
    }}

    // Formatos para números
    const formatValue = d3.format(",.1f");
    const formatPercent = d3.format(".1%");

    // Generador de arcos
    const arc = d3.arc()
      .innerRadius(d => y(d[0]))
      .outerRadius(d => y(d[1]))
      .startAngle(d => x(d.data.group))
      .endAngle(d => x(d.data.group) + x.bandwidth())
      .padAngle(padAngle)
      .padRadius(innerRadius);

    // FUNCIÓN RENDER MEJORADA
    function render(animate = false, duration = 1500) {{
      console.log("Renderizando con animación:", animate, "duración:", duration);
      
      // Stack generator
      const series = d3.stack().keys(keys)(data);
      
      // Actualizar dominio x (importante para reordenamiento)
      x.domain(data.map(d => d.group));

      // Selección y actualización de grupos de barras
      const barGroups = g.selectAll('.series-group')
        .data(series, d => d.key);
      
      barGroups.exit().remove();
      
      // Crear nuevos grupos para series
      const barGroupsEnter = barGroups.enter()
        .append('g')
        .attr('class', 'series-group')
        .attr('fill', d => colorScale(d.key));
      
      // Unir grupos existentes y nuevos
      const allBarGroups = barGroupsEnter.merge(barGroups);
      
      // Efecto visual de transición general
      if (animate) {{
        allBarGroups
          .transition()
          .duration(200)
          .style('opacity', 0.7)
          .transition()
          .duration(200)
          .style('opacity', 1);
      }}

      // Para cada grupo, actualizar los paths (segmentos del arco)
      allBarGroups.each(function(seriesData) {{
        // Seleccionar paths existentes y vincular nuevos datos
        const paths = d3.select(this).selectAll('path')
          .data(seriesData.map(d => ({{...d, key: seriesData.key}})), 
                d => d.data.group);
        
        // Quitar paths que ya no necesitamos
        paths.exit()
          .transition()
          .duration(animate ? duration : 0)
          .attrTween('d', d => {{
            // Animación de salida (colapsar al centro)
            const i = d3.interpolate(
              d,
              {{...d, 1: d[0]}}  // Colapsar altura a cero
            );
            return t => arc(i(t));
          }})
          .remove();
        
        // Actualizar paths existentes con transición suave
        paths.transition()
          .duration(animate ? duration : 0)
          .attrTween('d', function(d) {{
            // Crear interpolación simple para una transición suave
            const start = this.getAttribute('d') || arc({{...d, 1: d[0]}}); // Fallback
            const end = arc(d);
            return t => {{
              return start.length > 0 ? d3.interpolate(start, end)(t) : end;
            }};
          }});
        
        // Añadir nuevos paths con animación de entrada
        paths.enter()
          .append('path')
          .attr('d', d => {{
            // Comienza como un arco sin altura
            return arc({{...d, 1: d[0]}});
          }})
          .attr('stroke', '#fff')
          .attr('stroke-width', 1)
          .style('opacity', 0.85)
          .transition()
          .duration(animate ? duration : 0)
          .attrTween('d', d => {{
            // Animación de crecimiento
            const i = d3.interpolate(
              {{...d, 1: d[0]}},  // Comenzar con altura cero
              d
            );
            return t => arc(i(t));
          }})
          .on('end', function() {{
            // Configurar eventos después de la animación
            d3.select(this)
              .on('mouseover', function(event, d) {{
                // Destacar al pasar el ratón
                d3.select(this)
                  .style('opacity', 1)
                  .style('stroke', '#333')
                  .style('stroke-width', 2);
                
                // Mostrar información
                const total = d3.sum(keys, k => d.data[k]);
                const value = d.data[d.key];
                const percentage = value / total;
                
                status.textContent = `${{d.data.group}} – ${{d.key}}: ${{formatValue(value)}} (${{formatPercent(percentage)}})`;
              }})
              .on('mouseout', function() {{
                // Restaurar estilo al salir
                d3.select(this)
                  .style('opacity', 0.85)
                  .style('stroke', '#fff')
                  .style('stroke-width', 1);
                
                status.textContent = sorted ? 
                  'Visualización ordenada por tamaño. Haz clic en "Restaurar orden" para volver al orden original.' : 
                  'Haz clic en "Ordenar por tamaño" para reorganizar.';
              }})
              .append('title')
              .text(d => {{
                const total = d3.sum(keys, k => d.data[k]);
                const value = d.data[d.key];
                const percentage = value / total;
                return `${{d.data.group}} - ${{d.key}}: ${{formatValue(value)}} (${{formatPercent(percentage)}})`;
              }});
          }});
      }});
      
      // Actualizar etiquetas de grupos (en el perímetro)
      const labelGroups = g.selectAll('.label-group')
        .data(data, d => d.group);
      
      labelGroups.exit().remove();
      
      const labelGroupsEnter = labelGroups.enter()
        .append('g')
        .attr('class', 'label-group')
        .attr('text-anchor', 'middle');
      
      const allLabelGroups = labelGroupsEnter.merge(labelGroups);
      
      allLabelGroups.transition()
        .duration(animate ? duration : 0)
        .attr('transform', d => {{
          const angle = ((x(d.group) + x.bandwidth() / 2) * 180 / Math.PI) - 90;
          return `rotate(${{angle}})translate(${{outerRadius + 10}},0)`;
        }});
      
      // Añadir líneas y textos a las etiquetas
      labelGroupsEnter.append('line')
        .attr('x1', 0)
        .attr('x2', 0)
        .attr('y1', 0)
        .attr('y2', 7)
        .attr('stroke', '#999')
        .attr('stroke-width', 1);
      
      labelGroupsEnter.append('text')
        .style('font-size', '9px')
        .style('fill', '#333');
      
      allLabelGroups.select('text')
        .transition()
        .duration(animate ? duration : 0)
        .attr('transform', d => {{
          const angle = (x(d.group) + x.bandwidth() / 2);
          return ((angle + Math.PI / 2) % (2 * Math.PI) < Math.PI) ? 
            'rotate(90)translate(10,-2)' : 
            'rotate(-90)translate(-10,-2)';
        }})
        .text(d => d.group);
    }}

    // Grid circular (círculos concéntricos)
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

    // Etiquetas de valores en círculos concéntricos
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

    // Leyenda central mejorada
    const legendG = svg.append('g')
      .attr('class', 'legend')
      .attr('text-anchor', 'start');
    
    // Fondo para la leyenda central
    if (keys.length > 1) {{
      legendG.append('rect')
        .attr('x', -innerRadius * 0.8)
        .attr('y', -innerRadius * 0.6)
        .attr('width', innerRadius * 1.6)
        .attr('height', Math.min(keys.length * 22 + 40, innerRadius * 1.2))
        .attr('rx', 10)
        .attr('ry', 10)
        .attr('fill', '#fff')
        .attr('opacity', 0.8);
    }}
    
    // Título en el centro de la leyenda
    if (title) {{
      legendG.append('text')
        .attr('x', 0)
        .attr('y', -innerRadius * 0.4)
        .attr('text-anchor', 'middle')
        .attr('font-size', '14px')
        .attr('font-weight', 'bold')
        .text(title);
    }}

    // Distribuir items de leyenda en dos columnas si hay muchos
    const legendItems = legendG.selectAll('.legend-item')
      .data(keys)
      .join('g')
      .attr('class', 'legend-item')
      .attr('transform', (d, i) => {{
        const itemsPerColumn = Math.min(Math.ceil(keys.length / 2), 6);
        const column = Math.floor(i / itemsPerColumn);
        const row = i % itemsPerColumn;
        const x = (column === 0 ? -innerRadius * 0.6 : innerRadius * 0.1);
        const y = -innerRadius * 0.25 + row * 22;
        return `translate(${{x}},${{y}})`;
      }});

    // Cuadrados de color en la leyenda
    legendItems.append('rect')
      .attr('width', 16)
      .attr('height', 16)
      .attr('fill', d => colorScale(d))
      .attr('stroke', '#999')
      .attr('stroke-width', 0.5)
      .attr('rx', 2);

    // Texto de la leyenda
    legendItems.append('text')
      .attr('x', 22)
      .attr('y', 9)
      .attr('dy', '0.32em')
      .attr('font-size', '11px')
      .text(d => d);

    // Renderizado inicial
    render(false);
    
    // FUNCIÓN DE ORDENAMIENTO con animación
    function sortBySize() {{
      console.log("Ejecutando ordenamiento por tamaño...");
      
      // No hacer nada si ya está ordenado
      if (sorted) return;
      
      // Ordenar datos por valor total descendente
      data.sort((a, b) => {{
        const sumA = d3.sum(keys, k => +a[k]);
        const sumB = d3.sum(keys, k => +b[k]);
        return d3.descending(sumA, sumB);
      }});
      
      // Actualizar estado
      sorted = true;
      
      // Cambiar estilo de botones
      sortBtn.style.backgroundColor = '#e5e7eb';
      sortBtn.style.fontWeight = 'bold';
      resetBtn.style.backgroundColor = '#f3f4f6';
      resetBtn.style.fontWeight = 'normal';
      
      // Renderizar con animación
      render(true);
      
      // Actualizar mensaje de estado
      status.textContent = 'Visualización ordenada por tamaño. Haz clic en "Restaurar orden" para volver al orden original.';
    }}
    
    // FUNCIÓN PARA RESTAURAR ORDEN ORIGINAL
    function resetOrder() {{
      console.log("Restaurando orden original...");
      
      // No hacer nada si ya está en orden original
      if (!sorted) return;
      
      // Restaurar datos originales
      data = JSON.parse(originalDataJson);
      
      // Actualizar estado
      sorted = false;
      
      // Cambiar estilo de botones
      sortBtn.style.backgroundColor = '#f3f4f6';
      sortBtn.style.fontWeight = 'normal';
      resetBtn.style.backgroundColor = '#e5e7eb';
      resetBtn.style.fontWeight = 'bold';
      
      // Renderizar con animación
      render(true);
      
      // Actualizar mensaje de estado
      status.textContent = 'Orden original restaurado. Haz clic en "Ordenar por tamaño" para reorganizar.';
    }}
    
    // CONFIGURAR LOS EVENT HANDLERS
    
    // 1. Usar evento onclick directamente (más compatible)
    sortBtn.onclick = sortBySize;
    resetBtn.onclick = resetOrder;
    
    // 2. Agregar también event listeners usando D3 como alternativa
    d3.select(sortBtn).on("click", sortBySize);
    d3.select(resetBtn).on("click", resetOrder);
    
    // 3. Opcionalmente, agregar la funcionalidad de clic en el SVG
    if ({sort_on_click}) {{
      svg.on("click", () => {{
        if (sorted) {{
          resetOrder();
        }} else {{
          sortBySize();
        }}
      }});
    }}
    
    // Mensaje inicial
    status.textContent = 'Haz clic en "Ordenar por tamaño" para reorganizar el gráfico.';

  }} catch (e) {{
    console.error("Error en RadialStackedBar:", e);
    status.textContent = 'Error: ' + (e.message || e);
  }}
}})();
"""
    display(Javascript(js))
    return HTML(f"<small>Radial Stacked Bar Chart listo (#{uid})</small>")
########alex
def WorldRenewable(
    df,
    year_cols=None,                 # si None: detecta columnas Fxxxx
    country_col="Country",
    iso3_col="ISO3",
    tech_col="Technology_std",      # valores: Solar/Wind/Hydro/Bio/Fossil
    start_year=None,                # ej. "F2023" (si None usa último)
    width=1200,
    height=660,
    normalize=False,                # reservado para extensiones futuras
):
    """
    Coropleta mundial (% renovable) + línea temporal por país.
    - Fuente: df con columnas Fxxxx y Technology_std en {Solar, Wind, Hydro, Bio, Fossil}
    - GeoJSON: Isea/assets/world.geojson (debe estar empaquetado)
    """
    import json, uuid, math
    import pandas as pd
    from IPython.display import HTML, Javascript, display
    from importlib.resources import files

    # --- 1) Detectar años ---
    if year_cols is None:
        year_cols = [c for c in df.columns if isinstance(c, str) and c.startswith("F")]
    if not year_cols:
        raise ValueError("No se encontraron columnas de año (F2000..F2023).")

    # --- 2) Asegurar numéricos ---
    df = df.copy()
    for c in year_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # --- 3) Mantener solo las 5 tecnologías ---
    tech_keep = ["Solar", "Wind", "Hydro", "Bio", "Fossil"]
    d = df[df[tech_col].isin(tech_keep)][[country_col, iso3_col, tech_col] + year_cols].copy()

    # --- 4) Agregar por país+tecnología ---
    agg = d.groupby([country_col, iso3_col, tech_col])[year_cols].sum(min_count=1).reset_index()

    # --- 5) Construir % renovable por país y año ---
    countries = agg[[country_col, iso3_col]].drop_duplicates().values.tolist()
    years = list(year_cols)
    if start_year is None or start_year not in years:
        start_year = years[-1]

    records = []  # [{iso3, name, shares:[0..1 or None]}]
    for name, iso3 in countries:
        block = agg[agg[iso3_col] == iso3]
        vals = {}
        for t in tech_keep:
            r = block[block[tech_col] == t]
            if r.empty:
                vals[t] = {y: 0.0 for y in years}
            else:
                s = r.iloc[0][years].to_dict()
                vals[t] = {y: float(s.get(y, 0.0)) if pd.notna(s.get(y, None)) else 0.0 for y in years}

        shares = []
        for y in years:
            ren = vals["Solar"][y] + vals["Wind"][y] + vals["Hydro"][y] + vals["Bio"][y]
            tot = ren + vals["Fossil"][y]
            shares.append((ren / tot) if (tot and not math.isclose(tot, 0.0)) else None)

        records.append({"iso3": iso3, "name": name, "shares": shares})

    idx_now = years.index(start_year)

    # --- 6) Cargar world.geojson desde el paquete y parsear en Python ---
    try:
        world_text = (files("Isea.assets") / "world.geojson").read_text(encoding="utf-8")
        world_obj  = json.loads(world_text)
    except Exception as e:
        raise FileNotFoundError(
            "No se pudo leer Isea/assets/world.geojson. "
            "Colócalo en Isea/assets/ y en pyproject.toml incluye 'Isea/assets/**'."
        ) from e

    # --- 7) Payload para JS ---
    payload = {
        "years": years,
        "idx_now": idx_now,
        "records": records,
    }

    uid = f"wrld-{uuid.uuid4().hex[:8]}"

    # Contenedor
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Renderizando…</div>
<style>
  .vis {{ width: 100%; min-height: 80px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
</style>
"""))

    # --- 8) JavaScript (sin f-string). Usamos placeholders y los reemplazamos al final. ---
    js = r"""
(async () => {
  const status = document.getElementById("__UID__-status");
  try {
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const world = __WORLDOBJ__;         // GeoJSON ya como objeto
    const pack  = __PAYLOAD__;          // { years, idx_now, records }

    let YEARS = pack.years;
    let idx   = +pack.idx_now;
    const REC = pack.records;

    const W = __WIDTH__, H = __HEIGHT__;
    const m = { top: 72, right: 28, bottom: 46, left: 28 };
    const iW = W - m.left - m.right;
    const mapH  = Math.floor(H*0.62);
    const lineH = H - mapH - 32;

    const root = d3.select("#__UID__");
    root.html("");

    // Título + ayuda
    root.append("div")
      .style("font","600 16px/1.3 sans-serif")
      .style("color","#e5e7eb")
      .style("margin","0 0 6px 6px")
      .text("Participación de renovables en la capacidad instalada por país");

    root.append("div")
      .style("font","12px/1.35 sans-serif")
      .style("color","#94a3b8")
      .style("margin","0 0 8px 6px")
      .text("Coropleta (0–100%). Desliza el año. Haz clic en un país para ver su serie temporal. Fuente: Solar/Wind/Hydro/Bio/Fossil.");

    // Controles
    const controls = root.append("div")
      .style("display","flex")
      .style("gap","12px")
      .style("align-items","center")
      .style("margin","6px 0 10px 6px");

    controls.append("span").style("color","#cbd5e1").style("font","12px sans-serif").text("Año:");
    const slider = controls.append("input").attr("type","range")
      .attr("min", 0).attr("max", YEARS.length - 1)
      .attr("value", idx)
      .style("width","340px");
    const yearLbl = controls.append("span").style("color","#e5e7eb").style("font","12px sans-serif").text(YEARS[idx]);

    // SVG MAPA
    const svg = root.append("svg").attr("width", W).attr("height", mapH);
    const g   = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

    const proj = d3.geoNaturalEarth1().fitExtent([[0,0],[iW, mapH - m.top - m.bottom]], world);
    const path = d3.geoPath(proj);

    const fmtPct = d3.format(".0%");

    // Color 0..1
    const col = d3.scaleSequential(d3.interpolateYlGn).domain([0,1]);

    // ISO key flexible
    const isoKey = f => f.properties?.ISO_A3
                     || f.properties?.ADM0_A3
                     || f.properties?.ISO3
                     || f.properties?.iso_a3
                     || f.properties?.iso_a3_eh
                     || f.id;

    function valueAt(iso3, idxYear){
      const rec = REC.find(d => d.iso3 === iso3);
      if (!rec) return null;
      const v = rec.shares[idxYear];
      return (v==null || Number.isNaN(v)) ? null : v;
    }

    // Tooltip
    const tip = document.createElement('div');
    Object.assign(tip.style, {
      position:'fixed', zIndex:9999, pointerEvents:'none',
      background:'rgba(17,24,39,.95)', color:'#fff', padding:'8px 10px',
      borderRadius:'8px', font:'12px/1.35 sans-serif',
      boxShadow:'0 8px 24px rgba(0,0,0,.35)', opacity:0, transition:'opacity .12s'
    });
    document.body.appendChild(tip);
    function showTip(ev, name, v){
      let txt = `<div style="font-weight:700;margin-bottom:4px">${name}</div>`;
      if (v==null) txt += `<div>Sin dato</div>`;
      else txt += `<div>Renovable: <strong>${fmtPct(v)}</strong></div>`;
      tip.innerHTML = txt;
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX+12)+'px';
      tip.style.top  = (ev.clientY+12)+'px';
    }
    function hideTip(){ tip.style.opacity = 0; }

    // Países
    const countries = g.selectAll("path.country")
      .data(world.features)
      .join("path")
      .attr("class","country")
      .attr("d", path)
      .attr("fill", f => {
        const iso = isoKey(f);
        const v   = valueAt(iso, idx);
        return (v==null) ? "#374151" : col(v);
      })
      .attr("stroke","#111").attr("stroke-width",0.25)
      .on("mousemove", (ev,f) => {
        const iso  = isoKey(f);
        const rec  = REC.find(d => d.iso3===iso);
        const name = rec?.name || (f.properties?.NAME || "");
        const v    = valueAt(iso, idx);
        showTip(ev, name, v);
      })
      .on("mouseleave", hideTip)
      .on("click", (ev,f) => {
        const iso = isoKey(f);
        selectCountry(iso);
      });

    // Leyenda (0%-100%)
    const L = 160, Hbar = 10;
    const gradId = "grad-"+Math.random().toString(36).slice(2);
    const defs = svg.append("defs");
    const lg = defs.append("linearGradient").attr("id", gradId);
    d3.range(0, 11).forEach(i => {
      const t = i/10;
      lg.append("stop").attr("offset", `${t*100}%`).attr("stop-color", col(t));
    });
    svg.append("rect")
      .attr("x", W- L - 16).attr("y", 10).attr("width", L).attr("height", Hbar)
      .attr("fill", `url(#${gradId})`).attr("stroke","#222");
    svg.append("text").attr("x", W- L - 16).attr("y", 8).attr("fill","#e5e7eb")
      .style("font","12px sans-serif").text("0%");
    svg.append("text").attr("x", W- 16).attr("y", 8).attr("text-anchor","end").attr("fill","#e5e7eb")
      .style("font","12px sans-serif").text("100%");

    // ===== Línea temporal =====
    const svgLine = root.append("svg").attr("width", W).attr("height", lineH);
    const gl = svgLine.append("g").attr("transform", `translate(52,14)`);
    const lw = W - 52 - 26, lh = lineH - 20;

    const x = d3.scalePoint().domain(d3.range(YEARS.length)).range([0,lw]);
    const y = d3.scaleLinear().domain([0,1]).range([lh,0]).nice();

    gl.append("g").attr("transform",`translate(0,${lh})`).call(
      d3.axisBottom(x).tickValues(d3.range(YEARS.length).filter(i => i%Math.ceil(YEARS.length/10)===0)).tickFormat(i => YEARS[i])
    ).selectAll("text").style("font","10px sans-serif").attr("transform","rotate(-35)").style("text-anchor","end");
    gl.append("g").call(d3.axisLeft(y).ticks(6, ".0%")).selectAll("text").style("font","10px sans-serif");

    const line = d3.line().defined(v => v!=null).x((d,i)=>x(i)).y(d=>y(d));
    const linePath  = gl.append("path").attr("fill","none").attr("stroke","#60a5fa").attr("stroke-width",2);
    const lineTitle = svgLine.append("text").attr("x", 52).attr("y", 12).style("font","600 12px sans-serif").attr("fill","#e5e7eb").text("Selecciona un país…");

    function selectCountry(iso3){
      const rec = REC.find(d => d.iso3===iso3);
      if (!rec) return;
      lineTitle.text((rec.name || iso3) + " — participación renovable");
      linePath.datum(rec.shares).transition().duration(250).attr("d", line);
      countries.attr("stroke-width", d => ((d.properties?.ISO_A3||d.properties?.ADM0_A3||d.id)===iso3)? 1.2 : 0.25)
               .attr("stroke", d => ((d.properties?.ISO_A3||d.properties?.ADM0_A3||d.id)===iso3)? "#fff" : "#111");
    }

    function recolor(){
      countries.attr("fill", f => {
        const iso = isoKey(f);
        const v   = valueAt(iso, idx);
        return (v==null) ? "#374151" : col(v);
      });
      yearLbl.text(YEARS[idx]);
    }

    slider.on("input", ev => { idx = +ev.target.value; recolor(); });

    // Estado inicial
    status.textContent = `D3 OK · ${world.features?.length ?? 0} países · Año: ${YEARS[idx]}`;
    recolor();
  } catch (e) {
    const msg = (e && e.stack) ? e.stack : (''+e);
    document.getElementById("__UID__-status").textContent = 'Error: ' + msg;
  }
})();
"""

    # --- 9) Reemplazos seguros ---
    js = (js
          .replace("__UID__", uid)
          .replace("__WIDTH__", str(width))
          .replace("__HEIGHT__", str(height))
          .replace("__WORLDOBJ__", json.dumps(world_obj))
          .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
          )

    display(Javascript(js))
    return HTML(f"<small>WorldRenewable listo (#{uid})</small>")

###milan
def BubblePack(
    df,
    year=None,                   # p.ej. "F2023" (si None uso el último con datos)
    country_col="Country",
    iso3_col="ISO3",
    tech_col="Technology_std",   # en {Solar, Wind, Hydro, Bio, Fossil}
    color_by="DominantTech",     # "DominantTech" (default) o "Region" (si existe)
    value_mode="total",          # "total" (=S+W+H+Bio+Fossil) o "renewables" (=S+W+H+Bio)
    width=1200,
    height=660,
    min_label_r=18               # radio mínimo para mostrar etiqueta
):
    """
    Bubble plot (d3.pack): cada círculo = país, tamaño = capacidad (MW) en 'year',
    color = 'color_by' (DominantTech o Region). Tooltip con país y valor.
    """
    import json, uuid
    import pandas as pd
    from IPython.display import HTML, Javascript, display

    # --- detectar columnas de año ---
    year_cols = [c for c in df.columns if isinstance(c, str) and c.startswith("F") and df[c].notna().any()]
    if not year_cols:
        raise ValueError("No se encontraron columnas Fxxxx con datos.")
    if (year is None) or (year not in year_cols):
        year = year_cols[-1]

    # --- asegurar numéricos ---
    df = df.copy()
    for c in year_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # --- quedarnos con instaladas MW (por si el df completo viene con todo) ---
    if "Indicator" in df.columns and "Unit" in df.columns:
        df = df[(df["Indicator"] == "Electricity Installed Capacity") &
                (df["Unit"] == "Megawatt (MW)")].copy()

    # --- mantener sólo tecnologías esperadas ---
    tech_keep = ["Solar", "Wind", "Hydro", "Bio", "Fossil"]
    df = df[df[tech_col].isin(tech_keep)][[country_col, iso3_col, tech_col, year]].copy()

    # --- pivot país × tecnología (en el año elegido) ---
    piv = (df.pivot_table(index=[country_col, iso3_col], columns=tech_col, values=year, aggfunc="sum")
             .reindex(columns=tech_keep)
             .fillna(0.0)
             .reset_index())

    # --- valor del círculo ---
    if value_mode == "renewables":
        piv["__value__"] = piv[["Solar","Wind","Hydro","Bio"]].sum(axis=1, numeric_only=True)
    else:
        piv["__value__"] = piv[["Solar","Wind","Hydro","Bio","Fossil"]].sum(axis=1, numeric_only=True)

    # --- color por DominantTech si no hay Region o si así se pide ---
    if color_by == "Region" and ("Region" in df.columns or "Region" in piv.columns):
        pass  # usará piv["Region"] si existe (no la estamos construyendo aquí)
    else:
        color_by = "DominantTech"
        piv["DominantTech"] = piv[["Solar","Wind","Hydro","Bio","Fossil"]].idxmax(axis=1)

    # si existe columna Region en tu df y quieres usarla:
    if color_by == "Region" and "Region" not in piv.columns:
        # intenta heredar desde df si vino esa columna
        if "Region" in df.columns:
            piv = piv.merge(
                df[[country_col, iso3_col, "Region"]].drop_duplicates(),
                on=[country_col, iso3_col],
                how="left"
            )
        piv["Region"] = piv["Region"].fillna("Unknown")

    # --- construir data para JS ---
    data = []
    for _, r in piv.iterrows():
        if r["__value__"] is None or r["__value__"] <= 0:
            continue
        item = {
            "country": str(r[country_col]),
            "iso3": str(r[iso3_col]) if pd.notna(r[iso3_col]) else None,
            "value": float(r["__value__"]),
            "Solar": float(r.get("Solar", 0.0)),
            "Wind": float(r.get("Wind", 0.0)),
            "Hydro": float(r.get("Hydro", 0.0)),
            "Bio": float(r.get("Bio", 0.0)),
            "Fossil": float(r.get("Fossil", 0.0)),
        }
        if color_by == "Region":
            item["group"] = str(r.get("Region", "Unknown"))
        else:
            item["group"] = str(r.get("DominantTech", "Unknown"))
        data.append(item)

    if not data:
        raise ValueError("No hay datos > 0 para el año seleccionado.")

    uid = f"bp-{uuid.uuid4().hex[:8]}"

    # contenedor
    display(HTML(f"""
<div id="{uid}" class="vis"></div>
<div id="{uid}-status" class="status">Renderizando…</div>
<style>
  .vis {{ width: 100%; min-height: 80px; }}
  .status {{ font-size:12px; color:#64748b; margin:6px 2px; }}
</style>
"""))

    # --- JS con placeholders ---
    js = r"""
(async () => {
  const status = document.getElementById("__UID__-status");
  try {
    const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
    const d3  = mod.default ?? mod;

    const DATA  = __DATA__;               // [{country, iso3, value, group, ...}]
    const YEAR  = "__YEAR__";
    const W = __WIDTH__, H = __HEIGHT__;
    const minLabelR = __MINLABELR__;

    const root = d3.select("#__UID__");
    root.html("");

    // Título y ayuda
    root.append("div")
      .style("font","600 16px/1.3 sans-serif")
      .style("color","#e5e7eb")
      .style("margin","0 0 6px 6px")
      .text(`Capacidad instalada (${YEAR}) — Bubble pack`);

    root.append("div")
      .style("font","12px/1.35 sans-serif")
      .style("color","#94a3b8")
      .style("margin","0 0 8px 6px")
      .text("Tamaño = MW; Color = grupo seleccionado; Hover para detalle; haz clic en la leyenda para ocultar/mostrar grupos.");

    const svg = root.append("svg").attr("width", W).attr("height", H);
    const m   = {top: 8, right: 220, bottom: 8, left: 8};
    const iw  = W - m.left - m.right, ih = H - m.top - m.bottom;
    const GG  = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

    // Color por grupo
    const groups = Array.from(new Set(DATA.map(d => d.group)));
    const color = d3.scaleOrdinal()
      .domain(groups)
      .range(d3.schemeTableau10.concat(d3.schemeSet3).slice(0, groups.length));

    // Layout pack
    const packed = d3.pack().size([iw, ih]).padding(3);
    const rootH  = d3.hierarchy({children: DATA}).sum(d => Math.max(0, +d.value || 0));
    const leaves = packed(rootH).leaves();

    // Tooltip
    const tip = document.createElement('div');
    Object.assign(tip.style, {
      position:'fixed', zIndex:9999, pointerEvents:'none',
      background:'rgba(17,24,39,.95)', color:'#fff', padding:'8px 10px',
      borderRadius:'8px', font:'12px/1.35 sans-serif',
      boxShadow:'0 8px 24px rgba(0,0,0,.35)', opacity:0, transition:'opacity .12s'
    });
    document.body.appendChild(tip);
    const fmt = d3.format(",d");

    function showTip(ev, d){
      const html = `<div style="font-weight:700;margin-bottom:4px">${d.data.country}</div>`
                 + `<div>${fmt(d.data.value)} MW</div>`;
      tip.innerHTML = html;
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX+12)+'px';
      tip.style.top  = (ev.clientY+12)+'px';
    }
    function hideTip(){ tip.style.opacity = 0; }

    // Nodos
    const nodes = GG.selectAll("g.node")
      .data(leaves, d => d.data.iso3 ?? d.data.country)
      .join("g")
      .attr("class","node")
      .attr("transform", d => `translate(${d.x},${d.y})`);

    const dots = nodes.append("circle")
      .attr("class","dot")
      .attr("r", d => d.r)
      .attr("cx", 0).attr("cy", 0)
      .attr("fill", d => color(d.data.group))
      .attr("fill-opacity", 0.85)
      .attr("stroke", "#111")
      .attr("opacity", 0.85)
      .on("mousemove", function(ev,d){ d3.select(this).attr("opacity", 1); showTip(ev,d); })
      .on("mouseleave", function(){ d3.select(this).attr("opacity", 0.85); hideTip(); });

    // Etiquetas si el radio lo permite
    const labels = nodes.append("text")
      .attr("text-anchor","middle")
      .attr("pointer-events","none")
      .style("fill","#111")
      .style("font","11px sans-serif")
      .style("font-weight","600")
      .attr("opacity", d => d.r >= minLabelR ? 1 : 0);

    labels.append("tspan")
      .attr("x", 0).attr("y", -2)
      .text(d => d.r >= minLabelR ? (d.data.country || "") : "");

    labels.append("tspan")
      .attr("x", 0).attr("dy", "1.2em")
      .style("font-weight","400")
      .text(d => d.r >= minLabelR ? fmt(d.data.value) : "");

    // Leyenda a la derecha (click para filtrar)
    const legend = svg.append("g").attr("transform", `translate(${W - m.right + 20}, 8)`);
    legend.append("text").text("Grupo")
      .style("font","600 12px sans-serif").attr("fill","#e5e7eb");

    let hidden = new Set(); // grupos ocultos
    const rows = legend.selectAll("g.row")
      .data(groups)
      .enter().append("g")
      .attr("class","row")
      .attr("transform", (d,i) => `translate(0,${18 + i*20})`)
      .style("cursor","pointer")
      .on("click", (ev,gp) => {
        if (hidden.has(gp)) hidden.delete(gp); else hidden.add(gp);
        updateVisibility();
      });

    rows.append("rect").attr("width", 14).attr("height", 14)
      .attr("fill", d => color(d)).attr("stroke","#222");
    rows.append("text").attr("x", 20).attr("y", 10)
      .style("font","12px sans-serif").attr("fill","#e5e7eb")
      .text(d => d);

    function updateVisibility(){
      dots.attr("display", d => hidden.has(d.data.group) ? "none" : null);
      labels.attr("display", d => hidden.has(d.data.group) ? "none" : null);
    }

    status.textContent = `Listo · ${leaves.length} países · Año: ${YEAR}`;
  } catch (e) {
    const msg = (e && e.stack) ? e.stack : (''+e);
    document.getElementById("__UID__-status").textContent = 'Error: ' + msg;
  }
})();
"""

    js = (js
          .replace("__UID__", uid)
          .replace("__WIDTH__", str(width))
          .replace("__HEIGHT__", str(height))
          .replace("__MINLABELR__", str(int(min_label_r)))
          .replace("__YEAR__", str(year))
          .replace("__DATA__", json.dumps(data, ensure_ascii=False))
          )

    display(Javascript(js))
    return HTML(f"<small>BubblePack listo (#{uid})</small>")
