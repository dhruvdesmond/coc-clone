# COA-2 · Terrain heightfield, tile by tile

**Epic:** COA-TILES · **Status:** TODO · **Depends:** COA-1 · **Tiles:** all 100

## Summary
Generate the terrain height for the whole grid, then **build and review each tile's terrain individually**: correct biome
and elevation band, and — the hard one — **seams continuous to < 1 cm** with every neighbour so tiles assemble with no cracks or steps.

## Acceptance criteria
- [ ] `raw_h(x,y)` (or its successor) evaluated per tile; each tile's mesh built on its own.
- [ ] Per tile: biome matches the tile's declared type; elevation within the tile's band.
- [ ] **Seam assert:** at every shared edge, this tile's height == the neighbour's height to < 1 cm, sampled along the edge.
- [ ] Slopes buildable where they must be (< 12°) and cliffs where they must be (> 35°), per tile.
- [ ] Every one of the 100 tiles has a passing `REVIEW/<c>_<r>.md`; the assembled terrain has no visible seam.
