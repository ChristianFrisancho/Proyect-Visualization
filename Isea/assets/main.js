// main.js — versión para ISEA (sin DOMContentLoaded)

(async function () {

  const years = (window.__ENERGY_DATA?.years || []);
  const yearRange = document.getElementById('yearRange');
  const yearLabel = document.getElementById('yearLabel');
  const playBtn   = document.getElementById('playPause');
  const clearBtn  = document.getElementById('clearSelection');

  if (years.length && yearRange) {
    yearRange.min = Math.min(...years);
    yearRange.max = Math.max(...years);
    yearRange.value = yearRange.max;
    if (yearLabel) yearLabel.innerText = yearRange.value;
  }

  function dispatchYear(val){
    window.dispatchEvent(new CustomEvent('yearChange', {
      detail: { year: Number(val) }
    }));
  }

  if (yearRange) {
    yearRange.addEventListener('input', e => {
      const v = e.target.value;
      if (yearLabel) yearLabel.innerText = v;
      dispatchYear(Number(v));
    });
  }

  let playing = false;
  let intervalId = null;

  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (playing) {
        clearInterval(intervalId);
        playing = false;
        playBtn.textContent = '▶️';
        return;
      }
      playing = true;
      playBtn.textContent = '⏸️';

      intervalId = setInterval(() => {
        let v = Number(yearRange.value);
        v++;
        if (v > Number(yearRange.max)) v = Number(yearRange.min);
        yearRange.value = v;
        if (yearLabel) yearLabel.innerText = v;
        dispatchYear(Number(v));
      }, 900);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      window.__SELECTED_ISOS = [];
      window.dispatchEvent(new CustomEvent("selectionChanged", { detail: { isos: [] }}));
      window.dispatchEvent(new CustomEvent("highlightCountries", { detail: { isos: [] }}));
      window.dispatchEvent(new CustomEvent("clearSelection"));
    });
  }

  if (yearRange) {
    dispatchYear(Number(yearRange.value));
  }

})();
