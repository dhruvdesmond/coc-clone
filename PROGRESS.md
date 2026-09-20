# Clash of Ages — PROGRESS

> **This is a RISE OF NATIONS clone.** Not Clash of Clans — that was an offhand remark early on and
> it is wrong. The folder and repo keep the `clash-of-clans` name for continuity; the *game* does not.
> If you are deciding anything, the reference is RoN: borders as colour, attrition, cities, rares,
> national powers, the Armageddon counter. See `docs/12-territory.html`.

> **This file is the state of the project. Read it first, update it last.**
>
> **If you are a new session and the chat history is gone: everything you need is here.**
> Read this file top to bottom, then open `index.html` for the design. Do not ask the user to
> re-explain the concept — it is in `docs/01-concept.html` and it is settled.
>
> **Rules for keeping this file:**
> - Move rows between **Done / In flight / Next / Backlog**. Never delete a row — move it.
> - Every decision goes in the **Decisions log** with its *reason*. A decision without a reason
>   gets re-litigated in three sessions' time.
> - Every trap discovered goes in **Gotchas**, immediately, while it still hurts.
> - Update before you finish, not when you remember.

**Last updated:** 2026-09-20 · **Corrected to a Rise of Nations clone** (doc 12 added, Q1 closed).
**SLICE 0 IS DONE.** Unity project created, the Blender to Unity
bridge built and verified end to end on one asset. 11 design documents.
---

## 1. What this is, in four lines

**A Rise of Nations clone** for **Windows and macOS**. Six ages, medieval Norse through to atomic.
You begin with **one citizen**; citizens gather and build; buildings make more citizens; Knowledge
accrues and buys the next age. Continuous 3D map, no grid. Built from **procedural Blender assets**
in **Unity 6000.0.83f1 / URP 3D**. Premium, single player vs AI, no timers, no purchases.

Working title only — the name does not matter yet.

---

## 2. Status board

| Area | State | Where |
|---|---|---|
| 📐 Design docs | ✅ **DONE** — 12 documents | `index.html` + `docs/` |
| 🗺️ Territory system | ⬜ **DESIGNED, NOT BUILT** — borders, attrition, cities, rares, nations, Armageddon | `docs/12-territory.html` |
| 💡 Lighting | ✅ **DECIDED** — realtime sun + APV, verified against Unity 6 docs | `docs/11-lighting.html` |
| 🎨 Asset library | 🟡 **35 of ~192 built** (inherited from the Norse/Vale work) | `~/blender/base/` |
| 🔧 Blender→Unity bridge | ✅ **DONE and VERIFIED** — 9/9 assertions pass on `hut_a` | `docs/07-pipeline.html` |
| 🎮 Unity project | 🟡 **CREATED** — URP 3D, Unity 6000.0.83f1, quality configured for discrete GPUs | `unity/ClashOfAges` |
| 🧠 Simulation | ⬜ **NOT STARTED** | `docs/10-tech.html` |
| 🗺️ Map generator | 🟡 **Exists for Norse village**, needs the archetype system | `~/blender/lib/mapgen.py` |
| 🤖 Opponent AI | ⬜ **DESIGNED, NOT BUILT** | `docs/06-ai.html` |
| 🎥 Camera | 🟡 **WRITTEN, UNTUNED** — `RTSCamera.cs`; scroll scale still unmeasured (Q5) | `unity/ClashOfAges/Assets/Game` |
| 🔊 Audio | ⬜ **NOT STARTED** | `docs/09-fx-audio.html` |

---

## 3. Done

