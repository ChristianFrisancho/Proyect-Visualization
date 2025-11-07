// country_panel.js (final: UN SOLO DONUT con 2 capas)
(function(){
  const container = d3.select('#countryPanel');

  function isRenewable(typeStr){
    if (!typeStr) return false;
    return String(typeStr).toLowerCase().includes('renewable');
  }

  // color map for Energy_Type (outer ring)
  function buildTypeColorScale(types){
    // Use categorical scheme, fallback to interpolation for many types
    const base = d3.schemeTableau10.concat(d3.schemeCategory10);
    const scale = d3.scaleOrdinal().domain(types).range(base.slice(0, Math.max(types.length, base.length)));
    return scale;
  }

  async function renderForIsos(isos){
    container.selectAll('*').remove();
    container.style('display','block');

    if (!isos || !isos.length){
      container.append('div').text('No hay países seleccionados.');
      return;
    }

    const yearCol = 'F' + (document.getElementById('yearRange')?.value || '2023');
    const url = `/api/countries_breakdown?isos=${encodeURIComponent(isos.join(','))}&year=${encodeURIComponent(yearCol)}`;
    const body = await fetch(url).then(r=>r.json());

    const top = container.append('div').style('display','flex').style('justify-content','space-between').style('align-items','center').style('margin-bottom','8px');
    top.append('h3').text(`${isos.length} seleccionados · Año ${yearCol.replace('F','')}`);
    const actions = top.append('div');
    const firstIso = isos.length === 1 ? isos[0] : null;
    actions.append('button').text('Download CSV')
      .attr('disabled', isos.length !== 1 ? true : null)
      .style('margin-left','8px')
      .on('click', () => { if (firstIso) window.open(`/api/download_country_csv?iso=${encodeURIComponent(firstIso)}`, '_blank'); });
    actions.append('button').text('Reset selección').style('margin-left','8px').on('click', () => {
      window.dispatchEvent(new CustomEvent('clearHighlights'));
      container.style('display','none');
      container.selectAll('*').remove();
    });

    // Layout
    const layout = container.append('div').style('display','flex').style('gap','12px').style('align-items','flex-start');

    const left = layout.append('div').style('flex','1').style('min-width','340px');
    const w = Math.min(460, left.node().clientWidth || 420);
    const h = 460;
    const svg = left.append('svg').attr('width', w).attr('height', h).style('display','block').style('margin','0 auto');
    const g = svg.append('g').attr('transform', `translate(${w/2},${h/2})`);

    const data = (body.breakdown || []).filter(d => (d.Energy_Value || 0) > 0);
    const total = body.total || data.reduce((s,d)=> s + (d.Energy_Value || 0), 0);

    if (!data.length) {
      left.append('div').text('Sin datos para la selección.');
    } else {
      // build colors for types (outer ring)
      const types = data.map(d => d.Energy_Type);
      const typeColor = buildTypeColorScale(types);

      // outer ring: Energy_Type
      const pieOuter = d3.pie().value(d => d.Energy_Value).sort(null);
      const radius = Math.min(w,h)/2 - 8;
      const outerArc = d3.arc().innerRadius(radius * 0.60).outerRadius(radius);

      const outer = g.selectAll('path.outer').data(pieOuter(data)).join('path')
        .attr('class','outer')
        .attr('d', outerArc)
        .attr('fill', d => typeColor(d.data.Energy_Type))
        .attr('stroke', 'rgba(255,255,255,0.7)')
        .attr('stroke-width', 0.6)
        .on('mouseenter', (e,d) => {
          const pct = (d.data.pct !== undefined) ? d.data.pct.toFixed(2)+'%' : ((d.data.Energy_Value/total*100).toFixed(2)+'%');
          d3.select('#tooltip').style('visibility','visible').html(`<strong>${d.data.Energy_Type}</strong><div>${d3.format(',')(Math.round(d.data.Energy_Value))} (${pct})</div><div style="margin-top:6px">Click para resaltar países con este tipo</div>`);
        })
        .on('mousemove', (e) => d3.select('#tooltip').style('top',(e.pageY+12)+'px').style('left',(e.pageX+12)+'px'))
        .on('mouseleave', () => d3.select('#tooltip').style('visibility','hidden'))
        .on('click', (e,d) => {
          window.dispatchEvent(new CustomEvent('sliceSelected', {detail: {energy_type: d.data.Energy_Type, technology: null}}));
        });

      // inner ring: Renewable vs Non Renewable (2 segments)
      // compute sums
      let renewSum = 0, nonSum = 0;
      data.forEach(it => {
        if (isRenewable(it.Energy_Type)) renewSum += (it.Energy_Value || 0);
        else nonSum += (it.Energy_Value || 0);
      });
      const innerData = [{label:'Renewable', value: renewSum},{label:'Non-Renewable', value: nonSum}];
      const pieInner = d3.pie().value(d=> d.value).sort(null);
      const innerArc = d3.arc().innerRadius(radius*0.2).outerRadius(radius*0.55);
      const colorRN = d3.scaleOrdinal().domain(['Renewable','Non-Renewable']).range(['#ff7f0e','#2ca9b7']);

      const inner = g.selectAll('path.inner').data(pieInner(innerData)).join('path')
        .attr('class','inner')
        .attr('d', innerArc)
        .attr('fill', d => colorRN(d.data.label))
        .attr('stroke', 'rgba(255,255,255,0.85)')
        .attr('stroke-width', 0.5)
        .on('mouseenter', (e,d) => {
          const totalRN = renewSum + nonSum || 1;
          const pct = ((d.data.value / totalRN) * 100).toFixed(2) + '%';
          d3.select('#tooltip').style('visibility','visible').html(`<strong>${d.data.label}</strong><div>${d3.format(',')(Math.round(d.data.value || 0))} (${pct})</div><div style="margin-top:6px">Click para resaltar</div>`);
        })
        .on('mousemove', (e) => d3.select('#tooltip').style('top',(e.pageY+12)+'px').style('left',(e.pageX+12)+'px'))
        .on('mouseleave', () => d3.select('#tooltip').style('visibility','hidden'))
        .on('click', (e,d) => {
          window.dispatchEvent(new CustomEvent('sliceSelected', {detail: {energy_type: null, technology: d.data.label}}));
        });

      // labels for outer slices (only larger ones)
      const labelArc = d3.arc().innerRadius(radius * 0.77).outerRadius(radius * 0.9);
      g.selectAll('text.label').data(pieOuter(data)).join('text')
        .attr('class','label')
        .each(function(d){
          if ((d.endAngle - d.startAngle) < 0.06) return; // skip tiny
          const [x,y] = labelArc.centroid(d);
          d3.select(this).attr('transform', `translate(${x},${y})`).attr('text-anchor','middle').style('font-size','12px').style('fill','#fff').style('font-weight',700)
            .text(((d.data.pct !== undefined) ? (d.data.pct.toFixed(1)+'%') : ((d.data.Energy_Value/total*100).toFixed(1)+'%')));
        });

      // center total
      g.append('text').attr('text-anchor','middle').attr('dy','-6px').style('font-size','18px').style('font-weight','700').style('fill','var(--panel-text)').text(d3.format(',')(Math.round(total)));
      g.append('text').attr('text-anchor','middle').attr('dy','18px').style('font-size','12px').style('fill','var(--panel-text)').text('Total (unidad)');
    }

    // Right column: legend + techs
    const right = layout.append('div').style('width','320px');
    right.append('h4').text('Leyenda (Energy_Type)').style('margin-top','6px');

    (data || []).forEach(d => {
      const row = right.append('div').style('display','flex').style('align-items','center').style('gap','8px').style('margin-bottom','6px');
      const types = (body.breakdown || []).map(b=>b.Energy_Type);
      const typeColor = buildTypeColorScale(types);
      row.append('div').style('width','14px').style('height','14px').style('background', typeColor(d.Energy_Type)).style('border-radius','2px');
      row.append('div').text(`${d.Energy_Type} — ${ (d.pct !== undefined ? d.pct.toFixed(2) : ( (d.Energy_Value/ (body.total||1) * 100).toFixed(2) ) ) }%`).style('font-size','13px').style('color','var(--panel-text)');
    });

    right.append('h4').text('Top Technologies').style('margin-top','12px');
    const techs = body.tech_breakdown || [];
    const ttable = right.append('table').style('width','100%');
    const tbody = ttable.append('tbody');
    tbody.selectAll('tr').data(techs.slice(0,10)).join('tr').call(tr => {
      tr.append('td').text((d,i)=> i+1).style('width','24px').style('color','var(--panel-text)');
      tr.append('td').text(d=> d.Technology).style('color','var(--panel-text)');
      tr.append('td').text(d=> d3.format(',')(Math.round(d.Energy_Value))).style('text-align','right').style('color','var(--panel-text)');
      tr.append('td').text(d=> (d.pct||0) + '%').style('text-align','right').style('padding-left','8px').style('color','var(--panel-text)');
    });
  }

  // listeners
  window.addEventListener('selectionChanged', (ev) => {
    const isos = ev.detail.isos || [];
    if (!isos || isos.length === 0) {
      container.style('display','none');
      container.selectAll('*').remove();
      return;
    }
    renderForIsos(isos);
  });

  window.addEventListener('countrySelected', (ev) => {
    const detail = ev.detail || {};
    const isos = detail.isos || (detail.iso ? [detail.iso] : []);
    if (!isos || isos.length === 0) return;
    renderForIsos(isos);
  });

  window.addEventListener('clearHighlights', () => {
    container.style('display','none');
    container.selectAll('*').remove();
  });

})();
