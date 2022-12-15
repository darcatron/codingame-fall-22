import sys
import random

from imports.ActionManager import ActionManager
from imports.GameState import GameState
from imports.Tile import Tile


class Lockdown:
    @staticmethod
    def takeActions(gameState: GameState):
        bestRecyclerTiles = Lockdown.getBestRecyclerTiles(gameState)
        print('(DEBUG) best recycler locations: ' + str(bestRecyclerTiles), file=sys.stderr, flush=True)
        actionManager = ActionManager()
        for index, location in enumerate(bestRecyclerTiles):
            if location.canBuild:
                print('(DEBUG) about to build at ' + str(location), file=sys.stderr, flush=True)
                actionManager.enqueueBuild(location)
            # todo: using 'index' here should be safe to start since we have at least 4 bots.
            #  They could get got tho. Then we'll get an out-of-bounds exception
            myBotTile = gameState.myUnits[index]
            if myBotTile.x == location.x and myBotTile.y == location.y:
                remainingOptions = [t for t in bestRecyclerTiles if t != location]
                actionManager.enqueueMove(myBotTile.units, myBotTile, random.choice(remainingOptions))
            else:
                actionManager.enqueueMove(myBotTile.units, myBotTile, location)
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
