# COA-7 · Dressing + final per-tile sweep

**Epic:** COA-TILES · **Status:** TODO · **Depends:** COA-1..6 · **Tiles:** all 100

## Summary
Grass, flowers, rocks and props per tile, then a **final sweep that renders and re-asserts all 100 tiles** and confirms the
world assembles seamlessly. This ticket replaces the old whole-map `build.py`.

## Acceptance criteria
- [ ] Ground cover per tile (density by biome), clear of pads/roads/water; reviewed per tile.
- [ ] Final sweep: all 100 tiles render + pass their asserts in one run; a `REVIEW/` record for every tile.
- [ ] The assembled 420 m world has no seam, no stairs at crossings, no building on a road/crossing, oil upright — the B35 bugs cannot recur.
- [ ] Hero + region finals rendered from the assembled world; the old `build.py` retired.
