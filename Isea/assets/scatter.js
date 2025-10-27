// Isea/assets/scatter.js
export async function render({ model, el }) {
  const mod = await import("https://cdn.jsdelivr.net/npm/d3@7/+esm");
  const d3 = mod.default ?? mod;

  const nowEpoch = () => Date.now();
  const h = (t, p = {}, parent) => { const n = document.createElement(t); Object.assign(n, p); if (parent) parent.appendChild(n); return n; };
  const fmtNum = (v) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(v);
  const toCSV = (rows, columns) => {
    const esc = (s) => String(s ?? "").replace(/"/g, '""');
    const head = columns.map((c) => `"${esc(c)}"`).join(",");
    const body = rows.map((r) => columns.map((c) => `"${esc(r[c])}"`).join(",")).join("\n");
    return [head, body].filter(Boolean).join("\n");
  };

  function draw() {
    el.innerHTML = "";

    const data = model.get("data") || [];
    const o = Object.assign({
      x:"x", y:"y", key:"id", label:null, color:null, size:null,
      logX:false, logY:false,
      width:720, height:420, margin:{t:28,r:24,b:56,l:70},
      colors:["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"],
      colorMap:null, legend:true, legendPosition:"right", legend_width:160, // NEW: legend width reservation
      radius:5, opacity:0.92, grid:true, squareCells:true, xTicks:8, yTicks:8,
      panel_position:"right", panel_width:300, panel_height:220,
      title:null, xLabel:null, yLabel:null
    }, model.get("options") || {});

    const M = o.margin || {};
    const m = Array.isArray(M) ? {t:M[0], r:M[1], b:M[2], l:M[3]} : {
      t:+M.t ?? +M.top ?? 28, r:+M.r ?? +M.right ?? 24, b:+M.b ?? +M.bottom ?? 56, l:+M.l ?? +M.left ?? 70
    };

    const bounds = el.getBoundingClientRect();
    const W0 = (o.width != null ? +o.width : Math.max(1, Math.floor(bounds.width))) || 720;
    const H0 = (o.height != null ? +o.height : 420);

    // ---- Layout: plot + reserved legend + internal panel
    const LBLK = (o.legend && o.legendPosition === "right" && o.panel_position !== "right") ? Math.max(120, +o.legend_width || 160) : 0;

    let plotW = W0 - m.l - m.r - LBLK;        // reserve space for legend when panel is bottom (or not right)
    let plotH = H0 - m.t - m.b;
    let panelBox = null;

    if (o.panel_position === "right") {
      const pw = Math.max(200, +o.panel_width || 300);
      panelBox = { x: W0 - pw - 8, y: m.t, w: pw, h: H0 - m.t - m.b };
      // plot width ends where the panel gap starts
      plotW = Math.max(240, panelBox.x - m.l - 100);
    } else if (o.panel_position === "bottom") {
      const ph = Math.max(160, +o.panel_height || 220);
      panelBox = { x: m.l, y: H0 - ph - 8, w: W0 - m.l - m.r, h: ph };
      plotH = Math.max(160, panelBox.y - m.t - 100);
    }

    // Helpers
    const keyOf = (d) => String(o.key && d[o.key] != null ? d[o.key] : (o.label && d[o.label]) || "");
    const byKey = new Map(data.map(d => [keyOf(d), d]));

    // ---- SVG & layers
    const wrap = h("div", {}, el);
    const svg = d3.select(wrap).append("svg").attr("width", W0).attr("height", H0).attr("viewBox", `0 0 ${W0} ${H0}`);
    svg.append("rect").attr("x",0).attr("y",0).attr("width",W0).attr("height",H0).attr("fill","white");

    const gPlot = svg.append("g").attr("transform", `translate(${m.l},${m.t})`);
    const gGrid = gPlot.append("g");
    const gAxes = gPlot.append("g");
    const gBrush = gPlot.append("g"); // will be lowered below dots
    const gDots  = gPlot.append("g");
    const gTitle = svg.append("g");
    const gLegend= svg.append("g");   // legend is OUTSIDE the plot
    const gPanel = svg.append("g");

    if (o.title) {
      gTitle.append("text")
        .attr("x", m.l).attr("y", Math.max(18, m.t - 10))
        .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",14).attr("font-weight",600).attr("fill","#111827")
        .text(String(o.title));
    }

    // ---- tooltip (parallel-style) ----
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
      whiteSpace: "normal"
    });
    document.body.appendChild(tip);

    const nf = new Intl.NumberFormat();
    const tipHTML = (d) => {
      const head = (o.label && d[o.label] != null)
        ? `<div style="font-weight:700;margin-bottom:6px">${d[o.label]}</div>`
        : "";
      const rows = [
        `<div>${o.x}: <strong>${nf.format(+d[o.x] || 0)}</strong></div>`,
        `<div>${o.y}: <strong>${nf.format(+d[o.y] || 0)}</strong></div>`
      ];
      if (o.size)  rows.push(`<div>${o.size}: <strong>${nf.format(+d[o.size] || 0)}</strong></div>`);
      if (o.color) rows.push(`<div>${o.color}: <strong>${d[o.color]}</strong></div>`);
      return head + rows.join("");
    };
    const showTip = (ev, d) => {
      tip.innerHTML = tipHTML(d);
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX + 14) + "px";
      tip.style.top  = (ev.clientY + 14) + "px";
    };
    const hideTip = () => (tip.style.opacity = 0);




    // ---- Scales & axes  (REPLACED)
    const XV = data.map(d=>+d[o.x]).filter(Number.isFinite);
    const YV = data.map(d=>+d[o.y]).filter(Number.isFinite);

    // base scales (nice() first so ticks are sensible, then we’ll enforce aspect)
    const sx = (o.logX ? d3.scaleLog() : d3.scaleLinear())
      .domain([d3.min(XV), d3.max(XV)]).range([0, plotW]).nice();
    const sy = (o.logY ? d3.scaleLog() : d3.scaleLinear())
      .domain([d3.min(YV), d3.max(YV)]).range([plotH, 0]).nice();

    // --- Enforce square grid cells (equal px-per-unit on both axes), robust for wide/tall plots
    if (o.squareCells) {
      const toT = (log) => log ? (v) => Math.log(v) : (v) => v;
      const fromT = (log) => log ? (t) => Math.exp(t) : (t) => t;

      const tx = toT(o.logX),  ty = toT(o.logY);
      const ix = fromT(o.logX), iy = fromT(o.logY);

      // current data domains
      let [x0, x1] = sx.domain();
      let [y0, y1] = sy.domain();

      // guard log lower bounds to avoid -Inf
      if (o.logX) x0 = Math.max(x0, Number.MIN_VALUE);
      if (o.logY) y0 = Math.max(y0, Number.MIN_VALUE);

      // transform to linearized space for consistent “unit” math
      let Tx0 = tx(x0), Tx1 = tx(x1);
      let Ty0 = ty(y0), Ty1 = ty(y1);

      // handle degenerate spans
      if (!Number.isFinite(Tx0) || !Number.isFinite(Tx1) || !Number.isFinite(Ty0) || !Number.isFinite(Ty1) || Tx0 === Tx1 || Ty0 === Ty1) {
        // nothing we can safely do
      } else {
        const spanX = Math.abs(Tx1 - Tx0);
        const spanY = Math.abs(Ty1 - Ty0);

        // pixels per transformed unit
        const kx = plotW / spanX;
        const ky = plotH / spanY;

        // target px-per-unit is the SMALLER of the two (so we never clip);
        // this expands ONLY the axis that currently has higher px-per-unit.
        const kTarget = Math.min(kx, ky);

        // desired transformed spans for each axis to hit kTarget
        const wantSpanX = plotW / kTarget;
        const wantSpanY = plotH / kTarget;

        // center-preserving adjust in transformed space
        const cx = (Tx0 + Tx1) / 2;
        const cy = (Ty0 + Ty1) / 2;

        // If an axis already matches kTarget (within epsilon), leave it;
        // expand the other. This avoids the “reversed” feel on wide/tall canvases.
        const eps = 1e-9;

        let needX = Math.abs(kx - kTarget) > eps;
        let needY = Math.abs(ky - kTarget) > eps;

        // compute new transformed domains
        let nTx0 = Tx0, nTx1 = Tx1, nTy0 = Ty0, nTy1 = Ty1;

        if (needX) {
          const halfX = wantSpanX / 2;
          nTx0 = cx - halfX; nTx1 = cx + halfX;
        }
        if (needY) {
          const halfY = wantSpanY / 2;
          nTy0 = cy - halfY; nTy1 = cy + halfY;
        }

        // write back (no .nice() here; keep enforced aspect)
        sx.domain([ix(nTx0), ix(nTx1)]);
        sy.domain([iy(nTy0), iy(nTy1)]);
      }
    }

    const axX = d3.axisBottom(sx).ticks(o.xTicks || 8);
    const axY = d3.axisLeft(sy).ticks(o.yTicks || 8);

    if (o.grid) {
      gGrid.selectAll("line.v").data(sx.ticks(o.xTicks || 8)).join("line")
        .attr("x1", d => sx(d)).attr("x2", d => sx(d))
        .attr("y1", 0).attr("y2", plotH).attr("stroke", "#e5e7eb");
      gGrid.selectAll("line.h").data(sy.ticks(o.yTicks || 8)).join("line")
        .attr("x1", 0).attr("x2", plotW)
        .attr("y1", d => sy(d)).attr("y2", d => sy(d)).attr("stroke", "#e5e7eb");
    }


    gAxes.append("g").attr("transform", `translate(0,${plotH})`).call(axX)
      .call(g=>g.append("text").attr("x",plotW).attr("y",36).attr("text-anchor","end")
        .attr("fill","#111827").attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12)
        .text(o.xLabel ?? String(o.x)));
    gAxes.append("g").call(axY)
      .call(g=>g.append("text").attr("x",0).attr("y",-12).attr("text-anchor","start")
        .attr("fill","#111827").attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12)
        .text(o.yLabel ?? String(o.y)));

    // ---- Color
    let cmap = o.colorMap || null, cats=[];
    if (o.color){
      const domain = Array.from(new Set(data.map(d=>String(d[o.color]))));
      cats = domain;
      if (!cmap){ const pal=o.colors||[]; cmap={}; domain.forEach((v,i)=>cmap[v]=pal[i%pal.length]); }
    }

    // ---- Points
    const R = +o.radius || 5, A = +o.opacity || 0.92;

    const points = gDots.selectAll("circle")
      .data(data, (_, i) => i)
      .join("circle")
      .attr("cx", d => sx(+d[o.x]))
      .attr("cy", d => sy(+d[o.y]))
      .attr("r", d => (o.size && Number.isFinite(+d[o.size]))
        ? Math.max(1.5, Math.sqrt(+d[o.size])) : R)
      .attr("fill", d => o.color ? (cmap[String(d[o.color])] || "#888") : "#4b5563")
      .attr("fill-opacity", A)
      .attr("stroke", "white")
      .attr("stroke-width", 0.6)
      .style("cursor", "pointer")
      .style("pointer-events", "all")
      // hover + tooltip (parallel-style)
      .on("mouseenter", function (event, d) {
        d3.select(this)
          .attr("stroke", "#111")
          .attr("stroke-width", 1.2)
          .raise();
        showTip(event, d);
      })
      .on("mousemove", function (event, d) {
        showTip(event, d);
      })
      .on("mouseleave", function () {
        d3.select(this)
          .attr("stroke", "white")
          .attr("stroke-width", 0.6);
        hideTip();
      })
      // click toggle
      .on("click", function (_, d) { // stacked toggle
        const k = keyOf(d);
        if (selectedKeys.has(k)) selectedKeys.delete(k); else selectedKeys.add(k);
        pushSelectionFromKeys("set");
      });

    // ---- Selection state
    const selectedKeys = new Set();
    const pushSelectionFromKeys = (type="set")=>{
      const keys = Array.from(selectedKeys);
      const rows = keys.map(k=>byKey.get(k)).filter(Boolean);
      model.set("selection", { type, keys, rows, epoch: nowEpoch() });
      model.save_changes(); updatePanel(); applySelectionStyles();
    };

    // ---- Brush under points
    const brush = d3.brush().extent([[0,0],[plotW,plotH]]).on("end", brushed);
    gBrush.call(brush);
    gBrush.lower();   // brush under everything
    gDots.raise();    // dots above to receive pointer events

    function brushed({selection}){
      if (!selection){ selectedKeys.clear(); pushSelectionFromKeys("set"); return; }
      const [[x0,y0],[x1,y1]] = selection;
      selectedKeys.clear();
      points.each(function(d){ const x=sx(+d[o.x]), y=sy(+d[o.y]); if (x>=x0 && x<=x1 && y>=y0 && y<=y1) selectedKeys.add(keyOf(d)); });
      pushSelectionFromKeys("set");
    }

    function applySelectionStyles(){
      if (!selectedKeys.size){ points.attr("fill-opacity",A); return; }
      points.attr("fill-opacity", d=> selectedKeys.has(keyOf(d)) ? 1 : 0.15);
    }
    model.on("change:selection", ()=>{ updatePanel(); applySelectionStyles(); });

    // ---- Legend: ALWAYS OUTSIDE the plot, never under/over panel
    if (o.legend && cats.length){
      const gL = gLegend.append("g");
      gL.append("text").attr("x",0).attr("y",0)
        .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12).attr("font-weight",600).attr("fill","#111827")
        .text("Legend");
      const item=14, gap=6;
      const active = new Set(cats);
      cats.forEach((cat,i)=>{
        const y=16+i*(item+gap);
        gL.append("rect").attr("x",0).attr("y",y-item+2).attr("width",item).attr("height",item)
          .attr("fill",cmap[String(cat)]).style("cursor","pointer").on("click",toggle(cat));
        gL.append("text").attr("x",item+8).attr("y",y+2).attr("dominant-baseline","middle").attr("text-anchor","start")
          .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12).attr("fill","#111827")
          .style("cursor","pointer").text(String(cat)).on("click",toggle(cat));
        function toggle(catVal){
          return function(){
            if (active.has(catVal)) active.delete(catVal); else active.add(catVal);
            points.attr("fill-opacity", d=>{
              const on = !o.color || active.has(String(d[o.color]));
              const sel = selectedKeys.size ? selectedKeys.has(keyOf(d)) : true;
              return on && sel ? A : 0.08;
            });
          };
        }
      });

      // Estimate width; clamp inside available gap
      const bbox = gL.node().getBBox();
      const legendW = Math.max(+o.legend_width || 160, bbox.width + 10);

      let startX, startY = m.t + 4;

      if (o.legendPosition === "right") {
        if (o.panel_position === "right" && panelBox) {
          // place BETWEEN plot and panel
          const gapLeft = m.l + plotW + 2;
          const gapRight = panelBox.x - 2;
          const avail = Math.max(0, gapRight - gapLeft);
          const used = Math.min(legendW, avail);
          startX = gapLeft + Math.max(0, (avail - used) / 2);
        } else {
          // panel bottom (or none): we reserved LBLK, so safe to place here
          startX = m.l + plotW + 8;
        }
      } else {
        // left side (outside)
        startX = Math.max(4, m.l - (legendW + 8)); // push outside left margin
      }

      gL.attr("transform", `translate(${startX},${startY})`);
    }

    // ---- Panel (inside same SVG)
    function updatePanel(){
      gPanel.selectAll("*").remove();
      if (!panelBox) return;

      const cols = [o.label || o.key || "id", o.x, o.y, ...(o.color?[o.color]:[]), ...(o.size?[o.size]:[])].filter(Boolean);
      const rows = Array.from(selectedKeys).map(k=>byKey.get(k)).filter(Boolean);

      const panel = gPanel.append("g").attr("transform", `translate(${panelBox.x},${panelBox.y})`);
      panel.append("rect").attr("x",0).attr("y",0).attr("width",panelBox.w).attr("height",panelBox.h)
        .attr("rx",12).attr("fill","#f9fafb").attr("stroke","#e5e7eb");
      panel.append("text").attr("x",12).attr("y",18)
        .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12).attr("font-weight",700).attr("fill","#111827")
        .text(`Selected (${rows.length})`);

      const btn = panel.append("g").attr("transform", `translate(${panelBox.w-110},8)`).style("cursor","pointer");
      btn.append("rect").attr("width",100).attr("height",22).attr("rx",6).attr("fill", rows.length? "#111827":"#9ca3af");
      btn.append("text").attr("x",50).attr("y",14.5).attr("text-anchor","middle").attr("dominant-baseline","middle")
        .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",11).attr("fill","white").text("Export CSV");
      btn.on("click", ()=>{
        if (!rows.length) return;
        const csv = toCSV(rows, cols);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([csv], {type:"text/csv;charset=utf-8"}));
        a.download = "scatter_selection.csv"; a.click(); URL.revokeObjectURL(a.href);
      });

      const colX=[12]; const colW = Math.max(64,(panelBox.w-24)/Math.max(1,cols.length));
      for (let i=1;i<cols.length;i++) colX.push(12 + i*colW);

      panel.append("g").selectAll("text.th").data(cols).join("text")
        .attr("x",(_,i)=>colX[i]).attr("y",38)
        .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",11).attr("font-weight",600).attr("fill","#374151")
        .text(d=>String(d));
      panel.append("line").attr("x1",12).attr("x2",panelBox.w-12).attr("y1",44).attr("y2",44).attr("stroke","#e5e7eb");

      const maxRows = Math.floor((panelBox.h - 56) / 18);
      const show = rows.slice(0, maxRows);
      panel.append("g").selectAll("g.row").data(show).join(enter=>{
        const r = enter.append("g").attr("class","row");
        r.attr("transform",(_,i)=>`translate(0,${56+i*18})`);
        r.selectAll("text.td").data(row=>cols.map(c=>row[c])).join("text")
          .attr("x",(_,i)=>colX[i]).attr("y",0).attr("dominant-baseline","hanging")
          .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",11).attr("fill","#111827")
          .text(v=> typeof v==="number"? fmtNum(v): String(v ?? ""));
        return r;
      });
    }

    // Initial render & selection
    updatePanel(); applySelectionStyles();
    model.set("selection", { type:null, keys:[], rows:[], epoch: nowEpoch() });
    model.save_changes();
  }

  model.on("change:data", draw);
  model.on("change:options", draw);
  draw();
}



