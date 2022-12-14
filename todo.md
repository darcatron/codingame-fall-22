# Strategy
Flood fill?
  * Works well when bots can go all directions
  * Works okay on corners
  * If we maximize recycler coverage, it would perform better

Divide and conquer
    * Have bots split up. Half the bots go to mid-map or just beyond mid-map. Dropping recyclers along the way
    * Flood fill after reaching mid-map or just beyond mid-map

Phase 1
  * Collect mats
  * Prioritize recyclers over bots
Implementation
  * have bots move to closest, adjacent, unowned tiles - keep track of where one bot is sent so another isn't also sent there
  * if possible, build a recycler 
    * Later - avoid double-dipping on recycler tiles
    * 

Phase 2
* Prioritize bot building to own more tiles

General thoughts
    * Bots shouldn't stay on tiles they own if oppo bots are not close to those tiles

# Tasks
- 
- implement trash talking