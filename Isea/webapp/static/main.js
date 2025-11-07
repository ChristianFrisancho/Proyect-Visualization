// main.js
let playing = false, playInterval = null;

(async function(){
  const r = await fetch('/api/years').then(r=>r.json());
  const years = r.years.sort((a,b)=>a-b);
  const minY = years[0] || 2000;
  const maxY = years[years.length-1] || 2023;

  const yearRange = document.getElementById('yearRange');
  const yearLabel = document.getElementById('yearLabel');
  const playBtn = document.getElementById('playPause');

  yearRange.min = minY;
  yearRange.max = maxY;
  yearRange.value = maxY;
  yearLabel.innerText = yearRange.value;

  function dispatchYear(y){
    const yearCol = 'F' + y;
    window.dispatchEvent(new CustomEvent('yearChange', {detail: {year: yearCol}}));
  }

  yearRange.addEventListener('input', (e) => {
    yearLabel.innerText = e.target.value;
    dispatchYear(e.target.value);
  });

  playBtn.addEventListener('click', () => {
    if (playing){
      playing = false; clearInterval(playInterval); playBtn.textContent = '▶️';
    } else {
      playing = true; playBtn.textContent = '⏸️';
      playInterval = setInterval(() => {
        let val = Number(yearRange.value);
        val = val + 1;
        if (val > Number(yearRange.max)) val = Number(yearRange.min);
        yearRange.value = val; yearLabel.innerText = val;
        dispatchYear(val);
      }, 900);
    }
  });

  // when sunburst slice selected -> fetch countries and highlight
  window.addEventListener('sliceSelected', (ev) => {
    const {energy_type, technology} = ev.detail;
    const yearCol = 'F' + (document.getElementById('yearRange').value || 2023);
    const techParam = technology || energy_type;
    fetch(`/api/data?year=${encodeURIComponent(yearCol)}&technology=${encodeURIComponent(techParam)}`)
      .then(r=>r.json())
      .then(rows => window.dispatchEvent(new CustomEvent('highlightCountries', {detail: {rows, energy_type, technology}})));
  });

  // initial dispatch
  dispatchYear(yearRange.value);

})();
