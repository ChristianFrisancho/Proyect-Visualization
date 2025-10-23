export function render({ model, el }) {
  el.innerHTML = "";
  const SVGNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(SVGNS, "svg");
  el.appendChild(svg);

  function draw() {
    const data = model.get("data") ?? [];
    const opts = {
      width: 640, height: 360, x: "x", y: "y",
      key: "id",              // field to use as the stable key if present
      ...(model.get("options") || {})
    };
    svg.setAttribute("width", opts.width);
    svg.setAttribute("height", opts.height);

    const m = { t:20, r:20, b:30, l:40 };
    const w = Math.max(1, opts.width  - m.l - m.r);
    const h = Math.max(1, opts.height - m.t - m.b);

    const xs = data.map(d => +d[opts.x]).filter(Number.isFinite);
    const ys = data.map(d => +d[opts.y]).filter(Number.isFinite);
    let xmin = xs.length ? Math.min(...xs) : 0, xmax = xs.length ? Math.max(...xs) : 1;
    let ymin = ys.length ? Math.min(...ys) : 0, ymax = ys.length ? Math.max(...ys) : 1;
    if (xmin === xmax) { xmin -= 1; xmax += 1; }
    if (ymin === ymax) { ymin -= 1; ymax += 1; }

    const X = v => m.l + ((v - xmin)/(xmax - xmin)) * w;
    const Y = v => m.t + h - ((v - ymin)/(ymax - ymin)) * h;

    // clear
    while (svg.lastChild) svg.removeChild(svg.lastChild);

    // axes
    const line = (x1,y1,x2,y2,stroke="#888")=>{
      const L=document.createElementNS(SVGNS,"line");
      L.setAttribute("x1",x1); L.setAttribute("y1",y1);
      L.setAttribute("x2",x2); L.setAttribute("y2",y2);
      L.setAttribute("stroke",stroke); svg.appendChild(L);
    };
    line(m.l, m.t+h, m.l+w, m.t+h);   // x
    line(m.l, m.t,   m.l,   m.t+h);   // y

    // points
    const gDots = document.createElementNS(SVGNS, "g");
    svg.appendChild(gDots);
    const dots = []; // {el, d, cx, cy, key}
    data.forEach((d, i) => {
      const cx = X(+d[opts.x]), cy = Y(+d[opts.y]);
      if (!Number.isFinite(cx) || !Number.isFinite(cy)) return;
      const key = (opts.key && d[opts.key] != null) ? d[opts.key] : (d.name ?? i);
      const c = document.createElementNS(SVGNS, "circle");
      c.setAttribute("class","dot");
      c.setAttribute("cx", cx); c.setAttribute("cy", cy); c.setAttribute("r", 4);
      c.setAttribute("fill","black");
      c.style.opacity = 1;
      c.addEventListener("click", () => {
        model.set("selection", { type: "point", keys: [key], rows: [d] });
        model.save_changes();
      });
      gDots.appendChild(c);
      dots.push({ el: c, d, cx, cy, key });
    });

    // brush rect
    const brush = document.createElementNS(SVGNS,"rect");
    brush.setAttribute("fill","rgba(0,0,0,0.08)");
    brush.setAttribute("stroke","rgba(0,0,0,0.25)");
    brush.style.display = "none";
    svg.appendChild(brush);

    let start=null, moved=false;

    const clearSelection = () => {
      model.set("selection", {});
      model.save_changes();
    };

    svg.addEventListener("mousedown", (evt)=>{
      const r = svg.getBoundingClientRect();
      start = { x: evt.clientX - r.left, y: evt.clientY - r.top };
      moved = false;
      brush.style.display = "block";
      brush.setAttribute("x", start.x);
      brush.setAttribute("y", start.y);
      brush.setAttribute("width", 0);
      brush.setAttribute("height", 0);
    });

    svg.addEventListener("mousemove", (evt)=>{
      if (!start) return;
      moved = true;
      const r = svg.getBoundingClientRect();
      const x = evt.clientX - r.left, y = evt.clientY - r.top;
      const x0 = Math.min(start.x, x), y0 = Math.min(start.y, y);
      const x1 = Math.max(start.x, x), y1 = Math.max(start.y, y);
      brush.setAttribute("x", x0); brush.setAttribute("y", y0);
      brush.setAttribute("width", x1 - x0); brush.setAttribute("height", y1 - y0);
    });

    svg.addEventListener("mouseup", ()=>{
      if (!start) return;
      const x0 = +brush.getAttribute("x"), y0 = +brush.getAttribute("y");
      const w0 = +brush.getAttribute("width"), h0 = +brush.getAttribute("height");
      start = null; brush.style.display = "none";

      // tiny drag ⇒ clear
      if (!moved || (w0 < 3 && h0 < 3)) { clearSelection(); return; }

      const x1 = x0 + w0, y1 = y0 + h0;

      // choose points inside the pixel-rect
      const selected = dots.filter(p => (
        p.cx >= x0 && p.cx <= x1 && p.cy >= y0 && p.cy <= y1
      ));

      const keys = selected.map(p => p.key);
      const rows = selected.map(p => p.d);

      model.set("selection", { type: "set", keys, rows });
      model.save_changes();
    });

    svg.addEventListener("dblclick", clearSelection);
    window.addEventListener("keydown", e => { if (e.key === "Escape") clearSelection(); });

    function applySelection() {
      const s = model.get("selection") || {};
      if (!s.type) { dots.forEach(p => p.el.style.opacity = 1); return; }
      const keep = new Set((s.keys || []).map(String));
      if (keep.size) {
        dots.forEach(p => p.el.style.opacity = keep.has(String(p.key)) ? 1 : 0.2);
      } else {
        dots.forEach(p => p.el.style.opacity = 1);
      }
    }

    model.on("change:selection", applySelection);
    applySelection();
  }

  model.on("change:data", draw);
  model.on("change:options", draw);
  draw();
}
