# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget

from .parallel import ParallelEnergy
from .radial_stacked_bar import RadialStackedBar

from .graphs import (
    ScatterBrushOld,      # scatter con tooltip/leyenda (versión antigua)
    BeeSwarmCapacity,
    BubblePack,
)

from .world_renewable import WorldRenewable
from .scatter import ScatterBrush
from .energy_quad import EnergyQuad

# NUEVO: dashboard de energía
from .energy_dashboard import EnergyDashboardWidget, show_energy_dashboard

from .layouts import LinkedEnergyDashboard
from .widgets import ensure_bus, card

__all__ = [
    "__version__",
    "IseaWidget",
    "RadialStackedBar",
    "ScatterBrush",
    "BeeSwarmCapacity",
    "ParallelEnergy",
    "WorldRenewable",
    "BubblePack",
    "LinkedEnergyDashboard",
    "EnergyQuad",
    # Nuevos
    "EnergyDashboardWidget",
    "show_energy_dashboard",
    "ensure_bus",
    "card",
]
