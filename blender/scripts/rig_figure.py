"""Give a lib/figure.py humanoid a REAL skeleton -- and make every humanoid share ONE clip library.

    # a figure: skeleton + skinned mesh, NO clips (it plays the shared library)
    blender -b --factory-startup <figure>.blend --python blender/scripts/rig_figure.py -- --name swordsman --out <dir>

    # the library: the same rig, plus every clip. Exported once, from any figure.
    blender -b --factory-startup villager.blend --python blender/scripts/rig_figure.py -- \
        --name humanoid_clips --prefix villager --with-clips --out <dir>

WHAT IT BUILDS
    * An ARMATURE of 11 bones -- Root, Body, Head, ArmL/ForeL, ArmR/ForeR, LegL/ShinL, LegR/ShinR.
    * ONE skinned mesh, bound RIGIDLY: every part of these figures is a rigid box, so each vertex belongs to
      exactly one bone at weight 1.0. Nothing to paint; it deforms exactly as the loose parts did.
    * With --with-clips: every clip in CLIPS, 30 fps, every bone keyed on every frame.

THE CANONICAL REST POSE  (PROGRESS N12 / DL43)
    The figures are not authored neutral -- the archer is already aiming, the swordsman has his shield up.
    The first rig corrected for that per figure at pose time, which forced every FBX to carry its own copy
    of every clip: fine for 4 figures x 8 clips, hopeless for 60 x 43. So the correction now happens ONCE,
    to the geometry: each limb's mesh is rotated about its joint until the torso is upright and every limb
    hangs straight down. Every humanoid then has the SAME rest skeleton, a clip is just bone rotations, and
    one library drives them all. The bind is rigid, so this is exact -- no skin to distort.
    Unity asserts it: FigureRigSetup compares every figure's rest rotations against the library's.

GROUND LOCK
    After a pose is computed the lower ankle is measured and the pelvis shifted so it sits where it rests.
    Crouches, kneels and the walk's bob need no hand-tuned offsets. Clips that leave the ground or lie on
    it (deaths) opt out and give their own offset.

ANGLES (the convention every clip below is written in)
    X pitch: NEGATIVE swings a limb FORWARD/UP, positive back.   Body/Head X: positive leans/looks forward-down.
    Y yaw about up.   Z roll about forward: ArmL outward is negative, ArmR outward is positive.
"""
import bpy, sys, os, json, math, pathlib
from mathutils import Matrix, Vector, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_figure as EF                                                     # noqa: E402

FPS = 30
LIMBS = EF.LIMBS
PARENT = dict(EF.PARENT)
CHILD = {"ArmL": "ForeL", "ArmR": "ForeR", "LegL": "ShinL", "LegR": "ShinR"}
# Where a held tool's grip sits, from the wrist joint, with the arm hanging: in the fist, a little below and ahead.
HAND_GRIP = Vector((0.0, -0.015, -0.035))
DOWN, UP, FORWARD = Vector((0, 0, -1)), Vector((0, 0, 1)), Vector((0, -1, 0))
WALK_SPEED, RUN_SPEED = 3.34, 4.40               # m/s the 24-frame walk and 20-frame run cycles are authored for


# ====================================================================================== clips
def lerp(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))
def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def wave(f, n, ph=0.0): return math.sin(2 * math.pi * f / n + ph)


def snap(a, keys):
    """Piecewise-LINEAR through (time, value) keys. Violence does not ease (docs/09): a strike is a straight
    line from wind-up to impact over two or three frames, and that is the whole trick."""
    if a <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if a <= t1: return v0 + (v1 - v0) * (a - t0) / (t1 - t0)
    return keys[-1][1]


STANCE = {"LegL": (-12, 0, -4), "ShinL": (14, 0, 0), "LegR": (12, 0, 4), "ShinR": (8, 0, 0)}     # a fighting stance


# ---------------------------------------------------------------- shared
def clip_idle(f, n):
    s = wave(f, n)
    return {"Body": (2 + s * 1.2, 0, 0), "Head": (s * -1.5, wave(f, n, 1.0) * 9, 0),
            "ArmL": (-6 + s * 2, 0, -8), "ForeL": (-22, 0, 0), "ArmR": (-6 - s * 2, 0, 8), "ForeR": (-26, 0, 0),
            "LegL": (-5, 0, -3), "ShinL": (6, 0, 0), "LegR": (6, 0, 3), "ShinR": (3, 0, 0)}


def _gait(f, n, stride, lean, arms):
    s, c = wave(f, n), math.cos(2 * math.pi * f / n)
    p = {"LegL": (s * stride, 0, 0), "LegR": (-s * stride, 0, 0),
         "ShinL": (max(0.0, -c) * stride * 1.3, 0, 0), "ShinR": (max(0.0, c) * stride * 1.3, 0, 0),
         "Body": (lean, s * 3.5, 0), "Head": (-lean * 0.5, 0, 0)}
    p.update(arms(s))
    return p


def clip_walk(f, n):    # the tool arm swings less: it is carrying something
    return _gait(f, n, 25, 5, lambda s: {"ArmL": (-s * 20, 0, -6), "ForeL": (-20, 0, 0), "ArmR": (s * 11, 0, 6), "ForeR": (-32, 0, 0)})


