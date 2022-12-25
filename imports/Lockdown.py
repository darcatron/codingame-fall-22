import os
from typing import List, Optional, Tuple

from LOG import LOG

from copy import copy
from scipy import spatial
import numpy as np
import random

from imports.ActionManager import ActionManager
from imports.GameState import GameState
from imports.LockdownState import LockdownState
from imports.Tile import Tile, ME, OPP
from imports.MoveAction import MoveAction

from Economy import MATS_COST_TO_BUILD, MATS_COST_TO_SPAWN, MATS_INCOME_PER_TURN

class Lockdown:
    @staticmethod
    def takeActions(gameState: GameState):
        lockdownColumn = Lockdown.getLockdownColumn(gameState)
        bestRecyclerTiles = Lockdown.getTilesForRecyclersToBlockColumn(gameState.tiles, gameState.myRecyclers, lockdownColumn)
        actionManager = ActionManager()
        lockdownState = LockdownState(lockdownColumn, bestRecyclerTiles, len(bestRecyclerTiles), gameState.myMats, copy(gameState.myUnits), [])

        # todo: once the code works, in a separate commit move these args into self.args and remove the static methods
        LOG.debug(f"{lockdownState.matsRemaining} mats remaining at start")
        Lockdown.tryToPlaceRecyclers(gameState, lockdownState, actionManager)
        LOG.debug(f"{lockdownState.matsRemaining} mats remaining after placing recyclers")
        Lockdown.buildDefensiveBotWall(gameState, lockdownState, actionManager)
        LOG.debug(f"{lockdownState.matsRemaining} mats remaining after wall")
        Lockdown.invade(gameState, lockdownState, actionManager)
        LOG.debug(f"{lockdownState.matsRemaining} mats remaining after invade")
        Lockdown.moveBotsOnRecyclerTile(gameState, lockdownState, actionManager)

        # After recyclers are built - reclaim enemy land on my side of the map
        if lockdownState.isLocked(gameState) or Lockdown.hasSpareReclaimBot(gameState, lockdownState):
            Lockdown.reclaimMySideOfMap(gameState, lockdownState, actionManager)

        actionManager.doActions()

    @staticmethod
    def tryToPlaceRecyclers(gameState: GameState, lockdownState: LockdownState, actionManager: ActionManager):
        # First step, go build recyclers to block them out on part of the map
        LOG.debug("Best recycler tiles: " + str(lockdownState.bestRecyclerTiles))
        for buildLocation in lockdownState.bestRecyclerTiles:
            if buildLocation.canBuild and lockdownState.matsRemaining >= MATS_COST_TO_BUILD:
                actionManager.enqueueBuild(buildLocation)
                lockdownState.numRecyclersLeftToBuild -= 1
                lockdownState.matsRemaining -= MATS_COST_TO_BUILD
            if not lockdownState.botOptions:  # we're screwed
                break
            closestBot = Lockdown.findClosestTile(lockdownState.botOptions, buildLocation)
            if closestBot is not None:
                movedBot = False
                if closestBot.isSameLocation(buildLocation):
                    # move off target location so we can build on it next turn
                    # todo: instead of moving them forward, track these and continue the loop. if they're still not moved (still in botOptions), we can move them forward.
                    #       if this works, we can clean up the movedBot logic (merge the if with the elif clause)
                    # LOG.debug(f"moving bot={closestBot} away from desired recycler location")
                    # actionManager.enqueueMove(closestBot.units, closestBot, Lockdown.getEdgeTile(gameState, closestBot))
                    # movedBot = True

                    LOG.debug(f"must move {closestBot} away from desired recycler location")
                    lockdownState.botsOnRecyclerTile.append(closestBot)
                elif buildLocation.owner is not ME:  # we hit this if we don't have enough to build a recycler on an owned tile
                    # We need to go convert the tile to be owned by us before we can build on it, go move there
                    # todo this can sometimes cause us to move onto a different recycler build target location that is already owned by us, which can lead to an infinite loop of us getting on and then off that build location
                    # instead, we should make sure we go around
                    LOG.debug(f"moving {closestBot} to {buildLocation} to capture desired recycler location")
                    actionManager.enqueueMove(1, closestBot, buildLocation)
                    movedBot = True

                if movedBot:
                    if closestBot.units == 1:
                        lockdownState.botOptions.remove(closestBot)
                    else:
                        closestBot.units -= 1

    @staticmethod
    def buildDefensiveBotWall(gameState: GameState, lockdownState: LockdownState, actionManager: ActionManager) -> None:
        for row in gameState.tiles:
            curLockdownTile = row[lockdownState.lockdownCol]
            if curLockdownTile in lockdownState.bestRecyclerTiles:
                # we already have other logic moving bots to capture the recycler tiles
                continue
            elif curLockdownTile.canSpawn:
                if curLockdownTile.inRangeOfRecycler and curLockdownTile.scrapAmount == 1:
                    # don't wanna build on tiles that are about to be grassified
                    continue

                tileInFrontOfCurLockdownTile = gameState.tiles[curLockdownTile.y][curLockdownTile.x + 1 if gameState.startedOnLeftSide else curLockdownTile.x - 1]
                if tileInFrontOfCurLockdownTile.owner == OPP and tileInFrontOfCurLockdownTile.units > 0:
                    additionalRequiredUnits = max(tileInFrontOfCurLockdownTile.units - curLockdownTile.units + 1, 0)
                    if additionalRequiredUnits == 0:
                        continue
                    maxSpawnActions = Lockdown.getNumberOfSpawnActionsAvailable(lockdownState.matsRemaining, lockdownState.numRecyclersLeftToBuild)
                    spawnAmount = min(additionalRequiredUnits, maxSpawnActions)
                    LOG.debug(f"Spawning {spawnAmount} to hold lockdown tile {curLockdownTile}")
                    actionManager.enqueueSpawn(spawnAmount, curLockdownTile)
                    # todo: it's easy to forget to decrement mats. move this into a method so it's easier to maintain state
                    lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount
            elif lockdownState.botOptions and Lockdown.shouldCaptureLockdownTile(curLockdownTile):
                # todo: it's easy to forget to decrement the botOptions. move this into a method so it's easier to maintain state
                closestBot = Lockdown.findClosestTile(lockdownState.botOptions, curLockdownTile)
                LOG.debug(f"Moving {closestBot} to capture lockdown tile {curLockdownTile}")
                actionManager.enqueueMove(1, closestBot, curLockdownTile)
                if closestBot.units == 1:
                    lockdownState.botOptions.remove(closestBot)
                else:
                    closestBot.units -= 1

    @staticmethod
    def shouldCaptureLockdownTile(lockdownTile: Tile) -> bool:
        return not lockdownTile.owner == ME and not lockdownTile.recycler and not lockdownTile.isGrass()

    @staticmethod
    def invade(gameState: GameState, lockdownState: LockdownState, actionManager: ActionManager) -> None:
        # todo: break up this method
        botsThatCanInvade = [myBot for myBot in lockdownState.botOptions if myBot.x == lockdownState.lockdownCol or
                             Lockdown.isPassedLockdownColumn(gameState.startedOnLeftSide, lockdownState.lockdownCol,
                                                             myBot.x)]
        LOG.debug(f"{len(botsThatCanInvade)} bot options left with to invade")
        LOG.debug(f"{lockdownState.matsRemaining} mats left with to invade")
        enemyBotOptions = copy(gameState.oppoUnits)
        enemyTileOptions = [tile for tile in copy(gameState.oppoTiles) if tile.units == 0 and not tile.recycler]

        if lockdownState.isLocked(gameState) and not botsThatCanInvade:
            LOG.debug("Locked but no invading bots.")
            numSpawns = Lockdown.getNumberOfSpawnActionsAvailable(lockdownState.matsRemaining,
                                                                  lockdownState.numRecyclersLeftToBuild)
            counter = 0
            for _ in range(min(numSpawns, len(enemyTileOptions))):
                myTileClosestToEnemyTile = Lockdown.findClosestTile(gameState.myTiles, enemyTileOptions[counter])
                LOG.debug(f"no invading bots. spawning 1 at={myTileClosestToEnemyTile}")
                actionManager.enqueueSpawn(1, myTileClosestToEnemyTile)
                lockdownState.matsRemaining -= MATS_COST_TO_SPAWN

        for myBot in botsThatCanInvade:
            edgeTile = Lockdown.getEdgeTile(gameState, myBot)
            if myBot.x == lockdownState.lockdownCol:
                if myBot.scrapAmount == 1:
                    LOG.debug(f"Moving bot={myBot} to avoid getting wrecked by recycler")
                    actionManager.enqueueMove(myBot.units, myBot, edgeTile)
                    botsThatCanInvade.remove(myBot)
                # todo: this can be handled by the remaining invade logic that should take into account the enemy bot position.
                #       there's also a chance this messes up the wall logic which might spawn bots on a tile to protect against an enemy.
                #       If we move our bot forward, the enemy can overtake our wall cause bots dont get eliminated if they're crossing paths,
                #       only if they end up on the same tile.
                # elif myBot.units > 0:
                #     LOG.debug(f"Invading with bot={myBot}")
                #     actionManager.enqueueMove(myBot.units, myBot, edgeTile)
                #     botsThatCanInvade.remove(myBot)

        # todo: start new code
        Lockdown.huntEnemyBotsNew(lockdownState, actionManager, botsThatCanInvade, enemyBotOptions, enemyTileOptions)
        # todo: start new code

        # todo: start old code
        # if botsThatCanInvade and enemyBotOptions:
        #     Lockdown.huntEnemyBots(lockdownState, actionManager, botsThatCanInvade, enemyBotOptions)
        # else:
        #     for myBot2 in botsThatCanInvade:
        #         Lockdown.captureEnemyTiles(actionManager, myBot2, enemyTileOptions)
        # todo: end old code

        Lockdown.useRemainingMatsToEmpowerInvade(gameState, lockdownState, actionManager)

    @staticmethod
    def useRemainingMatsToEmpowerInvade(gameState: GameState, lockdownState: LockdownState, actionManager: ActionManager):
        numSpawns = Lockdown.getNumberOfSpawnActionsAvailable(lockdownState.matsRemaining,
                                                              lockdownState.numRecyclersLeftToBuild)
        LOG.debug(f"can build/spawn {numSpawns} in enemy territory")
        if numSpawns:
            buildLocationOptions = []
            for tile in gameState.myTiles:
                if Lockdown.isPassedLockdownColumn(gameState.startedOnLeftSide, lockdownState.lockdownCol, tile.x) and \
                        tile.canBuild and \
                        not tile.inRangeOfRecycler:
                    buildLocationOptions.append(tile)
            LOG.debug(f"{len(buildLocationOptions)} build options in enemy territory")
            myBotsAdvantageBuffer = 1.10  # have 10% more bots than oppo
            if buildLocationOptions and len(gameState.myUnits) < len(gameState.oppoUnits) * myBotsAdvantageBuffer:
                buildChoice = random.choice(buildLocationOptions)
                LOG.debug(f"randomly spawning in enemy territory at {buildChoice}")
                actionManager.enqueueSpawn(1, buildChoice)
                lockdownState.matsRemaining -= MATS_COST_TO_SPAWN
                buildLocationOptions.remove(buildChoice)

            # TODO - CONTINUE HERE - better recycler play
            # if buildLocationOptions and numSpawns > 1:
            #     # picks further into enemy territory and center-most location
            #     midWayRow = int(gameState.mapHeight / 2)
            #     midWayCol = int(gameState.mapWidth / 2)
            #     furthestOutTile = Lockdown.findClosestTile(buildLocationOptions, Lockdown.getEdgeTile(gameState,
            #                                                                                           gameState.tiles[
            #                                                                                               midWayRow][
            #                                                                                               midWayCol]))
            #     LOG.debug(f"building recycler in enemy territory at {furthestOutTile}")
            #     actionManager.enqueueBuild(furthestOutTile)
            #     lockdownState.matsRemaining -= MATS_COST_TO_BUILD
            #     buildLocationOptions.remove(furthestOutTile)

    @staticmethod
    def isPassedLockdownColumn(startedOnLeftSide: bool, lockdownCol: int, colNum: int):
        if startedOnLeftSide:
            return colNum > lockdownCol
        else:
            return colNum < lockdownCol

    @staticmethod
    def huntEnemyBots(lockdownState: LockdownState, actionManager: ActionManager, botsThatCanInvade: List[Tile], enemyBotOptions: List[Tile]):
        for enemyBot in enemyBotOptions:
            myClosestBot, distance = Lockdown.findClosestTileAndDistance(botsThatCanInvade, enemyBot)
            if myClosestBot is None:
                break
            maxDistanceInOrderToSpawn = 3
            maxSpawns = Lockdown.getNumberOfSpawnActionsAvailable(
                lockdownState.matsRemaining,
                lockdownState.numRecyclersLeftToBuild
            )
            LOG.debug(f"using={myClosestBot} to hunt enemy={enemyBot} that is {distance} away")
            actionManager.enqueueMove(myClosestBot.units, myClosestBot, enemyBot)
            botsThatCanInvade.remove(myClosestBot)
            if distance < maxDistanceInOrderToSpawn and maxSpawns and enemyBot.units >= myClosestBot.units:
                minRequiredToSurvive = max(enemyBot.units - myClosestBot.units + 1, 1)
                spawnAmount = min(minRequiredToSurvive, maxSpawns)
                LOG.debug(f"spawning={spawnAmount} to hunt enemy={enemyBot}")
                actionManager.enqueueSpawn(spawnAmount, myClosestBot)
                lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount

    @staticmethod
    def huntEnemyBotsNew(lockdownState: LockdownState, actionManager: ActionManager, botsThatCanInvade: List[Tile], enemyBotOptions: List[Tile], enemyTileOptions: List[Tile]):
        # todo: CONTINUE HERE - only the best matched bots move. the remaining bots aren't doing anything.
        # todo: part 2 - once better distance matching is in place, prevent bots from hunting backwards (on same col or forwards)

        if not enemyBotOptions:
            return

        # bestMatches = {}
        if botsThatCanInvade and enemyBotOptions:
            for myBot in botsThatCanInvade:
                closestEnemy, distance = Lockdown.findClosestTileAndDistance(enemyBotOptions, myBot)
                if Lockdown.findClosestTile(botsThatCanInvade, closestEnemy) == myBot:
                    maxDistanceInOrderToSpawn = 3
                    maxSpawns = Lockdown.getNumberOfSpawnActionsAvailable(
                        lockdownState.matsRemaining,
                        lockdownState.numRecyclersLeftToBuild
                    )
                    LOG.debug(f"using={myBot} to hunt enemy={closestEnemy} that is {distance} away")
                    actionManager.enqueueMove(myBot.units, myBot, closestEnemy)
                    botsThatCanInvade.remove(myBot)
                    if distance < maxDistanceInOrderToSpawn and maxSpawns and closestEnemy.units >= myBot.units:
                        minRequiredToSurvive = max(closestEnemy.units - myBot.units + 1, 1)
                        spawnAmount = min(minRequiredToSurvive, maxSpawns)
                        LOG.debug(f"spawning={spawnAmount} to hunt enemy={closestEnemy}")
                        actionManager.enqueueSpawn(spawnAmount, myBot)
                        lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount
        #     enemyCoordinate = (closestEnemy.x, closestEnemy.y)
        #     if enemyCoordinate in bestMatches:
        #         _, _, existingDistance = bestMatches[enemyCoordinate]
        #         if existingDistance > distance:
        #             bestMatches[enemyCoordinate] = (myBot, closestEnemy, distance)
        #     else:
        #         bestMatches[enemyCoordinate] = (myBot, closestEnemy, distance)
        #
        # for myClosestBot, enemyBot, distance in bestMatches.values():
        #     maxDistanceInOrderToSpawn = 3
        #     maxSpawns = Lockdown.getNumberOfSpawnActionsAvailable(
        #         lockdownState.matsRemaining,
        #         lockdownState.numRecyclersLeftToBuild
        #     )
        #     LOG.debug(f"using={myClosestBot} to hunt enemy={enemyBot} that is {distance} away")
        #     actionManager.enqueueMove(myClosestBot.units, myClosestBot, enemyBot)
        #     botsThatCanInvade.remove(myClosestBot)
        #     if distance < maxDistanceInOrderToSpawn and maxSpawns and enemyBot.units >= myClosestBot.units:
        #         minRequiredToSurvive = max(enemyBot.units - myClosestBot.units + 1, 1)
        #         spawnAmount = min(minRequiredToSurvive, maxSpawns)
        #         LOG.debug(f"spawning={spawnAmount} to hunt enemy={enemyBot}")
        #         actionManager.enqueueSpawn(spawnAmount, myClosestBot)
        #         lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount

        for unusedBot in botsThatCanInvade:
            Lockdown.captureEnemyTiles(actionManager, unusedBot, enemyTileOptions)

    @staticmethod
    def captureEnemyTiles(actionManager: ActionManager, myBot: Tile, enemyTileOptions: List[Tile]):
        for botUnit in range(myBot.units):
            if not enemyTileOptions:
                break
            closestEmptyEnemyTile = Lockdown.findClosestTile(enemyTileOptions, myBot)
            LOG.debug(f"using={myBot} to capture tile={closestEmptyEnemyTile}")
            actionManager.enqueueMove(1, myBot, closestEmptyEnemyTile)
            enemyTileOptions.remove(closestEmptyEnemyTile)

    @staticmethod
    def moveBotsOnRecyclerTile(gameState: GameState, lockdownState: LockdownState, actionManager: ActionManager):
        for bot in lockdownState.botsOnRecyclerTile:
            if bot in lockdownState.botOptions:
                LOG.debug(f"moving bot {bot} forward away from desired recycler location")
                actionManager.enqueueMove(bot.units, bot, Lockdown.getEdgeTile(gameState, bot))
                if bot.units == 1:
                    lockdownState.botOptions.remove(bot)
                else:
                    bot.units -= 1

    @staticmethod
    def hasSpareReclaimBot(gameState: GameState, lockdownState: LockdownState) -> bool:
        for myBot in lockdownState.botOptions:
            if myBot.x != lockdownState.lockdownCol and not Lockdown.isPassedLockdownColumn(gameState.startedOnLeftSide, lockdownState.lockdownCol, myBot.x):
                LOG.debug(f"Found spare reclaim bot {myBot}")
                return True

        return False

    # Prioritizes taking enemy tiles back first, then goes for neutral tiles
    @staticmethod
    def reclaimMySideOfMap(gameState: GameState, lockdownState: LockdownState, actionManager: ActionManager) -> List[MoveAction]:
        # todo: this doesn't handle islands well. if we have two islands with a bot only on one island,
        #  we need to spawn a new bot on the other island.
        LOG.debug("Reclaiming.")
        isTileOnMySide = lambda tile: tile.x < lockdownState.lockdownCol if gameState.startedOnLeftSide else tile.x > lockdownState.lockdownCol
        enemyTilesOnMySide = list(filter(isTileOnMySide, gameState.oppoTiles))
        neutralTilesOnMySide = list(filter(isTileOnMySide, gameState.neutralTiles))
        myBots = list(filter(isTileOnMySide, gameState.myUnits))

        if not myBots:
            # todo (optimization): only need to find a single tile rather than filtering through entire list
            myTilesOnMySide = list(filter(isTileOnMySide, gameState.myTiles))
            actionManager.enqueueSpawn(1, myTilesOnMySide[0])
            LOG.debug(f"spawning {myTilesOnMySide[0]} to start reclaiming")
            lockdownState.matsRemaining -= MATS_COST_TO_SPAWN

        moveActions = []
        if len(enemyTilesOnMySide) > 0:
            tilesToClaim = enemyTilesOnMySide
        elif len(neutralTilesOnMySide) > 0:
            tilesToClaim = neutralTilesOnMySide
        else:
            return []

        reachableTiles = list(filter(lambda tile: Lockdown.isAdjacentToOwnedTile(gameState, tile), tilesToClaim))
        LOG.debug(f"Can't reclaim {str(set(tilesToClaim) - set(reachableTiles))}")
        # for each bot go to closest enemy tile
        for myBot in myBots:
            tileToMoveTo = Lockdown.findClosestTile(reachableTiles, myBot)
            if tileToMoveTo is None:
                break
            LOG.debug(f"reclaiming={tileToMoveTo} with bot={myBot}")
            moveActions.append(MoveAction(myBot.units, myBot, tileToMoveTo))

        for moveAction in moveActions:
            actionManager.enqueueMoveAction(moveAction)

    @staticmethod
    def findClosestTile(tileOptions: List[Tile], targetTile: Tile) -> Optional[Tile]:
        return Lockdown.findClosestTileAndDistance(tileOptions, targetTile)[0]

    # todo this doesn't take into account grass tiles, recyclers, or enemy bots getting in the way
    #  I've noticed this will cause us to get in an infinite loop of moving directionally away from the targetTile since that's the shortest path (grass blocks us from going by the way the crow flies)
    #  Then we spawn where that bot used to be since it's the closest bot, then we'll repeat with the spawned bot next turn, etc.
    @staticmethod
    def findClosestTileAndDistance(tileOptions: List[Tile], targetTile: Tile) -> Tuple[Optional[Tile], int]:
        if len(tileOptions) == 0:
            return None, None
        # todo: had to remove the short-ciruit since the distance calc can't be simplified
        # if len(tileOptions) == 1:
        #     return tileOptions[0], None
        # Source: https://stackoverflow.com/questions/10818546/finding-index-of-nearest-point-in-numpy-arrays-of-x-and-y-coordinates
        allTiles = np.array([[tile.x, tile.y] for tile in tileOptions])
        tree = spatial.KDTree(allTiles)
        distance, index = tree.query([targetTile.x, targetTile.y])
        return tileOptions[index], distance

    @staticmethod
    def getNumberOfSpawnActionsAvailable(matsRemaining: int, numRecyclersToBuild: int) -> int:
        # We'll get another {MATS_INCOME_PER_TURN} mats next turn, so we can afford to be over budget by that much
        matsToSaveForNextTurn = max(numRecyclersToBuild * MATS_COST_TO_BUILD - MATS_INCOME_PER_TURN, 0)
        matsToSpend = max(matsRemaining - matsToSaveForNextTurn, 0)
        return int(matsToSpend / MATS_COST_TO_SPAWN)

    @staticmethod
    def getEdgeTile(gameState: GameState, bot: Tile):
        # todo: this doesn't account for grass tiles. In games, I've seen targeting grass tiles
        #  cause the bot to stay where it is
        return gameState.tiles[bot.y][-1] if gameState.startedOnLeftSide else gameState.tiles[bot.y][0]

    @staticmethod
    def isAdjacentToOwnedTile(gameState: GameState, tile: Tile) -> bool:
        coordinatesToTry = [
            {
                'x': tile.x,
                'y': tile.y - 1
            },
            {
                'x': tile.x,
                'y': tile.y + 1
            },
            # {
            #     'x': tile.x - 1,
            #     'y': tile.y - 1
            # },
            {
                'x': tile.x - 1,
                'y': tile.y
            },
            # {
            #     'x': tile.x - 1,
            #     'y': tile.y + 1
            # },
            # {
            #     'x': tile.x + 1,
            #     'y': tile.y - 1
            # },
            {
                'x': tile.x + 1,
                'y': tile.y
            },
            # {
            #     'x': tile.x + 1,
            #     'y': tile.y + 1
            # },
        ]

        for targetCoordinates in coordinatesToTry:
            if targetCoordinates['y'] < len(gameState.tiles) and targetCoordinates['x'] < len(gameState.tiles[targetCoordinates['y']]):
                targetTile = gameState.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if targetTile.owner == ME:
                    return True

        return False

    # Get the column we are blocking off with grass
    @staticmethod
    def getLockdownColumn(gameState: GameState) -> int:
        # todo (optimization): this can be calculated once rather than per turn
        if gameState.startedOnLeftSide:
            # return int(gameState.mapWidth / 2) - 1
            return int(gameState.mapWidth / 3)
            # return int((gameState.mapWidth / 2)) if gameState.mapWidth % 2 == 0 else int(
            #     (gameState.mapWidth / 2)) + 1
        else:
            # we started on the right side
            # return int((gameState.mapWidth / 2)) - 1 if gameState.mapWidth % 2 == 0 else int(
            #     (gameState.mapWidth / 2))
            return int(gameState.mapWidth / 3) * 2
            # return int(gameState.mapWidth / 2) + 1

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