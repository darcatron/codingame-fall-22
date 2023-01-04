from dataclasses import dataclass

ME = 1
OPP = 0
NONE = -1

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

    def turnsToGrassThisTurn(self) -> bool:
        return self.inRangeOfRecycler and self.scrapAmount == 1

    # A blocked tile is one that is grass or has a recycler on it or is going to turn to grass this turn
    # A tile with enemy bots is NOT considered to be blocked
    def isBlocked(self) -> bool:
        return self.recycler or self.isGrass() or self.turnsToGrassThisTurn()

    def hasEnemyUnits(self) -> bool:
        return self.owner == OPP and self.units > 0

    def __hash__(self):
        return hash((self.x, self.y, self.scrapAmount, self.owner, self.units, self.recycler, self.canBuild, self.canSpawn, self.inRangeOfRecycler))

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
