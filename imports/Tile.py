from dataclasses import dataclass

# todo: x and y is confusing, would be better to call them row and column
@dataclass
class Tile:
    x: int  # a.k.a. column
    y: int  # a.k.a. row
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

    def isAdjacent(self, other: 'Tile') -> bool:
        return abs(self.x - other.x) + abs(self.y - other.y) == 1

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Tile):
            return self.x == other.x and self.y == other.y and self.scrapAmount == other.scrapAmount and self.owner == other.owner and self.units == other.units and self.recycler == other.recycler and self.canBuild == other.canBuild and self.canSpawn == other.canSpawn and self.inRangeOfRecycler == other.inRangeOfRecycler
        return NotImplemented

    def __hash__(self):
        return hash((self.x, self.y, self.scrapAmount, self.owner, self.units, self.recycler, self.canBuild, self.canSpawn, self.inRangeOfRecycler))