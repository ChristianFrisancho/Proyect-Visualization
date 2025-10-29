# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget

# NUEVO widget (anywidget)
from .parallel import ParallelEnergy
from .radial_stacked_bar import RadialStackedBar

from .graphs import (
    ScatterBrushOld,      # scatter con tooltip/leyenda
    BeeSwarmCapacity,
    # ParallelEnergy,     # <- QUITAR/COMENTAR para evitar duplicado
    #RadialStackedBar,
    #WorldRenewable,
    BubblePack,
)
from .layouts import LinkedEnergyDashboard

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

# Added by Alex
from .world_renewable import WorldRenewable