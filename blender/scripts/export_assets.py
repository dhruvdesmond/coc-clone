"""Export a model .blend to FBX for Unity, joined per material.

    blender -b --factory-startup <asset>.blend \
        --python scripts/export_assets.py -- --name hut_a --out <dir>

WHAT IT DOES
    1. Counts source objects and triangles.
    2. Joins every mesh into ONE object -- Unity then gets one MeshRenderer with N
       submeshes instead of N GameObjects. Triangles were never the problem; draw
       calls were. A hall is 35k tris and fine; it is 252 objects and not fine.
    3. Recentres on the ground-contact point (X/Y centre, Z minimum) so the asset
       sits on its world position instead of carrying an authoring offset.
    4. Asserts the triangle count survived the join, and FAILS LOUDLY if not.
    5. Writes <name>.fbx plus <name>.meta.json carrying the expected dimensions in
       METRES and the triangle count.

WHY THE SIDECAR
    Blender writes FBX in centimetres and Unity compensates with 0.01 on the mesh
    and 100 on the prefab root. Get that wrong and geometry arrives 1/100th size --
    the '3 mm grass' bug, which was then misdiagnosed because a log printed
    'bounds (0.00, 0.00, 0.00)' at two decimals. The importer compares real
    dimensions against this file and errors on a mismatch, so the bug cannot
    reach a build silently.
"""
import bpy, sys, os, json, pathlib

TOL = 0.02   # 2% dimension tolerance


def _argv():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


