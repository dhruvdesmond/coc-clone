# Tickets — the Clash of Ages board (JIRA-style, local markdown)

We have no JIRA server, so tickets live here as markdown, one file per ticket. The board is the epic **COA-TILES**:
rebuild the world as a 10 × 10 tile grid where **every 1 × 1 tile is built AND reviewed, never assumed** (docs/17-tiles.md,
PENDING B36).

Status keys: `TODO` · `IN PROGRESS` · `IN REVIEW` · `DONE`. A ticket reaches DONE only when **every tile it touches has a
passing per-tile review record** in `blender/base/map_world/tiles/REVIEW/<col>_<row>.md`.

| Ticket | Title | Status |
|---|---|---|
| [COA-1](COA-1.md) | Tile framework + per-tile review harness | TODO |
| [COA-2](COA-2.md) | Terrain heightfield, tile by tile | TODO |
| [COA-3](COA-3.md) | Water — river, lake, sea, coast | TODO |
| [COA-4](COA-4.md) | Crossings — bridges, fords, ramps | TODO |
| [COA-5](COA-5.md) | Settlements — village + 3 hamlets | TODO |
| [COA-6](COA-6.md) | Resources — mountain, desert+oil, forest, volcano | TODO |
| [COA-7](COA-7.md) | Dressing + final per-tile sweep | TODO |
