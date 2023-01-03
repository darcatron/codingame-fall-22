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

from Economy import MATS_COST_TO_BUILD, MATS_COST_TO_SPAWN, MATS_INCOME_PER_TURN

class Lockdown:
    def __init__(self, gameState: GameState):
        lockdownColumn = Lockdown.getLockdownColumn(gameState)
        bestRecyclerTiles = Lockdown.getTilesForRecyclersToBlockColumn(gameState.tiles, gameState.myRecyclers, lockdownColumn)
        self.actionManager = ActionManager()
        self.lockdownState = LockdownState(lockdownColumn, bestRecyclerTiles, len(bestRecyclerTiles), gameState.myMats, copy(gameState.myUnits))
        self.gameState = gameState

    def takeActions(self):
        LOG.debug(f"{self.lockdownState.matsRemaining} mats remaining at start")
        self.tryToPlaceRecyclers()
        LOG.debug(f"{self.lockdownState.matsRemaining} mats remaining after placing recyclers")
        self.buildDefensiveBotWall()
        LOG.debug(f"{self.lockdownState.matsRemaining} mats remaining after wall")
        self.invade()
        LOG.debug(f"{self.lockdownState.matsRemaining} mats remaining after invade")
        self.moveBotsOnRecyclerTile()

        # After recyclers are built - reclaim enemy land on my side of the map
        if self.lockdownState.isLocked(self.gameState) or self.hasSpareReclaimBot():
            self.reclaimMySideOfMap()

        self.actionManager.doActions()

    def tryToPlaceRecyclers(self):
        # First step, go build recyclers to block them out on part of the map
        LOG.debug("== Best recycler tiles: " + str(self.lockdownState.bestRecyclerTiles))
        for buildLocation in self.lockdownState.bestRecyclerTiles:
            if buildLocation.canBuild and self.lockdownState.matsRemaining >= MATS_COST_TO_BUILD:
                self.actionManager.enqueueBuild(buildLocation)
                self.lockdownState.numRecyclersLeftToBuild -= 1
                self.lockdownState.matsRemaining -= MATS_COST_TO_BUILD
            if not self.lockdownState.botOptions:  # we're screwed
                break
            closestBot = Lockdown.findClosestTile(self.lockdownState.botOptions, buildLocation)
            if closestBot is not None:
                if closestBot.isSameLocation(buildLocation):
                    LOG.debug(f"must move {closestBot} away from desired recycler location")
                    continue
                elif buildLocation.owner is not ME:  # we hit this if we don't have enough to build a recycler on an owned tile
                    # We need to go convert the tile to be owned by us before we can build on it, go move there
                    # todo this can sometimes cause us to move onto a different recycler build target location
                    #  that is already owned by us, which can lead to an infinite loop of us getting on and then off that build location
                    # instead, we should make sure we go around
                    LOG.debug(f"moving {closestBot} to {buildLocation} to capture desired recycler location")
                    self.actionManager.enqueueMove(1, closestBot, buildLocation)

                    if closestBot.units == 1:
                        self.lockdownState.botOptions.remove(closestBot)
                    else:
                        closestBot.units -= 1

    def buildDefensiveBotWall(self) -> None:
        LOG.debug("== Starting Defensive Bot Wall Steps")
        for row in self.gameState.tiles:
            curLockdownTile = row[self.lockdownState.lockdownCol]
            if curLockdownTile.inRangeOfRecycler and curLockdownTile.scrapAmount == 1:
                # don't wanna build on tiles that are about to be grass
                continue
            tileInFrontOfCurLockdownTile = self.gameState.tiles[curLockdownTile.y][curLockdownTile.x + 1 if self.gameState.startedOnLeftSide else curLockdownTile.x - 1]
            if curLockdownTile.canSpawn and tileInFrontOfCurLockdownTile.owner == OPP and tileInFrontOfCurLockdownTile.units > 0:
                self.spawnToProtectLockdownTile(curLockdownTile, tileInFrontOfCurLockdownTile)
            elif self.lockdownState.botOptions and Lockdown.shouldCaptureLockdownTile(curLockdownTile):
                # todo: it's easy to forget to decrement the botOptions. move this into a method so it's easier to maintain state
                closestBot = Lockdown.findClosestTile(self.lockdownState.botOptions, curLockdownTile)
                LOG.debug(f"Moving {closestBot} to capture lockdown tile {curLockdownTile}")
                self.actionManager.enqueueMove(1, closestBot, curLockdownTile)
                if closestBot.units == 1:
                    self.lockdownState.botOptions.remove(closestBot)
                else:
                    closestBot.units -= 1

    def spawnToProtectLockdownTile(self, lockdownTile: Tile, tileInFrontOfLockdownTile: Tile):
        desiredTotalUnits = tileInFrontOfLockdownTile.units + 1
        unitsOnOurTile = 0
        curLockdownTileBotOption = None
        if lockdownTile in self.lockdownState.botOptions:
            # we can only use these units if they aren't already being assigned to another task like building recyclers
            curLockdownTileBotOption = self.findClosestTile(self.lockdownState.botOptions, lockdownTile)
            unitsOnOurTile = curLockdownTileBotOption.units
        additionalRequiredUnits = max(desiredTotalUnits - unitsOnOurTile, 0)
        LOG.debug(f"need {additionalRequiredUnits} to hold against {tileInFrontOfLockdownTile}")
        if additionalRequiredUnits == 0:
            # make sure the units defending aren't used elsewhere
            if curLockdownTileBotOption:
                if curLockdownTileBotOption.units == desiredTotalUnits:
                    self.lockdownState.botOptions.remove(lockdownTile)
                else:
                    curLockdownTileBotOption.units -= tileInFrontOfLockdownTile.units
            return

        maxSpawnActions = Lockdown.getNumberOfSpawnActionsAvailable(
            self.lockdownState.matsRemaining,
            self.lockdownState.numRecyclersLeftToBuild
        )
        spawnAmount = min(additionalRequiredUnits, maxSpawnActions)
        LOG.debug(f"spawning {spawnAmount} to hold lockdown tile {lockdownTile}")
        self.actionManager.enqueueSpawn(spawnAmount, lockdownTile)
        # todo: it's easy to forget to decrement mats. move this into a method so it's easier to maintain state
        self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount
        if lockdownTile in self.lockdownState.botOptions:
            # these bots need to stay put and can't be used for other actions
            self.lockdownState.botOptions.remove(lockdownTile)

    @staticmethod
    def shouldCaptureLockdownTile(lockdownTile: Tile) -> bool:
        return not lockdownTile.owner == ME and not lockdownTile.recycler and not lockdownTile.isGrass()

    def invade(self) -> None:
        LOG.debug("== Starting Invade Steps")
        botsThatCanInvade = [myBot for myBot in self.lockdownState.botOptions if myBot.x == self.lockdownState.lockdownCol or
                             Lockdown.isPassedLockdownColumn(self.gameState.startedOnLeftSide, self.lockdownState.lockdownCol,
                                                             myBot.x)]
        LOG.debug(f"{len(botsThatCanInvade)} bot options left with to invade")
        LOG.debug(f"{self.lockdownState.matsRemaining} mats left with to invade")
        enemyBotOptions = copy(self.gameState.oppoUnits) # todo: move this into huntEnemyBotsNew, it's the only method that uses it

        self.spawnBotsToInvadeIfNecessary(botsThatCanInvade)

        for myBot in botsThatCanInvade:
            edgeTile = self.getEdgeTile(myBot)
            if myBot.x == self.lockdownState.lockdownCol:
                if myBot.scrapAmount == 1:
                    LOG.debug(f"Moving bot={myBot} to avoid getting wrecked by recycler")
                    self.actionManager.enqueueMove(myBot.units, myBot, edgeTile)
                    botsThatCanInvade.remove(myBot)

        self.huntEnemyBotsNew(botsThatCanInvade, enemyBotOptions)
        self.useRemainingMatsToEmpowerInvade()

    def spawnBotsToInvadeIfNecessary(self, botsThatCanInvade: List[Tile]) -> None:
        if self.lockdownState.isLocked(self.gameState) and not botsThatCanInvade:
            LOG.debug("Locked but no invading bots.")
            numSpawns = Lockdown.getNumberOfSpawnActionsAvailable(self.lockdownState.matsRemaining,
                                                                  self.lockdownState.numRecyclersLeftToBuild)
            counter = 0
            enemyEmptyTileOptions = [tile for tile in copy(self.gameState.oppoTiles) if
                                     tile.units == 0 and not tile.recycler]
            for _ in range(min(numSpawns, len(enemyEmptyTileOptions))):
                myTileClosestToEnemyTile = Lockdown.findClosestTile(self.gameState.myTiles, enemyEmptyTileOptions[counter])
                LOG.debug(f"no invading bots. spawning 1 at={myTileClosestToEnemyTile}")
                self.actionManager.enqueueSpawn(1, myTileClosestToEnemyTile)
                self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN

    def useRemainingMatsToEmpowerInvade(self):
        numSpawns = Lockdown.getNumberOfSpawnActionsAvailable(self.lockdownState.matsRemaining,
                                                              self.lockdownState.numRecyclersLeftToBuild)
        LOG.debug(f"can build/spawn {numSpawns} in enemy territory")
        if numSpawns:
            buildLocationOptions = []
            for tile in self.gameState.myTiles:
                if Lockdown.isPassedLockdownColumn(self.gameState.startedOnLeftSide, self.lockdownState.lockdownCol, tile.x) and \
                        tile.canBuild and \
                        not tile.inRangeOfRecycler:
                    buildLocationOptions.append(tile)
            LOG.debug(f"{len(buildLocationOptions)} build options in enemy territory")
            myBotsAdvantageBuffer = 1.10  # have 10% more bots than oppo
            if buildLocationOptions and len(self.gameState.myUnits) < len(self.gameState.oppoUnits) * myBotsAdvantageBuffer:
                buildChoice = random.choice(buildLocationOptions)
                LOG.debug(f"randomly spawning in enemy territory at {buildChoice}")
                self.actionManager.enqueueSpawn(1, buildChoice)
                self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN
                buildLocationOptions.remove(buildChoice)

            # TODO - build recyclers strategically

    @staticmethod
    def isPassedLockdownColumn(startedOnLeftSide: bool, lockdownCol: int, colNum: int):
        if startedOnLeftSide:
            return colNum > lockdownCol
        else:
            return colNum < lockdownCol

    def huntEnemyBots(self, botsThatCanInvade: List[Tile], enemyBotOptions: List[Tile]):
        if not enemyBotOptions:
            return

        if botsThatCanInvade and enemyBotOptions:
            for myBot in botsThatCanInvade:
                # todo: this doesn't account for closestEnemy == None
                closestEnemy, distance = Lockdown.findClosestTileAndDistance(enemyBotOptions, myBot)
                if Lockdown.findClosestTile(botsThatCanInvade, closestEnemy) == myBot:
                    maxDistanceInOrderToSpawn = 3
                    maxSpawns = Lockdown.getNumberOfSpawnActionsAvailable(
                        self.lockdownState.matsRemaining,
                        self.lockdownState.numRecyclersLeftToBuild
                    )
                    LOG.debug(f"using={myBot} to hunt enemy={closestEnemy} that is {distance} away")
                    self.actionManager.enqueueMove(myBot.units, myBot, closestEnemy)
                    botsThatCanInvade.remove(myBot)
                    if distance < maxDistanceInOrderToSpawn and maxSpawns and closestEnemy.units >= myBot.units:
                        minRequiredToSurvive = max(closestEnemy.units - myBot.units + 1, 1)
                        spawnAmount = min(minRequiredToSurvive, maxSpawns)
                        LOG.debug(f"spawning={spawnAmount} to hunt enemy={closestEnemy}")
                        self.actionManager.enqueueSpawn(spawnAmount, myBot)
                        self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount

        for unusedBot in botsThatCanInvade:
            self.captureEnemyTiles(unusedBot)

    def huntEnemyBotsNew(self, botsThatCanInvade: List[Tile], enemyBotOptions: List[Tile]):
        if not enemyBotOptions:
            return

        if botsThatCanInvade and enemyBotOptions:
            LOG.debug(f"botsThatCanInvade={botsThatCanInvade}")
            # todo: verif there aren't other loops that might be borked cause we're mutating the iterable as we loop
            for myBot in copy(botsThatCanInvade):
                LOG.debug(f"{myBot}")
                closestEnemy, distance = self.findClosestTileInFrontAndDistance(enemyBotOptions, myBot)
                if closestEnemy is None:
                    continue
                LOG.debug(f"myBot={myBot}'s closestEnemy={closestEnemy}")
                LOG.debug(f"enemyBot={closestEnemy}'s all={Lockdown.findClosestTile(botsThatCanInvade, closestEnemy)}")
                if Lockdown.findClosestTile(botsThatCanInvade, closestEnemy) == myBot:
                    maxDistanceInOrderToSpawn = 3
                    maxSpawns = Lockdown.getNumberOfSpawnActionsAvailable(
                        self.lockdownState.matsRemaining,
                        self.lockdownState.numRecyclersLeftToBuild
                    )
                    LOG.debug(f"using={myBot} to hunt enemy={closestEnemy} that is {distance} away")
                    self.actionManager.enqueueMove(myBot.units, myBot, closestEnemy)
                    botsThatCanInvade.remove(myBot)
                    if distance < maxDistanceInOrderToSpawn and maxSpawns and closestEnemy.units >= myBot.units:
                        minRequiredToSurvive = max(closestEnemy.units - myBot.units + 1, 1)
                        spawnAmount = min(minRequiredToSurvive, maxSpawns)
                        LOG.debug(f"spawning={spawnAmount} to hunt enemy={closestEnemy}")
                        self.actionManager.enqueueSpawn(spawnAmount, myBot)
                        self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount
                LOG.debug(f"{botsThatCanInvade}")

        for unusedBot in botsThatCanInvade:
            self.captureEnemyTiles(unusedBot)

    def captureEnemyTiles(self, myBot: Tile):
        enemyEmptyTileOptions = [tile for tile in copy(self.gameState.oppoTiles) if tile.units == 0 and not tile.recycler]
        for botUnit in range(myBot.units):
            if not enemyEmptyTileOptions:
                break
            closestEmptyEnemyTile = Lockdown.findClosestTile(enemyEmptyTileOptions, myBot)
            LOG.debug(f"using={myBot} to capture tile={closestEmptyEnemyTile}")
            self.actionManager.enqueueMove(1, myBot, closestEmptyEnemyTile)
            enemyEmptyTileOptions.remove(closestEmptyEnemyTile)

    def moveBotsOnRecyclerTile(self):
        LOG.debug("== Starting moveBotsOnRecyclerTile")
        for botOption in self.lockdownState.botOptions:
            if botOption in self.lockdownState.bestRecyclerTiles:
                LOG.debug(f"moving bot {botOption} forward away from desired recycler location")
                self.actionManager.enqueueMove(botOption.units, botOption, self.getEdgeTile(botOption))
                if botOption.units == 1:
                    self.lockdownState.botOptions.remove(botOption)
                else:
                    botOption.units -= 1

    def hasSpareReclaimBot(self) -> bool:
        for myBot in self.lockdownState.botOptions:
            if myBot.x != self.lockdownState.lockdownCol and not Lockdown.isPassedLockdownColumn(self.gameState.startedOnLeftSide, self.lockdownState.lockdownCol, myBot.x):
                LOG.debug(f"found spare reclaim bot {myBot}")
                return True

        return False

    # Prioritizes taking enemy tiles back first, then goes for neutral tiles
    def reclaimMySideOfMap(self) -> None:
        # todo: this doesn't handle islands well. if we have two islands with a bot only on one island,
        #  we need to spawn a new bot on the other island.
        LOG.debug("== Starting reclaim")
        isTileOnMySide = lambda tile: tile.x < self.lockdownState.lockdownCol if self.gameState.startedOnLeftSide else tile.x > self.lockdownState.lockdownCol
        enemyTilesOnMySide = list(filter(isTileOnMySide, self.gameState.oppoTiles))
        neutralTilesOnMySide = list(filter(isTileOnMySide, self.gameState.neutralTiles))
        myBots = list(filter(isTileOnMySide, self.gameState.myUnits))

        if not myBots and self.lockdownState.matsRemaining >= MATS_COST_TO_SPAWN:
            # todo (optimization): only need to find a single tile rather than filtering through entire list
            myTilesOnMySide = list(filter(isTileOnMySide, self.gameState.myTiles))
            self.actionManager.enqueueSpawn(1, myTilesOnMySide[0])
            LOG.debug(f"spawning {myTilesOnMySide[0]} to start reclaiming")
            self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN

        if len(enemyTilesOnMySide) > 0:
            tilesToClaim = enemyTilesOnMySide
        elif len(neutralTilesOnMySide) > 0:
            tilesToClaim = neutralTilesOnMySide
        else:
            return

        reachableTiles = list(filter(lambda tile: self.isAdjacentToOwnedTile(tile), tilesToClaim))
        LOG.debug(f"Can't reclaim {str(set(tilesToClaim) - set(reachableTiles))}")
        for myBot in myBots:
            tileToMoveTo = Lockdown.findClosestTile(reachableTiles, myBot)
            if tileToMoveTo is None:
                break
            LOG.debug(f"reclaiming={tileToMoveTo} with bot={myBot}")
            self.actionManager.enqueueMove(myBot.units, myBot, tileToMoveTo)

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
        # Source: https://stackoverflow.com/questions/10818546/finding-index-of-nearest-point-in-numpy-arrays-of-x-and-y-coordinates
        allTiles = np.array([[tile.x, tile.y] for tile in tileOptions])
        tree = spatial.KDTree(allTiles)
        distance, index = tree.query([targetTile.x, targetTile.y])
        return tileOptions[index], distance

    def findClosestTileInFrontAndDistance(self, tileOptions: List[Tile], targetTile: Tile) -> Tuple[Optional[Tile], int]:
        if len(tileOptions) == 0:
            return None, None
        # Source: https://stackoverflow.com/questions/10818546/finding-index-of-nearest-point-in-numpy-arrays-of-x-and-y-coordinates
        # the references in this new list are the same as the old list so updates to
        # objects in the new list apply to the objects the old list
        tilesInFront = list(filter(lambda tile: tile.x > targetTile.x if self.gameState.startedOnLeftSide else tile.x < targetTile.x, tileOptions))
        if not tilesInFront:
            return None, None
        allTiles = np.array([[tile.x, tile.y] for tile in tilesInFront])
        tree = spatial.KDTree(allTiles)
        distance, index = tree.query([targetTile.x, targetTile.y])
        return tilesInFront[index], distance

    @staticmethod
    def getNumberOfSpawnActionsAvailable(matsRemaining: int, numRecyclersToBuild: int) -> int:
        # We'll get another {MATS_INCOME_PER_TURN} mats next turn, so we can afford to be over budget by that much
        matsToSaveForNextTurn = max(numRecyclersToBuild * MATS_COST_TO_BUILD - MATS_INCOME_PER_TURN, 0)
        matsToSpend = max(matsRemaining - matsToSaveForNextTurn, 0)
        return int(matsToSpend / MATS_COST_TO_SPAWN)

    def getEdgeTile(self, bot: Tile):
        # todo: this doesn't account for grass tiles. In games, I've seen targeting grass tiles
        #  cause the bot to stay where it is
        return self.gameState.tiles[bot.y][-1] if self.gameState.startedOnLeftSide else self.gameState.tiles[bot.y][0]

    def isAdjacentToOwnedTile(self, tile: Tile) -> bool:
        coordinatesToTry = [
            {
                'x': tile.x,
                'y': tile.y - 1
            },
            {
                'x': tile.x,
                'y': tile.y + 1
            },
            {
                'x': tile.x - 1,
                'y': tile.y
            },
            {
                'x': tile.x + 1,
                'y': tile.y
            },
        ]

        for targetCoordinates in coordinatesToTry:
            if targetCoordinates['y'] < len(self.gameState.tiles) and targetCoordinates['x'] < len(self.gameState.tiles[targetCoordinates['y']]):
                targetTile = self.gameState.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if targetTile.owner == ME:
                    return True

        return False

    # Get the column we are blocking off with grass
    @staticmethod
    def getLockdownColumn(gameState: GameState) -> int:
        # todo (optimization): this can be calculated once rather than per turn
        if gameState.startedOnLeftSide:
            return int(gameState.mapWidth / 3)
        else:
            # we started on the right side
            return int(gameState.mapWidth / 3) * 2

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