| # | What | When | Notes |
|---|---|---|---|
| D1 | Project folder created at `/Users/dhruv/clash-of-clans/` | 2026-09-19 | `docs/`, `unity/`, `blender/`, `art/` |
| D2 | `index.html` hub + `style.css` | 2026-09-19 | Matches the game-ideas studio aesthetic |
| D3 | **10 design documents** — concept, ages, economy, roster, assets, AI, pipeline, map, FX, tech | 2026-09-19 | Each is a decision record, not a wish list |
| D4 | Web research: RTS AI architecture, flow fields, formations, DOTS-vs-MonoBehaviour, RoN age design | 2026-09-19 | Sources cited in docs 06 and 10 |
| D5 | Economy first-pass numbers, hand-checked against a 15-minute walkthrough | 2026-09-19 | Age II lands at ~15 min against a ~14 min target |
| D6 | **Deep-research pass** (111 agents): URP sun/shadows, APV, era moods, world scale, AA | 2026-09-20 | Lighting + scale verified. Camera **not** answered. Asset benchmarks found nothing. |
| D7 | `docs/11-lighting.html` written; docs 08 and 10 updated with findings and refutations | 2026-09-20 | |
| D8 | **`blender/scripts/export_palette.py`** — exports all 4 kits to `palette.json` | 2026-09-20 | **79 materials**, no fallbacks, no failed probes. One authority. |
| D9 | **`blender/scripts/export_assets.py`** — FBX export, joins per material, asserts counts | 2026-09-20 | `hut_a`: 108 objects → 1 renderer, 6 submeshes, 22,548 tris |
| D10 | **Unity project `unity/ClashOfAges`** — URP 3D, Input System, arm64 | 2026-09-20 | Product "Clash of Ages" |
| D11 | **`PaletteImporter.cs`** — rebuilds Blender materials in Unity, magenta + error on unmapped | 2026-09-20 | Tone `pow(v,0.62)` applied once, to every surface |
| D12 | **`SliceZero.cs`** — builds the scene, renders it, asserts 9 things | 2026-09-20 | **ALL PASS**, reproducible across runs |
| D13 | **`ConfigureQuality.cs`** — 4096 shadows, 4 cascades, MSAA off, HDR, SRP Batcher | 2026-09-20 | Targets discrete NVIDIA + Apple silicon MacBook Pro |
| D14 | **`RTSCamera.cs` + `ScrollProbe.cs` + `Builder.cs`** | 2026-09-20 | Camera written; ScrollProbe is the Q5 measurement harness |
| D15 | **`docs/12-territory.html`** — borders, attrition, cities, rares, 6 nations, Armageddon | 2026-09-20 | The correction to a Rise of Nations clone. Closes Q1. |
| — | **Inherited: 35 procedural Blender assets** | pre-existing | Norse kit, modern kit, 6 terrain tiles, 10 troops |
| — | **Inherited: `lib/mapgen.py` map assembly + asserting `review()`** | pre-existing | Biome-as-vertex-attribute, paths in wear channel |
| — | **Inherited: a proven Blender→Unity port** (Vale) | pre-existing | Terrain FBX + 4K baked biome + 17,834 instanced cover |

---

## 4. In flight

*Nothing is currently mid-build.* The design pass finished cleanly; no half-written code or
half-authored assets exist. A new session starts from a clean state.

---

## 5. Next — in this order, and the order matters

| # | Task | Why it is next | Blocked by |
|---|---|---|---|
| ~~N1~~ | ~~Slice 0 — the bridge~~ | ✅ **DONE 2026-09-20.** 9/9 assertions pass on `hut_a`. | — |
| ~~N2~~ | ~~`export_palette.py`~~ | ✅ **DONE.** 79 materials. | — |
| ~~N3~~ | ~~`export_assets.py`~~ | ✅ **DONE.** Object-count assertion + join-per-material. | — |
| **N3b** | **Territory grid + border rendering.** One byte per 1 m cell, recomputed on city change; one fullscreen pass to draw it. | The system everything else in doc 12 hangs off, and it is cheap — 410 KB at the largest map, a handful of recomputes per match. Do it before combat exists, not after. | — |
| **N4** | **Slice 1 — one citizen.** Heightfield terrain, a citizen walks to a tree, chops, carries, drops off, the wood counter moves. | The first verb of the core loop, and the first thing that is fun to look at. | N5 |
| N5 | Build the `citizen` model in Blender | Slice 1 needs it, and it does not exist yet | — (can run parallel to N1) |
| N6 | **Slice 2 — build and grow.** Hut placement, pop cap, train citizen #2, Age I economy runs unattended 10 min. | The loop closes | N4 |
| N7 | Age I remaining assets: `runehall`, `farm`, `palisade`, `longship`, `fishingboat`, 6 resource nodes | Makes Age I complete and playable | N1 |

---

## 6. Backlog

Everything in `docs/05-assets.html` waves 2–6 (~157 assets), slices 3–5 in `docs/10-tech.html`,
audio, UI, the campaign, the 35-second showcase render. Not scheduled. Do not start any of it
before slice 2 plays.

---

## 7. Decisions log

Never delete. If a decision is reversed, add a new row saying so and why.

