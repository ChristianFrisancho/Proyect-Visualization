# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget
from .graphs import ScatterBrush  # aquí importamos lo que SÍ existe

__all__ = ["IseaWidget", "ScatterBrush", "__version__"]
