# Lockdown Strategy 🔒
  * Move past a derived column and build recyclers to prevent the enemy from breaching that column
  * Invade and destroy enemy territory

## Others considered
### Flood fill
  * Works well when bots can go all directions
  * Works okay on corners
  * If we maximize recycler coverage, it would perform better

### Divide and conquer
  * Have bots split up. Half the bots go to mid-map or just beyond mid-map. Dropping recyclers along the way
  * Flood fill after reaching mid-map or just beyond mid-map

## Implementation
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
#### Ideas
BUG 
  - seed=-2675635324638569500 Enemy gets passed lockdown col

1. Island capture
    * if it can't move forward, fight to destroy the island
      * seed=5713223225368061000
    * seed=8731928637395273000 
    * seed=1850738959795485400
      * would have won if we captured (9, 8) thru (12, 8) island
    * seed=41677082687474904
      * turn 21 shouldnt build recycler on (4,5). bot should capture the island
      * would have tied if it captured
    * seed=-2551717726100370400
    * seed=-7411460117948978000 - would have won if we captured this island
    * seed=7271542478827317000 - would have won if we captured (11,7) island around turn 24
2. Build recyclers spread out on enemy side***
   * seed=-8049619562529677000
     * bunch of bad recycler placements. more notable one was on bottom row at (7,6) when enemy recyclers were 
       already placed on the 3 top adjacent tiles.
3. Better bot utilization
   * Don't target lockdown tiles if bot is far from it, just wait until next turn for nearby bot to capture it
     * seed=-8687848559375048000 - turn 7 (10,1) is used to capture a far tile and moves down instead of forward
5. Better lockdown
   * seed=-8049619562529677000
     * This is locked cause the bottom tiles are green. No need to build recycler at (4,5)
   * seed=-9058728574429583000
     * recycler not necessary at (14,9) bc it will become an island
     * can remove bestLockdownTile if all 4 sides are grass or recycler or (if inrangeofrecycler, must be scraped by 
       recycler in range -- aka this tile isn't responsible for scraping the adjacent tile)
   * seed=-1912384040002314200 against Guizmol (but should be the same result against anyone)
     * (6,1) recycler isn't necessary - this is hard to recognize programmatically
     * Guizmol gets through lockdown cause we're out of resources


unused bot used to capture tile that's too far away
    * seed=9142638467907253000


### Sean
Better invade
   * Idea: focus on capturing tiles further out
     * spawn bots on further out tiles rather than randomly. Also spawn more than 1 to claim more land
     * hunt forward, not backwards whenever possible
   * building recyclers strategically on enemy side - reduces # of tiles they can capture

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
* We start so close to the center that we can't lockdown and get wrecked
  * seed=-6390432817551423000



#### Variables
* lockdown column
* enemy bot hunting distance minimum
* myBotsAdvantageBuffer

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
- implement trash talking
- become legends

## Arena results
* 12/19/22 09:20 (initial lockdown strat) - PROMOTED to Bronze League rank 1592/2692
* 12/19/22 14:54 (initial reclaim) - PROMOTED to Silver League 
* 12/23/22 14:23 (no changes) - 1,589 / 1,746
* 12/24/22 14:07 (initial invade) - 1,327 / 1754
* 12/24/22 17:27 (lots more added to invade) - 931 / 1753
* 12/25/22 9:53 (no change) - 879 / 1746
* 12/25/22 14:40 (committed latest) - 818 1,744
* 12/25/22 15:25 (wall and hunting++) - 459 / 1747
* 12/25/22 15:40 (cleaned up and committed latest) - 529 / 1746
* 12/31/22 15:37 (no changes) - 449 / 1815
* 1/2/23 11:14 (cleanup - no functional changes) - 675 / 1834
* 1/2/23 11:29 (fix defensive wall bug) - 518 / 1835
* 1/3/23 00:17 (only hunt forward) - 244 / 1825
* 1/3/23 12:00 (improvements - cant remember) - 128 / 1828
* 1/4/23 16:13 (improvements - cant remember) - 282 / 1832
* 1/4/23 16:37 (spawn improvements, best recycler tile optimization) - 75 / 1834
* 1/4/23 23:06 (sean takes over from 'sean help') - 172 / 1830
* 1/4/23 23:25 (sean makes minor updates to the spawn/build avoidance on owned islands) - 218 / 1830
* 1/5/23 00:07 (invade tries capturing neutral tiles if there aren't enemy tiles to capture) - 193 / 1828
* 1/5/23 00:22 (remove minimap island logic, and add island capture logic) - 30 / 1831
* 1/5/23 00:52 (update tile capture logic to try to pick the closest bot to the target tile) - 348 / 1831
* 1/5/23 01:05 (fix timeouts from the tile capture logic with some late night hacking, ow my brain) - 174 / 1831
* 1/5/23 01:27 (revert the last two updates) - 79 / 1831
* 1/5/23 01:49 (push out the lockdown column by one and do a better job defending it) - 18 / 1830
* 1/5/23 02:17 (make sure to update botOptions for units used in defending the bot wall) - 23 / 1829
* 1/5/23 02:36 (make defensive bot wall building take into account the recyclers that we are building this turn) - 71 / 1827 
* 1/5/23 02:50 (prioritize building recyclers that are closest to the enemy first, and change lockdown column logic to not bump by one if the map height is large) - 97 / 1827 
* 1/5/23 03:05 (build bot wall first before building recyclers to prioritize blocking enemies if possible) - 162 / 1827
* 1/5/23 03:22 (revert last change) - 16 / 1827
* 1/5/23 03:45 (try bumping lockdown column by another one, up to a limit though) - 90 / 1826
* 1/5/23 final (revert last change) - 15 / 1826

