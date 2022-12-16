
# Start Owned Imports
from imports.Lockdown import Lockdown
from imports.Parser import Parser
# End Owned Imports


gameState = Parser.parseMap()

# game loop
while True:
    gameState.resetForTurn()
    Parser.parseMatterInventory(gameState)
    Parser.parseTurnInput(gameState)
    Lockdown.takeActions(gameState)
