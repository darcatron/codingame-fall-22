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
  * determine tiles to put recycler
    * LATER
      * account for tiles that are owned by oppo
      * account for fact that we can start on either side
  * rush 3 bots to target tiles
    * make sure bots aren't all going to the same tile
    * start with just having the bots MOVE to TARGET
    * LATER - try to ensure bots aren't taking the same path so we optimize the number of blue tiles
    * LATER - depending on height, we may need fewer or more bots to travel
  * build recycler on target ASAP
    * LATER - handle enemy bot destroying our bot before we can build a recycler
  * LATER
    * we may want the lone bot to build recyclers on our side to get more mats
    * we may want to stack bots near the lockdown line to prevent enemy bots from crossing before the recyclers are done 

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