def clip_carry(f, n):   # the load lies across both forearms: elbows in, forearms level, a little lean back against the weight
    return _gait(f, n, 19, -3, lambda s: {"ArmL": (-26, 0, 3), "ForeL": (-66, 0, 8), "ArmR": (-26, 0, -3), "ForeR": (-66, 0, -8)})


def clip_run(f, n):
    return _gait(f, n, 36, 13, lambda s: {"ArmL": (-s * 34 - 10, 0, -8), "ForeL": (-78, 0, 0), "ArmR": (s * 26 - 10, 0, 8), "ForeR": (-72, 0, 0)})


def clip_hitreact(f, n):
    k = snap(f / FPS, [(0, 0), (0.07, 1), (0.40, 0)])
    return {"Body": (2 - 16 * k, 6 * k, 0), "Head": (-12 * k, 0, 0), "ArmL": (-6 - 20 * k, 0, -8 - 22 * k), "ForeL": (-22 - 20 * k, 0, 0),
            "ArmR": (-6 - 14 * k, 0, 8 + 18 * k), "ForeR": (-26, 0, 0), "LegL": (-5 + 12 * k, 0, -3), "ShinL": (6 + 8 * k, 0, 0),
            "LegR": (6 + 8 * k, 0, 3), "ShinR": (3, 0, 0)}


def clip_death(f, n):           # falls onto his back
    k = min(1.0, (f / FPS) / 0.55); k *= k
    return ({"Body": (-86 * k, 0, 6 * k), "Head": (-14 * k, 0, 0), "ArmL": (-30 * k, 0, -55 * k), "ArmR": (-20 * k, 0, 62 * k),
             "ForeL": (-24 * k, 0, 0), "ForeR": (-35 * k, 0, 0), "LegL": (8 * k, 0, -9 * k), "LegR": (-4 * k, 0, 11 * k),
             "ShinL": (14 * k, 0, 0), "ShinR": (26 * k, 0, 0)}, -0.80 * k)


def clip_deathfront(f, n):      # pitches forward, arms out to break a fall that does not get broken
    k = min(1.0, (f / FPS) / 0.50); k *= k
    return ({"Body": (84 * k, 0, -5 * k), "Head": (-22 * k, 18 * k, 0), "ArmL": (-130 * k, 0, -28 * k), "ArmR": (-112 * k, 0, 34 * k),
             "ForeL": (-38 * k, 0, 0), "ForeR": (-52 * k, 0, 0), "LegL": (-6 * k, 0, -7 * k), "LegR": (10 * k, 0, 9 * k),
             "ShinL": (8 * k, 0, 0), "ShinR": (30 * k, 0, 0)}, -0.82 * k)


# ---------------------------------------------------------------- worker
# THE BEAT every work clip shares. 0 = the blow has landed, 1 = fully wound up.
#   THE BLOW LANDS AT THE END OF THE LOOP. The sim fires its impact -- the thock, the chips -- when its work timer wraps,
#   and the clip starts when the work starts; so a clip whose blow lands at u ~ 0.97 is in time with the sound without the
#   game knowing anything about it. (The first version landed at u = 0.70: the thock came half a second after the axe.)
#   And he no longer FREEZES after the hit: the tool bites, is wrenched free (a small rebound), and is drawn back.
def _beat(u):
    u %= 1.0
    if u < 0.06: return 0.0                                     # bites
    if u < 0.16: return 0.16 * smooth((u - 0.06) / 0.10)        # wrenched free
    if u < 0.62: return lerp(0.16, 1.0, smooth((u - 0.16) / 0.46))   # drawn back, unhurried
    if u < 0.80: return 1.0 + 0.06 * math.sin(math.pi * (u - 0.62) / 0.18)   # a breath at the top: anticipation
    if u < 0.965: return 1.0 - (u - 0.80) / 0.165               # the blow. LINEAR: violence does not ease
    return 0.0


def _mix(hit, wound, k):
    """Every channel of `hit` blended toward `wound` by k (k may overshoot 1 a little)."""
    out = {}
    for l in set(hit) | set(wound):
        a, b = hit.get(l, (0, 0, 0)), wound.get(l, (0, 0, 0))
        out[l] = tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    return out


def _swing(f, n, up, down, body_up, body_dn, reach=0.0):
    """Overhead: right for a pick, a hammer, a splitting maul. Knees give as the blow lands."""
    hit = {"ArmR": (down, 0, 0), "ForeR": (-25, 0, 0), "ArmL": (down + 5 - reach, 0, 0), "ForeL": (-40, 0, 0),
           "Body": (body_dn, 6, 0), "Head": (8, 0, 0),
           "LegL": (-22, 0, -3), "ShinL": (30, 0, 0), "LegR": (4, 0, 3), "ShinR": (22, 0, 0)}
    wound = {"ArmR": (up, 0, 0), "ForeR": (-70, 0, 0), "ArmL": (up * 0.63, 0, 0), "ForeL": (-40, 0, 0),
             "Body": (body_up, -12, 0), "Head": (-12, 0, 0),
             "LegL": (-10, 0, -3), "ShinL": (10, 0, 0), "LegR": (12, 0, 3), "ShinR": (8, 0, 0)}
    return _mix(hit, wound, _beat(f / n))


