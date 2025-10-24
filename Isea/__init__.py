# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget

# NUEVO widget (anywidget)
from .parallel import ParallelEnergy

from .graphs import (
    ScatterBrushOld,      # scatter con tooltip/leyenda
    BeeSwarmCapacity,
    # ParallelEnergy,     # <- QUITAR/COMENTAR para evitar duplicado
    RadialStackedBar,
    WorldRenewable,
    BubblePack,
)
from .layouts import LinkedEnergyDashboard

# Added by Milan
from .scatter import ScatterBrush

__all__ = [
    "__version__",
    "IseaWidget",
    "ScatterBrush",
    "BeeSwarmCapacity",
    "ParallelEnergy",          # <-- el del widget
    "RadialStackedBar",
    "WorldRenewable",
    "BubblePack",
    "LinkedEnergyDashboard",
]