// // Isea/assets/scatter.js
// // Scatter with d3 rendering, same generic data API, same selection mechanics,
// // plus an inline selection panel (right/bottom) drawn *inside the same SVG*.
// // Selection payload remains { type, keys, rows } for linked views.

// export async function render({ model, el }) {
//   const mod = await import("https://cdn.jsdelivr.net/npm/d3@7/+esm");
//   const d3 = mod.default ?? mod;

//   function h(t, p = {}, parent) {
//     const n = document.createElement(t);
//     Object.assign(n, p);
//     if (parent) parent.appendChild(n);
//     return n;
//   }

//   function fmtNum(v) {
//     return new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(v);
//   }

//   function toCSV(rows, columns) {
//     const esc = (s) =>
//       String(s ?? "")
//         .replace(/"/g, '""');
//     const head = columns.map((c) => `"${esc(c)}"`).join(",");
//     const body = rows.map((r) => columns.map((c) => `"${esc(r[c])}"`).join(",")).join("\n");
//     return [head, body].filter(Boolean).join("\n");
//   }

//   function draw() {
//     el.innerHTML = "";

//     const data = model.get("data") || [];
//     const o = Object.assign(
//       {
//         x: "x",
//         y: "y",
//         key: "id",
//         label: null,
//         color: null,
//         size: null,
//         logX: false,
//         logY: false,

