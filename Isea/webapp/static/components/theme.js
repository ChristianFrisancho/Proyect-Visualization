const THEME_KEY = "vis-theme";
const initial = localStorage.getItem(THEME_KEY) || "light";
if (initial === "dark") document.body.classList.add("dark");
const btn = document.getElementById("theme-toggle");
if (btn) btn.addEventListener("click", () => {
  const isDark = document.body.classList.toggle("dark");
  localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
});
