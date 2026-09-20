"""Give a lib/figure.py humanoid a REAL skeleton: armature, skinning, authored clips -> one FBX for Unity.

    blender -b --factory-startup <figure>.blend --python blender/scripts/rig_figure.py -- \
        --name villager --out <dir> [--sheet <png>] [--save-blend <path>]

WHAT IT BUILDS
    * An ARMATURE of 12 bones -- Root, Body, Head, ArmL/ForeL, ArmR/ForeR, LegL/ShinL, LegR/ShinR --
      whose heads are the figure's joint spheres and whose tails are the far end of each segment.
    * ONE skinned mesh. Every part of these figures is a rigid box, so the bind is rigid: each vertex
      belongs to exactly one bone at weight 1.0. Nothing to paint, nothing to blend, and it deforms
      exactly as the separate parts did. One SkinnedMeshRenderer instead of ten MeshRenderers.
    * EIGHT ACTIONS at 30 fps, keyed on every frame: Idle, Walk, Carry, Chop, Hammer, Attack, Shoot,
      Death. Looping clips repeat their first frame as their last.

WHY THE POSES ARE ABSOLUTE
    The figures are not authored in a neutral stance -- the archer is already aiming, the swordsman has
    his shield up. So each limb's REST direction is measured (joint -> far end) and corrected to
    "hanging straight down", and the clip angles are applied on top of that. The same clip then means
    the same thing on every figure. Angles are in the convention the clips were first written in
    (X = pitch forward/back, Y = yaw about up, Z = roll about forward).

WHY THIS EXPORT PATH
    An earlier attempt shipped a nested OBJECT hierarchy with bake_space_transform=True and it arrived
    in Unity broken at the bind pose. An ARMATURE is different: it is the path every rigged character
    takes from Blender to Unity, and bone transforms are converted consistently by both ends. It is
    still VERIFIED, not assumed -- FigureRigSetup in Unity asserts bone count, clip list and height.
"""
import bpy, sys, os, json, math, pathlib
from mathutils import Matrix, Vector, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_figure as EF                                                     # noqa: E402

FPS = 30
LIMBS = EF.LIMBS
PARENT = dict(EF.PARENT)                         # limb -> parent limb
CORR_PARENT = {"ForeL": "ArmL", "ForeR": "ArmR", "ShinL": "LegL", "ShinR": "LegR"}
DOWN = Vector((0, 0, -1))
WALK_SPEED = 3.34                                # m/s the Walk/Carry cycle is authored for (24 frames)


# ------------------------------------------------------------------------------ clips
def lerp(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))
def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def clip_idle(f, n):
    s = math.sin(2 * math.pi * f / n)
    return {"Body": (s * 1.2, 0, 0), "Head": (s * -1.5, math.sin(2 * math.pi * f / n + 1.0) * 9, 0),
            "ArmL": (-6 + s * 2, 0, -8), "ForeL": (-22, 0, 0), "ArmR": (-6 - s * 2, 0, 8), "ForeR": (-26, 0, 0),
            "LegL": (-5, 0, -3), "ShinL": (6, 0, 0), "LegR": (6, 0, 3), "ShinR": (3, 0, 0)}, 0.0


def _stride(f, n, carry):
    ph = 2 * math.pi * f / n
    s, c = math.sin(ph), math.cos(ph)
    st = 25.0
    p = {"LegL": (s * st, 0, 0), "LegR": (-s * st, 0, 0),
         "ShinL": (max(0.0, -c) * st * 1.25, 0, 0), "ShinR": (max(0.0, c) * st * 1.25, 0, 0),
         "Body": (5, s * 3.5, 0), "Head": (-3, 0, 0)}
    if carry:
        p.update({"ArmL": (-58, 0, 0), "ForeL": (-48, 0, 0), "ArmR": (-58, 0, 0), "ForeR": (-48, 0, 0)})
    else:   # the tool arm swings less: it is carrying something
        p.update({"ArmL": (-s * st * 0.8, 0, -6), "ForeL": (-20, 0, 0), "ArmR": (s * st * 0.45, 0, 6), "ForeR": (-32, 0, 0)})
    return p, abs(c) * 0.035


def clip_walk(f, n): return _stride(f, n, False)
def clip_carry(f, n): return _stride(f, n, True)


