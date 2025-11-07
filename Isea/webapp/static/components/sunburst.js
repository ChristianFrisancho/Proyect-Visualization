// sunburst.js - Anillo interno: Renewable/Non-Renewable; Externo: Tecnologías
(function(){
  const container = d3.select('#sunburst');
  const tooltip = d3.select('#tooltip');

  const cssVar = (name, fallback) =>
    (getComputedStyle(document.documentElement).getPropertyValue(name) || fallback).trim() || fallback;

  function isRenewable(type){
    if (!type) return false;
    const s = String(type).toLowerCase();
    return s.includes('renewable') || s.includes('hydro') || s.includes('solar') ||
           s.includes('wind') || s.includes('geothermal') || s.includes('biomass');
  }

  function clear(){
    container.selectAll('*').remove();
    d3.selectAll('.legendBox').remove();
  }

  async function fetchAndRender(isos, yearCol){
    let url = '/api/aggregated';
    const params = [];
    if (yearCol) params.push(`year=${encodeURIComponent(yearCol)}`);
    if (isos && isos.length) params.push(`isos=${encodeURIComponent(isos.join(','))}`);
    if (params.length) url += '?' + params.join('&');
    const res = await fetch(url).then(r => r.json());
    render(res, isos, yearCol);
  }

  function safePalette(){
    const p = [];
    if (d3.schemeTableau10) p.push(...d3.schemeTableau10);
    if (d3.schemeSet3)     p.push(...d3.schemeSet3);
    if (d3.schemePaired)   p.push(...d3.schemePaired);
    if (!p.length)         p.push('#2ca9b7','#ff7f0e','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf');
    return p;
  }

  function render(data, isos, yearCol){
    clear();
    const width = container.node().clientWidth || 720;
    const height = Math.max(520, container.node().clientHeight || 520);
    const svg = container.append('svg')
      .attr('width','100%').attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio','xMidYMid meet');
    const g = svg.append('g').attr('transform', `translate(${width/2},${height/2})`);

    const total = data.total || 0;
    const pairs  = data.pairs || [];        // [{Energy_Type, Technology, Energy_Value, pct}, ...]

    if (!pairs.length){
      g.append('text')
        .attr('text-anchor','middle').attr('dy','0')
        .style('font-size','16px').style('fill', cssVar('--panel-text','#111'))
        .text('No hay datos para la selección');
      return;
    }

    // Construye: RN/NR -> tecnologías
    const groups = { Renewable: [], 'Non-Renewable': [] };
    pairs.forEach(p => {
      const techName = (p.Technology && p.Technology.toLowerCase() !== 'nan') ? p.Technology : p.Energy_Type;
      const grp = isRenewable(p.Energy_Type) ? 'Renewable' : 'Non-Renewable';
      groups[grp].push({ name: techName, value: p.Energy_Value });
    });

    // Agrega por tecnología dentro de cada grupo (por si viene repetida)
    const aggChildren = (arr) => {
      const m = new Map();
      arr.forEach(x => m.set(x.name, (m.get(x.name)||0) + (x.value||0)));
      return Array.from(m.entries()).map(([name, value]) => ({ name, value }));
    };

    const rootObj = {
      name: 'root',
      children: [
        { name: 'Renewable', children: aggChildren(groups.Renewable) },
        { name: 'Non-Renewable', children: aggChildren(groups['Non-Renewable']) }
      ]
    };

    const root = d3.hierarchy(rootObj).sum(d => d.value || 0).sort((a,b)=> b.value - a.value);

    const radius = Math.min(width, height) * 0.42;
    const partition = d3.partition().size([2*Math.PI, radius]);
    partition(root);

    const colorInner = d3.scaleOrdinal().domain(['Renewable','Non-Renewable'])
                        .range([cssVar('--accent','#2ca9b7'), cssVar('--accent-nr','#ff7f0e')]);
    const techNames = Array.from(new Set([...(groups.Renewable||[]), ...(groups['Non-Renewable']||[])]
                      .map(t => t.name)));
    const outerPalette = safePalette();
    const outerColor = d3.scaleOrdinal().domain(techNames).range(outerPalette);

    const arc = d3.arc()
      .startAngle(d=>d.x0).endAngle(d=>d.x1)
      .innerRadius(d => d.y0).outerRadius(d => Math.max(d.y0, d.y1) - 1)
      .padAngle(0.005);

    const nodes = root.descendants().filter(d => d.depth >= 1);

    g.selectAll('path.node').data(nodes, d => d.data.name + '-' + d.depth).join('path')
      .attr('class','node')
      .attr('d', arc)
      .attr('fill', d => d.depth === 1 ? colorInner(d.data.name) : outerColor(d.data.name))
      .attr('stroke', '#fff').attr('stroke-width', 0.6)
      .on('mouseenter', (e,d) => {
        const label = d.data.name;
        const val = d.value || 0;
        const pctTotal = total ? (val / total * 100).toFixed(2) + '%' : '0%';
        tooltip.style('visibility','visible').html(
          `<strong>${label}</strong><div>Valor: ${d3.format(',')(Math.round(val))}</div><div>Porcentaje del total: ${pctTotal}</div>`
        );

        // Hover: autobrush (no cambia selección)
        const yr = (document.getElementById('yearRange')?.value) ? 'F' + document.getElementById('yearRange').value : null;
        if (d.depth === 2){
          const tech = d.data.name;
          fetch(`/api/data?technology=${encodeURIComponent(tech)}${yr?`&year=${encodeURIComponent(yr)}`:''}`)
            .then(r=>r.json()).then(rows => {
              window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { rows } }));
            });
        } else if (d.depth === 1){
          const childTechs = (d.children||[]).map(c=>c.data.name);
          fetch(`/api/data${yr?`?year=${encodeURIComponent(yr)}`:''}`)
            .then(r=>r.json()).then(rows => {
              const filtered = rows.filter(r => childTechs.includes(r.Technology));
              window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { rows: filtered } }));
            });
        }
      })
      .on('mousemove', (e)=> tooltip.style('top',(e.pageY+12)+'px').style('left',(e.pageX+12)+'px'))
      .on('mouseleave', ()=> {
        tooltip.style('visibility','hidden');
        // limpia highlight y vuelve al estado de selección
        window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { rows: [] } }));
      })
      .on('click', (e,d) => {
        const addToggle = e.ctrlKey || e.metaKey;
        const yr = (document.getElementById('yearRange')?.value) ? 'F' + document.getElementById('yearRange').value : null;
        const qYear = yr ? `&year=${encodeURIComponent(yr)}` : '';

        if (d.depth === 2) {
          // Click en tecnología -> selección y brushing
          const technology = d.data.name;
          fetch(`/api/data?technology=${encodeURIComponent(technology)}${qYear}`).then(r=>r.json()).then(rows => {
            const isos = Array.from(new Set(rows.map(r => (r.ISO3||'').toString().toUpperCase()).filter(Boolean)));
            if (addToggle){
              const current = new Set(Array.from(window.__selectedIsos || []));
              isos.forEach(i => current.has(i) ? current.delete(i) : current.add(i));
              window.__selectedIsos = new Set(current);
            } else {
              window.__selectedIsos = new Set(isos);
            }
            const arr = Array.from(window.__selectedIsos);
            window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
            window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { rows } }));
            window.dispatchEvent(new CustomEvent('countrySelected', { detail: { isos: arr } }));
          });
        } else if (d.depth === 1){
          // Click en RN/NR -> agrupa todas sus tecnologías
          const childTechs = (d.children||[]).map(c=>c.data.name);
          fetch(`/api/data${qYear ? '?year='+encodeURIComponent(yr) : ''}`).then(r=>r.json()).then(rows => {
            const filtered = rows.filter(r => childTechs.includes(r.Technology));
            const isos = Array.from(new Set(filtered.map(r => (r.ISO3||'').toString().toUpperCase()).filter(Boolean)));
            if (addToggle){
              const current = new Set(Array.from(window.__selectedIsos || []));
              isos.forEach(i => current.has(i) ? current.delete(i) : current.add(i));
              window.__selectedIsos = new Set(current);
            } else {
              window.__selectedIsos = new Set(isos);
            }
            const arr = Array.from(window.__selectedIsos);
            window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
            window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { rows: filtered } }));
            window.dispatchEvent(new CustomEvent('countrySelected', { detail: { isos: arr } }));
          });
        }
      });

    // Labels internos (porcentajes RN / NR)
    const innerNodes = root.descendants().filter(d => d.depth === 1);
    const innerLabelArc = d3.arc().innerRadius(d => d.y0 + (d.y1 - d.y0)/2).outerRadius(d => d.y0 + (d.y1 - d.y0)/2);
    g.selectAll('text.innerLabel').data(innerNodes).join('text')
      .attr('class','innerLabel')
      .attr('transform', d => {
        const [x,y] = innerLabelArc.centroid(d);
        return `translate(${x},${y})`;
      })
      .attr('text-anchor','middle')
      .style('fill','#fff').style('font-weight',700).style('font-size','12px')
      .text(d => total ? (d.value / total * 100).toFixed(1) + '%' : '0%');

    // Labels externos (solo en arcos grandes)
    const outerNodes = root.descendants().filter(d => d.depth === 2 && (d.x1 - d.x0) > 0.06);
    const outerLabelArc = d3.arc().innerRadius(d => (d.y0 + d.y1)/2).outerRadius(d => (d.y0 + d.y1)/2);
    g.selectAll('text.outerLabel').data(outerNodes).join('text')
      .attr('class','outerLabel')
      .attr('transform', d => {
        const [x,y] = outerLabelArc.centroid(d);
        return `translate(${x},${y})`;
      })
      .attr('text-anchor','middle')
      .style('fill','#fff').style('font-weight',700).style('font-size','11px')
      .text(d => total ? (d.value / total * 100).toFixed(1) + '%' : '');

    // Total en el centro
    g.append('text')
      .attr('text-anchor','middle').attr('dy','-6px')
      .style('font-size','18px').style('font-weight','700')
      .style('fill', cssVar('--panel-text','#111'))
      .text(d3.format(',')(Math.round(total)));
    g.append('text')
      .attr('text-anchor','middle').attr('dy','18px')
      .style('font-size','12px')
      .style('fill', cssVar('--panel-text','#111'))
      .text('Total (unidad)');

    // Leyenda simple
    const legend = container.append('div').attr('class','legendBox');
    legend.append('div').style('font-weight','700').text('Leyenda (click = select; Ctrl+click = toggle)');
    legend.append('div').style('margin-top','8px').html(`
      <div style="display:flex;gap:8px;align-items:center">
        <div style="width:12px;height:12px;background:${colorInner('Renewable')};border-radius:2px"></div>
        <div>Renewable</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;margin-top:6px">
        <div style="width:12px;height:12px;background:${colorInner('Non-Renewable')};border-radius:2px"></div>
        <div>Non-Renewable</div>
      </div>
    `);

    container.node().scrollTop = 0;
  }

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

  const initialYear = 'F' + (document.getElementById('yearRange')?.value || '2023');
  fetchAndRender(null, initialYear);
})();
