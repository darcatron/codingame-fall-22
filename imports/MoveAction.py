from dataclasses import dataclass

from imports.Tile import Tile

@dataclass
class MoveAction:
    numUnits: int
    fromTile: Tile
    toTile: Tile

    def getActionString(self) -> str:
        return f"MOVE {self.numUnits} {self.fromTile.x} {self.fromTile.y} {self.toTile.x} {self.toTile.y}"
