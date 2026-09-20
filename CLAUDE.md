# Clash of Ages — working instructions for Claude

A medieval-to-modern real-time strategy game for Windows and macOS. You start with **one citizen**
and finish with a **missile silo**. Six ages, continuous 3D map, procedural Blender art, Unity 6 URP.

> **Read `PROGRESS.md` first, every session. Update it last, every session.**
> It is the living state of the project: done / in flight / next, the decisions log with reasons, the
> open questions, and every trap already paid for. It exists so a lost chat session costs nothing.
> The design lives in `index.html` + `docs/`. This file is how to *work* here.

---

## 1. Where everything is

```
clash-of-clans/                     ← this repo
├── CLAUDE.md                       ← you are here
├── PROGRESS.md                     ← LIVING STATE. read first, update last.
├── index.html                      ← design hub, opens the 11 docs
├── style.css
├── docs/01-concept … 11-lighting.html
├── blender/scripts/                ← pipeline scripts (synced copies, see §5)
└── unity/ClashOfAges/              ← the game
    └── Assets/
        ├── Editor/    PaletteImporter · SliceZero · ConfigureQuality · Builder
        ├── Game/      RTSCamera · ScrollProbe
        ├── Sim/       (empty — plain C#, NO UnityEngine dependency)
        ├── Models/    FBX from Blender, generated
        └── Resources/palette.json  generated from lib/materials.py

~/blender/                          ← THE ASSET LIBRARY (shared, outside this repo)
├── CLAUDE.md                       ← read before authoring any asset
├── lib/                            ← nodeutils meshkit materials norse modern
│                                      terrain figure mapgen vegetation
├── scripts/                        ← render · review_map · export_palette · export_assets
└── base/<family>/                  ← 35 built assets across 11 families
```

---

## 2. Skills — load these before working

### Created during this project. Both are user-level and available in any session.

| Skill | Load it before | What it covers |
|---|---|---|
| **`blender-procedural`** | authoring **any** 3D asset | The build→preview→final loop, parametric surfaces and geometry, procedural shader networks, realistic light wattages, and Blender 5.x API drift. Has `references/geometry.md`, `references/shading.md`, `references/api-drift.md`. |
| **`procedural-map-assembly`** | combining assets into a map | Append-once/instance-many, terrain and biomes, paths as vertex data, scatter density, and the asserting review harness. Has `references/asset-library.md`, `references/terrain-and-dressing.md`, `references/review.md`. |

These two encode everything learned building the Norse kit, the troop rig, the village map and the
Vale port. **Do not re-derive their contents from the code — load them.**

### Unity skills from the environment

| Skill | Use for |
|---|---|
| `unity:unity-cli` | creating projects, headless builds, running `-executeMethod`, template discovery |
| `unity:unity-package-management` | adding UPM packages headlessly — **the Unity CLI does not manage packages** |
| `unity:ui-uitk` / `unity:ui-ugui` | menus and HUD, once there is one |
| `unity:urp-postprocessing` | the Volume stack — bloom, tonemapping, colour grading |
| `unity:physics-3d-collision` | when selection raycasts or unit collision misbehave |
| `unity:optimize-audio` | the audio pass in `docs/09-fx-audio.html` |
| `unity:build-live-game` | save/progression, much later |

### Other

| Skill | Use for |
|---|---|
| `loop` | the review → improve → run → review cycle |
| `code-review` | before anything lands that others will build on |

---

## 3. The rules

### Blender
1. **`build.py` is the source of truth, not the `.blend`.** GUI edits are destroyed on the next build.
2. **Procedural only** — primitives, modifiers, shader nodes. No downloaded models, no image textures.
3. **Shared code goes in `lib/`.** If two scenes would need it, it belongs in the library.
4. **Fixed `random.seed()`** at the top of every build script. Builds must be reproducible.
5. **Preview render before the final, and LOOK AT THE IMAGE.** Previews are prefixed `preview_`.
6. Run `scripts/set_viewport_colors.py` after building or the scene is grey in the GUI.