| # | Decision | Reason |
|---|---|---|
| **DL1** | **Six ages, not eight** | Each age is a complete art set. Six is what this team can finish, and the arc from spear to warhead still lands. |
| **DL2** | **3D, not sprites** | The mobile Norse build used pre-rendered isometric sprites — correct there, wrong here. A PC RTS needs a rotating, zooming camera, which sprites cannot give. |
| **DL3** | **MonoBehaviour, not DOTS** | Our cap is 200 units, not 100,000. DOTS' real cost in 2026 is developer experience and debugging, and the scarce resource here is learning time. Escape hatch: the `Sim` assembly has no UnityEngine dependency, so it can be ported later without touching the rest. |
| **DL4** | **Fixed 20 Hz simulation, separated from presentation** | Headless-testable (sweep the economy with bots the way Merchants of War was swept), cheap, and makes save/replay a seed plus an order log. |
| **DL5** | **Knowledge is generated, never gathered** | From Rise of Nations. Makes advancing an age a decision made twenty minutes earlier, which is the strategic spine of the game. |
| **DL6** | **Buildings/units cross as mesh + named material slots; terrain crosses baked** | Procedural Blender materials cannot export. Buildings have simple flat palettes → rebuild in engine. Terrain's material reads a vertex attribute authored into the mesh — that is a painted map, and textures are what painted maps are for. |
| **DL7** | **Continuous map, no grid or hexes** | The world reads as a place, and `lib/mapgen.py` already produces exactly this. Cost: harder placement, pathing and collision — accepted. |
| **DL8** | **Left-click is selection only, never pan** | Carried from the Norse desktop-port notes. Binding pan to left-click breaks RTS muscle memory permanently. |
| **DL9** | **Fog of war applies to the AI at every difficulty** | An AI that sees through fog can only be out-statted, never outwitted, and every feint the player attempts silently fails. Difficulty comes from reaction time, scouting and micro instead. |
| **DL10** | **Uranium: only 2–3 deposits per map** | Converts the endgame from an economy race into a territorial fight over three points. One line in the map generator. |
| **DL11** | **No multiplayer at launch** | Netcode is a second project and would eat the art budget. The 20 Hz deterministic sim keeps lockstep possible later without a rewrite. |
| **DL12** | **This is a Rise of Nations clone. The folder name `clash-of-clans` is historical and stays.** | Dhruv's original brief was "a game like rise of nations from medieval times to modern times"; the Clash of Clans framing was a later offhand remark and was wrong. Renaming the folder and repo buys nothing and breaks links — the *design* is what had to change. |
| **DL13** | **4 buildings get all 6 age variants; everything else exists in 2–3 ages** | Literal "every building swaps every age" is 108 models. This is ~70 and nobody will notice the difference. |
| **DL14** | **One fully realtime directional sun. No Shadowmask for ground cover.** | Shadowmask requires a static GameObject; our ~18,000 cover instances are `DrawMeshInstancedIndirect` with no GameObjects, so they can never be shadowmasked under any configuration. Verified 3-0. |
| **DL15** | **Shadows Max Distance is driven by camera zoom height (18–90 m), never by map size** | URP stretches the shadow map over Max Distance, so pixel density depends on that distance alone; the 240/420/640 m map extents are irrelevant to it. Verified 3-0. Step it between discrete zoom bands — changing it at runtime pops. |
| **DL16** | **Adaptive Probe Volumes for indirect; six era moods driven by realtime sun colour/angle/fog, NOT APV Lighting Scenarios** | Scenario sharing and blending require identical probe counts and positions across bakes, and age advancement swaps every building mesh in place — which breaks exactly that. Verified 3-0. Also means no bake to invalidate. |
| **DL17** | **1 Unity unit = 1 metre; flow-field cells at 1 m** | Validated against Supreme Commander 2's shipped convention (1 cell = 1 m, 10×10 m sectors). Worst case 410 KB of cost field at 640 m — a non-issue. Verified 3-0. |
| **DL18** | **Build the plain shared flow field first. No portals, no tile caching, until a profile asks.** | Tiled/portal flow fields decouple planning from unit count, but at a 200-unit cap per-agent steering dominates and the full architecture is over-engineering. |
| **DL19** | **Start from SMAA or TAA, not MSAA** | MSAA is the *most* expensive AA in URP on desktop, cannot combine with TAA, and fixes geometric edges only — it will not fix grass shimmer without alpha-to-coverage. Overturns the intuitive choice for a game full of thin geometry. |
| **DL20** | **`Camera.Render()` is never used. Capture goes through `RenderPipeline.SubmitRenderRequest`.** | `Camera.Render()` is not supported under an SRP. It produces correct geometry and shadows and silently ignores materials. |
| **DL21** | **The SRP Batcher is disabled for scripted captures, and left ON for the player.** | It mis-binds per-draw constants during a render request: with it on the capture is dark and flat, with it off it is correct. Two runs differing by only that flag isolated it. |
| **DL22** | **Visual verification runs the Editor in GUI mode, never `-batchmode`.** | Under `-batchmode` every draw uses one material — a red control quad turned the whole scene red. Asset-level assertions are still valid in batchmode; only the image is not. |
| **DL23** | **`palette.json` is read with `File.ReadAllText`, never `Resources.Load`.** | `AssetPostprocessor` import order is not guaranteed. On a cold import the FBX was processed before palette.json existed as a TextAsset and every material came out magenta. |
| **DL24** | **Material remaps are cleared before reimport.** | Once an FBX stores a remap in its `.meta`, `OnAssignMaterialModel` is skipped entirely, so materials created during a failed import stay wrong forever. |
| **DL25** | **Modifiers are applied in Blender before counting and exporting.** | The exporter runs with `use_mesh_modifiers=True`, so `hut_a`s 95 bevels and 12 displaces reach Unity: 9,860 → 22,548 triangles. Counting before applying them puts a wrong number in the sidecar. |
| **DL26** | **Quality targets discrete GPUs only.** RTX 3060 floor, Apple silicon MacBook Pro (M4 Pro is the dev machine). | 4096 shadow maps, 4 cascades, HDR, SMAA, full post-processing. Integrated graphics are explicitly not a target. |
| **DL27** | **Borders are a core system: territory drawn as colour, and you can only build inside your own.** | The thing RoN is actually remembered for. Docs 01–11 had RoN's economy but a base-builder's map. Expansion becomes *found a city, wait for the border, then build* — visible to the opponent a minute before it is useful to you. |
| **DL28** | **Attrition: enemy units inside your borders lose 1.8 HP/s; yours regenerate at 1.0.** | This is what makes borders load-bearing rather than decorative, and it is why you cannot just mass an army and walk it into a capital. Supply wagons are the counter, which gives raiding cavalry a job in every age. |
| **DL29** | **Cities are the territory instrument, capped 2/3/5/7/9/12 by age, 60 m apart.** | Caps and spacing stop border-stacking and make each city a real decision. Capturing flips territory instantly; razing returns it to neutral. |
| **DL30** | **Six nations, not RoN's eighteen — chosen around the art we already have.** | Norse, Franks, Rus, Britons, Turks, Maurya. Four of the six unique units (berserker, lancer, horsearcher, war elephant) are already modelled, so six nations costs two new models. |
| **DL31** | **The Armageddon counter answers Q1.** Five detonations by anyone ends the world; every nation that ever launched loses, a non-nuclear survivor wins. | Better than anything I proposed. The warhead becomes a button that spends a shared, finite, irreversible resource — and the fifth press kills you too. Also makes the ABM site matter, since interception does not increment the counter. |

