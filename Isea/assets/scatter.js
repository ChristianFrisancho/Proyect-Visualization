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
      colorMap:null, legend:true, legendPosition:"right", legend_width:160,
      radius:5, opacity:0.92, grid:true, squareCells:true, xTicks:8, yTicks:8,
      panel_position:"right", panel_width:300, panel_height:220,
      title:null, xLabel:null, yLabel:null
    }, model.get("options") || {});
    
      // --- Year-aware remapping (TechUnit__FYYYY -> TechUnit) ---   #! added to try to fix year slider
      const listVars = Array.isArray(o.xyVars) ? o.xyVars.filter(Boolean) : [];
      let currentYear = null;

      function remapTechVars(year) {    // !Changed to try and fix
        if (!listVars.length || !Number.isFinite(+year)) return;
        const tag = `F${+year}`;
        const rows = model.get("data") || [];

        rows.forEach(d => {
          // ✅ ensure key/label stay present & non-empty
          if (o.label && (d[o.label] == null)) d[o.label] = d.Country ?? d.name ?? "";
          if (o.key   && (d[o.key]   == null)) d[o.key]   = d[o.label] ?? d.Country ?? "";

          // copy current year values into bare TechUnit fields
          listVars.forEach(v => { d[v] = +d[`${v}__${tag}`] || 0; });
          d.Year = +year; // handy for selection table/tooltip
        });

        currentYear = +year;
      }

    const M = o.margin || {};
    const m = Array.isArray(M) ? {t:M[0], r:M[1], b:M[2], l:M[3]} : {
      t:+M.t ?? +M.top ?? 28, r:+M.r ?? +M.right ?? 24, b:+M.b ?? +M.bottom ?? 56, l:+M.l ?? +M.left ?? 70
    };

    const bounds = el.getBoundingClientRect();
    const W0 = (o.width != null ? +o.width : Math.max(1, Math.floor(bounds.width))) || 720;
    const H0 = (o.height != null ? +o.height : 420);

    // ---- Layout: plot + reserved legend + internal panel
    const LBLK = (o.legend && o.legendPosition === "right" && o.panel_position !== "right") ? Math.max(120, +o.legend_width || 160) : 0;

    let plotW = W0 - m.l - m.r - LBLK;
    let plotH = H0 - m.t - m.b;
    let panelBox = null;

    if (o.panel_position === "right") {
      const pw = Math.max(200, +o.panel_width || 300);
      panelBox = { x: W0 - pw - 8, y: m.t, w: pw, h: H0 - m.t - m.b };
      plotW = Math.max(240, panelBox.x - m.l - 100);
    } else if (o.panel_position === "bottom") {
      const ph = Math.max(160, +o.panel_height || 220);
      panelBox = { x: m.l, y: H0 - ph - 8, w: W0 - m.l - m.r, h: ph };
      plotH = Math.max(160, panelBox.y - m.t - 100);
    }

    // Helpers
    const keyOf = d => (o.key && d[o.key] != null) ? d[o.key] : (o.label ? d[o.label] : null); //! changed to try and fix
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
    const tipHTML = (d) => {                    // Adjusted to try and fix
      const head = (o.label && d[o.label] != null)
        ? `<div style="font-weight:700;margin-bottom:6px">${d[o.label]}</div>`
        : "";

      const meta = [
        (o.color && d[o.color] != null) ? `Continent: <strong>${d[o.color]}</strong>` : null,
        (currentYear != null) ? `Year: <strong>${currentYear}</strong>` : null,
      ].filter(Boolean).map(s => `<div>${s}</div>`).join("");

      const allVars = (Array.isArray(o.xyVars) ? o.xyVars : []).map(v =>
        `<div>${v}: <strong>${nf.format(+d[v] || 0)}</strong></div>`
      ).join("");

      return head + (meta ? `<div style="margin-bottom:6px">${meta}</div>` : "") + allVars;
    };

    const showTip = (ev, d) => {
      tip.innerHTML = tipHTML(d);
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX + 14) + "px";
      tip.style.top  = (ev.clientY + 14) + "px";
    };
    const hideTip = () => (tip.style.opacity = 0);
    
    // 🔹 Initialize current-year values under bare TechUnit names (so XV/YV are valid) //! trying to fix
    const initYear = Number.isFinite(+o.yearMax) ? +o.yearMax : +o.yearMin;
    remapTechVars(initYear);

    // ---- Scales & axes
    const XV = data.map(d=>+d[o.x]).filter(Number.isFinite);
    const YV = data.map(d=>+d[o.y]).filter(Number.isFinite);

    const sx = (o.logX ? d3.scaleLog() : d3.scaleLinear())
      .domain([d3.min(XV), d3.max(XV)]).range([0, plotW]).nice();
    const sy = (o.logY ? d3.scaleLog() : d3.scaleLinear())
      .domain([d3.min(YV), d3.max(YV)]).range([plotH, 0]).nice();

    if (o.squareCells) {
      const toT = (log) => log ? (v) => Math.log(v) : (v) => v;
      const fromT = (log) => log ? (t) => Math.exp(t) : (t) => t;

      const tx = toT(o.logX),  ty = toT(o.logY);
      const ix = fromT(o.logX), iy = fromT(o.logY);

      let [x0, x1] = sx.domain();
      let [y0, y1] = sy.domain();
      if (o.logX) x0 = Math.max(x0, Number.MIN_VALUE);
      if (o.logY) y0 = Math.max(y0, Number.MIN_VALUE);

      let Tx0 = tx(x0), Tx1 = tx(x1);
      let Ty0 = ty(y0), Ty1 = ty(y1);
      if (Number.isFinite(Tx0) && Number.isFinite(Tx1) && Number.isFinite(Ty0) && Number.isFinite(Ty1) && Tx0 !== Tx1 && Ty0 !== Ty1) {
        const spanX = Math.abs(Tx1 - Tx0);
        const spanY = Math.abs(Ty1 - Ty0);
        const kx = plotW / spanX;
        const ky = plotH / spanY;
        const kTarget = Math.min(kx, ky);
        const wantSpanX = plotW / kTarget;
        const wantSpanY = plotH / kTarget;
        const cx = (Tx0 + Tx1) / 2;
        const cy = (Ty0 + Ty1) / 2;
        const eps = 1e-9;
        const needX = Math.abs(kx - kTarget) > eps;
        const needY = Math.abs(ky - kTarget) > eps;
        let nTx0 = Tx0, nTx1 = Tx1, nTy0 = Ty0, nTy1 = Ty1;
        if (needX) { const halfX = wantSpanX / 2; nTx0 = cx - halfX; nTx1 = cx + halfX; }
        if (needY) { const halfY = wantSpanY / 2; nTy0 = cy - halfY; nTy1 = cy + halfY; }
        sx.domain([ix(nTx0), ix(nTx1)]);
        sy.domain([iy(nTy0), iy(nTy1)]);
      }
    }

    // axis groups we can update later
    const gx = gAxes.append("g").attr("transform", `translate(0,${plotH})`);
    const gy = gAxes.append("g");

    const axX = d3.axisBottom(sx).ticks(o.xTicks || 8);
    const axY = d3.axisLeft(sy).ticks(o.yTicks || 8);

    // if (o.grid) {
    //   gGrid.selectAll("line.v").data(sx.ticks(o.xTicks || 8)).join("line")
    //     .attr("x1", d => sx(d)).attr("x2", d => sx(d))
    //     .attr("y1", 0).attr("y2", plotH).attr("stroke", "#e5e7eb");
    //   gGrid.selectAll("line.h").data(sy.ticks(o.yTicks || 8)).join("line")
    //     .attr("x1", 0).attr("x2", plotW)
    //     .attr("y1", d => sy(d)).attr("y2", d => sy(d)).attr("stroke", "#e5e7eb");
    // }

    gx.call(axX)
      .call(g=>g.selectAll(".x-label").data([0]).join("text")
        .attr("class","x-label").attr("x",plotW).attr("y",36).attr("text-anchor","end")
        .attr("fill","#111827").attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12)
        .text(o.xLabel ?? String(o.x)));
    gy.call(axY)
      .call(g=>g.selectAll(".y-label").data([0]).join("text")
        .attr("class","y-label").attr("x",0).attr("y",-12).attr("text-anchor","start")
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
      .data(data, keyOf)   //1 ✅ bind by key, not index
      .join("circle")
      .attr("cx", d => sx(+d[o.x]))
      .attr("cy", d => sy(+d[o.y]))
      .attr("r", d => (o.size && Number.isFinite(+d[o.size]))
        ? Math.max(1.5, Math.sqrt(+d[o.size])) : R)
      .attr("fill", d => o.color ? (cmap[String(d[o.color])] || "#888") : "#4b5563")
      .attr("fill-opacity", A)
      .attr("stroke", "white")
      .attr("stroke-width", 0.6)
      .attr("display", d => (+d[o.x] === 0 && +d[o.y] === 0) ? "none" : null)
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

    // ===== Controls: dynamic X/Y button groups (driven by o.xyVars) =====
    const xyVars = Array.isArray(o.xyVars) ? o.xyVars.filter(Boolean) : [];
    if (xyVars.length) {
      const controls = el.insertBefore(document.createElement("div"), wrap);
      Object.assign(controls.style, {
        display: "flex", gap: "16px", alignItems: "center",
        margin: "6px 0 10px 0", flexWrap: "wrap"
      });

      function makeGroup(titleText) {
        const group = document.createElement("div");
        group.style.display = "flex";
        group.style.alignItems = "center";
        group.style.gap = "8px";
        const label = document.createElement("span");
        label.textContent = titleText;
        Object.assign(label.style, {
          font: "12px/1.3 sans-serif", color: "#374151", fontWeight: 600
        });
        const btns = document.createElement("div");
        btns.style.display = "flex";
        btns.style.gap = "6px";
        group.appendChild(label); group.appendChild(btns);
        return { group, btns };
      }

      const { group: xGroup, btns: xBtns } = makeGroup("X:");
      const { group: yGroup, btns: yBtns } = makeGroup("Y:");
      controls.appendChild(xGroup);
      controls.appendChild(yGroup);

      function asButton(text, active) {
        const b = document.createElement("button");
        b.textContent = text;
        Object.assign(b.style, {
          font: "12px/1.2 sans-serif",
          padding: "4px 8px",
          borderRadius: "999px",
          border: "1px solid " + (active ? "#111827" : "#D1D5DB"),
          background: active ? "#111827" : "#FFFFFF",
          color: active ? "#FFFFFF" : "#111827",
          cursor: "pointer",
        });
        return b;
      }

      // helpers to update axes/grid/points
      function updateGrid() {
        if (!o.grid) return;
        gGrid.selectAll("line.v").data(sx.ticks(o.xTicks || 8)).join(
          enter => enter.append("line").attr("class","v")
            .attr("y1", 0).attr("y2", plotH).attr("stroke", "#e5e7eb")
            .attr("x1", d => sx(d)).attr("x2", d => sx(d)),
          update => update
            .attr("x1", d => sx(d)).attr("x2", d => sx(d))
            .attr("y1", 0).attr("y2", plotH),
          exit => exit.remove()
        );
        gGrid.selectAll("line.h").data(sy.ticks(o.yTicks || 8)).join(
          enter => enter.append("line").attr("class","h")
            .attr("x1", 0).attr("x2", plotW).attr("stroke", "#e5e7eb")
            .attr("y1", d => sy(d)).attr("y2", d => sy(d)),
          update => update
            .attr("x1", 0).attr("x2", plotW)
            .attr("y1", d => sy(d)).attr("y2", d => sy(d)),
          exit => exit.remove()
        );
      }

      function updateScalesAndAxes() {
        const XV2 = data.map(d=>+d[o.x]).filter(Number.isFinite);
        const YV2 = data.map(d=>+d[o.y]).filter(Number.isFinite);
        sx.domain([d3.min(XV2), d3.max(XV2)]).nice();
        sy.domain([d3.min(YV2), d3.max(YV2)]).nice();

        gx.call(d3.axisBottom(sx).ticks(o.xTicks || 8));
        gx.select(".x-label").text(o.xLabel ?? String(o.x));
        gy.call(d3.axisLeft(sy).ticks(o.yTicks || 8));
        gy.select(".y-label").text(o.yLabel ?? String(o.y));

        updateGrid();
      }

      function repositionPoints() {
        gDots.selectAll("circle")
          .transition().duration(220)
          .attr("cx", d => sx(+d[o.x]))
          .attr("cy", d => sy(+d[o.y]))
          .attr("display", d => (+d[o.x] === 0 && +d[o.y] === 0) ? "none" : null);
      }
      
      // Initial render --
      updateScalesAndAxes();
      repositionPoints();
      // -- Initial render

      function setX(v) { if (v !== o.x) { o.x = v; updateScalesAndAxes(); repositionPoints(); renderButtons(); } }
      function setY(v) { if (v !== o.y) { o.y = v; updateScalesAndAxes(); repositionPoints(); renderButtons(); } }

      function renderButtons() {
        xBtns.innerHTML = ""; yBtns.innerHTML = "";
        xyVars.forEach(v => {
          const bx = asButton(v, v === o.x); bx.onclick = () => setX(v); xBtns.appendChild(bx);
          const by = asButton(v, v === o.y); by.onclick = () => setY(v); yBtns.appendChild(by);
        });
      }

      renderButtons();
      // ===== Year slider (below the X/Y button groups, only if o.yearMin & o.yearMax) =====
      if (Number.isFinite(+o.yearMin) && Number.isFinite(+o.yearMax) && +o.yearMin < +o.yearMax) {
        const yrMin = +o.yearMin;
        const yrMax = +o.yearMax;

        // Container just below the XY buttons
        const bar = document.createElement("div");
        Object.assign(bar.style, {
          display: "flex",
          gap: "10px",
          alignItems: "center",
          margin: "6px 0 10px 0",
        });
        controls.insertAdjacentElement("afterend", bar);

        // Label
        const label = document.createElement("span");
        Object.assign(label.style, {
          font: "12px/1.3 sans-serif",
          color: "#374151",
          fontWeight: 600,
        });
        label.textContent = "Year:";
        bar.appendChild(label);

        // Year value
        const val = document.createElement("span");
        Object.assign(val.style, {
          font: "12px/1.3 sans-serif",
          color: "#111827",
          minWidth: "36px",
        });
        bar.appendChild(val);

        // Slider element
        const slider = document.createElement("input");
        slider.type = "range";
        slider.min = String(yrMin);
        slider.max = String(yrMax);
        slider.step = "1";
        slider.value = String(yrMax);
        Object.assign(slider.style, {
          width: plotW + "px",
          height: "6px",
          accentColor: "#2563eb", // optional: blue accent (matches your screenshot)
          cursor: "pointer",
        });
        val.textContent = slider.value;
        bar.appendChild(slider);

        // Event handler
        slider.addEventListener("input", () => {
          const y = +slider.value;
          remapTechVars(y);   // <- copy <TechUnit>__FYYYY into bare <TechUnit> for all rows
          val.textContent = String(y);
          // const col = `F${y}`;
          // if (!(data.length && col in data[0])) return;

          // Update x/y if they are year-like
          if (/^F\d{4}$/.test(o.x)) o.x = col;
          if (/^F\d{4}$/.test(o.y)) o.y = col;

          if (typeof renderButtons === "function") renderButtons();
          updateScalesAndAxes();
          repositionPoints();
        });
      }

    }

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

    // ---- Legend (use existing `cats` and `cmap` from above)
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
          .attr("fill", cmap[String(cat)])                     // <- use existing cmap
          .style("cursor","pointer").on("click", toggle(cat));

        gL.append("text").attr("x",item+8).attr("y",y+2).attr("dominant-baseline","middle").attr("text-anchor","start")
          .attr("font-family","system-ui,Segoe UI,Arial").attr("font-size",12).attr("fill","#111827")
          .style("cursor","pointer").text(String(cat)).on("click", toggle(cat));

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

      const bbox = gL.node().getBBox();
      const legendW = Math.max(+o.legend_width || 160, bbox.width + 10);

      let startX, startY = m.t + 4;
      if (o.legendPosition === "right") {
        if (o.panel_position === "right" && panelBox) {
          const gapLeft = m.l + plotW + 2;
          const gapRight = panelBox.x - 2;
          const avail = Math.max(0, gapRight - gapLeft);
          const used = Math.min(legendW, avail);
          startX = gapLeft + Math.max(0, (avail - used) / 2);
        } else {
          startX = m.l + plotW + 8;
        }
      } else {
        startX = Math.max(4, m.l - (legendW + 8));
      }
      gL.attr("transform", `translate(${startX},${startY})`);
    }

    // ---- Panel (inside same SVG)
    function updatePanel(){
      gPanel.selectAll("*").remove();
      if (!panelBox) return;

      const cols = [o.label || o.key || "id", o.x, o.y, "Year"].filter(Boolean); //! trying to fix
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
