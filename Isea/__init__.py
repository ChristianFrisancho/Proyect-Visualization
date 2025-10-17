# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget
from .graphs import ScatterBrush, RadarChart, Sunburst, StreamGraph

__all__ = ["IseaWidget", "ScatterBrush", "RadarChart", "Sunburst", "StreamGraph", "__version__"]
