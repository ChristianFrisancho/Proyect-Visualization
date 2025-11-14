// bubble_map.js — versión adaptada para ISEA sin API, usando window.__ENERGY_DATA

(async function () {
  const container = d3.select('#bubble-map');
  container.selectAll('*').remove();

  const width = container.node().clientWidth || 900;
  const height = container.node().clientHeight || 700;

  const svg = container.append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`);

  const projection = d3.geoNaturalEarth1()
    .scale(width / 6.3)
    .translate([width / 2, height / 2]);

  const geo = d3.geoPath(projection);

  // Load topojson from assets
  const world = await d3.json("world.json");
  const features = topojson.feature(world, world.objects.countries).features;

  // draw map
  svg.append('g').attr('class', 'basemap')
    .selectAll('path')
    .data(features)
    .join('path')
    .attr('d', geo)
    .attr('fill', '#e2e8f0')
    .attr('stroke', '#94a3b8')
    .attr('stroke-width', 0.5);

  const centroidPx = new Map();
  features.forEach(f => {
    const props = f.properties || {};
    const iso = props.ISO_A3 || props.iso_a3;
    const pt = geo.centroid(f);
    if (iso) centroidPx.set(String(iso).toUpperCase(), pt);
  });

  // window.__ENERGY_DATA is filled by Python
  const DATA = window.__ENERGY_DATA || [];

  function loadAndDraw(year) {
    const rows = DATA.filter(r => r.year === year);

    const isoAgg = new Map();
    rows.forEach(r => {
      if (!isoAgg.has(r.ISO3)) {
        isoAgg.set(r.ISO3, {
          iso: r.ISO3,
          country: r.Country,
          total: 0
        });
      }
      isoAgg.get(r.ISO3).total += r.Energy_Value;
    });

    const bubbles = [];
    isoAgg.forEach(o => {
      const pt = centroidPx.get(o.iso);
      if (!pt) return;
      bubbles.push({
        iso: o.iso,
        country: o.country,
        total: o.total,
        cx: pt[0],
        cy: pt[1]
      });
    });

    const maxTotal = d3.max(bubbles, d => d.total) || 1;
    const rScale = d3.scaleSqrt().domain([0, maxTotal]).range([2, 26]);

    svg.selectAll("g.bubbles").remove();
    const g = svg.append("g").attr("class", "bubbles");

    g.selectAll("circle")
      .data(bubbles)
      .join("circle")
      .attr("cx", d => d.cx)
      .attr("cy", d => d.cy)
      .attr("r", d => rScale(d.total))
      .attr("fill", "#3b82f6")
      .attr("opacity", .85);
  }

  // listen to slider
  window.addEventListener("yearChange", ev => {
    loadAndDraw(ev.detail.year);
  });

  loadAndDraw(2023);
})();