//         width: 720,
//         height: 420,
//         margin: { t: 28, r: 24, b: 56, l: 70 },

//         // legend + palette (same as before)
//         colors: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
//         colorMap: null,
//         legend: true,
//         legendPosition: "right",

//         // marks
//         radius: 5,
//         opacity: 0.92,
//         grid: true,
//         xTicks: 8,
//         yTicks: 8,

//         // NEW: inline selection panel, *inside the same SVG*
//         panel_position: "right", // "right" | "bottom"
//         panel_width: 300,
//         panel_height: 220,
//       },
//       model.get("options") || {}
//     );

//     // normalize margin
//     const m = (() => {
//       const M = o.margin || {};
//       if (Array.isArray(M)) {
//         const [t, r, b, l] = M;
//         return { t, r, b, l };
//       }
//       return {
//         t: +M.t ?? +M.top ?? 28,
//         r: +M.r ?? +M.right ?? 24,
//         b: +M.b ?? +M.bottom ?? 56,
//         l: +M.l ?? +M.left ?? 70,
//       };
//     })();

//     const W0 = Math.max(320, +o.width || 720);
//     const H0 = Math.max(240, +o.height || 420);

//     // Compute inner plotting area, reserving space for the panel (inside the same SVG)
//     let W = W0, H = H0;
//     let plotW = W0 - m.l - m.r;
//     let plotH = H0 - m.t - m.b;
//     let panelBox = null;
//     if (o.panel_position === "right") {
//       const pw = Math.max(200, +o.panel_width || 300);
//       panelBox = { x: W0 - pw - 8, y: m.t, w: pw, h: H0 - m.t - m.b };
//       plotW = Math.max(240, panelBox.x - m.l - 8);
//     } else if (o.panel_position === "bottom") {
//       const ph = Math.max(160, +o.panel_height || 220);
//       panelBox = { x: m.l, y: H0 - ph - 8, w: W0 - m.l - m.r, h: ph };
//       plotH = Math.max(160, panelBox.y - m.t - 8);
//     }

