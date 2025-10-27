// Isea/assets/worldrenewable.js — layout: map on top, chart + panel below
export async function render({ model, el }) {
  const mod = await import('https://cdn.jsdelivr.net/npm/d3@7/+esm');
  const d3 = mod.default ?? mod;

  const data = model.get("data");
  const opts = model.get("options");

  const YEARS = data.years;
  const REC = data.records;
  const world = data.world;
  const TECHS = ["Fossil", "Solar", "Wind", "Hydro", "Bio"];

  let idx = opts.idx_now;
  const totalW = opts.width;
  const totalH = opts.height * 1.2;

  // --- layout proportions
  const mapH = Math.floor(totalH * 0.65);
  const bottomH = totalH - mapH - 30;
  const panelW = 800;
  const gap = 50;
  const chartW = totalW - panelW - gap;

  el.innerHTML = "";

  // --- master grid: map (top), bottom split (chart + panel)
  const wrapper = document.createElement("div");
  wrapper.style.cssText = `
    display:grid;
    grid-template-rows:${mapH}px ${bottomH}px;
    gap:${gap}px;
    width:100%;
    max-width:${totalW}px;
    box-sizing:border-box;
    overflow-x:auto;
    color:#e5e7eb;
  `;
  el.appendChild(wrapper);

  const mapContainer = document.createElement("div");
  const bottom = document.createElement("div");
  bottom.style.cssText = `
    display:grid;
    grid-template-columns:${chartW}px ${panelW}px;
    gap:${gap}px;
    min-width:${chartW + panelW + gap}px;
    overflow-x:auto;
  `;
  wrapper.appendChild(mapContainer);
  wrapper.appendChild(bottom);

  const chartContainer = document.createElement("div");
  const panelContainer = document.createElement("div");
  bottom.appendChild(chartContainer);
  bottom.appendChild(panelContainer);

  const root = d3.select(mapContainer);

  // ---- panel
  const selHead = document.createElement("div");
  selHead.textContent = "point selection — 0 points";
  selHead.style.cssText = "font:600 13px system-ui,Segoe UI,Arial;color:#111827;margin:2px 0 8px 0";
  panelContainer.appendChild(selHead);

  const btnClear = document.createElement("button");
  btnClear.textContent = "Limpiar selección";
  btnClear.style.cssText = "font:12px system-ui;padding:8px 12px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#111827;margin:0 0 10px 0;cursor:pointer";
  panelContainer.appendChild(btnClear);

  const selBox = document.createElement("div");
  selBox.style.cssText = `
    max-height:${bottomH - 60}px;
    overflow:auto;
    border:1px solid #e2e8f0;
    border-radius:12px;
    background:#ffffff;
    box-shadow:0 1px 2px rgba(0,0,0,.04);
  `;
  panelContainer.appendChild(selBox);

  function renderSelPanel(rows) {
    selHead.textContent = `point selection — ${rows.length} points`;
    selBox.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.style.overflow = "auto";
    wrap.style.maxWidth = "100%";
    selBox.appendChild(wrap);

    if (!rows.length) {
      const empty = document.createElement("div");
      empty.textContent = "Haz clic en uno o más países en el mapa.";
      empty.style.cssText = "padding:12px 14px;font:12px system-ui;color:#475569";
      wrap.appendChild(empty);
      return;
    }

    const cols = ["Country", ...TECHS];
    const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
    const tbl = document.createElement("table");
    tbl.style.borderCollapse = "separate";
    tbl.style.borderSpacing = "0";
    tbl.style.width = "100%";
    tbl.style.minWidth = `${160 + (cols.length - 1) * 100}px`;
    wrap.appendChild(tbl);

    const thead = tbl.createTHead();
    const hr = thead.insertRow();
    hr.style.position = "sticky";
    hr.style.top = "0";
    hr.style.background = "#f8fafc";
    hr.style.boxShadow = "inset 0 -1px 0 #e2e8f0";

    cols.forEach((c, i) => {
      const th = document.createElement("th");
      th.textContent = c;
      th.style.padding = "10px 12px";
      th.style.textAlign = i === 0 ? "left" : "right";
      th.style.font = "600 12px system-ui";
      th.style.color = "#0f172a";
      if (i === 0) th.style.borderTopLeftRadius = "12px";
      if (i === cols.length - 1) th.style.borderTopRightRadius = "12px";
      hr.appendChild(th);
    });

    const tb = tbl.createTBody();
    rows.forEach((r, idx) => {
      const tr = tb.insertRow();
      tr.style.background = idx % 2 ? "#f9fafb" : "#ffffff";
      tr.addEventListener("mouseenter", () => (tr.style.background = "#eef2ff"));
      tr.addEventListener("mouseleave", () => (tr.style.background = idx % 2 ? "#f9fafb" : "#ffffff"));
      cols.forEach((c, i) => {
        const td = tr.insertCell();
        const v = r[c];
        const isNum = i > 0 && Number.isFinite(+v);
        td.textContent = isNum ? nf.format(+v) : (v ?? "—");
        td.style.padding = "10px 12px";
        td.style.textAlign = i === 0 ? "left" : "right";
        td.style.font = "12px system-ui";
        td.style.color = "#0f172a";
        td.style.borderBottom = "1px solid #eef2f7";
        if (i === 0) td.style.fontWeight = "600";
      });
    });
  }

  // ---- headers + controls
  const hdr = root.append("div")
    .style("font", "600 16px/1.3 sans-serif")
    .style("color", "#e5e7eb")
    .style("margin", "0 0 6px 6px")
    .text("Participación de renovables en la capacidad instalada por país");

  const desc = root.append("div")
    .style("font", "12px/1.35 sans-serif")
    .style("color", "#94a3b8")
    .style("margin", "0 0 8px 6px")
    .text("Coropleta (0–100%). Desliza el año. Haz clic en países para ver datos.");

  const controls = root.append("div")
    .style("display", "flex")
    .style("gap", "12px")
    .style("align-items", "center")
    .style("margin", "6px 0 10px 6px");

  controls.append("span").style("color", "#cbd5e1").style("font", "12px sans-serif").text("Año:");
  const slider = controls.append("input").attr("type", "range")
    .attr("min", 0).attr("max", YEARS.length - 1).attr("value", idx).style("width", "340px");
  const yearLbl = controls.append("span").style("color", "#e5e7eb").style("font", "12px sans-serif").text(YEARS[idx]);

  // ---- map
  const svg = root.append("svg").attr("width", totalW).attr("height", mapH);
  const g = svg.append("g").attr("transform", `translate(20,40)`);

  const proj = d3.geoNaturalEarth1().fitExtent([[0, 0], [totalW - 40, mapH - 80]], world);
  const path = d3.geoPath(proj);

  const fmtPct = d3.format(".0%");
  const col = d3.scaleSequential(d3.interpolateYlGn).domain([0, 1]);

  const isoKey = f =>
    f.properties?.ISO_A3 ||
    f.properties?.ADM0_A3 ||
    f.properties?.ISO3 ||
    f.properties?.iso_a3 ||
    f.properties?.iso_a3_eh ||
    f.id;

  function valueAt(iso3, idxYear) {
    const rec = REC.find(d => d.iso3 === iso3);
    if (!rec) return null;
    const v = rec.shares[idxYear];
    return (v == null || Number.isNaN(v)) ? null : v;
  }

  const tip = document.createElement("div");
  Object.assign(tip.style, {
    position: "fixed", zIndex: 9999, pointerEvents: "none",
    background: "rgba(17,24,39,.95)", color: "#fff", padding: "8px 10px",
    borderRadius: "8px", font: "12px/1.35 sans-serif",
    boxShadow: "0 8px 24px rgba(0,0,0,.35)", opacity: 0, transition: "opacity .12s"
  });
  document.body.appendChild(tip);

  function showTip(ev, name, v) {
    let txt = `<div style="font-weight:700;margin-bottom:4px">${name}</div>`;
    if (v == null) txt += `<div>Sin dato</div>`;
    else txt += `<div>Renovable: <strong>${fmtPct(v)}</strong></div>`;
    tip.innerHTML = txt;
    tip.style.opacity = 1;
    tip.style.left = (ev.clientX + 12) + "px";
    tip.style.top = (ev.clientY + 12) + "px";
  }
  function hideTip() { tip.style.opacity = 0; }

  let selectedIso = new Set();

  const countries = g.selectAll("path.country")
    .data(world.features)
    .join("path")
    .attr("class", "country")
    .attr("d", path)
    .attr("fill", f => {
      const iso = isoKey(f);
      const v = valueAt(iso, idx);
      return (v == null) ? "#374151" : col(v);
    })
    .attr("stroke", "#111")
    .attr("stroke-width", 0.25)
    .on("mousemove", (ev, f) => {
      const iso = isoKey(f);
      const rec = REC.find(d => d.iso3 === iso);
      const name = rec?.name || (f.properties?.NAME || "");
      const v = valueAt(iso, idx);
      showTip(ev, name, v);
    })
    .on("mouseleave", hideTip)
    .on("click", (ev, f) => selectCountry(isoKey(f)));

  // ---- line chart
  const chart = d3.select(chartContainer);
  const svgLine = chart.append("svg").attr("width", chartW).attr("height", bottomH);
  const gl = svgLine.append("g").attr("transform", `translate(52,14)`);
  const lw = chartW - 52 - 26;
  const lh = bottomH - 40;

  const x = d3.scalePoint().domain(d3.range(YEARS.length)).range([0, lw]);
  const y = d3.scaleLinear().domain([0, 1]).range([lh, 0]).nice();
  const line = d3.line().defined(v => v != null).x((d, i) => x(i)).y(d => y(d));

  gl.append("g")
    .attr("transform", `translate(0,${lh})`)
    .call(
      d3.axisBottom(x)
        .tickValues(d3.range(YEARS.length).filter(i => i % Math.ceil(YEARS.length / 10) === 0))
        .tickFormat(i => YEARS[i])
    )
    .selectAll("text")
    .style("font", "10px sans-serif")
    .attr("transform", "rotate(-35)")
    .style("text-anchor", "end");

  gl.append("g")
    .call(d3.axisLeft(y).ticks(6, ".0%"))
    .selectAll("text")
    .style("font", "10px sans-serif");

  const lineTitle = svgLine.append("text")
    .attr("x", 52).attr("y", 12)
    .style("font", "600 12px sans-serif")
    .attr("fill", "#e5e7eb")
    .text("Selecciona uno o más países…");

  // ---- selection logic
  function selectCountry(iso3) {
    const rec = REC.find(d => d.iso3 === iso3);
    if (!rec) return;
    if (selectedIso.has(iso3)) selectedIso.delete(iso3);
    else selectedIso.add(iso3);

    countries
      .attr("stroke-width", d => (selectedIso.has(isoKey(d)) ? 1.2 : 0.25))
      .attr("stroke", d => (selectedIso.has(isoKey(d)) ? "#fff" : "#111"));

    const rows = REC.filter(d => selectedIso.has(d.iso3)).map(rec => ({
      Country: rec.name, Year: YEARS[idx],
      Fossil: rec.Fossil[idx], Solar: rec.Solar[idx],
      Wind: rec.Wind[idx], Hydro: rec.Hydro[idx], Bio: rec.Bio[idx]
    }));
    model.set("selection", { type: "country", iso3s: [...selectedIso], year: YEARS[idx], rows });
    model.save_changes();
    renderSelPanel(rows);

    gl.selectAll("path.countryline")
      .data(REC.filter(d => selectedIso.has(d.iso3)), d => d.iso3)
      .join(
        enter => enter.append("path")
          .attr("class", "countryline")
          .attr("fill", "none")
          .attr("stroke", "#60a5fa")
          .attr("stroke-width", 1.8)
          .attr("opacity", 0.9)
          .attr("d", d => line(d.shares)),
        update => update.attr("d", d => line(d.shares)),
        exit => exit.remove()
      );

    lineTitle.text(selectedIso.size ? "Países seleccionados" : "Selecciona uno o más países…");
  }

  btnClear.onclick = () => {
    selectedIso.clear();
    countries.attr("stroke-width", 0.25).attr("stroke", "#111");
    gl.selectAll("path.countryline").remove();
    lineTitle.text("Selecciona uno o más países…");
    model.set("selection", {});
    model.save_changes();
    renderSelPanel([]);
  };

  function recolor() {
    countries.attr("fill", f => {
      const iso = isoKey(f);
      const v = valueAt(iso, idx);
      return (v == null) ? "#374151" : col(v);
    });
    yearLbl.text(YEARS[idx]);
    if (selectedIso.size) {
      const rows = REC.filter(d => selectedIso.has(d.iso3)).map(rec => ({
        Country: rec.name, Year: YEARS[idx],
        Fossil: rec.Fossil[idx], Solar: rec.Solar[idx],
        Wind: rec.Wind[idx], Hydro: rec.Hydro[idx], Bio: rec.Bio[idx]
      }));
      model.set("selection", { type: "country", iso3s: [...selectedIso], year: YEARS[idx], rows });
      model.save_changes();
      renderSelPanel(rows);
    }
  }

  slider.on("input", ev => { idx = +ev.target.value; recolor(); });

  recolor();
  renderSelPanel([]);
}
