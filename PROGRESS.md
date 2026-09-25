# Clash of Ages — PROGRESS

> **This is a RISE OF NATIONS clone.** Not Clash of Clans — that was an offhand remark early on and
> it is wrong. The folder and repo keep the `clash-of-clans` name for continuity; the *game* does not.
> If you are deciding anything, the reference is RoN: borders as colour, attrition, cities, rares,
> national powers, the Armageddon counter. See `docs/12-territory.html`.

> **`PENDING.md` is the queue** — what is not done, in order, plus every pointer Dhruv gives (bugs seen while playing, reference
> screenshots, standing direction). This file is the history and the detail. If they disagree on what is pending, PENDING wins.

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

**Last updated:** 2026-09-20 · **THERE IS A PLAYABLE DEMO.** One citizen to the Feudal Age, with borders, raids and a
win screen; a bot plays it start to finish and wins. 10 headless sim tests. See `docs/13-demo.html`.
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
| 🗺️ Territory system | 🟡 **Borders, build-inside-only, attrition, regen BUILT.** Cities, rares, nations, Armageddon not yet. | `docs/12-territory.html` |
| 💡 Lighting | ✅ **DECIDED** — realtime sun + APV, verified against Unity 6 docs | `docs/11-lighting.html` |
| 🎨 Asset library | 🟡 **38 of ~192** — +Rune Hall, Muster Hall, Farm (authored in this repo) | `~/blender/base/`, `blender/base/age1_demo/` |
| 🔧 Blender→Unity bridge | ✅ **DONE and VERIFIED** — 9/9 assertions pass on `hut_a` | `docs/07-pipeline.html` |
| 🎮 Unity project | ✅ **PLAYABLE DEMO** — Age I → Feudal, generated scene, HUD, minimap, FX, synthesised audio | `unity/ClashOfAges`, `docs/13-demo.html` |
| 🧠 Simulation | ✅ **BUILT + TESTED** — `Assets/Sim`, no engine refs, 20 Hz, 10/10 EditMode tests | `docs/10-tech.html` |
| 🗺️ Map generator | 🟡 **Exists for Norse village**, needs the archetype system | `~/blender/lib/mapgen.py` |
| 🤖 Opponent AI | 🟡 **SCRIPTED `RaidDirector` only.** The three-layer utility AI of doc 06 is still unbuilt. | `docs/06-ai.html` |
| 🎥 Camera | 🟡 **WORKS; zoom feel untested by a human hand** — scroll is self-calibrating (Q5) | `Assets/Game/RTSCamera.cs` |
| 🏃 Animation | 🟡 **29 of ~80 clips · 1 of 13 rigs · 2 of 14 code-driven motions.** Tier 1 done: ONE shared clip library drives every humanoid (N12/N13 ✅). Full inventory in §5b | `blender/scripts/rig_figure.py` |
| 🔊 Audio | 🟡 **SYNTHESISED PLACEHOLDER** — every sound generated at startup; no audio files exist | `Assets/Game/Fx/Sfx.cs` |

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
| D16 | **The land in Unity** — terrain + baked 4K albedo, water, **19,727 GPU-instanced objects in 128 draw calls**, NavMesh | 2026-09-20 | `export_nature.py`, `InstancedWorld.cs`. Axis mapping MEASURED: Blender (x,y,z) → Unity (−x,z,−y) |
| D17 | **The simulation** — economy, construction, training, scholars, 4 techs, age advance, territory, attrition, combat, raids | 2026-09-20 | Pure C#. **10 EditMode tests.** One `Catalog.cs` table |
| D18 | **Rigged figures** — `rig_figure.py`: villager, swordsman, spearman, archer | 2026-09-20 | **11 bones, rigid skin, 8 clips each.** Asserted on import by `FigureRigSetup`. `art/rig_sheet_villager.png` |
| D19 | **Three new Norse models** — Rune Hall, Muster Hall, Farm | 2026-09-20 | `blender/base/age1_demo/build.py`, reads `~/blender/lib`, writes nothing there |
| D20 | **Play layer** — NavMesh movers, selection, orders, placement ghost, construction | 2026-09-20 | Left-click is selection only |
| D21 | **HUD** — resources, command panel + tooltips + hotkeys, objectives, toasts, banners, minimap, title/end cards | 2026-09-20 | uGUI built in code |
| D22 | **Borders drawn as colour** — custom shader on a 0.5 m terrain drape; eased so a border blooms | 2026-09-20 | The RoN signature. Line + faintest tint |
| D23 | **FX + synthesised audio + AgeDirector + occluded-unit silhouette** | 2026-09-20 | |
| D24 | **`DemoAutopilot`** — a bot plays the whole arc in the Editor, 8 screenshots, asserts, exits | 2026-09-20 | **Wins**: Feudal reached, final raid survived. The visual regression check |
| D25 | **Standalone macOS build** — `Builder.PerformMacBuild`, Mono backend, 161 MB | 2026-09-20 | Launches, loads 19,727 instances, runs clean. Mono sidesteps the Xcode-licence gate. **Windows build not attempted.** |
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
| ~~N3b~~ | ~~Territory grid + border rendering~~ ✅ DONE |  |  |
| ~~N4–N6~~ | ~~Slices 1 and 2, the citizen model~~ ✅ DONE — superseded by the demo |  |  |
| ~~N12~~ | ✅ **DONE 2026-09-20 (session 8).** ~~Canonical rest pose + ONE shared humanoid clip library.~~ See DL44. Normalise every figure to the same A-pose in `rig_figure.py`; author clips once into `humanoid_clips.fbx`. | Prerequisite for every clip after the first 8 — otherwise 43 clips × ~60 figures are baked separately. See §5b. | — |
| ~~N13~~ | ✅ **DONE 2026-09-20 (session 8).** ~~Tier 1 animation — the 20 clips that finish Age I.~~ 17 of the 20 are wired into the game; Idle2H/Attack2H/AttackSpin, Brace, BannerIdle/BannerWalk and Flee are in the library and asserted but **nothing plays them yet** — no axeman, no standard bearer, no brace or flee order exists. See DL45. Mine, Farm, Forage, Flee, Cheer, Run, HitReact, DeathFront, Block, Attack2, GuardIdle, 2H×3, Spear×3, AimIdle, Banner×2. | Spearmen currently thrust with the *sword* Attack; citizens mine and farm with the *chop*. | N12 |
| **N8** | **A human plays the demo.** Zoom feel on a real wheel and a real trackpad; is the first raid fair; is 15 minutes the right length. | Everything so far was verified by a bot and by screenshots. None of it has been *felt*. | — |
| **N9** | **The real opponent** — doc 06's utility Commander replacing `RaidDirector`. | The demo's enemy does not gather, build or decide. | N8 |
| **N10** | **Cities, rare resources, nations** — the rest of doc 12. | Borders exist; the things that make territory a *choice* do not. | — |
| ~~N11~~ | ~~A real rig~~ ✅ **DONE 2026-09-20** — `rig_figure.py`: armature, rigid skinning, 8 authored clips; Unity `Animator`. See DL41. |  |  |
| N7 | Age I remaining assets: `runehall`, `farm`, `palisade`, `longship`, `fishingboat`, 6 resource nodes | Makes Age I complete and playable | N1 |