---

## 8. Open questions — need the user

| # | Question | Why it matters | Status |
|---|---|---|---|
| ~~Q1~~ | ~~Is launching a nuke a win button, or a loss condition disguised as one?~~ | ✅ **RESOLVED 2026-09-20 by DL31** — the RoN Armageddon counter. Five detonations end the world and everyone who launched loses. | ✅ Closed |
| **Q2** | Does the existing **Norse RTS** sprite project (`game-ideas/unity/NorseRTS`) get retired, or continue as a separate mobile track? | It shares the Blender asset library. If both live, asset changes must serve two pipelines. | ⬜ Open |
| **Q3** | Campaign, or skirmish-only at first? | A campaign is a large content commitment; skirmish + a good AI may be the better first release. | ⬜ Open |
| **Q4** | Target: Steam release, or a portfolio/learning project? | Changes how much polish, localisation and storefront work is scoped. | ⬜ Open |
| **Q5** | **What do `Mouse.current.scroll` deltas actually read on Windows vs a macOS trackpad in Unity 6?** | The "±120 on Windows" explanation was **refuted 0-3, twice**. Normalisation strategy is now unknown. **Blocks zoom-at-cursor.** Half-day measurement harness. | 🔴 Blocking N4 |
| **Q6** | Cascade count and split ratios for a fixed-50° camera at 18–90 m zoom? | Nothing published survived verification; Unity's worked example is at Cascade Count 1. Needs an in-editor pass at both zoom extremes. | ⬜ Open |
| **Q7** | Do era building swaps break APV probe subdivision? | Try baking subdivision against terrain and props only, excluding era buildings from the probe-influencing set. Fallback: one Baking Set per era, no blending. | ⬜ Open |
| **Q8** | What does a dressed 420 m map + 18,000 cover instances + 200 units actually cost at 1440p? | The 16.6 ms / 1,500 draw call / 6 M triangle budget is **our assumption, externally unvalidated**. Needs a synthetic stress scene **before** the art budget is committed. | ⬜ Open |
| **Q9** | Is there any published asset-count breakdown for a comparable indie RTS? | Research found **nothing**. The ~192-model plan and the four-buildings-get-six-variants compromise are untested assumptions about the single largest cost in the project. | ⬜ Open |