def clip_hammer(f, n): return _swing(f, n, -120, -48, -4, 12)
def clip_mine(f, n): return _swing(f, n, -172, -22, -14, 30, reach=10)          # a pick comes from right overhead, into the ground


# A TREE IS NOT A LOG ON A BLOCK. The first Chop was the overhead swing above, aimed at a standing trunk. This one is a
# woodsman's: wound up behind the right shoulder with the body turned away, then hips, shoulders, arms -- ACROSS the body
# and into the trunk at waist height. The tool is square to the forearm and its edge points down the forearm, so:
#   forearm across the body pointing LEFT  ->  haft points FORWARD into the tree, edge leading LEFT. That is the blow.
#   the swing itself is the forearm (and the body under it) sweeping round the vertical: ForeR yaw.
CHOP_HIT = {"Body": (16, 32, 0), "Head": (2, -26, 0),
            "ArmR": (-38, 0, 6), "ForeR": (-8, 14, -84),
            "ArmL": (-46, -34, 0), "ForeL": (-52, 0, 26),              # the left hand comes across to the haft
            "LegL": (-26, 0, -6), "ShinL": (34, 0, 0), "LegR": (16, 0, 8), "ShinR": (24, 0, 0)}
CHOP_WOUND = {"Body": (2, -40, 0), "Head": (-2, 34, 0),
              "ArmR": (14, 0, 38), "ForeR": (-20, -128, -84),
              "ArmL": (-44, -50, 0), "ForeL": (-52, 0, 30),
              "LegL": (-14, 0, -6), "ShinL": (12, 0, 0), "LegR": (14, 0, 8), "ShinR": (10, 0, 0)}


def clip_chop(f, n): return _mix(CHOP_HIT, CHOP_WOUND, _beat(f / n))


def clip_farm(f, n):
    """Hoeing: reach out, chop down, drag home. The hoe runs down from the fist, so where it points is the forearm's pitch
    in the WORLD = arm + forearm + the body's lean. The chop lands at the end of the loop, like every blow."""
    u = ((f / n) - 0.51) % 1.0
    reach = snap(u, [(0, 0), (0.30, 1), (0.38, 1.12), (0.46, 0.62), (1.0, 0)])     # 1.12: lifted clear before it comes down
    lift = snap(u, [(0, 0), (0.30, 0), (0.38, 1), (0.46, 0), (1.0, 0)])
    return {"Body": (20 + 9 * reach, 0, 0), "Head": (12, 0, 0),
            "ArmR": (lerp(-24, -44, reach) - 14 * lift, 0, 6), "ForeR": (lerp(-32, -42, reach) - 10 * lift, 0, 0),
            "ArmL": (lerp(-40, -62, reach) - 14 * lift, 8, -4), "ForeL": (lerp(-20, -30, reach), 0, 14),
            "LegL": (-18, 0, -4), "ShinL": (22, 0, 0), "LegR": (14, 0, 4), "ShinR": (12, 0, 0)}


def clip_forage(f, n):          # crouched at the bush, hands working alternately
    s = wave(f, n)
    return {"Body": (34, s * 4, 0), "Head": (6, s * -8, 0),
            "ArmL": (-74 + s * 18, 0, -10), "ForeL": (-34 - s * 22, 0, 0), "ArmR": (-74 - s * 18, 0, 10), "ForeR": (-34 + s * 22, 0, 0),
            "LegL": (-62, 0, -6), "ShinL": (96, 0, 0), "LegR": (-48, 0, 6), "ShinR": (104, 0, 0)}


def clip_flee(f, n):            # a run with the hands up: it must read as panic from thirty metres
    p = _gait(f, n, 38, 10, lambda s: {})
    s = wave(f, n)
    p.update({"ArmL": (-152 + s * 16, 0, -26), "ForeL": (-38 - s * 14, 0, 0), "ArmR": (-152 - s * 16, 0, 26), "ForeR": (-38 + s * 14, 0, 0),
              "Head": (-10, s * 14, 0)})
    return p


def clip_cheer(f, n):           # the age advance: both arms up, pumping, a bounce in the knees
    s, s2 = wave(f, n), wave(f, n / 2)
    b = (s2 + 1) * 0.5
    return {"Body": (-6, s * 5, 0), "Head": (-14, 0, 0),
            "ArmR": (-158 + b * 18, 0, 16), "ForeR": (-26 - b * 22, 0, 0), "ArmL": (-150 + (1 - b) * 18, 0, -18), "ForeL": (-30 - (1 - b) * 22, 0, 0),
            "LegL": (-8 - b * 12, 0, -4), "ShinL": (12 + b * 22, 0, 0), "LegR": (-6 - b * 12, 0, 4), "ShinR": (10 + b * 22, 0, 0)}


# ---------------------------------------------------------------- sword + shield
# The shield arm. With the arm hanging the shield faces forward (canonicalise). PITCHING the forearm up would lay it
# flat, so the forearm is ROLLED across the chest instead, and the upper arm's forward pitch is cancelled in the forearm.
SHIELD_UP = {"ArmL": (-35, 0, -20), "ForeL": (35, 0, 100)}
GUARD_SWORD = {**SHIELD_UP, "ArmR": (-24, 0, 14), "ForeR": (-58, 0, 0)}


