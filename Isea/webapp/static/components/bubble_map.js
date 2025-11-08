// bubble_map.js — 1 burbuja por país; selección aditiva por defecto (Shift=replace).
// Autobrush por "top tech" cuando recibe {techs} desde el sunburst.
// Evita burbujas en el océano (si no hay centroido -> no se dibuja).

(async function () {
  const container = d3.select('#bubble-map');
  container.selectAll('*').remove();

  const width  = container.node().clientWidth  || 900;
  const height = container.node().clientHeight || 700;

  const svg = container.append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`);

  const projection = d3.geoNaturalEarth1().scale(width / 6.3).translate([width / 2, height / 2]);
  const geo = d3.geoPath(projection);

  const cssVar = (name, fallback) => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  };

  // ----- MAPA BASE
  const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
  const features = topojson.feature(world, world.objects.countries).features;

  svg.append('g').attr('class', 'basemap')
    .selectAll('path').data(features).join('path')
    .attr('d', geo)
    .attr('fill',   cssVar('--map-land',    '#eef2f7'))
    .attr('stroke', cssVar('--map-borders', '#9aa6b2'))
    .attr('stroke-width', 0.6);

  // Centroidos en píxeles (para posicionar círculos)
  const centroidPx = new Map();
  features.forEach(f => {
    const props = f.properties || {};
    const iso   = props.iso_a3 || props.ISO_A3 || props.ADM0_A3;
    const name  = props.name || props.name_long;
    const pt    = geo.centroid(f); // ya está en PX
    if (iso)  centroidPx.set(String(iso).toUpperCase(), pt);
    if (name) centroidPx.set(String(name).toLowerCase(), pt);
  });

  // ----- ESTADO
  window.__selectedIsos = window.__selectedIsos || new Set();
  // modo agregar por defecto = verdadero
  if (window.__addMode === undefined) window.__addMode = true;

  let highlightIsos = new Set();           // hover
  let currentTechsHighlight = null;        // techs enfocadas (para tooltip)
  let isoAgg = new Map();                  // ISO -> { total, rn, nr, byTech: Map }
  let rScale = d3.scaleSqrt().domain([1, 1]).range([2, 28]);

  const fmt = n => d3.format(',')(Math.round(+n || 0));
  function isRenewable(str) {
    if (!str) return false;
    const s = String(str).toLowerCase();
    return s.includes('renew') || s.includes('hydro') || s.includes('solar') ||
           s.includes('wind')  || s.includes('geother') || s.includes('biomass') ||
           s.includes('bio')   || s.includes('tide') || s.includes('wave');
  }

  // ----- CARGA Y DIBUJO
  async function loadAndDraw(yearCol) {
    const rows = await fetch(`/api/data?year=${encodeURIComponent(yearCol)}`).then(r => r.json());

    // 1) Agregar por ISO
    isoAgg = new Map();
    rows.forEach(r => {
      const iso     = String(r.ISO3 || '').toUpperCase();
      const country = r.Country || iso;
      const tech    = String(r.Technology || '').trim();
      const value   = +r.Energy_Value || 0;
      if (!iso) return; // sin ISO, descartamos
      if (!isoAgg.has(iso)) isoAgg.set(iso, { iso, country, total: 0, rn: 0, nr: 0, byTech: new Map() });
      const o = isoAgg.get(iso);
      o.total += value;
      o.byTech.set(tech, (o.byTech.get(tech) || 0) + value);
      if (isRenewable(tech)) o.rn += value; else o.nr += value;
    });

    // 2) Construir burbujas (una por ISO) — si no hay centroido, NO se pinta
    const bubbles = [];
    isoAgg.forEach(o => {
      let pos = centroidPx.get(o.iso);
      if (!pos && o.country) pos = centroidPx.get(String(o.country).toLowerCase());
      if (!pos) return; // evitar “burbujas en el océano”
      bubbles.push({ iso: o.iso, country: o.country, total: o.total, cx: pos[0], cy: pos[1] });
    });

    // 3) Escala de radio
    const maxTotal = d3.max(bubbles, b => b.total) || 1;
    rScale.domain([1, maxTotal]);

    // 4) Limpiar y dibujar capa de burbujas (evita duplicados)
    svg.selectAll('g.bubbles').remove();
    const g = svg.append('g').attr('class', 'bubbles');

    const sel = g.selectAll('circle').data(bubbles, d => d.iso);
    sel.enter().append('circle')
      .attr('cx', d => d.cx).attr('cy', d => d.cy).attr('r', 0)
      .attr('fill', '#3b82f6').attr('stroke', '#0b214a').attr('stroke-width', 1.2).attr('opacity', 0.9)
      .on('mouseover', (e, d) => showTooltip(e, d))
      .on('mousemove', (e) => d3.select('#tooltip').style('top', (e.pageY + 12) + 'px').style('left', (e.pageX + 12) + 'px'))
      .on('mouseout', () => d3.select('#tooltip').style('visibility', 'hidden'))
      .on('click', (e, d) => {
        // Por defecto agregamos/quitemos (toggle). Shift = reemplazar.
        const globalAdd = (window.__addMode === undefined ? true : window.__addMode);
        const addMode   = e.shiftKey ? false : (globalAdd || e.ctrlKey || e.metaKey);

        if (!window.__selectedIsos) window.__selectedIsos = new Set();
        if (addMode) {
          if (window.__selectedIsos.has(d.iso)) window.__selectedIsos.delete(d.iso);
          else window.__selectedIsos.add(d.iso);
          // Notificar para que el donut se actualice
          const arr = Array.from(window.__selectedIsos);
          window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
          window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { isos: arr } }));
        } else {
          window.__selectedIsos = new Set([d.iso]);
          const arr = Array.from(window.__selectedIsos);
          window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
          window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { isos: arr } }));
          window.dispatchEvent(new CustomEvent('countrySelected',   { detail: { isos: arr } }));
        }
        applyHighlight();
      })
      .transition().duration(450).attr('r', d => rScale(d.total));

    applyHighlight();
  }

  function showTooltip(e, d) {
    const info = isoAgg.get(d.iso);
    if (!info) return;
    const total = info.total || 0;
    const rn = info.rn || 0, nr = info.nr || 0;

    let focusBlock = '';
    if (currentTechsHighlight && currentTechsHighlight.length) {
      const sumSel = currentTechsHighlight.reduce((acc, t) => acc + (+info.byTech.get(t) || 0), 0);
      const p = total ? (sumSel / total * 100).toFixed(1) : '0.0';
      focusBlock = `<div style="margin-top:6px;"><em>${currentTechsHighlight.join(' + ')}</em>: <strong>${fmt(sumSel)}</strong> (${p}%)</div>`;
    }

    const top = Array.from(info.byTech.entries())
      .sort((a, b) => b[1] - a[1]).slice(0, 4)
      .map(([k, v]) => `<div>${k}: <strong>${fmt(v)}</strong> (${total ? (v / total * 100).toFixed(1) : '0.0'}%)</div>`)
      .join('');

    d3.select('#tooltip').style('visibility', 'visible').html(`
      <strong>${info.country}</strong>
      <div>Total: <strong>${fmt(total)}</strong></div>
      <div>Renovable: ${fmt(rn)} (${total ? (rn / total * 100).toFixed(1) : '0.0'}%)</div>
      <div>No-Renovable: ${fmt(nr)} (${total ? (nr / total * 100).toFixed(1) : '0.0'}%)</div>
      ${focusBlock}
      <div style="margin-top:6px;border-top:1px solid rgba(255,255,255,.12);padding-top:6px;">${top}</div>
    `);
  }

  function applyHighlight() {
    const circlesSel = svg.select('g.bubbles').selectAll('circle');
    if (circlesSel.empty()) return;

    const selected = window.__selectedIsos || new Set();

    circlesSel
      .attr('opacity', d => {
        if (highlightIsos.size) return highlightIsos.has(d.iso) ? 1 : 0.15;
        if (selected.size)      return selected.has(d.iso)       ? 1 : 0.15;
        return 0.9;
      })
      .attr('stroke-width', d => {
        if (highlightIsos.size && highlightIsos.has(d.iso)) return 2.2;
        if (selected.size      && selected.has(d.iso))      return 2.0;
        return 1.2;
      })
      .attr('stroke', d => {
        if (highlightIsos.size && highlightIsos.has(d.iso)) return '#111';
        if (selected.size      && selected.has(d.iso))      return '#111';
        return '#0b214a';
      });
  }

  // ----- EVENTOS
  window.addEventListener('yearChange', ev => {
    const year = ev.detail.year || 'F2023';
    loadAndDraw(year);
  });

  window.addEventListener('highlightCountries', ev => {
    const techs = Array.isArray(ev.detail?.techs) ? ev.detail.techs.filter(Boolean) : [];
    currentTechsHighlight = techs.length ? techs : null;

    if (techs.length) {
      const setTechs = new Set(techs.map(String));
      const isos = [];
      isoAgg.forEach(o => {
        let bestT = null, bestV = -1;
        o.byTech.forEach((v, t) => { if (v > bestV) { bestV = v; bestT = t; } });
        if (bestT && setTechs.has(bestT)) isos.push(o.iso);
      });
      highlightIsos = new Set(isos);
    } else {
      const isos = ev.detail?.isos || [];
      highlightIsos = new Set(isos.map(s => String(s || '').toUpperCase()));
    }
    applyHighlight();
  });

  window.addEventListener('selectionChanged', () => applyHighlight());

  window.addEventListener('themeChanged', () => {
    svg.select('.basemap').selectAll('path')
      .attr('fill',   cssVar('--map-land',    '#eef2f7'))
      .attr('stroke', cssVar('--map-borders', '#9aa6b2'));
  });

  // Inicial
  loadAndDraw('F' + (document.getElementById('yearRange')?.value || '2023'));
})();
