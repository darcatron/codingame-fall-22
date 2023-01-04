from typing import List

from imports.Tile import Tile
from LOG import LOG


class IslandFinder:
    def __init__(self, tiles: List[List[Tile]]):
        self.tiles = tiles
        self.maxRows = len(tiles)
        self.maxCols = len(tiles[0])
        LOG.debug(f"IslandFinder - maxCols={self.maxCols} maxRows={self.maxRows}")

    def findIslands(self):
        tilesRemainingToCheck = set([tile for row in self.tiles for tile in row if not tile.isBlocked()])
        allIslands: List[List[Tile]] = []

        while len(tilesRemainingToCheck) > 0:
            startingTile = tilesRemainingToCheck.pop()
            curIsland = []
            toVisit = [startingTile]
            while len(toVisit) > 0:
                sourceTile = toVisit.pop()
                curIsland.append(sourceTile)
                adjacentTiles = self.getAdjacentTiles(sourceTile)
                for adjacentTile in adjacentTiles:
                    if adjacentTile in tilesRemainingToCheck:
                        toVisit.append(adjacentTile)
                        tilesRemainingToCheck.remove(adjacentTile)

            allIslands.append(curIsland)

        return allIslands


    # Find all tiles adjacent to the source tile, but does not include the source tile itself in the return value
    # Excludes blocked tiles by default, but can use the {includeBlockedTiles} flag to include them
    def getAdjacentTiles(self, sourceTile: Tile, includeBlockedTiles: bool = False) -> List[Tile]:
        adjacentTiles = []
        coordinatesToTry = [
            {
                'x': sourceTile.x,
                'y': sourceTile.y - 1
            },
            {
                'x': sourceTile.x,
                'y': sourceTile.y + 1
            },
            {
                'x': sourceTile.x - 1,
                'y': sourceTile.y
            },
            {
                'x': sourceTile.x + 1,
                'y': sourceTile.y
            },
        ]

        for targetCoordinates in coordinatesToTry:
            if self.maxRows > targetCoordinates['y'] >= 0 and 0 <= targetCoordinates['x'] < self.maxCols:
                targetTile = self.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if includeBlockedTiles:
                    adjacentTiles.append(targetTile)
                elif not targetTile.isBlocked():
                    adjacentTiles.append(targetTile)
        return adjacentTiles
