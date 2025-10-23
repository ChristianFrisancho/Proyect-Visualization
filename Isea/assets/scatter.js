// Isea/assets/scatter.js
// Compact scatter with nice axes, color legend toggle, size encoding, tooltip, and JS->PY selection.
export function render({ model, el }) {
  // ---------- helpers ----------
  const NS = "http://www.w3.org/2000/svg";
  const $ = (name) => document.createElementNS(NS, name);

  // 1-2-5 nice ticks
  const niceStep = (span, n) => {
    const raw = span / Math.max(1, n || 5);
    const p10 = Math.pow(10, Math.floor(Math.log10(raw)));
    const m = raw / p10;
    const k = m >= 5 ? 5 : m >= 2 ? 2 : 1;
    return k * p10;
  };
  const makeTicks = (min, max, n) => {
    const step = niceStep(max - min, n);
    const a = Math.floor(min / step) * step;
    const b = Math.ceil(max / step) * step;
    const out = [];
    for (let v = a; v <= b + 1e-9; v += step) out.push(+v.toFixed(12));
    return { a, b, step, ticks: out };
  };
  const fmtTick = (step) =>
    new Intl.NumberFormat(undefined, {
      maximumFractionDigits: Math.max(0, -Math.floor(Math.log10(step))) + 2,
    });

  const scheme10 = [
    "#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f",
    "#edc948","#b07aa1","#ff9da7","#9c755f","#bab0ab"
  ];

  // ---------- drawing ----------
  function draw() {
    el.innerHTML = "";
    const svg = $("svg");
    el.appendChild(svg);

    // data & options
    const data = model.get("data") ?? [];
    const o = Object.assign(
      {
        x: "x", y: "y", key: "id",
        color: null, size: null, label: null,
        logX: false, logY: false,

        width: 720, height: 420,
        margin: { t: 28, r: 24, b: 56, l: 70 },

        grid: true, xTicks: 8, yTicks: 8,
        radius: 5, opacity: 0.92,
        colors: scheme10, colorMap: null,
        legend: true, legendPosition: "right",

        title: "", xLabel: null, yLabel: null
      },
      model.get("options") || {}
    );

    // auto labels
    if (!o.xLabel) o.xLabel = String(o.x);
    if (!o.yLabel) o.yLabel = String(o.y);

    // add extra right space if legend on right
    const extraRight = o.legend && o.legendPosition === "right" ? 120 : 0;
    svg.setAttribute("width", o.width + extraRight);
    svg.setAttribute("height", o.height);

    const m = o.margin;
    const W = o.width - m.l - m.r;
    const H = o.height - m.t - m.b;

    // extents (respect log > 0)
    const xVals = data.map(d => +d[o.x]).filter(v => Number.isFinite(v) && (!o.logX || v > 0));
    const yVals = data.map(d => +d[o.y]).filter(v => Number.isFinite(v) && (!o.logY || v > 0));
    let x0 = xVals.length ? Math.min(...xVals) : 0, x1 = xVals.length ? Math.max(...xVals) : 1;
    let y0 = yVals.length ? Math.min(...yVals) : 0, y1 = yVals.length ? Math.max(...yVals) : 1;
    if (x0 === x1) { x0 -= 1; x1 += 1; }
    if (y0 === y1) { y0 -= 1; y1 += 1; }

    // nice ticks
    const XT = makeTicks(x0, x1, o.xTicks);
    const YT = makeTicks(y0, y1, o.yTicks);
    x0 = o.logX ? Math.max(1e-12, x0) : XT.a; x1 = o.logX ? x1 : XT.b;
    y0 = o.logY ? Math.max(1e-12, y0) : YT.a; y1 = o.logY ? y1 : YT.b;

    // scales
    const X = o.logX
      ? (v) => m.l + (Math.log(v) - Math.log(x0)) / (Math.log(x1) - Math.log(x0)) * W
      : (v) => m.l + (v - x0) / (x1 - x0) * W;
    const Y = o.logY
      ? (v) => m.t + H - (Math.log(v) - Math.log(y0)) / (Math.log(y1) - Math.log(y0)) * H
      : (v) => m.t + H - (v - y0) / (y1 - y0) * H;

    // groups
    const gGrid = $("g"), gAxes = $("g"), gDots = $("g"), gLegend = $("g");
    svg.append(gGrid, gAxes, gDots, gLegend);

    // grid
    if (o.grid && !o.logX) XT.ticks.forEach(v => {
      const L = $("line"); L.setAttribute("x1", X(v)); L.setAttribute("y1", m.t);
      L.setAttribute("x2", X(v)); L.setAttribute("y2", m.t+H);
      L.setAttribute("stroke", "#e6e6e6"); gGrid.appendChild(L);
    });
    if (o.grid && !o.logY) YT.ticks.forEach(v => {
      const L = $("line"); L.setAttribute("x1", m.l); L.setAttribute("y1", Y(v));
      L.setAttribute("x2", m.l+W); L.setAttribute("y2", Y(v));
      L.setAttribute("stroke", "#e6e6e6"); gGrid.appendChild(L);
    });

    // axes
    const xAxis = $("line"); xAxis.setAttribute("x1", m.l); xAxis.setAttribute("y1", m.t+H);
    xAxis.setAttribute("x2", m.l+W); xAxis.setAttribute("y2", m.t+H);
    xAxis.setAttribute("stroke", "#444"); xAxis.setAttribute("stroke-width", "1.25"); gAxes.appendChild(xAxis);

    const yAxis = $("line"); yAxis.setAttribute("x1", m.l); yAxis.setAttribute("y1", m.t);
    yAxis.setAttribute("x2", m.l); yAxis.setAttribute("y2", m.t+H);
    yAxis.setAttribute("stroke", "#444"); yAxis.setAttribute("stroke-width", "1.25"); gAxes.appendChild(yAxis);

    const tfx = fmtTick(XT.step), tfy = fmtTick(YT.step);
    if (!o.logX) XT.ticks.forEach(v => {
      const l = $("line"); l.setAttribute("x1", X(v)); l.setAttribute("x2", X(v));
      l.setAttribute("y1", m.t+H); l.setAttribute("y2", m.t+H+6);
      l.setAttribute("stroke", "#444"); gAxes.appendChild(l);
      const t = $("text"); t.setAttribute("x", X(v)); t.setAttribute("y", m.t+H+22);
      t.setAttribute("text-anchor","middle"); t.setAttribute("font-size","12");
      t.textContent = tfx.format(v); gAxes.appendChild(t);
    });
    if (!o.logY) YT.ticks.forEach(v => {
      const l = $("line"); l.setAttribute("x1", m.l-6); l.setAttribute("x2", m.l);
      l.setAttribute("y1", Y(v)); l.setAttribute("y2", Y(v));
      l.setAttribute("stroke", "#444"); gAxes.appendChild(l);
      const t = $("text"); t.setAttribute("x", m.l-10); t.setAttribute("y", Y(v)+4);
      t.setAttribute("text-anchor","end"); t.setAttribute("font-size","12");
      t.textContent = tfy.format(v); gAxes.appendChild(t);
    });

    // labels + title
    if (o.title) { const t = $("text"); t.setAttribute("x", m.l + W/2); t.setAttribute("y", m.t-10); t.setAttribute("text-anchor","middle"); t.textContent = o.title; gAxes.appendChild(t); }
    { const t = $("text"); t.setAttribute("x", m.l + W/2); t.setAttribute("y", m.t+H+40); t.setAttribute("text-anchor","middle"); t.textContent = o.xLabel; gAxes.appendChild(t); }
    { const t = $("text"); t.setAttribute("x", m.l-46); t.setAttribute("y", m.t+H/2); t.setAttribute("text-anchor","middle"); t.setAttribute("transform", `rotate(-90 ${m.l-46} ${m.t+H/2})`); t.textContent = o.yLabel; gAxes.appendChild(t); }

    // color + size
    const cats = o.color ? [...new Set(data.map(d => d[o.color]).filter(v => v!=null))] : [];
    const cmap = Object.assign(
      Object.fromEntries(cats.map((c,i)=>[String(c), (o.colors[i % o.colors.length]) ])),
      o.colorMap || {}
    );
    const colorOf = o.color ? (d)=> cmap[String(d[o.color])] : ()=>"#4f46e5";

    let S = ()=>o.radius;
    if (o.size) {
      const sVals = data.map(d => +d[o.size] || 0);
      const s0 = Math.min(...sVals), s1 = Math.max(...sVals);
      const r0 = 3, r1 = 16;
      S = (d) => {
        const v = +d[o.size] || 0;
        if (s1 === s0) return (r0 + r1)/2;
        return r0 + (v - s0) / (s1 - s0) * (r1 - r0);
      };
    }

    // tooltip
    const tipHost = el.appendChild(document.createElement("div"));
    tipHost.style.position = "relative";
    const tip = document.createElement("div");
    Object.assign(tip.style, {
      position: "absolute", zIndex: "9999", pointerEvents: "none", background: "rgba(17,24,39,.92)",
      color: "#fff", padding: "6px 8px", borderRadius: "6px", font: "12px sans-serif",
      boxShadow: "0 4px 16px rgba(0,0,0,.25)", opacity: 0, transition: "opacity .12s",
      whiteSpace: "pre"
    });
    tipHost.appendChild(tip);
    const nf = new Intl.NumberFormat();
    const tipHTML = (d) => {
      const head = o.label && d[o.label] != null ? `${d[o.label]}\n` : "";
      const lines = [
        `${o.x}: ${nf.format(+d[o.x]||0)}`,
        `${o.y}: ${nf.format(+d[o.y]||0)}`
      ];
      if (o.size) lines.push(`${o.size}: ${nf.format(+d[o.size]||0)}`);
      if (o.color) lines.push(`${o.color}: ${d[o.color]}`);
      return head + lines.join("\n");
    };

    // draw points
    const points = [];
    data.forEach((d, i) => {
      const xv = +d[o.x], yv = +d[o.y];
      if (!Number.isFinite(xv) || !Number.isFinite(yv)) return;
      if ((o.logX && xv <= 0) || (o.logY && yv <= 0)) return;

      const c = $("circle");
      const cx = X(xv), cy = Y(yv);
      c.setAttribute("cx", cx); c.setAttribute("cy", cy);
      c.setAttribute("r", S(d));
      c.setAttribute("fill", colorOf(d));
      c.style.opacity = o.opacity;

      c.addEventListener("mouseenter", (ev) => {
        c.setAttribute("stroke", "#111"); c.setAttribute("stroke-width", "1.2");
        tip.textContent = tipHTML(d); tip.style.opacity = 1;
        tip.style.left = (ev.clientX + 12) + "px";
        tip.style.top  = (ev.clientY + 12) + "px";
        tip.style.position = "fixed"; // instead of absolute
      });
      c.addEventListener("mouseleave", () => {
        c.removeAttribute("stroke"); c.removeAttribute("stroke-width");
        tip.style.opacity = 0;
      });
      c.addEventListener("mousemove", (ev) => {
        tip.style.left = (ev.clientX + 12) + "px";
        tip.style.top  = (ev.clientY + 12) + "px";
        tip.style.position = "fixed"; // instead of absolute
      });
      c.addEventListener("click", () => {
        const key = o.key && d[o.key] != null ? d[o.key] : (d.name ?? i);
        model.set("selection", { type: "point", keys: [key], rows: [d] });
        model.save_changes();
      });

      gDots.appendChild(c);
      points.push({ el: c, d, cx, cy, key: o.key && d[o.key] != null ? d[o.key] : (d.name ?? i) });
    });

    // brush select (drag rectangle)
    const brush = $("rect");
    brush.setAttribute("fill", "rgba(0,0,0,0.08)");
    brush.setAttribute("stroke", "rgba(0,0,0,0.25)");
    brush.style.display = "none";
    svg.appendChild(brush);
    let start = null, moved = false;
    const clearSel = () => { model.set("selection", {}); model.save_changes(); };

    svg.addEventListener("mousedown",(e)=>{
      const r = svg.getBoundingClientRect();
      start = { x: e.clientX - r.left, y: e.clientY - r.top }; moved = false;
      brush.style.display = "block";
      brush.setAttribute("x", start.x); brush.setAttribute("y", start.y);
      brush.setAttribute("width", 0); brush.setAttribute("height", 0);
    });
    svg.addEventListener("mousemove",(e)=>{
      if (!start) return; moved = true;
      const r = svg.getBoundingClientRect(); const x = e.clientX - r.left, y = e.clientY - r.top;
      const x0 = Math.min(start.x, x), y0 = Math.min(start.y, y);
      brush.setAttribute("x", x0); brush.setAttribute("y", y0);
      brush.setAttribute("width", Math.abs(x - start.x)); brush.setAttribute("height", Math.abs(y - start.y));
    });
    svg.addEventListener("mouseup",()=>{
      if (!start) return;
      const x0 = +brush.getAttribute("x"), y0 = +brush.getAttribute("y");
      const x1 = x0 + (+brush.getAttribute("width")), y1 = y0 + (+brush.getAttribute("height"));
      brush.style.display = "none"; const prev = start; start = null;
      if (!moved || (x1 - x0 < 3 && y1 - y0 < 3)) { clearSel(); return; }
      const sel = points.filter(p => p.cx>=x0 && p.cx<=x1 && p.cy>=y0 && p.cy<=y1);
      model.set("selection", { type: "set", keys: sel.map(p=>p.key), rows: sel.map(p=>p.d) });
      model.save_changes();
    });
    svg.addEventListener("dblclick", clearSel);
    window.addEventListener("keydown", (e)=>{ if (e.key === "Escape") clearSel(); });

    // selection highlight
    function applySelection() {
      const s = model.get("selection") || {};
      if (!s.type) { points.forEach(p => p.el.style.opacity = o.opacity); return; }
      const keep = new Set((s.keys || []).map(String));
      if (!keep.size) { points.forEach(p => p.el.style.opacity = o.opacity); return; }
      points.forEach(p => p.el.style.opacity = keep.has(String(p.key)) ? 1.0 : 0.2);
    }
    model.on("change:selection", applySelection); applySelection();

    // legend with toggle
    if (o.legend && cats.length) {
      const pad = 10, item = 14, gap = 6;
      const startX = m.l + W + 16, startY = m.t + pad;
      const active = new Set(cats);

      cats.forEach((cat, i) => {
        const y = startY + i * (item + gap);
        const swatch = $("rect");
        swatch.setAttribute("x", startX); swatch.setAttribute("y", y - item + 2);
        swatch.setAttribute("width", item); swatch.setAttribute("height", item);
        swatch.setAttribute("fill", cmap[String(cat)]);
        swatch.style.cursor = "pointer";
        gLegend.appendChild(swatch);

        const lbl = $("text");
        lbl.setAttribute("x", startX + item + 8); lbl.setAttribute("y", y + 2);
        lbl.setAttribute("dominant-baseline","middle"); lbl.setAttribute("text-anchor","start");
        lbl.textContent = String(cat); lbl.style.cursor = "pointer";
        gLegend.appendChild(lbl);

        const toggle = () => {
          if (active.has(cat)) active.delete(cat); else active.add(cat);
          const on = (d) => !o.color || active.has(d[o.color]);
          points.forEach(p => p.el.style.opacity = on(p.d) ? o.opacity : 0.08);
          swatch.setAttribute("opacity", active.has(cat) ? 1 : 0.25);
          lbl.setAttribute("opacity", active.has(cat) ? 1 : 0.35);
        };
        swatch.addEventListener("click", toggle);
        lbl.addEventListener("click", toggle);
      });
    }
  }

  model.on("change:data", draw);
  model.on("change:options", draw);
  draw();
}

