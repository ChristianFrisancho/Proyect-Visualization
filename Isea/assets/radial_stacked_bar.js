// RadialStackedBar ESM module para anywidget

export function render({ model, el }) {
  // ========== Crear estructura HTML ==========
  const container = document.createElement("div");
  container.style.cssText = `
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  `;

  // Título
  const title = document.createElement("div");
  title.style.cssText = `
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
  `;
  container.appendChild(title);

  // Barra de controles
  const controls = document.createElement("div");
  controls.style.cssText = `
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 8px;
    background: #f9fafb;
    border-radius: 8px;
  `;

  const yearLabel = document.createElement("span");
  yearLabel.textContent = "Año:";
  yearLabel.style.cssText = `font-weight: 500; color: #374151;`;
  controls.appendChild(yearLabel);

  const slider = document.createElement("input");
  slider.type = "range";
  slider.style.cssText = `width: 300px; cursor: pointer;`;
  controls.appendChild(slider);

  const yearValue = document.createElement("span");
  yearValue.style.cssText = `
    min-width: 60px;
    font-weight: 600;
    color: #1f2937;
  `;
  controls.appendChild(yearValue);

  // Botones de ordenamiento
  const sortBtn = document.createElement("button");
  sortBtn.textContent = "📊 Ordenar por tamaño";
  sortBtn.style.cssText = `
    padding: 8px 12px;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  `;

  const resetBtn = document.createElement("button");
  resetBtn.textContent = "↺ Restaurar orden";
  resetBtn.style.cssText = `
    padding: 8px 12px;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  `;

  controls.appendChild(sortBtn);
  controls.appendChild(resetBtn);
  container.appendChild(controls);

  // Contenedor SVG
  const svgContainer = document.createElement("div");
  svgContainer.style.cssText = `
    display: flex;
    justify-content: center;
    align-items: center;
  `;
  container.appendChild(svgContainer);

  // Estado
  const status = document.createElement("div");
  status.style.cssText = `
    font-size: 12px;
    color: #64748b;
    text-align: center;
    min-height: 20px;
  `;
  container.appendChild(status);

  // Panel de selección
  const selectionPanel = document.createElement("div");
  selectionPanel.style.cssText = `
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
  `;

  const selectionTitle = document.createElement("div");
  selectionTitle.style.cssText = `
    font-weight: 600;
    color: #374151;
    margin-bottom: 8px;
  `;
  selectionPanel.appendChild(selectionTitle);

  const selectionTable = document.createElement("div");
  selectionTable.style.cssText = `
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
  `;
  selectionPanel.appendChild(selectionTable);

  container.appendChild(selectionPanel);
  el.appendChild(container);

  // ========== Función render ==========
  async function draw() {
    try {
      // Importar D3
      const d3Module = await import("https://cdn.jsdelivr.net/npm/d3@7/+esm");
      const d3 = d3Module.default ?? d3Module;

      console.log("✅ D3 cargado:", d3.version);

      // Obtener datos del modelo
      const pack = model.get("data");
      const opts = model.get("options");

      if (!pack || !pack.years || !pack.records) {
        status.textContent = "⏳ Esperando datos...";
        return;
      }

      const YEARS = pack.years;
      const CATEGORIES = pack.categories || [];
      const DATA_ORIGINAL = JSON.parse(JSON.stringify(pack.records)); // Deep copy
      let DATA = JSON.parse(JSON.stringify(pack.records));

      // Configuración
      const W = opts.width || 900;
      const H = opts.height || 900;
      const innerRadius = opts.inner_radius || 200;
      const padAngle = opts.pad_angle || 0.015;
      const colorScheme = opts.color_scheme || "schemeSpectral";
      const sortOnClick = opts.sort_on_click !== false;
      const chartTitle = opts.title || "Radial Stacked Bar";
      let customColors = opts.custom_colors;

      // Convertir set a array si es necesario
      if (customColors instanceof Set) {
        customColors = Array.from(customColors);
      }

      // Estado
      let sorted = false;
      let idxYear = YEARS.indexOf(opts.year_start || YEARS[YEARS.length - 1]);
      if (idxYear < 0) idxYear = YEARS.length - 1;

      // Actualizar controles
      slider.min = "0";
      slider.max = String(YEARS.length - 1);
      slider.value = String(idxYear);
      yearValue.textContent = YEARS[idxYear];
      title.textContent = `${chartTitle} — ${YEARS[idxYear]}`;

      // ========== Scales & Colors ==========
      const outerRadius = Math.min(W, H) / 2 - 60;

      // Color scale
      let colorScale;
      if (customColors && customColors.length > 0) {
        colorScale = d3
          .scaleOrdinal()
          .domain(CATEGORIES)
          .range(customColors);
      } else {
        const numColors = CATEGORIES.length;
        let colorRange;

        if (colorScheme === "schemeSpectral") {
          if (numColors <= 3) {
            colorRange = d3.schemeSpectral[3];
          } else if (numColors <= 11) {
            colorRange = d3.schemeSpectral[numColors];
          } else {
            colorRange = d3.schemeSpectral[11];
          }
        } else if (colorScheme.startsWith("scheme")) {
          try {
            colorRange =
              d3[colorScheme][Math.max(Math.min(numColors, 12), 3)] ||
              d3.schemeCategory10;
          } catch (e) {
            colorRange = d3.schemeCategory10;
          }
        } else {
          colorRange = d3.schemeCategory10;
        }

        colorScale = d3
          .scaleOrdinal()
          .domain(CATEGORIES)
          .range(colorRange);
      }

      // Formatters
      const fmt = d3.format(",.1f");
      const fmtPct = d3.format(".1%");

      // ========== SVG Setup ==========
      svgContainer.innerHTML = "";

      const svg = d3
        .select(svgContainer)
        .append("svg")
        .attr("width", W)
        .attr("height", H)
        .attr("viewBox", [-W / 2, -H / 2, W, H])
        .style("width", "100%")
        .style("height", "auto")
        .style("font", "11px sans-serif");

      const g = svg.append("g");

      // Tooltip
      const tip = document.createElement("div");
      Object.assign(tip.style, {
        position: "fixed",
        zIndex: "9999",
        pointerEvents: "none",
        background: "rgba(17,24,39,.95)",
        color: "#fff",
        padding: "10px 12px",
        borderRadius: "8px",
        font: "12px/1.35 sans-serif",
        boxShadow: "0 8px 24px rgba(0,0,0,.35)",
        opacity: "0",
        transition: "opacity .12s",
      });
      document.body.appendChild(tip);

      function showTip(event, category, value, total) {
        const pct = total > 0 ? value / total : 0;
        tip.innerHTML = `
          <div style="font-weight:700;margin-bottom:6px">${category}</div>
          <div>Valor: <strong>${fmt(value)}</strong> MW</div>
          <div style="opacity:0.9">Porcentaje: <strong>${fmtPct(pct)}</strong></div>
        `;
        tip.style.opacity = "1";
        tip.style.left = event.clientX + 14 + "px";
        tip.style.top = event.clientY + 14 + "px";
      }

      function hideTip() {
        tip.style.opacity = "0";
      }

      // ========== Render Function ==========
      let selected = new Set();

      function render(animate = false, duration = 1200) {
        console.log("🎨 Renderizando:", {
          animate,
          duration,
          groups: DATA.length,
        });

        // Update scales
        const x = d3
          .scaleBand()
          .domain(DATA.map((d) => d.group))
          .range([0, 2 * Math.PI])
          .align(0);

        const yMax = d3.max(DATA, (d) =>
          d3.sum(CATEGORIES, (k) => +d[k][idxYear] || 0)
        );
        const y = d3
          .scaleRadial()
          .domain([0, yMax])
          .range([innerRadius, outerRadius]);

        const arc = d3
          .arc()
          .innerRadius((d) => y(d[0]))
          .outerRadius((d) => y(d[1]))
          .startAngle((d) => x(d.data.group))
          .endAngle((d) => x(d.data.group) + x.bandwidth())
          .padAngle(padAngle)
          .padRadius(innerRadius);

        // Stack
        const dataForStack = DATA.map((d) => {
          const obj = { group: d.group };
          for (const cat of CATEGORIES) {
            obj[cat] = d[cat][idxYear] || 0;
          }
          return obj;
        });

        const series = d3.stack().keys(CATEGORIES)(dataForStack);

        // Bind series
        const seriesGroups = g
          .selectAll(".series-group")
          .data(series, (d) => d.key);

        seriesGroups.exit().remove();

        const seriesEnter = seriesGroups
          .enter()
          .append("g")
          .attr("class", "series-group")
          .attr("fill", (d) => colorScale(d.key));

        const allSeries = seriesEnter.merge(seriesGroups);

        // Render paths
        allSeries.each(function (seriesData) {
          const paths = d3
            .select(this)
            .selectAll("path")
            .data(seriesData, (d) => d.data.group);

          paths.exit().remove();

          const pathsEnter = paths
            .enter()
            .append("path")
            .attr("stroke", "#fff")
            .attr("stroke-width", 1)
            .style("opacity", 0.85);

          const allPaths = pathsEnter.merge(paths);

          allPaths
            .transition()
            .duration(animate ? duration : 0)
            .attr("d", arc)
            .on("end", function (d) {
              d3.select(this)
                .on("mousemove", function (event) {
                  const total = d3.sum(
                    CATEGORIES,
                    (k) => +d.data[k][idxYear] || 0
                  );
                  showTip(
                    event,
                    d.key,
                    d.data[d.key][idxYear] || 0,
                    total
                  );
                })
                .on("mouseleave", hideTip)
                .on("click", (event) => {
                  event.stopPropagation();
                  toggleSelect(d.data.group);
                });
            });
        });

        // Labels
        const labelGroups = g
          .selectAll(".label-group")
          .data(DATA, (d) => d.group);

        labelGroups.exit().remove();

        const labelEnter = labelGroups
          .enter()
          .append("g")
          .attr("class", "label-group")
          .attr("text-anchor", "middle");

        const allLabels = labelEnter.merge(labelGroups);

        allLabels
          .transition()
          .duration(animate ? duration : 0)
          .attr("transform", (d) => {
            const angle = ((x(d.group) + x.bandwidth() / 2) * 180) / Math.PI - 90;
            return `rotate(${angle})translate(${outerRadius + 10},0)`;
          });

        labelEnter
          .append("line")
          .attr("x1", 0)
          .attr("x2", 0)
          .attr("y1", 0)
          .attr("y2", 7)
          .attr("stroke", "#999")
          .attr("stroke-width", 1);

        labelEnter
          .append("text")
          .style("font-size", "10px")
          .style("fill", "#333");

        allLabels
          .select("text")
          .transition()
          .duration(animate ? duration : 0)
          .attr("transform", (d) => {
            const angle = x(d.group) + x.bandwidth() / 2;
            return ((angle + Math.PI / 2) % (2 * Math.PI)) < Math.PI
              ? "rotate(90)translate(10,-2)"
              : "rotate(-90)translate(-10,-2)";
          })
          .text((d) => d.group);

        // Grid circles
        const yTicks = y.ticks(5).slice(1);
        g.selectAll(".grid-circle").remove();

        g.selectAll(".grid-circle")
          .data(yTicks)
          .enter()
          .append("circle")
          .attr("class", "grid-circle")
          .attr("r", (d) => y(d))
          .style("fill", "none")
          .style("stroke", "#ddd")
          .style("stroke-dasharray", "2,4")
          .style("stroke-width", 0.5);

        // Grid labels
        g.selectAll(".grid-label").remove();

        g.selectAll(".grid-label")
          .data(yTicks)
          .enter()
          .append("text")
          .attr("class", "grid-label")
          .attr("y", (d) => -y(d))
          .attr("dy", "-0.35em")
          .attr("text-anchor", "middle")
          .attr("fill", "#666")
          .attr("stroke", "#fff")
          .attr("stroke-width", 3)
          .attr("stroke-linejoin", "round")
          .attr("paint-order", "stroke")
          .style("font-size", "9px")
          .text((d) => d3.format("~s")(d))
          .clone(true)
          .attr("stroke", "none");

        updateSelectionStyles();
      }

      // ========== Selection ==========
      function toggleSelect(group) {
        if (selected.has(group)) {
          selected.delete(group);
        } else {
          selected.add(group);
        }
        updateSelectionStyles();
        syncSelection();
      }

      function updateSelectionStyles() {
        g.selectAll(".series-group path").attr("opacity", (d) => {
          if (selected.size === 0) return 0.85;
          const inGroup = DATA.find((r) => r.group === d.data.group);
          return selected.has(inGroup.group) ? 1 : 0.15;
        });

        status.textContent = `Año: ${YEARS[idxYear]} · Seleccionados: ${selected.size} / ${DATA.length}`;
      }

      function syncSelection() {
        const rows = DATA.filter((d) => selected.has(d.group)).map((d) => {
          const obj = { group: d.group };
          for (const cat of CATEGORIES) {
            obj[cat] = d[cat][idxYear] || 0;
          }
          return obj;
        });

        model.set("selection", {
          type: "segment",
          keys: Array.from(selected),
          rows: rows,
        });

        renderSelectionTable(rows);
      }

      function renderSelectionTable(rows) {
        if (rows.length === 0) {
          selectionTitle.textContent = "Sin selección";
          selectionTable.innerHTML =
            '<div style="color:#9ca3af;padding:8px;">Haz clic en segmentos para seleccionar.</div>';
          return;
        }

        selectionTitle.textContent = `Selección (${rows.length} puntos)`;

        const cols = ["group", ...CATEGORIES];
        const nf = new Intl.NumberFormat(undefined, {
          maximumFractionDigits: 1,
        });

        let html = `
          <table style="width:100%;border-collapse:collapse;font-size:11px;">
            <thead>
              <tr style="background:#e5e7eb;">
                ${cols.map((c) => `<th style="padding:6px;text-align:left;font-weight:600;">${c}</th>`).join("")}
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (r) => `
              <tr style="border-bottom:1px solid #d1d5db;">
                ${cols
                  .map((c) => {
                    const v = r[c];
                    const isNum = c !== "group" && Number.isFinite(+v);
                    return `<td style="padding:6px;">${isNum ? nf.format(+v) : v || "—"}</td>`;
                  })
                  .join("")}
              </tr>
            `
                )
                .join("")}
            </tbody>
          </table>
        `;

        selectionTable.innerHTML = html;
      }

      // ========== Event Handlers ==========
      slider.addEventListener("input", (ev) => {
        idxYear = +ev.target.value;
        yearValue.textContent = YEARS[idxYear];
        title.textContent = `${chartTitle} — ${YEARS[idxYear]}`;
        render(true, 800);
        if (selected.size > 0) {
          syncSelection();
        }
      });

      function sortBySize() {
        if (sorted) return;

        DATA.sort((a, b) => {
          const sumA = d3.sum(CATEGORIES, (k) => +a[k][idxYear] || 0);
          const sumB = d3.sum(CATEGORIES, (k) => +b[k][idxYear] || 0);
          return d3.descending(sumA, sumB);
        });

        sorted = true;
        sortBtn.style.backgroundColor = "#e5e7eb";
        sortBtn.style.fontWeight = "bold";
        resetBtn.style.backgroundColor = "#f3f4f6";
        resetBtn.style.fontWeight = "normal";

        render(true, 1200);
        status.textContent = "Ordenado por tamaño. Haz clic en 'Restaurar' para volver.";
      }

      function resetOrder() {
        if (!sorted) return;

        DATA = JSON.parse(JSON.stringify(DATA_ORIGINAL));
        sorted = false;
        sortBtn.style.backgroundColor = "#f3f4f6";
        sortBtn.style.fontWeight = "normal";
        resetBtn.style.backgroundColor = "#e5e7eb";
        resetBtn.style.fontWeight = "bold";

        render(true, 1200);
        status.textContent = "↺ Orden original restaurado.";
      }

      sortBtn.addEventListener("click", sortBySize);
      resetBtn.addEventListener("click", resetOrder);

      // ========== Initial Render ==========
      render(false);
      status.textContent = `Listo. ${DATA.length} grupos, ${CATEGORIES.length} categorías.`;
    } catch (e) {
      console.error("Error en RadialStackedBar:", e);
      status.textContent = `Error: ${e.message || e}`;
    }
  }

  // ========== Watch for changes ==========
  model.on("change:data", draw);
  model.on("change:options", draw);

  // Initial draw
  draw();
}