//     // Build SVG + layers
//     const wrap = h("div", {}, el);
//     const svg = d3.select(wrap).append("svg").attr("width", W).attr("height", H).attr("viewBox", `0 0 ${W0} ${H0}`);

//     // Background
//     svg.append("rect").attr("x", 0).attr("y", 0).attr("width", W0).attr("height", H0).attr("fill", "white");

//     const gPlot = svg.append("g").attr("transform", `translate(${m.l},${m.t})`);
//     const gGrid = gPlot.append("g");
//     const gAxes = gPlot.append("g");
//     const gDots = gPlot.append("g");
//     const gBrush = gPlot.append("g");
//     const gTitle = svg.append("g");
//     const gLegend = svg.append("g");
//     const gPanel = svg.append("g");

//     // Title
//     if (o.title) {
//       gTitle
//         .append("text")
//         .attr("x", m.l)
//         .attr("y", Math.max(18, m.t - 10))
//         .attr("font-family", "system-ui,Segoe UI,Arial")
//         .attr("font-size", 14)
//         .attr("font-weight", 600)
//         .attr("fill", "#111827")
//         .text(String(o.title));
//     }

//     // Tooltip div (HTML for readability, same content logic as before)
//     const tipHost = h("div", { style: "position:fixed;left:0;top:0;pointer-events:none;z-index:10" }, wrap);
//     const tip = h(
//       "div",
//       {
//         style:
//           "min-width:160px;max-width:280px;background:#111827;color:white;border-radius:8px;padding:8px 10px;font:12px/1.35 system-ui,Segoe UI,Arial;opacity:0;transform:translate(10px,10px)",
//       },
//       tipHost
//     );

//     function tipHTML(d) {
//       const xv = d[o.x], yv = d[o.y];
//       const parts = [];
//       if (o.label && d[o.label] != null) parts.push(`<div style="font-weight:600;margin-bottom:4px">${d[o.label]}</div>`);
//       parts.push(`<div><b>${o.x}:</b> ${fmtNum(xv)}</div>`);
//       parts.push(`<div><b>${o.y}:</b> ${fmtNum(yv)}</div>`);
//       if (o.size && d[o.size] != null) parts.push(`<div><b>${o.size}:</b> ${fmtNum(d[o.size])}</div>`);
//       if (o.color && d[o.color] != null) parts.push(`<div><b>${o.color}:</b> ${String(d[o.color])}</div>`);
//       return parts.join("");
//     }

//     function showTip(ev, d) {
//       tip.style.opacity = 0.98;
//       tip.style.left = ev.clientX + 12 + "px";
//       tip.style.top = ev.clientY + 12 + "px";
//       tip.innerHTML = tipHTML(d);
//     }
//     function hideTip() {
//       tip.style.opacity = 0;
//     }

//     // ----- Scales -----
//     const XV = data.map((d) => +d[o.x]).filter((v) => Number.isFinite(v));
//     const YV = data.map((d) => +d[o.y]).filter((v) => Number.isFinite(v));
//     const xmin = d3.min(XV), xmax = d3.max(XV);
//     const ymin = d3.min(YV), ymax = d3.max(YV);

//     const sx = (o.logX ? d3.scaleLog() : d3.scaleLinear()).domain([xmin, xmax]).range([0, plotW]).nice();
//     const sy = (o.logY ? d3.scaleLog() : d3.scaleLinear()).domain([ymin, ymax]).range([plotH, 0]).nice();

//     // ----- Axes + grid -----
//     const axX = d3.axisBottom(sx).ticks(o.xTicks || 8);
//     const axY = d3.axisLeft(sy).ticks(o.yTicks || 8);

//     if (o.grid) {
//       gGrid
//         .selectAll("line.v")
//         .data(sx.ticks(o.xTicks || 8))
//         .join("line")
//         .attr("class", "v")
//         .attr("x1", (d) => sx(d))
//         .attr("x2", (d) => sx(d))
//         .attr("y1", 0)
//         .attr("y2", plotH)
//         .attr("stroke", "#e5e7eb");

//       gGrid
//         .selectAll("line.h")
//         .data(sy.ticks(o.yTicks || 8))
//         .join("line")
//         .attr("class", "h")
//         .attr("x1", 0)
//         .attr("x2", plotW)
//         .attr("y1", (d) => sy(d))
//         .attr("y2", (d) => sy(d))
//         .attr("stroke", "#e5e7eb");
//     }

//     gAxes
//       .append("g")
//       .attr("transform", `translate(0,${plotH})`)
//       .call(axX)
//       .call((g) =>
//         g
//           .append("text")
//           .attr("x", plotW)
//           .attr("y", 36)
//           .attr("text-anchor", "end")
//           .attr("fill", "#111827")
//           .attr("font-family", "system-ui,Segoe UI,Arial")
//           .attr("font-size", 12)
//           .text(o.xLabel ?? String(o.x))
//       );

