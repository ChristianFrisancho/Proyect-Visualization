# Isea/widgets.py
from IPython.display import Javascript, HTML, display

def ensure_bus():
    """
    Inyecta un EventBus global (window.IseaBus) una sola vez y estilos base.
    """
    display(Javascript(r"""
    (function(){
      if(window.__isea_bus_ready__) return;
      window.__isea_bus_ready__ = true;

      // Bus simple
      if(!window.IseaBus){
        window.IseaBus = new class {
          constructor(){ this.tgt = new EventTarget(); }
          on(t, h){ this.tgt.addEventListener(t, h); }
          off(t, h){ this.tgt.removeEventListener(t, h); }
          emit(t, detail){ this.tgt.dispatchEvent(new CustomEvent(t, {detail})); }
        };
      }

      // CSS base para contenedores y tooltips (oscuro elegante)
      const css = `
      .isea-grid{ display:grid; gap:14px; }
      .isea-card{ background:#111827; border:1px solid #1f2937; border-radius:10px; padding:10px; }
      .isea-title{ color:#e5e7eb; font:600 14px/1.2 sans-serif; margin:2px 0 6px; }
      .isea-subtle{ color:#94a3b8; font:12px/1.35 sans-serif; margin-bottom:8px; }
      `
      const tag = document.createElement('style');
      tag.setAttribute('data-isea','bus');
      tag.innerHTML = css;
      document.head.appendChild(tag);
    })();
    """))

def card(title, subtitle=""):
    return HTML(f"""
<div class="isea-card">
  <div class="isea-title">{title}</div>
  {f'<div class="isea-subtle">{subtitle}</div>' if subtitle else ''}
  <div class="isea-slot"></div>
</div>
""")
