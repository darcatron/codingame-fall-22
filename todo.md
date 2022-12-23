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
    * Prioritize killing enemy bots on our side alongside taking over enemy tiles (right now we just take enemy 
      tiles and then neutral tiles after)
  * determine tiles to put recycler
    * Could technically go with a diagonal approach that cuts back towards our side to minimize how far we have to go
    * Sometimes the enemy causes a diagonal blockage that our lockdown algo doesn't detect so we still try to add a 
      recycler even though they've already been cut off (and we might not be able to reach the target tile)
  * move bots to target tiles
    * take into account grass (and maybe enemy bots?) that are in the way (an improvement to the findClosestTile method)
    * don't cover up buildable recycler target locations
    * try to ensure bots aren't taking the same path so we optimize the number of blue tiles
  * build recycler on target ASAP
    * handle enemy bot destroying our bot before we can build a recycler
  * LATER
    * we want any remaining bots to capture tiles and build a recycler or two on our side to get more mats (tbh not 
      sure we want recyclers on our side because they'll kill our land)
    * we may want to stack bots near the lockdown line to prevent enemy bots from crossing before the recyclers are 
      done
      * basically a really heavy front line

### Matush Ideas
#### TODO
1. enemies build recyclers on their side quickly and then move out. This removes a lot of tiles from their side. It 
  takes us a long time to get to past the midway point and build recyclers. We can get overtaken quickly. Maybe we 
  can build the wall at width/3 (first third). This could give us enough time to prevent enemy progression.
2. When bots start going towards the recycler targets, they can converge on a tile. Once they converge, we move them 
  together rather than separately.
  * Tests
    * seed=3064518459982095000 | turn 2 has 3 clumps, turn 4 has 2 clumps
3. assess spawning opportunities separately. Don't spawn until bots are near the lockdown point. Spawn shouldn't 
     get in the way of building the recycler
   * If a recycler is built, we need to ensure enemies don't cross the lockdown line. We can spawn and destroy enemies
4. findClosestTile needs to account for grass and recycler blockers 
   * this looks hard to do cause of the scipy lib we're using.  

#### Variables
* lockdown column
* bot wall spawn distribution

#### Later
* Bots can get stuck between recyclers and grass. We should exclude stuck bots from any actions. 
  * Method to change: Lockdown#findClosestTile 
  * Tests
    * seed=550138732694500030
* When we spawn a bot, we don't incorporate it into our MOVE action. We might not always want to but move the newly 
  spawned unit but if we're trying to overtake enemies, we'll need to ensure we move everyone together. If we don't 
  yet own the destination tile, there's no way to spawn new bots on the destination tile.
  * E.g. 1 bot at (2, 4) moving to (2, 5). We might SPAWN 1 at (2,4) and then MOVE only 1 unit to (2, 5)
  * Tests
    * seed=3064518459982095000 
      * Turn 5: (DEBUG) Actions: MOVE 2 6 5 8 1 | MOVE 2 6 7 8 4 | SPAWN 1 6 5
* We need to consider the rest of the map to see if we have a lockdown due to grass or enemy obstacles. Sometimes 
  our bots end up in a position to build a recycler that would create a lockdown outside the desired column. We can 
  try to pay attention to this and build the recycler.  
  * Tests
    * seed=3064518459982095000
      * In this game, we think we need recyclers on (8,1) (8,4) (8,6) (8,9) (8,10). We don't need it at (8,10) 
        because there's a grass tile next to (8,10) that naturally creates the lockdown

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
12/19/22 09:20 (initial lockdown strat) - PROMOTED to Bronze League rank 1592/2692
12/19/22 14:54 (initial reclaim) - PROMOTED to Silver League 
12/23/22 14:23 (no changes) - 1,589 / 1,746
