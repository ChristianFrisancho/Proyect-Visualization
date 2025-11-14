// sunburst.js — donut 2 anillos (inner: Renewable / Non-Renewable; outer: tecnologías)
// Usa window.__ENERGY_DATA (inyectado por Python en energy_dashboard.py)
// Se actualiza con yearChange y selectionChanged, y coordina con el mapa.

(function () {

  const container = d3.select("#sunburst");
  const tooltip   = d3.select("#tooltip");

  // Helpers de estilo
  const cssVar = (name, fallback) => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  };

  function safePalette() {
    const p = [];
    if (d3.schemeTableau10) p.push(...d3.schemeTableau10);
    if (d3.schemeSet3)      p.push(...d3.schemeSet3);
    if (d3.schemePaired)    p.push(...d3.schemePaired);
    if (!p.length)          p.push("#3b82f6","#f59e0b","#16a34a","#ef4444","#a855f7","#22d3ee","#eab308","#10b981");
    return p;
  }

  function clear() {
    container.selectAll("*").remove();
  }

  // ------------------------------------------------------------------
  // Construye estructura jerárquica a partir de window.__ENERGY_DATA
  // ------------------------------------------------------------------
  function buildHierarchy(year, isos) {
    const DATA = window.__ENERGY_DATA || [];
    let rows = DATA.filter(d => d.year === year);

    if (isos && isos.length) {
      rows = rows.filter(d => isos.includes(d.ISO3));
    }

    if (!rows.length) return null;

    // Mapear tecnologías según tipo de energía
    const rnChildren = [];   // Renewable
    const nrChildren = [];   // Non-Renewable

    const byTech = new Map();  // key = Technology, value = {tech, type, value}

    rows.forEach(r => {
      const tech = (r.Technology || "N/A").toString();
      const type = (r.Energy_Type || "").toString();  // "Total Renewable" o "Total Non-Renewable"
      const val  = +r.Energy_Value || 0;

      if (!byTech.has(tech)) {
        byTech.set(tech, { tech, type, value: 0 });
      }
      const obj = byTech.get(tech);
      obj.value += val;

      // Si alguna fila marca este tech como Renovable, nos quedamos con eso
      if (type.toLowerCase().includes("renew")) {
        obj.type = "Renewable";
      } else if (type.toLowerCase().includes("non")) {
        obj.type = "Non-Renewable";
      }
    });

    byTech.forEach(({ tech, type, value }) => {
      if (!value) return;
      const child = { name: tech, value: value };
      if (type === "Renewable") rnChildren.push(child);
      else if (type === "Non-Renewable") nrChildren.push(child);
      else {
        // Si no se reconoce, lo ponemos como no-renovable por defecto
        nrChildren.push(child);
      }
    });

    const rnTotal = d3.sum(rnChildren, d => d.value);
    const nrTotal = d3.sum(nrChildren, d => d.value);
    const total   = rnTotal + nrTotal;

    if (!total) return null;

    const rootObj = {
      name: "root",
      children: [
        { name: "Renewable",     children: rnChildren },
        { name: "Non-Renewable", children: nrChildren }
      ]
    };

    return {
      rootObj,
      rnChildren,
      nrChildren,
      rnTotal,
      nrTotal,
      total
    };
  }

  // ------------------------------------------------------------------
  // Render principal
  // ------------------------------------------------------------------
  function render(year, isos) {
    clear();

    const width  = container.node().clientWidth  || 720;
    const height = Math.max(520, container.node().clientHeight || 520);

    const h = buildHierarchy(year, isos);
    if (!h) {
      container
        .append("div")
        .style("padding", "12px")
        .style("color", cssVar("--panel-text", "#111"))
        .text("No hay datos para la selección / año.");
      return;
    }

    const { rootObj, rnChildren, nrChildren, rnTotal, nrTotal, total } = h;

    const svg = container
      .append("svg")
      .attr("width", "100%")
      .attr("height", height)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet");

    const g = svg
      .append("g")
      .attr("transform", `translate(${width / 2},${height / 2})`);

    const root = d3
      .hierarchy(rootObj)
      .sum(d => d.value || 0);

    const techNames = [];
    root.each(d => {
      if (d.depth === 2) techNames.push(d.data.name);
    });

    const radius    = Math.min(width, height) * 0.42;
    const partition = d3.partition().size([2 * Math.PI, radius]);
    partition(root);

    const colorInner = d3
      .scaleOrdinal()
      .domain(["Renewable", "Non-Renewable"])
      .range([
        cssVar("--accent", "#3b82f6"),
        cssVar("--accent-nr", "#f59e0b")
      ]);

    const outerColor = d3
      .scaleOrdinal()
      .domain(techNames)
      .range(safePalette());

    const arc = d3
      .arc()
      .startAngle(d => d.x0)
      .endAngle(d => d.x1)
      .innerRadius(d => d.y0)
      .outerRadius(d => Math.max(d.y0, d.y1) - 1)
      .padAngle(0.005);

    const nodes = root
      .descendants()
      .filter(d => d.depth >= 1);

    const fmt = n => d3.format(",")(Math.round(+n || 0));

    // ------------------------------------------------------------
    // Función para disparar highlight en el mapa
    // ------------------------------------------------------------
    function highlightByTechList(techs) {
      window.dispatchEvent(
        new CustomEvent("highlightCountries", {
          detail: { techs: techs || [] }
        })
      );
    }

    // ------------------------------------------------------------
    // Función para seleccionar países (click)
    // ------------------------------------------------------------
    function selectCountriesByFilter(filterFn, addMode) {
      const DATA = window.__ENERGY_DATA || [];
      const yr   = year;

      // Filtramos por año y condición
      const rows = DATA.filter(
        d => d.year === yr && filterFn(d)
      );

      const isos = Array.from(
        new Set(
          rows
            .map(r => (r.ISO3 || "").toString())
            .filter(Boolean)
        )
      );

      if (!window.__SELECTED_ISOS) window.__SELECTED_ISOS = [];

      let current = new Set(window.__SELECTED_ISOS);

      if (addMode) {
        isos.forEach(iso => {
          if (current.has(iso)) current.delete(iso);
          else current.add(iso);
        });
      } else {
        current = new Set(isos);
      }

      const arr = Array.from(current);
      window.__SELECTED_ISOS = arr;

      window.dispatchEvent(
        new CustomEvent("selectionChanged", { detail: { isos: arr, year: yr } })
      );
      window.dispatchEvent(
        new CustomEvent("countrySelected", { detail: { isos: arr, year: yr } })
      );
      window.dispatchEvent(
        new CustomEvent("highlightCountries", { detail: { isos: arr, techs: [] } })
      );
    }

    // ------------------------------------------------------------
    // Dibujo de los arcos
    // ------------------------------------------------------------
    g.selectAll("path.node")
      .data(nodes, d => d.ancestors().map(a => a.data.name).join("/"))
      .join("path")
      .attr("class", "node")
      .attr("d", arc)
      .attr("fill", d =>
        d.depth === 1
          ? colorInner(d.data.name)
          : outerColor(d.data.name)
      )
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.6)
      // HOVER
      .on("mouseenter", (e, d) => {
        const label = d.data.name;
        const val   = d.value || 0;
        const pct   = total ? ((val / total) * 100).toFixed(2) + "%" : "0%";

        tooltip
          .style("visibility", "visible")
          .html(
            `<strong>${label}</strong>` +
            `<div>Valor: ${fmt(val)}</div>` +
            `<div>Porcentaje del total: ${pct}</div>`
          );

        if (d.depth === 2) {
          // tecnología individual
          highlightByTechList([d.data.name]);
        } else if (d.depth === 1) {
          // grupo Renewable / Non-Renewable
          const techs = (d.children || []).map(c => c.data.name);
          highlightByTechList(techs);
        }
      })
      .on("mousemove", e => {
        tooltip
          .style("top", e.pageY + 12 + "px")
          .style("left", e.pageX + 12 + "px");
      })
      .on("mouseleave", () => {
        tooltip.style("visibility", "hidden");
        const arr = window.__SELECTED_ISOS || [];
        window.dispatchEvent(
          new CustomEvent("highlightCountries", {
            detail: { isos: arr, techs: [] }
          })
        );
      })
      // CLICK
      .on("click", (e, d) => {
        const addMode = e.ctrlKey || e.metaKey; // Ctrl/⌘ = sumar/quitar
        if (d.depth === 2) {
          const tech = d.data.name;
          selectCountriesByFilter(r => r.Technology === tech, addMode);
        } else if (d.depth === 1) {
          const type = d.data.name; // "Renewable" / "Non-Renewable"
          if (type === "Renewable") {
            selectCountriesByFilter(r =>
              (r.Energy_Type || "").toLowerCase().includes("renew"), addMode);
          } else {
            selectCountriesByFilter(r =>
              (r.Energy_Type || "").toLowerCase().includes("non"), addMode);
          }
        }
      });

    // ------------------------------------------------------------
    // Etiquetas
    // ------------------------------------------------------------
    const innerNodes = root.descendants().filter(d => d.depth === 1);
    const innerLabelArc = d3
      .arc()
      .innerRadius(d => d.y0 + (d.y1 - d.y0) / 2)
      .outerRadius(d => d.y0 + (d.y1 - d.y0) / 2);

    g.selectAll("text.innerLabel")
      .data(innerNodes)
      .join("text")
      .attr("class", "innerLabel")
      .attr("transform", d => `translate(${innerLabelArc.centroid(d)})`)
      .attr("text-anchor", "middle")
      .style("fill", "#fff")
      .style("font-weight", 700)
      .style("font-size", "12px")
      .text(d => {
        const val = d.value || 0;
        return total ? ((val / total) * 100).toFixed(1) + "%" : "0%";
      });

    const outerNodes = root
      .descendants()
      .filter(d => d.depth === 2 && (d.x1 - d.x0) > 0.06);

    const outerLabelArc = d3
      .arc()
      .innerRadius(d => (d.y0 + d.y1) / 2)
      .outerRadius(d => (d.y0 + d.y1) / 2);

    g.selectAll("text.outerLabel")
      .data(outerNodes)
      .join("text")
      .attr("class", "outerLabel")
      .attr("transform", d => `translate(${outerLabelArc.centroid(d)})`)
      .attr("text-anchor", "middle")
      .style("fill", "#fff")
      .style("font-weight", 700)
      .style("font-size", "11px")
      .text(d => {
        const val = d.value || 0;
        return total ? ((val / total) * 100).toFixed(1) + "%" : "";
      });

    // ------------------------------------------------------------
    // Texto central
    // ------------------------------------------------------------
    const rnPct = total ? (rnTotal / total) * 100 : 0;
    const nrPct = total ? (nrTotal / total) * 100 : 0;

    g.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "-4px")
      .style("font-size", "18px")
      .style("font-weight", "700")
      .style("fill", cssVar("--panel-text", "#111"))
      .text(`Renovable ${rnPct.toFixed(1)}%`);

    g.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "20px")
      .style("font-size", "12px")
      .style("fill", cssVar("--panel-text", "#111"))
      .text(`No-Renovable ${nrPct.toFixed(1)}%`);

    // ------------------------------------------------------------
    // Pequeña leyenda simple (RN / NR + top techs)
    // ------------------------------------------------------------
    const legend = container
      .append("div")
      .style("padding", "8px 14px 12px 14px")
      .style("font-size", "13px")
      .style("color", cssVar("--panel-text", "#111"));

    legend.append("div").html(
      `<strong>Año ${year}</strong> · ` +
      `Total: ${fmt(total)}`
    );

    const row1 = legend.append("div").style("margin-top", "4px");
    row1.html(
      `<span style="display:inline-flex;align-items:center;gap:6px;margin-right:12px;">
         <span style="width:10px;height:10px;border-radius:9999px;background:${cssVar("--accent","#3b82f6")}"></span>
         Renewable: ${rnPct.toFixed(1)}%
       </span>
       <span style="display:inline-flex;align-items:center;gap:6px;">
         <span style="width:10px;height:10px;border-radius:9999px;background:${cssVar("--accent-nr","#f59e0b")}"></span>
         Non-Renewable: ${nrPct.toFixed(1)}%
       </span>`
    );

    // Top tecnologías (globales)
    const topTech = [...rnChildren, ...nrChildren]
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);

    if (topTech.length) {
      legend.append("div")
        .style("margin-top", "6px")
        .style("font-weight", "600")
        .text("Top tecnologías (selección):");

      topTech.forEach(t => {
        const p = total ? (t.value / total * 100).toFixed(1) : "0.0";
        legend.append("div").text(`${t.name}: ${p}%`);
      });
    }
  }

  // ------------------------------------------------------------------
  // Event listeners
  // ------------------------------------------------------------------
  function currentYear() {
    if (window.__CURRENT_YEAR) return window.__CURRENT_YEAR;
    const slider = document.getElementById("yearRange");
    if (slider && slider.value) return +slider.value;
    return 2023;
  }

  function currentIsos() {
    return window.__SELECTED_ISOS || [];
  }

  window.addEventListener("selectionChanged", ev => {
    const isos = (ev.detail && ev.detail.isos) || currentIsos();
    window.__SELECTED_ISOS = isos;
    render(currentYear(), isos);
  });

  window.addEventListener("countrySelected", ev => {
    const isos = (ev.detail && ev.detail.isos) || currentIsos();
    window.__SELECTED_ISOS = isos;
    render(currentYear(), isos);
  });

  window.addEventListener("yearChange", ev => {
    const year = ev.detail && ev.detail.year ? ev.detail.year : currentYear();
    window.__CURRENT_YEAR = year;
    render(year, currentIsos());
  });

  window.addEventListener("themeChanged", () => {
    render(currentYear(), currentIsos());
  });

  // Init (primer render)
  const initialYear = currentYear();
  render(initialYear, currentIsos());

})();
