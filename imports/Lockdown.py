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
from imports.ScoredTile import ScoredTile
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

        # todo: moved this to end so we wouldn't exhaust mats before reclaimin (seed=-8687848559375048000)
        self.useRemainingMatsToEmpowerInvade()
        LOG.debug(f"{self.lockdownState.matsRemaining} mats remaining after empower")

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

            tileInFrontOfCurLockdownTile = self.getTileInFront(curLockdownTile)
            if curLockdownTile.canSpawn and \
                    tileInFrontOfCurLockdownTile.hasEnemyUnits() and \
                    self.isLockdownTileBreachable(curLockdownTile):
                # todo: if tile is surrounded by blocked tiles, don't spawn
                #  seed=1475951007224868600
                #  (14,4) and (15,9) don't need protection
                self.spawnToProtectLockdownTile(curLockdownTile, tileInFrontOfCurLockdownTile)
            elif self.lockdownState.botOptions and self.shouldCaptureLockdownTile(curLockdownTile):
                # todo: it's easy to forget to decrement the botOptions. move this into a method so it's easier to maintain state
                closestBot = Lockdown.findClosestTile(self.lockdownState.botOptions, curLockdownTile)
                LOG.debug(f"Moving {closestBot} to capture lockdown tile {curLockdownTile}")
                self.actionManager.enqueueMove(1, closestBot, curLockdownTile)
                if closestBot.units == 1:
                    self.lockdownState.botOptions.remove(closestBot)
                else:
                    closestBot.units -= 1

    def isLockdownTileBreachable(self, tile: Tile) -> bool:
        coordinatesToTry = [
            {
                'x': tile.x,
                'y': tile.y - 1  # above
            },
            {
                'x': tile.x,
                'y': tile.y + 1  # below
            },
            {
                'x': tile.x - 1 if self.gameState.startedOnLeftSide else tile.x + 1,  # behind
                'y': tile.y
            }
        ]

        for targetCoordinates in coordinatesToTry:
            if self.gameState.mapHeight > targetCoordinates['y'] >= 0 and 0 <= targetCoordinates['x'] < self.gameState.mapWidth:
                targetTile = self.gameState.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if not targetTile.isGrass() and not targetTile.recycler:
                    return True

        return False

    def spawnToProtectLockdownTile(self, lockdownTile: Tile, tileInFrontOfLockdownTile: Tile):
        desiredTotalUnits = tileInFrontOfLockdownTile.units
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

    def shouldCaptureLockdownTile(self, lockdownTile: Tile) -> bool:
        return lockdownTile not in self.lockdownState.bestRecyclerTiles and \
               not lockdownTile.owner == ME and \
               not lockdownTile.isBlocked() and \
               self.isLockdownTileBreachable(lockdownTile)

    def invade(self) -> None:
        LOG.debug("== Starting Invade Steps")
        botsThatCanInvade = self.getBotsThatCanInvade()
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

        self.huntEnemyBots(botsThatCanInvade, enemyBotOptions)
        # todo: capture nearest tile enemy OR neutral tile
        #  seed=7769579162094411000
        self.captureEnemyTiles(botsThatCanInvade)

    def getBotsThatCanInvade(self):
        return [myBot for myBot in self.lockdownState.botOptions if myBot.x == self.lockdownState.lockdownCol or Lockdown.isPassedColumn(self.gameState.startedOnLeftSide, self.lockdownState.lockdownCol, myBot.x)]

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
        LOG.debug("== Starting empower")
        numSpawns = Lockdown.getNumberOfSpawnActionsAvailable(self.lockdownState.matsRemaining,
                                                              self.lockdownState.numRecyclersLeftToBuild)

        LOG.debug(f"can build/spawn {numSpawns} in enemy territory")

        buildLocationOptions = self.getEmpowerBuildOptions() if numSpawns else []
        scoredSpawnLocationOptions = self.getEmpowerSpawnOptions() if numSpawns else []
        LOG.debug(f"{len(buildLocationOptions)} build options in enemy territory")
        LOG.debug(f"{len(scoredSpawnLocationOptions)} scored spawn options in enemy territory")

        if numSpawns and scoredSpawnLocationOptions:
            LOG.debug(f"spawn scores {scoredSpawnLocationOptions}")
            topScoredSpawn = max(scoredSpawnLocationOptions, key=lambda opt: opt.score)
            allTopScoredSpawns = [s for s in scoredSpawnLocationOptions if s.score == topScoredSpawn.score]
            LOG.debug(f"top spawn scores {allTopScoredSpawns}")
            spawnChoice = self.getFrontmostTiles([top.tile for top in allTopScoredSpawns])[0]

            # first build recyclers
            if buildLocationOptions:
                recyclerChoice = self.findClosestTile(buildLocationOptions, spawnChoice)
                if recyclerChoice != spawnChoice:
                    LOG.debug(f"building recycler in enemy territory at {recyclerChoice}")
                    self.actionManager.enqueueBuild(recyclerChoice)
                    self.lockdownState.matsRemaining -= MATS_COST_TO_BUILD
                    numSpawns -= 1

            # second spawn bots
            if numSpawns:
                spawnAmount = max(int(numSpawns/2), 1)
                LOG.debug(f"spawning {spawnAmount} in enemy territory at {spawnChoice}")
                self.actionManager.enqueueSpawn(spawnAmount, spawnChoice)
                self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount

    def getEmpowerBuildOptions(self) -> List[Tile]:
        buildLocationOptions = []
        for tile in self.gameState.myTiles:
            minCol = self.lockdownState.lockdownCol + 1 if self.gameState.startedOnLeftSide else self.lockdownState.lockdownCol - 1
            if Lockdown.isPassedColumn(self.gameState.startedOnLeftSide, minCol, tile.x) and tile.canBuild and not self.isSurroundedByGrass(tile):
                buildLocationOptions.append(tile)
        return buildLocationOptions

    def getEmpowerSpawnOptions(self) -> List[ScoredTile]:
        spawnLocationOptions = []
        for tile in self.gameState.myTiles:
            if Lockdown.isPassedColumn(self.gameState.startedOnLeftSide, self.lockdownState.lockdownCol, tile.x) and not self.isSurroundedByGrass(tile):
                if tile.inRangeOfRecycler:
                    if tile.scrapAmount > 1:
                        spawnLocationOptions.append(self.scoreSpawnTile(tile))
                else:
                    spawnLocationOptions.append(self.scoreSpawnTile(tile))
        return spawnLocationOptions

    def scoreSpawnTile(self, tile: Tile) -> ScoredTile:
        score = 0
        tileInFront = self.getTileInFront(tile)
        if tileInFront and tileInFront.isBlocked():
            score -= 2
        tileInFrontTopCorner = self.getTileInFrontTopCorner(tile)
        if not tileInFrontTopCorner:
            score -= 1
        if tileInFrontTopCorner and tileInFrontTopCorner.isBlocked():
            score -= 2
        tileInFrontBottomCorner = self.getTileInFrontBottomCorner(tile)
        if not tileInFrontBottomCorner:
            score -= 1
        if tileInFrontBottomCorner and tileInFrontBottomCorner.isBlocked():
            score -= 2

        tileAbove = self.getTileAbove(tile)
        if tileAbove:
            if tileAbove.isBlocked():
                score -= 1
            elif tileAbove.hasEnemyUnits():
                score -= 0.5
        else:
            score -= 1

        tileBelow = self.getTileBelow(tile)
        if tileBelow:
            if tileBelow.isBlocked():
                score -= 1
            elif tileBelow.hasEnemyUnits():
                score -= 0.5
        else:
            score -= 1

        return ScoredTile(tile, score)

    def getFrontmostTiles(self, tileOptions: List[Tile]) -> List[Tile]:
        # check highest x (startedOnLeft) or lowest x (!startedOnLeft)
        cols = [tile.x for tile in tileOptions]
        if self.gameState.startedOnLeftSide:
            frontmostCol = max(cols)
        else:
            frontmostCol = min(cols)

        return [tile for tile in tileOptions if tile.x == frontmostCol]


    @staticmethod
    def isPassedColumn(startedOnLeftSide: bool, fromCol: int, colToCheck: int):
        if startedOnLeftSide:
            return colToCheck > fromCol
        else:
            return colToCheck < fromCol

    def huntEnemyBots(self, botsThatCanInvade: List[Tile], enemyBotOptions: List[Tile]):
        if not enemyBotOptions:
            return

        if botsThatCanInvade and enemyBotOptions:
            # todo: verif there aren't other loops that might be borked cause we're mutating the iterable as we loop
            botsThatCanInvadeOriginalSet = copy(botsThatCanInvade)
            maxDistanceInOrderToHunt = 3
            for myBot in botsThatCanInvadeOriginalSet:
                closestEnemy, distance = self.findClosestTileInFrontAndDistance(enemyBotOptions, myBot)
                if closestEnemy is None or distance > maxDistanceInOrderToHunt:
                    continue
                # LOG.debug(f"myBot={myBot}'s closestEnemy={closestEnemy}")
                # LOG.debug(f"enemyBot={closestEnemy}'s allyBot={Lockdown.findClosestTile(botsThatCanInvadeOriginalSet, closestEnemy)}")
                if Lockdown.findClosestTile(botsThatCanInvadeOriginalSet, closestEnemy) == myBot:
                    maxSpawns = Lockdown.getNumberOfSpawnActionsAvailable(
                        self.lockdownState.matsRemaining,
                        self.lockdownState.numRecyclersLeftToBuild
                    )
                    LOG.debug(f"using={myBot} to hunt enemy={closestEnemy} that is {distance} away")
                    self.actionManager.enqueueMove(myBot.units, myBot, closestEnemy)
                    self.lockdownState.botOptions.remove(myBot)
                    botsThatCanInvade.remove(myBot)
                    if maxSpawns and closestEnemy.units >= myBot.units and myBot not in self.lockdownState.bestRecyclerTiles:
                        minRequiredToSurvive = max(closestEnemy.units - myBot.units + 1, 1)
                        spawnAmount = min(minRequiredToSurvive, maxSpawns)
                        # todo: don't spawn on tiles that are about to be scraped
                        LOG.debug(f"spawning={spawnAmount} to hunt enemy={closestEnemy}")
                        self.actionManager.enqueueSpawn(spawnAmount, myBot)
                        self.lockdownState.matsRemaining -= MATS_COST_TO_SPAWN * spawnAmount

    def captureEnemyTiles(self, botsThatCanInvade: List[Tile]):
        enemyEmptyTileOptions = [tile for tile in copy(self.gameState.oppoTiles) if tile.units == 0 and not tile.recycler]
        for myBot in botsThatCanInvade:
            for botUnit in range(myBot.units):
                if not enemyEmptyTileOptions:
                    break
                closestEmptyEnemyTile, distance = self.findClosestTileInFrontAndDistance(enemyEmptyTileOptions, myBot)
                if not closestEmptyEnemyTile:
                    # closestEmptyEnemyTile = Lockdown.findClosestTile(enemyEmptyTileOptions, myBot)
                    continue
                # if not closestEmptyEnemyTile:
                #     continue
                LOG.debug(f"using={myBot} to capture tile={closestEmptyEnemyTile} that is {distance} away")
                self.actionManager.enqueueMove(1, myBot, closestEmptyEnemyTile)
                enemyEmptyTileOptions.remove(closestEmptyEnemyTile)
    #
    # def moveForward(self, botsThatCanInvade: List[Tile]):
    #     for myBot in botsThatCanInvade:
    #         LOG.debug(f"moving {myBot} forward")
    #         self.actionManager.enqueueMove(myBot.units, myBot, self.getEdgeTile(myBot))

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
            if myBot.x != self.lockdownState.lockdownCol and not Lockdown.isPassedColumn(self.gameState.startedOnLeftSide, self.lockdownState.lockdownCol, myBot.x):
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

    def getTileInFront(self, tile: Tile) -> Optional[Tile]:
        if tile.x + 1 >= self.gameState.mapWidth or tile.x - 1 < 0:
            return None

        if self.gameState.startedOnLeftSide:
            return self.gameState.tiles[tile.y][tile.x + 1]
        else:
            return self.gameState.tiles[tile.y][tile.x - 1]

    def getTileInFrontTopCorner(self, tile: Tile) -> Optional[Tile]:
        if tile.x + 1 >= self.gameState.mapWidth or tile.x - 1 < 0:
            return None
        if tile.y - 1 < 0:
            return None

        if self.gameState.startedOnLeftSide:
            return self.gameState.tiles[tile.y - 1][tile.x + 1]
        else:
            return self.gameState.tiles[tile.y - 1][tile.x - 1]

    def getTileInFrontBottomCorner(self, tile: Tile) -> Optional[Tile]:
        if tile.x + 1 >= self.gameState.mapWidth or tile.x - 1 < 0:
            return None
        if tile.y + 1 >= self.gameState.mapHeight:
            return None

        if self.gameState.startedOnLeftSide:
            return self.gameState.tiles[tile.y + 1][tile.x + 1]
        else:
            return self.gameState.tiles[tile.y + 1][tile.x - 1]

    def getTileAbove(self, tile: Tile) -> Optional[Tile]:
        if tile.y - 1 >= 0:
            return self.gameState.tiles[tile.y - 1][tile.x]

    def getTileBelow(self, tile: Tile) -> Optional[Tile]:
        if tile.y + 1 < self.gameState.mapHeight:
            return self.gameState.tiles[tile.y + 1][tile.x]

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
            if self.gameState.mapHeight > targetCoordinates['y'] >= 0 and 0 <= targetCoordinates['x'] < self.gameState.mapWidth:
                targetTile = self.gameState.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if targetTile.owner == ME:
                    return True

        return False

    '''
    Simple single-tile island check
    '''
    def isSurroundedByGrass(self, tile: Tile) -> bool:
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
            if self.gameState.mapHeight > targetCoordinates['y'] >= 0 and 0 <= targetCoordinates['x'] < self.gameState.mapWidth:
                targetTile = self.gameState.tiles[targetCoordinates['y']][targetCoordinates['x']]
                if not targetTile.isGrass():
                    return False

        return True

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