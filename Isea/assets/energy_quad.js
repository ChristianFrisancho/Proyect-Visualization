// Isea/assets/energy_quad.js
export function render({ model, el }) {
  // -------- helper to create nodes --------
  const h = (t, p = {}, parent) => {
    const n = document.createElement(t);
    Object.assign(n, p);
    if (parent) parent.appendChild(n);
    return n;
  };

  async function draw() {
    // hard cleanup of host
    el.innerHTML = "";

    // ---------- data and options ----------
    const pack = model.get("data") ?? {};
    const opts = model.get("options") ?? {};
    const YEARS = pack.years || [];
    let DIMS = (pack.dims || []).slice();
    const R = pack.records || [];
    if (!YEARS.length || !DIMS.length || !R.length) {
      el.textContent = "No data.";
      return;
    }

    // ---------- d3 ----------
    const mod = await import("https://cdn.jsdelivr.net/npm/d3@7/+esm");
    const d3 = mod.default ?? mod;

    // ---------- responsive dimensions ----------
    const GAP = 12;
    const availW = Math.max(el.clientWidth || 0, 640);
    const targetW = Math.min(+opts.width || 1200, availW);

    // right column: proportion and max
    const rShare   = Math.max(0.30, Math.min(+opts.right_share || 0.40, 0.60));
    const rightMax = +opts.right_width || 560;
    const rightW   = Math.min(Math.round(targetW * rShare), rightMax);
    const leftW    = targetW - rightW - GAP;

    // heights
    const row1H = +opts.left_height || 460;
    const row2H = Math.max(+opts.table_height || 180, +opts.mini_height || 260);

    const useLog       = !!opts.log_axes;
    const normalize    = !!opts.normalize;
    const allowReorder = !!opts.reorder;

    let idxYear = YEARS.indexOf(opts.year_start ?? YEARS[YEARS.length - 1]);
    if (idxYear < 0) idxYear = YEARS.length - 1;

    // ---------- data helpers ----------
    function datasetFor(i) {
      return R.map(r => {
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
        const vals = data.map(d => +d[k]).filter(Number.isFinite);
        const mn = d3.min(vals), mx = d3.max(vals);
        ext[k] = (mx > mn) ? [mn, mx] : [0, 1];
      }
      return data.map(d => {
        const o = { Country: d.Country, Year: d.Year, DominantTech: d.DominantTech };
        for (const k of DIMS) {
          const [mn, mx] = ext[k], v = +d[k] || 0;
          o[k] = (mx > mn) ? (v - mn) / (mx - mn) : 0;
        }
        return o;
      });
    }
    function datasetYear(i) {
      let d = datasetFor(i);
      if (normalize) d = normalizeByDim(d);
      return d;
    }

    // ---------- colors + tooltip ----------
    const color = d3.scaleOrdinal(
      ["Fossil", "Hydro", "Wind", "Solar", "Bio"],
      ["#60a5fa", "#f59e0b", "#ef4444", "#2dd4bf", "#9b59b6"]
    );

    // tooltip global (INVISIBLE at start)
    const tip = document.createElement("div");
    Object.assign(tip.style, {
      position: "fixed",
      zIndex: 9999,
      pointerEvents: "none",
      background: "rgba(17,24,39,.96)",
      color: "#fff",
      padding: "10px 12px",
      borderRadius: "10px",
      font: "12px/1.35 system-ui",
      boxShadow: "0 10px 24px rgba(0,0,0,.35)",
      opacity: 0,
      transition: "opacity .12s"
    });
    document.body.appendChild(tip);
    const showTip = (ev, html) => {
      tip.innerHTML = html;
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX + 14) + "px";
      tip.style.top  = (ev.clientY + 14) + "px";
    };
    const hideTip = () => { tip.style.opacity = 0; };

    // ---------- container and grid ----------
    const frame = h("div", {}, el);
    frame.style.cssText = "overflow:auto;max-width:100%;";
    const grid = h("div", {}, frame);
    grid.style.cssText =
      `display:grid;grid-template-columns:${leftW}px ${rightW}px;` +
      `grid-template-rows:${row1H}px ${row2H}px;gap:${GAP}px;align-items:start;width:${targetW}px;`;

    const cellCss = "position:relative;overflow:hidden;background:transparent;";

    // row 1
    const leftTop  = h("div", {}, grid);  leftTop.style.cssText  = cellCss + `height:${row1H}px;display:flex;flex-direction:column;`;
    const rightTop = h("div", {}, grid);  rightTop.style.cssText = cellCss + `height:${row1H}px;`;

    // row 2
    const leftBottom  = h("div", {}, grid);  leftBottom.style.cssText  = cellCss + `height:${row2H}px;`;
    const rightBottom = h("div", {}, grid);  rightBottom.style.cssText = cellCss + `height:${row2H}px;`;

    // ---------- header with slider + help button ----------
    const header = h("div", {}, leftTop);
    header.style.cssText = "display:flex;gap:12px;align-items:center;margin-bottom:6px;flex:0 0 auto;";

    h("span", { textContent: "Year:", style: "font:13px system-ui;color:#0f172a" }, header);

    const slider = h("input", {}, header);
    slider.type  = "range";
    slider.min   = "0";
    slider.max   = String(YEARS.length - 1);
    slider.value = String(idxYear);
    slider.style.width = "320px";

    const yearLbl = h("span", {
      textContent: YEARS[idxYear],
      style: "font:13px system-ui;color:#0f172a"
    }, header);

    // help button (popover)
    const helpBtn = h("button", { innerText: "How to interact?" }, header);
    Object.assign(helpBtn.style, {
      marginLeft: "auto",
      padding: "6px 10px",
      borderRadius: "10px",
      border: "1px solid #cbd5e1",
      background: "#f8fafc",
      color: "#0f172a",
      cursor: "pointer"
    });
    // container of main parallel
    const mainContainer = h("div", {}, leftTop);
    mainContainer.style.cssText = `flex:1 1 auto;min-height:0;width:${leftW}px;`;

    // ---------- parallel constructor ----------
    function makeParallel(root, width, height, { allowReorderHere }) {
      const svg = d3.select(root).append("svg")
        .attr("width", width).attr("height", height).style("display", "block");

      const m = { top: 20, right: 16, bottom: 10, left: 56 };
      const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
      const iW = width - m.left - m.right;
      const iH = height - m.top - m.bottom;

      const x = d3.scalePoint().domain(DIMS).range([0, iW]).padding(0.5);
      const y = {};
      const dragging = {};
      const getX = d => (dragging[d] != null ? dragging[d] : x(d));
      const line = d3.line().defined(([, v]) => Number.isFinite(v));

      let DATA = [];
      let selected = new Set();

      const layer = g.append("g").attr("fill", "none");
      const hit   = g.append("g").attr("fill", "none");

      function buildY() {
        for (const k of DIMS) {
          const vals = DATA.map(d => +d[k]).filter(v => Number.isFinite(v) && (!useLog || v > 0));
          y[k] = (useLog ? d3.scaleLog() : d3.scaleLinear())
            .domain(useLog ? [Math.max(1e-6, d3.min(vals)), d3.max(vals)] : d3.extent(vals))
            .nice()
            .range([iH, 0]);
        }
      }

      function applySel() {
        if (selected.size === 0) {
          vis.attr("stroke-opacity", .85).attr("stroke-width", 1.2);
        } else {
          vis.attr("stroke-opacity", d => selected.has(d.Country) ? 1 : .08)
             .attr("stroke-width",   d => selected.has(d.Country) ? 2.6 : .7);
        }
      }

      const bw = Math.min(36, Math.max(24, (iW / DIMS.length) * .5));
      const filters = {};
      function brushed(event) {
        g.selectAll(".brush").each(function (dim) {
          const s = d3.brushSelection(this);
          if (s) {
            const y0 = y[dim].invert(s[1]);
            const y1 = y[dim].invert(s[0]);
            filters[dim] = [Math.min(y0, y1), Math.max(y0, y1)];
          } else delete filters[dim];
        });
        const keys = Object.keys(filters);
        const disp = d => {
          for (const k of keys) {
            const v = +d[k] || 0;
            const [a, b] = filters[k];
            if (v < a || v > b) return "none";
          }
          return null;
        };
        vis.style("display", disp);
        hits.style("display", disp);

        if (event && event.type === "end") {
          const rows = DATA.filter(d => disp(d) === null);
          selected = new Set(rows.map(r => r.Country));
          publish("brush");
        }
      }

      let axis = null, vis = null, hits = null;

      function renderAxes() {
        axis = g.selectAll(".axis").data(DIMS, d => d).join(
          e => {
            const a = e.append("g").attr("class", "axis");
            a.append("text")
              .attr("class", "t").attr("y", -8).attr("text-anchor", "middle")
              .style("font", "600 12px system-ui").style("fill", "#111827");
            return a;
          },
          u => u,
          x => x.remove()
        );

        axis.attr("transform", d => `translate(${getX(d)},0)`)
          .each(function (d) {
            const A = d3.select(this);
            A.selectAll("g.tick").remove();
            A.call(d3.axisLeft(y[d]).ticks(6, useLog ? "~g" : undefined));
            A.select("text.t").text(d => d);
            A.selectAll("text").style("fill", "#111827").style("font", "12px system-ui");
            A.selectAll("line,path").style("stroke", "#111827").style("stroke-width", "1.05");
          });

        axis.selectAll(".brush").remove();
        axis.append("g").attr("class", "brush").attr("transform", `translate(${-bw / 2},0)`)
          .each(function (dim) {
            d3.select(this).call(d3.brushY().extent([[0, 0], [bw, iH]]).on("brush end", brushed));
          });

        if (allowReorderHere) {
          const drag = d3.drag()
            .on("start", (ev, dim) => {
              dragging[dim] = getX(dim);
              g.selectAll(".brush").style("pointer-events", "none");
            })
            .on("drag", (ev, dim) => {
              dragging[dim] = Math.max(0, Math.min(iW, ev.x));
              axis.attr("transform", d => `translate(${getX(d)},0)`);
              const L = d => line(DIMS.map(k => [getX(k), y[k](+d[k])]));
              vis.attr("d", L); hits.attr("d", L);
            })
            .on("end", (ev, dim) => {
              DIMS.sort((a, b) => getX(a) - getX(b));
              dragging[dim] = null; delete dragging[dim];
              x.domain(DIMS);
              const Lt = d => line(DIMS.map(k => [x(k), y[k](+d[k])]));
              axis.transition().duration(150).attr("transform", d => `translate(${x(d)},0)`);
              vis.transition().duration(150).attr("d", Lt);
              hits.transition().duration(150).attr("d", Lt);
              g.selectAll(".brush").style("pointer-events", null);
              onReorder && onReorder(DIMS.slice());
            });
          axis.select("text.t").style("cursor", "grab").call(drag);
        }
      }

      function renderData() {
        buildY(); renderAxes();

        const pathD = d => line(DIMS.map(k => [x(k), y[k](+d[k])]));

        vis = layer.selectAll("path").data(DATA, d => d.Country).join("path")
          .attr("d", pathD)
          .attr("fill", "none")
          .attr("stroke", d => color(d.DominantTech || "Solar"))
          .attr("stroke-opacity", .85)
          .attr("stroke-width", 1.2)
          .style("pointer-events", "none");

        hits = hit.selectAll("path").data(DATA, d => d.Country).join("path")
          .attr("d", pathD)
          .attr("stroke", "transparent")
          .attr("stroke-width", 12)
          .style("cursor", "pointer")
          .on("mousemove", (ev, d) => {
            const html =
              `<div style="font-weight:700;margin-bottom:6px">${d.Country}</div>` +
              DIMS.map(k => `${k}: <b>${d3.format(",.0f")(+d[k] || 0)}</b>${normalize ? "" : " MW"}`).join("<br>");
            showTip(ev, html);
          })
          .on("mouseleave", hideTip)
          .on("click", (_, d) => {
            if (selected.has(d.Country)) selected.delete(d.Country);
            else selected.add(d.Country);
            publish("line");
          });

        applySel();
      }

      function publish(type) {
        applySel();
        const keys = [...selected];
        const rows = DATA.filter(d => selected.has(d.Country));
        model.set("selection", { type, keys, rows });
        model.save_changes();
        onSelect && onSelect();
      }

      function setSelected(s) { selected = new Set(s); applySel(); }
      function updateData(d) { DATA = d || []; renderData(); }

      let onSelect = null, onReorder = null;
      return {
        updateData, setSelected,
        setOnSelection: f => (onSelect = f),
        setOnReorder:   f => (onReorder = f)
      };
    }

    // ---------- insight (share lines) ----------
    let updateInsightCursor = null;
    function renderInsight(selectedKeys) {
      rightTop.innerHTML = "";
      const svg = d3.select(rightTop).append("svg")
        .attr("width", rightW).attr("height", row1H).style("display", "block");

      const m = { t: 22, r: 18, b: 34, l: 50 };
      const w = rightW - m.l - m.r;
      const h = row1H  - m.t - m.b;

      const g = svg.append("g").attr("transform", `translate(${m.l},${m.t})`);

      // data
      const keys = new Set(selectedKeys || []);
      const series = DIMS.map(dim => {
        const values = YEARS.map((y, i) => {
          let sumDim = 0, sumAll = 0;
          for (const r of R) {
            if (keys.size && !keys.has(r.label)) continue;
            const v = +r[dim][i] || 0;
            const tot = DIMS.reduce((a, k) => a + (+r[k][i] || 0), 0);
            if (tot > 0) { sumDim += v; sumAll += tot; }
          }
          return { idx: i, year: y, share: (sumAll > 0 ? sumDim / sumAll : 0) };
        });
        return { dim, values };
      });

      const x = d3.scaleLinear().domain([0, YEARS.length - 1]).range([0, w]);
      const y = d3.scaleLinear().domain([0, 1]).nice().range([h, 0]);

      g.append("g")
        .attr("transform", `translate(0,${h})`)
        .call(d3.axisBottom(x).ticks(6).tickFormat(i => YEARS[i]))
        .call(s => s.selectAll("text").style("fill", "#111827").style("font", "12px system-ui"));

      g.append("g")
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".0%")))
        .call(s => s.selectAll("text").style("fill", "#111827").style("font", "12px system-ui"))
        .call(s => s.selectAll("path,line").style("stroke", "#111827").style("stroke-width", "1.05"));

      const l = d3.line().x(d => x(d.idx)).y(d => y(d.share));

      g.selectAll("path.s").data(series).join("path")
        .attr("class", "s")
        .attr("d", d => l(d.values))
        .attr("fill", "none")
        .attr("stroke", d => color(d.dim))
        .attr("stroke-width", 2);

      // points with tooltip
      const pts = g.selectAll("g.pts").data(series).join("g")
        .attr("class", "pts").attr("fill", d => color(d.dim));

      pts.selectAll("circle").data(d => d.values.map(v => ({ ...v, dim: d.dim }))).join("circle")
        .attr("cx", d => x(d.idx)).attr("cy", d => y(d.share)).attr("r", 3.2)
        .on("mousemove", (ev, d) => showTip(ev, `<b>${d.dim}</b> — ${d.year}<br>${d3.format(".1%")(d.share)}`))
        .on("mouseleave", hideTip);

      // vertical rule linked to year
      const rule = g.append("line").attr("y1", 0).attr("y2", h)
        .attr("stroke", "#334155").attr("stroke-dasharray", "3,3");
      rule.attr("x1", x(idxYear)).attr("x2", x(idxYear));
      updateInsightCursor = () => { rule.attr("x1", x(idxYear)).attr("x2", x(idxYear)); };

      // legend: top-right corner
      const lg = svg.append("g")
        .attr("transform", `translate(${m.l + w - 260},${m.t - 12})`);

      // soft background
      lg.append("rect")
        .attr("x", -10).attr("y", -6).attr("width", 260).attr("height", 22)
        .attr("rx", 10).attr("fill", "#f1f5f9").attr("stroke", "#e2e8f0");

      const items = lg.selectAll("g.i").data(DIMS).join("g").attr("class", "i")
        .attr("transform", (d, i) => `translate(${i * 52},0)`);

      items.append("rect").attr("width", 10).attr("height", 10).attr("rx", 2)
        .attr("fill", d => color(d)).attr("y", 3);
      items.append("text").attr("x", 14).attr("y", 12)
        .text(d => d).style("font", "12px system-ui").style("fill", "#334155");

      // title
      svg.append("text")
        .attr("x", 10).attr("y", 16)
        .text("Selected countries")
        .style("font", "600 13px system-ui")
        .style("fill", "#0f172a");
    }
    // ---------- state + synchronization ----------
    let currentData = datasetYear(idxYear);
    let currentSelection = new Set();

    const calcMainH = () => Math.max(140, mainContainer.clientHeight || (row1H - 44));

    // parallel instances
    const main = makeParallel(mainContainer, leftW, calcMainH(), { allowReorderHere: allowReorder });
    const miniHost = h("div", {}, rightBottom);
    miniHost.style.cssText = `width:${rightW}px;height:100%;`;
    const mini = makeParallel(miniHost, rightW, row2H, { allowReorderHere: allowReorder });

    // table
    const tableWrap = h("div", {}, leftBottom);
    tableWrap.style.cssText =
      `height:100%;overflow:auto;border:1px solid #e2e8f0;border-radius:12px;` +
      `background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.04);`;

    function renderTable(selRows) {
      tableWrap.innerHTML = "";
      const wrap = h("div", {}, tableWrap);
      wrap.style.overflow = "auto";
      wrap.style.maxWidth = "100%";

      const rows = selRows || [];
      const cols = ["Country", "Year", ...DIMS, "DominantTech"];

      const tbl = h("table", {}, wrap);
      Object.assign(tbl.style, {
        borderCollapse: "separate",
        borderSpacing: "0",
        width: "100%",
        minWidth: `${220 + (cols.length - 1) * 140}px`
      });

      const thead = tbl.createTHead();
      const trh = thead.insertRow();
      Object.assign(trh.style, {
        position: "sticky",
        top: "0",
        background: "#f8fafc",
        boxShadow: "inset 0 -1px 0 #e2e8f0"
      });

      cols.forEach((c, i) => {
        const th = document.createElement("th");
        th.textContent = c;
        Object.assign(th.style, {
          padding: "10px 12px",
          textAlign: i === 0 ? "left" : "right",
          font: "600 12px system-ui",
          color: "#0f172a"
        });
        if (i === 0) th.style.borderTopLeftRadius = "12px";
        if (i === cols.length - 1) th.style.borderTopRightRadius = "12px";
        trh.appendChild(th);
      });

      const tb = tbl.createTBody();
      const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
      rows.forEach((r, idx) => {
        const tr = tb.insertRow();
        tr.style.background = idx % 2 ? "#f9fafb" : "#ffffff";
        tr.addEventListener("mouseenter", () => tr.style.background = "#eef2ff");
        tr.addEventListener("mouseleave", () => tr.style.background = idx % 2 ? "#f9fafb" : "#ffffff");

        cols.forEach((c, i) => {
          const td = tr.insertCell();
          const v = r[c];
          const isNum = i > 1 && i < cols.length - 1 && Number.isFinite(+v);
          td.textContent = isNum ? nf.format(+v) : (v ?? "—");
          Object.assign(td.style, {
            padding: "10px 12px",
            textAlign: i === 0 ? "left" : "right",
            font: "12px system-ui",
            color: "#0f172a",
            borderBottom: "1px solid #eef2f7"
          });
          if (i === 0) td.style.fontWeight = "600";
        });
      });
    }

    function updateAll() {
      const hNow = calcMainH();
      const svgMain = mainContainer.querySelector("svg");
      if (svgMain) svgMain.setAttribute("height", String(hNow));

      currentData = datasetYear(idxYear);
      main.updateData(currentData);

      const subset = currentData.filter(d => currentSelection.has(d.Country));
      mini.updateData(subset);

      main.setSelected(currentSelection);
      mini.setSelected(currentSelection);

      renderTable(subset);
      renderInsight([...currentSelection]);

      // Never leave tooltips “stuck” after update
      hideTip();
    }

    // selection / reorder hooks
    main.setOnSelection(() => {
      const s = new Set((model.get("selection") || {}).keys || []);
      currentSelection = s; updateAll();
    });
    mini.setOnSelection(() => {
      const s = new Set((model.get("selection") || {}).keys || []);
      currentSelection = s; updateAll();
    });
    const onReorder = (order) => { DIMS = order.slice(); updateAll(); };
    main.setOnReorder(onReorder); mini.setOnReorder(onReorder);

    // year slider
    slider.addEventListener("input", ev => {
      idxYear = +ev.target.value;
      yearLbl.textContent = YEARS[idxYear];
      updateAll();
      if (updateInsightCursor) updateInsightCursor();
    });

    // ---------- Help popover ----------
    const HELP_KEY = "isea_vis_help_v1";
    function showHelp() {
      // close previous instances
      document.querySelectorAll(".isea-help").forEach(n => n.remove());

      const r = helpBtn.getBoundingClientRect();
      const left = Math.min(Math.max(12, r.left - 260), window.innerWidth - 560 - 12);
      const top  = r.bottom + 8;

      const card = h("div", { className: "isea-help" }, document.body);
      Object.assign(card.style, {
        position: "fixed",
        top: `${top}px`,
        left: `${left}px`,
        width: "560px",
        maxWidth: "92vw",
        background: "#0b1220",
        color: "#e5e7eb",
        border: "1px solid #1f2937",
        borderRadius: "14px",
        padding: "16px 18px",
        boxShadow: "0 16px 40px rgba(0,0,0,.35)",
        font: "14px/1.5 system-ui",
        zIndex: 9998
      });

      const caret = h("div", {}, card);
      caret.style.cssText =
        "position:absolute;top:-8px;left:50%;transform:translateX(-50%);" +
        "width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;" +
        "border-bottom:8px solid #0b1220";

      card.innerHTML += `
        <div style="font:600 18px system-ui; margin:4px 0 12px; color:#fff">How to interact</div>
        <ul style="margin:0 0 12px 18px; padding:0;">
          <li><b>Drag the axis title</b> to <b>reorder</b>.</li>
          <li><b>Brush</b> (drag on an axis) to <b>filter</b> by range.</li>
          <li><b>Click</b> a line to (de)select; <b>Shift+Click</b> for multiple.</li>
          <li>Use the <b>year slider</b> (above) to change the period.</li>
          <li>Axis <b>titles</b> have <b>tooltips</b> with explanation.</li>
        </ul>
        <div style="display:flex; align-items:center; gap:12px; justify-content:space-between; margin-top:8px;">
          <label style="display:flex; align-items:center; gap:10px; user-select:none; color:#cbd5e1;">
            <input id="help-dont" type="checkbox" style="width:16px;height:16px;" />
            <span>Do not show again</span>
          </label>
          <button id="help-ok"
            style="padding:8px 14px;border-radius:10px;border:1px solid #1f2937;background:#111827;color:#fff;cursor:pointer;">
            OK
          </button>
        </div>
      `;

      const close = () => {
        const dont = card.querySelector("#help-dont")?.checked;
        if (dont) localStorage.setItem(HELP_KEY, "1");
        card.remove();
      };

      const outside = (e) => { if (!card.contains(e.target) && e.target !== helpBtn) { cleanup(); close(); } };
      const esc = (e) => { if (e.key === "Escape") { cleanup(); close(); } };
      const cleanup = () => {
        document.removeEventListener("click", outside, true);
        window.removeEventListener("keydown", esc, true);
      };
      setTimeout(() => {
        document.addEventListener("click", outside, true);
        window.addEventListener("keydown", esc, true);
      }, 0);

      card.querySelector("#help-ok").addEventListener("click", () => { cleanup(); close(); });
    }

    helpBtn.addEventListener("click", showHelp);
    setTimeout(() => { if (localStorage.getItem(HELP_KEY) !== "1") showHelp(); }, 500);

    // ---------- responsive redraw ----------
    const ro = new ResizeObserver(() => {
      const w = Math.max(el.clientWidth || 0, 640);
      if (w !== targetW) draw();
    });
    ro.observe(el);

    // ---------- first render ----------
    updateAll();
  }

  model.on("change:data", draw);
  model.on("change:options", draw);
  draw();
}
