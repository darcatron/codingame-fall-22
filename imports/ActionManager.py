import os
import random

from imports.LOG import LOG
from imports.Tile import Tile


class ActionManager:
    def __init__(self):
        self.actions = []
        self.insults = [
            "come at me",
            "who's your daddy",
            "cash me outside",
            "2 + 2 don't know what it is!",
            "yawn",
            "dis some disrespect",
            "you're fuming!",
            "ez tutorial",
            "gg",
            "thank you, next"
        ]

    def enqueueMove(self, numUnits: int, fromTile: Tile, toTile: Tile) -> None:
        self.actions.append(f"MOVE {numUnits} {fromTile.x} {fromTile.y} {toTile.x} {toTile.y}")

    def enqueueSpawn(self, amount, tile: Tile) -> None:
        self.actions.append('SPAWN {} {} {}'.format(amount, tile.x, tile.y))

    def enqueueBuild(self, tile: Tile) -> None:
        self.actions.append('BUILD {} {}'.format(tile.x, tile.y))

    def doActions(self) -> None:
        if self.actions:
            self.__hurlInsultMaybe()
            print(';'.join(self.actions))
        else:
            print('WAIT')
        self.actions = []

    def debugActions(self) -> None:
        LOG.debug('Actions: ' + os.linesep.join(self.actions))

    def __hurlInsultMaybe(self) -> None:
        if random.choices([0, 1], weights=[8, 2])[0]:  # about 20% of the time
            self.actions.append(f"MESSAGE {random.choice(self.insults)}")


