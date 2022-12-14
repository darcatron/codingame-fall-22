from GameState import GameState

class Parser:
    @staticmethod
    def parseMap() -> GameState:
        width, height = [int(i) for i in input().split()]
        return GameState(width, height)

    @staticmethod
    def parseTurnInput():
        pass
