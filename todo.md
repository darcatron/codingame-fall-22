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
  * next big step is to have our bots handle lockdown success!
    * Kill any enemy bots on our side, and also move to take back any enemy territory on our side
    * Then, once they are gone we can just casually take over our entire side
  * determine tiles to put recycler
    * Could technically go with a diagonal approach that cuts back towards our side to minimize how far we have to go
  * move bots to target tiles
    * try to ensure bots aren't taking the same path so we optimize the number of blue tiles (this also helps avoid infinite loop problems with the auto-move option)
  * build recycler on target ASAP
    * handle enemy bot destroying our bot before we can build a recycler
  * LATER
    * we want any remaining bots to capture tiles and build a recycler or two on our side to get more mats
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