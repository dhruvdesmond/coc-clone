"""The citizen: his body and the four tools he swaps. Age I, the player's own people.

WHY HE IS NOT IN ~/blender: that library is shared with the mobile game and this repo never writes there. Its helpers
are imported READ-ONLY (Model, seg, blob, skeleton). Everything new lives here.

WHAT WAS WRONG WITH THE OLD ONE (Dhruv's close-up, PENDING B7): ball joints fatter and paler than the limbs -- an artist's
mannequin -- thin square sticks for limbs, no face, every surface tan on ochre ground, and an axe head the size of a spade.

WHAT THIS ONE IS: chunky (head ~1/4.5 of his height, thick tapered limbs, big boots, mitten hands) because he is seen from
60 m; joints buried INSIDE the limbs in the limb's own material (the rig still reads its pivots from them); a tunic skirt
that gives him a silhouette; a face; and a tunic in the player's blue, so he separates from the ground without help.

PART NAMES ARE A CONTRACT with blender/scripts/export_figure.py (PART / PIVOT / SEGMENT): a name with no underscore is a
body part and must be in PART; "<prop>_<Piece>" is a held prop. He holds NOTHING -- tools are separate files, origin at
the grip, authored in rig space (forward = -Y, up = +Z) exactly as they sit in a hanging right hand.

    blender -b --factory-startup --python blender/base/citizen/build.py
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/dhruv/blender/lib")
import materials as M, figure as F                                          # noqa: E402  (read-only)

random.seed(417)
D, C = bpy.data, bpy.context
bpy.ops.wm.read_factory_settings(use_empty=True)
MODELS = os.path.join(SCENE_DIR, "models")
os.makedirs(MODELS, exist_ok=True)

TONE = 0.62                       # Unity shows pow(v, 0.62). Colours below are written AS THEY SHOULD LOOK and inverted here.
def look(r, g, b): return (r ** (1 / TONE), g ** (1 / TONE), b ** (1 / TONE), 1.0)

# His own materials, his own names: export_palette.py --scan reads them out of the .blend (no second table).
MAT = {
    "tunic":   M.cloth_material("CitTunic",    look(0.30, 0.56, 0.96)),              # the player's blue
    "trim":    M.cloth_material("CitTrim",     look(0.18, 0.36, 0.72)),
    "trouser": M.cloth_material("CitTrouser",  look(0.34, 0.27, 0.22), rough=0.85),
    "skin":    M.cloth_material("CitSkin",     look(0.80, 0.57, 0.43), rough=0.66, noise=26.0),
    "hair":    M.cloth_material("CitHair",     look(0.78, 0.56, 0.24), rough=0.80, noise=22.0),
    "cap":     M.cloth_material("CitCap",      look(0.62, 0.22, 0.16)),
    "leather": M.cloth_material("CitLeather",  look(0.36, 0.22, 0.13), rough=0.74),
    "boot":    M.cloth_material("CitBoot",     look(0.20, 0.13, 0.09), rough=0.70),
    "eye":     M.cloth_material("CitEye",      look(0.06, 0.05, 0.05), rough=0.5),
    "haft":    M.cloth_material("CitHaft",     look(0.55, 0.38, 0.22), rough=0.78),
    "steel":   M.metal_material("CitSteel",    look(0.70, 0.73, 0.78), rough=0.30),
    "iron":    M.metal_material("CitIron",     look(0.36, 0.37, 0.40), rough=0.46),
}
V = Vector


def citizen(name="citizen", H=1.70):
    m = F.Model(name)
    u = H
    # fractions of H. Short legs, long torso, big head: the proportions of something meant to be read from above.
    J = F.skeleton(H, pose=dict(
        pelvis=(0.0, 0.0, 0.440), chest=(0.0, 0.0, 0.640), neck=(0.0, 0.0, 0.752), head=(0.012, 0.0, 0.868),
        l_shoulder=(0.0, 0.192, 0.722), r_shoulder=(0.0, -0.192, 0.722),
        l_elbow=(0.018, 0.232, 0.566), r_elbow=(0.018, -0.232, 0.566),
        l_hand=(0.052, 0.236, 0.418), r_hand=(0.052, -0.236, 0.418),
        l_hip=(0.0, 0.098, 0.430), r_hip=(0.0, -0.098, 0.430),
        l_knee=(0.016, 0.104, 0.240), r_knee=(0.016, -0.104, 0.240),
        l_ankle=(0.0, 0.106, 0.060), r_ankle=(0.0, -0.106, 0.060),
        l_toe=(0.150, 0.106, 0.034), r_toe=(0.150, -0.106, 0.034)))
    T, S, L = MAT["tunic"], MAT["skin"], MAT["trouser"]
    P = lambda part: f"{name}_{part}"

    # ---- body: barrel chest, and a skirt that flares below the belt and hides the hips
    F.seg(m, P("Torso"), J["pelvis"], J["chest"], (0.175 * u, 0.300 * u), (0.205 * u, 0.368 * u), T, n=3, bevel=0.02)
    F.seg(m, P("Chest"), J["chest"], J["neck"], (0.205 * u, 0.368 * u), (0.150 * u, 0.250 * u), T, n=2, bevel=0.02)
    F.seg(m, P("Skirt"), J["pelvis"] + V((0, 0, 0.020 * u)), J["pelvis"] - V((0, 0, 0.150 * u)),
          (0.190 * u, 0.318 * u), (0.232 * u, 0.372 * u), T, n=2, bevel=0.018)
    F.seg(m, P("Hem"), J["pelvis"] - V((0, 0, 0.150 * u)), J["pelvis"] - V((0, 0, 0.172 * u)),
          (0.240 * u, 0.380 * u), (0.242 * u, 0.382 * u), MAT["trim"], n=1, bevel=0.008)
    F.seg(m, P("Belt"), J["pelvis"] + V((0, 0, 0.010 * u)), J["pelvis"] + V((0, 0, 0.048 * u)),
          (0.200 * u, 0.330 * u), (0.200 * u, 0.330 * u), MAT["leather"], n=1, bevel=0.01)
    F.seg(m, P("Buckle"), J["pelvis"] + V((0.100 * u, 0, 0.010 * u)), J["pelvis"] + V((0.100 * u, 0, 0.048 * u)),
          (0.018 * u, 0.050 * u), (0.018 * u, 0.050 * u), MAT["iron"], n=1, bevel=0.004)
    F.seg(m, P("Pouch"), J["pelvis"] + V((0.030 * u, 0.175 * u, 0.020 * u)), J["pelvis"] + V((0.030 * u, 0.175 * u, -0.060 * u)),
          (0.085 * u, 0.050 * u), (0.095 * u, 0.058 * u), MAT["leather"], n=1, bevel=0.012)
    F.seg(m, P("Collar"), J["neck"] - V((0, 0, 0.012 * u)), J["neck"] + V((0, 0, 0.014 * u)),
          (0.150 * u, 0.200 * u), (0.125 * u, 0.160 * u), MAT["trim"], n=1, bevel=0.008)

    # ---- head: big, with a face you can find at portrait zoom
    hd = J["head"]
    F.seg(m, P("Neck"), J["neck"] - V((0, 0, 0.030 * u)), hd - V((0, 0, 0.050 * u)),
          (0.088 * u, 0.096 * u), (0.096 * u, 0.104 * u), S, n=1)
    F.blob(m, P("Head"), hd, 0.112 * u, S, scale=(0.95, 0.90, 1.0))
    F.blob(m, P("Hair"), hd + V((-0.022 * u, 0, 0.018 * u)), 0.116 * u, MAT["hair"], scale=(0.95, 0.95, 0.88))
    F.blob(m, P("Cap"), hd + V((-0.010 * u, 0, 0.072 * u)), 0.100 * u, MAT["cap"], scale=(1.04, 1.04, 0.52))
    F.seg(m, P("CapBrim"), hd + V((-0.010 * u, 0, 0.040 * u)), hd + V((-0.010 * u, 0, 0.058 * u)),
          (0.232 * u, 0.232 * u), (0.220 * u, 0.220 * u), MAT["cap"], n=1, bevel=0.01)
    F.blob(m, P("Beard"), hd + V((0.052 * u, 0, -0.066 * u)), 0.074 * u, MAT["hair"], scale=(0.80, 0.92, 1.0))
    F.seg(m, P("Nose"), hd + V((0.100 * u, 0, 0.012 * u)), hd + V((0.128 * u, 0, -0.026 * u)),
          (0.030 * u, 0.034 * u), (0.040 * u, 0.042 * u), S, n=1, bevel=0.006)
    F.seg(m, P("Brow"), hd + V((0.094 * u, -0.060 * u, 0.030 * u)), hd + V((0.094 * u, 0.060 * u, 0.030 * u)),
          (0.022 * u, 0.018 * u), (0.022 * u, 0.018 * u), MAT["hair"], n=1, bevel=0.004)
    for side, s in (("l", 1), ("r", -1)):
        F.blob(m, P("Eye" + side), hd + V((0.098 * u, s * 0.040 * u, 0.006 * u)), 0.015 * u, MAT["eye"], scale=(0.6, 1.0, 1.15))

    # ---- limbs. Joints are INSIDE the limb and in its material: they are pivots, not decoration.
    for side, s in (("l", 1), ("r", -1)):
        sh, el, ha = J[side + "_shoulder"], J[side + "_elbow"], J[side + "_hand"]
        F.blob(m, P("Shoulder" + side), sh, 0.060 * u, T, scale=(1.0, 1.0, 0.95))
        F.seg(m, P("UpperArm" + side), sh, el, (0.112 * u, 0.112 * u), (0.092 * u, 0.092 * u), T, n=3, bevel=0.016)
        F.blob(m, P("Elbow" + side), el, 0.040 * u, T)
        F.seg(m, P("Forearm" + side), el, ha, (0.090 * u, 0.090 * u), (0.074 * u, 0.074 * u), S, n=3, bevel=0.014)
        cuff0 = el + (ha - el) * 0.02; cuff1 = el + (ha - el) * 0.34
        F.seg(m, P("Cuff" + side), cuff0, cuff1, (0.102 * u, 0.102 * u), (0.098 * u, 0.098 * u), MAT["trim"], n=1, bevel=0.01)
        F.blob(m, P("Hand" + side), ha + (ha - el).normalized() * 0.022 * u, 0.056 * u, S, scale=(1.08, 0.86, 1.18))

        hip, kn, an, toe = J[side + "_hip"], J[side + "_knee"], J[side + "_ankle"], J[side + "_toe"]
        F.blob(m, P("Hip" + side), hip, 0.064 * u, L)
        F.seg(m, P("Thigh" + side), hip, kn, (0.140 * u, 0.140 * u), (0.116 * u, 0.116 * u), L, n=3, bevel=0.016)
        F.blob(m, P("Knee" + side), kn, 0.052 * u, L)
        F.seg(m, P("Shin" + side), kn, an, (0.114 * u, 0.114 * u), (0.100 * u, 0.100 * u), L, n=3, bevel=0.014)
        boot0 = kn + (an - kn) * 0.42
        F.seg(m, P("Boot" + side), boot0, an - V((0, 0, 0.030 * u)), (0.128 * u, 0.128 * u), (0.120 * u, 0.124 * u), MAT["boot"], n=2, bevel=0.014)
        F.seg(m, P("BootCuff" + side), boot0 - V((0, 0, 0.004 * u)), boot0 + V((0, 0, 0.026 * u)),
              (0.142 * u, 0.142 * u), (0.146 * u, 0.146 * u), MAT["leather"], n=1, bevel=0.008)
        F.seg(m, P("Foot" + side), an + V((-0.045 * u, 0, -0.026 * u)), toe + V((0.010 * u, 0, -0.004 * u)),
              (0.070 * u, 0.128 * u), (0.058 * u, 0.118 * u), MAT["boot"], up=V((0, 0, 1)), n=1, bevel=0.016)
    return m


# ------------------------------------------------------------------------------------------------ tools
# RIG SPACE: forward = -Y, up = +Z, origin AT THE GRIP. Held in a fist, so the haft is square to the forearm: with the arm
# hanging it lies level and points forward, head in front, working edge DOWN. Clips are written against exactly this.
def haft(m, name, length, back=0.18, w=0.046):
    return F.seg(m, f"{name}_Haft", V((0, back, 0)), V((0, -length, 0)), (w, w), (w * 0.9, w * 0.9), MAT["haft"], up=V((0, 0, 1)), n=2)


def plate(m, name, pts, thick, mat, at):
    """A flat head cut from an outline in the Y-Z plane (the plane the tool swings in), `thick` across X."""
    bm = bmesh.new(); a, b = [], []
    for (y, z) in pts:
        a.append(bm.verts.new(at + V((thick / 2, y, z)))); b.append(bm.verts.new(at + V((-thick / 2, y, z))))
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts); bm.faces.new((a[i], a[j], b[j], b[i]))
    return F.obj_from_bm(m, name, bm, mat, bevel=0.004)


def tool_axe():
    m = F.Model("tool_axe"); L = 0.80
    haft(m, "axe", L)
    # a bearded axe: socket on the haft, blade sweeping DOWN to the edge. 17 cm of blade, not a spade.
    plate(m, "axe_Head", [(0.045, 0.036), (-0.055, 0.036), (-0.095, -0.075), (-0.110, -0.235), (0.080, -0.235), (0.050, -0.075)],
          0.032, MAT["steel"], V((0, -L + 0.07, 0)))
    F.blob(m, "axe_Collar", V((0, -L + 0.07, 0)), 0.030, MAT["iron"], scale=(1.0, 1.5, 1.0))
    return m


def tool_pick():
    m = F.Model("tool_pick"); L = 0.90
    haft(m, "pick", L, w=0.040)
    at = V((0, -L + 0.05, 0))
    plate(m, "pick_Head", [(0.030, 0.040), (-0.030, 0.040), (-0.020, -0.090), (-0.006, -0.300), (0.006, -0.300), (0.020, -0.090)], 0.030, MAT["iron"], at)
    plate(m, "pick_Poll", [(0.026, 0.040), (-0.026, 0.040), (-0.018, 0.150), (0.018, 0.150)], 0.034, MAT["iron"], at)
    return m


def tool_hoe():
    """NOT gripped like an axe. A hoe runs DOWN from the fist like a staff: with the forearm reaching forward and down, the
    haft points at the soil a metre ahead and the blade -- which faces BACK, toward him -- bites and is dragged home.
    (Mounted like the axe, it stood upright in front of his face.)"""
    m = F.Model("tool_hoe"); L = 1.25
    F.seg(m, "hoe_Haft", V((0, 0, 0.34)), V((0, 0, -L + 0.34)), (0.040, 0.040), (0.036, 0.036), MAT["haft"], n=2)
    at = V((0, 0, -L + 0.36))
    F.seg(m, "hoe_Neck", at, at + V((0, 0.075, -0.010)), (0.024, 0.024), (0.020, 0.020), MAT["iron"], up=V((0, 0, 1)), n=1, bevel=0.003)
    # the blade: wide across X, hanging from the neck, facing back along +Y
    F.seg(m, "hoe_Blade", at + V((0, 0.075, 0.020)), at + V((0, 0.095, -0.150)), (0.200, 0.012), (0.220, 0.008), MAT["iron"], up=V((0, 1, 0)), n=1, bevel=0.003)
    return m


def tool_hammer():
    m = F.Model("tool_hammer"); L = 0.52
    haft(m, "hammer", L, back=0.12, w=0.034)
    F.seg(m, "hammer_Head", V((0, -L + 0.04, 0.060)), V((0, -L + 0.04, -0.080)), (0.085, 0.100), (0.090, 0.105), MAT["iron"], up=V((0, 1, 0)), n=1, bevel=0.010)
    return m


built = []
for fn in (citizen, tool_axe, tool_pick, tool_hoe, tool_hammer):
    m = fn()
    path = os.path.join(MODELS, m.name + ".blend")
    D.libraries.write(path, set(m.objects), fake_user=True, path_remap="NONE")
    built.append((m.name, len(m.objects)))
    # each asset is written alone, then cleared, so no file carries another's objects
    for o in list(m.objects):
        D.objects.remove(o, do_unlink=True)
print("BUILT " + "  ".join(f"{n}:{c} objects" for n, c in built))