//     gAxes
//       .append("g")
//       .call(axY)
//       .call((g) =>
//         g
//           .append("text")
//           .attr("x", 0)
//           .attr("y", -12)
//           .attr("text-anchor", "start")
//           .attr("fill", "#111827")
//           .attr("font-family", "system-ui,Segoe UI,Arial")
//           .attr("font-size", 12)
//           .text(o.yLabel ?? String(o.y))
//       );

//     // ----- Color scale -----
//     let cmap = o.colorMap || null;
//     let cats = [];
//     if (o.color) {
//       const domain = Array.from(new Set(data.map((d) => d[o.color]).map(String)));
//       cats = domain;
//       if (cmap) {
//         // keep provided mapping
//       } else {
//         const pal = o.colors || [];
//         cmap = {};
//         domain.forEach((v, i) => (cmap[String(v)] = pal[i % pal.length]));
//       }
//     }

//     // ----- Points -----
//     const R = +o.radius || 5;
//     const A = +o.opacity || 0.92;

//     const points = gDots
//       .selectAll("circle")
//       .data(data, (_, i) => i)
//       .join("circle")
//       .attr("cx", (d) => sx(+d[o.x]))
//       .attr("cy", (d) => sy(+d[o.y]))
//       .attr("r", (d) => (o.size && Number.isFinite(+d[o.size]) ? Math.max(1.5, Math.sqrt(+d[o.size])) : R))
//       .attr("fill", (d) => (o.color ? (cmap[String(d[o.color])] || "#888") : "#4b5563"))
//       .attr("fill-opacity", A)
//       .attr("stroke", "white")
//       .attr("stroke-width", 0.6)
//       .style("cursor", "pointer")
//       .on("mousemove", function (ev, d) {
//         showTip(ev, d);
//       })
//       .on("mouseleave", function () {
//         hideTip();
//       })
//       .on("click", function (_, d) {
//         const key = o.key && d[o.key] != null ? d[o.key] : (o.label && d[o.label]) || "";
//         model.set("selection", { type: "point", keys: [String(key)], rows: [d] });
//         model.save_changes();
//         updatePanel();
//         applySelectionStyles();
//       });

//     // ----- Brush (same mechanics, now using d3.brush for rectangular selection) -----
//     const brush = d3
//       .brush()
//       .extent([
//         [0, 0],
//         [plotW, plotH],
//       ])
//       .on("end", brushed);

//     gBrush.call(brush);

//     function brushed({ selection }) {
//       if (!selection) {
//         // cleared
//         model.set("selection", { type: "set", keys: [], rows: [] });
//         model.save_changes();
//         updatePanel();
//         applySelectionStyles();
//         return;
//       }
//       const [[x0, y0], [x1, y1]] = selection;
//       const picked = [];
//       const keys = [];
//       points.each(function (d) {
//         const x = sx(+d[o.x]);
//         const y = sy(+d[o.y]);
//         if (x >= x0 && x <= x1 && y >= y0 && y <= y1) {
//           picked.push(d);
//           const key = o.key && d[o.key] != null ? d[o.key] : (o.label && d[o.label]) || "";
//           keys.push(String(key));
//         }
//       });
//       model.set("selection", { type: "set", keys, rows: picked });
//       model.save_changes();
//       updatePanel();
//       applySelectionStyles();
//     }

//     // ----- Selection highlight (same contract) -----
//     function applySelectionStyles() {
//       const s = model.get("selection") || {};
//       const keep = new Set((s.keys || []).map(String));
//       if (!keep.size) {
//         points.attr("fill-opacity", A);
//         return;
//       }
//       points.attr("fill-opacity", (d) => {
//         const key = o.key && d[o.key] != null ? d[o.key] : (o.label && d[o.label]) || "";
//         return keep.has(String(key)) ? 1 : 0.15;
//       });
//     }
//     model.on("change:selection", () => {
//       updatePanel();
//       applySelectionStyles();
//     });

//     // ----- Legend (same behavior) -----
//     if (o.legend && cats.length) {
//       const pad = 10, item = 14, gap = 6;
//       const rightX = m.l + plotW + 8;
//       const topY = m.t + 4;

//       const startX = (o.legendPosition === "right") ? rightX : m.l;
//       const startY = (o.legendPosition === "right") ? topY : m.t + 4;

//       const active = new Set(cats);
//       const gL = gLegend.append("g").attr("transform", `translate(${startX},${startY})`);
//       gL.append("text")
//         .attr("x", 0)
//         .attr("y", 0)
//         .attr("font-family", "system-ui,Segoe UI,Arial")
//         .attr("font-size", 12)
//         .attr("font-weight", 600)
//         .attr("fill", "#111827")
//         .text("Legend");

//       cats.forEach((cat, i) => {
//         const y = 16 + i * (item + gap);
//         gL
//           .append("rect")
//           .attr("x", 0)
//           .attr("y", y - item + 2)
//           .attr("width", item)
//           .attr("height", item)
//           .attr("fill", cmap[String(cat)])
//           .style("cursor", "pointer")
//           .on("click", toggle(cat));

//         gL
//           .append("text")
//           .attr("x", item + 8)
//           .attr("y", y + 2)
//           .attr("dominant-baseline", "middle")
//           .attr("text-anchor", "start")
//           .attr("font-family", "system-ui,Segoe UI,Arial")
//           .attr("font-size", 12)
//           .attr("fill", "#111827")
//           .style("cursor", "pointer")
//           .text(String(cat))
//           .on("click", toggle(cat));

//         function toggle(catVal) {
//           return function () {
//             if (active.has(catVal)) active.delete(catVal);
//             else active.add(catVal);
//             points.attr("fill-opacity", (d) => {
//               const on = !o.color || active.has(String(d[o.color]));
//               const s = model.get("selection") || {};
//               const keep = new Set((s.keys || []).map(String));
//               const key = o.key && d[o.key] != null ? d[o.key] : (o.label && d[o.label]) || "";
//               const selected = keep.size ? keep.has(String(key)) : true;
//               return on && selected ? A : 0.08;
//             });
//           };
//         }
//       });
//     }

//     // ----- Inline selection panel (inside same SVG) -----
//     function updatePanel() {
//       gPanel.selectAll("*").remove();
//       if (!panelBox) return;

//       const s = model.get("selection") || {};
//       const rows = s.rows || [];
//       const cols = [
//         o.label || o.key || "id",
//         o.x,
//         o.y,
//         ...(o.color ? [o.color] : []),
//         ...(o.size ? [o.size] : []),
//       ].filter(Boolean);

//       // panel frame
//       const panel = gPanel.append("g").attr("transform", `translate(${panelBox.x},${panelBox.y})`);
//       panel
//         .append("rect")
//         .attr("x", 0)
//         .attr("y", 0)
//         .attr("width", panelBox.w)
//         .attr("height", panelBox.h)
//         .attr("rx", 12)
//         .attr("fill", "#f9fafb")
//         .attr("stroke", "#e5e7eb");

