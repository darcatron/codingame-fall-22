# Strategy
## Flood fill
  * Works well when bots can go all directions
  * Works okay on corners
  * If we maximize recycler coverage, it would perform better

## Divide and conquer
  * Have bots split up. Half the bots go to mid-map or just beyond mid-map. Dropping recyclers along the way
  * Flood fill after reaching mid-map or just beyond mid-map

## Lockdown ✅
  * Move past the midline and build recyclers to prevent the enemy from leaving that space

### Implementation
  * after blocking column success:
    * Prioritize killing enemy bots on our side alongside taking over enemy tiles (right now we just take enemy tiles and then neutral tiles after)
  * determine tiles to put recycler
    * Could technically go with a diagonal approach that cuts back towards our side to minimize how far we have to go
    * Sometimes the enemy causes a diagonal blockage that our lockdown algo doesn't detect so we still try to add a recycler even though they've already been cut off (and we might not be able to reach the target tile)
  * move bots to target tiles
    * take into account grass (and maybe enemy bots?) that are in the way (an improvement to the findClosestTile method)
    * don't cover up buildable recycler target locations
    * try to ensure bots aren't taking the same path so we optimize the number of blue tiles
  * build recycler on target ASAP
    * handle enemy bot destroying our bot before we can build a recycler
  * LATER
    * we want any remaining bots to capture tiles and build a recycler or two on our side to get more mats (tbh not sure we want recyclers on our side because they'll kill our land)
    * we may want to stack bots near the lockdown line to prevent enemy bots from crossing before the recyclers are done
      * basically a really heavy front line

## General thoughts
  * Bots shouldn't stay on tiles they own if oppo bots are not close to those tiles
Phase 1
  * Collect mats
  * Prioritize recyclers over bots
Phase 2
  * Prioritize bot building to own more tiles

# Other Tasks
- implement trash talking
- become legends

## Arena results
12/19/22 08:45 (initial lockdown strat) - PROMOTED to Bronze League rank 1592/2692