"""Export a lib/figure.py humanoid as a LIMB HIERARCHY for procedural animation in Unity.

    blender -b --factory-startup <figure>.blend --python blender/scripts/export_figure.py -- \
        --name villager --out <dir>

WHY NOT AN ARMATURE
    figure.py builds ~30 loose rigid boxes from a dict of joint positions. There is no armature,
    no skinning and no action anywhere in the library. But every part is rigid, and the joints
    are literal spheres in the mesh (Shoulder, Elbow, Hip, Knee) -- so the pivots are already in
    the data. Joining parts into ten limbs with their origins at those spheres gives Unity a
    transform hierarchy it can animate in code, with no FBX animation and no change to lib/.

HIERARCHY (Unity reads these names; FigureAnimator.cs depends on them)
    <name>
    └── Body                      pivot: pelvis (Belt centre)
        ├── Head                  pivot: Neck base
        ├── ArmL ── ForeL         pivots: Shoulderl, Elbowl      (+ anything held in the left hand)
        ├── ArmR ── ForeR         pivots: Shoulderr, Elbowr      (+ anything held in the right hand)
        ├── LegL ── ShinL         pivots: Hipl, Kneel
        └── LegR ── ShinR         pivots: Hipr, Kneer

ORIENTATION
    Figures are authored facing +X. Measured axis mapping is Blender (x,y,z) -> Unity (-x,z,-y),
    so the figure is turned to face Blender -Y, which lands as Unity +Z (forward). Exported with
    bake_space_transform=True so limb objects carry identity rotation and "swing" is plain local X.
"""
import bpy, sys, os, json, math, pathlib, re
from mathutils import Matrix, Vector

LIMBS = ["Body", "Head", "ArmL", "ForeL", "ArmR", "ForeR", "LegL", "ShinL", "LegR", "ShinR"]
PARENT = {"Head": "Body", "ArmL": "Body", "ArmR": "Body", "LegL": "Body", "LegR": "Body",
          "ForeL": "ArmL", "ForeR": "ArmR", "ShinL": "LegL", "ShinR": "LegR"}

# part-name (after the figure prefix) -> limb.  Anything unlisted is a prop and goes to the
# nearest hand, or to Body if it is not near either (cloak, quiver, mail skirt).
PART = {
    "Torso": "Body", "Chest": "Body", "Belt": "Body",
    "Head": "Head", "Neck": "Head", "Beard": "Head", "Hair": "Head", "Helm": "Head", "HelmNose": "Head",
    "Shoulderl": "ArmL", "UpperArml": "ArmL", "Elbowl": "ForeL", "Forearml": "ForeL", "Handl": "ForeL",
    "Shoulderr": "ArmR", "UpperArmr": "ArmR", "Elbowr": "ForeR", "Forearmr": "ForeR", "Handr": "ForeR",
    "Hipl": "LegL", "Thighl": "LegL", "Kneel": "ShinL", "Shinl": "ShinL", "Footl": "ShinL",
    "Hipr": "LegR", "Thighr": "LegR", "Kneer": "ShinR", "Shinr": "ShinR", "Footr": "ShinR",
}
PIVOT = {"Body": "Belt", "Head": "Neck", "ArmL": "Shoulderl", "ForeL": "Elbowl", "ArmR": "Shoulderr",
         "ForeR": "Elbowr", "LegL": "Hipl", "ShinL": "Kneel", "LegR": "Hipr", "ShinR": "Kneer"}


def _argv():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