//       // header
//       panel
//         .append("text")
//         .attr("x", 12)
//         .attr("y", 18)
//         .attr("font-family", "system-ui,Segoe UI,Arial")
//         .attr("font-size", 12)
//         .attr("font-weight", 700)
//         .attr("fill", "#111827")
//         .text(`Selected (${rows.length})`);

//       // "Export CSV" button
//       const btn = panel.append("g").attr("transform", `translate(${panelBox.w - 110},8)`).style("cursor", "pointer");
//       btn
//         .append("rect")
//         .attr("width", 100)
//         .attr("height", 22)
//         .attr("rx", 6)
//         .attr("fill", rows.length ? "#111827" : "#9ca3af");
//       btn
//         .append("text")
//         .attr("x", 50)
//         .attr("y", 14.5)
//         .attr("text-anchor", "middle")
//         .attr("dominant-baseline", "middle")
//         .attr("font-family", "system-ui,Segoe UI,Arial")
//         .attr("font-size", 11)
//         .attr("fill", "white")
//         .text("Export CSV");
//       btn.on("click", () => {
//         if (!rows.length) return;
//         const csv = toCSV(rows, cols);
//         const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
//         const a = document.createElement("a");
//         a.href = URL.createObjectURL(blob);
//         a.download = "scatter_selection.csv";
//         a.click();
//         URL.revokeObjectURL(a.href);
//       });

//       // table header
//       const colX = [12];
//       const colW = Math.max(64, (panelBox.w - 24) / Math.max(1, cols.length));
//       for (let i = 1; i < cols.length; i++) colX.push(12 + i * colW);

//       panel
//         .append("g")
//         .selectAll("text.th")
//         .data(cols)
//         .join("text")
//         .attr("class", "th")
//         .attr("x", (_, i) => colX[i])
//         .attr("y", 38)
//         .attr("font-family", "system-ui,Segoe UI,Arial")
//         .attr("font-size", 11)
//         .attr("font-weight", 600)
//         .attr("fill", "#374151")
//         .text((d) => String(d));

//       panel
//         .append("line")
//         .attr("x1", 12)
//         .attr("x2", panelBox.w - 12)
//         .attr("y1", 44)
//         .attr("y2", 44)
//         .attr("stroke", "#e5e7eb");

//       // rows
//       const maxRows = Math.floor((panelBox.h - 56) / 18);
//       const show = rows.slice(0, maxRows);

//       panel
//         .append("g")
//         .selectAll("g.row")
//         .data(show)
//         .join((enter) => {
//           const r = enter.append("g").attr("class", "row");
//           r.attr("transform", (_, i) => `translate(0,${56 + i * 18})`);
//           r
//             .selectAll("text.td")
//             .data((row) => cols.map((c) => row[c]))
//             .join("text")
//             .attr("class", "td")
//             .attr("x", (_, i) => colX[i])
//             .attr("y", 0)
//             .attr("dominant-baseline", "hanging")
//             .attr("font-family", "system-ui,Segoe UI,Arial")
//             .attr("font-size", 11)
//             .attr("fill", "#111827")
//             .text((v) => (typeof v === "number" ? fmtNum(v) : String(v ?? "")));
//           return r;
//         });
//     }

//     updatePanel();
//     applySelectionStyles();

//     // initial push so listeners downstream can unify payloads
//     const s0 = model.get("selection") || { type: null, keys: [], rows: [] };
//     model.set("selection", s0);
//     model.save_changes();
//   }

//   model.on("change:data", draw);
//   model.on("change:options", draw);
//   draw();
// }


// // Isea/assets/scatter.js
// // Compact scatter with nice axes, color legend toggle, size encoding, tooltip, and JS->PY selection.
// export function render({ model, el }) {
//   // ---------- helpers ----------
//   const NS = "http://www.w3.org/2000/svg";
//   const $ = (name) => document.createElementNS(NS, name);

//   // 1-2-5 nice ticks
//   const niceStep = (span, n) => {
//     const raw = span / Math.max(1, n || 5);
//     const p10 = Math.pow(10, Math.floor(Math.log10(raw)));
//     const m = raw / p10;
//     const k = m >= 5 ? 5 : m >= 2 ? 2 : 1;
//     return k * p10;
//   };
//   const makeTicks = (min, max, n) => {
//     const step = niceStep(max - min, n);
//     const a = Math.floor(min / step) * step;
//     const b = Math.ceil(max / step) * step;
//     const out = [];
//     for (let v = a; v <= b + 1e-9; v += step) out.push(+v.toFixed(12));
//     return { a, b, step, ticks: out };
//   };
//   const fmtTick = (step) =>
//     new Intl.NumberFormat(undefined, {
//       maximumFractionDigits: Math.max(0, -Math.floor(Math.log10(step))) + 2,
//     });

//   const scheme10 = [
//     "#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f",
//     "#edc948","#b07aa1","#ff9da7","#9c755f","#bab0ab"
//   ];

//   // ---------- drawing ----------
//   function draw() {
//     el.innerHTML = "";
//     const svg = $("svg");
//     el.appendChild(svg);

//     // data & options
//     const data = model.get("data") ?? [];
//     const o = Object.assign(
//       {
//         x: "x", y: "y", key: "id",
//         color: null, size: null, label: null,
//         logX: false, logY: false,

//         width: 720, height: 420,
//         margin: { t: 28, r: 24, b: 56, l: 70 },

//         grid: true, xTicks: 8, yTicks: 8,
//         radius: 5, opacity: 0.92,
//         colors: scheme10, colorMap: null,
//         legend: true, legendPosition: "right",

//         title: "", xLabel: null, yLabel: null
//       },
//       model.get("options") || {}
//     );

//     // auto labels
//     if (!o.xLabel) o.xLabel = String(o.x);
//     if (!o.yLabel) o.yLabel = String(o.y);

//     // add extra right space if legend on right
//     const extraRight = o.legend && o.legendPosition === "right" ? 120 : 0;
//     svg.setAttribute("width", o.width + extraRight);
//     svg.setAttribute("height", o.height);

//     const m = o.margin;
//     const W = o.width - m.l - m.r;
//     const H = o.height - m.t - m.b;

//     // extents (respect log > 0)
//     const xVals = data.map(d => +d[o.x]).filter(v => Number.isFinite(v) && (!o.logX || v > 0));
//     const yVals = data.map(d => +d[o.y]).filter(v => Number.isFinite(v) && (!o.logY || v > 0));
//     let x0 = xVals.length ? Math.min(...xVals) : 0, x1 = xVals.length ? Math.max(...xVals) : 1;
//     let y0 = yVals.length ? Math.min(...yVals) : 0, y1 = yVals.length ? Math.max(...yVals) : 1;
//     if (x0 === x1) { x0 -= 1; x1 += 1; }
//     if (y0 === y1) { y0 -= 1; y1 += 1; }

