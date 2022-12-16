from dataclasses import dataclass

@dataclass
class Tile:
    x: int
    y: int
    scrapAmount: int
    owner: int
    units: int
    recycler: bool
    canBuild: bool
    canSpawn: bool
    inRangeOfRecycler: bool

    def isGrass(self) -> bool:
        return self.scrapAmount == 0

    def isSameLocation(self, other: 'Tile') -> bool:
        return self.x == other.x and self.y == other.y