---

## 5b. Pending — the animation inventory

**~80 authored clips (29 done, 51 to go) · 14 code-driven motions (2 done) · 13 rigs (1 done).**
Derived from the roster in `docs/04-roster.html`: 60 unit types, 39 building types, six ages.

**What keeps it at 79 and not 500:** clips are authored per **weapon class**, not per unit. Sixty unit types
collapse into about ten ways of holding something — an Age VI rifleman reuses the Age I citizen's Walk and
Death. And everything with wheels, wings or a hull is moved **in code**, not with clips (DL42).

### A. Humanoid — one skeleton for every person in all six ages: 44 clips (29 done → 15 to go)
| Class | Clips | n | Have |
|---|---|---|---|
| Shared (everyone) | Idle ✅ · Walk ✅ · Run ✅ · HitReact ✅ · DeathBack ✅ · DeathFront ✅ | 6 | 6 |
| Worker | Carry ✅ · Chop ✅ · Hammer ✅ · Mine ✅ · Farm ✅ · Forage ✅ · Flee ✅ · Cheer ✅ | 8 | 8 |
| Sword + shield | Attack ✅ · Attack2 ✅ · Block ✅ · GuardIdle ✅ · RunShield ✅ | 5 | 5 — *RunShield was not in the original count: the shared Run tips a shield face-up (found in the raid screenshot)* |
| Two-handed (axeman, berserker) | Idle2H ✅ · Attack2H ✅ · AttackSpin ✅ | 3 | 3 — *authored; no two-handed figure exists to play them* |
| Spear / pike | GuardSpear ✅ · Thrust ✅ · Brace ✅ | 3 | 3 |
| Bow / crossbow | Shoot ✅ · AimIdle ✅ · ReloadCrossbow | 3 | 2 |
| Firearm (Ages III–VI) | RifleIdle · RifleWalk · Aim · Fire · ReloadMuzzle · ReloadBolt · KneelFire · Bayonet | 8 | 0 |
| Thrown (grenadier) | Throw | 1 | 0 |
| Crew-served (MG, AT gun, artillery, missile team) | Load · FireBrace · Deploy · Operate | 4 | 0 |
| Support (standard bearer, monk, medic) | BannerIdle ✅ · BannerWalk ✅ · Heal | 3 | 2 — *authored; no standard bearer exists, and a banner pole will need its own canonical facing (upright), unlike a spear* |

### B. Creatures and riders: 19 clips (0 done)
| Rig | Clips | n |
|---|---|---|
| Rider (humanoid upper body on a mount) | RideIdle · Ride · AttackMelee · AttackLance · ShootMounted · DeathFall | 6 |
| Horse | Idle · Walk · Gallop · Rear · Death | 5 |
| War elephant | Idle · Walk · Attack · Death | 4 |
| Deer (the hunt resource) | Graze · Walk · Run · Death | 4 |

### C–F. Machines 8 · ships 3 · buildings 5 · sequences 1
| Group | Clips | n |
|---|---|---|
| Machines | Trebuchet Fire + Reload · Ram Swing · Cannon Fire, Limber, Unlimber *(one rig serves bombard, field gun, howitzer, AT gun)* · Rocket-truck Raise + Fire | 8 |
| Ships | Oars Row · Sail Unfurl · Sail Furl *(bobbing, rolling and sinking are code)* | 3 |
| Buildings | Gate Open/Close · Silo Open/Close · Derrick Pump | 5 |
| Sequences | the missile launch timeline (`docs/09-fx-audio.html`) | 1 |

### G. Code-driven motion, NOT clips: 14 systems (2 done)
Wheel spin · track scroll · suspension bob · turret traverse · barrel recoil · propeller/rotor spin ·
aircraft bank-and-pitch · ship/balloon bob-and-roll · ship sinking · radar/windmill rotation ·
banner/sail cloth sway · tree fall · building construction rise ✅ · building collapse ✅.
**This is why tanks, planes and destroyers cost zero authored clips.**

