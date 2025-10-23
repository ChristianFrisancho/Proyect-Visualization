# Isea/__init__.py
from ._version import __version__
from .base_widget import IseaWidget
from .graphs import (
    ScatterBrushOld,      # scatter con tooltip/leyenda
    BeeSwarmCapacity,
    ParallelEnergy,
    RadialStackedBar,
    WorldRenewable,
    BubblePack 
)
from .layouts import LinkedEnergyDashboard

#Added by Milan
from .scatter import ScatterBrush            # new class




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