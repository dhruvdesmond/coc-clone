# Clash of Ages — working instructions for Claude

**A Rise of Nations clone** — medieval to modern, for Windows and macOS. You start with **one
citizen** and finish with a **missile silo**. Six ages, continuous 3D map, procedural Blender art,
Unity 6 URP.

**The reference is Rise of Nations, not Clash of Clans.** That matters when making judgement calls:
the game is fought over **territory drawn as colour on the map**, with attrition inside borders,
cities as the territory instrument, rare resources, national powers, and a shared Armageddon counter.
If a proposed feature would work equally well in a base-builder, it is probably the wrong feature.
See `docs/12-territory.html`.

> **Read `PENDING.md` and `PROGRESS.md` first, every session. Update them last, every session.**
> `PENDING.md` is the queue and the pointer store: when Dhruv sends a screenshot, a bug or a half-sentence of direction, it is
> written into PENDING §5 **before** any work starts — his words, verbatim. `PROGRESS.md` is the history and the detail.
> It is the living state of the project: done / in flight / next, the decisions log with reasons, the
> open questions, and every trap already paid for. It exists so a lost chat session costs nothing.
> The design lives in `index.html` + `docs/`. This file is how to *work* here.

---

## 1. Where everything is

```
clash-of-clans/                     ← this repo
├── CLAUDE.md                       ← you are here
├── PENDING.md                      ← THE QUEUE + every pointer Dhruv gives. If it disagrees with PROGRESS on what is pending, it wins.
├── PROGRESS.md                     ← LIVING STATE: done, decisions, gotchas, session log. read first, update last.
├── index.html                      ← design hub, opens the 13 docs
├── style.css
├── docs/01-concept … 13-demo.html
├── tools/                          ← u.sh (guarded Unity runner) · test.sh · export_all.sh
├── art/unit_sheet.png              ← the units, their pivots and their poses, rendered in Blender
├── blender/scripts/                ← AUTHORITATIVE pipeline scripts: export_palette · export_assets ·
│                                      rig_figure (skeleton + THE shared clip library) · export_figure (flat fallback) ·
│                                      export_nature · figure_sheet
├── blender/base/age1_demo/         ← models authored HERE (Rune Hall, Muster Hall, Farm)
├── blender/base/map_world/         ← THE WORLD MAP (Blender only, PENDING B12): 260 x 190 m, biomes + every resource, from the library
├── blender/base/map_ref/           ← THE MAP (Blender only, PENDING P0): build.py renders straight to renders/; QUALITY=final for the full render
├── blender/base/citizen/           ← THE CITIZEN and his four tools, authored HERE (the library's villager is retired from the game)
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
| `unity:audio-setup-mixers` | an AudioMixer with SFX / ambience / music groups — needed for the distance-and-zoom audio work (PENDING B3) |
| `unity:validate-urp-render-graph-renderer-feature` | before adding any renderer feature (the unit silhouette is one; fog of war will be another) |
| `unity:initialize-ai-navigation` | NavMesh problems — units stuck, bad bakes, obstacles |
| `unity:build-live-game` | save/progression, much later |

### Third-party skills and MCP servers — READ on 2026-09-21, none installed

Dhruv asked what exists online for animation and game design. These were read file by file, not just by their descriptions.
**Nothing below is installed.** A skill runs with Claude's permissions (this project often runs in bypass mode) and an MCP
server executes code inside the Editor — so read the `SKILL.md` and any scripts before installing anything, every time.

| What | Facts (2026-09-21) | Verdict for THIS project |
|---|---|---|
| [`CoplayDev/unity-mcp`](https://github.com/CoplayDev/unity-mcp) | MIT · 14k★ · active. Drives a **live, open** Editor. Tool groups: core, `animation` (Animator + AnimationClip creation), `vfx` (shaders, procedural textures), `testing`, `profiling` (profiler, memory, **Frame Debugger**), `docs`. | **Maybe later, for LOOKING, not authoring.** Two conflicts with how we work: (1) our scenes are *generated* — anything it edits in a scene is destroyed by the next `DemoSceneBuilder` run; (2) it needs the Editor open, and `tools/u.sh` launches its own Editor on the same project — one project, one Editor. Its real value here is `profiling`/Frame Debugger for open questions Q6 and Q8. |
| [`Besty0728/Unity-Skills`](https://github.com/Besty0728/Unity-Skills) | MIT · 1.8k★. 805 REST "skills" for the live Editor; built on unity-mcp's idea, adds dry-run, audit log, rollback. | **Skip** — same two conflicts as above; at most one of the two. |
| [`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp) | MIT · 29k★. Drives a live Blender through an add-on socket; pulls Poly Haven / Sketchfab assets. | **Skip.** Breaks Blender rule 1 (`build.py` is the source of truth — GUI edits are destroyed) and rule 2 (procedural only, nothing downloaded). Independent reviews say it is weak at rigging and exact dimensions — the two things `rig_figure.py` and the sidecar assertions get exactly right. |
| [`Donchitos/Claude-Code-Game-Studios`](https://github.com/Donchitos/Claude-Code-Game-Studios) | MIT · 25k★. 49 agents + 72 skills: a whole studio PROCESS (epics, sprints, gates, GDD folders). | **Do not install wholesale**: it expects its own folder layout, and its agents stop to ask "May I write this file?" before every change — the opposite of Dhruv's standing direction ("dont wait for me"). **Borrow three ideas** (below). |
| [`baxatron-git/claude-game-design-suite`](https://github.com/baxatron-git/claude-game-design-suite) | 14★ · **no licence** (read it, do not copy it). 22 design skills. | Its `game-balance-analyst` is the best single file found: dominant-strategy analysis, an option-viability matrix, matchup matrices ("no matchup worse than 30/70"), and *simulate 1000+ encounters*. We have a headless sim — we can actually do that. **Borrow the method.** |
| `agent-skills-hub` game-design | MIT · generic, 129 lines. | Skip — nothing we do not already do. |

**No skill anywhere writes procedural animation clips.** For that, our own `blender-procedural` skill + `rig_figure.py` (with `--sheet`
to look before Unity) is the tool, and it is better than anything found.

**Ideas borrowed (no install needed) — tracked in `PENDING.md`:**
1. **An SFX spec sheet per sound** (from the sound-designer agent): what it is, frequency character, duration, volume range, spatial
   behaviour, variations needed, concurrency limit, cooldown. Use it for the axe (B3) and then every sound in `Sfx.cs`.
2. **A playtest report template** (first five minutes · confusion points · moments of delight · bugs · pacing) for Dhruv's sessions.
3. **A matchup matrix from the headless sim**: run N battles for every unit pair and assert no pairing is worse than 30/70 and the
   counter triangle is circular. Today one test checks one triangle at one army size.

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
tools/test.sh                        # 13 headless sim tests. Batchmode is safe: no pixels.
tools/u.sh play DemoVerify.Full      # a bot plays the whole demo in the Editor: 8 screenshots, asserts, exits
tools/u.sh compile                   # ALWAYS before a GUI run -- a compile error in GUI mode hangs on a dialog

tools/export_all.sh [figures|buildings|new|nodes|all]   # re-export every Blender asset the demo uses

# palette -> 82 materials. --scan reads materials that live only inside an asset .blend
$BL -b --factory-startup --python blender/scripts/export_palette.py -- --out $P/Assets/Resources \
    --scan ~/blender/base/starter/models/node_food.blend ~/blender/base/starter/models/node_iron.blend \
           blender/base/citizen/models/{citizen,tool_axe,tool_pick,tool_hoe,tool_hammer}.blend

# LOOK at a figure and a clip before Unity: a tool in his hand, 3/4 view, chosen frames
$BL -b --factory-startup blender/base/citizen/models/citizen.blend --python blender/scripts/rig_figure.py -- \
    --name tmp --prefix citizen --with-clips --out /tmp/rig --attach blender/base/citizen/models/tool_axe.blend \
    --sheet /tmp/chop.png --turn 35 --shots "Chop:0,Chop:30,Chop:42,Chop:46"

# the land: unique meshes + instance matrices (axes MEASURED: Blender (x,y,z) -> Unity (-x,z,-y))
$BL -b --factory-startup ~/blender/base/map_village/map_village.blend \
    --python blender/scripts/export_nature.py -- --out $P/Assets/World

# verify the bridge  (NOT -batchmode, or the PNG is a single-material grey)
tools/u.sh gui SliceZero.Verify

# 4. quality settings for discrete GPUs
$UE -projectPath $P -executeMethod ConfigureQuality.Apply -logFile /tmp/q.log -quit

# 5. build (Mono backend: no Xcode licence needed) -> unity/ClashOfAges/Build/StandaloneOSX/ClashOfAges.app
tools/u.sh batch Builder.PerformMacBuild
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
**The units have real skeletons and share ONE clip library** (DL41, DL44, DL45): `blender/scripts/rig_figure.py` gives every figure the same canonical rest pose (limbs, shields and spears), so the 29 clips are authored once in `humanoid_clips.fbx` and the figure FBXs carry none. `FigureRigSetup` asserts each figure's bind pose against the library and builds one `humanoid.controller`; `RigAnimator.Style` picks the weapon-class clip set. Look at a clip before Unity with `--with-clips --sheet x.png --turn 55 --shots "Thrust:6"`. See `PROGRESS.md` §5b for the remaining ~51 clips.