def _work(f, n):
    """Slow raise, a SNAP down with no easing, a short rest. Violence does not ease (docs/09)."""
    u = (f % n) / n
    raise_ = smooth(u / 0.62) if u < 0.62 else (1 - (u - 0.62) / 0.08 if u < 0.70 else 0.0)
    return {"ArmR": (lerp(-35, -150, raise_), 0, 0), "ForeR": (lerp(-25, -70, raise_), 0, 0),
            "ArmL": (lerp(-30, -95, raise_), 0, 0), "ForeL": (-40, 0, 0),
            "Body": (lerp(16, -10, raise_), lerp(6, -12, raise_), 0), "Head": (lerp(8, -12, raise_), 0, 0),
            "LegL": (-8, 0, 0), "LegR": (10, 0, 0), "ShinL": (8, 0, 0), "ShinR": (6, 0, 0)}, 0.0


def clip_chop(f, n): return _work(f, n)
def clip_hammer(f, n): return _work(f, n)


def clip_attack(f, n):
    a = f / FPS                                   # anticipation (3 frames back), SNAP, recover
    arm = lerp(-40, -155, a / 0.10) if a < 0.10 else lerp(-155, 25, (a - 0.10) / 0.06) if a < 0.16 else lerp(25, -40, (a - 0.16) / 0.45)
    tw = lerp(0, -28, a / 0.10) if a < 0.10 else lerp(-28, 30, (a - 0.10) / 0.06) if a < 0.16 else lerp(30, 0, (a - 0.16) / 0.45)
    return {"ArmR": (arm, 0, -12), "ForeR": (-30, 0, 0), "Body": (6, tw, 0), "ArmL": (-55, 0, 0), "ForeL": (-70, 0, 0),
            "LegL": (-14, 0, 0), "LegR": (16, 0, 0), "ShinL": (10, 0, 0), "ShinR": (4, 0, 0), "Head": (0, -tw * 0.5, 0)}, 0.0


def clip_shoot(f, n):
    a = f / FPS                                   # release, then draw again and hold
    draw = 1 - a / 0.12 if a < 0.12 else max(0.0, min(1.0, (a - 0.35) / 0.7))
    return {"ArmL": (-88, -8, 0), "ForeL": (-4, 0, 0), "ArmR": (-75, 30, 0), "ForeR": (lerp(-20, -95, draw), 0, 0),
            "Body": (0, -24, 0), "Head": (0, 22, 0), "LegL": (-6, 0, 0), "LegR": (8, 0, 0), "ShinL": (0, 0, 0), "ShinR": (0, 0, 0)}, 0.0


def clip_death(f, n):
    k = min(1.0, (f / FPS) / 0.55); k = k * k     # accelerating fall, no ease-out
    return {"Body": (-86 * k, 0, 6 * k), "Head": (-14 * k, 0, 0), "ArmL": (-30 * k, 0, -55 * k), "ArmR": (-20 * k, 0, 62 * k),
            "ForeL": (-24 * k, 0, 0), "ForeR": (-35 * k, 0, 0), "LegL": (8 * k, 0, -9 * k), "LegR": (-4 * k, 0, 11 * k),
            "ShinL": (14 * k, 0, 0), "ShinR": (26 * k, 0, 0)}, -0.80 * k


#        name      frames  loop   function
CLIPS = [("Idle",   72, True,  clip_idle),   ("Walk",   24, True,  clip_walk),  ("Carry",  24, True,  clip_carry),
         ("Chop",   48, True,  clip_chop),   ("Hammer", 33, True,  clip_hammer),
         ("Attack", 27, False, clip_attack), ("Shoot",  36, False, clip_shoot), ("Death",  33, False, clip_death)]


# ------------------------------------------------------------------------------ maths
def euler_q(x, y, z):
    """Clip angles -> Blender quaternion. X = pitch, Y = yaw about UP (Blender Z), Z = roll about FORWARD
    (the figure faces Blender -Y). Composition order Y * X * Z, as the clips were authored."""
    return (Matrix.Rotation(math.radians(y), 3, "Z") @ Matrix.Rotation(math.radians(x), 3, "X")
            @ Matrix.Rotation(math.radians(-z), 3, "Y")).to_quaternion()


def world_rotations(pose, corr):
    """limb -> the rotation (armature space) that takes it from REST to the posed orientation."""
    E = {l: euler_q(*pose.get(l, (0, 0, 0))) for l in LIMBS}
    W = {"Body": E["Body"]}
    W["Head"] = W["Body"] @ E["Head"]
    for l in ("ArmL", "ArmR", "LegL", "LegR"):
        W[l] = W["Body"] @ (E[l] @ corr[l])
    for l, p in CORR_PARENT.items():
        cp = corr[p]
        W[l] = W[p] @ (cp.inverted() @ E[l] @ corr[l] @ cp)
    return W


