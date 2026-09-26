"""Give the library's horse (lib/figure.py horse(), the loose parts under <prefix>_*) a REAL skeleton and its own
clip library -- animation Tier 2 (PROGRESS §5b B), the mount every horseman, lancer and horse archer rides.

    blender -b --factory-startup ~/blender/base/troops/models/horseman.blend --python blender/scripts/rig_quadruped.py -- \
        --name horse --prefix horseman_h --with-clips --out /tmp/rig \
        --sheet /tmp/horse.png --turn 30 --shots "Idle:0,Walk:0,Walk:8,Gallop:4,Gallop:12,Rear:30,Death:33"

WHAT IT BUILDS
    * An ARMATURE of 20 bones: Root · Body · Chest · Rump · Saddle · Neck · Head · Tail · four legs x (Thigh, Shin, Hoof),
      named ThighFL, ShinFL, HoofFL … (F/H = fore/hind, L/R = the horse's left/right).
    * ONE skinned mesh, bound RIGIDLY (every part is a rigid box or blob -- one bone per vertex at weight 1.0), like the
      humanoid rig in rig_figure.py. Pivots are measured from the parts: a leg segment's top face is its joint, the neck's
      end nearest the chest is the neck's root, and so on. No hand-typed joint positions.
    * With --with-clips: Idle, Walk, Gallop, Rear, Death at 30 fps, every bone keyed every frame, exported ONCE as
      horse_clips.fbx. The rider is a humanoid and plays the humanoid library (RideIdle, Ride, AttackMounted, …); Unity
      parents his Root to this rig's Saddle bone, whose rest position is in the meta.json.

ANGLES (armature space, the same euler_q as rig_figure.py)
    X pitch: NEGATIVE swings a hanging leg FORWARD; on a horizontal bone (Body, Neck, Tail) negative lifts its far end
    (Body negative = the front rises = a rear).  Y yaw about up.  Z roll about forward (Body roll = the horse rolls over).
"""
import bpy, sys, os, json, math, pathlib, re
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_figure as EF                                                     # noqa: E402
import rig_figure as RF                                                        # noqa: E402  (euler_q, snap, wave, smooth, render_sheet)

FPS = RF.FPS
UP, DOWN, FORWARD = Vector((0, 0, 1)), Vector((0, 0, -1)), Vector((0, -1, 0))
LEGS = [f"{a}{b}" for a in "FH" for b in "LR"]                                  # FL FR HL HR
BONES = ["Body", "Chest", "Rump", "Saddle", "Neck", "Head", "Tail"] + [f"{k}{leg}" for leg in LEGS for k in ("Thigh", "Shin", "Hoof")]
PARENT = {"Chest": "Body", "Rump": "Body", "Saddle": "Body", "Neck": "Chest", "Head": "Neck", "Tail": "Rump"}
for leg in LEGS:
    PARENT[f"Thigh{leg}"] = "Chest" if leg[0] == "F" else "Rump"
    PARENT[f"Shin{leg}"] = f"Thigh{leg}"
    PARENT[f"Hoof{leg}"] = f"Shin{leg}"
LEVELS = [["Body"], ["Chest", "Rump", "Saddle"], ["Neck", "Tail"] + [f"Thigh{l}" for l in LEGS], ["Head"] + [f"Shin{l}" for l in LEGS], [f"Hoof{l}" for l in LEGS]]
# part name (after the prefix) -> bone. Legs are matched by regex below: FThigh1 -> ThighFL (s=1 is the authored +y side = the left).
PART = {"Barrel": "Body", "Chest": "Chest", "Barding": "Chest", "Rump": "Rump", "Neck": "Neck", "Head": "Head", "Cheek": "Head",
        "Bridle": "Head", "Tail": "Tail", "Blanket": "Saddle", "Saddle": "Saddle"}
LEG_RE = re.compile(r"^([FH])(Thigh|Shin|Hoof)(-?1)$")
WALK_SPEED, GALLOP_SPEED = 1.6, 7.5                                             # m/s the 32-frame walk and 16-frame gallop are authored for


# ====================================================================================== clips
wave, snap, smooth, lerp = RF.wave, RF.snap, RF.smooth, RF.lerp


