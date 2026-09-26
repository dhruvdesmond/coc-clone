# How we build things in Blender — the handbook

Everything learned building Clash of Ages' art in Blender, in one place: how an asset is made, how a figure is rigged
and animated, how a map is assembled, how it reaches Unity, and every trap already paid for. Two copies exist on
purpose — `~/clash-of-clans/blender/HOW-WE-BUILD.md` (canonical, in git) and `~/blender/HOW-WE-BUILD.md` (the library).
**Edit the repo copy and copy it over.**

The technique lives in two skills we wrote (`~/.claude/skills/`): **`blender-procedural`** (authoring one asset) and
**`procedural-map-assembly`** (turning assets into a map). Load them before building. This file is the project's own
record: what exists, how it fits together, and what went wrong.

---

## 1. The two folders

```
~/blender/                      THE LIBRARY  (git: dhruvdesmond/blender-lib, private)
├── lib/                        shared code: nodeutils meshkit materials norse modern terrain figure mapgen vegetation
├── scripts/                    render · review_map · set_viewport_colors · export_* (older exporters)
├── base/<scene>/build.py       one folder per scene: build.py is the source of truth, the .blend is an artifact
│   └── models/<name>.blend     one asset per file, no camera or lights — what maps append
└── sprites/                    the mobile game's renders (not ours)

~/clash-of-clans/               THE GAME  (git: dhruvdesmond/coc-clone)
├── blender/scripts/            OUR pipeline: export_palette · export_assets · export_figure · rig_figure · export_nature
├── blender/base/age1_demo/     Rune Hall · Muster Hall · Farm
├── blender/base/citizen/       the citizen and his four tools
├── blender/base/map_ref/       the Northgard-reference frame (paused at v3)
├── blender/base/map_world/     THE WORLD MAP, 260 x 190 m
└── unity/ClashOfAges/Assets/Models, World, Resources   what the exporters write
```

**Rule:** the game imports `~/blender/lib` **read-only**, by absolute path. New models are authored in the game repo.
(Until 2026-09-26 the library was not under version control at all; it is now.)

## 2. One asset

1. `build.py` starts from `read_factory_settings(use_empty=True)` with a fixed `random.seed()`. Rebuild = delete + regenerate.
2. Geometry from `lib/meshkit.py` primitives (`bm_box`, `bm_cyl`, `beam_between`, `sweep`, `seg`, `blob`) and the era kit
   (`norse.py`: a parametric roof surface every part samples; `modern.py`: pad + panel box).
3. Materials from `materials.kit()` / `troop_kit()` / `terrain_kit()` — one palette per `.blend`. Procedural nodes only.
4. Author **centred on the origin, base at z = 0**, facing +X (figures) — maps recentre anyway, Unity does not.
5. `D.libraries.write(path, set(objects), fake_user=True, path_remap='NONE')` → `models/<name>.blend`.
6. Preview render (`RENDER_QUALITY=preview scripts/render.py`), **look at the PNG**, then final. Previews are prefixed
   `preview_` so they never overwrite a final.
7. `scripts/set_viewport_colors.py --save` or the GUI shows everything grey.

## 3. A figure: skeleton, skin, clips

`lib/figure.py` builds a humanoid as ~30 rigid boxes on a posed skeleton (`skeleton(H, pose)` → joints; `humanoid()` →
tapered segments). Nothing in the library has an armature. The game gives it one:

- `blender/scripts/export_figure.py` — `prepare()` joins the parts into ten limbs pivoting on the joint spheres
  (`PART`, `PIVOT`, `SEGMENT` tables are the contract: a part name must be in `PART`; `<prop>_<Piece>` is a held prop).
- `blender/scripts/rig_figure.py` — **one canonical rest pose for every humanoid**: torso upright, limbs plumb, bone roll
  pinned, shields turned to face forward, polearms laid level (found by shape, not name). Rigid skin (weight 1.0). Clips are
  pose functions sampled at 30 fps with a ground lock; the blow of every work clip lands at the END of the loop, because that
  is when the sim fires its impact. `humanoid_clips.fbx` carries all 29 clips once; figure FBXs carry none.
