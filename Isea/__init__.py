# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget
from .graphs import (
    ScatterBrush,      # scatter con tooltip/leyenda
    BeeSwarmCapacity,
    ParallelEnergy,
    RadialStackedBar,
    WorldRenewable,
    BubblePack 
)
from .layouts import LinkedEnergyDashboard



__all__ = [
    "__version__",
    "ScatterBrush",
    "BeeSwarmCapacity",
    "ParallelEnergy",
    "RadialStackedBar",
    "WorldRenewable",
    "BubblePack"
]
__all__ += ["LinkedEnergyDashboard"]