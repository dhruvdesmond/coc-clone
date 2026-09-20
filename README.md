# Clash of Ages

A medieval-to-modern real-time strategy game for **Windows and macOS**.

> You start with **one citizen** and a patch of ground in the Norse iron age.
> You finish with a **missile silo**. Everything in between — gathering, building,
> population, research, war — is the game.

Rise of Nations' age ladder, Clash of Clans' base-building intimacy. Built entirely from
**procedural Blender assets** in **Unity 6 (URP, 3D)**. Premium, single player vs AI, no timers.

| | |
|---|---|
| **Engine** | Unity 6000.0.83f1, URP 3D |
| **Art** | Blender 5.2.1 LTS, fully procedural — no downloaded models, no image textures |
| **Ages** | 6 — Settlement · Feudal · Gunpowder · Industrial · Modern · Atomic |
| **Resources** | 9, never more than 6 on screen (three are age-gated) |
| **Content** | 39 building types · 60 unit types · ~192 models planned, 35 built |
| **Targets** | Discrete GPUs only — RTX 3060 floor, Apple silicon MacBook Pro |

## Start here

| File | What it is |
|---|---|
| **[`PROGRESS.md`](PROGRESS.md)** | **The living state of the project.** Done / in flight / next, the decisions log *with reasons*, open questions, and every trap already paid for. Read it first. |
| [`CLAUDE.md`](CLAUDE.md) | How to work in this repo — skills to load, rules, commands, and two things that will bite you |
| [`index.html`](index.html) | The design hub. Opens the 11 design documents. |

## The design documents

`docs/` — concept · the six ages · economy · buildings and units · asset manifest ·
AI (game and workflow) · the Blender→Unity pipeline · the map · animation, VFX and sound ·
Unity architecture · lighting.

## State

**Slice 0 is done.** The Blender→Unity bridge is built and verified end to end on one asset —
9/9 assertions, reproducible:

```
scale       5.513 x 5.042 x 4.585 m, matching Blender exactly
draw calls  108 Blender objects -> 1 renderer, 6 submeshes
triangles   22,548 exact
materials   6/6 mapped from a 79-entry palette, 0 magenta, tone correction applied once
```

**Next: slice 1 — one citizen.** A citizen walks to a tree on a heightfield, chops, carries, drops
off, and the wood counter moves.

## Why the pipeline is the interesting part

**Procedural Blender materials cannot be exported.** Not to FBX, not to glTF — they arrive
untextured grey. So the mesh crosses with its material *slots named*, and
`lib/materials.py` is exported to `palette.json` which Unity reads to rebuild them. One authority,
so the Python and C# tables cannot drift apart. An unmapped material is magenta plus a console
error, never a silent grey.

```bash
BL=/Applications/Blender.app/Contents/MacOS/Blender
UE=/Applications/Unity/Hub/Editor/6000.0.83f1/Unity.app/Contents/MacOS/Unity
P=unity/ClashOfAges

$BL -b --factory-startup --python blender/scripts/export_palette.py -- --out $P/Assets/Resources
$BL -b --factory-startup ~/blender/base/huts/models/hut_a.blend \
    --python blender/scripts/export_assets.py -- --name hut_a --out $P/Assets/Models
$UE -projectPath $P -executeMethod SliceZero.Verify -logFile /tmp/slice0.log -quit
```

Run the verification **without** `-batchmode` — under batchmode Unity draws every mesh with one
material, and the resulting image is a single-material grey. That one cost a long detour.