def clip_runshield(f, n):      # the shared Run pumps the forearm, which tips a shield face-up. A shield is carried IN FRONT.
    return _gait(f, n, 36, 13, lambda s: {**SHIELD_UP, "ArmR": (10 + s * 20, 0, 8), "ForeR": (-40, 0, 0)})


def clip_guardidle(f, n):
    s = wave(f, n)
    p = dict(STANCE); p.update(GUARD_SWORD)
    p.update({"Body": (6 + s, -12, 0), "Head": (-2, 12 + wave(f, n, 1.3) * 5, 0), "ArmR": (-24 + s * 2, 0, 14)})
    return p


def clip_attack(f, n):          # overhead cut: anticipation, SNAP, recover
    a = f / FPS
    arm = snap(a, [(0, -40), (0.10, -158), (0.16, 22), (0.62, -24)])
    tw = snap(a, [(0, 0), (0.10, -28), (0.16, 30), (0.62, -12)])
    p = dict(STANCE); p.update(GUARD_SWORD)
    p.update({"ArmR": (arm, 0, 12), "ForeR": (-30, 0, 0), "Body": (6 + tw * 0.2, tw, 0), "Head": (0, -tw * 0.5, 0)})
    return p


def clip_attack2(f, n):         # a flat backhand across the body, so two cuts in a row are not the same cut
    a = f / FPS
    yaw = snap(a, [(0, 0), (0.12, 62), (0.18, -58), (0.62, 0)])
    tw = snap(a, [(0, -12), (0.12, 34), (0.18, -36), (0.62, -12)])
    p = dict(STANCE); p.update(GUARD_SWORD)
    p.update({"ArmR": (-84, yaw, 0), "ForeR": (-14, 0, 0), "Body": (8, tw, 0), "Head": (0, -tw * 0.45, 0)})
    return p


def clip_block(f, n):           # the shield comes UP and across, fast, and is held a beat
    k = snap(f / FPS, [(0, 0), (0.06, 1), (0.30, 1), (0.50, 0)])
    p = dict(STANCE); p.update(GUARD_SWORD)
    p.update({"ArmL": (lerp(-35, -55, k), 0, lerp(-20, -48, k)), "ForeL": (lerp(35, 55, k), 0, lerp(100, 132, k)),
              "Body": (6 - 9 * k, -12 - 8 * k, 0), "Head": (-2 + 8 * k, 12, 0),
              "LegL": (-12 - 6 * k, 0, -4), "ShinL": (14 + 10 * k, 0, 0), "LegR": (12 + 8 * k, 0, 4), "ShinR": (8 + 6 * k, 0, 0)})
    return p


# ---------------------------------------------------------------- two-handed
HANDS_2H = {"ArmR": (-42, -24, 6), "ForeR": (-72, 0, 0), "ArmL": (-56, 30, -4), "ForeL": (-66, 0, 0)}


def clip_idle2h(f, n):
    s = wave(f, n)
    p = dict(STANCE); p.update(HANDS_2H)
    p.update({"Body": (5 + s, -8, 0), "Head": (-2, 8 + wave(f, n, 0.8) * 6, 0)})
    return p


def clip_attack2h(f, n):        # the cleave: both hands, right overhead, all the way down
    a = f / FPS
    up = snap(a, [(0, 0), (0.16, 1), (0.23, -0.12), (0.70, 0)])
    p = dict(STANCE)
    p.update({"ArmR": (lerp(-42, -170, up), lerp(-24, -6, abs(up)), 6), "ForeR": (lerp(-72, -34, abs(up)), 0, 0),
              "ArmL": (lerp(-56, -166, up), lerp(30, 8, abs(up)), -4), "ForeL": (lerp(-66, -30, abs(up)), 0, 0),
              "Body": (lerp(5, -14, up) if up > 0 else lerp(5, 30, -up / 0.12), -8, 0), "Head": (lerp(-2, -14, max(up, 0)), 8, 0)})
    return p


def clip_attackspin(f, n):      # the berserker's whirl: arms out, the whole body is the weapon
    a = f / FPS
    yaw = snap(a, [(0, 0), (0.14, -70), (0.34, 250), (0.80, 360)])
    out = snap(a, [(0, 0), (0.14, 1), (0.34, 1), (0.80, 0)])
    p = dict(STANCE)
    p.update({"Body": (8, yaw, 0), "Head": (0, 0, 0),
              "ArmR": (lerp(-42, -88, out), lerp(-24, 40, out), 6), "ForeR": (lerp(-72, -10, out), 0, 0),
              "ArmL": (lerp(-56, -84, out), lerp(30, -20, out), -4), "ForeL": (lerp(-66, -20, out), 0, 0)})
    return p


# ---------------------------------------------------------------- spear
# The spear is level when the arm hangs (canonicalise), so its pitch is the NET pitch of upper arm + forearm.
GUARD_SPEAR = {"ArmR": (25, 0, 10), "ForeR": (-35, 0, 0), **SHIELD_UP}


