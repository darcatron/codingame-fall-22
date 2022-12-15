import re
import time
import pyperclip as pc

# This must be in the correct import order!
classesToMerge = ['Tile', 'GameState', 'Parser', 'ActionManager', 'Lockdown']

def isRemoveableImportLine(line: str) -> bool:
    if "import" not in line:
        return False

    for className in classesToMerge:
        if className in line:
            return True
    return False

def getClassImports():
    print("Getting classes...")
    classImports = ''
    for desiredImport in classesToMerge:
        with open('imports/' + desiredImport + '.py') as fileToImport:
            line = fileToImport.readline()
            while line != '':
                if not isRemoveableImportLine(line):
                    classImports += line
                line = fileToImport.readline()

            classImports += '\n'

    return classImports

def merge():
    print("Merging this beautiful solution...")
    classImports = getClassImports()
    with open('winner_' + str(time.time()) + ".py", 'x') as mergedFile:
        with open('main.py') as originalFile:
            fileData = originalFile.read()
            print("Merging...")
            mergedFileData = re.sub("# Start Owned Imports[\s\S]*End Owned Imports", classImports, fileData)
            mergedFile.write(mergedFileData)
            pc.copy(mergedFileData)
    print("Not a gram on her!")

merge()

