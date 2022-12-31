import os

from imports.LOG import LOG
from imports.Tile import Tile


class ActionManager:
    def __init__(self):
        self.actions = []

    def enqueueMove(self, numUnits: int, fromTile: Tile, toTile: Tile) -> None:
        self.actions.append(f"MOVE {numUnits} {fromTile.x} {fromTile.y} {toTile.x} {toTile.y}")

    def enqueueSpawn(self, amount, tile: Tile) -> None:
        self.actions.append('SPAWN {} {} {}'.format(amount, tile.x, tile.y))

    def enqueueBuild(self, tile: Tile) -> None:
        self.actions.append('BUILD {} {}'.format(tile.x, tile.y))

    def doActions(self) -> None:
        print(';'.join(self.actions) if len(self.actions) > 0 else 'WAIT')
        self.actions = []

    def debugActions(self) -> None:
        LOG.debug('Actions: ' + os.linesep.join(self.actions))