def clip_guardspear(f, n):
    s = wave(f, n)
    p = dict(STANCE); p.update(GUARD_SPEAR)
    p.update({"Body": (7 + s, -16, 0), "Head": (-2, 16 + wave(f, n, 1.1) * 5, 0)})
    return p


def clip_thrust(f, n):          # draw back, SNAP the point out with the whole body behind it, recover
    a = f / FPS
    k = snap(a, [(0, 0), (0.12, -1), (0.18, 1), (0.30, 1), (0.60, 0)])        # -1 = drawn back, +1 = extended
    p = dict(STANCE); p.update(GUARD_SPEAR)
    ext = max(k, 0); back = max(-k, 0)
    p.update({"ArmR": (25 + back * 22 - ext * 87, 0, 10), "ForeR": (-35 - back * 17 + ext * 72, 0, 0),
              "Body": (7 + ext * 16 - back * 6, -16 + ext * 22 - back * 10, 0), "Head": (-2 - ext * 8, 16 - ext * 16, 0),
              "LegL": (-12 - ext * 22, 0, -4), "ShinL": (14 + ext * 20, 0, 0), "LegR": (12 + ext * 14, 0, 4)})
    return p


def clip_brace(f, n):           # set against a charge: low, front knee bent, butt of the spear grounded
    s = wave(f, n)
    return {"Body": (14 + s * 0.8, -20, 0), "Head": (-10, 20, 0),
            "ArmR": (12, 0, 12), "ForeR": (-58, 0, 0), "ArmL": (-40, 0, -24), "ForeL": (40, 0, 96),
            "LegL": (-58, 0, -6), "ShinL": (84, 0, 0), "LegR": (26, 0, 8), "ShinR": (58, 0, 0)}


# ---------------------------------------------------------------- bow
def _archer(draw, sway=0.0):
    return {"ArmL": (-88, -8 + sway, 0), "ForeL": (-4, 0, 0), "ArmR": (-75, 30, 0), "ForeR": (lerp(-20, -95, draw), 0, 0),
            "Body": (0, -24 + sway, 0), "Head": (0, 22, 0), "LegL": (-8, 0, -4), "LegR": (10, 0, 4), "ShinL": (6, 0, 0), "ShinR": (4, 0, 0)}


def clip_shoot(f, n):
    a = f / FPS
    return _archer(1 - a / 0.12 if a < 0.12 else max(0.0, min(1.0, (a - 0.35) / 0.7)))


def clip_aimidle(f, n): return _archer(0.35, wave(f, n) * 2.5)


# ---------------------------------------------------------------- standard bearer
BANNER_ARM = {"ArmR": (-78, 0, 8), "ForeR": (-58, 0, 0)}


def clip_banneridle(f, n):
    s = wave(f, n)
    p = {"Body": (1 + s, 0, 0), "Head": (-6, wave(f, n, 0.9) * 8, 0), "ArmL": (-6, 0, -8), "ForeL": (-22, 0, 0),
         "LegL": (-5, 0, -3), "ShinL": (6, 0, 0), "LegR": (6, 0, 3), "ShinR": (3, 0, 0)}
    p.update(BANNER_ARM); return p


def clip_bannerwalk(f, n):
    return _gait(f, n, 25, 3, lambda s: {"ArmL": (-s * 20, 0, -6), "ForeL": (-20, 0, 0), **BANNER_ARM})


#         name           frames loop   fn                ground-lock
CLIPS = [("Idle",         72, True,  clip_idle,        True),  ("Walk",        24, True,  clip_walk,       True),
         ("Run",          20, True,  clip_run,         True),  ("HitReact",    14, False, clip_hitreact,   True),
         ("Death",        33, False, clip_death,       False), ("DeathFront",  33, False, clip_deathfront, False),
         ("Carry",        24, True,  clip_carry,       True),  ("Chop",        48, True,  clip_chop,       True),
         ("Hammer",       33, True,  clip_hammer,      True),  ("Mine",        48, True,  clip_mine,       True),
         ("Farm",         48, True,  clip_farm,        True),  ("Forage",      48, True,  clip_forage,     True),
         ("Flee",         18, True,  clip_flee,        True),  ("Cheer",       40, True,  clip_cheer,      True),
         ("Attack",       27, False, clip_attack,      True),  ("Attack2",     27, False, clip_attack2,    True),
         ("Block",        18, False, clip_block,       True),  ("GuardIdle",   72, True,  clip_guardidle,  True),
         ("Idle2H",       72, True,  clip_idle2h,      True),  ("Attack2H",    30, False, clip_attack2h,   True),
         ("AttackSpin",   30, False, clip_attackspin,  True),  ("GuardSpear",  72, True,  clip_guardspear, True),
         ("Thrust",       24, False, clip_thrust,      True),  ("Brace",       60, True,  clip_brace,      True),
         ("Shoot",        36, False, clip_shoot,       True),  ("AimIdle",     60, True,  clip_aimidle,    True),
         ("BannerIdle",   72, True,  clip_banneridle,  True),  ("BannerWalk",  24, True,  clip_bannerwalk, True),
         ("RunShield",    20, True,  clip_runshield,   True)]


# ====================================================================================== maths
def euler_q(x, y, z):
    return (Matrix.Rotation(math.radians(y), 3, "Z") @ Matrix.Rotation(math.radians(x), 3, "X")
            @ Matrix.Rotation(math.radians(-z), 3, "Y")).to_quaternion()


