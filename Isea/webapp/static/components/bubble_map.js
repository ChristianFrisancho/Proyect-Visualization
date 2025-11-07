// bubble_map.js - mapa + burbujas con resize, tema y brushing
(async function(){
  const container = d3.select('#bubble-map');
  container.selectAll('*').remove();

  let width = container.node().clientWidth || 900;
  let height = container.node().clientHeight || 700;

  const svg = container.append('svg')
    .attr('width','100%').attr('height','100%')
    .attr('viewBox', `0 0 ${width} ${height}`);

  const cssVar = (name, fallback) =>
    (getComputedStyle(document.documentElement).getPropertyValue(name) || fallback).trim() || fallback;

  let projection = d3.geoNaturalEarth1().scale(width/6.3).translate([width/2, height/2]);
  let path = d3.geoPath().projection(projection);

  const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
  const countries = topojson.feature(world, world.objects.countries).features;

  const landG = svg.append('g').attr('class','land');
  const bubbleG = svg.append('g').attr('class','bubbles');

  function paintLand(){
    const fill = cssVar('--panel-bg', '#e8eaed');
    const stroke = cssVar('--stroke-soft', 'rgba(0,0,0,0.08)');
    landG.selectAll('path').data(countries, d => d.id).join('path')
      .attr('d', path)
      .attr('fill', fill)
      .attr('stroke', stroke)
      .attr('stroke-width', 1)
      .attr('vector-effect','non-scaling-stroke');
  }

  const centroidCache = new Map();
  const recomputeCentroids = () => {
    centroidCache.clear();
    countries.forEach(f => {
      const props = f.properties || {};
      const iso = props.iso_a3 || props.ISO_A3 || props.ADM0_A3;
      const c = d3.geoCentroid(f);
      const p = projection(c);
      if (iso) centroidCache.set(String(iso).toUpperCase(), p);
      if (props.name) centroidCache.set(String(props.name).toLowerCase(), p);
    });
  };
  recomputeCentroids();

  window.__selectedIsos = window.__selectedIsos || new Set();
  let lastRows = [];

  async function loadAndDraw(yearCol){
    const url = `/api/data?year=${encodeURIComponent(yearCol)}`;
    const rows = await fetch(url).then(r => r.json());
    lastRows = rows;
    drawBubbles(rows);
  }

  function drawBubbles(rows){
    rows.forEach(d => {
      const iso = (d.ISO3 || '').toString().toUpperCase();
      let pos = centroidCache.get(iso) ||
                centroidCache.get(String(d.Country||'').toLowerCase());
      if (!pos){
        const key = (d.ISO3 || d.Country || '').toString();
        let seed = 0; for (let i=0;i<key.length;i++) seed += key.charCodeAt(i);
        const angle = (seed % 360) * Math.PI/180;
        const r = 200 + (seed % 160);
        pos = [width/2 + Math.cos(angle)*r, height/2 + Math.sin(angle)*r];
      }
      d.cx = pos[0]; d.cy = pos[1];
    });

    const maxVal = d3.max(rows, r => +r.Energy_Value || 0) || 1;
    const rScale = d3.scaleSqrt().domain([0,maxVal]).range([2,28]);

    const strokeSel = cssVar('--text', '#111');
    const fillBub = cssVar('--accent', '#2ca9b7');

    const circles = bubbleG.selectAll('circle').data(rows, d => (d.ISO3 || d.Country));

    circles.join(
      enter => enter.append('circle')
        .attr('cx', d => d.cx).attr('cy', d => d.cy)
        .attr('r', 0)
        .attr('fill', fillBub)
        .attr('stroke', '#fff').attr('stroke-width', 0.8).attr('opacity', 0.9)
        .on('mouseover', (e,d) => {
          const tip = d3.select('#tooltip');
          tip.style('visibility','visible').html(
            `<strong>${d.Country}</strong><div>${d.Energy_Type}</div><div>${d3.format(',')(Math.round(d.Energy_Value||0))}</div>`
          );
        })
        .on('mousemove', (e) => d3.select('#tooltip')
          .style('top',(e.pageY+10)+'px').style('left',(e.pageX+12)+'px'))
        .on('mouseout', () => d3.select('#tooltip').style('visibility','hidden'))
        .on('click', (e,d) => {
          const iso = (d.ISO3 || '').toString().toUpperCase();
          if (window.__selectedIsos.has(iso)) window.__selectedIsos.delete(iso);
          else window.__selectedIsos.add(iso);
          const arr = Array.from(window.__selectedIsos);
          window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: arr } }));
          window.dispatchEvent(new CustomEvent('countrySelected', { detail: { isos: arr } }));
          refreshSelection(strokeSel);
        })
        .call(sel => sel.transition().duration(450).attr('r', d => rScale(+d.Energy_Value || 0))),
      update => update
        .transition().duration(300)
        .attr('cx', d => d.cx).attr('cy', d => d.cy)
        .attr('r', d => rScale(+d.Energy_Value || 0)),
      exit => exit.transition().duration(240).attr('r', 0).remove()
    );

    refreshSelection(strokeSel);
  }

  function refreshSelection(strokeSel){
    const hasSel = window.__selectedIsos && window.__selectedIsos.size;
    svg.selectAll('g.bubbles circle')
      .attr('opacity', d => hasSel ? (window.__selectedIsos.has(((d.ISO3||'')+'').toUpperCase()) ? 1 : 0.15) : 0.9)
      .attr('stroke-width', d => (window.__selectedIsos.has(((d.ISO3||'')+'').toUpperCase()) ? 2 : 0.8))
      .attr('stroke', d => (window.__selectedIsos.has(((d.ISO3||'')+'').toUpperCase()) ? strokeSel : '#fff'));
  }

  window.addEventListener('selectionChanged', ev => {
    const isos = ev.detail.isos || [];
    window.__selectedIsos = new Set(isos.map(s => (s||'').toString().toUpperCase()));
    refreshSelection(cssVar('--text', '#111'));
  });

  window.addEventListener('yearChange', ev => {
    const year = ev.detail.year || 'F2023';
    loadAndDraw(year);
  });

  window.addEventListener('highlightCountries', ev => {
    const rows = ev.detail.rows || [];
    const setIso = new Set(rows.map(r => String(r.ISO3||'').toUpperCase()));
    svg.selectAll('g.bubbles circle').attr('opacity', d => setIso.size ? (setIso.has(((d.ISO3||'')+'').toUpperCase()) ? 1 : 0.12) : (window.__selectedIsos.size?0.15:0.9));
  });

  window.addEventListener('themeChanged', ()=> { paintLand(); refreshSelection(cssVar('--text', '#111')); });

  const ro = new ResizeObserver(entries => {
    const cr = entries[0].contentRect;
    width = cr.width; height = cr.height;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    projection = d3.geoNaturalEarth1().scale(width/6.3).translate([width/2, height/2]);
    path = d3.geoPath().projection(projection);
    recomputeCentroids();
    paintLand();
    if (lastRows.length) drawBubbles(lastRows);
  });
  ro.observe(container.node());

  paintLand();
  loadAndDraw('F' + (document.getElementById('yearRange')?.value || '2023'));
})();
