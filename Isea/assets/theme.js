// theme.js — versión ISEA (sin DOMContentLoaded)

(function () {

  const KEY = "vis-theme";

  function apply(mode) {
    const m = mode === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", m);
    localStorage.setItem(KEY, m);

    const btn = document.getElementById("theme-toggle");
    if (btn) btn.textContent = m === "dark" ? "Light" : "Dark";

    // Notificar a los gráficos
    window.dispatchEvent(
      new CustomEvent("themeChanged", { detail: { theme: m } })
    );
  }

  // Aplicar tema guardado
  const saved =
    document.documentElement.getAttribute("data-theme") ||
    localStorage.getItem(KEY) ||
    "light";

  apply(saved);

  // Listener del botón
  const btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.textContent = saved === "dark" ? "Light" : "Dark";
    btn.addEventListener("click", () => {
      const now =
        document.documentElement.getAttribute("data-theme") || "light";
      apply(now === "dark" ? "light" : "dark");
    });
  }

})();
