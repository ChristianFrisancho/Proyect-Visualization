# Isea/widgets.py
from IPython.display import Javascript, HTML, display

def ensure_bus():
    """
    Inject a shared JavaScript event bus and base CSS into the notebook.

    This function should be called once (typically near the top of a
    notebook) before displaying any Isea widgets that rely on
    cross-widget communication or shared styling.

    Behaviour
    ---------
    - In the browser, it checks ``window.__isea_bus_ready__`` and returns
      immediately if the bus has already been installed. This makes the
      function safe to call multiple times from different cells.
    - If not yet installed, it creates:

      * ``window.IseaBus`` – a very small global event bus with methods:

        - ``on(type, handler)`` to subscribe to an event.
        - ``off(type, handler)`` to unsubscribe.
        - ``emit(type, detail)`` to broadcast an event with an optional
          ``detail`` payload (wrapped in a ``CustomEvent``).

      * A ``<style>`` tag with base CSS classes:

        - ``.isea-grid`` – grid layout helper.
        - ``.isea-card`` – dark card container for widgets.
        - ``.isea-title`` – title styling.
        - ``.isea-subtle`` – subtle subtitle / helper text styling.

    Usage
    -----
    In a notebook:

    .. code-block:: python

        from Isea.widgets import ensure_bus
        ensure_bus()  # call once before showing Isea widgets

    The JavaScript parts of the Isea visualisations can then use
    ``window.IseaBus`` to coordinate interactions (e.g. selecting a
    country in one view and reacting in another).
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
    """
    Create a styled HTML card container for embedding a widget.

    This helper returns a small HTML snippet that uses the base Isea CSS
    classes injected by :func:`ensure_bus`. It is useful for giving a
    consistent dark-card framing to widgets or other HTML content.

    Parameters
    ----------
    title : str
        Main title text shown at the top of the card.
    subtitle : str, optional
        Optional secondary line shown below the title in a subtler style.
        If an empty string is passed (the default), the subtitle element
        is omitted.

    Returns
    -------
    IPython.display.HTML
        An HTML object that renders a ``<div class="isea-card">`` with:

        - A title element: ``<div class="isea-title">…``.
        - An optional subtitle: ``<div class="isea-subtle">…``.
        - An empty slot container: ``<div class="isea-slot"></div>`` where
          you can later insert a widget using ``display`` in another cell
          or by composing HTML.

    Example
    -------
    .. code-block:: python

        from Isea.widgets import ensure_bus, card
        ensure_bus()
        display(card("EV adoption", "Click a country in the map to begin"))
    """
    return HTML(f"""
<div class="isea-card">
  <div class="isea-title">{title}</div>
  {f'<div class="isea-subtle">{subtitle}</div>' if subtitle else ''}
  <div class="isea-slot"></div>
</div>
""")