### H. Rigs to build: 13 (1 done)
Humanoid ✅ · horse · elephant · deer · trebuchet · ram · cannon family · rocket truck · oared hull ·
sailed hull · gate · silo · derrick.

### In build order
| Tier | Unlocks | Clips | Rigs |
|---|---|---|---|
| 0 — ✅ done | the demo | 8 | 1 |
| 1 — ✅ done (session 8), +1 unforeseen (RunShield) → 21 | Mine · Farm · Forage · Flee · Cheer · Run · HitReact · DeathFront · Block · Attack2 · GuardIdle · 2H×3 · Spear×3 · AimIdle · Banner×2 | **21** | 0 |
| 2 — Age II + mounts + water | rider 6 · horse 5 · elephant 4 · deer 4 · ReloadCrossbow · Heal · trebuchet 2 · ram 1 · gate 2 · oars + sails 3 | **29** | 8 |
| 3 — Gunpowder + Industrial | firearm 8 · Throw · crew 4 · cannon 3 | **16** | 1 |
| 4 — Modern + Atomic | rocket truck 2 · silo 2 · derrick 1 · missile sequence 1 — *plus 12 code-driven systems* | **6** | 3 |
| | | **80** | **13** |

### The one prerequisite — before Tier 1 (N12)  ✅ DONE — see DL44
**How it is built now.** `rig_figure.py` rotates each figure's geometry into ONE canonical rest pose (torso upright, limbs
plumb, bone roll pinned, shields facing forward, polearms at the trail). `tools/export_all.sh figures` exports
`humanoid_clips.fbx` (the rig + all clips, once) and four figure FBXs with **no clips**. `FigureRigSetup` copies the clips to
`Assets/Animation/Clips/*.anim` keeping only rotations + Root position, builds ONE `humanoid.controller`, and asserts every
figure's **bind pose** is within 0.5° of the library's (measured: 0.000° on all four). To add a clip: write a
`clip_*` function, add a row to `CLIPS`, re-export, map it in `RigAnimator.StateFor`. To LOOK at clips before Unity:
`--with-clips --sheet out.png --turn 55 --shots "Thrust:4,Thrust:6"` → see `art/clip_sheet_*.png`.

