from typing import List, Optional

from LOG import LOG

from copy import copy
from scipy import spatial
import numpy as np

from imports.ActionManager import ActionManager
from imports.GameState import GameState
from imports.Tile import Tile

from Economy import MATS_COST_TO_BUILD, MATS_COST_TO_SPAWN, MATS_INCOME_PER_TURN


class Lockdown:
    @staticmethod
    def takeActions(gameState: GameState):
        bestRecyclerTiles = Lockdown.getBestRecyclerTiles(gameState)
        actionManager = ActionManager()
        botOptions = copy(gameState.myUnits)
        matsRemaining = gameState.myMats  # todo track remaining funds in a common class for all actions, maybe the action manager?
        numRecyclersLeftToBuild = len(bestRecyclerTiles)
        botsForSpawning = []

        LOG.debug(f"Best recycler tiles: {bestRecyclerTiles}")
        for location in bestRecyclerTiles:
            if location.canBuild and matsRemaining >= MATS_COST_TO_BUILD:
                actionManager.enqueueBuild(location)
                numRecyclersLeftToBuild -= 1
                matsRemaining -= MATS_COST_TO_BUILD
            if not botOptions:  # we're screwed
                break
            closestBot = Lockdown.findClosestBot(botOptions, location)
            botOptions.remove(closestBot)
            if closestBot.isSameLocation(location):
                # move off target location so we can build on it next turn
                # todo (optimization): this move can be smarter
                destinationTile = Lockdown.getAdjacentTileToMoveTo(gameState, location)
                if destinationTile:
                    actionManager.enqueueMove(closestBot.units, closestBot, destinationTile)
            else:
                botsForSpawning.append(closestBot)
                actionManager.enqueueMove(closestBot.units, closestBot, location) # todo going directly to the tile like this sometimes doesn't work, and the auto-move just makes the bots go back and forth between the same two tiles

        for myUnit in botsForSpawning:
            if myUnit.canSpawn:
                numSpawns = Lockdown.getNumberOfSpawnActionsAvailable(matsRemaining, numRecyclersLeftToBuild)
                actionManager.enqueueSpawn(numSpawns, myUnit)
                matsRemaining -= MATS_COST_TO_SPAWN * numSpawns

        actionManager.debugActions()
        actionManager.doActions()

    @staticmethod
    def findClosestBot(bots: List[Tile], targetTile: Tile) -> Tile:
        if len(bots) == 1:
            return bots[0]
        # Source: https://stackoverflow.com/questions/10818546/finding-index-of-nearest-point-in-numpy-arrays-of-x-and-y-coordinates
        allBots = np.array([[bot.x, bot.y] for bot in bots])
        tree = spatial.KDTree(allBots)
        distance, index = tree.query([targetTile.x, targetTile.y])
        return bots[index]

    @staticmethod
    def getNumberOfSpawnActionsAvailable(matsRemaining: int, numRecyclersToBuild: int) -> int:
        # We'll get another {MATS_INCOME_PER_TURN} mats next turn, so we can afford to be over budget by that much
        matsToSaveForNextTurn = numRecyclersToBuild * MATS_COST_TO_BUILD - MATS_INCOME_PER_TURN
        matsToSpend = max(matsRemaining - matsToSaveForNextTurn, 0)
        return int(matsToSpend / MATS_COST_TO_SPAWN)

    @staticmethod
    def getAdjacentTileToMoveTo(gameState: GameState, fromTile: Tile) -> Optional[Tile]:
        coordinatesToTry = [
            {
                'x': fromTile.x,
                'y': fromTile.y - 1
            },
            {
                'x': fromTile.x,
                'y': fromTile.y + 1
            },
            {
                'x': fromTile.x - 1,
                'y': fromTile.y - 1
            },
            {
                'x': fromTile.x - 1,
                'y': fromTile.y
            },
            {
                'x': fromTile.x - 1,
                'y': fromTile.y + 1
            },
            {
                'x': fromTile.x + 1,
                'y': fromTile.y - 1
            },
            {
                'x': fromTile.x + 1,
                'y': fromTile.y
            },
            {
                'x': fromTile.x + 1,
                'y': fromTile.y + 1
            },
        ]

        for targetCoordinates in coordinatesToTry:
            if targetCoordinates['x'] < len(gameState.tiles) and targetCoordinates['y'] < len(gameState.tiles[targetCoordinates['x']]):
                targetTile = gameState.tiles[targetCoordinates['x']][targetCoordinates['y']]
                if not targetTile.isGrass():
                    return targetTile

        return None

    @staticmethod
    def getBestRecyclerTiles(gameState: GameState) -> [Tile]:
        myUnitX = gameState.myUnits[0].x if len(gameState.myUnits) > 0 else 0
        oppoUnitX = gameState.oppoUnits[0].x if len(gameState.oppoUnits) > 0 else 0

        # todo (optimization): this can be calculated once rather than per turn
        invadeColumn = int((gameState.mapWidth / 2) + 1)
        if myUnitX > oppoUnitX:
            # we start on the right side
            invadeColumn = int((gameState.mapWidth / 2) - 1)
        buildableSteps = [1, 4, 7, 10]  # todo we need more advanced calculations to determine this. If the tile with the recycler on it has less scrap than either the tile above or below it, it will turn to grass and get disassembled before turning those tiles to grass
        curStep = 0
        targetTiles = []
        for row in range(gameState.mapHeight + 1):
            # LOG.debug(f'checking row={row} step={curStep}', 'best recycler locations')
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