def world_rotations(pose):
    """limb -> rotation (armature space) from REST to posed. The rest pose is canonical, so this is just the
    chain of clip rotations -- the per-figure corrections the first rig needed are gone."""
    E = {l: euler_q(*pose.get(l, (0, 0, 0))) for l in LIMBS}
    W = {"Body": E["Body"]}
    for l in ("Head", "ArmL", "ArmR", "LegL", "LegR"):
        W[l] = W["Body"] @ E[l]
    for p, c in CHILD.items():
        W[c] = W[p] @ E[c]
    return W


# ====================================================================================== canonical rest pose
def canonicalise(limb_obj, pivots, tips):
    """Rotate the GEOMETRY until the torso is upright and every limb hangs straight down. See module docstring."""
    def subtree(l):
        out = [l]
        for c, p in PARENT.items():
            if p == l: out += subtree(c)
        return out

    def rotate(limbs, q, about):
        R = q.to_matrix()
        for l in limbs:
            limb_obj[l].data.transform(R.to_4x4())                     # vertices are stored relative to the limb's own joint
            limb_obj[l].data.update()
            pivots[l] = about + q @ (pivots[l] - about)
            if l in tips: tips[l] = about + q @ (tips[l] - about)
            limb_obj[l].matrix_world = Matrix.Translation(pivots[l])

    rotate(subtree("Body"), (pivots["Head"] - pivots["Body"]).normalized().rotation_difference(UP), pivots["Body"].copy())
    for l in ("ArmL", "ArmR", "LegL", "LegR"):
        rotate(subtree(l), (tips[l] - pivots[l]).normalized().rotation_difference(DOWN), pivots[l].copy())
    for l in ("ForeL", "ForeR", "ShinL", "ShinR"):
        rotate([l], (tips[l] - pivots[l]).normalized().rotation_difference(DOWN), pivots[l].copy())

    # HELD DISCS (shields). One figure straps his shield facing forward, the next faces it along the forearm, and a
    # guard pose can only suit one of them. So: with the arm hanging, every shield faces FORWARD. A disc is found by
    # its shape -- one thin axis, two wide ones -- not by its name. Long props (sword, spear, bow) are left as authored.
    import numpy as np
    for l in ("ForeL", "ForeR"):
        o = limb_obj[l]
        for g in [g for g in o.vertex_groups if g.name.startswith("prop:")]:
            idx = [v.index for v in o.data.vertices if any(e.group == g.index for e in v.groups)]
            pts = np.array([o.data.vertices[i].co[:] for i in idx])
            c = pts.mean(axis=0)
            w, v = np.linalg.eigh(np.cov((pts - c).T))                  # ascending
            if len(idx) >= 8 and w[0] < 0.15 * w[1] and w[1] > 0.45 * w[2]:
                nrm = Vector(v[:, 0]); hand = tips[l] - pivots[l]           # limb-local, like the vertices
                if nrm.dot(Vector(c) - hand) < 0: nrm.negate()              # the face is the side away from the fist
                R = nrm.rotation_difference(FORWARD).to_matrix()
                for i in idx:
                    o.data.vertices[i].co = hand + R @ (o.data.vertices[i].co - hand)
                print(f"[rig] {l} {g.name}: disc, turned {math.degrees(nrm.angle(FORWARD)):.0f} deg to face forward")
            elif len(idx) >= 8 and w[1] < 0.05 * w[2] and np.ptp((pts - c) @ v[:, 2]) > 1.4:
                # A POLEARM. Carried "at the trail": level, point forward, when the arm hangs. Then a thrust is the hand
                # travelling forward with the forearm kept plumb, and the point stays on the enemy instead of the turf.
                axis = Vector(v[:, 2]); hand = tips[l] - pivots[l]
                along = (pts - c) @ v[:, 2]
                far = pts[np.argmax(np.abs(along + (Vector(c) - hand).dot(axis)))]      # the end furthest from the fist is the point
                if axis.dot(Vector(far) - hand) < 0: axis.negate()
                R = axis.rotation_difference(FORWARD).to_matrix()
                for i in idx:
                    o.data.vertices[i].co = hand + R @ (o.data.vertices[i].co - hand)
                print(f"[rig] {l} {g.name}: polearm {np.ptp(along):.2f} m, turned {math.degrees(axis.angle(FORWARD)):.0f} deg to the trail")
            o.vertex_groups.remove(g)
        o.data.update()
    if limb_obj["Body"].vertex_groups:                                   # none expected; a stray one would fail the skin check
        for g in list(limb_obj["Body"].vertex_groups): limb_obj["Body"].vertex_groups.remove(g)

    # stand it on the ground, pelvis over the origin. Feet only: a spear hanging from a relaxed hand goes below them.
    zmin = min((limb_obj[l].matrix_world @ v.co).z for l in ("ShinL", "ShinR") for v in limb_obj[l].data.vertices)
    shift = Vector((-pivots["Body"].x, -pivots["Body"].y, -zmin))
    for l in LIMBS:
        pivots[l] = pivots[l] + shift
        if l in tips: tips[l] = tips[l] + shift
        limb_obj[l].matrix_world = Matrix.Translation(pivots[l])
    bpy.context.view_layer.update()


