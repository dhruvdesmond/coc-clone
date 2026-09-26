"""THE FIGURES v2 (plan B25 Phase H, PENDING B27): every soldier and the rider rebuilt in the citizen's kit -- chunky, joints
buried INSIDE the limbs in the limb's own material, sleeves / cuffs / skirt / boot cuffs over every joint line, a face,
the tunic in the player's blue, gear as body parts (helm, mail, cloak, quiver) and weapons as held props at the grip.

WHY: Dhruv, on the old soldiers -- "the humans have a circle on the shoulder. maybe put some t-shirt or something so that
I should [not] be able to see the skeleton from outside. It should look seamless." The library's humanoid() draws its
pivots as pale ball joints fatter than the limbs. The citizen (session 10) fixed that for one figure; this does it for all.

PART NAMES ARE A CONTRACT with blender/scripts/export_figure.py (PART / PIVOT / SEGMENT). A name with no underscore is a
body part; "<prop>_<Piece>" is a held prop and goes to the nearest hand. The rig (rig_figure.py) canonicalises the rest
pose, so the poses here only matter for the sheet.

    blender -b --factory-startup --python blender/base/figures/build.py          # writes models/<name>.blend for every figure
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))
import materials as M, figure as F                                          # noqa: E402  (read-only)

random.seed(418)
D, C = bpy.data, bpy.context
bpy.ops.wm.read_factory_settings(use_empty=True)
MODELS = os.path.join(SCENE_DIR, "models")
os.makedirs(MODELS, exist_ok=True)
V = Vector
H = 1.72
TONE = 0.62                       # Unity shows pow(v, 0.62): colours are written as they should LOOK and inverted here
def look(r, g, b): return (r ** (1 / TONE), g ** (1 / TONE), b ** (1 / TONE), 1.0)


MAT = {  # docs/16-look.md §3 + §8: team blue on the body, warm skin and leather, cool steel
    "tunic":   M.cloth_material("FigTunic",   look(0.15, 0.30, 0.75)),
    "trim":    M.cloth_material("FigTrim",    look(0.10, 0.20, 0.52)),
    "trouser": M.cloth_material("FigTrouser", look(0.34, 0.27, 0.22), rough=0.85),
    "skin":    M.cloth_material("FigSkin",    look(0.80, 0.57, 0.43), rough=0.66, noise=26.0),
    "hair":    M.cloth_material("FigHair",    look(0.52, 0.36, 0.18), rough=0.80, noise=22.0),
    "leather": M.cloth_material("FigLeather", look(0.36, 0.22, 0.13), rough=0.74),
    "boot":    M.cloth_material("FigBoot",    look(0.20, 0.13, 0.09), rough=0.70),
    "eye":     M.cloth_material("FigEye",     look(0.06, 0.05, 0.05), rough=0.5),
    "cloak":   M.cloth_material("FigCloak",   look(0.62, 0.18, 0.14)),
    "mail":    M.metal_material("FigMail",    look(0.48, 0.50, 0.54), rough=0.62),
    "steel":   M.metal_material("FigSteel",   look(0.70, 0.73, 0.78), rough=0.30),
    "iron":    M.metal_material("FigIron",    look(0.36, 0.37, 0.40), rough=0.46),
}
K = M.troop_kit()                 # the library's weapon materials (wood, iron, shield faces), read-only


def body(name, pose, helmet=False, mail=False, cloak=False, quiver=False, cap=False, beard=True, bare_arms=False, H=H):
    """The chunky humanoid. Short legs, long torso, big head; joints INSIDE the limbs; every joint line covered."""
    m = F.Model(name)
    u = H
    base = dict(pelvis=(0.0, 0.0, 0.440), chest=(0.0, 0.0, 0.640), neck=(0.0, 0.0, 0.752), head=(0.012, 0.0, 0.868),
                l_shoulder=(0.0, 0.192, 0.722), r_shoulder=(0.0, -0.192, 0.722),
                l_elbow=(0.018, 0.232, 0.566), r_elbow=(0.018, -0.232, 0.566),
                l_hand=(0.052, 0.236, 0.418), r_hand=(0.052, -0.236, 0.418),
                l_hip=(0.0, 0.098, 0.430), r_hip=(0.0, -0.098, 0.430),
                l_knee=(0.016, 0.104, 0.240), r_knee=(0.016, -0.104, 0.240),
                l_ankle=(0.0, 0.106, 0.060), r_ankle=(0.0, -0.106, 0.060),
                l_toe=(0.150, 0.106, 0.034), r_toe=(0.150, -0.106, 0.034))
    base.update(pose)
    J = F.skeleton(H, pose=base)
    T, S, L = MAT["tunic"], MAT["skin"], MAT["trouser"]
    CH = MAT["mail"] if mail else T                       # the chest and shoulders wear the mail
    P = lambda part: f"{name}_{part}"

    # ---- body: barrel chest, and a skirt that flares below the belt and hides the hips
    F.seg(m, P("Torso"), J["pelvis"], J["chest"], (0.175 * u, 0.300 * u), (0.205 * u, 0.368 * u), T, n=3, bevel=0.02)
    F.seg(m, P("Chest"), J["chest"], J["neck"], (0.205 * u, 0.368 * u), (0.150 * u, 0.250 * u), CH, n=2, bevel=0.02)
    if mail:                                              # a mail hem over the tunic's top, so the metal has an edge
        F.seg(m, P("MailHem"), J["chest"] - V((0, 0, 0.030 * u)), J["chest"] + V((0, 0, 0.006 * u)), (0.212 * u, 0.376 * u), (0.210 * u, 0.372 * u), MAT["mail"], n=1, bevel=0.01)
    F.seg(m, P("Skirt"), J["pelvis"] + V((0, 0, 0.020 * u)), J["pelvis"] - V((0, 0, 0.150 * u)), (0.190 * u, 0.318 * u), (0.232 * u, 0.372 * u), T, n=2, bevel=0.018)
    F.seg(m, P("Hem"), J["pelvis"] - V((0, 0, 0.150 * u)), J["pelvis"] - V((0, 0, 0.172 * u)), (0.240 * u, 0.380 * u), (0.242 * u, 0.382 * u), MAT["trim"], n=1, bevel=0.008)
    F.seg(m, P("Belt"), J["pelvis"] + V((0, 0, 0.010 * u)), J["pelvis"] + V((0, 0, 0.048 * u)), (0.200 * u, 0.330 * u), (0.200 * u, 0.330 * u), MAT["leather"], n=1, bevel=0.01)
    F.seg(m, P("Buckle"), J["pelvis"] + V((0.100 * u, 0, 0.010 * u)), J["pelvis"] + V((0.100 * u, 0, 0.048 * u)), (0.018 * u, 0.050 * u), (0.018 * u, 0.050 * u), MAT["iron"], n=1, bevel=0.004)
    F.seg(m, P("Collar"), J["neck"] - V((0, 0, 0.012 * u)), J["neck"] + V((0, 0, 0.014 * u)), (0.150 * u, 0.200 * u), (0.125 * u, 0.160 * u), MAT["trim"], n=1, bevel=0.008)
    if cloak:
        F.seg(m, P("Cloak"), J["neck"] + V((-0.060 * u, 0, -0.010 * u)), J["pelvis"] + V((-0.120 * u, 0, -0.230 * u)), (0.030 * u, 0.300 * u), (0.030 * u, 0.420 * u), MAT["cloak"], n=3, bevel=0.008)
    if quiver:
        F.seg(m, P("Quiver"), J["chest"] + V((-0.140 * u, -0.090 * u, -0.080 * u)), J["chest"] + V((-0.200 * u, -0.070 * u, 0.240 * u)), (0.080 * u, 0.080 * u), (0.084 * u, 0.084 * u), MAT["leather"], n=1, bevel=0.01)
        for k in range(4):
            F.seg(m, P(f"QArrow{k}"), J["chest"] + V((-0.200 * u, -0.070 * u + k * 0.012, 0.240 * u)), J["chest"] + V((-0.230 * u, -0.070 * u + k * 0.012, 0.340 * u)), (0.010, 0.010), (0.010, 0.010), K["wood"], n=1)

    # ---- head: big, with a face you can find at portrait zoom
    hd = J["head"]
    F.seg(m, P("Neck"), J["neck"] - V((0, 0, 0.030 * u)), hd - V((0, 0, 0.050 * u)), (0.088 * u, 0.096 * u), (0.096 * u, 0.104 * u), S, n=1)
    F.blob(m, P("Head"), hd, 0.112 * u, S, scale=(0.95, 0.90, 1.0))
    if helmet:
        F.blob(m, P("Helm"), hd + V((-0.006 * u, 0, 0.034 * u)), 0.124 * u, MAT["steel"], scale=(1.0, 0.98, 0.84))
        F.seg(m, P("HelmNose"), hd + V((0.098 * u, 0, 0.040 * u)), hd + V((0.112 * u, 0, -0.050 * u)), (0.028 * u, 0.040 * u), (0.022 * u, 0.028 * u), MAT["steel"], n=1)
        F.seg(m, P("HelmRim"), hd + V((-0.006 * u, 0, 0.004 * u)), hd + V((-0.006 * u, 0, 0.026 * u)), (0.238 * u, 0.234 * u), (0.242 * u, 0.238 * u), MAT["iron"], n=1, bevel=0.006)
    else:
        F.blob(m, P("Hair"), hd + V((-0.022 * u, 0, 0.018 * u)), 0.116 * u, MAT["hair"], scale=(0.95, 0.95, 0.88))
        if cap:
            F.blob(m, P("Cap"), hd + V((-0.010 * u, 0, 0.072 * u)), 0.100 * u, MAT["cloak"], scale=(1.04, 1.04, 0.52))
    if beard: F.blob(m, P("Beard"), hd + V((0.052 * u, 0, -0.066 * u)), 0.074 * u, MAT["hair"], scale=(0.80, 0.92, 1.0))
    F.seg(m, P("Nose"), hd + V((0.100 * u, 0, 0.012 * u)), hd + V((0.128 * u, 0, -0.026 * u)), (0.030 * u, 0.034 * u), (0.040 * u, 0.042 * u), S, n=1, bevel=0.006)
    F.seg(m, P("Brow"), hd + V((0.094 * u, -0.060 * u, 0.030 * u)), hd + V((0.094 * u, 0.060 * u, 0.030 * u)), (0.022 * u, 0.018 * u), (0.022 * u, 0.018 * u), MAT["hair"], n=1, bevel=0.004)
    for side, s in (("l", 1), ("r", -1)):
        F.blob(m, P("Eye" + side), hd + V((0.098 * u, s * 0.040 * u, 0.006 * u)), 0.015 * u, MAT["eye"], scale=(0.6, 1.0, 1.15))

    # ---- limbs. Joints are INSIDE the limb and in its material: they are pivots, not decoration.
    A = S if bare_arms else T
    for side, s in (("l", 1), ("r", -1)):
        sh, el, ha = J[side + "_shoulder"], J[side + "_elbow"], J[side + "_hand"]
        F.blob(m, P("Shoulder" + side), sh, 0.060 * u, CH, scale=(1.0, 1.0, 0.95))
        if mail: F.blob(m, P("Pauldron" + side), sh + V((0, s * 0.020 * u, 0.030 * u)), 0.090 * u, MAT["mail"], scale=(1.05, 1.0, 0.70))
        F.seg(m, P("UpperArm" + side), sh, el, (0.112 * u, 0.112 * u), (0.092 * u, 0.092 * u), A, n=3, bevel=0.016)
        F.blob(m, P("Elbow" + side), el, 0.040 * u, A)
        F.seg(m, P("Forearm" + side), el, ha, (0.090 * u, 0.090 * u), (0.074 * u, 0.074 * u), S, n=3, bevel=0.014)
        cuff0 = el + (ha - el) * 0.02; cuff1 = el + (ha - el) * 0.34
        F.seg(m, P("Cuff" + side), cuff0, cuff1, (0.102 * u, 0.102 * u), (0.098 * u, 0.098 * u), MAT["leather"] if bare_arms else MAT["trim"], n=1, bevel=0.01)
        F.blob(m, P("Hand" + side), ha + (ha - el).normalized() * 0.022 * u, 0.056 * u, S, scale=(1.08, 0.86, 1.18))

        hip, kn, an, toe = J[side + "_hip"], J[side + "_knee"], J[side + "_ankle"], J[side + "_toe"]
        F.blob(m, P("Hip" + side), hip, 0.064 * u, L)
        F.seg(m, P("Thigh" + side), hip, kn, (0.140 * u, 0.140 * u), (0.116 * u, 0.116 * u), L, n=3, bevel=0.016)
        F.blob(m, P("Knee" + side), kn, 0.052 * u, L)
        F.seg(m, P("Shin" + side), kn, an, (0.114 * u, 0.114 * u), (0.100 * u, 0.100 * u), L, n=3, bevel=0.014)
        boot0 = kn + (an - kn) * 0.42
        F.seg(m, P("Boot" + side), boot0, an - V((0, 0, 0.030 * u)), (0.128 * u, 0.128 * u), (0.120 * u, 0.124 * u), MAT["boot"], n=2, bevel=0.014)
        F.seg(m, P("BootCuff" + side), boot0 - V((0, 0, 0.004 * u)), boot0 + V((0, 0, 0.026 * u)), (0.142 * u, 0.142 * u), (0.146 * u, 0.146 * u), MAT["leather"], n=1, bevel=0.008)
        F.seg(m, P("Foot" + side), an + V((-0.045 * u, 0, -0.026 * u)), toe + V((0.010 * u, 0, -0.004 * u)), (0.070 * u, 0.128 * u), (0.058 * u, 0.118 * u), MAT["boot"], up=V((0, 0, 1)), n=1, bevel=0.016)
    return m, J


# ---------------------------------------------------------------------------- the figures
def swordsman():
    m, J = body("swordsman", dict(l_elbow=(0.14, 0.24, 0.60), l_hand=(0.30, 0.16, 0.52), r_elbow=(0.20, -0.24, 0.66), r_hand=(0.36, -0.12, 0.60)), helmet=True, mail=True, cloak=True)
    F.sword(m, J["r_hand"] + V((-0.08, -0.03, 0.08)), J["r_hand"] + V((0.55, 0.15, -0.28)), K, "swordsman_sw")
    F.round_shield(m, J["l_hand"] + V((0.06, 0.02, 0.04)), K, face="shield_b", r=0.38, name="swordsman_sh", rot=(0.22, math.pi / 2 - 0.30, 0))
    return m


def spearman():
    m, J = body("spearman", dict(l_elbow=(0.12, 0.24, 0.58), l_hand=(0.28, 0.16, 0.50), r_elbow=(0.02, -0.26, 0.70), r_hand=(0.16, -0.20, 0.80)), helmet=True, mail=False)
    F.spear(m, J["r_hand"] + V((-0.80, -0.05, -0.30)), J["r_hand"] + V((1.30, 0.08, 0.50)), K, "spearman_sp")
    F.round_shield(m, J["l_hand"] + V((0.06, 0.02, 0.04)), K, face="shield_r", r=0.36, name="spearman_sh", rot=(0.22, math.pi / 2 - 0.30, 0))
    return m


def archer():
    m, J = body("archer", dict(l_elbow=(0.22, 0.16, 0.72), l_hand=(0.42, 0.10, 0.75), r_elbow=(-0.06, -0.24, 0.75), r_hand=(0.10, -0.12, 0.78)), helmet=False, cap=True, beard=False, quiver=True)
    F.bow(m, J["l_hand"] + V((0.06, -0.02, 0.0)), K, "archer_bow", span=1.34, depth=0.20, drawn=True)
    return m


def axeman():
    m, J = body("axeman", dict(l_elbow=(-0.06, 0.20, 0.74), l_hand=(-0.14, 0.06, 0.90), r_elbow=(-0.10, -0.22, 0.74), r_hand=(-0.19, -0.07, 0.95)), helmet=True, mail=True)
    F.axe(m, J["l_hand"] + V((0.04, 0.02, -0.12)), J["r_hand"] + V((-0.38, -0.06, 0.52)), K, "axeman_ax", big=True)
    return m


def standard():
    m, J = body("standard", dict(l_elbow=(0.09, 0.22, 0.68), l_hand=(0.15, 0.20, 0.87), r_elbow=(0.04, -0.22, 0.62), r_hand=(0.13, -0.22, 0.47)), helmet=True, mail=True, cloak=True)
    F.banner(m, (J["l_hand"].x + 0.02, J["l_hand"].y + 0.02, 0.02), K, height=2.55, cloth="tunic_b", name="standard_bn")
    F.sword(m, J["r_hand"] + V((0.02, 0, -0.02)), J["r_hand"] + V((0.34, -0.02, -0.66)), K, "standard_sw")
    return m


def rider():
    """The humanoid who sits on the horse (rig_quadruped.py): standing here, seated by the RideIdle/Ride clips."""
    m, J = body("rider", dict(l_elbow=(0.12, 0.24, 0.60), l_hand=(0.26, 0.18, 0.56), r_elbow=(0.16, -0.24, 0.62), r_hand=(0.30, -0.16, 0.56)), helmet=True, mail=True, cloak=True)
    F.sword(m, J["r_hand"] + V((-0.06, -0.03, 0.06)), J["r_hand"] + V((0.50, 0.12, -0.30)), K, "rider_sw")
    F.round_shield(m, J["l_hand"] + V((0.06, 0.02, 0.04)), K, face="shield_b", r=0.34, name="rider_sh", rot=(0.22, math.pi / 2 - 0.30, 0))
    return m


built = []
for fn in (swordsman, spearman, archer, axeman, standard, rider):
    m = fn()
    path = os.path.join(MODELS, m.name + ".blend")
    D.libraries.write(path, set(m.objects), fake_user=True, path_remap="NONE")
    built.append((m.name, len(m.objects)))
    for o in list(m.objects): D.objects.remove(o, do_unlink=True)      # each asset written alone
print("BUILT " + "  ".join(f"{n}:{c} objects" for n, c in built))
