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
