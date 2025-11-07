// bubble_map.js
(async function(){
  const container = d3.select('#bubble-map');
  const tooltip = d3.select('#tooltip');
  const width = container.node().clientWidth || 860;
  const height = container.node().clientHeight || 520;

  const svg = container.append('svg').attr('width', width).attr('height', height);
  const g = svg.append('g').attr('class','map-layer');

  const projection = d3.geoNaturalEarth1().scale(160).translate([width/2, height/2]);
  const path = d3.geoPath().projection(projection);

  const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
  const countries = topojson.feature(world, world.objects.countries).features;

  const nameMap = new Map(), isoMap = new Map();
  countries.forEach(f => {
    const p = f.properties || {};
    const names = [p.name, p.NAME, p.admin, p.name_long].filter(Boolean);
    names.forEach(n => nameMap.set(String(n).toLowerCase().replace(/[^\w\s]/g,'').trim(), f));
    const iso = p.iso_a3 || p.ISO_A3 || p.iso3 || p.ADM0_A3;
    if (iso) isoMap.set(String(iso).toUpperCase(), f);
  });

  function normalize(s){ return String(s||'').toLowerCase().replace(/[^\w\s]/g,'').trim(); }
  const manual = {
    "afghanistan, islamic rep. of": "AFG",
    "afghanistan, islamic rep of": "AFG",
    "united states of america": "USA",
    "united states": "USA",
    "korea, rep. of": "KOR",
    "iran, islamic rep. of": "IRN",
    "venezuela, rb": "VEN",
    "bolivia (plurinational state of)": "BOL"
  };

  function findFeature(countryName, iso3){
    if (iso3 && isoMap.has(String(iso3).toUpperCase())) return isoMap.get(String(iso3).toUpperCase());
    const manualIso = manual[normalize(countryName)];
    if (manualIso && isoMap.has(manualIso)) return isoMap.get(manualIso);
    const n = normalize(countryName);
    if (nameMap.has(n)) return nameMap.get(n);
    const token = n.split(' ')[0];
    for (const [k,f] of nameMap.entries()) if (k.includes(token) || token.includes(k)) return f;
    return null;
  }

  // draw map in g
  g.selectAll('path.country').data(countries).join('path')
    .attr('class','country')
    .attr('d', path)
    .attr('fill', getComputedStyle(document.documentElement).getPropertyValue('--map-fill') || '#d3d3d3')
    .attr('stroke', getComputedStyle(document.documentElement).getPropertyValue('--map-stroke') || '#777')
    .attr('stroke-width', 0.5);

  // centroid cache
  const centroidCache = new Map();
  countries.forEach(f => {
    const p = f.properties || {};
    const iso = p.iso_a3 || p.ISO_A3 || p.iso3 || p.ADM0_A3;
    const cent = d3.geoCentroid(f);
    const proj = projection(cent);
    if (iso) centroidCache.set(String(iso).toUpperCase(), proj);
    [p.name, p.NAME, p.admin, p.name_long].filter(Boolean).forEach(n => centroidCache.set(normalize(n), proj));
  });

  const bubblesGroup = g.append('g').attr('class','bubbles');
  let selected = new Set();
  window.__selectedIsos = new Set();

  async function draw(yearCol='F2023', highlightSet=null){
    const resp = await fetch(`/api/data?year=${encodeURIComponent(yearCol)}`);
    const data = await resp.json();

    data.forEach(d => {
      const iso = (d.ISO3 || '').toString().toUpperCase();
      let pos = null;
      if (centroidCache.has(iso)) pos = centroidCache.get(iso);
      if (!pos && manual[normalize(d.Country)]) {
        const m = manual[normalize(d.Country)];
        if (centroidCache.has(m)) pos = centroidCache.get(m);
      }
      if (!pos){
        const f = findFeature(d.Country, d.ISO3);
        if (f){
          const c = d3.geoCentroid(f);
          pos = projection(c);
          if (d.ISO3) centroidCache.set(d.ISO3.toUpperCase(), pos);
          centroidCache.set(normalize(d.Country), pos);
        }
      }
      if (pos){ d.cx = pos[0]; d.cy = pos[1]; d.onland = true; }
      else {
        const key = (d.ISO3 || d.Country);
        const seed = String(key).split('').reduce((s,c)=> s + c.charCodeAt(0), 0);
        const angle = ((seed % 360) * Math.PI/180);
        const r = 200 + (seed % 80);
        d.cx = width/2 + Math.cos(angle) * r;
        d.cy = height/2 + Math.sin(angle) * r;
        d.onland = false;
      }
    });

    const maxVal = d3.max(data, d => +d.Energy_Value || 0) || 1;
    const size = d3.scaleSqrt().domain([0, maxVal]).range([2,28]);

    const circles = bubblesGroup.selectAll('circle').data(data, d => d.ISO3 || d.Country);

    circles.join(
      enter => enter.append('circle')
        .attr('cx', d => d.cx).attr('cy', d => d.cy)
        .attr('r', 0)
        .attr('fill', getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#2ca9b7')
        .attr('stroke','#fff').attr('stroke-width',0.6).attr('opacity',0.85)
        .on('mouseover', (e,d) => {
          d3.select(e.currentTarget).raise().transition().duration(120).attr('r', size(+d.Energy_Value||0)*1.25);
          tooltip.style('visibility','visible').html(
            `<strong>${d.Country}</strong><div>Value: ${d3.format(',')(Math.round(d.Energy_Value || 0))}</div>
             <div style="margin-top:6px"><button id="toggleSelect">Toggle Select</button><button id="detailsBtn" style="margin-left:6px">Details</button></div>`
          );
          d3.select('#toggleSelect').on('click', ()=> { toggleSelect(d.ISO3); tooltip.style('visibility','hidden'); });
          d3.select('#detailsBtn').on('click', ()=> { openDetails(d.ISO3); tooltip.style('visibility','hidden'); });
        })
        .on('mousemove', (e)=> tooltip.style('top',(e.pageY+12)+'px').style('left',(e.pageX+12)+'px'))
        .on('mouseout', (e)=> { d3.select(e.currentTarget).transition().duration(120).attr('r', size(+d.Energy_Value||0)); tooltip.style('visibility','hidden'); })
        .on('click', (e,d)=> { openCountryPanel(d.ISO3); toggleSelect(d.ISO3, true); })
        .call(sel => sel.transition().duration(450).attr('r', d => size(+d.Energy_Value||0))),
      update => update.transition().duration(300).attr('cx', d=> d.cx).attr('cy', d=> d.cy).attr('r', d => size(+d.Energy_Value||0)),
      exit => exit.transition().duration(240).attr('r', 0).remove()
    );

    if (highlightSet && highlightSet.size){
      bubblesGroup.selectAll('circle').attr('opacity', d => highlightSet.has((d.ISO3||'').toUpperCase()) ? 1 : 0.12)
        .attr('stroke-width', d => highlightSet.has((d.ISO3||'').toUpperCase()) ? 1.6 : 0.6);
    } else {
      bubblesGroup.selectAll('circle').attr('opacity', d => selected.size ? (selected.has((d.ISO3||'').toUpperCase()) ? 1 : 0.12) : 0.85)
        .attr('stroke-width', d => selected.has((d.ISO3||'').toUpperCase()) ? 1.8 : 0.6)
        .attr('stroke', d => selected.has((d.ISO3||'').toUpperCase()) ? '#222' : '#fff');
    }
  }

  function toggleSelect(iso, keepPanel=false){
    if (!iso) return;
    const key = String(iso).toUpperCase();
    if (selected.has(key)) { selected.delete(key); window.__selectedIsos.delete(key); }
    else { selected.add(key); window.__selectedIsos.add(key); }
    bubblesGroup.selectAll('circle').attr('stroke-width', d => selected.has((d.ISO3||'').toUpperCase()) ? 2.2 : 0.6)
      .attr('stroke', d => selected.has((d.ISO3||'').toUpperCase()) ? '#222' : '#fff')
      .attr('opacity', d => selected.size ? (selected.has((d.ISO3||'').toUpperCase()) ? 1 : 0.12) : 0.85);
    const arr = Array.from(window.__selectedIsos);
    window.dispatchEvent(new CustomEvent('selectionChanged', {detail: {isos: arr}}));
    if (!keepPanel && selected.size===0) { document.getElementById('countryPanel').style.display = 'none'; }
  }

  async function openCountryPanel(clickedIso){
    // if there are selected ISOs, use them (aggregate), otherwise open for clicked iso
    const si = Array.from(window.__selectedIsos || []);
    const toUse = (si && si.length > 0) ? si : [clickedIso];
    window.dispatchEvent(new CustomEvent('countrySelected', {detail: {isos: toUse}}));
    document.getElementById('countryPanel').style.display = 'block';
  }

  async function openDetails(iso){
    if (!iso) return;
    const yearCol = 'F' + (document.getElementById('yearRange')?.value || '2023');
    const resp = await fetch(`/api/country_details?iso=${encodeURIComponent(iso)}&year=${encodeURIComponent(yearCol)}`);
    const rows = await resp.json();
    const w = window.open("", "_blank");
    w.document.write("<pre style='font-family:monospace'>"+JSON.stringify(rows, null, 2)+"</pre>");
  }

  window.addEventListener('yearChange', ev => draw(ev.detail.year));
  window.addEventListener('highlightCountries', ev => {
    const rows = ev.detail.rows || [];
    const setIso = new Set(rows.map(r => String(r.ISO3||'').toUpperCase()));
    draw('F' + (document.getElementById('yearRange')?.value || '2023'), setIso);
  });

  // initial draw
  draw('F' + (document.getElementById('yearRange')?.value || '2023'));

})();
