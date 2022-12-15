from dataclasses import dataclass, field

from imports.Tile import Tile


@dataclass
class GameState:
    mapWidth: int
    mapHeight: int
    tiles: list[list[Tile]]

    myMats: int = None
    oppoMats: int = None
    myUnits: list[Tile] = field(default_factory=list)
    oppoUnits: list[Tile] = field(default_factory=list)
    myRecyclers: list[Tile] = field(default_factory=list)
    oppoRecyclers: list[Tile] = field(default_factory=list)
    oppoTiles: list[Tile] = field(default_factory=list)
    myTiles: list[Tile] = field(default_factory=list)
    neutralTiles: list[Tile] = field(default_factory=list)
    grassTiles: list[Tile] = field(default_factory=list)

    def resetForTurn(self):
        self.myMats = -1
        self.oppoMats = -1
        self.myUnits = []
        self.oppoUnits = []
        self.myRecyclers = []
        self.oppoRecyclers = []
        self.oppoTiles = []
        self.myTiles = []
        self.neutralTiles = []
        self.grassTiles = []
