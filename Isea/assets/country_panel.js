// country_panel.js — Panel lateral que muestra desglose por país usando window.__ENERGY_DATA

(function () {

  const container = d3.select("#countryPanel");

  function clearPanel() {
    container.selectAll("*").remove();
    container.style("display", "none");
  }

  // ---- Render panel para un conjunto de ISOs
  function renderForIsos(isos, year) {
    container.selectAll("*").remove();
    container.style("display", "block");

    const DATA = window.__ENERGY_DATA || [];

    if (!isos || isos.length === 0) {
      clearPanel();
      return;
    }

    // Filtrar por país y año
    const rows = DATA.filter(
      d =>
        isos.includes(d.ISO3) &&
        d.year === year
    );

    if (rows.length === 0) {
      container.append("p").text("Sin datos para la selección.");
      return;
    }

    // ---- Agregación
    // Total, por tipo, por tecnología
    let total = 0;

    const byType = new Map();       // Energy_Type -> sum
    const byTech = new Map();       // Technology -> sum

    rows.forEach(r => {
      const val = r.Energy_Value || 0;
      total += val;

      // por tipo
      const t = r.Energy_Type || "N/A";
      byType.set(t, (byType.get(t) || 0) + val);

      // por tecnología
      const tech = r.Technology || "N/A";
      byTech.set(tech, (byTech.get(tech) || 0) + val);
    });

    // Título superior
    container
      .append("h3")
      .text(`${isos.length === 1 ? rows[0].Country : isos.length + " países"} — ${year}`);

    // TOTAL
    container.append("div").attr("class", "type-header").html(`
      <strong>Total:</strong> ${d3.format(",")(Math.round(total))}
    `);

    // ---- LISTA DE TIPOS
    container.append("h4").text("Por tipo de energía");
    const typeTable = container.append("table").attr("class", "panel-table");
    byType.forEach((v, k) => {
      const pct = total ? ((v / total) * 100).toFixed(1) : 0;
      const tr = typeTable.append("tr");
      tr.append("td").text(k);
      tr.append("td").text(d3.format(",")(Math.round(v)));
      tr.append("td").text(pct + "%");
    });

    // ---- LISTA DE TECNOLOGÍAS
    container.append("h4").text("Top tecnologías");
    const techsSorted = Array.from(byTech.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12);

    const techTable = container.append("table").attr("class", "panel-table");
    techsSorted.forEach(([tech, v]) => {
      const pct = total ? ((v / total) * 100).toFixed(1) : 0;
      const tr = techTable.append("tr");
      tr.append("td").text(tech);
      tr.append("td").text(d3.format(",")(Math.round(v)));
      tr.append("td").text(pct + "%");
    });
  }

  // ---- Eventos globales
  // 1) Selección desde el mapa o sunburst
  window.addEventListener("countrySelected", ev => {
    const isos = ev.detail.isos || [];
    const year = ev.detail.year || window.__CURRENT_YEAR || 2023;
    renderForIsos(isos, year);
  });

  // 2) Cambio de año
  window.addEventListener("yearChange", ev => {
    const year = ev.detail.year;
    window.__CURRENT_YEAR = year;

    // refrescar si hay selección activa
    if (window.__SELECTED_ISOS && window.__SELECTED_ISOS.length > 0) {
      renderForIsos(window.__SELECTED_ISOS, year);
    }
  });

  // 3) Para limpiar selección
  window.addEventListener("clearSelection", () => {
    clearPanel();
  });

})();
