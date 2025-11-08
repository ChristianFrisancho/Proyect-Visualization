// main.js - slider, autoplay y utilidades de selección/limpieza
(async function(){
  const yearsResp = await fetch('/api/years').then(r => r.json());
  const years = yearsResp.years || [];
  const yearRange = document.getElementById('yearRange');
  const yearLabel = document.getElementById('yearLabel');
  const playBtn = document.getElementById('playPause');
  const clearBtn = document.getElementById('clearSelection');

  if (years.length){
    yearRange.min = Math.min(...years);
    yearRange.max = Math.max(...years);
    yearRange.value = yearRange.max;
    yearLabel.innerText = yearRange.value;
  }

  function dispatchYear(y){
    const yearCol = 'F' + y;
    window.dispatchEvent(new CustomEvent('yearChange', { detail: { year: yearCol } }));
  }

  yearRange.addEventListener('input', (e)=> {
    yearLabel.innerText = e.target.value;
    dispatchYear(e.target.value);
  });

  let playing = false, intervalId = null;
  playBtn.addEventListener('click', () => {
    if (playing){ clearInterval(intervalId); playing = false; playBtn.textContent = '▶️'; return; }
    playing = true; playBtn.textContent = '⏸️';
    intervalId = setInterval(() => {
      let v = Number(yearRange.value);
      v = v + 1;
      if (v > Number(yearRange.max)) v = Number(yearRange.min);
      yearRange.value = v; yearLabel.innerText = v;
      dispatchYear(v);
    }, 900);
  });

  // 🧹 limpiar selección global (mapa + sunburst)
  clearBtn.addEventListener('click', () => {
    window.__selectedIsos = new Set();
    window.dispatchEvent(new CustomEvent('selectionChanged', { detail: { isos: [] } }));
    window.dispatchEvent(new CustomEvent('highlightCountries', { detail: { rows: [] } }));
  });

  // dispatch inicial
  dispatchYear(yearRange.value);
})();