def _leg(t, thigh, shin, hoof):
    """One leg through one stride, phase t in [0,1): back at t=0, swinging forward through t=0.5, the knee and fetlock
    folding while the hoof is in the air (the forward swing) and straight while it bears weight."""
    c, s = math.cos(2 * math.pi * t), max(0.0, math.sin(2 * math.pi * t))
    return (thigh * c, 0, 0), (shin * s, 0, 0), (hoof * s * 0.6, 0, 0)


def _legs(f, n, phases, thigh, shin, hoof):
    p = {}
    for leg, ph in phases.items():
        t = (f / n + ph) % 1.0
        p[f"Thigh{leg}"], p[f"Shin{leg}"], p[f"Hoof{leg}"] = _leg(t, thigh, shin, hoof)
    return p


def clip_idle(f, n):
    s, s2 = wave(f, n), wave(f, n * 0.5, 0.7)
    return ({"Body": (0.5 * s, 0, 0), "Neck": (2.0 * s - 3, 0, 0), "Head": (2.5 * wave(f, n, 1.1), 5 * wave(f, n, 2.0), 0),
             "Tail": (0, 14 * s2, 0), "ThighHL": (4, 0, 0), "ShinHL": (-8, 0, 0), "HoofHL": (12, 0, 0)}, 0.0)


def clip_walk(f, n):        # four-beat lateral walk: LH, LF, RH, RF
    s = wave(f, n * 0.5)
    p = _legs(f, n, {"HL": 0.0, "FL": 0.25, "HR": 0.5, "FR": 0.75}, 20, 34, 20)
    p.update({"Body": (1.5 * s, 0, 0), "Neck": (3 * wave(f, n * 0.5, 0.5) - 2, 0, 0), "Head": (3 * s, 0, 0), "Tail": (0, 6 * wave(f, n), 0)})
    return (p, 0.0)


def clip_gallop(f, n):      # fore pair and hind pair nearly together; the back arches and the neck reaches with the stride
    s, c = wave(f, n), math.cos(2 * math.pi * f / n)
    p = _legs(f, n, {"FL": 0.0, "FR": 0.12, "HL": 0.55, "HR": 0.65}, 42, 58, 28)
    p.update({"Body": (-7 * c, 0, 0), "Chest": (-4 * c, 0, 0), "Rump": (5 * c, 0, 0), "Neck": (-10 + 6 * s, 0, 0), "Head": (10 - 4 * s, 0, 0), "Tail": (-30, 0, 0)})
    return (p, 0.06 + 0.10 * max(0.0, s))


def clip_rear(f, n):        # up on the hind legs, forelegs tucked, held, then back down
    k = snap(f / FPS, [(0, 0), (0.35, 1), (0.85, 1), (1.30, 0)])
    return ({"Body": (-48 * k, 0, 0), "Chest": (-4 * k, 0, 0), "Neck": (-14 * k, 0, 0), "Head": (12 * k, 0, 0), "Tail": (-20 * k, 0, 0),
             "ThighFL": (-55 * k, 0, 0), "ShinFL": (85 * k, 0, 0), "HoofFL": (30 * k, 0, 0), "ThighFR": (-62 * k, 0, 0), "ShinFR": (80 * k, 0, 0), "HoofFR": (30 * k, 0, 0),
             "ThighHL": (18 * k, 0, 0), "ShinHL": (-28 * k, 0, 0), "ThighHR": (22 * k, 0, 0), "ShinHR": (-32 * k, 0, 0)}, 0.0)


def clip_death(f, n):       # the legs fold, then it goes over onto its left side
    k = min(1.0, (f / FPS) / 0.75); k *= k
    fold = min(1.0, k * 1.8)
    p = {"Body": (6 * fold, 0, -82 * k), "Neck": (18 * k, 0, 0), "Head": (14 * k, 10 * k, 0), "Tail": (10 * k, 0, 0)}
    for leg in LEGS:
        p[f"Thigh{leg}"] = ((-28 if leg[0] == "F" else 30) * fold, 0, 0); p[f"Shin{leg}"] = ((70 if leg[0] == "F" else -60) * fold, 0, 0)
    return (p, -0.30 * fold - 0.30 * k)


#         name      frames loop   fn           ground-lock
CLIPS = [("Idle",   72, True,  clip_idle,   True), ("Walk",   32, True,  clip_walk,   True), ("Gallop", 16, True,  clip_gallop, False),
         ("Rear",   45, False, clip_rear,   True), ("Death",  36, False, clip_death,  False)]