---

## 9. Gotchas — paid for already, do not re-learn

Every one of these cost real time on a previous project.

### Blender
- **`build.py` is the source of truth, not the `.blend`.** GUI edits are destroyed on the next build.
- **Read `matrix_basis`, not `matrix_world`,** on appended objects — the depsgraph never evaluates a
  hidden collection, and every part of a building collapses to one point.
- **Append once, instance with `obj.copy()`.** Three appends → six duplicate materials.
- **Assets carry authoring offsets.** Recentre on load or a hut places 11.77 m from where you asked.
- **Objects in a view-layer-excluded collection cannot be selected.** `select_set` reports nothing,
  an **empty FBX** is written, and no error appears anywhere. 2,510 objects vanished this way.
- **Split grouping keys at the first `_` *after* the `@`.** Otherwise `hut_a…hut_e` merge into one.
- **Biome must read `raw()`, not `height()`** — otherwise every building sits in a bare sand disc.
- **Previews are prefixed `preview_`.** A preview once overwrote a finished final render.
- **Never hash two Cycles renders to test for a regression.** GPU denoising is not bit-reproducible.
  Compare object counts and geometry.
- **Run `scripts/set_viewport_colors.py` after building** or the scene is grey in the GUI.
- **Do not raise sky strength to brighten sprites/renders** — it tints everything blue. Use a warm
  fill light.
- **Uniform scatter makes a hedge.** 864 evenly-placed trees formed an impassable wall. Use a
  low-frequency clump mask plus a keep-out radius.

### Blender → Unity
- **Procedural materials do not export.** Not FBX, not glTF. They arrive grey. Bake or rebuild.
- **The 3 mm grass bug.** Blender writes FBX in cm; Unity puts `0.01` on the mesh and **`100` on the
  prefab root**. Lifting `sharedMesh` onto a bare GameObject throws the 100 away.
- **Do not then compound it with `lossyScale`** — `lossyScale` already *is* the whole chain from the
  root. Applying both counts it twice: 10,000×, grass 236 m tall.
- **Apply `pow(v, 0.62)` tone correction to every surface or none.** These palettes are authored for
  Cycles with AgX. Half-applying it gave orange timber on mint grass.
- **One palette table, not two.** Seven Norse materials arrived unmapped because C# and Python each
  had their own table. Export the Python one to JSON; Unity reads that.
- **Triangles were never the problem — draw calls were.** A hall is 35 k tris and fine; it is 252
  objects and not fine. Join to one mesh per material at export.

### Unity
- **Anything importing `UnityEditor` goes in `Assets/Editor/`.** Mixing breaks player builds.
- **Generated scenes are regenerated every build.** Hand-edits are destroyed silently; the symptom is
  "my change did nothing". Change the generator.
- **ASTC is a mobile format.** Desktop needs a Standalone override — BC7/DXT5, larger max size.
- **Camera bounds and zoom must respond to aspect ratio.** A camera tuned for a fixed phone aspect
  shows the edge of the world at 21:9.

### Unity rendering and importing (all found on 2026-09-20 building slice 0)
- **`Camera.Render()` is not supported under an SRP.** It renders geometry and shadows correctly and
  **silently ignores materials**. Use `RenderPipeline.SubmitRenderRequest` with a
  `UniversalRenderPipeline.SingleCameraRequest`.
- **The SRP Batcher mis-binds per-draw constants during a scripted render request.** With it on, the
  capture is dark and flat; with it off, correct. Disable it around a capture only.