*The original statement of the problem:*
Today every figure FBX carries **its own copy** of the 8 clips, because poses are corrected per figure (the
figures are not authored neutral). At 43 humanoid clips × ~60 figures that is thousands of baked clips.
**Fix: normalise the REST pose in `blender/scripts/rig_figure.py`** — rotate each limb's mesh data to one
canonical A-pose when the rig is built. Every humanoid then shares one rest pose, so the 43 clips are authored
**once**, exported as `humanoid_clips.fbx`, and shared by every person in the game. Unity Generic clips bind
by bone path and the paths are already identical; the rigid bind makes the normalisation exact (DL43).

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
| **DL32** | **Demo movement is Unity NavMesh; the sim says where, the agent walks, the sim is told where the unit really is.** | 200-unit flow fields (DL18) are not needed for a 40-unit demo. `Assets/Sim` stays engine-free and headless-testable; pathfinding is replaceable without touching it. |
| **DL33** | **`Catalog.DemoEconomyScale = 1.4`, carry 20, citizens 4.2 m/s.** | docs/03's rates assume perfect play and no walking. MEASURED in the running game they gave about half the documented pace: citizens spent 29% of their time gathering and 45% walking. The design numbers are left alone and the gap is kept visible in one constant. |
| **DL34** | **Farms bank food where it grows — farmers do not carry.** | Rise of Nations does it this way, and it is what makes a farm worth its wood over a berry bush. See Q10 for whether *all* gathering should. |
| **DL35** | **Raiders target the army, towers, muster halls and the longhouse — not huts, farms or storehouses.** | They burned huts faster than they could be rebuilt, the population cap thrashed, and every run ended in a slow defeat that taught nothing. |
| **DL36** | **Figures are limb hierarchies posed in code, with ABSOLUTE poses.** | No armature exists anywhere in the library. Every part is rigid and the joints are literal spheres, so ten pivots reproduce what a rigid-bind rig would. Poses must be absolute because the figures are not authored neutral: additive angles sent the archer's bow arm straight up. |
| **DL39** | **Figures ship as FLAT limb meshes; the skeleton is assembled in Unity (`FigureAnimator.Awake`).** | FBX could not carry the hierarchy intact (see Gotchas). Flat root-level objects are the path slice 0 and `AxisProbe` already proved. |
| **DL40** | **Units are drawn 1.38× life size, their palette lifted ~45% in value, on a team-colour disc.** | At true scale a citizen is a dark speck from 30 m. Every RTS exaggerates its figures; buildings stay true scale and the sim is unaffected. |
| **DL41** | **Units have a REAL skeleton.** `rig_figure.py` builds an 11-bone armature from the figure's joint spheres, binds ONE skinned mesh rigidly (each vertex → one bone, weight 1.0), authors 8 clips at 30 fps, and exports the standard Blender-armature FBX. Unity imports a Generic rig; `FigureRigSetup` asserts it and generates an `AnimatorController`; `RigAnimator` drives it. | Dhruv asked for it, and it is strictly better: one SkinnedMeshRenderer instead of ten MeshRenderers, clips that can be viewed and edited in Blender, cross-fades between states, and `Animator` doing the work instead of per-frame C#. Rigid bind because every part of these figures IS rigid — nothing to paint, and it deforms exactly as the loose parts did. DL36/DL39 (limbs posed in code) remain as the fallback for any figure exported flat. |
| **DL42** | **Clips are authored per WEAPON CLASS, not per unit; anything with wheels, wings or a hull moves in code.** | 60 unit types are ~10 ways of holding something, so the humanoid needs 43 clips, not hundreds. Wheels, tracks, turrets, propellers, banking and bobbing are rotations and offsets — a clip would only be a worse copy of the maths. Whole-game total: ~79 clips (§5b). |
| **DL48** | **The citizen is authored in this repo (`blender/base/citizen/build.py`), chunky and in the player's blue; he holds NO tool in his mesh — axe, pick, hoe and hammer are separate grip-origin props parented to his `ForeR` bone, chosen by the job, and his hands are empty when he carries. Work clips share one beat (`_beat`) whose blow lands at the END of the loop.** | Dhruv's close-up: a wooden mannequin with a sledgehammer. Chunky because he is seen from 60 m (the 40-pixel render is the test); blue because team colour on a disc is not enough; separate tools because he farmed, mined and hauled with an axe welded to his hand. The blow lands at the end of the loop because that is when the sim fires its impact — sound and chips now coincide with the axe **without the sim or the sound code knowing anything about animation**. The hoe is mounted down the fist like a staff, not square to it like an axe: one mount does not suit every tool. No new bones: the hand is rigid with the forearm, so the soldiers' rigs were not touched. |
| **DL49** | **`export_figure.py` turns every part's faces outward before joining.** | `lib/figure.py`'s `seg()` winds every box **inside-out** — measured: 14 parts of the old villager, 100% of their faces; 1,000–1,800 faces per figure. Cycles is double-sided so Blender never showed it; Unity culls back faces, so **every figure in this game had been drawn as the inside of its own limbs since session 5**. `~/blender` is not ours to fix; the exporter is, and there each part is still one closed shell so "outward" is unambiguous. |
| **DL47** | **Water is one custom shader (`COA/Water`) built for a camera 18–90 m up: lapping shore foam, depth colour from the depth texture, crawling sun glitter, a ≤5 cm swell, and SOFTENED shadows. The swell is defined once, in `WaterSurface.cs`, pushed to the shader as globals and exposed as `HeightAt(x, z)`.** Water time is unscaled and its own. | From that height rolling waves are invisible; foam at the shoreline is what reads as alive, and it draws the waterline so a building can never again *look* as if it stands in the water. One wave definition, because boats will need to bob in phase with what is drawn (two tables of one fact is one too many). No opaque texture / refraction: a full-screen copy for an effect nobody can see from 60 m. |
| **DL46** | **A building's footprint is a turned RECTANGLE measured from its model, and every building in the world — the player's, the bot's, and the two halls and tower that setup spawns — is sited through the same two rules:** `Ground.FootprintProblem` (dry out to a 1.2 m shore margin; no steeper than ~10° across the floor) and `World.TreesOn` (any tree whose *canopy* reaches the walls is felled). `Catalog.half` is asserted against the Blender sidecar at scene build. | Dhruv found a house in a lake in his first ten minutes (PENDING B1). Three causes, all of the form "a rule existed but something went round it": footprints were circles and a 15.8 × 9.3 m longhouse does not fit in its own 7.5 m circle; trees were cleared by trunk distance, ignoring a 3 m canopy; and setup spawned buildings at coordinates nobody checked. The enemy camp search demanded 58 m and a flat 9 m circle, which nothing on a 104 × 84 m map satisfies, so **every game** it fell back to an unchecked mirror point 29 m from the player. It is now the farthest place a longhouse really fits (54.5 m). |
| **DL44** | **The canonical rest pose covers held PROPS, not just limbs — and the pelvis offset rides on `Root`.** Shields are found by shape (one thin axis, two wide) and turned to face forward with the arm hanging; polearms (> 1.4 m, one long axis) are laid level, point forward. Clips keep only bone rotations plus `Root`'s position; `RigAnimator` scales that offset by the figure's thigh length. | Measured, not assumed: the swordsman's shield was mounted 47° off and the spearman's 70° off, so one guard pose stood one shield up and laid the other flat like a table; the spear was 101° off and a thrust drove it into the turf. And an FBX bake keys position on every bone — 1,932 curves that would have stamped the citizen's limb lengths onto troops that are 16–23% bigger. `Root` rests at the origin on every figure, so it is the one bone whose position is portable. |
| **DL45** | **`UnitAnim.Clip` says what a unit is DOING; `RigAnimator.Style` (Worker / Sword / Spear / Bow) decides which authored clip that is.** Strikes are entered by the sim's Attack event and return to the style's guard stance; a Hit event plays HitReact, or Block half the time for shield bearers, and never interrupts the unit's own strike; soldiers closing on a target Run; idle units Cheer for ~5 s on an age advance; death picks Death or DeathFront at random. | It is DL42 in code: `UnitView` stays ignorant of weapons, and a new weapon class is one enum value and one row per verb. Swordsmen alternate Attack/Attack2 so two cuts in a row are not the same cut. |
| **DL43** | **One shared humanoid clip library, made possible by a canonical rest pose.** | Poses are currently corrected per figure because the figures are not authored neutral, which forces every FBX to carry its own clips. Normalising the rest pose once, at rig time, removes the reason — and rigid binding makes it exact. |
| **DL37** | **This repo never writes inside `~/blender`.** The repo's `blender/scripts/` is authoritative. | `~/blender` is not under version control and a live mobile session edits it; that session's rules make `lib/` and `scripts/` integrator-owned. New models live in `blender/base/` here and only READ `~/blender/lib`. |
| **DL38** | **Generated materials are synced from the palette in a separate pass; stray materials are scanned out of asset `.blend`s.** | Unity resolves an existing external material by name without calling `OnAssignMaterialModel`, so a material created magenta stays magenta forever. And `Berry`/`OreIron` lived only inside another scene's script. |

