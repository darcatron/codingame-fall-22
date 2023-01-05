from dataclasses import dataclass
from typing import List, Set

from imports.Tile import Tile


@dataclass
class LockdownState:
    lockdownCol: int
    bestRecyclerTiles: List[Tile]
    numRecyclersLeftToBuild: int
    matsRemaining: int
    botOptions: List[Tile]
    islandTiles: List[Tile]
    recyclerPlacements: Set[Tile]
