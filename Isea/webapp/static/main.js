// main.js - slider, play y status
(async function(){
  const status = document.getElementById('statusbar');
  const yearsResp = await fetch('/api/years').then(r => r.json());
  const years = yearsResp.years || [];
  const yearRange = document.getElementById('yearRange');
  const yearLabel = document.getElementById('yearLabel');
  const playBtn = document.getElementById('playPause');

  if (years.length){
    yearRange.min = Math.min(...years);
    yearRange.max = Math.max(...years);
    yearRange.value = yearRange.max;
    yearLabel.innerText = yearRange.value;
  }

  function dispatchYear(y){
    const val = String(y).startsWith('F') ? y : 'F' + y;
    window.dispatchEvent(new CustomEvent('yearChange', { detail: { year: val } }));
    if (status) status.textContent = `Año activo: ${String(y).replace(/^F/,'')}`;
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
      let v = Number(yearRange.value) + 1;
      if (v > Number(yearRange.max)) v = Number(yearRange.min);
      yearRange.value = v; yearLabel.innerText = v;
      dispatchYear(v);
    }, 900);
  });

  document.addEventListener('visibilitychange', ()=> {
    if (document.hidden && playing){ clearInterval(intervalId); playing = false; playBtn.textContent = '▶️'; }
  });

  dispatchYear(yearRange.value);
})();
