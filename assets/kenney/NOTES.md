# Kenney CC0 asset integration — findings (2026-09-27, B31/P10)

## Packs downloaded (CC0, public domain)
- **Fantasy Town Kit** (`fantasy-town/`, 167 models): modular buildings + props (cart, fountain, stall, windmill BLADES,
  watermill, lanterns, banners, fences, hedges, chimney). GLB used; FBX/OBJ gitignored.
- **Nature Kit** (`nature/`, 329 models, GLTF format folder): trees (blocks/cone/default/detailed/fat/oak/palm ×dark/fall),
  rocks, stone bridges, ground/path pieces.

## Import (proven, local via tools/bl.sh)
- `bpy.ops.import_scene.gltf(filepath=...)` -> a single MESH per model, parent=None, named after the file. Textures load.
- Some models (windmill) are PARTS not whole buildings: `windmill.glb` is only the sail/blade cross (thin in X, centred on
  origin so half sinks below z=0). Re-origin every placed model so its min-Z sits on the ground.

## The building grid (measured)
- 1-unit cells. `wall.glb` / `wall-door` / `wall-window-glass`: a thin panel on the +X EDGE of a 1x1 cell (local X≈+0.45,
  spans Y[-0.5,0.5], Z[0,1]), origin at cell centre. Rotate about Z to face a wall outward: +X=0°, -X=180°, +Y=90°, -Y=270°.
  Stack storeys by +1 in Z. Walls assemble into a beautiful plaster+timber house (proven, `/tmp/house.png`).
- `wall-block.glb`: a solid 1x1x1 block (foundations / solid walls).

## The roof modules (rendered labelled, /tmp/roofs.png)
- `roof-gable` (1.10 x 1.07 x 0.57): a COMPLETE gable segment for ONE cell -- ridge along X, slopes ±Y, base at z=0.
- `roof-gable-end`: the triangular GABLE-END wall (vertical), for the ends of a gable roof.
- `roof-gable-top`: a variant gable, NOT a ridge cap -- do NOT stack it on roof-gable (that was the floating-roof bug).
- Hip roof set: `roof` (slope tile), `roof-left`/`roof-right` (timber-edged end slopes), `roof-corner`/`roof-corner-inner`
  (hip corners), `roof-point` (pyramid cap). For a square building: 4x roof-corner + roof-point.
- `roof-window`, `roof-flat` also exist.

## Next (the major step, P10): a PARAMETRIC BUILDING GENERATOR
Compose a house from a footprint (nx, ny, storeys): floor -> perimeter walls (door + windows placed) -> matching roof
(gable for long buildings, hip/pyramid for square). Then a table of building recipes maps our game buildings (hall, hut,
forge, ...) to sizes/roofs. Then the map asset-layer rewrite places them via AssetLibrary (GLB import).
