from dataclasses import dataclass
from typing import List

from imports.GameState import GameState
from imports.Tile import Tile


@dataclass
class LockdownState:
    lockdownCol: int
    bestRecyclerTiles: List[Tile]
    numRecyclersLeftToBuild: int
    matsRemaining: int
    botOptions: List[Tile]
