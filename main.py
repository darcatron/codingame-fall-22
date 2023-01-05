
# Start Owned Imports
from imports.Lockdown import Lockdown
from imports.Parser import Parser
# End Owned Imports


gameState = Parser.parseMap()

startedOnLeftSide = True  # Dynamically set in first turn
turnNumber = 1

# game loop
while True:
    gameState.resetForTurn()
    Parser.parseMatterInventory(gameState)
    Parser.parseTurnInput(gameState)

    if turnNumber == 1:
        myUnitX = gameState.myUnits[0].x if len(gameState.myUnits) > 0 else 0
        oppoUnitX = gameState.oppoUnits[0].x if len(gameState.oppoUnits) > 0 else 0
        startedOnLeftSide = myUnitX < oppoUnitX
        gameState.startedOnLeftSide = startedOnLeftSide

    lockdown = Lockdown(gameState)
    lockdown.takeActions(turnNumber)

    turnNumber += 1