# ====================================================================================== main
def main():
    args = EF._argv()
    name, out = EF._opt(args, "--name"), EF._opt(args, "--out")
    prefix = EF._opt(args, "--prefix", name)
    with_clips = "--with-clips" in args
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.fps = FPS

    ctx = EF.prepare(name, prefix)
    limb_obj, pivots, tips, coll = ctx["limb_obj"], ctx["pivots"], ctx["tips"], ctx["coll"]
    canonicalise(limb_obj, pivots, tips)

    # ---- optional: put a TOOL in the right hand, for contact sheets only. It is joined to the forearm exactly as Unity
    #      will parent it to the ForeR bone: grip at the hand, in rig space, with the arm hanging. Never used for an export
    #      that ships -- the citizen's mesh carries no tool; he swaps them.
    attach = EF._opt(args, "--attach")
    if attach:
        with bpy.data.libraries.load(attach) as (src, dst):
            dst.objects = list(src.objects)
        fore = limb_obj["ForeR"]; grip = tips["ForeR"] + HAND_GRIP
        for o in [o for o in dst.objects if o is not None and o.type == "MESH"]:
            coll.objects.link(o)
            bpy.context.view_layer.update()
            o.data.transform(Matrix.Translation(grip - pivots["ForeR"]) @ o.matrix_world)
            o.matrix_world = fore.matrix_world.copy()
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True); fore.select_set(True); bpy.context.view_layer.objects.active = fore
            bpy.ops.object.join()
        limb_obj["ForeR"] = bpy.context.view_layer.objects.active

    head = {l: pivots[l].copy() for l in LIMBS}
    tail = {l: tips[l].copy() for l in tips}
    tail["Body"] = pivots["Head"].copy()
    tail["Head"] = pivots["Head"] + Vector((0, 0, 0.22))

    # ---- skin ------------------------------------------------------------------------------------
    for l, o in limb_obj.items():
        o.vertex_groups.new(name=l).add([v.index for v in o.data.vertices], 1.0, "REPLACE")
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

    # ---- armature ----------------------------------------------------------------------------------
    arm_data = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new("Rig", arm_data)
    coll.objects.link(arm)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    root = eb.new("Root"); root.head = (0, 0, 0); root.tail = (0, -0.3, 0)
    for l in LIMBS:
        b = eb.new(l); b.head = head[l]; b.tail = tail[l]
        # The rest pose is only shared if the bone ROLL is too. Limbs all point straight down and Body/Head
        # straight up, so pin each bone's local Z to the figure's forward: identical on every figure.
        b.align_roll(Vector((0, -1, 0)))
    for l in LIMBS:
        eb[l].parent = eb[PARENT[l]] if l in PARENT else eb["Root"]
        eb[l].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.parent = arm
    mesh.modifiers.new("Armature", "ARMATURE").object = arm
    bpy.context.view_layer.update()

    root_rest = arm_data.bones["Root"].matrix_local.copy()
    rest_rot = {l: arm_data.bones[l].matrix_local.to_3x3().to_4x4() for l in LIMBS}
    ankle = {s: tail[s].copy() for s in ("ShinL", "ShinR")}
    ankle_rest_z = min(a.z for a in ankle.values())
    levels = [["Body"], ["Head", "ArmL", "ArmR", "LegL", "LegR"], ["ForeL", "ForeR", "ShinL", "ShinR"]]

    def apply_pose(pose, bob, ground):
        W = world_rotations(pose)
        P = {"Body": head["Body"].copy()}
        for lvl in levels[1:]:
            for l in lvl:
                P[l] = P[PARENT[l]] + W[PARENT[l]] @ (head[l] - head[PARENT[l]])
        if ground:      # GROUND LOCK: put the lower ankle back where it rests
            low = min((P[s] + W[s] @ (ankle[s] - head[s])).z for s in ("ShinL", "ShinR"))
            bob += ankle_rest_z - low
        # The offset rides on ROOT, which sits at the origin on EVERY figure, so the curve is portable. Keyed on
        # Body it would carry the library figure's pelvis height into everyone else.
        arm.pose.bones["Root"].matrix = Matrix.Translation((0, 0, bob)) @ root_rest
        bpy.context.view_layer.update()
        for l in P: P[l] = P[l] + Vector((0, 0, bob))
        for lvl in levels:
            for l in lvl:
                arm.pose.bones[l].matrix = Matrix.Translation(P[l]) @ W[l].to_matrix().to_4x4() @ rest_rot[l]
            bpy.context.view_layer.update()

    report = []
    if with_clips:
        arm.animation_data_create()
        for clip, n, loop, fn, ground in CLIPS:
            act = bpy.data.actions.new(clip); act.use_fake_user = True
            arm.animation_data.action = act
            prev = {}
            for f in range(n + 1):
                r = fn(0 if (loop and f == n) else f, n)               # a looping clip ends where it began
                pose, bob = r if isinstance(r, tuple) else (r, 0.0)
                apply_pose(pose, bob, ground)
                for l in LIMBS:
                    pb = arm.pose.bones[l]
                    q = pb.rotation_quaternion.copy()
                    if l in prev and prev[l].dot(q) < 0:               # q and -q are one rotation; the path between is a spin
                        q.negate(); pb.rotation_quaternion = q
                    prev[l] = q
                    pb.keyframe_insert("rotation_quaternion", frame=f)
                arm.pose.bones["Root"].keyframe_insert("location", frame=f)
            report.append((clip, n, loop))
        arm.animation_data.action = bpy.data.actions["Idle"]
        scene.frame_start, scene.frame_end = 0, 72
        scene.frame_set(0)

    # ---- export ------------------------------------------------------------------------------------
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
        bake_anim=with_clips, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode="STRIP")

    meta = {
        "_comment": "GENERATED by blender/scripts/rig_figure.py. Do not hand-edit.",
        "name": name, "kind": "clips" if with_clips else "rig", "triangles": tris,
        "materials": sorted({s.name for s in mesh.material_slots if s.name}),
        "bones": ["Root"] + LIMBS, "fps": FPS, "walkSpeed": WALK_SPEED, "runSpeed": RUN_SPEED,
        "clips": [{"name": c, "frames": n, "seconds": round(n / FPS, 4), "loop": lp} for c, n, lp in report],
        "dimensionsMetres": {"x": dims[0], "y": dims[1], "z": dims[2]}, "toleranceFraction": 0.04,
        # rig space (Blender, metres): x right-to-left, -y forward, z up. Unity = (-x, z, -y). A tool is parented to the
        # ForeR bone with its origin here and its axes square to the FIGURE, while the figure is at rest.
        "gripR": [round(c, 4) for c in (tail["ForeR"] + HAND_GRIP)], "gripL": [round(c, 4) for c in (tail["ForeL"] + HAND_GRIP)],
        "restPose": "canonical: torso upright, every limb straight down, bone roll pinned to forward",
        "facing": "Unity +Z", "pivot": "ground contact under the pelvis",
    }
    with open(os.path.join(out, f"{name}.meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # ---- optional inspection sheet: --sheet out.png --shots "Thrust:3,Thrust:5,Brace:0" ----------------------
    sheet = EF._opt(args, "--sheet")
    if sheet and with_clips:
        shots = [(c, int(fr)) for c, fr in (s.split(":") for s in EF._opt(args, "--shots", "Idle:0").split(","))]
        render_sheet(scene, arm, mesh, sheet, shots, float(EF._opt(args, "--turn", "0")))

    keep = EF._opt(args, "--save-blend")
    if keep:
        bpy.ops.wm.save_as_mainfile(filepath=keep)

    leg = (head["LegL"] - tail["ShinL"]).length
    print(f"[rig] {name}: pelvis {head['Body'].z:.3f} m, leg {leg:.3f} m, shoulder {head['ArmR'].z:.3f} m")
    print(f"[rig] {name}: {ctx['parts']} parts -> 1 skinned mesh, {tris} tris, {len(LIMBS) + 1} bones, "
          f"{len(report)} clips, {dims[0]} x {dims[1]} x {dims[2]} m")
    if report:
        print("[rig] clips: " + ", ".join(f"{c}({n}f{' loop' if lp else ''})" for c, n, lp in report))
    print(f"[rig] wrote {fbx} ({os.path.getsize(fbx) // 1024} KB)")
    print("[rig] OK")


def render_sheet(scene, arm, mesh, path, shots, turn=0.0):
    """Freeze the SKINNED mesh at chosen frames of chosen actions and lay the copies out in a row. What this
    shows is the armature deforming the mesh -- the real thing, not a re-implementation of the pose maths."""
    sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))
    import norse as N
    from nodeutils import new_mat, principled, noise_node, math_node, maprange
    dg_objs = []
    for i, (clip, frame) in enumerate(shots):
        arm.animation_data.action = bpy.data.actions[clip]
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(mesh.evaluated_get(dg))
        o = bpy.data.objects.new(f"shot_{clip}_{frame}", me)
        scene.collection.objects.link(o)
        o.location = ((i - (len(shots) - 1) / 2) * 2.3, 0, 0)
        o.rotation_euler = (0, 0, math.radians(turn))
        dg_objs.append(o)
    arm.animation_data.action = bpy.data.actions["Idle"]; scene.frame_set(0)
    mesh.hide_render = True
    # show the skeleton itself next to the first figure: a thin emissive stick per bone
    stick = bpy.data.materials.new("BoneStick"); stick.use_nodes = True
    nt = stick.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (1.0, 0.25, 0.05, 1); e.inputs[1].default_value = 5.0
    nt.links.new(e.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    x0 = dg_objs[0].location.x - 2.3
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
    cd = bpy.data.cameras.new("Cam"); cd.type = "ORTHO"; cd.ortho_scale = 2.3 * (len(shots) + 1.4)
    cam = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(cam); scene.camera = cam
    cam.location = (-1.15, -16, 5.4); cam.rotation_euler = (math.radians(76), 0, 0)
    N.render_settings(scene, path.replace(".png", "_"), res=(2600, 640), samples=96, exposure=-1.3)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in dg_objs:
        bpy.data.objects.remove(o)
    mesh.hide_render = False
    print("[rig] sheet ->", path)



if __name__ == "__main__":
    main()
