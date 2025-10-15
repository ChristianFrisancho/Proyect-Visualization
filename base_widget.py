from traitlets import Unicode, Dict, List, Int
import anywidget

class IseaWidget(anywidget.AnyWidget):
    """
    Clase base para todos los gráficos Isea.
    - Sincroniza estado: data (lista de dicts), options (dict), width/height, title.
    - El frontend JS debe definir render({model, el}) y escuchar cambios.
    """
    _esm   = Unicode("").tag(sync=True)   
    data   = List([]).tag(sync=True)
    options= Dict({}).tag(sync=True)
    width  = Int(640).tag(sync=True)
    height = Int(360).tag(sync=True)
    title  = Unicode("").tag(sync=True)