- **`-batchmode` renders every draw with ONE material.** A pure red control quad turned the entire
  scene red. Run the Editor in GUI mode for any visual check. Asset assertions remain valid in
  batchmode.
- **`AssetPostprocessor` import order is not guaranteed.** The FBX was processed before
  `palette.json` existed as a TextAsset, so `Resources.Load` returned null and everything came out
  magenta. Read generated data from disk with `File.ReadAllText`.
- **An FBX material remap in the `.meta` skips `OnAssignMaterialModel` entirely.** Materials created
  during a failed import stay wrong forever. Clear remaps with
  `GetExternalObjectMap()` + `RemoveRemap()` before reimporting.
- **Shadow bias lives on the `Light` component in URP 17**, not on `UniversalAdditionalLightData`.
  Set `usePipelineSettings = false` there, then `light.shadowBias` / `light.shadowNormalBias`.
- **A material made with `new Material()` and never saved as an asset leaks across renderers.**
  The red control material coloured the whole scene.

### This machine
- **`python3` is the Xcode Command Line Tools stub and is license-blocked** (exit 69,
  "You have not agreed to the Xcode license agreements"). Use `perl` for scripted edits. It also
  means **`sudo xcodebuild -license accept` is required before a macOS player build will work.**
- A `perl -0777 -pe` replacement that does not match **fails silently**. Always count and print the
  number of replacements applied, and assert it. A script that printed "patched" while changing
  nothing cost a full debug cycle here.

### Working method
- **A measurement rounded past the thing you are measuring is not evidence.** A log reading
  `bounds (0.00, 0.00, 0.00)` was read as "empty mesh" and used to *reverse a correct fix*. It was a
  3 mm mesh printed at two decimals. Print enough precision to separate the hypotheses, and include a
  count alongside any dimension.
- **Look at the render.** A build that completes is not a build that is correct.
- **One agent, one asset.** Agents given "build the Feudal age" produce eight mediocre models.

---

## 10. Where everything lives

```
/Users/dhruv/clash-of-clans/        ← THIS PROJECT
├── PROGRESS.md                     ← this file
├── index.html                      ← design hub
├── style.css
├── docs/01-concept … 10-tech.html  ← the ten design documents
├── blender/                        ← project-specific build scripts (empty)
├── unity/                          ← ClashOfAges project (not created yet)
└── art/                            ← references, renders (empty)

/Users/dhruv/blender/               ← THE ASSET LIBRARY (shared, pre-existing)
├── CLAUDE.md                       ← read before authoring anything
├── lib/                            ← nodeutils, meshkit, materials, norse, modern,
│                                      terrain, figure, mapgen, vegetation
├── scripts/                        ← render, review_map, export_map_layout, …
└── base/<family>/                  ← 35 assets across 11 families

/Users/dhruv/game-ideas/            ← the wider studio
├── CLAUDE.md                       ← studio-wide state board (§52 = the Vale port)
└── unity/NorseRTS/                 ← the mobile sprite build — see Q2
```

### Tools, confirmed working
| Tool | Version / path |
|---|---|
| Blender | 5.2.1 LTS · `/Applications/Blender.app` · Metal GPU |
| Unity | 6000.0.83f1 · `/Users/dhruv/.unity/bin/unity` · Personal licence active |
| Skills | `blender-procedural`, `procedural-map-assembly`, `unity:unity-cli`, `unity:unity-package-management` |

---

## 11. Session log

Append one block per session. Newest at the top.

### 2026-09-20 — Session 4: it is a RISE OF NATIONS clone, not Clash of Clans
Dhruv corrected the brief. His original words, at the very start, were "a game like rise of nations
from medieval times to modern times" — the Clash of Clans framing was a later offhand remark and I
built the docs around it. **Folder and repo keep the `clash-of-clans` name** at his instruction;
renaming buys nothing and breaks links.

**This was not a find-and-replace.** Only four literal "Clash of Clans" strings existed, and the
economy was already pure RoN — Knowledge generated not gathered, four research branches, three-gate
age advance, the catch-up discount. What was missing was RoN's *map*. Docs 01–11 described a game
where you build a base and fight over resource nodes. **In Rise of Nations you fight over the map
itself, and the map is coloured.**

`docs/12-territory.html` is the correction: **borders** projected from cities and painted on the
ground, **attrition** (enemies bleed 1.8 HP/s inside your nation, your own units regenerate),
**cities** as the capped territory instrument, **rare resources**, **six nations** chosen around the
art we already own, and the **Armageddon counter**.

