"""Export a built map's instanced content (ground cover, trees, rocks, logs) for Unity.

    blender -b --factory-startup <map>.blend --python blender/scripts/export_nature.py -- --out <dir>

READ-ONLY on the .blend: nothing is saved back. Structures and figures are skipped -- the
demo starts with one citizen on empty land; the flattened pads and worn paths stay in the
terrain and become natural building sites.

OUTPUTS
    world_meshes.fbx   every unique mesh datablock once, at identity, as object m_NNN
    world.bytes          instances + tree entities (format below)
    world.json         small facts: terrain size, sea level, counts

AXES -- MEASURED, NOT ASSUMED (Assets/Editor/AxisProbe.cs is the regression check)
    Through FBX (-Z forward, Y up) and Unity's importer, a Blender world point (x, y, z)
    lands in Unity at (-x, z, -y). An instance with Blender matrix M therefore renders in
    Unity with  C * M * C^-1  applied on top of the imported mesh child's own localToWorld.
    Vale's cover.json used (x, z, -y): X-mirrored against its own terrain. Not reused.

world.bytes (little-endian)
    char[4] "COAW" | u32 version=1 | u32 meshCount | u32 instanceCount | u32 entityCount
    instances: u16 mesh | u8 layer (0 cover 1 tree 2 rock 3 log) | i32 entity (-1 none)
               | f32[16] row-major Unity-space matrix
    entities : f32[3] base position (Unity) | f32 height | f32 radius | u8 kindLen | kind utf8
"""
import bpy, sys, os, json, struct, pathlib, re
from mathutils import Matrix, Vector

COVER = ("Tuft_", "flow", "mush")
LAYER = {"cover": 0, "tree": 1, "rock": 2, "log": 3}

C = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
C_INV = C.inverted()


def _argv():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


def classify(o):
    n = o.name
    if n.startswith(COVER):
        return "cover"
    if re.match(r"tree\d+_", n):
        return "tree"
    if re.match(r"rock\d+", n):
        return "rock"
    if re.match(r"log\d+_", n):
        return "log"
    return None


def main():
    args = _argv()
    out = args[args.index("--out") + 1]
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)

    scene_objs = set(bpy.context.scene.collection.all_objects)
    asset_coll = bpy.data.collections.get("_assets")
    asset_objs = set(asset_coll.all_objects) if asset_coll else set()

    picked = []
    for o in bpy.data.objects:
        if o.type != "MESH" or o in asset_objs:
            continue
        kind = classify(o)
        if kind:
            picked.append((o, kind))
    if not picked:
        print("[nature] ! nothing matched"); sys.exit(1)

    # ---- unique meshes ------------------------------------------------------
    mesh_index, reps = {}, []
    for o, _ in picked:
        if o.data.name not in mesh_index:
            mesh_index[o.data.name] = len(reps)
            reps.append(o)

    # Representatives are COPIES placed at identity and linked into the scene. An object
    # in an excluded collection cannot be selected, and the exporter then writes an
    # EMPTY FBX with no error -- 2,510 objects vanished that way once.
    coll = bpy.context.scene.collection
    bpy.ops.object.select_all(action="DESELECT")
    rep_objs = []
    for i, src in enumerate(reps):
        r = src.copy()
        r.name = f"m_{i:03d}"
        r.matrix_world = Matrix.Identity(4)
        r.parent = None
        coll.objects.link(r)
        rep_objs.append(r)
    bpy.context.view_layer.update()
    for r in rep_objs:
        r.hide_set(False); r.hide_select = False
        r.select_set(True)
    n_sel = sum(1 for r in rep_objs if r.select_get())
    if n_sel != len(rep_objs):
        print(f"[nature] ! only {n_sel}/{len(rep_objs)} representatives selectable"); sys.exit(1)

    fbx = os.path.join(out, "world_meshes.fbx")
    bpy.context.view_layer.objects.active = rep_objs[0]
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0,
        apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
        object_types={"MESH"}, use_mesh_modifiers=True, mesh_smooth_type="FACE",
        bake_space_transform=False, bake_anim=False, add_leaf_bones=False, path_mode="STRIP")

    # ---- tree entities --------------------------------------------------------
    trees = {}
    for o, kind in picked:
        if kind != "tree":
            continue
        key, species = o.name.split("_")[0], o.name.split("_")[1]
        trees.setdefault(key, {"kind": species, "parts": []})["parts"].append(o)

    entity_index, entities = {}, []
    for key in sorted(trees, key=lambda k: int(k[4:])):
        t = trees[key]
        trunk = next((p for p in t["parts"] if "Trunk" in p.name), t["parts"][0])
        base = trunk.matrix_basis.translation.copy()
        zs, rad = [], 0.0
        for p in t["parts"]:
            for c in p.bound_box:
                w = p.matrix_basis @ Vector(c)
                zs.append(w.z)
                rad = max(rad, ((w.x - base.x) ** 2 + (w.y - base.y) ** 2) ** 0.5)
        base.z = min(zs)
        entity_index[key] = len(entities)
        entities.append((C @ base, max(zs) - min(zs), rad, t["kind"]))

    # ---- write ------------------------------------------------------------------
    counts = {k: 0 for k in LAYER}
    with open(os.path.join(out, "world.bytes"), "wb") as f:
        f.write(b"COAW")
        f.write(struct.pack("<IIII", 1, len(reps), len(picked), len(entities)))
        for o, kind in picked:
            ent = entity_index[o.name.split("_")[0]] if kind == "tree" else -1
            # matrix_basis, not matrix_world: the depsgraph does not evaluate everything
            # in a batch-loaded file, and none of these objects is parented.
            m = C @ o.matrix_basis @ C_INV
            f.write(struct.pack("<HBi", mesh_index[o.data.name], LAYER[kind], ent))
            f.write(struct.pack("<16f", *[m[r][c] for r in range(4) for c in range(4)]))
            counts[kind] += 1
        for pos, h, rad, kind in entities:
            kb = kind.encode("utf8")
            f.write(struct.pack("<3fffB", pos.x, pos.y, pos.z, h, rad, len(kb)))
            f.write(kb)

    terrain = bpy.data.objects.get("Terrain") or bpy.data.objects.get("World_Terrain")
    sea = bpy.data.objects.get("Sea")
    facts = {
        "_comment": "GENERATED by blender/scripts/export_nature.py. Do not hand-edit.",
        "axes": "Blender (x,y,z) -> Unity (-x, z, -y), measured by AxisProbe",
        "terrainSizeMetres": [round(terrain.dimensions.x, 3), round(terrain.dimensions.y, 3)]
                             if terrain else None,
        "seaLevelY": round(sea.matrix_basis.translation.z + sea.dimensions.z * 0.5, 3)
                     if sea else None,
        "meshes": len(reps), "instances": counts, "trees": len(entities),
        "treeKinds": sorted({e[3] for e in entities}),
    }
    with open(os.path.join(out, "world.json"), "w") as f:
        json.dump(facts, f, indent=2)

    print(f"[nature] {len(reps)} unique meshes -> {fbx} ({os.path.getsize(fbx)//1024} KB)")
    print(f"[nature] instances {counts}  tree entities {len(entities)}")
    print(f"[nature] sea level y={facts['seaLevelY']}  terrain {facts['terrainSizeMetres']}")
    print("[nature] OK")


main()
