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
    botsOnRecyclerTile: List[Tile]

    def isLocked(self, gameState: GameState) -> bool:
        # todo: if adjacent tile is grass or recycler, it's in a lockdown
        #     e.g seed=-8074968484840114000 by turn 8 it's locked
        for row in gameState.tiles:
            tile = row[self.lockdownCol]
            if not (tile.isGrass() or tile.recycler):
                return False
        return True