- Look before Unity: `rig_figure.py --with-clips --sheet out.png --turn 55 --shots "Chop:0,Chop:30,Chop:46" --attach tool.blend`.
- Tools are separate grip-origin props (`export_assets.py --keep-origin --recalc-normals`), parented to the `ForeR` bone in Unity.

## 4. A map

Pipeline (the `procedural-map-assembly` skill has the detail):
`assets → AssetLibrary (append once, instance many) → terrain (pads flattened BEFORE the mesh) → siting → placement →
dressing (clumped scatter) → review (numbers, then a top-down PLAN, then angles, then close-ups) → render`.

Three maps exist:

| map | where | what |
|---|---|---|
| `map_village` | `~/blender/base/map_village/` | 104 x 84 m, the Unity demo's land: 11 buildings, lake, 310 trees, tracks |
| `map_ref` | game repo | one frame imitating a Northgard screenshot — paused at v3: right layout, palette and light; the painted look is not a modelling problem |
| **`map_world`** | game repo | **260 x 190 m, six regions, every resource**, from the library — the direction from 2026-09-25 |

`map_world/build.py` is the pattern to copy for the next map: `region(x, y)` returns soft weights (mount, volcano, desert,
forest, sea, grass); `raw_h` sums a base fBm with a mountain ridge, a volcano cone with crater, dunes, a sea floor and a lake
basin; `biome(x, y)` is one index along a ramp (seabed → desert → steppe → grass → forest → rock → ash → snow) so neighbours
blend; roads are polylines with a kind (grass path / dirt / mud) written into the ground's colour attribute; `site()` searches
outward for **dry, flat** ground; scatter is capped and region-aware; resources are placed where you would look for them.

**Instancing (2026-09-26).** Every tree, bush and rock kind is built ONCE in `map_world/protos.py` -- pure bmesh, one joined
mesh per prototype with material slots, canopy blobs displaced by `mathutils.noise` instead of a Displace modifier + texture
per object -- and registered with `AssetLibrary.register()`; the scatter loops then `place()` copies (shared mesh). 36
prototypes, 526 trees + 300 rocks + 214 bushes placed in 10 s; the whole build 108 s where it was 6 min. The prototype
objects live in the hidden `_assets` collection; `lib.offset[key]` is zeroed because they are authored at the origin with
the base on z = 0 (rocks: centre on the origin, so a placement z of `height - 0.3` half-buries them as before). Names follow
what `export_nature.py` classifies: `tree{n}_…`, `rock{n}_…`, `Tuft_…`.

**The review is an assertion (`map_world/worldreview.py`).** Everything placed is recorded in `PLACED` (kind, x, y, objs); the
review checks each kind against `EXPECTED` (minimum count, allowed regions or water or dry ground), floating/sunken (buried,
for rock-like kinds), off-map and building/node overlaps, writes `renders/REVIEW.md` with a "since the last review" diff, and
the build **raises after the renders** so the batch rc is 1 while the pictures still exist to look at. First run found three
real faults the eye had missed: a fish shoal on the beach, berry bushes in the stable yard and on top of each other, the salt
flat outside the desert.

## 5. To Unity

- `export_palette.py` reads `lib/materials.py` + `--scan` of asset `.blend`s → `palette.json`. Unity applies `pow(v, 0.62)` once.
  Colours in build scripts are written *as they should look* and inverted with `look()`.
- `export_assets.py` (buildings, props), `rig_figure.py` (figures), `export_nature.py` (the land + instance matrices).
- Measured axis mapping: Blender (x, y, z) → Unity (−x, z, −y). Every FBX gets a `.meta.json.txt` sidecar Unity asserts against.
- `tools/export_all.sh [figures|buildings|new|nodes|all]` runs all of it.

## 6. Traps already paid for (do not re-learn)