### Unity
1. **Anything importing `UnityEditor` lives in `Assets/Editor/`.** Mixing breaks player builds.
2. **Scenes are generated.** `Builder` regenerates before every build. Hand-edits are destroyed
   silently, and the symptom is "my change did nothing". Change the generator.
3. **`Assets/Sim/` must never reference `UnityEngine`** beyond math types. It is the headless,
   testable simulation and the escape hatch to DOTS. Keep it clean from day one.
4. **Visual checks run the Editor in GUI mode, never `-batchmode`.** Under batchmode every draw uses
   one material. Asset-level assertions are still valid there; the image is not.

### Both
- **One agent, one asset or one system.** "Build the Feudal age" produces eight mediocre models.
- **Two tables of the same fact is one table too many.** `lib/materials.py` is the only palette;
  Unity reads the JSON it exports.
- **A measurement rounded past the thing you are measuring is not evidence.** Print enough precision
  to separate the hypotheses, and a count alongside any dimension.
- **When a measurement disagrees with the thing it measures, add a control before changing the
  thing.** A red control quad found a broken capture path in one run, after a long detour spent
  suspecting the materials — which were correct all along.

---

## 4. Commands

```bash
BL=/Applications/Blender.app/Contents/MacOS/Blender
UE=/Applications/Unity/Hub/Editor/6000.0.83f1/Unity.app/Contents/MacOS/Unity
P=/Users/dhruv/clash-of-clans/unity/ClashOfAges

# 1. palette  -> 79 materials into Assets/Resources/palette.json
$BL -b --factory-startup --python ~/blender/scripts/export_palette.py -- \
    --out $P/Assets/Resources

# 2. one asset -> FBX + the assertion sidecar
$BL -b --factory-startup ~/blender/base/huts/models/hut_a.blend \
    --python ~/blender/scripts/export_assets.py -- --name hut_a --out $P/Assets/Models

# 3. verify the bridge  (NOT -batchmode, or the PNG is a single-material grey)
$UE -projectPath $P -executeMethod SliceZero.Verify -logFile /tmp/slice0.log -quit

# 4. quality settings for discrete GPUs
$UE -projectPath $P -executeMethod ConfigureQuality.Apply -logFile /tmp/q.log -quit

# 5. build
$UE -projectPath $P -executeMethod Builder.PerformMacBuild -logFile /tmp/b.log -quit
```

**Targets: discrete GPUs only.** NVIDIA RTX 3060 floor, Apple silicon MacBook Pro (the dev machine is
an M4 Pro, 16-core, 24 GB). Integrated graphics are explicitly not a target — hence 4096 shadow maps,
4 cascades, HDR, SMAA and full post-processing.

---

## 5. Two things that will bite you

**`python3` on this machine is the Xcode Command Line Tools stub and is licence-blocked** — it exits
69 with "You have not agreed to the Xcode license agreements", and a heredoc script will appear to run
while doing nothing. **Use `perl` for scripted edits**, and always print and assert the number of
replacements applied. The same licence gate blocks macOS player builds until someone runs:

```bash
sudo xcodebuild -license accept
```

**`blender/scripts/` in this repo is a synced copy.** The live scripts the commands above call are in
`~/blender/scripts/`, next to the `lib/` they import. If you change one, copy it to the other — or
better, fix this properly by making the repo the authority and pointing `~/blender` at it.

---

## 6. State of play

**Slice 0 is done.** The Blender→Unity bridge is built and verified end to end on one asset:
9/9 assertions pass, reproducibly. Scale exact to the millimetre, 108 objects joined to 1 renderer
with 6 submeshes, 22,548 triangles exact, all 6 materials mapped from the 79-entry palette, tone
correction confirmed applied once.

**Next is slice 1 — one citizen.** A citizen walks to a tree on a heightfield, chops, carries, drops
off, and the wood counter moves. The `citizen` model does not exist yet and is the first thing to
build. See `PROGRESS.md` §5.

**Nothing else is built.** No simulation, no AI, no map generator, no UI.