---

## 8. Open questions — need the user

| # | Question | Why it matters | Status |
|---|---|---|---|
| ~~Q1~~ | ~~Is launching a nuke a win button, or a loss condition disguised as one?~~ | ✅ **RESOLVED 2026-09-20 by DL31** — the RoN Armageddon counter. Five detonations end the world and everyone who launched loses. | ✅ Closed |
| **Q2** | Does the existing **Norse RTS** sprite project (`game-ideas/unity/NorseRTS`) get retired, or continue as a separate mobile track? | It shares the Blender asset library. If both live, asset changes must serve two pipelines. | ⬜ Open |
| **Q3** | Campaign, or skirmish-only at first? | A campaign is a large content commitment; skirmish + a good AI may be the better first release. | ⬜ Open |
| **Q4** | Target: Steam release, or a portfolio/learning project? | Changes how much polish, localisation and storefront work is scoped. | ⬜ Open |
| ~~Q5~~ | ~~Scroll deltas on Windows vs macOS trackpad~~ | 🟡 **Side-stepped, not answered.** `RTSCamera` is self-calibrating: the smallest non-zero \|Δ\| seen is one notch. No constant assumed. **Still needs a human hand on both devices** (N8). | 🟡 Mitigated |
| **Q6** | Cascade count and split ratios for a fixed-50° camera at 18–90 m zoom? | Nothing published survived verification; Unity's worked example is at Cascade Count 1. Needs an in-editor pass at both zoom extremes. | ⬜ Open |
| **Q7** | Do era building swaps break APV probe subdivision? | Try baking subdivision against terrain and props only, excluding era buildings from the probe-influencing set. Fallback: one Baking Set per era, no blending. | ⬜ Open |
| **Q8 (partly answered)** | Measured on the M4 Pro, Editor play mode at 1080p with the full village, 19,727 instances and ~30 units: **130–260 fps at 8× sim speed**, 128 instanced draw calls. No RTX measurement exists. The 16.6 ms budget is comfortably met here; the *art budget* question (6 M tris, 1,500 draw calls at 200 units) is still open. | 🟡 |
| **Q8** | What does a dressed 420 m map + 18,000 cover instances + 200 units actually cost at 1440p? | The 16.6 ms / 1,500 draw call / 6 M triangle budget is **our assumption, externally unvalidated**. Needs a synthetic stress scene **before** the art budget is committed. | ⬜ Open |
| **Q10** | **Should citizens carry at all?** Rise of Nations citizens gather in place; the resource simply ticks in. | The demo carries (readable, charming) except at farms (DL34). Carrying cost 45% of citizen time before tuning. RoN-faithful in-place gathering would remove walking from the economy entirely and make Storehouses pointless. | ⬜ Open |
| **Q9** | Is there any published asset-count breakdown for a comparable indie RTS? | Research found **nothing**. The ~192-model plan and the four-buildings-get-six-variants compromise are untested assumptions about the single largest cost in the project. | ⬜ Open |

---

## 9. Gotchas — paid for already, do not re-learn

Every one of these cost real time on a previous project.

### Sim / placement
- **In `SiteProblem`, ask the cheap questions first.** The ground test is dozens of terrain raycasts; building and resource overlap
  are a few subtractions. With the ground test first, a bot hunting for a hut site in a full town halved the frame rate.
- **`grep -c Exception` lies on a Unity log.** Every `Debug.Log` carries a call stack, and Unity's UI code has parameters of type
  `System.Exception&`. Count `^[A-Za-z.]*Exception:` instead.
- **A Unity `-batchmode -quit` can finish its work and then hang on exit** (seen once, 13 min, log ended "Cleanup mono"). It holds
  the project lock; the next run waits forever. `pkill -9 -f Unity.app/Contents/MacOS/Unity` and remove `Temp/UnityLockfile`.
- **A search that can fail needs a loud fallback.** `FindCampSite` returned a default when no candidate passed, and no candidate
  ever passed. Eight sessions of games were played 29 m from an enemy hall standing in a lake. Log the fallback as an ERROR.
- **When the bot loses after a rules change, read WHY it was refused before touching balance.** The first footprint rule was
  accidentally twice as strict on slope; the bot logged `Farm:Ground too steep x2175` per minute, hoarded 899 wood and lost.
  The per-minute `refused:` line in the autopilot log is permanent now.
- **The shore margin tests for WATER only.** Measuring slope out there too is what made the rule too strict.
- **A bot does not look.** It walked past a house in a lake for eight sessions. Anything a human would see at a glance and a bot
  would not needs an explicit assertion (`CheckFootprints`), and its first run found a second bug (the tower in the trees).

### Blender
- **A world Volume Scatter renders NIGHT.** The sun is attenuated over an infinite path. Haze is a bounded box over the map with
  the volume material; at a 55 m camera path, density 0.001 is a breath and 0.005 is milk.
- **`mapgen.AssetLibrary.load()` merges `Foo.001` into `Foo` and REMOVES it.** Any material of yours whose name a library kit
  already uses (LeafGold, Iron…) is created as `.001`, merged away, and every later reference dies with "StructRNA … has been
  removed". Prefix scene-local material names (`Ref…`).
- **A Cycles render cannot tell you a mesh is inside-out.** It is double-sided; Unity is not. If a figure looks hollow or see-through
  in Unity and perfect in Blender, measure face normals against each part's centre before anything else (DL49). A CONTROL found
  it in one run: the same test on the old villager failed the same way.
- **Tools are not all held alike.** An axe is square to the forearm; a hoe runs down from the fist. Check every tool in the hand on
  a contact sheet (`rig_figure.py --attach tool.blend --sheet ...`) — the hoe first stood upright in front of his face.