//     // nice ticks
//     const XT = makeTicks(x0, x1, o.xTicks);
//     const YT = makeTicks(y0, y1, o.yTicks);
//     x0 = o.logX ? Math.max(1e-12, x0) : XT.a; x1 = o.logX ? x1 : XT.b;
//     y0 = o.logY ? Math.max(1e-12, y0) : YT.a; y1 = o.logY ? y1 : YT.b;

//     // scales
//     const X = o.logX
//       ? (v) => m.l + (Math.log(v) - Math.log(x0)) / (Math.log(x1) - Math.log(x0)) * W
//       : (v) => m.l + (v - x0) / (x1 - x0) * W;
//     const Y = o.logY
//       ? (v) => m.t + H - (Math.log(v) - Math.log(y0)) / (Math.log(y1) - Math.log(y0)) * H
//       : (v) => m.t + H - (v - y0) / (y1 - y0) * H;

//     // groups
//     const gGrid = $("g"), gAxes = $("g"), gDots = $("g"), gLegend = $("g");
//     svg.append(gGrid, gAxes, gDots, gLegend);

//     // grid
//     if (o.grid && !o.logX) XT.ticks.forEach(v => {
//       const L = $("line"); L.setAttribute("x1", X(v)); L.setAttribute("y1", m.t);
//       L.setAttribute("x2", X(v)); L.setAttribute("y2", m.t+H);
//       L.setAttribute("stroke", "#e6e6e6"); gGrid.appendChild(L);
//     });
//     if (o.grid && !o.logY) YT.ticks.forEach(v => {
//       const L = $("line"); L.setAttribute("x1", m.l); L.setAttribute("y1", Y(v));
//       L.setAttribute("x2", m.l+W); L.setAttribute("y2", Y(v));
//       L.setAttribute("stroke", "#e6e6e6"); gGrid.appendChild(L);
//     });

//     // axes
//     const xAxis = $("line"); xAxis.setAttribute("x1", m.l); xAxis.setAttribute("y1", m.t+H);
//     xAxis.setAttribute("x2", m.l+W); xAxis.setAttribute("y2", m.t+H);
//     xAxis.setAttribute("stroke", "#444"); xAxis.setAttribute("stroke-width", "1.25"); gAxes.appendChild(xAxis);

//     const yAxis = $("line"); yAxis.setAttribute("x1", m.l); yAxis.setAttribute("y1", m.t);
//     yAxis.setAttribute("x2", m.l); yAxis.setAttribute("y2", m.t+H);
//     yAxis.setAttribute("stroke", "#444"); yAxis.setAttribute("stroke-width", "1.25"); gAxes.appendChild(yAxis);

//     const tfx = fmtTick(XT.step), tfy = fmtTick(YT.step);
//     if (!o.logX) XT.ticks.forEach(v => {
//       const l = $("line"); l.setAttribute("x1", X(v)); l.setAttribute("x2", X(v));
//       l.setAttribute("y1", m.t+H); l.setAttribute("y2", m.t+H+6);
//       l.setAttribute("stroke", "#444"); gAxes.appendChild(l);
//       const t = $("text"); t.setAttribute("x", X(v)); t.setAttribute("y", m.t+H+22);
//       t.setAttribute("text-anchor","middle"); t.setAttribute("font-size","12");
//       t.textContent = tfx.format(v); gAxes.appendChild(t);
//     });
//     if (!o.logY) YT.ticks.forEach(v => {
//       const l = $("line"); l.setAttribute("x1", m.l-6); l.setAttribute("x2", m.l);
//       l.setAttribute("y1", Y(v)); l.setAttribute("y2", Y(v));
//       l.setAttribute("stroke", "#444"); gAxes.appendChild(l);
//       const t = $("text"); t.setAttribute("x", m.l-10); t.setAttribute("y", Y(v)+4);
//       t.setAttribute("text-anchor","end"); t.setAttribute("font-size","12");
//       t.textContent = tfy.format(v); gAxes.appendChild(t);
//     });

//     // labels + title
//     if (o.title) { const t = $("text"); t.setAttribute("x", m.l + W/2); t.setAttribute("y", m.t-10); t.setAttribute("text-anchor","middle"); t.textContent = o.title; gAxes.appendChild(t); }
//     { const t = $("text"); t.setAttribute("x", m.l + W/2); t.setAttribute("y", m.t+H+40); t.setAttribute("text-anchor","middle"); t.textContent = o.xLabel; gAxes.appendChild(t); }
//     { const t = $("text"); t.setAttribute("x", m.l-46); t.setAttribute("y", m.t+H/2); t.setAttribute("text-anchor","middle"); t.setAttribute("transform", `rotate(-90 ${m.l-46} ${m.t+H/2})`); t.textContent = o.yLabel; gAxes.appendChild(t); }

//     // color + size
//     const cats = o.color ? [...new Set(data.map(d => d[o.color]).filter(v => v!=null))] : [];
//     const cmap = Object.assign(
//       Object.fromEntries(cats.map((c,i)=>[String(c), (o.colors[i % o.colors.length]) ])),
//       o.colorMap || {}
//     );
//     const colorOf = o.color ? (d)=> cmap[String(d[o.color])] : ()=>"#4f46e5";

//     let S = ()=>o.radius;
//     if (o.size) {
//       const sVals = data.map(d => +d[o.size] || 0);
//       const s0 = Math.min(...sVals), s1 = Math.max(...sVals);
//       const r0 = 3, r1 = 16;
//       S = (d) => {
//         const v = +d[o.size] || 0;
//         if (s1 === s0) return (r0 + r1)/2;
//         return r0 + (v - s0) / (s1 - s0) * (r1 - r0);
//       };
//     }

//     // tooltip
//     const tipHost = el.appendChild(document.createElement("div"));
//     tipHost.style.position = "relative";
//     const tip = document.createElement("div");
//     Object.assign(tip.style, {
//       position: "absolute", zIndex: "9999", pointerEvents: "none", background: "rgba(17,24,39,.92)",
//       color: "#fff", padding: "6px 8px", borderRadius: "6px", font: "12px sans-serif",
//       boxShadow: "0 4px 16px rgba(0,0,0,.25)", opacity: 0, transition: "opacity .12s",
//       whiteSpace: "pre"
//     });
//     tipHost.appendChild(tip);
//     const nf = new Intl.NumberFormat();
//     const tipHTML = (d) => {
//       const head = o.label && d[o.label] != null ? `${d[o.label]}\n` : "";
//       const lines = [
//         `${o.x}: ${nf.format(+d[o.x]||0)}`,
//         `${o.y}: ${nf.format(+d[o.y]||0)}`
//       ];
//       if (o.size) lines.push(`${o.size}: ${nf.format(+d[o.size]||0)}`);
//       if (o.color) lines.push(`${o.color}: ${d[o.color]}`);
//       return head + lines.join("\n");
//     };

