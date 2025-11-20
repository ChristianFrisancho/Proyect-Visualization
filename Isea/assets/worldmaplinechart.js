// ==============================================================================
// WorldMapLineChart.js — EV-wide Version (Final Behavior)
// - Map with year slider and numeric color scale legend
// - Line chart for selected countries with adaptive Y-axis
// - Y-axis adapts only on metric change and selection change,
//   not when moving the year slider.
// - Y-axis domain based on full time series of:
//      * selected countries if any
//      * otherwise all countries
// - Mode colored lines + mode legend
// - Selection table with constrained width/scroll
// - Metric switching via Python-side dropdown
// ==============================================================================

export async function render({ model, el }) {
  const mod = await import("https://cdn.jsdelivr.net/npm/d3@7/+esm");
  const d3 = mod.default ?? mod;

  // ------------------ Extract data & options ------------------
  let data = model.get("data");
  let opts = model.get("options");

  const YEARS     = data.years;
  const YEARS_NUM = data.years_num;
  let REC         = data.records;
  let world       = data.world;

  const totalW = opts.width;
  const totalH = opts.height * 1.20;

  let metricName = opts.metric;
  let idx        = opts.idx_now;        // index in YEARS

  const mapH    = Math.floor(totalH * 0.55);
  const gap     = 50;
  const panelW  = 800;
  const chartW  = totalW - panelW - gap;
  const bottomH = totalH - mapH - 40;

  // ------------------ Clear container ------------------
  el.innerHTML = "";

  // ------------------ Layout grid ------------------
  const wrapper = document.createElement("div");
  wrapper.style.cssText = `
    display:grid;
    gap:${gap}px;
    width:${totalW}px;
    max-width:${totalW}px;
    overflow-x:auto;
    font-family:sans-serif;
    color:#94a3b8;
  `;
  el.appendChild(wrapper);

  const mapContainer = document.createElement("div");
  const bottom = document.createElement("div");
  bottom.style.cssText = `
    display:grid;
    grid-template-columns:1fr 1fr;   /* 50/50 layout */
    gap:${gap}px;
    overflow:hidden;
  `;


  wrapper.appendChild(mapContainer);
  wrapper.appendChild(bottom);

  const chartContainer = document.createElement("div");
  const panelContainer = document.createElement("div");
  bottom.appendChild(chartContainer);
  bottom.appendChild(panelContainer);

  const root = d3.select(mapContainer);

  // ------------------ Title + info bubble ------------------
  root.append("div")
    .style("font","600 18px sans-serif")
    .style("margin","0 0 6px 6px")
    .text(opts.title || metricName);

  const infoWrap = root.append("div")
    .style("display","inline-block")
    .style("position","relative")
    .style("margin","0 0 10px 8px");

  infoWrap.html(`
    <div style="
      display:inline-flex;align-items:center;justify-content:center;
      width:18px;height:18px;border-radius:50%;
      border:1.5px solid #60a5fa;color:#60a5fa;
      font-size:12px;font-weight:bold;cursor:pointer;user-select:none;">
      i
    </div>
    <div class="tooltip-panel" style="
      display:none;position:absolute;top:24px;left:0;width:260px;
      background:#1e293b;color:#e2e8f0;border:1px solid #334155;
      border-radius:8px;padding:10px 12px;font:12px/1.4 sans-serif;
      box-shadow:0 4px 10px rgba(0,0,0,.3);z-index:1000;">
      <b>${opts.title}</b><br>${opts.subtitle}
    </div>
  `);

  const iconEl = infoWrap.node().querySelector("div");
  const tooltipInfo = infoWrap.node().querySelector(".tooltip-panel");
  iconEl.addEventListener("mouseenter",()=> tooltipInfo.style.display="block");
  iconEl.addEventListener("mouseleave",()=> tooltipInfo.style.display="none");

  root.append("div")
    .style("font","12px sans-serif")
    .style("color","#94a3b8")
    .style("margin","0 0 8px 6px")
    .text(opts.subtitle);

  // ------------------ Year slider ------------------
  const controls = root.append("div")
    .style("display","flex")
    .style("align-items","center")
    .style("gap","12px")
    .style("margin","6px 0 10px 6px");

  controls.append("span")
    .style("font","12px sans-serif")
    .style("color","#cbd5e1")
    .text("Year:");

  const slider = controls.append("input")
    .attr("type","range")
    .attr("min",0)
    .attr("max",YEARS.length-1)
    .attr("value",idx)
    .style("width","260px");

  const yearLbl = controls.append("span")
    .style("font","12px sans-serif")
    .style("color","#94a3b8")
    .text(YEARS[idx]);

  // ------------------ Mode colors ------------------
  const modeColor = {
    "Cars":   "#1f77b4",
    "Vans":   "#ff7f0e",
    "Buses":  "#2ca02c",
    "Trucks": "#d62728",
  };

  function getMode(name) {
    if (!name.includes("•")) return null;
    return name.split("•")[1].trim();
  }

  // ------------------ Tooltip ------------------
  const tip = document.createElement("div");
  Object.assign(tip.style,{
    position:"fixed",
    pointerEvents:"none",
    padding:"6px 10px",
    background:"rgba(17,24,39,.95)",
    color:"#fff",
    font:"12px sans-serif",
    borderRadius:"6px",
    zIndex:9999,
    opacity:0,
    transition:"opacity .12s"
  });
  document.body.appendChild(tip);

  function showTip(ev, name, v){
    tip.innerHTML = `<strong>${name}</strong><br>${metricName}: ${v==null?"—":d3.format(".2s")(v)}`;
    tip.style.left = (ev.clientX+12)+"px";
    tip.style.top  = (ev.clientY+12)+"px";
    tip.style.opacity = 1;
  }
  function hideTip(){ tip.style.opacity = 0; }

  // ------------------ Helpers for values & keys ------------------
  function isoKey(f){
    return (
      f.properties?.ISO_A3 ||
      f.id ||
      f.properties?.ADM0_A3 ||
      f.properties?.iso_a3 ||
      f.properties?.ISO3
    );
  }

  function valueAt(iso3, yearIdx){
    const r = REC.find(d=>d.iso3===iso3);
    if (!r) return null;
    const v = r.values[yearIdx];
    return (v==null || isNaN(v)) ? null : v;
  }

  let selectedIso = new Set();

  // ------------------ Color scale for map (per year) ------------------
  function computeMaxValForYear(){
    return d3.max(
      REC.map(r => r.values[idx]).filter(v => v!=null)
    ) || 1;
  }

  let maxVal = computeMaxValForYear();
  let col = d3.scaleSequential(d3.interpolateYlGn)
              .domain([0, maxVal]);

  // ------------------ MAP ------------------
  const svg = root.append("svg")
    .attr("width", totalW)
    .attr("height", mapH);

  const gMap = svg.append("g")
    .attr("transform","translate(20,40)");

  const proj = d3.geoNaturalEarth1()
    .fitExtent([[0,0],[totalW-40,mapH-80]], world);

  const path = d3.geoPath(proj);

  const countries = gMap.selectAll("path.country")
    .data(world.features)
    .join("path")
      .attr("class","country")
      .attr("d", path)
      .attr("fill", f => {
        const v = valueAt(isoKey(f), idx);
        return v==null ? "#374151" : col(v);
      })
      .attr("stroke","#111")
      .attr("stroke-width",0.25)
      .on("mousemove",(ev,f)=>{
        const iso = isoKey(f);
        const r = REC.find(d=>d.iso3===iso);
        if (!r) return;
        showTip(ev, r.name, r.values[idx]);
      })
      .on("mouseleave", hideTip)
      .on("click",(ev,f)=> selectCountry(isoKey(f)));

  // ======================================================================
  // LINE CHART
  // ======================================================================

  // Instead of using chartW, compute width from container size later
  const chartHeight = 400;
  const chartSvg = d3.select(chartContainer)
    .append("svg")
    .style("width", "100%")
    .attr("height", chartHeight);


  // NEW: container for mode legend between linechart and table
  const midLegendContainer = d3.select(chartContainer)
    .insert("div", ":first-child")
    .attr("id", "mid-mode-legend")
    .style("display", "flex")
    .style("gap", "12px")
    .style("padding", "8px 0")  
    .style("align-items", "center");

  // group for legends above the plot
  const topLegendGroup = chartSvg.append("g")
    .attr("transform","translate(52,0)");

  const gl = chartSvg.append("g")
    .attr("transform","translate(52,40)");

  const chartWidth = chartContainer.clientWidth;  // actual width in 50/50 cell
  const lw = chartWidth - 52 - 26;
  const lh = bottomH - 80;   // space for legends + title

  // X scale is fixed over all years
  const x = d3.scalePoint()
    .domain(d3.range(YEARS.length))
    .range([0, lw]);

  // Y scale will adapt based on selection/metric
  const y = d3.scaleLinear().range([lh,0]);

  const xAxisG = gl.append("g")
    .attr("class","x-axis")
    .attr("transform",`translate(0,${lh})`)
    .call(
      d3.axisBottom(x)
        .tickValues(
          d3.range(YEARS.length)
            .filter(i => i % Math.ceil(YEARS.length/10) === 0)
        )
        .tickFormat(i => YEARS[i])
    );

  xAxisG.selectAll("text")
    .style("font","10px sans-serif")
    .attr("transform","rotate(-35)")
    .style("text-anchor","end");

  const yAxisG = gl.append("g")
    .attr("class","y-axis");

  const lineGen = d3.line()
    .defined(v=>v!=null)
    .x((d,i)=>x(i))
    .y(v=>y(v));

  const lineTitle = chartSvg.append("text")
    .attr("x",52)
    .attr("y",25)
    .style("font","600 12px sans-serif")
    .attr("fill","#94a3b8")
    .text("Select one or more countries…");

  // ------------------ Y-domain logic (full time series) ------------------
  function computeYMaxForSelection(){
    const relevant = selectedIso.size
      ? REC.filter(r => selectedIso.has(r.iso3))
      : REC;

    const vals = [];
    for (const r of relevant) {
      for (const v of r.values) {
        if (v != null && !isNaN(v)) vals.push(v);
      }
    }
    return d3.max(vals) || 1;
  }

  function updateYScale(){
    const maxY = computeYMaxForSelection();
    y.domain([0, maxY]).nice();

    yAxisG
      .call(d3.axisLeft(y).ticks(6, ".2s"))
      .selectAll("text")
      .style("font","10px sans-serif");
  }

// ======================================================================
// LEGENDS INSIDE SLIDER ROW (on the right)
// ======================================================================

function drawTopLegends() {

  // Clear previous legends
  d3.select("#mid-mode-legend").html("");

  // ===========================================================
  // COLOR SCALE LEGEND  (moved above the linechart)
  // ===========================================================
  const scaleWrap = d3.select("#mid-mode-legend")
    .append("div")
    .style("display", "flex")
    .style("align-items", "center")
    .style("gap", "10px");

  const scaleSvg = scaleWrap.append("svg")
    .attr("width", 160)
    .attr("height", 28);

  const defs = scaleSvg.append("defs");
  const grad = defs.append("linearGradient")
    .attr("id", "legend-gradient")
    .attr("x1", "0%").attr("x2", "100%")
    .attr("y1", "0%").attr("y2", "0%");

  for (let i = 0; i <= 10; i++) {
    let s = i / 10;
    grad.append("stop")
      .attr("offset", (s * 100) + "%")
      .attr("stop-color", col(s * maxVal));
  }

  // Scale: text
  scaleSvg.append("text")
    .attr("x", 0).attr("y", 10)
    .style("font", "10px sans-serif")
    .style("fill", "#94a3b8")
    .text("Scale:");

  // gradient bar
  scaleSvg.append("rect")
    .attr("x", 32).attr("y", 4)
    .attr("width", 120).attr("height", 10)
    .style("fill", "url(#legend-gradient)");

  // min + max value text
  scaleSvg.append("text")
    .attr("x", 32).attr("y", 22)
    .style("font", "10px sans-serif")
    .style("fill", "#94a3b8")
    .text("0");

  scaleSvg.append("text")
    .attr("x", 152).attr("y", 22)
    .attr("text-anchor", "end")
    .style("font", "10px sans-serif")
    .style("fill", "#94a3b8")
    .text(d3.format(".2s")(maxVal));

  // ===========================================================
  // MODE LEGEND (Cars / Vans / Buses / Trucks)
  // ===========================================================
  const modeLegend = d3.select("#mid-mode-legend")
    .append("div")
    .style("display", "flex")
    .style("gap", "14px")
    .style("align-items", "center");

  Object.entries(modeColor).forEach(([mode, color]) => {
    const item = modeLegend.append("div")
      .style("display", "flex")
      .style("align-items", "center")
      .style("gap", "6px");

    item.append("div")
      .style("width", "12px")
      .style("height", "12px")
      .style("background", color)
      .style("border-radius", "3px");

    item.append("span")
      .style("font", "11px sans-serif")
      .style("color", "#94a3b8")
      .text(mode);
  });
}


  // ======================================================================
  // SELECTION PANEL TABLE
  // ======================================================================
  const selHead = document.createElement("div");
  selHead.textContent = "Selection — 0 rows";
  selHead.style.cssText = `
    font:600 13px system-ui;color:#111827;margin:2px 0 8px 0;
  `;
  panelContainer.appendChild(selHead);

  const btnClear = document.createElement("button");
  btnClear.textContent = "Clear selection";
  btnClear.style.cssText = `
    font:12px system-ui;padding:8px 12px;border:1px solid #cbd5e1;
    border-radius:10px;background:#fff;color:#111827;margin-bottom:10px;
  `;
  panelContainer.appendChild(btnClear);

  const selBox = document.createElement("div");
  selBox.style.cssText = `
    overflow:auto;
    max-height:100%;
    border:1px solid #e2e8f0;
    border-radius:12px;
    background:#fff;
    box-shadow:0 1px 2px rgba(0,0,0,.04);
    max-width:100%;
  `;

  panelContainer.appendChild(selBox);

  function renderSelPanel(records){
    selHead.textContent = `Selection — ${records.length} rows`;
    selBox.innerHTML = "";

    const wrap = document.createElement("div");
    wrap.style.overflow = "visible";       /* no scroll */
    wrap.style.maxWidth = "100%";
    selBox.appendChild(wrap);

    if (!records.length){
      const empty = document.createElement("div");
      empty.textContent = "Click one or more countries on the map.";
      empty.style.cssText = "padding:12px;font:12px system-ui;color:#475569";
      wrap.appendChild(empty);
      return;
    }

    const nf = new Intl.NumberFormat(undefined,{maximumFractionDigits:1});

    const tbl = document.createElement("table");
    tbl.style.cssText = `
      border-collapse:separate;border-spacing:0;
      width:100%;min-width:220px;
    `;
    wrap.appendChild(tbl);

    const thead = tbl.createTHead();
    const hr = thead.insertRow();
    hr.style.cssText = `
      position:sticky;top:0;background:#f8fafc;
      box-shadow:inset 0 -1px 0 #e2e8f0;
    `;

    ["Country", metricName].forEach((c,i)=>{
      const th = document.createElement("th");
      th.textContent = c;
      th.style.cssText = `
        padding:10px 12px;
        text-align:${i===0?"left":"right"};
        font:600 12px system-ui;color:#0f172a;
      `;
      hr.appendChild(th);
    });

    const tb = tbl.createTBody();
    records.forEach((r,i)=>{
      const tr = tb.insertRow();
      tr.style.background = i%2?"#f9fafb":"#ffffff";
      tr.onmouseenter = ()=> tr.style.background="#eef2ff";
      tr.onmouseleave = ()=> tr.style.background=i%2?"#f9fafb":"#ffffff";

      const tdName = tr.insertCell();
      tdName.textContent = r.Country;
      tdName.style.cssText = `
        padding:10px 12px;text-align:left;
        font:600 12px system-ui;color:#0f172a;
        border-bottom:1px solid #eef2f7;
        max-width:150px;overflow:hidden;text-overflow:ellipsis;
      `;

      const tdVal = tr.insertCell();
      tdVal.textContent = (r.Value==null ? "—" : nf.format(r.Value));
      tdVal.style.cssText = `
        padding:10px 12px;text-align:right;
        font:12px system-ui;color:#0f172a;
        border-bottom:1px solid #eef2f7;
        width:70px;
      `;
    });
  }

  // ======================================================================
  // LINES (mode colored)
  // ======================================================================
  function redrawLines(){
    gl.selectAll("path.countryline").remove();

    if (!selectedIso.size){
      lineTitle.text("Select one or more countries…");
      return;
    }

    lineTitle.text("Selected countries");

    gl.selectAll("path.countryline")
      .data(REC.filter(r=>selectedIso.has(r.iso3)), d=>d.iso3)
      .join(
        enter =>
          enter.append("path")
            .attr("class","countryline")
            .attr("fill","none")
            .attr("stroke", d => modeColor[getMode(d.name)] || "#60a5fa")
            .attr("stroke-width",1.8)
            .attr("opacity",0.9)
            .attr("d", d => lineGen(d.values)),

        update =>
          update.attr("stroke", d => modeColor[getMode(d.name)] || "#60a5fa")
                .attr("d", d => lineGen(d.values)),

        exit => exit.remove()
      );
  }

  // ======================================================================
  // SELECTION HANDLING
  // ======================================================================
  function selectCountry(iso3){
    const rec = REC.find(r=>r.iso3===iso3);
    if (!rec) return;

    if (selectedIso.has(iso3)) selectedIso.delete(iso3);
    else selectedIso.add(iso3);

    countries
      .attr("stroke-width", f=>selectedIso.has(isoKey(f))?1.5:0.25)
      .attr("stroke",      f=>selectedIso.has(isoKey(f))?"#e5e7eb":"#111");

    const rows = REC.filter(r=>selectedIso.has(r.iso3))
      .map(r => ({Country:r.name, Value:r.values[idx]}));

    model.set("selection",{iso3s:[...selectedIso], year:YEARS[idx], rows});
    model.save_changes();

    // Update Y-scale based on new selection, then lines & table
    updateYScale();
    redrawLines();
    renderSelPanel(rows);
  }

  btnClear.onclick = () => {
    selectedIso.clear();
    countries.attr("stroke-width",0.25).attr("stroke","#111");
    model.set("selection",{});
    model.save_changes();

    updateYScale();
    redrawLines();
    renderSelPanel([]);
  };

  // ======================================================================
  // RECOLOR ON SLIDER MOVE (Y-axis DO NOT change here)
  // ======================================================================
  function recolorOnSlider(){
    maxVal = computeMaxValForYear();
    col.domain([0,maxVal]);

    countries.attr("fill", f => {
      const v = valueAt(isoKey(f), idx);
      return v==null ? "#374151" : col(v);
    });

    yearLbl.text(YEARS[idx]);

    // update table values for current year
    if (selectedIso.size){
      const rows = REC.filter(r=>selectedIso.has(r.iso3))
        .map(r=>({Country:r.name,Value:r.values[idx]}));
      renderSelPanel(rows);
    }

    drawTopLegends();
  }

  slider.on("input", ev=>{
    idx = +ev.target.value;
    recolorOnSlider();
  });

  // ======================================================================
  // METRIC SWITCHING (Python side)
  // ======================================================================
  model.on("change:options", ()=>{
    const newMetric = model.get("options")?.metric;
    if (!newMetric || newMetric === metricName) return;

    metricName = newMetric;

    // get updated REC from Python
    data = model.get("data");
    REC  = data.records;

    selectedIso.clear();
    model.set("selection",{});
    model.save_changes();

    // Y-scale should adapt (based on all countries now)
    updateYScale();
    redrawLines();
    renderSelPanel([]);

    // also recolor map & color scale legend for current year
    recolorOnSlider();
  });

  // ------------------ Initial draw ------------------
  updateYScale();
  drawTopLegends();
  recolorOnSlider();
  renderSelPanel([]);
}
