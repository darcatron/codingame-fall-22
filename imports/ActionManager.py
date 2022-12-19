import sys

from imports.Tile import Tile
from imports.MoveAction import MoveAction


class ActionManager:
    def __init__(self):
        self.actions = []

    def enqueueMoveAction(self, moveAction: MoveAction) -> None:
        self.actions.append(moveAction.getActionString())

    def enqueueMove(self, numUnits: int, fromTile: Tile, toTile: Tile) -> None:
        moveAction = MoveAction(numUnits, fromTile, toTile)
        self.enqueueMoveAction(moveAction)

    def enqueueSpawn(self, amount, tile: Tile) -> None:
        self.actions.append('SPAWN {} {} {}'.format(amount, tile.x, tile.y))

    def enqueueBuild(self, tile: Tile) -> None:
        self.actions.append('BUILD {} {}'.format(tile.x, tile.y))

    def doActions(self) -> None:
        print(';'.join(self.actions) if len(self.actions) > 0 else 'WAIT')
        self.actions = []

    def debugActions(self) -> None:
        print('(DEBUG) Actions: ' + ';'.join(self.actions), file=sys.stderr, flush=True)


