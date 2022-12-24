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

    def isLocked(self, gameState: GameState) -> bool:
        for row in gameState.tiles:
            tile = row[self.lockdownCol]
            if not (tile.isGrass() or tile.recycler):
                return False
        return True