def main():
    args = EF._argv()
    name, out = EF._opt(args, "--name"), EF._opt(args, "--out")
    prefix = EF._opt(args, "--prefix", name)
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.fps = FPS

    ctx = EF.prepare(name, prefix)
    limb_obj, pivots, tips, coll = ctx["limb_obj"], ctx["pivots"], ctx["tips"], ctx["coll"]

    # ---- rest data --------------------------------------------------------------------------
    head = {l: pivots[l].copy() for l in LIMBS}
    tail = {l: tips[l].copy() for l in tips}
    tail["Body"] = pivots["Head"].copy()                         # pelvis -> base of the neck
    tail["Head"] = pivots["Head"] + Vector((0, 0, 0.22))
    corr = {}
    for l in ("ArmL", "ArmR", "LegL", "LegR"):
        corr[l] = (tail[l] - head[l]).normalized().rotation_difference(DOWN)
    for l, p in CORR_PARENT.items():
        corr[l] = (corr[p] @ (tail[l] - head[l]).normalized()).rotation_difference(DOWN)

    # ---- skin: one vertex group per limb, weight 1.0, then ONE mesh ---------------------------
    for l, o in limb_obj.items():
        g = o.vertex_groups.new(name=l)
        g.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    for o in limb_obj.values():
        o.select_set(True)
    bpy.context.view_layer.objects.active = limb_obj["Body"]
    bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    mesh.name = name + "_mesh"; mesh.data.name = name + "_mesh"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    loose = [v.index for v in mesh.data.vertices if len(v.groups) != 1]
    if loose:
        print(f"[rig] ! {len(loose)} vertices are not bound to exactly one bone"); sys.exit(1)

    # ---- armature -------------------------------------------------------------------------------
    arm_data = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new("Rig", arm_data)
    coll.objects.link(arm)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    root = eb.new("Root"); root.head = (0, 0, 0); root.tail = (0, -0.3, 0)       # points where the figure faces
    for l in LIMBS:
        b = eb.new(l); b.head = head[l]; b.tail = tail[l]
        if (b.tail - b.head).length < 0.02:
            b.tail = b.head + Vector((0, 0, 0.05))
    for l in LIMBS:
        eb[l].parent = eb[PARENT[l]] if l in PARENT else eb["Root"]
        eb[l].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")

    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", "ARMATURE"); mod.object = arm
    bpy.context.view_layer.update()

    rest = {l: arm_data.bones[l].matrix_local.copy() for l in LIMBS}             # armature space
    rest_rot = {l: rest[l].to_3x3().to_4x4() for l in LIMBS}
    levels = [["Body"], ["Head", "ArmL", "ArmR", "LegL", "LegR"], ["ForeL", "ForeR", "ShinL", "ShinR"]]

    def apply_pose(pose, bob):
        W = world_rotations(pose, corr)
        P = {"Body": head["Body"] + Vector((0, 0, bob))}
        for lvl in levels[1:]:
            for l in lvl:
                par = PARENT[l]
                P[l] = P[par] + W[par] @ (head[l] - head[par])
        for lvl in levels:                                  # parents first; a child's matrix is resolved
            for l in lvl:                                   # against its parent's CURRENT pose
                arm.pose.bones[l].matrix = Matrix.Translation(P[l]) @ W[l].to_matrix().to_4x4() @ rest_rot[l]
            bpy.context.view_layer.update()

    # ---- actions ----------------------------------------------------------------------------------
    arm.animation_data_create()
    report = []
    for clip, n, loop, fn in CLIPS:
        act = bpy.data.actions.new(clip)
        act.use_fake_user = True
        arm.animation_data.action = act
        prev = {}
        for f in range(n + 1):
            pose, bob = fn(0 if (loop and f == n) else f, n)           # a looping clip ends where it began
            apply_pose(pose, bob)
            for l in LIMBS:
                pb = arm.pose.bones[l]
                q = pb.rotation_quaternion.copy()
                if l in prev and prev[l].dot(q) < 0:                   # q and -q are the same rotation, but the
                    q.negate(); pb.rotation_quaternion = q             # interpolation between them is a full spin
                prev[l] = q
                pb.keyframe_insert("rotation_quaternion", frame=f)
            arm.pose.bones["Body"].keyframe_insert("location", frame=f)
        report.append((clip, n, loop))
    arm.animation_data.action = bpy.data.actions["Idle"]
    scene.frame_start, scene.frame_end = 0, 72
    scene.frame_set(0)

    # ---- optional inspection sheet: one static copy of the skinned mesh per (clip, frame) ------------
    sheet = EF._opt(args, "--sheet")
    if sheet:
        render_sheet(scene, arm, mesh, sheet)

    # ---- export --------------------------------------------------------------------------------------
    mesh.data.calc_loop_triangles(); tris = len(mesh.data.loop_triangles)
    pts = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
    dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 4) for i in range(3)]
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    fbx = os.path.join(out, f"{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0,
        apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
        object_types={"ARMATURE", "MESH"}, use_mesh_modifiers=True, mesh_smooth_type="FACE",
        bake_space_transform=False, add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
        use_armature_deform_only=False, armature_nodetype="NULL",
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode="STRIP")

    mats = sorted({s.name for s in mesh.material_slots if s.name})
    meta = {
        "_comment": "GENERATED by blender/scripts/rig_figure.py. Do not hand-edit.",
        "name": name, "kind": "rig", "triangles": tris, "materials": mats,
        "bones": ["Root"] + LIMBS, "fps": FPS, "walkSpeed": WALK_SPEED,
        "clips": [{"name": c, "frames": n, "seconds": round(n / FPS, 4), "loop": lp} for c, n, lp in report],
        "dimensionsMetres": {"x": dims[0], "y": dims[1], "z": dims[2]}, "toleranceFraction": 0.04,
        "facing": "Unity +Z", "pivot": "ground contact under the pelvis",
    }
    with open(os.path.join(out, f"{name}.meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    keep = EF._opt(args, "--save-blend")
    if keep:
        bpy.ops.wm.save_as_mainfile(filepath=keep)

    print(f"[rig] {name}: {ctx['parts']} parts -> 1 skinned mesh, {tris} tris, {len(LIMBS) + 1} bones, "
          f"{len(report)} clips, {dims[0]} x {dims[1]} x {dims[2]} m")
    print(f"[rig] clips: " + ", ".join(f"{c}({n}f{' loop' if lp else ''})" for c, n, lp in report))
    print(f"[rig] wrote {fbx} ({os.path.getsize(fbx) // 1024} KB)")
    print("[rig] OK")


def render_sheet(scene, arm, mesh, path):
    """Freeze the SKINNED mesh at chosen frames of chosen actions and lay the copies out in a row. What this
    shows is the armature deforming the mesh -- the real thing, not a re-implementation of the pose maths."""
    sys.path.insert(0, "/Users/dhruv/blender/lib")
    import norse as N
    from nodeutils import new_mat, principled, noise_node, math_node, maprange
    shots = [("Idle", 0), ("Walk", 6), ("Walk", 18), ("Carry", 6), ("Chop", 29), ("Chop", 34),
             ("Attack", 3), ("Attack", 5), ("Shoot", 12), ("Death", 33)]
    dg_objs = []
    for i, (clip, frame) in enumerate(shots):
        arm.animation_data.action = bpy.data.actions[clip]
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(mesh.evaluated_get(dg))
        o = bpy.data.objects.new(f"shot_{clip}_{frame}", me)
        scene.collection.objects.link(o)
        o.location = ((i - (len(shots) - 1) / 2) * 1.9, 0, 0)
        dg_objs.append(o)
    arm.animation_data.action = bpy.data.actions["Idle"]; scene.frame_set(0)
    mesh.hide_render = True
    # show the skeleton itself next to the first figure: a thin emissive stick per bone
    stick = bpy.data.materials.new("BoneStick"); stick.use_nodes = True
    nt = stick.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (1.0, 0.25, 0.05, 1); e.inputs[1].default_value = 5.0
    nt.links.new(e.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    x0 = dg_objs[0].location.x - 1.9
    for b in arm.data.bones:
        if b.name == "Root": continue
        h, t = b.head_local, b.tail_local
        bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=(t - h).length, location=(h + t) / 2 + Vector((x0, 0, 0)))
        c = bpy.context.object; c.rotation_mode = "QUATERNION"
        c.rotation_quaternion = Vector((0, 0, 1)).rotation_difference((t - h).normalized()); c.data.materials.append(stick)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=h + Vector((x0, 0, 0))); bpy.context.object.data.materials.append(stick)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    bpy.context.object.data.materials.append(N.turf_material(new_mat, principled, noise_node, math_node, maprange,
                                             lush=(0.05, 0.11, 0.03, 1), dry=(0.09, 0.12, 0.04, 1)))
    N.daylight(sun_energy=2.8, sky_strength=0.32, elevation=44.0, rotation=150.0)
    cd = bpy.data.cameras.new("Cam"); cd.type = "ORTHO"; cd.ortho_scale = 21.5
    cam = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(cam); scene.camera = cam
    cam.location = (-0.95, -16, 5.2); cam.rotation_euler = (math.radians(76), 0, 0)
    N.render_settings(scene, path.replace(".png", "_"), res=(2400, 560), samples=96, exposure=-1.3)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in dg_objs:
        bpy.data.objects.remove(o)
    mesh.hide_render = False
    print("[rig] sheet ->", path)


if __name__ == "__main__":
    main()
