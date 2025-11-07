// sunburst.js
(async function(){
  const container = d3.select('#sunburst');
  const width = container.node().clientWidth || 520;
  const radius = Math.min(width, 520) / 2;
  const svg = container.append('svg').attr('viewBox', [0,0,width,width]);
  const g = svg.append('g').attr('transform', `translate(${width/2},${width/2})`);
  const color = d3.scaleOrdinal(d3.schemeTableau10);

  async function loadAndRender(opts = {}) {
    const { yearCol='F2023', country=null } = opts;
    let url = `/api/hierarchy?year=${encodeURIComponent(yearCol)}`;
    if (country) url += `&country=${encodeURIComponent(country)}`;
    const rows = await fetch(url).then(r=>r.json());
    render(rows);
  }

  function render(rows){
    g.selectAll('*').remove();
    const map = new Map();
    for (const r of rows){
      const type = r.Energy_Type || 'Unknown';
      const tech = r.Technology || 'Other';
      const val = + (r.Energy_Value || r.Energy_Total || 0);
      if (!map.has(type)) map.set(type, new Map());
      const inner = map.get(type);
      inner.set(tech, (inner.get(tech) || 0) + val);
    }
    const rootObj = { name: 'root', children: Array.from(map.entries()).map(([type, inner]) => ({ name: type, children: Array.from(inner.entries()).map(([tech, val]) => ({ name: tech, value: val })) })) };
    const root = d3.hierarchy(rootObj).sum(d=> d.value || 0);
    d3.partition().size([2*Math.PI, radius])(root);

    const arc = d3.arc().startAngle(d=> d.x0).endAngle(d=> d.x1).innerRadius(d=> d.y0).outerRadius(d=> Math.max(d.y0, d.y1) - 1).padAngle(0.005);

    g.selectAll('path')
      .data(root.descendants().filter(d => d.depth))
      .join('path')
      .attr('d', arc)
      .attr('fill', d => {
        const top = d.ancestors().slice().reverse()[1];
        return color(top ? top.data.name : d.data.name);
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 0.6)
      .attr('fill-opacity', 0.95)
      .on('click', (e,d) => {
        const anc = d.ancestors().slice().reverse();
        const energy_type = (anc[1] && anc[1].data && anc[1].data.name) || (d.depth===1 ? d.data.name : null);
        const technology = (d.depth===2 ? d.data.name : (d.depth===1 ? null : d.data.name));
        window.dispatchEvent(new CustomEvent('sliceSelected', {detail: {energy_type, technology}}));
        g.selectAll('path').attr('opacity', 0.25);
        d3.select(e.currentTarget).attr('opacity', 1);
      });
  }

  // initial
  loadAndRender();

  window.addEventListener('yearChange', (ev) => loadAndRender({yearCol: ev.detail.year}));
  window.addEventListener('countrySelected', (ev) => {
    const isoList = ev.detail.isos || (ev.detail.iso ? [ev.detail.iso] : []);
    if (isoList && isoList.length === 1) {
      loadAndRender({yearCol: 'F' + (document.getElementById('yearRange')?.value || '2023'), country: isoList[0]});
    } else {
      // if multiple, still load global partition (default)
      loadAndRender();
    }
  });

})();