- **An FBX that carries animation imports its transforms POSED, not at bind.** The clip library "differed" from the villager it
  was built from by 88°. Compare rest poses from `sharedMesh.bindposes`, never from the prefab's transforms.
- **Judge a thrust from a ¾ view.** A spear pointed at the camera foreshortens to nothing and looks like it points at the floor
  (`rig_figure.py --turn 55`). Twenty minutes went on a pose that was already correct.
- **Held props are mounted differently on every figure.** Do not tune a pose to make one figure's shield look right; canonicalise
  the prop (DL44).
- **`tools/u.sh play … | tail` hangs for the whole watchdog period** — the watchdog's `sleep` inherits the pipe. Redirect to a file.
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

### Building the demo (2026-09-20) — each of these looked like something else
- **A skinned renderer's bounds are NOT the mesh's size.** Unity grows them to enclose every animation clip, so a
  swordsman with his sword overhead measures "2.18 m" and a correct rig fails a height check. Assert against
  `sharedMesh.bounds` (which stays in Blender's Z-up frame: height is `size.z`).
- **An ARMATURE survives Blender→Unity where a nested object hierarchy did not.** Same FBX exporter, opposite
  outcome — bones are the path every rigged character takes and both ends convert them consistently. Still
  asserted, never assumed: bone count, clip names, clip lengths, loop flags, mesh height.
- **Easing a border in from nothing flashes the whole nation** — every texel passes through the 0.5 "frontier"
  value at once. The first border must appear, not ease.
- **NEVER ship a nested hierarchy through FBX with `bake_space_transform=True`.** It arrived broken at the BIND
  pose: children rotated 90°, positions in a different axis convention from their parent. The citizen lay in
  pieces on the ground and I did not notice for hours, because every shot was from 30 m and my Blender sheet
  looked perfect (in Blender the limbs *are* identity). Dhruv noticed from a 170-pixel crop. **Export flat,
  root-level limbs and build the skeleton in Unity**, where pivots are identity by construction.
- **Look at the thing at the distance it fails.** A unit that is a dark speck from 30 m hides every rigging bug.
  The autopilot now opens with a close portrait of the citizen, standing and walking.
- **A depth-Greater silhouette pass needs a stencil mask**, or a unit's own arm (behind its own torso) outlines
  itself and every figure is covered in pale shards. Corpses must leave the layer or the ground outlines them.
- **The camera rig must pivot on real terrain height**, not y = 0. On 2–4 m terrain, close shots aimed below the
  surface and the subject slid to the top of the frame.
- **Path to a building's PERIMETER, never its centre.** The centre is inside the carved NavMesh obstacle; the
  destination snaps to the near edge, the agent measures "remaining" to *that* and stops, while the sim still
  sees it metres from the centre. Every citizen froze outside the longhouse. It looked like a slow economy.
- **Count workers EN ROUTE to a node, not just AT it.** Nine of twelve citizens walked to work forever, arriving
  at a full bush and retargeting to another full bush. It looked like bad balance.
- **Poses on these figures must be absolute.** They are not authored neutral. It looked like a wrong axis.
- **Ids are shared between units, buildings and nodes.** `id % 10 == 9` never happened, so the bot never
  assigned a miner: no metal, no army, defeat. It looked like raids being too strong.
- **MEASURE where time goes before tuning numbers.** Four bot/balance guesses failed; a per-state time histogram
  (`citizen time: Gathering 29% ToNode 26% ToDropOff 19%`) found the cause in one run.
- **A wait-loop that greps a log can match the PREVIOUS run's log.** Delete the log before launching.
- **In GUI mode a compile error opens a Safe Mode dialog and Unity never exits.** `tools/u.sh` compile-checks
  in batchmode first and puts a watchdog on every GUI run.
- **Never edit `Assets/` while an Editor run is live** — it can recompile mid-play.
- **Vale's `cover.json` is X-mirrored against its own terrain.** It used (x, z, −y); the measured mapping is
  (−x, z, −y). Tufts are symmetric so nobody saw it. Re-exported here with full matrices.
- **`RenderMeshInstanced` throws a bare NullReferenceException on a null material.** Guard and report at build.

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

### 2026-09-25 — Session 11c: "keep trying / show me" — trees and building detail
Spruces and autumn trees are now authored in this repo (`fir()`, `autumn()` in `map_ref/build.py`): 8–10 jagged tiers, dark
needles below and lit tips above, leaning trunks with limbs and 12–16 two-tone crown blobs. Bushes at the wood edge. Buildings:
weathered plaster (dirt rising from the ground), shutters, a brick-course chimney, the smithy's awning with anvil and barrels,
torches on poles, a campfire with flame tongues and a glow. Haze box (after a world volume rendered night). `art/map_ref_v3.png`.
Preview renders now take ~3 min (the crowns are ~1,200 icospheres); final ~6 min.

### 2026-09-25 — Session 11b: "are they the same?" — no; and "why not use our assets?" — done
Compared honestly: same layout, palette and light; not the same picture — no people, flat buildings, white sand, hay grass, no
props, no haze. Then the library went into the frame (`MG.AssetLibrary`, read-only): four citizens, six warriors including two
horsemen, the well, crates and fences, at 1.55× so they read at RTS scale as the reference does; tile courses on the red roofs, a
sigil on the banner, stripes and a door on the tent, cream sand with tufts thinning into it, finer grass. `art/map_ref_v2.png`.
**Still short of the reference:** buildings are clean boxes (no shutters, chimney bricks, worn paint); trees are low-poly cones and
blobs; no haze; the campfire is a stub. Those are the next passes if Dhruv wants this frame tighter before the vast map.

### 2026-09-25 — Session 11: the map, in Blender only — step 1, the reference frame (PENDING B9 / P0)
Dhruv: "create a map in blender first. forget about the game … this is the reference image … try to make it 100% the same …
then we will see how to improve it". Reference saved at last (`art/reference/northgard_camp.png`). Built `blender/base/map_ref/`:
its own ground material (ochre grass + green patches, sand / cobble / mud from a vertex attribute), its own Northgard-style
buildings (white plaster + timber frame + red tile; thatched pyramid hall with turret and banner; smithy with a stone furnace;
tent; campfire), the library's trees, rocks, mushrooms and grass, a camera matched to the reference (50° pitch, 40 mm).
Three preview iterations, each looked at against the reference: (1) overexposed, hall roof a flat disc, trees a hedge; (2) camera
too tight, sand invisible; (3) `art/map_ref_v1_preview.png` — composition, palette and light now match. What is still missing is
listed in PENDING P0. **Step 2, the vast biome/resource map, is not started.** Nothing in Unity changed.

### 2026-09-22 — Session 10: the citizen (PENDING B7/B8, DL48, DL49)
Dhruv, on a close-up: "our citizen — improve its design?" then "just the citizen and its animation. let's not do anything
related to the game." **New body** in this repo: chunky, blue tunic, red cap, a face, joints buried in the limbs. It passes the
40-pixel test (cap / tunic / boots still separate). **Tools** are props on his forearm bone — axe at trees, pick at rock, hoe on
the farm, hammer on a site, **empty hands under a log**. **Animation:** Chop is a woodsman's side swing; every work clip shares
one beat whose blow lands at the end of the loop, so the thock and the chips arrive with the axe (they were 0.5 s late) with no
change to sim or sound; a rebound replaces the frozen half-second; knees give at impact; a two-arm carry.
**The find of the session (DL49):** in Unity the new body looked hollow. Measured: the shared library winds every box part
inside-out, and the OLD villager failed the same test — every figure had been drawn as the inside of its own limbs since
session 5. Fixed in our exporter for all four figures at once (the one declared step outside "just the citizen").
Also his: the ghost over the carried log (load joined him in the silhouette pass) and the sunk feet (the NavMesh sits under the
terrain; he now stands on the terrain). **Verified:** rig assertions 0 failures, all four figures 0.000° from the shared rest
pose · 13/13 sim tests · full bot run PASS, won 20.6 min, 0 exceptions · looked at: portrait, chop landing, carry, farm, mine.
**Not done:** tools pop in and out with no draw/stow; soldiers keep their old thin bodies; one face and one cap for everyone;
the axe SOUND design (B3) still waits for its plan. **He has not seen it yet.**

### 2026-09-21 — Session 9b: water that moves; the axe reviewed; third-party skills read
**Water (DL47, PENDING B2).** The lake was a static near-black plane. Now `COA/Water`: pale turquoise shelf → deep blue centre,
a foam line that laps the shore, glitter, a small swell, soft shadows. The bot proves it moves in the real frame: two grabs
1.2 s apart, 52% of water samples change, **land control 0%**. Bot still wins (19.1 and 21.0 min), 14/14 footprints clean.
**Measured, not assumed:** fps was unchanged with the lake on screen; a late-game fps drop turned out to be the *bot* re-testing
30 hut sites a second with the raycast-heavy check first — reordered cheapest-first, bot search widened to 72 spots.
**Axe review (B4), nothing changed:** the sound lands ~0.5 s after the axe; overhead chop where a side swing belongs; a frozen
half-second after impact; static legs. **He asked for a plan for the axe sound (B3) before any code — not written yet.**
**Skills (B5/B6):** six third-party skill packs / MCP servers read file by file; none installed; verdicts and three borrowed ideas
in `CLAUDE.md` §2. Web-search limit raised to 1000 in `~/.claude/settings.json` (the deep-research run had spent the 200).

### 2026-09-21 — Session 9: Dhruv plays it; a house in a lake; PENDING.md
**First human play.** Within minutes: "house on lake.. and on trees also.." He also sent a Northgard screenshot — "how beautiful
it is" — and asked for a `PENDING.md` that stores every pointer. Created it first: the queue, 14 concrete visual pointers from
the reference (V1 ground pads and V2 soft light are the cheap, large ones), the bug list, his standing directions.
**The bug (DL46):** circular footprints, trunk-only tree clearing, and setup buildings sited at unchecked coordinates — the
house in the lake was the enemy's hall, put there every game by a camp search that could never succeed. Fixed with measured
rectangular footprints, one ground rule and one tree rule used by everyone, and an enemy camp that is now genuinely far
(29 m → 54.5 m). The bot now asserts every building at start and end; its first run found the enemy tower inside three trees.
My first version of the rule was too strict on slope and the bot lost (0 rune halls, 899 wood hoarded); the refusal tally showed
why in one run. **Verified:** 13/13 sim tests · `DemoVerify.Full` PASS, won at 19.3 min, 14/14 buildings clean, 0 exceptions.
**Changed for the player:** the enemy is farther away, so raids take longer to arrive — the bot lost 3 units instead of 8–9 and
faced 4 raids instead of 5. The demo is probably a little EASIER now; whether that is right is a question for Dhruv's next game.
**Not done:** the reference screenshots could not be saved (macOS temp folder is unreadable to Claude) — Dhruv needs to drop
them in `art/reference/`. None of the visual pointers are built yet (PENDING P2).

### 2026-09-20 — Session 8: one clip library, and Tier 1 (N12 + N13)
Dhruv: "do it." **29 clips now, authored once, played by every humanoid.** `rig_figure.py` canonicalises each figure's rest
pose — limbs, and (found the hard way, from the contact sheets) shields and spears too (DL44). `humanoid_clips.fbx` carries the
clips; the four figure FBXs carry none (125–148 KB each, was ~1 MB). Unity strips the 1,932 non-portable position/scale curves,
builds one controller, and asserts each figure's bind pose against the library: **0.000° on all four**. The 20 Tier 1 clips
are authored with a ground lock (no hand-tuned crouch offsets) and wired through weapon-class styles (DL45): citizens Mine /
Farm / Forage instead of chopping at everything, spearmen Thrust from a spear guard, swordsmen alternate two cuts and Block,
archers hold AimIdle, soldiers Run at the enemy (shield bearers with RunShield, added after the raid screenshot showed the shared Run laying shields flat), everyone flinches, and the settlement cheers the Feudal Age.
Verified: 10/10 sim tests · rig assertions 0 failures · `DemoVerify.Chop` PASS · `DemoVerify.Full` PASS twice — bot won at 19.3 and 19.5 min (28 kills, 8–9 lost, 5 raids, 0 exceptions), i.e. unchanged from before: the animation work did not touch the sim.
**Not done / honest limits:** 7 of the 29 clips have nothing to play them yet (2H×3, Brace, Banner×2, Flee). The citizen still
holds an axe while mining and farming — tool swapping is not built. Clips are still generated from pose functions, not
hand-animated. Still no human has played it (N8).

### 2026-09-20 — Session 7: how many animations the whole game needs
Dhruv asked for the count. **~79 authored clips (8 done), 14 code-driven motions (2 done), 13 rigs (1 done)** — the
full inventory is §5b. Two ideas keep it that small: clips per *weapon class* rather than per unit (60 units →
~10 classes → 43 humanoid clips), and code rather than clips for anything with wheels, wings or a hull. One
prerequisite surfaced while counting: each figure currently bakes its own copy of every clip, which does not
scale past the demo — a canonical rest pose fixes it (N12, DL43). Tier 1 is 20 clips and finishes Age I (N13).

### 2026-09-20 — Session 6: a real skeleton
Dhruv: "let's focus on the skeleton. how can we create it? let's do it." `blender/scripts/rig_figure.py` builds an
11-bone armature straight from the figure's joint spheres (the pivots were always in the data), joins the parts
into one mesh with a **rigid bind**, and authors eight clips — Idle, Walk, Carry, Chop, Hammer, Attack, Shoot,
Death — by sampling the pose functions at 30 fps and keying every bone on every frame (quaternions
sign-continuous, looping clips closed on their first frame). Poses stay absolute: each limb's rest direction is
corrected to "hanging down" first, so one clip means the same thing on the aiming archer and the idle citizen.

In Unity: Generic rig, clips renamed from `Rig|Walk` and loop-flagged by name at import, one generated
`AnimatorController` per figure (a state per clip, no transitions — the sim decides state; `Walk`/`Carry` speed
follows ground speed so feet do not skate), `RigAnimator` cross-fading and snapping attacks to frame 0.
`FigureRigSetup` asserts all of it; its first run FAILED two figures on height, and the failure was the check
(skinned bounds include animation) — measured, fixed, recorded. **All four rigs pass; the bot won again
(19.3 min), every unit on a skeleton.** `art/rig_sheet_villager.png` is the armature deforming the mesh.

### 2026-09-20 — Session 5: a playable demo, and a bot that wins it
Six phases, each committed: the land, the citizen, build-and-grow, borders and the age advance, something to
defend against, polish. **`tools/u.sh play DemoVerify.Full` now plays one citizen to the Feudal Age, survives the
final raid, wins, and leaves eight screenshots in `Verification/`.**

The sim was written first and tested headless, which paid immediately: the tests caught that trained units never
spawned (the cap check counted the reservation against itself) and that the counter triangle did not hold at ×1.5
(a swordsman beat a spearman 10.0 s to 10.4 s) before a single pixel existed.

Then the bot lost. Five times. Each loss looked like a balance problem and none of them were — see Gotchas. What
finally worked was not another guess but **instrumenting the autopilot**: a status line per sim-minute, per-unit
NavMesh diagnostics, and a histogram of where citizen time goes. *The rule from slice 0 held again: when a
measurement disagrees with the thing it measures, add a control before changing the thing.*

**Dhruv asked to see the units in Blender, and whether they have skeletons.** They do not, and the sheet
(`art/unit_sheet.png`) showed a real flaw while answering: additive poses on non-neutral figures. Fixed with
absolute poses and exported `_tip` markers. He also asked how construction time and multiple builders work — it
already worked (1×, 1.6×, 2.2×, 2.8×) and was invisible; it is in the tooltip and on the site readout now.

**Then Dhruv sent a 170-pixel crop: "THIS is the citizen?"** It was a dark blob in pale shards. Up close it was
worse — the figure lay scattered on the ground. Two bugs stacked: a silhouette pass with no stencil mask, and an
FBX hierarchy that arrived broken at the bind pose (`bake_space_transform`). I had verified the rig in *Blender*,
where it is fine, and the game from 30 m, where nothing shows. The fix — flat limbs, skeleton built in Unity,
1.38× scale, lifted palette, team disc, a camera that pivots on real terrain — is DL39/DL40, and the autopilot
now begins with the citizen's portrait. **Three consecutive bot wins since (17.8, 18.3, 20.6 min); citizens
now spend 50% of their time gathering, up from 29%.**

**What is faked is written down** in `docs/13-demo.html`: no skeleton, no Age II models, all audio synthesised,
the opponent scripted. **What has never been done: a human playing it.**

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
