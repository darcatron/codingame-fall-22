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
    def takeActions(gameState: GameState, startedOnLeftSide: bool):
        bestRecyclerTiles = Lockdown.getBestRecyclerTiles(gameState, startedOnLeftSide)
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
                if numSpawns > 0:
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
            if targetCoordinates['y'] < len(gameState.tiles) and targetCoordinates['x'] < len(gameState.tiles[targetCoordinates['y']]):
                targetTile = gameState.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if not targetTile.isGrass():
                    return targetTile

        return None

    @staticmethod
    def getBestRecyclerTiles(gameState: GameState, startedOnLeftSide: bool) -> [Tile]:
        # todo (optimization): this can be calculated once rather than per turn
        if startedOnLeftSide:
            invadeColumn = int((gameState.mapWidth / 2)) if gameState.mapWidth % 2 == 0 else int((gameState.mapWidth / 2)) + 1
        else:
            # we started on the right side
            invadeColumn = int((gameState.mapWidth / 2)) - 1 if gameState.mapWidth % 2 == 0 else int((gameState.mapWidth / 2))

        return Lockdown.getTilesForRecyclersToBlockColumn(gameState.tiles, gameState.myRecyclers, invadeColumn)

    @staticmethod
    def getTilesForRecyclersToBlockColumn(allTiles: List[List[Tile]], ourExistingRecyclersAtTurnStart: List[Tile], column: int) -> List[Tile]:
        # Find the fewest number of recyclers needed to turn the entire column into grass
        # Remember that a recycler is destroyed when it exhausts the scrap pile of the tile it is on
        # So, we will generally prefer building the recyclers on the tiles that have more scrap than the adjacent tiles above and below it

        mapHeight = len(allTiles)
        if mapHeight == 0:
            return []

        # https://stackoverflow.com/questions/903853/how-do-you-extract-a-column-from-a-multi-dimensional-array
        allTilesArr = np.array(allTiles)
        tilesInColumn = allTilesArr[:, column].tolist()
        nonGrassTilesInColumn = list(filter(lambda tile: not tile.isGrass(), tilesInColumn))

        # DFS to find the combo of recyclers that has full coverage with minimal recyclers, using this stack to keep track of recycler combinations to try
        recyclerTilesSoFarStack: List[List[Tile]] = [[]]
        bestRecyclerComboFound = None

        while len(recyclerTilesSoFarStack) > 0:
            recyclerTilesSoFar = recyclerTilesSoFarStack.pop()
            # These are the tiles that we do not need to worry about blocking (turning to grass), since the recyclers we have so far should take care of them
            grassifiedTiles = Lockdown.getTilesThatRecyclersWillGrassify(nonGrassTilesInColumn, [*ourExistingRecyclersAtTurnStart, *recyclerTilesSoFar])
            # That makes these the ones we do need to block, by turning into grass
            tilesToGrassify = list(set(nonGrassTilesInColumn).difference(set(grassifiedTiles)))
            if len(tilesToGrassify) == 0:
                # No tiles left to block! We've found a possible recycler combo for the lockdown strat. Let's see if it's the best we've found so far
                if bestRecyclerComboFound is None or len(bestRecyclerComboFound) > len(recyclerTilesSoFar):
                    bestRecyclerComboFound = recyclerTilesSoFar
            else:
                # There are more tiles to block, let's iterate from the lowest row number to highest row number to try differnet recycler placements.
                # We know they work on adjacent tiles, so we definitely need a recycler on or adjacent to the lowest row number that doesn't correspond to a grass tile
                firstTileToGrassify = min(tilesToGrassify, key=lambda tile: tile.y)
                recyclerTilesSoFarStack.append([*recyclerTilesSoFar, firstTileToGrassify])
                secondTileArr = list(filter(lambda tile: tile.y == firstTileToGrassify.y + 1, tilesToGrassify))
                if len(secondTileArr) > 0:
                    recyclerTilesSoFarStack.append([*recyclerTilesSoFar, secondTileArr[0]])

        return [] if bestRecyclerComboFound is None else bestRecyclerComboFound

    @staticmethod
    def getTilesThatRecyclersWillGrassify(tilesToCheck: List[Tile], recyclerTiles: List[Tile]) -> List[Tile]:
        return list(filter(lambda tile: any((recyclerTile.isAdjacent(tile) or recyclerTile.isSameLocation(tile)) and recyclerTile.scrapAmount >= tile.scrapAmount for recyclerTile in recyclerTiles), tilesToCheck))