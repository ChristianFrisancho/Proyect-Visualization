from traitlets import Unicode, Dict
from .base_widget import IseaWidget

BAR_ESM = """
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7/+esm';

export function render({ model, el }) {
  el.innerHTML = '';
  const width  = model.get('width');
  const height = model.get('height');
  const title  = model.get('title') || 'Isea Bar';
  const opts   = model.get('options') || {};
  const margin = {top:30,right:20,bottom:40,left:50, ...(opts.margin||{})};

  const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  g.append('text').attr('x', innerW/2).attr('y', -10)
    .attr('text-anchor','middle').attr('font-weight',600).text(title);

  function update(){
    const data = model.get('data') || [];
    const xKey = (model.get('options')?.x) || 'label';
    const yKey = (model.get('options')?.y) || 'value';

    const x = d3.scaleBand().domain(data.map(d=>d[xKey])).range([0,innerW]).padding(0.2);
    const y = d3.scaleLinear().domain([0, d3.max(data, d=>+d[yKey]) || 0]).nice()
                 .range([innerH,0]);

    g.selectAll('.x-axis').data([null]).join('g')
      .attr('class','x-axis').attr('transform',`translate(0,${innerH})`)
      .call(d3.axisBottom(x).tickSizeOuter(0));
    g.selectAll('.y-axis').data([null]).join('g')
      .attr('class','y-axis').call(d3.axisLeft(y));

    const bars = g.selectAll('.bar').data(data, d=>d[xKey]);
    bars.join(
      enter => enter.append('rect').attr('class','bar')
        .attr('x', d=>x(d[xKey])).attr('y', innerH)
        .attr('width', x.bandwidth()).attr('height',0)
        .call(enter=>enter.transition().duration(500)
          .attr('y', d=>y(+d[yKey])).attr('height', d=>innerH - y(+d[yKey]))),
      update => update.call(u=>u.transition().duration(400)
          .attr('x', d=>x(d[xKey])).attr('y', d=>y(+d[yKey]))
          .attr('width', x.bandwidth()).attr('height', d=>innerH - y(+d[yKey]))),
      exit => exit.call(x=>x.transition().duration(300).attr('y',innerH).attr('height',0).remove())
    );
  }

  update();
  model.on('change:data change:options change:width change:height change:title', update);
}
"""

class Bar(IseaWidget):
    """Bar chart: data = [{'label': str, 'value': number}, ...]"""
    _esm = Unicode(BAR_ESM).tag(sync=True)
    options = Dict({"x":"label","y":"value"}).tag(sync=True)


SCATTER_ESM = """
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7/+esm';
export function render({ model, el }) {
  el.innerHTML = '';
  const w = model.get('width'), h = model.get('height'), m = {top:20,right:20,bottom:40,left:50};
  const svg = d3.select(el).append('svg').attr('width', w).attr('height', h);
  const g = svg.append('g').attr('transform', `translate(${m.left},${m.top})`);
  const innerW = w - m.left - m.right, innerH = h - m.top - m.bottom;

  function update(){
    const data = model.get('data') || [];
    const ox = model.get('options') || {};
    const xKey = ox.x || 'x', yKey = ox.y || 'y';

    const x = d3.scaleLinear().domain(d3.extent(data, d=>+d[xKey])).nice().range([0, innerW]);
    const y = d3.scaleLinear().domain(d3.extent(data, d=>+d[yKey])).nice().range([innerH, 0]);

    g.selectAll('.x').data([null]).join('g').attr('class','x')
      .attr('transform',`translate(0,${innerH})`).call(d3.axisBottom(x));
    g.selectAll('.y').data([null]).join('g').attr('class','y').call(d3.axisLeft(y));

    g.selectAll('circle').data(data).join('circle')
      .attr('cx', d=>x(+d[xKey])).attr('cy', d=>y(+d[yKey])).attr('r', 3);
  }
  update();
  model.on('change:data change:options change:width change:height', update);
}
"""

class Scatter(IseaWidget):
    _esm = Unicode(SCATTER_ESM).tag(sync=True)
    options = Dict({"x":"x","y":"y"}).tag(sync=True)
