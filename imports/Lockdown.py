import random
from LOG import LOG

from copy import copy
from scipy import spatial
import numpy as np

from imports.ActionManager import ActionManager
from imports.GameState import GameState
from imports.Tile import Tile


class Lockdown:
    @staticmethod
    def takeActions(gameState: GameState):
        bestRecyclerTiles = Lockdown.getBestRecyclerTiles(gameState)
        actionManager = ActionManager()
        botOptions = copy(gameState.myUnits)

        for location in bestRecyclerTiles:
            if location.canBuild:
                actionManager.enqueueBuild(location)
            if not botOptions:  # we're screwed
                break
            closestBot = Lockdown.findClosestBot(botOptions, location)
            botOptions.remove(closestBot)
            if closestBot.isSameLocation(location):
                # move off target location so we can build on it next turn
                # todo (optimization): this move can be smarter
                remainingOptions = [t for t in bestRecyclerTiles if t != location]
                actionManager.enqueueMove(closestBot.units, closestBot, random.choice(remainingOptions))
            else:
                actionManager.enqueueMove(closestBot.units, closestBot, location)
        actionManager.debugActions()
        actionManager.doActions()

    @staticmethod
    def findClosestBot(bots: list[Tile], targetTile: Tile) -> Tile:
        if len(bots) == 1:
            return bots[0]
        # Source: https://stackoverflow.com/questions/10818546/finding-index-of-nearest-point-in-numpy-arrays-of-x-and-y-coordinates
        allBots = np.array([[bot.x, bot.y] for bot in bots])
        tree = spatial.KDTree(allBots)
        distance, index = tree.query([targetTile.x, targetTile.y])
        return bots[index]

    @staticmethod
    def getBestRecyclerTiles(gameState: GameState) -> [Tile]:
        # todo (optimization): this can be calculated once rather than per turn
        invadeColumn = int((gameState.mapWidth / 2) + 1)
        buildableSteps = [1, 4, 7, 10]
        curStep = 0
        targetTiles = []
        for row in range(gameState.mapHeight + 1):
            LOG.debug(f'checking row={row} step={curStep}', 'best recycler locations')
            if curStep in buildableSteps:
                if row >= gameState.mapHeight:
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
