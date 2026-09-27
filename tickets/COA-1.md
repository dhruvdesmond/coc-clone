# COA-1 · Tile framework + per-tile review harness

**Epic:** COA-TILES · **Status:** TODO · **Blocks:** COA-2..7 · **Tiles:** all 100 (framework)

## Summary
Build the foundation for a tile-reviewed world: a 10 × 10 grid (42 m tiles, 420 m world), a tile registry, one close
camera per tile, and the **compulsory per-tile review harness** that every later ticket uses.

## Why
The old whole-map build reviewed in aggregate and missed the bridge-as-stairs and house-at-the-crossing bugs. Review must
be per tile and mandatory (PENDING B36, docs/17-tiles.md §2).

## Acceptance criteria (Definition of Done)
- [ ] `blender/base/map_world/tiles/grid.py`: the 10×10 grid, tile `(col,row)` addressing, world 420 m, tile 42 m.
- [ ] A **camera per tile** framing the 42 m tile + a small seam margin.
- [ ] `tiles/review.py` runs, per tile, ALL of docs/17-tiles.md §2: float/sink (1 cm), overlap, biome match, building
      keep-out (roads + 14 m from crossings), water-meets-bank, **seam continuity to < 1 cm** with 4 neighbours, resource sanity.
- [ ] Each tile writes `tiles/REVIEW/<col>_<row>.md` (render path + every assert pass/fail + the measured numbers).
- [ ] A FAILED assert makes the build exit non-zero on that tile (fix, don't skip).
- [ ] Proven on a trivial 2×2 sub-grid: renders + records exist, a deliberately broken tile FAILS.
