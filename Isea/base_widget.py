from traitlets import Unicode, Dict, List, Int
import anywidget

class IseaWidget(anywidget.AnyWidget):
    """
    Lightweight base class for custom Isea widgets.

    It defines a standard set of traitlets that are kept in sync between
    Python and the JavaScript frontend:

    - `data`: list of records (dicts) that the visualization will render.
    - `options`: configuration dictionary with visual and interaction settings.
    - `width` / `height`: pixel dimensions of the drawing area.
    - `title`: optional title for the chart.
    - `_esm`: string containing the JavaScript module source for the widget.

    To build a custom widget, subclass `IseaWidget`, set `self._esm` to the
    contents of a JS module that exports a `render({ model, el })` function,
    and populate `self.data` and `self.options` in `__init__`.

    The widgets shipped in this repository currently subclass
    `anywidget.AnyWidget` directly, but `IseaWidget` is provided as a
    reusable convenience base for future Isea components.
    """
    _esm   = Unicode("").tag(sync=True)   
    data   = List([]).tag(sync=True)
    options= Dict({}).tag(sync=True)
    width  = Int(640).tag(sync=True)
    height = Int(360).tag(sync=True)
    title  = Unicode("").tag(sync=True)
