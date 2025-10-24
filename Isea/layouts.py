# Isea/layouts.py
from IPython.display import HTML, Javascript, display
from .widgets import ensure_bus, card
from .medias import prepare_energy
from .graphs import BubblePack,WorldRenewable, ScatterBrushOld
from .parallel import ParallelEnergy

def LinkedEnergyDashboard(df, year=None, color_by="DominantTech", width=1280, height=900):
    """
    Crea una matriz 2×2 con vistas enlazadas:
      [ BubblePack | ParallelEnergy ]
      [ WorldMap   | ScatterBrush   ]
    - year: "F2023" o cualquier Fyyyy (si None usa el último con datos)
    - color_by: "DominantTech" o "Region" (si existe)
    """
    ensure_bus()

    pack = prepare_energy(df)
    Y = year or pack["year_default"]
    # grid responsive
    gid = "isea-grid"

    grid_html = f"""
<div id="{gid}" class="isea-grid" style="
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
">
  <div id="{gid}-a">{card("Bubble pack", f"Año: {Y} · tamaño=MW · color={color_by}").data}</div>
  <div id="{gid}-b">{card("Paralelas por país", "Arrastra ejes para reordenar · click/brush para filtrar").data}</div>
  <div id="{gid}-c">{card("Mapa mundial % renovable", "Desliza año · click para ver serie temporal").data}</div>
  <div id="{gid}-d">{card("Scatter Solar vs Wind", "Tamaño=Total · Leyenda por tecnología dominante").data}</div>
</div>
"""
    display(HTML(grid_html))

    # IDs de slots
    A = f"{gid}-a"
    B = f"{gid}-b"
    C = f"{gid}-c"
    D = f"{gid}-d"

    # --- 1) BUBBLE (top-left)
    BubblePack(df, year=Y, color_by=color_by, value_mode="total",
               width=int(width*0.49), height=int(height*0.48),
               min_label_r=16, mount_id=f"{A}--slot")

    # --- 2) PARALLEL (top-right)
    ParallelEnergy(df, year=Y, width=int(width*0.49), height=int(height*0.48),
                   mount_id=f"{B}--slot")

    # --- 3) MAP + LINE (bottom-left)
    WorldRenewable(df, year_cols=pack["year_cols"], start_year=Y,
                   width=int(width*0.49), height=int(height*0.48),
                   mount_id=f"{C}--slot")

    # --- 4) SCATTER (bottom-right)
    from pandas import to_numeric
    piv = pack["piv"].copy()
    piv["Total"] = piv[["Solar","Wind","Hydro","Bio","Fossil"]].sum(axis=1, numeric_only=True)
    ScatterBrush(piv, x="Solar", y="Wind", color="DominantTech", size="Total", label="Country",
                 zero_filter=True, width=int(width*0.49), height=int(height*0.48),
                 mount_id=f"{D}--slot")

    # Enlazado básico por ISO3 (si tus gráficos emiten 'select-country')
    display(Javascript(r"""
    (function(){
      // pinta un ping visual cuando llega un select-country (debug-friendly)
      if(!window.__isea_linked_dbg__){
        window.__isea_linked_dbg__ = true;
        IseaBus && IseaBus.on('select-country', (e)=>{
          console.debug('[IseaBus] select-country', e.detail);
        });
      }
    })();
    """))