def _opt(args, flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default


def centre(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(bb, Vector()) / 8.0


def main():
    args = _argv()
    name, out = _opt(args, "--name"), _opt(args, "--out")
    prefix = _opt(args, "--prefix", name)          # object-name prefix inside the .blend
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)

    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(prefix + "_")]
    if not meshes:
        print(f"[figure] ! no objects named {prefix}_*"); sys.exit(1)

    # unlinked objects cannot be selected, joined, or have modifiers evaluated
    coll = bpy.context.scene.collection
    for o in meshes:
        if o.name not in bpy.context.view_layer.objects:
            coll.objects.link(o)
    bpy.context.view_layer.update()
    for o in meshes:
        o.hide_set(False); o.hide_select = False

    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target="MESH")                       # apply modifiers
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ---- recentre on the ground-contact point and turn to face Blender -Y (= Unity +Z) ------
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    body = [o for o in meshes if o.name[len(prefix) + 1:] in ("Torso", "Belt")]
    ref = body or meshes
    cx = sum(centre(o).x for o in ref) / len(ref)
    cy = sum(centre(o).y for o in ref) / len(ref)
    zmin = min(p.z for p in pts)
    fix = Matrix.Rotation(math.radians(-90.0), 4, "Z") @ Matrix.Translation((-cx, -cy, -zmin))
    for o in meshes:
        o.data.transform(fix)
        o.data.update()
    bpy.context.view_layer.update()

    # ---- assign parts to limbs ----------------------------------------------------------
    part = {o: o.name[len(prefix) + 1:] for o in meshes}
    hands = {"ForeL": next((o for o in meshes if part[o] == "Handl"), None),
             "ForeR": next((o for o in meshes if part[o] == "Handr"), None)}
    groups = {l: [] for l in LIMBS}
    props = []

    # A held prop is several objects sharing a prefix ("sp_Shaft", "sp_Head"). It must move as
    # ONE thing: deciding per object put a spear's head on the body and its shaft in the hand.
    # Gear with no prop prefix (Quiver, QArrow*, Cloak) is worn, not held -> Body.
    held = {}
    for o in meshes:
        if part[o] not in PART and "_" in part[o]:
            held.setdefault(part[o].split("_")[0], []).append(o)
    held_limb = {}
    for key, objs in held.items():
        best, bd = "Body", 0.30                          # further than this from a hand -> Body
        for l, h in hands.items():
            if h is None:
                continue
            hc = centre(h)
            d = min(min((o.matrix_world @ Vector(c) - hc).length for c in o.bound_box) for o in objs)
            d = min(d, min((centre(o) - hc).length for o in objs))
            if d < bd:
                best, bd = l, d
        held_limb[key] = best

    for o in meshes:
        limb = PART.get(part[o])
        if limb is None:
            limb = held_limb.get(part[o].split("_")[0], "Body") if "_" in part[o] else "Body"
            props.append(f"{part[o]}->{limb}")
        groups[limb].append(o)

    missing = [l for l in LIMBS if not groups[l]]
    if missing:
        print(f"[figure] ! limbs with no parts: {missing}"); sys.exit(1)

    tris_before = 0
    for o in meshes:
        o.data.calc_loop_triangles(); tris_before += len(o.data.loop_triangles)

    # ---- pivots, then join each limb ------------------------------------------------------
    pivots = {}
    for l in LIMBS:
        p = next((o for o in groups[l] if part[o] == PIVOT[l]), None)
        if p is None:
            print(f"[figure] ! limb {l} has no pivot part {PIVOT[l]}"); sys.exit(1)
        c = centre(p)
        if l == "Head":                                   # pivot at the BASE of the neck
            c.z = min((p.matrix_world @ Vector(v)).z for v in p.bound_box)
        pivots[l] = c

    limb_obj = {}
    for l in LIMBS:
        bpy.ops.object.select_all(action="DESELECT")
        for o in groups[l]:
            o.select_set(True)
        bpy.context.view_layer.objects.active = groups[l][0]
        if len(groups[l]) > 1:
            bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active
        j.name = l
        j.data.name = f"{name}_{l}"
        j.data.transform(Matrix.Translation(-pivots[l]))   # vertices relative to the pivot
        j.matrix_world = Matrix.Translation(pivots[l])
        limb_obj[l] = j
    bpy.context.view_layer.update()

    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    limb_obj["Body"].parent = root
    for child, parent in PARENT.items():
        w = limb_obj[child].matrix_world.copy()
        limb_obj[child].parent = limb_obj[parent]
        limb_obj[child].matrix_world = w
    bpy.context.view_layer.update()

    tris = 0
    for o in limb_obj.values():
        o.data.calc_loop_triangles(); tris += len(o.data.loop_triangles)
    if tris != tris_before:
        print(f"[figure] ! triangles changed {tris_before} -> {tris}"); sys.exit(1)

    pts = [o.matrix_world @ Vector(v.co) for o in limb_obj.values() for v in o.data.vertices]
    dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 4) for i in range(3)]

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for o in limb_obj.values():
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    fbx = os.path.join(out, f"{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0,
        apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
        object_types={"MESH", "EMPTY"}, use_mesh_modifiers=True, mesh_smooth_type="FACE",
        bake_space_transform=True, bake_anim=False, add_leaf_bones=False, path_mode="STRIP")

    mats = sorted({s.name for o in limb_obj.values() for s in o.material_slots if s.name})
    meta = {
        "_comment": "GENERATED by blender/scripts/export_figure.py. Do not hand-edit.",
        "name": name, "kind": "figure", "limbs": LIMBS, "triangles": tris, "materials": mats,
        "dimensionsMetres": {"x": dims[0], "y": dims[1], "z": dims[2]},
        "toleranceFraction": 0.03,
        "facing": "Unity +Z", "pivot": "ground contact under the pelvis",
        "pivotsBlender": {l: [round(v, 4) for v in pivots[l]] for l in LIMBS},
    }
    with open(os.path.join(out, f"{name}.meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[figure] {name}: {len(meshes)} parts -> {len(LIMBS)} limbs, {tris} tris, "
          f"{dims[0]} x {dims[1]} x {dims[2]} m")
    print(f"[figure] props: {', '.join(props) if props else 'none'}")
    print(f"[figure] wrote {fbx} ({os.path.getsize(fbx)//1024} KB)")
    print("[figure] OK")


main()
