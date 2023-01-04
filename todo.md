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

### Matush
1. implement trash talking
2. Better lockdown
   * seed=-8049619562529677000
     * This is locked cause the bottom tiles are green. No need to build recycler at (4,5)

### Later
* If adjacent tile to lockdown tile is grass or recycler, it's in a lockdown (LockdownState#L17). We don't need to 
   spawn a defense bot on tiles that are next to grass or recyclers either
* Getting killed by recyclers that grassify a square 
* Getting many bots stuck on an island/Spawning excessive bots on an island
* Bots can get stuck between recyclers and grass. We should exclude stuck bots from any actions. 
  * Method to change: Lockdown#findClosestTile 
  * Tests
    * seed=550138732694500030
* https://github.com/darcatron/codingame-fall-22/pull/4#discussion_r1059464702
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
findClosestTile needs to account for grass and recycler blockers 
   * this looks hard to do cause of the scipy lib we're using. We'd need a graph rather than a k-d grid

Crazy maps
* Only one path to get to the other side. Bots end up destroying their own territory.
  * seed=-7202217520983007000


#### Variables
* lockdown column
* enemy bot hunting distance minimum
* myBotsAdvantageBuffer
* range to look for reachable enemy tiles for the invade
* reachability values for opponent / neutral tiles for the invade

Game constraints: 
12 ≤ width ≤ 24
6 ≤ height ≤ 12


## General thoughts
  * Bots shouldn't stay on tiles they own if oppo bots are not close to those tiles
Phase 1
  * Collect mats
  * Prioritize recyclers over bots
Phase 2
  * Prioritize bot building to own more tiles

# Other Tasks
- become legends

## Sean invade plan
* find tiles to put recyclers on in enemy territory 
  * for all MY empty tiles on enemy side of lockdown, filter down to those that:
    * add as many net-new grass tiles as possible (keep in mind existing recyclers may already be scheduled to grassify some, also take into account scrap amount differences), prioritizing grassification of enemy then neutral then my tiles
    * don't block MY bots from advancing (better to build them behind, closer to the lockdown col)
      * to do this look at adjacent tiles (prioritizing up, down, and forward) and count up how many are "blocked" (are grass or will be grass next turn, have too many enemy bots, or have a recycler)
* (DONE) spawn on MY tiles on enemy side of lockdown that have the most enemy tiles in some adjacent range (e.g. within 3 reachable tiles), filtering out tiles that are on schedule to be grassified
* (DONE) move bots on enemy side of lockdown to capture more enemy territory
  * spread out rather than attack one place so we are harder to block
  * once again, prioritize moving to enemy tiles that have the most enemy tiles in some adjacent range (e.g. within 3 reachable tiles), filtering out tiles that are on schedule to be grassified
    * can move proportionally to how many of those enemy tiles there are in range 
    * can also consider neutral tiles secondarily

### Improvements
* for move, don't include the sourceTile and other adjacentTiles in the reachability tile traversal per adjacentTile (if we wanted that value, we would just choose that adjacentTile)
* also for move, split up based on how many enemy bots are on/adjacent to the target tiles (prefer splitting if possible to do so without putting our bots in danger)
* for spawn, come up with some semblance of island detection (and prediction based on where we think they may block us)
  * then prioritize spawning based on the contents of each island
    * if we have one tile left on an island, make sure to reinforce it
    * if the enemy has one tile left on an island, spawn next to it and take it
    * otherwise, determine where to spawn based on some combo of the size of the island and the bot differential between us and the enemy on the island

### Test losing seeds for better invade
* 4331125007385936000

## Arena results
12/19/22 09:20 (initial lockdown strat) - PROMOTED to Bronze League rank 1592 / 2692
12/19/22 14:54 (initial reclaim) - PROMOTED to Silver League 
12/23/22 14:23 (no changes) - 1,589 / 1,746
12/24/22 14:07 (initial invade) - 1,327 / 1754
12/24/22 17:27 (lots more added to invade) - 931 / 1753
12/25/22 9:53 (no change) - 879 / 1746
12/25/22 14:40 (committed latest) - 818 1,744
12/25/22 15:25 (wall and hunting++) - 459 / 1747
12/25/22 15:40 (cleaned up and committed latest) - 529 / 1746
12/31/22 15:37 (no changes) - 449 / 1815
1/2/23 11:14 (cleanup - no functional changes) - 675 / 1834
1/2/23 11:29 (fix defensive wall bug) - 518 / 1835
1/2/23 16:28 (no changes) 539 / 1832
1/2/23 18:09 (initial sean invade strat) 1633 / 1834