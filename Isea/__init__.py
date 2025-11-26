"""
Public entry point for the Isea visualisation package.

This module re-exports the main widget classes so they can be imported
directly from :mod:`Isea`, for example:

    from Isea import ScatterBrush, ParallelEnergy, EnergyQuad

It also exposes the package version string as ``__version__``.
"""
# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget

# NUEVO widget (anywidget)
from .parallel import ParallelEnergy

# Added by Milan
from .scatter import ScatterBrush
from .energy_quad import EnergyQuad


__all__ = [
    "__version__",
    "IseaWidget",
    "RadialStackedBar",      
    "ScatterBrush",
    "BeeSwarmCapacity",
    "ParallelEnergy",          # <-- el del widget
    "RadialStackedBar",
    "WorldRenewable",
    "BubblePack",
    "LinkedEnergyDashboard",
    "WorldRenewable",
    "EnergyQuad",
]
