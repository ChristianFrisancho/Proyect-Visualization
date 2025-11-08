// sunburst.js — donut 2 anillos (inner: Renewable/Non-Renewable; outer: tecnologías)
// Centro: %RN / %NR. Leyenda colapsable con botón “🧩 Agregar” (modo suma) y “Limpiar”.
// HOVER → envía sólo { techs } (autobrush por tecnología dominante en el mapa).
// CLICK → selección por bloques (Ctrl/⌘ o 🧩 para sumar/quitar; Shift en el mapa = replace).

(function(){
  const container = d3.select('#sunburst');
  const tooltip   = d3.select('#tooltip');

  const cssVar = (name, fallback) => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  };
  function safePalette(){
    const p = [];
    if (d3.schemeTableau10) p.push(...d3.schemeTableau10);
    if (d3.schemeSet3)     p.push(...d3.schemeSet3);
    if (d3.schemePaired)   p.push(...d3.schemePaired);
    if (!p.length)         p.push('#3b82f6','#f59e0b','#16a34a','#ef4444','#a855f7','#22d3ee','#eab308','#10b981');
    return p;
  }
  function isRenewable(txt){
    if (!txt) return false;
    const s = String(txt).toLowerCase();
    return s.includes('renew') || s.includes('hydro') || s.includes('solar') ||
           s.includes('wind')  || s.includes('geother') || s.includes('biomass') ||
           s.includes('bio')   || s.includes('tide') || s.includes('wave');
  }
  function clear(){
    container.selectAll('*').remove();
    d3.selectAll('.legendBox').remove();
  }

  // Estado global persistente: addMode ON por defecto, leyenda colapsada por defecto
  if (window.__addMode === undefined) window.__addMode = true;
  window.__legendCollapsed = window.__legendCollapsed ?? true;

  async function fetchAndRender(isos, yearCol){
    let url = '/api/aggregated';
    const qs = [];
    if (yearCol) qs.push(`year=${encodeURIComponent(yearCol)}`);
    if (isos && isos.length) qs.push(`isos=${encodeURIComponent(isos.join(','))}`);
    if (qs.length) url += '?' + qs.join('&');
    const res = await fetch(url).then(r => r.json());
    render(res, isos, yearCol);
  }

  function render(data, isos, yearCol){
    clear();

    const width  = container.node().clientWidth  || 720;
    const height = Math.max(520, container.node().clientHeight || 520);

    const svg = container.append('svg')
      .attr('width','100%').attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio','xMidYMid meet');

    const g = svg.append('g').attr('transform', `translate(${width/2},${height/2})`);

    // ---- preparar outer = tecnologías limpias; inner = RN/NR
    const techRows = Array.isArray(data.tech_breakdown) ? data.tech_breakdown : [];
    const cleaned  = techRows.filter(t => {
      const name = (t.Technology ?? '').toString().trim();
      return name && name.toLowerCase() !== 'nan';
    });
    if (!cleaned.length){
      g.append('text').attr('text-anchor','middle')
        .style('font-size','16px').style('fill', cssVar('--panel-text','#111'))
        .text('No hay datos para la selección');
      return;
    }

    const byTech = new Map();
    cleaned.forEach(r => {
      const key   = String(r.Technology);
      const value = +r.Energy_Value || 0;
      byTech.set(key, (byTech.get(key)||0) + value);
    });

    const rnChildren = [], nrChildren = [];
    byTech.forEach((v,k) => (isRenewable(k) ? rnChildren : nrChildren).push({ name:k, value:v }));

    const rnTotal = d3.sum(rnChildren, d => d.value);
    const nrTotal = d3.sum(nrChildren, d => d.value);
    const total   = rnTotal + nrTotal;
    const rnPct   = total ? (rnTotal/total*100) : 0;
    const nrPct   = total ? (nrTotal/total*100) : 0;

    const techNames = Array.from(new Set([...rnChildren, ...nrChildren].map(t => t.name))).sort((a,b)=>a.localeCompare(b));
    const orderMap  = new Map(techNames.map((n,i)=>[n,i]));

    const rootObj = { name:'root',
      children: [
        { name:'Renewable',     children: rnChildren },
        { name:'Non-Renewable', children: nrChildren }
      ]
    };
    const root = d3.hierarchy(rootObj).sum(d => d.value || 0);
    root.each(node => {
      if (!node.children) return;
      node.children.sort((a,b) => {
        if (node.depth === 0) return (a.data.name === 'Renewable' ? 0 : 1) - (b.data.name === 'Renewable' ? 0 : 1);
        return (orderMap.get(a.data.name) ?? 0) - (orderMap.get(b.data.name) ?? 0);
      });
    });

    const radius    = Math.min(width, height) * 0.42;
    const partition = d3.partition().size([2*Math.PI, radius]);
    partition(root);

    const colorInner = d3.scaleOrdinal()
      .domain(['Renewable','Non-Renewable'])
      .range([cssVar('--accent','#3b82f6'), cssVar('--accent-nr','#f59e0b')]);
    const outerColor = d3.scaleOrdinal().domain(techNames).range(safePalette());

    const arc = d3.arc()
      .startAngle(d=>d.x0).endAngle(d=>d.x1)
      .innerRadius(d => d.y0).outerRadius(d => Math.max(d.y0, d.y1) - 1)
      .padAngle(0.005);

    const nodes = root.descendants().filter(d => d.depth >= 1);

    g.selectAll('path.node').data(nodes, d => d.ancestors().map(a=>a.data.name).join('/')).join('path')
      .attr('class','node')
      .attr('d', arc)
      .attr('fill', d => d.depth === 1 ? colorInner(d.data.name) : outerColor(d.data.name))
      .attr('stroke', '#fff').attr('stroke-width', 0.6)

      // HOVER → sólo techs (mapa decide por top-tech)
      .on('mouseenter', (e,d) => {
        const label = d.data.name;
        const val   = d.value || 0;
        const pct   = total ? (val/total*100).toFixed(2)+'%' : '0%';
        tooltip.style('visibility','visible')
               .html(`<strong>${label}</strong><div>Valor: ${d3.format(',')(Math.round(val))}</div><div>Porcentaje del total: ${pct}</div>`);

        if (d.depth === 2){
          const tech = d.data.name;
          window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { techs: [tech] } }));
        } else if (d.depth === 1){
          const types = (d.children || []).map(c => c.data.name);
          window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { techs: types } }));
        }
      })
      .on('mousemove', (e)=> tooltip.style('top',(e.pageY+12)+'px').style('left',(e.pageX+12)+'px'))
      .on('mouseleave', ()=> {
        tooltip.style('visibility','hidden');
        const arr = Array.from(window.__selectedIsos || []);
        window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { isos: arr, techs: [] } }));
      })

      // CLICK → selección por bloques (🧩/Ctrl/⌘ suma; sin eso, reemplaza)
      .on('click', (e,d) => {
        const yr    = (document.getElementById('yearRange')?.value) ? 'F' + document.getElementById('yearRange').value : null;
        const qYear = yr ? `&year=${encodeURIComponent(yr)}` : '';
        const addMode = window.__addMode || e.ctrlKey || e.metaKey;

        const toggleWithIsos = (isos) => {
          if (!window.__selectedIsos) window.__selectedIsos = new Set();
          if (addMode){
            const cur = new Set(Array.from(window.__selectedIsos));
            isos.forEach(i => cur.has(i) ? cur.delete(i) : cur.add(i));
            window.__selectedIsos = new Set(cur);
          } else {
            window.__selectedIsos = new Set(isos);
          }
          const arr = Array.from(window.__selectedIsos);
          window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
          window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { isos: arr } }));
          window.dispatchEvent(new CustomEvent('countrySelected',   { detail: { isos: arr } }));
        };

        if (d.depth === 2){
          const tech = d.data.name;
          fetch(`/api/data?technology=${encodeURIComponent(tech)}${qYear}`)
            .then(r=>r.json()).then(rows => {
              const isos = Array.from(new Set(rows.map(r => (r.ISO3||'').toString().toUpperCase()).filter(Boolean)));
              toggleWithIsos(isos);
            });
        } else if (d.depth === 1){
          const types = (d.children || []).map(c => c.data.name);
          fetch(`/api/data${qYear ? '?year='+encodeURIComponent(yr) : ''}`)
            .then(r=>r.json()).then(rows => {
              const filtered = rows.filter(r => types.includes(r.Technology));
              const isos = Array.from(new Set(filtered.map(r => (r.ISO3||'').toString().toUpperCase()).filter(Boolean)));
              toggleWithIsos(isos);
            });
        }
      });

    // Etiquetas
    const innerNodes = root.descendants().filter(d => d.depth === 1);
    const innerLabelArc = d3.arc().innerRadius(d => d.y0 + (d.y1 - d.y0)/2).outerRadius(d => d.y0 + (d.y1 - d.y0)/2);
    g.selectAll('text.innerLabel').data(innerNodes).join('text')
      .attr('class','innerLabel')
      .attr('transform', d => `translate(${innerLabelArc.centroid(d)})`)
      .attr('text-anchor','middle')
      .style('fill','#fff').style('font-weight',700).style('font-size','12px')
      .text(d => total ? (d.value / total * 100).toFixed(1) + '%' : '0%');

    const outerNodes = root.descendants().filter(d => d.depth === 2 && (d.x1 - d.x0) > 0.06);
    const outerLabelArc = d3.arc().innerRadius(d => (d.y0 + d.y1)/2).outerRadius(d => (d.y0 + d.y1)/2);
    g.selectAll('text.outerLabel').data(outerNodes).join('text')
      .attr('class','outerLabel')
      .attr('transform', d => `translate(${outerLabelArc.centroid(d)})`)
      .attr('text-anchor','middle')
      .style('fill','#fff').style('font-weight',700).style('font-size','11px')
      .text(d => total ? (d.value / total * 100).toFixed(1) + '%' : '');

    // Centro (%RN / %NR)
    g.append('text').attr('text-anchor','middle').attr('dy','-4px')
      .style('font-size','18px').style('font-weight','700')
      .style('fill', cssVar('--panel-text','#111'))
      .text(`Renovable ${rnPct.toFixed(1)}%`);
    g.append('text').attr('text-anchor','middle').attr('dy','20px')
      .style('font-size','12px').style('fill', cssVar('--panel-text','#111'))
      .text(`No-Renovable ${nrPct.toFixed(1)}%`);

    // Leyenda
    const legend = container.append('div').attr('class','legendBox');
    if (window.__legendCollapsed) legend.classed('collapsed', true);

    const header = legend.append('div').attr('class','legendHeaderBar');
    header.append('div').text('Leyenda');

    const controls = header.append('div').attr('class','legendControls');
    const addBtn = controls.append('button')
      .attr('class','legendBtnTiny' + (window.__addMode ? ' active' : ''))
      .text(window.__addMode ? '🧩 Agregar ✓' : '🧩 Agregar')
      .on('click', () => {
        window.__addMode = !window.__addMode;
        addBtn.classed('active', window.__addMode)
              .text(window.__addMode ? '🧩 Agregar ✓' : '🧩 Agregar');
      });
    const collapseBtn = controls.append('button')
      .attr('class','legendBtnTiny')
      .text(window.__legendCollapsed ? '▸' : '▾')
      .on('click', () => {
        window.__legendCollapsed = !window.__legendCollapsed;
        legend.classed('collapsed', window.__legendCollapsed);
        collapseBtn.text(window.__legendCollapsed ? '▸' : '▾');
      });

    const body = legend.append('div').attr('class','legendBody');
    body.append('div').attr('class','legendRow').html(`
      <span style="display:flex;align-items:center;gap:8px;">
        <span class="swatch" style="background:${cssVar('--accent','#3b82f6')}"></span>
        <span>Renewable</span>
      </span>
      <span class="legendPct">${rnPct.toFixed(1)}%</span>
    `);
    body.append('div').attr('class','legendRow').html(`
      <span style="display:flex;align-items:center;gap:8px;">
        <span class="swatch" style="background:${cssVar('--accent-nr','#f59e0b')}"></span>
        <span>Non-Renewable</span>
      </span>
      <span class="legendPct">${nrPct.toFixed(1)}%</span>
    `);

    body.append('div')
      .style('margin','8px 0')
      .style('border-top','1px solid '+cssVar('--stroke-soft','#e5e7eb'))
      .style('height','1px');

    const topTech = [...rnChildren, ...nrChildren]
      .sort((a,b)=> a.name.localeCompare(b.name)).slice(0,8);
    topTech.forEach(t => {
      const p = total ? (t.value/total*100).toFixed(1) : '0.0';
      body.append('div').attr('class','legendRow').html(`
        <span style="display:flex;align-items:center;gap:8px;">
          <span class="swatch" style="background:${outerColor(t.name)}"></span>
          <span>${t.name}</span>
        </span>
        <span class="legendPct">${p}%</span>
      `);
    });

    body.append('button').attr('id','legendClear').attr('class','legendBtn').text('🧹 Limpiar selección');
    body.append('div').attr('class','legendHint').text('Click = seleccionar · Ctrl+click o 🧩 Agregar = sumar/quitar');

    document.getElementById('legendClear').addEventListener('click', () => {
      window.__selectedIsos = new Set();
      const arr = [];
      window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
      window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { isos: arr, techs: [] } }));
    });

    container.node().scrollTop = 0;
  }

  // Listeners
  window.addEventListener('selectionChanged', ev => {
    const isos = ev.detail.isos || [];
    const year = (document.getElementById('yearRange')?.value) ? 'F' + document.getElementById('yearRange').value : null;
    fetchAndRender(isos.length ? isos : null, year);
  });
  window.addEventListener('countrySelected', ev => {
    const isos = ev.detail.isos || (ev.detail.iso ? [ev.detail.iso] : []);
    const year = (document.getElementById('yearRange')?.value) ? 'F' + document.getElementById('yearRange').value : null;
    fetchAndRender(isos.length ? isos : null, year);
  });
  window.addEventListener('yearChange', ev => {
    const year = ev.detail.year || null;
    const currentSel = (window.__selectedIsos && window.__selectedIsos.size) ? Array.from(window.__selectedIsos) : null;
    fetchAndRender(currentSel, year);
  });
  window.addEventListener('themeChanged', ()=> {
    const year = (document.getElementById('yearRange')?.value) ? 'F' + document.getElementById('yearRange').value : null;
    const currentSel = (window.__selectedIsos && window.__selectedIsos.size) ? Array.from(window.__selectedIsos) : null;
    fetchAndRender(currentSel, year);
  });

  // Init
  const initialYear = 'F' + (document.getElementById('yearRange')?.value || '2023');
  fetchAndRender(null, initialYear);
})();