**Q1 is closed.** It had been open since session 1: is a nuke a win button or a loss condition
disguised as one? RoN's own answer is better than anything I proposed — a shared counter where five
detonations end the world and *every nation that ever launched loses*, so a non-nuclear survivor
wins. The warhead becomes a button that spends a shared, finite, irreversible resource, and the fifth
press kills you too. It also makes the ABM site matter, because interception does not increment it.

**Four of the six nations' unique units already exist** (berserker, lancer, horsearcher, war
elephant), so six nations costs two new models rather than eighteen. The roster was chosen around the
art, deliberately.

### 2026-09-20 — Session 3: SLICE 0, and the bridge is real
Built and verified the whole Blender to Unity path on one asset.

**What exists now**
- `blender/scripts/export_palette.py` -> `palette.json`, **79 materials** across the 4 kits, probed
  straight off each Principled BSDF. No fallbacks, no failures. One authority, as DL6 required.
- `blender/scripts/export_assets.py` -> FBX + a `.meta.json` sidecar of expected dimensions and
  triangle count. `hut_a`: **108 objects joined to 1 renderer with 6 submeshes, 22,548 tris.**
- `unity/ClashOfAges` — URP 3D, Unity 6000.0.83f1, Input System, arm64.
- `PaletteImporter.cs`, `SliceZero.cs`, `ConfigureQuality.cs`, `RTSCamera.cs`, `ScrollProbe.cs`,
  `Builder.cs`.

**Slice 0 result: 9/9 assertions PASS, reproducible across runs.**
Scale 5.513 x 5.042 x 4.585 m against Blenders own measurement — **the 3 mm grass bug does not
happen here**. Triangles exact. 1 renderer. 6 submeshes. All 6 materials mapped, none magenta.
Tone correction confirmed present (Timber base R = 0.349, raw would be 0.183). And the render was
looked at: warm timber, mossy shingle roof, stone footings, correct shadows.

**Five failures on the way, all now in Gotchas §9.** The expensive one: the render came out flat
grey and I assumed the materials were wrong. They were not — asset-level reads showed correct
colours all along. A **pure red control quad** proved it in one run: red also rendered grey, so the
fault was the capture path, not the palette. *When a measurement disagrees with the thing it
measures, add a control before changing the thing.*

**One blocker for the user.** `sudo xcodebuild -license accept` has never been run on this machine.
It blocks macOS player builds (and it silently broke `python3` mid-session).

### 2026-09-20 — Session 2: deep research on the Unity side
- Ran a 111-agent deep-research pass on Unity 6 lighting, camera, world scale, graphics and asset-count
  benchmarks. **Coverage was uneven and the gaps matter more than the confirmations.**
- **Well answered:** URP sun/shadow setup and Adaptive Probe Volumes (Unity 6 manual, quoted verbatim,
  stable across 6000.0–6000.4), and world scale/pathfinding (first-hand Game AI Pro chapter by the
  engineer who shipped Supreme Commander 2's pathfinder). → new `docs/11-lighting.html`, DL14–DL18.
- **Barely answered:** the camera. The only source was one hobby repo targeting Cinemachine 2 on Unity
  2022.3, and the key cross-platform scroll claim was **refuted**. There is now *less* to go on than
  before — logged as Q5, and it blocks zoom-at-cursor.
- **Not answered at all:** shipped-RTS asset counts, per-asset authoring time, art direction, and
  per-setting frame cost. Every number in §5 of `docs/05-assets.html` remains an internal assumption.
- One genuinely useful overturn: **MSAA is the wrong default** for our thin geometry (DL19).
- **Nothing was built.** Still starts at N1, slice 0.

### 2026-09-19 — Session 1: the folder and the design pass
- Created `/Users/dhruv/clash-of-clans/`.
- Wrote `index.html`, `style.css` and **ten design documents**, grounded in web research on RTS AI
  architecture, flow-field pathfinding, formation systems, Unity DOTS-vs-MonoBehaviour at RTS scale,
  and Rise of Nations' age-advancement structure.
- Settled 13 decisions (§7) and hand-checked the economy to the 15-minute mark.
- Carried forward every gotcha from the Norse RTS and Vale projects into §9 rather than leaving them
  in a chat log.
- **Nothing was built.** No Unity project, no new assets. Next session starts at N1, slice 0.
