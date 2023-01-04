from dataclasses import dataclass

from imports.Tile import Tile


@dataclass
class ScoredTile:
    tile: Tile
    score: float