**Geometry and export**
- `lib/figure.py`'s `seg()` winds every box **inside-out**. Cycles is double-sided so Blender never shows it; Unity culls back
  faces, so every figure was drawn as the inside of its own limbs for five sessions. `export_figure.py` turns normals outward.
- `bake_space_transform=True` on a nested FBX hierarchy arrives broken at bind pose. Flat objects or an armature; never that flag.
- Skinned-renderer bounds in Unity include the animation; assert against `sharedMesh.bounds`.
- An FBX that carries animation imports its transforms **posed**; compare rest poses from `bindposes`, not transforms.

**Materials and colour**
- A **byte colour attribute is sRGB-encoded**: write 0.42, read 0.15. Masks of 0/1 survive; a biome index does not. Use
  `bm.loops.layers.float_color`.
- `mapgen.AssetLibrary.load()` merges `Foo.001` into `Foo` and **removes** it — a scene-local material whose name a kit already
  uses (LeafGold, Iron…) dies with "StructRNA … has been removed". Prefix scene-local names.
- Materials with no users yet get purged by the same loader. `use_fake_user = True` until they are assigned.
- Procedural node materials do not survive FBX. Hence the palette JSON.

**Light and render**
- A **world Volume Scatter renders night** (the sun is attenuated over an infinite path). Haze is a bounded box over the map;
  at a 55 m camera path density 0.001 is a breath, 0.005 is milk.
- Wattages are physical: sun 2–4, sky 0.3–0.4, exposure −1 to −2 with AgX. The first map_ref render was blown out at −1.05.
- Judge a thrust or a lunge from a ¾ view (`--turn 55`); head-on, a spear foreshortens to nothing.

**Performance**
- `bpy.ops` object creation slows as the scene grows: 26k scatter tries made thousands of trees and the build ran 21 minutes
  without reaching the save. Cap counts (17k tries → 553 trees → ~6 min), `print(..., flush=True)`, and log to a file — a
  `| grep` pipeline buffers everything until the end.
- Instances (`obj.copy()`, shared mesh) are free; grass at 30k tufts is fine; 1,200 icosphere crowns are not.

**Process**
- The plan view finds what the hero shot hides: buildings in a lake, hedge-like scatter, dead space.
- A bot does not look. Anything a human would see at a glance needs an explicit assertion, and its first run usually finds a
  second bug.
- When a measurement disagrees with the thing it measures, add a control before changing the thing (the red quad; the old
  villager failing the same normals test).

## 7. Running it on the cloud (Vast.ai) -- done 2026-09-26

`tools/cloud/vast.sh` in the game repo: `up` rents a verified 1x RTX 4090 (3090 fallback, >= 16 cores, 80 GB disk), installs
Blender 5.2.1 Linux, clones BOTH repos with read-only deploy keys (`/work/repo`, `/work/blender-lib`); `batch <script>` runs a
build detached under nohup with `--python-exit-code 1`; `wait` polls it; `pull` brings renders back; `down` destroys; `cost start|end`
prints the credit and the session's spend (Dhruv's standing direction). Rules for the shared account are in the `vast-ai` skill:
our box is always `VAST_NAME=coa`, `down` only touches our own state file, another session's box is never a "stray".

What made the scripts portable: `BLENDER_LIB` (default `/Users/dhruv/blender`) replaces every hard-coded library path in this
repo, and `meshkit.render_settings` takes the Cycles device from `BLENDER_GPU` (METAL on macOS, OPTIX/CUDA elsewhere) and PRINTS
it -- the old `try/except` around `'METAL'` would have fallen back to the CPU in silence. Measured on the first 4090 box (driver
595): OptiX works; build 108 s + three previews = 161 s; the box costs $0.46/h including its disk.

What stays on the Mac: nothing in Blender. Unity's visual verification (`DemoVerify`, play mode + `ScreenCapture`) needs a GUI
editor on a real GPU display and a Vast container has none; the 13 sim tests, the compile check and the Windows build can run
headless there (`tools/cloud/unity-bootstrap.sh`).