def _opt(args, flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default


def _tris(objs):
    n = 0
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        n += len(me.loop_triangles)
    return n


def main():
    args = _argv()
    name = _opt(args, "--name")
    out = _opt(args, "--out", "/Users/dhruv/blender/export")
    if not name:
        print("[asset] ! --name is required"); sys.exit(1)
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        print("[asset] ! no mesh objects in file"); sys.exit(1)

    src_objects = len(meshes)
    pre_tris = _tris(meshes)          # BEFORE modifiers -- not what gets exported
    src_mats = sorted({s.name for o in meshes for s in o.material_slots if s.name})
    nmods = sum(len(o.modifiers) for o in meshes)
    TOPO_MODS = sum(1 for o in meshes for md in o.modifiers
                    if md.type in {"BEVEL", "SUBSURF", "SOLIDIFY", "ARRAY", "MIRROR", "DECIMATE", "REMESH"})
    print(f"[asset] {name}: {src_objects} objects, {pre_tris} tris pre-modifier, "
          f"{nmods} modifiers, {len(src_mats)} materials")

    # --- make everything visible and selectable -------------------------------
    # Objects in a collection excluded from the view layer cannot be selected:
    # select_set() reports nothing and an EMPTY FBX is written with no error.
    # 2,510 objects vanished this way once.
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False

    # Asset .blends store objects that may not be linked into the scene at all.
    # An unlinked object is invisible to select_set() and to the FBX exporter.
    scene_coll = bpy.context.scene.collection
    linked_in = 0
    for o in meshes:
        if o.name not in bpy.context.view_layer.objects:
            scene_coll.objects.link(o)
            linked_in += 1
    if linked_in:
        print(f"[asset] linked {linked_in} unlinked object(s) into the scene")
    bpy.context.view_layer.update()

    for o in meshes:
        o.hide_set(False); o.hide_viewport = False; o.hide_select = False

    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    selected = [o for o in meshes if o.select_get()]
    if len(selected) != src_objects:
        print(f"[asset] ! only {len(selected)}/{src_objects} objects selectable "
              f"-- refusing to write a partial FBX")
        sys.exit(1)

    # --- apply modifiers -------------------------------------------------------
    # The FBX exporter runs with use_mesh_modifiers=True, so 95 bevels and 12
    # displaces DO reach Unity. Applying them here first means the triangle count in
    # the sidecar is the count Unity will actually import.
    #
    # Note the depsgraph will NOT evaluate modifiers on objects that are not linked
    # into the scene -- the same trap as stale matrix_world on appended objects. This
    # must run AFTER the linking step above, never before.
    bpy.context.view_layer.objects.active = selected[0]
    bpy.ops.object.convert(target="MESH")
    src_tris = _tris(meshes)
    # Only topology-changing modifiers must move the count; a Displace legitimately does not.
    if TOPO_MODS and src_tris == pre_tris:
        print(f"[asset] ! {nmods} modifiers present but the triangle count did not "
              "change -- they were probably not evaluated. Refusing to write a "
              "sidecar that will not match the FBX.")
        sys.exit(1)
    print(f"[asset] applied {nmods} modifiers: {pre_tris} -> {src_tris} tris")

    # --- join ------------------------------------------------------------------
    bpy.context.view_layer.objects.active = selected[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name

    out_tris = _tris([joined])
    if out_tris != src_tris:
        print(f"[asset] ! triangle count changed in join: {src_tris} -> {out_tris}")
        sys.exit(1)

    # --- props built with lib/figure.py's seg() arrive inside-out (see export_figure.py). Opt-in: a building's open planes
    #     (shingles, banners) have no "outward" and must not be touched.
    if "--recalc-normals" in args:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(joined.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(joined.data); bm.free(); joined.data.update()

    # --- recentre on the ground-contact point ---------------------------------
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bb = [joined.matrix_world @ __import__("mathutils").Vector(c)
          for c in joined.bound_box]
    xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
    cx, cy, zmin = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    if "--keep-origin" in args:          # a held PROP: its origin is the grip, and moving it to the ground would move the grip
        cx = cy = zmin = 0.0
    for v in joined.data.vertices:
        v.co.x -= cx; v.co.y -= cy; v.co.z -= zmin
    joined.location = (0, 0, 0)

    dims = (round(max(xs) - min(xs), 4),
            round(max(ys) - min(ys), 4),
            round(max(zs) - min(zs), 4))

    slots = [s.name for s in joined.material_slots if s.name]
    missing = [m for m in src_mats if m not in slots]
    if missing:
        print(f"[asset] ! material slots lost in join: {missing}")
        sys.exit(1)

    # --- export ----------------------------------------------------------------
    fbx = os.path.join(out, f"{name}.fbx")
    bpy.ops.object.select_all(action="DESELECT")
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    bpy.ops.export_scene.fbx(
        filepath=fbx,
        use_selection=True,
        apply_unit_scale=True,
        global_scale=1.0,
        apply_scale_options="FBX_SCALE_ALL",   # bake scale -> Unity reads metres
        axis_forward="-Z", axis_up="Y",        # Blender Z-up -> Unity Y-up
        object_types={"MESH"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        bake_space_transform=False,
        add_leaf_bones=False,
        path_mode="STRIP",
    )
    if not os.path.exists(fbx) or os.path.getsize(fbx) < 1024:
        print(f"[asset] ! FBX missing or suspiciously small: {fbx}")
        sys.exit(1)

    meta = {
        "_comment": "GENERATED by blender/scripts/export_assets.py. Unity's importer "
                    "asserts against these values; a mismatch means the scale or the "
                    "export is wrong. Do not hand-edit.",
        "name": name,
        "sourceObjects": src_objects,
        "trianglesPreModifier": pre_tris,
        "triangles": src_tris,
        "materials": slots,
        "dimensionsMetres": {"x": dims[0], "y": dims[1], "z": dims[2]},
        "toleranceFraction": TOL,
        "pivot": "ground-contact: X/Y centre, Z minimum",
    }
    with open(os.path.join(out, f"{name}.meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[asset] joined {src_objects} -> 1 object, {len(slots)} submeshes")
    print(f"[asset] dims  {dims[0]} x {dims[1]} x {dims[2]} m  (W x D x H in Blender Z-up)")
    print(f"[asset] mats  {', '.join(slots)}")
    print(f"[asset] wrote {fbx} ({os.path.getsize(fbx)//1024} KB)")
    print("[asset] OK")


main()
