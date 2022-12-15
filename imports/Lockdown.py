import sys

from imports.ActionManager import ActionManager
from imports.GameState import GameState
from imports.Tile import Tile


class Lockdown:
    @staticmethod
    def takeActions(gameState: GameState):
        bestRecyclerTiles = Lockdown.getBestRecyclerTiles(gameState)
        print('(DEBUG) best recycler locations: ' + str(bestRecyclerTiles), file=sys.stderr, flush=True)
        actionManager = ActionManager()
        unitIndex = 0
        for location in bestRecyclerTiles:
            actionManager.enqueueMove(gameState.myUnits[unitIndex].units, gameState.myUnits[unitIndex], location)
            unitIndex += 1
        actionManager.debugActions()
        actionManager.doActions()


    @staticmethod
    def getBestRecyclerTiles(gameState: GameState) -> [Tile]:
        invadeColumn = int((gameState.mapWidth / 2) + 1)
        buildableSteps = [1, 4, 7, 10]
        curStep = 0
        targetTiles = []
        for row in range(gameState.mapHeight + 1):
            if curStep in buildableSteps:
                if row > gameState.mapHeight:
                    # can't build off the map, build before
                    targetTiles.append(gameState.tiles[row - 1][invadeColumn])
                elif gameState.tiles[row][invadeColumn].isGrass() and row - 1 >= 0:
                    # can't build on grass, build before
                    targetTiles.append(gameState.tiles[row - 1][invadeColumn])
                else:
                    # regular tile
                    targetTiles.append(gameState.tiles[row][invadeColumn])

            if row >= gameState.mapHeight:
                break

            if gameState.tiles[row][invadeColumn].isGrass():
                # grass resets optimal recycler placement calculation
                curStep = 0
                continue

            curStep += 1

        return targetTiles
