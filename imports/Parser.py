from GameState import GameState
from imports.Tile import Tile, ME, OPP


class Parser:
    @staticmethod
    def parseMap() -> GameState:
        width, height = [int(i) for i in input().split()]
        return GameState(width, height, [])

    @staticmethod
    def parseMatterInventory(gameState: GameState) -> None:
        gameState.myMats, gameState.oppMats = [int(i) for i in input().split()]

    @staticmethod
    def parseTurnInput(gameState: GameState) -> None:
        for y in range(gameState.mapHeight):
            gameState.tiles.append([])  # set up row

            for x in range(gameState.mapWidth):
                # owner: 1 = me, 0 = foe, -1 = neutral
                # recycler, can_build, can_spawn, in_range_of_recycler: 1 = True, 0 = False
                scrap_amount, owner, units, recycler, \
                can_build, can_spawn, in_range_of_recycler = [int(k) for k in input().split()]
                tile = Tile(x, y, scrap_amount, owner, units, recycler == 1,
                            can_build == 1, can_spawn == 1, in_range_of_recycler == 1)

                gameState.tiles[y].append(tile)

                if tile.owner == ME:
                    gameState.myTiles.append(tile)
                    if tile.units > 0:
                        gameState.myUnits.append(tile)
                    elif tile.recycler:
                        gameState.myRecyclers.append(tile)
                elif tile.owner == OPP:
                    gameState.oppoTiles.append(tile)
                    if tile.units > 0:
                        gameState.oppoUnits.append(tile)
                    elif tile.recycler:
                        gameState.oppoRecyclers.append(tile)
                else:
                    if tile.scrapAmount == 0:
                        gameState.grassTiles.append(tile)
                    else:
                        gameState.neutralTiles.append(tile)


