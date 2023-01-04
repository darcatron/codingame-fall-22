from typing import List
from imports.Tile import Tile

# Traverses tiles based on the same rules as bot movement (can only move to adjacent tiles, cannot move onto a grass tile
# or a tile with a recycler on it)
#
# Does NOT take into account enemy bots getting in the way
class TileTraverser:

    def __init__(self, tiles: List[List[Tile]]):
        self.tiles = tiles

    # Gets all tiles that could be reached within {range} amount of movement of the sourceTile, excluding the source tile
    def getTilesInMovementRangeOfTile(self, sourceTile: Tile, range: int) -> List[Tile]:
        # DFS to find all tiles within range
        tilesInRange = set()
        tilePaths = [[sourceTile]]
        while len(tilePaths) > 0:
            currentTilePath = tilePaths.pop()
            adjacentUnblockedTiles = self.getAdjacentTiles(currentTilePath[-1])
            for tile in adjacentUnblockedTiles:
                if tile not in tilesInRange and tile != sourceTile:
                    tilesInRange.add(tile)
                    if len(currentTilePath) <= range: # allow range + 1 since the path includes the source tile
                        newTilePath = [*currentTilePath, tile]
                        tilePaths.append(newTilePath)

        return list(tilesInRange)



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
            if targetCoordinates['y'] < len(self.tiles) and targetCoordinates['x'] < len(self.tiles[targetCoordinates['y']]):
                targetTile = self.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if includeBlockedTiles:
                    adjacentTiles.append(targetTile)
                elif not targetTile.isBlocked():
                    adjacentTiles.append(targetTile)

        return adjacentTiles
