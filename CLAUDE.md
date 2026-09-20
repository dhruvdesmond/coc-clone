# Clash of Ages — working instructions for Claude

**A Rise of Nations clone** — medieval to modern, for Windows and macOS. You start with **one
citizen** and finish with a **missile silo**. Six ages, continuous 3D map, procedural Blender art,
Unity 6 URP.

**The reference is Rise of Nations, not Clash of Clans.** That matters when making judgement calls:
the game is fought over **territory drawn as colour on the map**, with attrition inside borders,
cities as the territory instrument, rare resources, national powers, and a shared Armageddon counter.
If a proposed feature would work equally well in a base-builder, it is probably the wrong feature.
See `docs/12-territory.html`.

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
├── index.html                      ← design hub, opens the 13 docs
├── style.css
├── docs/01-concept … 13-demo.html
├── tools/                          ← u.sh (guarded Unity runner) · test.sh · export_all.sh
├── art/unit_sheet.png              ← the units, their pivots and their poses, rendered in Blender
├── blender/scripts/                ← AUTHORITATIVE pipeline scripts: export_palette · export_assets ·
│                                      export_figure · export_nature · figure_sheet
├── blender/base/age1_demo/         ← models authored HERE (Rune Hall, Muster Hall, Farm)
└── unity/ClashOfAges/              ← the game
    └── Assets/
        ├── Sim/       THE GAME. Pure C#, noEngineReferences, 20 Hz. World · Commands · Catalog · Territory · RaidDirector
        ├── Game/      Core (GameRoot, PlayerInput, DemoAutopilot) · Views · World (instancing) · Fx · Shaders
        ├── UI/        Hud · Minimap · UiKit — uGUI built in code
        ├── Editor/    DemoSceneBuilder · DemoVerify · SceneKit · PaletteImporter · UnitSilhouette · Builder …
        ├── Tests/     EditMode sim tests
        ├── World/     terrain + world_meshes.fbx + world.bytes (generated)
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

### This repo and `~/blender`
**Never write inside `~/blender`.** It is not under version control, a live mobile session edits it, and its
rules make `lib/` and `scripts/` integrator-owned. Pipeline scripts live in **this repo's** `blender/scripts/` and
are authoritative; new models are authored in `blender/base/<name>/build.py` here, importing `~/blender/lib`
read-only by absolute path.

### Both
- **The reference is Rise of Nations.** If a proposed feature would work equally well in a
  base-builder, it is probably the wrong feature. The game is fought over territory drawn as colour.
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

# THE THREE YOU WILL ACTUALLY USE
tools/test.sh                        # 10 headless sim tests. Batchmode is safe: no pixels.
tools/u.sh play DemoVerify.Full      # a bot plays the whole demo in the Editor: 8 screenshots, asserts, exits
tools/u.sh compile                   # ALWAYS before a GUI run -- a compile error in GUI mode hangs on a dialog

tools/export_all.sh [figures|buildings|new|nodes|all]   # re-export every Blender asset the demo uses

# palette -> 82 materials. --scan reads materials that live only inside an asset .blend
$BL -b --factory-startup --python blender/scripts/export_palette.py -- --out $P/Assets/Resources \
    --scan ~/blender/base/starter/models/node_food.blend ~/blender/base/starter/models/node_iron.blend

# the land: unique meshes + instance matrices (axes MEASURED: Blender (x,y,z) -> Unity (-x,z,-y))
$BL -b --factory-startup ~/blender/base/map_village/map_village.blend \
    --python blender/scripts/export_nature.py -- --out $P/Assets/World

# verify the bridge  (NOT -batchmode, or the PNG is a single-material grey)
tools/u.sh gui SliceZero.Verify

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

**Never edit `Assets/` while an Editor run is live** — Unity can recompile mid-play and the run dies oddly. And
delete the log before launching a run you intend to wait on: a wait-loop will happily match the *previous* run's
log and hand you stale numbers.

---

## 6. State of play

**There is a playable demo** — one citizen to the Feudal Age, borders drawn as colour, raids, a win screen. A bot
plays it start to finish and wins (`tools/u.sh play DemoVerify.Full`). Read `docs/13-demo.html` for what is real,
what is scripted and what is faked. **No human has played it yet** — that is the next thing (PROGRESS N8).

**Slice 0 is done.** The Blender→Unity bridge is built and verified end to end on one asset:
9/9 assertions pass, reproducibly. Scale exact to the millimetre, 108 objects joined to 1 renderer
with 6 submeshes, 22,548 triangles exact, all 6 materials mapped from the 79-entry palette, tone
correction confirmed applied once.

**Borders, build-inside-only, attrition and regen are built.** Cities, rare resources, nations and the Armageddon
counter (the rest of `docs/12-territory.html`) are not. The opponent is a scripted `RaidDirector`, not doc 06's AI.
**The units have no skeleton** — limb hierarchies posed in code (DL36). See `PROGRESS.md` §5 for what is next.
