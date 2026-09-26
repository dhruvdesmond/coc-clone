"""Inspection sheet for the unit figures: bind poses, the limb pivots, and the PROCEDURAL poses
Unity's FigureAnimator produces -- reproduced here with the same angles, so what you see is what
the game does. Input: the *.rig.blend files written by export_figure.py --save-blend.

    blender -b --factory-startup --python blender/scripts/figure_sheet.py -- <rig dir> <out.png>
"""
import bpy, sys, math, os
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))
import norse as N
from nodeutils import new_mat, principled, noise_node, math_node, maprange

args = sys.argv[sys.argv.index("--") + 1:]
RIGS, OUT = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
C, D = bpy.context, bpy.data
LIMBS = ["Body", "Head", "ArmL", "ForeL", "ArmR", "ForeR", "LegL", "ShinL", "LegR", "ShinR"]


def load(name, at):
    with D.libraries.load(os.path.join(RIGS, name + ".rig.blend")) as (src, dst):
        dst.objects = list(src.objects)
    objs = {}
    for o in dst.objects:
        C.scene.collection.objects.link(o)
        objs[o.name.split(".")[0]] = o
    root = objs[name]
    root.location = Vector(at)
    return objs


PARENT_OF = {"ForeL": "ArmL", "ForeR": "ArmR", "ShinL": "LegL", "ShinR": "LegR"}
DOWN = Vector((0, 0, -1))


def pose(objs, p, bob=0.0):
    """The SAME maths as FigureAnimator.Set(): absolute poses. p: limb -> (x, y, z) in Unity degrees.
    Unity composes Euler as Y * X * Z; Unity X = Blender X, Unity Y(up) = Blender Z, Unity Z(fwd) = Blender -Y."""
    corr = {}
    for limb in ["ArmL", "ArmR", "LegL", "LegR", "ForeL", "ForeR", "ShinL", "ShinR"]:
        d = objs[limb + "_tip"].matrix_basis.translation.normalized()          # bind direction, limb frame
        par = PARENT_OF.get(limb)
        corr[limb] = (corr[par] @ d if par else d).rotation_difference(DOWN)
    for limb, (x, y, z) in p.items():
        o = objs[limb]
        E = (Matrix.Rotation(math.radians(y), 4, "Z") @ Matrix.Rotation(math.radians(x), 4, "X") @ Matrix.Rotation(math.radians(-z), 4, "Y")).to_quaternion()
        if limb in ("Body", "Head"): q = E
        elif limb in PARENT_OF: cp = corr[PARENT_OF[limb]]; q = cp.inverted() @ E @ corr[limb] @ cp
        else: q = E @ corr[limb]
        loc = o.matrix_basis.translation.copy()
        o.matrix_basis = Matrix.Translation(loc) @ q.to_matrix().to_4x4()
    objs["Body"].location.z += bob


def pivots(objs):
    m = D.materials.new("Pivot"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (1.0, 0.12, 0.05, 1); e.inputs[1].default_value = 6.0
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], out.inputs[0])
    C.view_layer.update()
    for l in LIMBS:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.10, location=objs[l].matrix_world.translation)
        C.object.data.materials.append(m)