//     // draw points
//     const points = [];
//     data.forEach((d, i) => {
//       const xv = +d[o.x], yv = +d[o.y];
//       if (!Number.isFinite(xv) || !Number.isFinite(yv)) return;
//       if ((o.logX && xv <= 0) || (o.logY && yv <= 0)) return;

//       const c = $("circle");
//       const cx = X(xv), cy = Y(yv);
//       c.setAttribute("cx", cx); c.setAttribute("cy", cy);
//       c.setAttribute("r", S(d));
//       c.setAttribute("fill", colorOf(d));
//       c.style.opacity = o.opacity;

//       c.addEventListener("mouseenter", (ev) => {
//         c.setAttribute("stroke", "#111"); c.setAttribute("stroke-width", "1.2");
//         tip.textContent = tipHTML(d); tip.style.opacity = 1;
//         tip.style.left = (ev.clientX + 12) + "px";
//         tip.style.top  = (ev.clientY + 12) + "px";
//         tip.style.position = "fixed"; // instead of absolute
//       });
//       c.addEventListener("mouseleave", () => {
//         c.removeAttribute("stroke"); c.removeAttribute("stroke-width");
//         tip.style.opacity = 0;
//       });
//       c.addEventListener("mousemove", (ev) => {
//         tip.style.left = (ev.clientX + 12) + "px";
//         tip.style.top  = (ev.clientY + 12) + "px";
//         tip.style.position = "fixed"; // instead of absolute
//       });
//       c.addEventListener("click", () => {
//         const key = o.key && d[o.key] != null ? d[o.key] : (d.name ?? i);
//         model.set("selection", { type: "point", keys: [key], rows: [d] });
//         model.save_changes();
//       });

//       gDots.appendChild(c);
//       points.push({ el: c, d, cx, cy, key: o.key && d[o.key] != null ? d[o.key] : (d.name ?? i) });
//     });

//     // brush select (drag rectangle)
//     const brush = $("rect");
//     brush.setAttribute("fill", "rgba(0,0,0,0.08)");
//     brush.setAttribute("stroke", "rgba(0,0,0,0.25)");
//     brush.style.display = "none";
//     svg.appendChild(brush);
//     let start = null, moved = false;
//     const clearSel = () => { model.set("selection", {}); model.save_changes(); };

//     svg.addEventListener("mousedown",(e)=>{
//       const r = svg.getBoundingClientRect();
//       start = { x: e.clientX - r.left, y: e.clientY - r.top }; moved = false;
//       brush.style.display = "block";
//       brush.setAttribute("x", start.x); brush.setAttribute("y", start.y);
//       brush.setAttribute("width", 0); brush.setAttribute("height", 0);
//     });
//     svg.addEventListener("mousemove",(e)=>{
//       if (!start) return; moved = true;
//       const r = svg.getBoundingClientRect(); const x = e.clientX - r.left, y = e.clientY - r.top;
//       const x0 = Math.min(start.x, x), y0 = Math.min(start.y, y);
//       brush.setAttribute("x", x0); brush.setAttribute("y", y0);
//       brush.setAttribute("width", Math.abs(x - start.x)); brush.setAttribute("height", Math.abs(y - start.y));
//     });
//     svg.addEventListener("mouseup",()=>{
//       if (!start) return;
//       const x0 = +brush.getAttribute("x"), y0 = +brush.getAttribute("y");
//       const x1 = x0 + (+brush.getAttribute("width")), y1 = y0 + (+brush.getAttribute("height"));
//       brush.style.display = "none"; const prev = start; start = null;
//       if (!moved || (x1 - x0 < 3 && y1 - y0 < 3)) { clearSel(); return; }
//       const sel = points.filter(p => p.cx>=x0 && p.cx<=x1 && p.cy>=y0 && p.cy<=y1);
//       model.set("selection", { type: "set", keys: sel.map(p=>p.key), rows: sel.map(p=>p.d) });
//       model.save_changes();
//     });
//     svg.addEventListener("dblclick", clearSel);
//     window.addEventListener("keydown", (e)=>{ if (e.key === "Escape") clearSel(); });

//     // selection highlight
//     function applySelection() {
//       const s = model.get("selection") || {};
//       if (!s.type) { points.forEach(p => p.el.style.opacity = o.opacity); return; }
//       const keep = new Set((s.keys || []).map(String));
//       if (!keep.size) { points.forEach(p => p.el.style.opacity = o.opacity); return; }
//       points.forEach(p => p.el.style.opacity = keep.has(String(p.key)) ? 1.0 : 0.2);
//     }
//     model.on("change:selection", applySelection); applySelection();

//     // legend with toggle
//     if (o.legend && cats.length) {
//       const pad = 10, item = 14, gap = 6;
//       const startX = m.l + W + 16, startY = m.t + pad;
//       const active = new Set(cats);

//       cats.forEach((cat, i) => {
//         const y = startY + i * (item + gap);
//         const swatch = $("rect");
//         swatch.setAttribute("x", startX); swatch.setAttribute("y", y - item + 2);
//         swatch.setAttribute("width", item); swatch.setAttribute("height", item);
//         swatch.setAttribute("fill", cmap[String(cat)]);
//         swatch.style.cursor = "pointer";
//         gLegend.appendChild(swatch);

//         const lbl = $("text");
//         lbl.setAttribute("x", startX + item + 8); lbl.setAttribute("y", y + 2);
//         lbl.setAttribute("dominant-baseline","middle"); lbl.setAttribute("text-anchor","start");
//         lbl.textContent = String(cat); lbl.style.cursor = "pointer";
//         gLegend.appendChild(lbl);

//         const toggle = () => {
//           if (active.has(cat)) active.delete(cat); else active.add(cat);
//           const on = (d) => !o.color || active.has(d[o.color]);
//           points.forEach(p => p.el.style.opacity = on(p.d) ? o.opacity : 0.08);
//           swatch.setAttribute("opacity", active.has(cat) ? 1 : 0.25);
//           lbl.setAttribute("opacity", active.has(cat) ? 1 : 0.35);
//         };
//         swatch.addEventListener("click", toggle);
//         lbl.addEventListener("click", toggle);
//       });
//     }
//   }

//   model.on("change:data", draw);
//   model.on("change:options", draw);
//   draw();
// }

