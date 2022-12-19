from dataclasses import dataclass, field

from typing import List

from imports.Tile import Tile


@dataclass
class GameState:
    mapWidth: int
    mapHeight: int

    tiles: List[List[Tile]]
    myMats: int = None
    oppoMats: int = None
    myUnits: List[Tile] = field(default_factory=list)
    oppoUnits: List[Tile] = field(default_factory=list)
    myRecyclers: List[Tile] = field(default_factory=list)
    oppoRecyclers: List[Tile] = field(default_factory=list)
    oppoTiles: List[Tile] = field(default_factory=list)
    myTiles: List[Tile] = field(default_factory=list)
    neutralTiles: List[Tile] = field(default_factory=list)
    grassTiles: List[Tile] = field(default_factory=list)

    def resetForTurn(self):
        self.tiles = []
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