# ====================================================================================== maths
def world_rotations(pose):
    E = {b: RF.euler_q(*pose.get(b, (0, 0, 0))) for b in BONES}
    W = {"Body": E["Body"]}
    for lvl in LEVELS[1:]:
        for b in lvl:
            W[b] = W[PARENT[b]] @ E[b]
    return W


def end_point(o, toward):
    """Centre of the face of a rigid part that is nearest `toward` (a point): the joint of a tapered leg box."""
    axis = (centre(o) - toward).normalized()
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    proj = [(p - centre(o)).dot(axis) for p in pts]
    lo = min(proj)
    near = [p for p, d in zip(pts, proj) if d < lo + 0.03]
    return sum(near, Vector()) / len(near)


def centre(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(bb, Vector()) / 8.0


# ====================================================================================== main
def main():
    args = EF._argv()
    name, out = EF._opt(args, "--name", "horse"), EF._opt(args, "--out")
    prefix = EF._opt(args, "--prefix", "horseman_h")
    with_clips = "--with-clips" in args
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.fps = FPS

    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(prefix + "_")]
    if not meshes:
        print(f"[quad] ! no objects named {prefix}_*"); sys.exit(1)
    coll = bpy.context.scene.collection
    for o in meshes:
        if o.name not in bpy.context.view_layer.objects: coll.objects.link(o)
    bpy.context.view_layer.update()
    for o in meshes: o.hide_set(False); o.hide_select = False
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    import bmesh                                                              # inside-out boxes, as in export_figure.prepare
    flipped = 0
    for o in meshes:
        bm = bmesh.new(); bm.from_mesh(o.data); before = [f.normal.copy() for f in bm.faces]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); flipped += sum(1 for f, b in zip(bm.faces, before) if f.normal.dot(b) < 0)
        bm.to_mesh(o.data); bm.free(); o.data.update()
    print(f"[quad] normals: {flipped} inside-out faces turned outward")
    # recentre: hooves on the ground, the barrel's centre over the origin, turned to face Blender -Y (= Unity +Z). The facing is
    # MEASURED from head to rump -- the troops lineup rotates each mount, so a fixed turn faced the first horse away from the camera.
    part = {o: o.name[len(prefix) + 1:] for o in meshes}
    barrel = next(o for o in meshes if part[o] == "Barrel")
    fwd = centre(next(o for o in meshes if part[o] == "Head")) - centre(next(o for o in meshes if part[o] == "Rump")); fwd.z = 0
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    c = centre(barrel); zmin = min(p.z for p in pts)
    fix = Matrix.Rotation(math.radians(-90.0) - math.atan2(fwd.y, fwd.x), 4, "Z") @ Matrix.Translation((-c.x, -c.y, -zmin))
    print(f"[quad] authored facing {math.degrees(math.atan2(fwd.y, fwd.x)):.0f} deg -> turned to -Y")
    for o in meshes: o.data.transform(fix); o.data.update()
    bpy.context.view_layer.update()

    # ---- parts -> bones ----------------------------------------------------------------------------
    groups = {b: [] for b in BONES}
    for o in meshes:
        p = part[o]; m = LEG_RE.match(p)
        if m:
            bone = f"{m.group(2)}{m.group(1)}{'L' if m.group(3) == '1' else 'R'}"
        elif p in PART: bone = PART[p]
        elif p.startswith("Mane"): bone = "Neck"
        elif p.startswith("Ear"): bone = "Head"
        elif p.startswith("Stirrup"): bone = "Saddle"
        else: bone = "Body"; print(f"[quad] {p} -> Body (unlisted)")
        groups[bone].append(o)
    missing = [b for b in BONES if not groups[b]]
    if missing: print(f"[quad] ! bones with no parts: {missing}"); sys.exit(1)

    # ---- pivots and tips, measured -----------------------------------------------------------------
    one = {b: next((o for o in groups[b] if part[o] == k), None) for b, k in
           [("Body", "Barrel"), ("Chest", "Chest"), ("Rump", "Rump"), ("Saddle", "Saddle"), ("Neck", "Neck"), ("Head", "Head"), ("Tail", "Tail")]}
    for leg in LEGS:
        for k in ("Thigh", "Shin", "Hoof"):
            one[f"{k}{leg}"] = next(o for o in groups[f"{k}{leg}"] if LEG_RE.match(part[o]) and LEG_RE.match(part[o]).group(2) == k)
    head, tail = {}, {}
    head["Body"] = centre(one["Body"]); tail["Body"] = head["Body"] + FORWARD * 0.5
    head["Chest"] = centre(one["Chest"]); tail["Chest"] = head["Chest"] + FORWARD * 0.3
    head["Rump"] = centre(one["Rump"]); tail["Rump"] = head["Rump"] - FORWARD * 0.3
    head["Saddle"] = centre(one["Saddle"]) if one["Saddle"] else head["Body"] + UP * 0.35; tail["Saddle"] = head["Saddle"] + FORWARD * 0.25
    head["Neck"] = end_point(one["Neck"], head["Chest"]); tail["Neck"] = end_point(one["Neck"], head["Neck"] + (head["Neck"] - head["Chest"]) * 3)
    head["Head"] = end_point(one["Head"], tail["Neck"]); tail["Head"] = end_point(one["Head"], head["Head"] + (head["Head"] - tail["Neck"]) * 3)
    head["Tail"] = end_point(one["Tail"], head["Rump"]); tail["Tail"] = end_point(one["Tail"], head["Tail"] + (head["Tail"] - head["Rump"]) * 3)
    for leg in LEGS:
        for k in ("Thigh", "Shin", "Hoof"):
            o = one[f"{k}{leg}"]
            head[f"{k}{leg}"] = end_point(o, centre(o) + UP * 5); tail[f"{k}{leg}"] = end_point(o, centre(o) + DOWN * 5)

    # ---- skin ------------------------------------------------------------------------------------
    limb_obj = {}
    for b in BONES:
        bpy.ops.object.select_all(action="DESELECT")
        for o in groups[b]: o.select_set(True)
        bpy.context.view_layer.objects.active = groups[b][0]
        if len(groups[b]) > 1: bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = b; j.data.name = f"{name}_{b}"
        j.vertex_groups.new(name=b).add([v.index for v in j.data.vertices], 1.0, "REPLACE")
        limb_obj[b] = j
    bpy.ops.object.select_all(action="DESELECT")
    for o in limb_obj.values(): o.select_set(True)
    bpy.context.view_layer.objects.active = limb_obj["Body"]
    bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    mesh.name = name + "_mesh"; mesh.data.name = name + "_mesh"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    loose = [v.index for v in mesh.data.vertices if len(v.groups) != 1]
    if loose: print(f"[quad] ! {len(loose)} vertices are not bound to exactly one bone"); sys.exit(1)

    # ---- armature ----------------------------------------------------------------------------------
    arm_data = bpy.data.armatures.new(name + "_rig"); arm = bpy.data.objects.new("Rig", arm_data); coll.objects.link(arm)
    bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    root = eb.new("Root"); root.head = (0, 0, 0); root.tail = (0, -0.3, 0)
    for b in BONES:
        e = eb.new(b); e.head = head[b]; e.tail = tail[b]
        e.align_roll(FORWARD if (tail[b] - head[b]).normalized().dot(UP) < -0.5 else UP)     # legs: roll to forward; horizontal bones: roll to up
    for b in BONES:
        eb[b].parent = eb[PARENT[b]] if b in PARENT else eb["Root"]; eb[b].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.parent = arm; mesh.modifiers.new("Armature", "ARMATURE").object = arm
    bpy.context.view_layer.update()
    root_rest = arm_data.bones["Root"].matrix_local.copy()
    rest_rot = {b: arm_data.bones[b].matrix_local.to_3x3().to_4x4() for b in BONES}
    hoof_rest_z = min(tail[f"Hoof{l}"].z for l in LEGS)

    def apply_pose(pose, bob, ground):
        W = world_rotations(pose)
        P = {"Body": head["Body"].copy()}
        for lvl in LEVELS[1:]:
            for b in lvl: P[b] = P[PARENT[b]] + W[PARENT[b]] @ (head[b] - head[PARENT[b]])
        if ground:      # GROUND LOCK: the lowest hoof back where it rests
            low = min((P[f"Hoof{l}"] + W[f"Hoof{l}"] @ (tail[f"Hoof{l}"] - head[f"Hoof{l}"])).z for l in LEGS)
            bob += hoof_rest_z - low
        arm.pose.bones["Root"].matrix = Matrix.Translation((0, 0, bob)) @ root_rest
        bpy.context.view_layer.update()
        for b in P: P[b] = P[b] + Vector((0, 0, bob))
        for lvl in LEVELS:
            for b in lvl: arm.pose.bones[b].matrix = Matrix.Translation(P[b]) @ W[b].to_matrix().to_4x4() @ rest_rot[b]
            bpy.context.view_layer.update()

    report = []
    if with_clips:
        arm.animation_data_create()
        for clip, n, loop, fn, ground in CLIPS:
            act = bpy.data.actions.new(clip); act.use_fake_user = True; arm.animation_data.action = act
            prev = {}
            for f in range(n + 1):
                pose, bob = fn(0 if (loop and f == n) else f, n)
                apply_pose(pose, bob, ground)
                for b in BONES:
                    pb = arm.pose.bones[b]; q = pb.rotation_quaternion.copy()
                    if b in prev and prev[b].dot(q) < 0: q.negate(); pb.rotation_quaternion = q
                    prev[b] = q; pb.keyframe_insert("rotation_quaternion", frame=f)
                arm.pose.bones["Root"].keyframe_insert("location", frame=f)
            report.append((clip, n, loop))
        arm.animation_data.action = bpy.data.actions["Idle"]; scene.frame_start, scene.frame_end = 0, 72; scene.frame_set(0)

    # ---- export ------------------------------------------------------------------------------------
    mesh.data.calc_loop_triangles(); tris = len(mesh.data.loop_triangles)
    pts = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
    dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 4) for i in range(3)]
    bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = arm
    fbx = os.path.join(out, f"{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z", axis_up="Y", object_types={"ARMATURE", "MESH"}, use_mesh_modifiers=True, mesh_smooth_type="FACE",
        bake_space_transform=False, add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
        use_armature_deform_only=False, armature_nodetype="NULL", bake_anim=with_clips, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode="STRIP")
    meta = {"_comment": "GENERATED by blender/scripts/rig_quadruped.py. Do not hand-edit.",
            "name": name, "kind": "clips" if with_clips else "rig", "triangles": tris,
            "materials": sorted({s.name for s in mesh.material_slots if s.name}), "bones": ["Root"] + BONES, "fps": FPS,
            "walkSpeed": WALK_SPEED, "gallopSpeed": GALLOP_SPEED,
            "clips": [{"name": c, "frames": n, "seconds": round(n / FPS, 4), "loop": lp} for c, n, lp in report],
            "dimensionsMetres": {"x": dims[0], "y": dims[1], "z": dims[2]}, "toleranceFraction": 0.04,
            # rig space (Blender, metres): x right-to-left, -y forward, z up. Unity = (-x, z, -y). The rider's Root goes here,
            # parented to the Saddle bone, at rest.
            "saddle": [round(v, 4) for v in head["Saddle"]], "withersHeight": round(max(p.z for p in pts), 3),
            "facing": "Unity +Z", "pivot": "ground contact under the barrel"}
    with open(os.path.join(out, f"{name}.meta.json"), "w") as f: json.dump(meta, f, indent=2)

    sheet = EF._opt(args, "--sheet")
    if sheet and with_clips:
        shots = [(c, int(fr)) for c, fr in (s.split(":") for s in EF._opt(args, "--shots", "Idle:0").split(","))]
        RF.render_sheet(scene, arm, mesh, sheet, shots, float(EF._opt(args, "--turn", "0")), spacing=3.4)
    keep = EF._opt(args, "--save-blend")
    if keep: bpy.ops.wm.save_as_mainfile(filepath=keep)

    print(f"[quad] {name}: withers {meta['withersHeight']:.3f} m, saddle z {head['Saddle'].z:.3f} m, barrel z {head['Body'].z:.3f} m, "
          f"leg {(head['ThighFL'] - tail['HoofFL']).length:.3f} m")
    print(f"[quad] {name}: {len(meshes)} parts -> 1 skinned mesh, {tris} tris, {len(BONES) + 1} bones, {len(report)} clips, "
          f"{dims[0]} x {dims[1]} x {dims[2]} m")
    if report: print("[quad] clips: " + ", ".join(f"{c}({n}f{' loop' if lp else ''})" for c, n, lp in report))
    print(f"[quad] wrote {fbx} ({os.path.getsize(fbx) // 1024} KB)")
    print("[quad] OK")


if __name__ == "__main__":
    main()