IDLE = {"Body": (1, 0, 0), "Head": (-1, 6, 0), "ArmL": (-6, 0, -8), "ForeL": (-22, 0, 0), "ArmR": (-6, 0, 8), "ForeR": (-26, 0, 0), "LegL": (-5, 0, -3), "ShinL": (6, 0, 0), "LegR": (6, 0, 3), "ShinR": (3, 0, 0)}
S = 28   # walk stride, degrees
WALK_A = {"LegL": (S, 0, 0), "LegR": (-S, 0, 0), "ShinL": (0, 0, 0), "ShinR": (S * 1.25, 0, 0), "ArmL": (-S * .8, 0, 0), "ArmR": (S * .8, 0, 0), "ForeL": (-12, 0, 0), "ForeR": (-12, 0, 0), "Body": (5, 3.5, 0), "Head": (-3, 0, 0)}
WALK_B = {"LegL": (-S, 0, 0), "LegR": (S, 0, 0), "ShinL": (S * 1.25, 0, 0), "ShinR": (0, 0, 0), "ArmL": (S * .8, 0, 0), "ArmR": (-S * .8, 0, 0), "ForeL": (-12, 0, 0), "ForeR": (-12, 0, 0), "Body": (5, -3.5, 0), "Head": (-3, 0, 0)}
CARRY = dict(WALK_A, ArmL=(-58, 0, 0), ForeL=(-48, 0, 0), ArmR=(-58, 0, 0), ForeR=(-48, 0, 0))
CHOP_UP = {"ArmR": (-150, 0, 0), "ForeR": (-70, 0, 0), "ArmL": (-95, 0, 0), "ForeL": (-40, 0, 0), "Body": (-10, -12, 0), "Head": (-12, 0, 0), "LegL": (-8, 0, 0), "LegR": (10, 0, 0), "ShinL": (8, 0, 0), "ShinR": (6, 0, 0)}
CHOP_DN = {"ArmR": (-35, 0, 0), "ForeR": (-25, 0, 0), "ArmL": (-30, 0, 0), "ForeL": (-40, 0, 0), "Body": (16, 6, 0), "Head": (8, 0, 0), "LegL": (-8, 0, 0), "LegR": (10, 0, 0), "ShinL": (8, 0, 0), "ShinR": (6, 0, 0)}
WINDUP = {"ArmR": (-155, 0, -12), "ForeR": (-30, 0, 0), "Body": (6, -28, 0), "ArmL": (-55, 0, 0), "ForeL": (-70, 0, 0), "LegL": (-14, 0, 0), "LegR": (16, 0, 0), "ShinL": (10, 0, 0), "ShinR": (4, 0, 0), "Head": (0, 14, 0)}
STRIKE = dict(WINDUP, ArmR=(25, 0, -12), Body=(6, 30, 0), Head=(0, -15, 0))
SHOOT = {"ArmL": (-88, -8, 0), "ForeL": (-4, 0, 0), "ArmR": (-80, 25, 0), "ForeR": (-118, 0, 0), "Body": (0, -24, 0), "Head": (0, 22, 0), "LegL": (-6, 0, 0), "LegR": (8, 0, 0), "ShinL": (0, 0, 0), "ShinR": (0, 0, 0)}
DEAD = {"Body": (-86, 0, 6), "Head": (-14, 0, 0), "ArmL": (-30, 0, -55), "ArmR": (-20, 0, 62), "ForeL": (-24, 0, 0), "ForeR": (-35, 0, 0), "LegL": (8, 0, -9), "LegR": (-4, 0, 11), "ShinL": (14, 0, 0), "ShinR": (26, 0, 0)}

dx = 2.5; ROW = 4.4
# back row: the four units in their authored bind pose; the first one shows its ten pivots
for i, n in enumerate(["villager", "swordsman", "spearman", "archer"]):
    o = load(n, ((i - 2) * dx, 2 * ROW, 0))
    if i == 0: pivots(o)
pose(load("swordsman", (2 * dx, 2 * ROW, 0)), IDLE)          # far right of the back row: the idle clip
# middle row: the citizen's procedural clips
for i, p in enumerate([WALK_A, WALK_B, CARRY, CHOP_UP, CHOP_DN]):
    pose(load("villager", ((i - 2) * dx, ROW, 0)), p)
# front row: the raiders'
pose(load("swordsman", (-2 * dx, 0, 0)), WINDUP); pose(load("swordsman", (-1 * dx, 0, 0)), STRIKE)
pose(load("archer", (0, 0, 0)), SHOOT); pose(load("spearman", (1 * dx, 0, 0)), STRIKE)
pose(load("swordsman", (2 * dx, 0, 0)), DEAD, bob=-0.80)

bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
C.object.data.materials.append(N.turf_material(new_mat, principled, noise_node, math_node, maprange, lush=(0.05, 0.11, 0.03, 1), dry=(0.09, 0.12, 0.04, 1)))
N.daylight(sun_energy=2.8, sky_strength=0.32, elevation=46.0, rotation=160.0)
cam_d = D.cameras.new("Cam"); cam_d.type = "ORTHO"; cam_d.ortho_scale = 14.2
cam = D.objects.new("Cam", cam_d); C.scene.collection.objects.link(cam); C.scene.camera = cam
cam.location = (0, -26, 17.6); cam.rotation_euler = (math.radians(60), 0, 0)
N.render_settings(C.scene, OUT.replace(".png", "_"), res=(2000, 1500), samples=96, exposure=-1.3)
C.scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("[sheet] wrote", OUT)
