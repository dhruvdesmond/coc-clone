# 17 · The Tiled Rebuild — review every tile, assume nothing (B36)

> Direction, 2026-09-27 (PENDING B36): *"let's make the review a compulsory part of everything that we do. even the
> tiniest bit of a pixel, we should review. even 1 cm."* + *"create the map again from scratch. a few JIRA tickets. in each
> ticket a map of 10 by 10. for each 1×1 tile: it should always be reviewed, not assumed."*
>
> This supersedes the whole-map build (`map_world/build.py` builds the world in one pass and reviews it in aggregate).
> The bridge-as-stairs and the house-at-the-bridge-mouth bugs (B35) are exactly what an aggregate review misses and a
> **per-tile** review catches. So: rebuild the world as a **10 × 10 grid of tiles**, and **build AND review every 1 × 1
> tile on its own** before it is accepted. Nothing is assumed correct.

## 1. The grid

- The world is **10 × 10 = 100 tiles**. Each tile is **42 × 42 m**, so the world is **420 × 420 m** (unchanged size).
- A tile is addressed `(col, row)`, `col` and `row` in `0..9`. `(0,0)` is the SW corner.
- Each tile carries: its **biome/type**, its **elevation band**, the **features** it owns (terrain, water, a building, a
  resource, a road segment), and its **review record** — the close render that was looked at and the asserts that passed.
- Neighbouring tiles must be **seamless**: terrain height is continuous across every shared edge (to < 1 cm), and any
  river / road / coastline that crosses an edge must line up on both sides. Seam continuity is a hard assert.

## 2. The rule: review is compulsory, per tile, never assumed

Every tile, before it is marked done, gets **both**:

1. **A close render** — a camera framed on that one 42 m tile (plus a small margin for the seam), rendered and **looked at**
   by the model. Not the hero shot. The tile fills the frame.
2. **Asserting checks** (`tiles/review.py`), all of which must pass or the tile FAILS the build:
   - nothing floating (> 0.4 m above ground) or sunken (buried) within the tile;
   - no two objects overlapping beyond eaves tolerance;
   - every object in the biome/type the tile declares;
   - buildings on dry, flat ground, **not on a road and not within 14 m of a bridge end or ford** (the B35 fix, now a rule);
   - water meets its banks — no floating deck, no step where a bridge/ford lands (the B35 bridge-as-stairs fix);
   - **seam continuity** with all four neighbours (terrain height, river, road, coast line up to < 1 cm);
   - resource sanity — e.g. an oil derrick stands upright on dry desert over its seep, not floating, not in grass.
- The tile's review record (render path + each assert's pass/fail + what was measured) is written to `tiles/REVIEW/<col>_<row>.md`.
- **"Even 1 cm"**: the seam and float/sink tolerances are 1 cm, printed to the millimetre. A disagreement bigger than that
  fails the tile. No tile is accepted because it "looks fine from the hero shot."

## 3. The JIRA tickets (the epic, in `tickets/`)

The rebuild is one epic, `COA-TILES`, split into the tickets below. Each ticket owns a subsystem across the 10 × 10 grid,
and its **Definition of Done is that every tile it touches has been individually reviewed** (§2), recorded, and passes.

| Ticket | Title | Tiles it owns | Done when |
|---|---|---|---|
| **COA-1** | Tile framework + per-tile review harness | all 100 (the grid, cameras, registry) | the grid, one camera per tile, `tiles/review.py` asserting §2, and the per-tile `REVIEW/<c>_<r>.md` all exist and run |
| **COA-2** | Terrain heightfield, tile by tile | all 100 | every tile's terrain reviewed: correct biome + elevation, **seams continuous to < 1 cm** with neighbours |
| **COA-3** | Water — river, lake, sea, coast | the ~24 water/edge tiles | every water tile reviewed: water meets banks, coast lines up across seams, no floating water |
| **COA-4** | Crossings — bridges, fords, ramps | the ~4 crossing tiles | every crossing reviewed: the road RAMPS onto the deck (no stairs), the deck lands on both banks, nothing blocks the mouth |
| **COA-5** | Settlements — village, 3 hamlets | the ~16 settlement tiles | every building reviewed: dry flat ground, not on a road, ≥ 14 m from a crossing, dressed, pads blend (no terraces) |
| **COA-6** | Resources — mountain, desert+oil, forest, volcano | the ~40 resource tiles | every resource reviewed in place: oil derricks upright on dry desert over a seep, ore at the mountain foot, uranium on the volcano, fish in water |
| **COA-7** | Dressing + final per-tile sweep | all 100 | grass/props reviewed per tile; a final pass renders and re-asserts all 100 tiles; the world assembles seamlessly |

"A few different tickets, each a 10 × 10 map" = these seven tickets, each acting on the one 10 × 10 grid, in order. Each is
a stage; together they build and review the whole world tile by tile.

## 4. How a tile is built and reviewed (the loop, per §2)

```
for col in 0..9, row in 0..9:
    build the tile's terrain + features (only this tile)
    render a close camera on the tile  ->  tiles/renders/<col>_<row>.png
    run review.py on the tile          ->  asserts + seam check vs neighbours
    write tiles/REVIEW/<col>_<row>.md  (render + every assert + measurements)
    if any assert FAILS: the build stops on that tile (rc != 0) -- fix, don't skip
```

The model **looks at** each tile render (the skill's "look at the image" rule, now per tile), and the asserts are the
floor, not the ceiling. A tile is done only when both the eye and the asserts pass.

## 5. Where it lives

- `blender/base/map_world/tiles/` — `grid.py` (the 10×10 grid + tile registry + cameras), `tile_build.py` (build one
  tile), `review.py` (the per-tile asserts + seam checks), `REVIEW/<c>_<r>.md` (records), `renders/<c>_<r>.png`.
- The old whole-map `build.py` stays as reference until COA-7 replaces it.
- Tickets in `tickets/COA-*.md`.

Clash of Ages — a Rise of Nations clone. Changes here mirror the Decisions log in `PROGRESS.md`. 2026-09-27.
