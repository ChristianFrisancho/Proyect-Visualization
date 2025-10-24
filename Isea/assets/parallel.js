// Isea/assets/parallel.js
// anywidget ESM module
export function render({ model, el }) {
  const h = (t, p = {}, parent) => {
    const n = document.createElement(t);
    Object.assign(n, p);
    if (parent) parent.appendChild(n);
    return n;
  };

  async function draw() {
    el.innerHTML = "";

    const pack = model.get("data") ?? {};
    const opts = model.get("options") ?? {};
    const YEARS = pack.years || [];
    const R = pack.records || [];
    let DIMS = (pack.dims || []).slice();

    if (!YEARS.length || !R.length || !DIMS.length) {
      el.textContent = "Sin datos.";
      return;
    }

    // load d3
    const mod = await import("https://cdn.jsdelivr.net/npm/d3@7/+esm");
    const d3 = mod.default ?? mod;

    // ---- options ----
    const totalW = +(opts.width ?? 1150);   // ancho total del componente
    const H = +(opts.height ?? 600);
    const useLog = !!opts.log_axes;
    const normalize = !!opts.normalize;
    const allowReorder = !!opts.reorder;
    let idxYear = YEARS.indexOf(opts.year_start ?? YEARS[YEARS.length - 1]);
    if (idxYear < 0) idxYear = YEARS.length - 1;

    // Margins (configurables)
    const mo = opts.margin || {};
    const m = {
      top: mo.top ?? mo.t ?? 105,
      right: mo.right ?? mo.r ?? 220,
      bottom: mo.bottom ?? mo.b ?? 40,
      left: mo.left ?? mo.l ?? 60,
    };

    // Panel settings
    const panelPos = (opts.panel_position || "right"); // "right" | "bottom"
    const panelW = +(opts.panel_width ?? 340);
    const panelH = +(opts.panel_height ?? 260);
    const gridGap = 12; // gap entre columnas/filas

    // Ancho efectivo de la gráfica cuando el panel está a la derecha
    let W = totalW;
    if (panelPos === "right") {
      W = Math.max(360, totalW - panelW - gridGap);
    }

    const iW = W - m.left - m.right;
    const iH = H - m.top - m.bottom;

    // ---- layout (grid) ----
    const wrap = h("div", {}, el);
    if (panelPos === "right") {
      wrap.style.cssText =
        `display:grid;grid-template-columns:${W}px ${panelW}px;gap:${gridGap}px;align-items:start;`;
    } else {
      wrap.style.cssText =
        `display:grid;grid-template-rows:auto ${panelH}px;gap:10px;align-items:start;`;
    }
    const left = h("div", {}, wrap);
    const right = h("div", {}, wrap);
    if (panelPos === "bottom") right.style.gridColumn = "1 / -1";

    // ---- header + controls ----
    const status = h("div", {}, left);
    status.style.cssText =
      "font:12px/1.35 system-ui,Segoe UI,Arial;color:#111827;margin:0 0 6px 0";

    const title = h("div", {}, left);
    title.style.cssText =
      "margin:0 0 6px 0;font:700 20px/1.25 system-ui,Segoe UI,Arial;color:#111827";

    const hint = h(
      "div",
      {
        innerHTML:
          "Arrastra el <b>NOMBRE</b> del eje para reordenar (las líneas se mueven mientras arrastras). Brush para filtrar. Click en una línea para (de)seleccionar. Exporta la selección a CSV.",
      },
      left
    );
    hint.style.cssText =
      "margin:0 0 8px 0;font:13px/1.4 system-ui,Segoe UI,Arial;color:#334155";

    const ctrls = h("div", {}, left);
    ctrls.style.cssText =
      "display:flex;gap:12px;align-items:center;margin:6px 0 8px 0";
    const lblA = h("span", { textContent: "Año:" }, ctrls);
    lblA.style.cssText = "color:#111827;font:13px system-ui";
    const slider = h("input", {}, ctrls);
    slider.type = "range";
    slider.min = "0";
    slider.max = String(YEARS.length - 1);
    slider.value = String(idxYear);
    slider.style.width = "320px";
    const yearLbl = h("span", { textContent: YEARS[idxYear] }, ctrls);
    yearLbl.style.cssText = "color:#111827;font:13px system-ui";
    const btn = h("button", { textContent: "Export selección CSV" }, ctrls);
    btn.style.cssText =
      "font:12px system-ui;padding:8px 12px;border:1px solid #1f2937;border-radius:10px;color:#e5e7eb;background:#1f2937";

    // ---- svg root ----
    const svg = d3.select(left).append("svg").attr("width", W).attr("height", H);
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const layer = g.append("g").attr("fill", "none");
    const hit = g.append("g").attr("fill", "none");

    // ---- panel selección ----
    const selHead = h("div", { textContent: "point selection — 0 points" }, right);
    selHead.style.cssText =
      "font:600 13px system-ui,Segoe UI,Arial;color:#111827;margin:2px 0 8px 0";

    const btnClear = h("button", { textContent: "Limpiar selección" }, right);
    btnClear.style.cssText =
      "font:12px system-ui;padding:6px 8px;border:1px solid #334155;border-radius:8px;background:#fff;color:#111827;margin:0 0 10px 0;cursor:pointer";

    const selBox = h("div", {}, right);
    selBox.style.cssText =
      `max-height:${panelH}px;overflow:auto;border:1px solid #e5e7eb;border-radius:10px;padding:8px;font:12px system-ui,Arial;color:#111827;background:#fff`;

    // ---- colors ----
    const color = d3.scaleOrdinal(
      ["Fossil", "Hydro", "Wind", "Solar", "Bio"],
      ["#60a5fa", "#f59e0b", "#ef4444", "#2dd4bf", "#9b59b6"]
    );

    // ---- data helpers ----
    function datasetFor(i) {
      return R.map((r) => {
        const o = { Country: r.label, Year: YEARS[i] };
        let best = DIMS[0], bestV = +r[DIMS[0]][i] || 0;
        for (const k of DIMS) {
          const v = +r[k][i] || 0;
          o[k] = v;
          if (v > bestV) { bestV = v; best = k; }
        }
        o.DominantTech = best;
        return o;
      });
    }
    function normalizeByDim(data) {
      const ext = {};
      for (const k of DIMS) {
        const vals = data.map((d) => +d[k]).filter(Number.isFinite);
        const mn = d3.min(vals), mx = d3.max(vals);
        ext[k] = mx > mn ? [mn, mx] : [0, 1];
      }
      return data.map((d) => {
        const o = { Country: d.Country, Year: d.Year, DominantTech: d.DominantTech };
        for (const k of DIMS) {
          const [mn, mx] = ext[k], v = +d[k] || 0;
          o[k] = mx > mn ? (v - mn) / (mx - mn) : 0;
        }
        return o;
      });
    }

    let DATA = datasetFor(idxYear);
    if (normalize) DATA = normalizeByDim(DATA);

    title.textContent = `Capacidad instalada por país — ${YEARS[idxYear]}`;

    // ---- scales ----
    const x = d3.scalePoint().domain(DIMS).range([0, iW]).padding(0.5);
    const y = {};
    function buildY() {
      for (const k of DIMS) {
        const vals = DATA.map((d) => +d[k]).filter((v) => Number.isFinite(v) && (!useLog || v > 0));
        y[k] = (useLog ? d3.scaleLog() : d3.scaleLinear())
          .domain(useLog ? [Math.max(1e-6, d3.min(vals)), d3.max(vals)] : d3.extent(vals))
          .nice()
          .range([iH, 0]);
      }
    }
    buildY();

    // ---- drag + path ----
    const dragging = {};
    const position = (d) => (dragging[d] != null ? dragging[d] : x(d));
    const line = d3.line().defined(([, v]) => Number.isFinite(v));
    const pathFor = (d) => line(DIMS.map((k) => [position(k), y[k](+d[k])]));

    // ---- tooltip ----
    const tip = document.createElement("div");
    Object.assign(tip.style, {
      position: "fixed",
      zIndex: 9999,
      pointerEvents: "none",
      background: "rgba(17,24,39,.95)",
      color: "#fff",
      padding: "10px 12px",
      borderRadius: "10px",
      font: "12px/1.35 sans-serif",
      boxShadow: "0 8px 24px rgba(0,0,0,.35)",
      opacity: 0,
      transition: "opacity .12s",
    });
    document.body.appendChild(tip);
    const fmt = d3.format(",.0f");
    const tipHTML = (d) =>
      `<div style="font-weight:700;margin-bottom:6px">${d.Country}</div>` +
      DIMS.map((k) => `<div>${k}: <strong>${fmt(+d[k] || 0)}</strong>${normalize ? "" : " MW"}</div>`).join("");
    const showTip = (ev, d) => { tip.innerHTML = tipHTML(d); tip.style.opacity = 1; tip.style.left = ev.clientX + 14 + "px"; tip.style.top = ev.clientY + 14 + "px"; };
    const hideTip = () => (tip.style.opacity = 0);

    // ---- selection state ----
    let selected = new Set();

    function renderSelPanel(rows) {
      selHead.textContent = `point selection — ${rows.length} points`;
      selBox.innerHTML = "";
      if (!rows.length) { selBox.textContent = "Sin selección."; return; }
      const cols = ["Country", ...DIMS];
      const tbl = document.createElement("table");
      tbl.style.borderCollapse = "collapse"; tbl.style.width = "100%";
      const thead = tbl.createTHead(); const hr = thead.insertRow();
      cols.forEach((c) => {
        const th = document.createElement("th");
        th.textContent = c;
        th.style.textAlign = "left"; th.style.padding = "4px 6px";
        th.style.borderBottom = "1px solid #e5e7eb"; th.style.position = "sticky";
        th.style.top = "0"; th.style.background = "#fff"; th.style.fontWeight = "600";
        hr.appendChild(th);
      });
      const tb = tbl.createTBody();
      rows.forEach((r) => {
        const tr = tb.insertRow();
        cols.forEach((c) => {
          const td = tr.insertCell();
          td.textContent = r[c] ?? 0;
          td.style.padding = "4px 6px"; td.style.borderBottom = "1px solid #f1f5f9";
        });
      });
      selBox.appendChild(tbl);
    }

    function pushSelection(type = "line") {
      const keys = [...selected];
      const rows = DATA.filter((d) => keys.includes(d.Country));
      model.set("selection", { type, keys, rows });
      model.save_changes();
      renderSelPanel(rows);
    }

    function applySelectionStyles() {
      if (selected.size === 0) {
        vis.attr("stroke-opacity", 0.85).attr("stroke-width", 1.2);
      } else {
        vis.attr("stroke-opacity", (d) => (selected.has(d.Country) ? 1 : 0.08))
           .attr("stroke-width", (d) => (selected.has(d.Country) ? 2.6 : 0.7));
      }
      status.textContent = `Año: ${YEARS[idxYear]} · Seleccionados: ${selected.size} / ${DATA.length}`;
    }

    function toggleSelect(_, d) {
      if (selected.has(d.Country)) selected.delete(d.Country);
      else selected.add(d.Country);
      applySelectionStyles();
      pushSelection("line");
    }

    btnClear.onclick = () => { selected = new Set(); applySelectionStyles(); pushSelection("line"); };

    // ---- draw paths ----
    let vis = layer.selectAll("path").data(DATA, (d) => d.Country).join("path")
      .attr("d", pathFor).attr("stroke", (d) => color(d.DominantTech || "Solar"))
      .attr("stroke-opacity", 0.85).attr("stroke-width", 1.2).style("pointer-events", "none");

    let hits = hit.selectAll("path").data(DATA, (d) => d.Country).join("path")
      .attr("d", pathFor).attr("stroke", "transparent").attr("stroke-width", 12)
      .style("cursor", "pointer").on("mousemove", showTip).on("mouseleave", hideTip).on("click", toggleSelect);

    // ---- axes + brushes + drag ----
    let axis = null;
    const bw = Math.min(36, Math.max(24, (iW / DIMS.length) * 0.5));
    const filters = {};

    function visibleRows() {
      const keys = Object.keys(filters);
      return DATA.filter((d) => {
        for (const k of keys) { const v = +d[k] || 0; const [a, b] = filters[k]; if (v < a || v > b) return false; }
        return true;
      });
    }

    function brushed(event) {
      g.selectAll(".brush").each(function (dim) {
        const s = d3.brushSelection(this);
        if (s) {
          const y0 = y[dim].invert(s[1]); const y1 = y[dim].invert(s[0]);
          filters[dim] = [Math.min(y0, y1), Math.max(y0, y1)];
        } else delete filters[dim];
      });

      const keys = Object.keys(filters);
      const disp = (d) => {
        for (const k of keys) { const v = +d[k] || 0; const [a, b] = filters[k]; if (v < a || v > b) return "none"; }
        return null;
      };
      vis.style("display", disp); hits.style("display", disp);

      const visible = visibleRows().length;
      status.textContent = `Año: ${YEARS[idxYear]} · Filtrado: ${visible} / ${DATA.length} · Seleccionados: ${selected.size}`;

      if (event && event.type === "end") {
        const rows = visibleRows();
        model.set("selection", { type: "brush", keys: rows.map((r) => r.Country), rows });
        model.save_changes();
        renderSelPanel(rows);
      }
    }

    function renderAxes() {
      axis = g.selectAll(".axis").data(DIMS, (d) => d).join(
        (enter) => {
          const a = enter.append("g").attr("class", "axis");
          a.append("text").attr("class", "axis-title").attr("y", -10).attr("text-anchor", "middle")
           .style("font", "12px system-ui").style("fill", "#111827");
          return a;
        },
        (update) => update,
        (exit) => exit.remove()
      );

      axis.attr("transform", (d) => `translate(${position(d)},0)`)
        .each(function (d) {
          const A = d3.select(this);
          A.selectAll("g.tick").remove();
          A.call(d3.axisLeft(y[d]).ticks(6, useLog ? "~g" : undefined));
          A.select("text.axis-title").text((d) => d).style("fill", "#111827");
          A.selectAll("text").style("fill", "#111827").style("font", "12px system-ui");
          A.selectAll("line,path").style("stroke", "#111827").style("stroke-width", "1.1");
        });

      axis.selectAll(".brush").remove();
      axis.append("g").attr("class", "brush").attr("transform", `translate(${-bw / 2},0)`)
        .each(function (dim) {
          d3.select(this).call(
            d3.brushY().extent([[0, 0], [bw, iH]]).on("brush end", brushed)
          );
        });

      if (allowReorder) {
        const drag = d3.drag()
          .on("start", (ev, dim) => { dragging[dim] = position(dim); g.selectAll(".brush").style("pointer-events", "none"); })
          .on("drag", (ev, dim) => {
            dragging[dim] = Math.max(0, Math.min(iW, ev.x));
            axis.attr("transform", (d) => `translate(${position(d)},0)`);
            vis.attr("d", (d) => d3.line()(DIMS.map((k) => [position(k), y[k](+d[k])])));
            hits.attr("d", (d) => d3.line()(DIMS.map((k) => [position(k), y[k](+d[k])])));
          })
          .on("end", (ev, dim) => {
            DIMS.sort((a, b) => position(a) - position(b));
            dragging[dim] = null; delete dragging[dim];
            x.domain(DIMS);
            axis.transition().duration(150).attr("transform", (d) => `translate(${x(d)},0)`);
            vis.transition().duration(150).attr("d", (d) => d3.line()(DIMS.map((k) => [x(k), y[k](+d[k])])));
            hits.transition().duration(150).attr("d", (d) => d3.line()(DIMS.map((k) => [x(k), y[k](+d[k])])));
            g.selectAll(".brush").style("pointer-events", null);
          });
        axis.select("text.axis-title").style("cursor", "grab").call(drag);
      }
    }
    renderAxes();

    // ---- slider year ----
    function updateYear(newIdx) {
      idxYear = newIdx;
      yearLbl.textContent = YEARS[idxYear];
      title.textContent = `Capacidad instalada por país — ${YEARS[idxYear]}`;
      DATA = datasetFor(idxYear);
      if (normalize) DATA = normalizeByDim(DATA);
      buildY();
      renderAxes();
      vis = layer.selectAll("path").data(DATA, (d) => d.Country).join("path")
        .attr("stroke", (d) => color(d.DominantTech || "Solar"))
        .attr("fill", "none").attr("stroke-opacity", 0.85).style("pointer-events", "none")
        .attr("d", (d) => d3.line()(DIMS.map((k) => [x(k), y[k](+d[k])])));

      hits = hit.selectAll("path").data(DATA, (d) => d.Country).join("path")
        .attr("stroke", "transparent").attr("stroke-width", 12).style("cursor", "pointer")
        .on("mousemove", showTip).on("mouseleave", hideTip).on("click", toggleSelect)
        .attr("d", (d) => d3.line()(DIMS.map((k) => [x(k), y[k](+d[k])])));

      applySelectionStyles();
      for (const k in filters) delete filters[k];
      pushSelection("line");
    }
    slider.addEventListener("input", (ev) => updateYear(+ev.target.value));

    // ---- export CSV ----
    btn.addEventListener("click", () => {
      const curSel = model.get("selection") || {};
      const rows = curSel.keys && curSel.keys.length
        ? DATA.filter((d) => curSel.keys.includes(d.Country))
        : visibleRows();
      const header = ["Country", "Year", ...DIMS].join(",");
      const body = rows.map((r) => [r.Country, r.Year, ...DIMS.map((k) => +r[k] || 0)].join(",")).join("\n");
      const csv = header + "\n" + body;
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `parallel_selection_${YEARS[idxYear]}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    });

    // ---- initial paint ----
    applySelectionStyles();
    pushSelection("line");
  }

  model.on("change:data", draw);
  model.on("change:options", draw);
  draw();
}
