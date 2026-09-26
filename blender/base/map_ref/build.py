"""THE MAP, step 1: one frame that matches art/reference/northgard_camp.png as closely as we can.

Blender only (PENDING B9). Nothing here goes to Unity yet. ~/blender/lib is imported READ-ONLY; everything new lives here.

What the reference IS, read off the image and built in this order of visual weight:
  1. GROUND  warm ochre grass, big pale sandy patches with soft edges, a few greener patches, everything under long wispy
             yellow grass. Dark cobble pads under the buildings. A worn muddy track.
  2. LIGHT   soft, warm, high-key: short blue-grey shadows, nothing black.
  3. TREES   tall dark blue-green conifers in tiers, orange/gold autumn broadleaf as accents, one dead white tree.
  4. BUILDINGS  white plaster + dark timber frame + red tile roofs (twin-tower house, smithy with a stone furnace),
             a thatched hall with a square turret and a red banner, a white tent with orange trim, a campfire.
  5. DRESSING  pebble clusters, mushrooms, flowers, a log.

    blender -b --factory-startup --python blender/base/map_ref/build.py            # build + preview render
    QUALITY=final blender -b --factory-startup --python blender/base/map_ref/build.py
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))
from nodeutils import new_mat, principled, noise_node, math_node, maprange     # noqa: E402
from meshkit import Model, obj_from_bm, bm_box, bm_cyl, beam_between, crate, fence_run, daylight, render_settings  # noqa: E402
import mapgen as MG                                                             # noqa: E402
from vegetation import make_tuft_mesh, grass_material                          # noqa: E402
import materials, terrain as T                                                  # noqa: E402

SEED = 7
random.seed(SEED); rnd = random.Random(SEED)
D, C = bpy.data, bpy.context
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = C.scene
TK = materials.terrain_kit()
QUALITY = os.environ.get("QUALITY", "preview")
W, Dp = 84.0, 58.0                      # metres in frame, a bit more than the camera sees


# ============================================================================ materials
def flat(name, rgb, rough=0.9, noise=(9.0, 0.08)):
    """A matte colour with a little large-scale mottle so nothing is a flat fill."""
    m, nt, out = new_mat("Ref" + name)                     # "Ref" prefix: the library kits own names like LeafGold, and the loader merges duplicates
    p = principled(nt, out, base=(*rgb, 1), rough=rough, spec=0.15)
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-900, 0)
    n = noise_node(nt, co.outputs["Object"], noise[0], 6.0, 0.6, (-700, 0))
    v = maprange(nt, n.outputs["Fac"], 0.35, 0.65, 1 - noise[1], 1 + noise[1], (-500, 0))
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.location = (-250, 0); mul.blend_type = "MULTIPLY"; mul.inputs["Fac"].default_value = 1
    mul.inputs["Color1"].default_value = (*rgb, 1)
    nt.links.new(v.outputs["Result"], mul.inputs["Color2"]); nt.links.new(mul.outputs["Color"], p.inputs["Base Color"])
    return m


def emissive(name, rgb, strength):
    m, nt, out = new_mat("Ref" + name)
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0]); return m


def ground_material():
    """Reads the terrain's colour attribute: R = sand, G = cobble, B = mud. Base is ochre grass with greener patches."""
    m, nt, out = new_mat("RefGround")
    p = principled(nt, out, rough=0.95, spec=0.1)
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "map"; at.location = (-1500, 300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1300, 300); nt.links.new(at.outputs["Color"], sep.inputs[0])
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-1500, -200)
    # ochre grass, mottled, with greener patches from a low-frequency noise
    n1 = noise_node(nt, co.outputs["Object"], 0.09, 4.0, 0.55, (-1300, -100))
    green = maprange(nt, n1.outputs["Fac"], 0.42, 0.62, 0.0, 1.0, (-1100, -100))
    base = nt.nodes.new("ShaderNodeMixRGB"); base.location = (-900, -100)
    base.inputs["Color1"].default_value = (0.30, 0.24, 0.05, 1)          # ochre
    base.inputs["Color2"].default_value = (0.11, 0.24, 0.04, 1)          # meadow green
    nt.links.new(green.outputs["Result"], base.inputs["Fac"])
    n2 = noise_node(nt, co.outputs["Object"], 0.9, 8.0, 0.6, (-1300, -350))
    mott = maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0.78, 1.18, (-1100, -350))
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.location = (-700, -100); mul.blend_type = "MULTIPLY"; mul.inputs["Fac"].default_value = 1
    nt.links.new(base.outputs["Color"], mul.inputs["Color1"]); nt.links.new(mott.outputs["Result"], mul.inputs["Color2"])
    # sand: pale warm, its edge broken by noise
    n3 = noise_node(nt, co.outputs["Object"], 0.7, 6.0, 0.6, (-1300, 500))
    jit = maprange(nt, n3.outputs["Fac"], 0.35, 0.65, -0.22, 0.22, (-1100, 500))
    sandf = math_node(nt, "ADD", sep.outputs["X"], jit.outputs["Result"], loc=(-900, 500))
    sandc = maprange(nt, sandf.outputs[0], 0.28, 0.72, 0.0, 1.0, (-700, 500))
    sand = nt.nodes.new("ShaderNodeMixRGB"); sand.location = (-500, 200)
    sand.inputs["Color2"].default_value = (0.74, 0.70, 0.58, 1)
    nt.links.new(sandc.outputs["Result"], sand.inputs["Fac"]); nt.links.new(mul.outputs["Color"], sand.inputs["Color1"])
    # mud track
    mud = nt.nodes.new("ShaderNodeMixRGB"); mud.location = (-300, 200)
    mud.inputs["Color2"].default_value = (0.20, 0.13, 0.07, 1)
    mudc = maprange(nt, sep.outputs["Z"], 0.2, 0.8, 0.0, 0.9, (-500, 600))
    nt.links.new(mudc.outputs["Result"], mud.inputs["Fac"]); nt.links.new(sand.outputs["Color"], mud.inputs["Color1"])
    # cobbles: dark grey stones with lighter joints (Voronoi cells), only where G says pad
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.location = (-1300, 900); vor.inputs["Scale"].default_value = 2.6
    vor.feature = "F1"
    nt.links.new(co.outputs["Object"], vor.inputs["Vector"])
    stone = maprange(nt, vor.outputs["Distance"], 0.0, 0.5, 1.0, 0.45, (-1100, 900))
    stonec = nt.nodes.new("ShaderNodeMixRGB"); stonec.location = (-900, 900); stonec.blend_type = "MULTIPLY"; stonec.inputs["Fac"].default_value = 1
    stonec.inputs["Color1"].default_value = (0.30, 0.28, 0.26, 1)
    nt.links.new(stone.outputs["Result"], stonec.inputs["Color2"])
    cob = nt.nodes.new("ShaderNodeMixRGB"); cob.location = (-100, 200)
    cobc = maprange(nt, sep.outputs["Y"], 0.3, 0.7, 0.0, 1.0, (-500, 900))
    nt.links.new(cobc.outputs["Result"], cob.inputs["Fac"]); nt.links.new(mud.outputs["Color"], cob.inputs["Color1"])
    nt.links.new(stonec.outputs["Color"], cob.inputs["Color2"])
    nt.links.new(cob.outputs["Color"], p.inputs["Base Color"])
    bn = noise_node(nt, co.outputs["Object"], 40.0, 12.0, 0.7, (-700, -600))
    bmp = nt.nodes.new("ShaderNodeBump"); bmp.location = (100, -300); bmp.inputs["Strength"].default_value = 0.3; bmp.inputs["Distance"].default_value = 0.05
    nt.links.new(bn.outputs["Fac"], bmp.inputs["Height"]); nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    return m


def plaster_material():
    """White lime wash that has been rained on: grey-green streaks, and dirt creeping up from the ground (Object Z)."""
    m, nt, out = new_mat("RefPlaster")
    p = principled(nt, out, rough=0.92, spec=0.1)
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-1100, 0)
    n = noise_node(nt, co.outputs["Object"], 3.0, 8.0, 0.65, (-900, 0))
    v = maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.78, 1.05, (-700, 0))
    base = nt.nodes.new("ShaderNodeMixRGB"); base.location = (-500, 0); base.blend_type = "MULTIPLY"; base.inputs["Fac"].default_value = 1
    base.inputs["Color1"].default_value = (0.66, 0.66, 0.62, 1); nt.links.new(v.outputs["Result"], base.inputs["Color2"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-900, -300); nt.links.new(co.outputs["Object"], sep.inputs[0])
    dirt = maprange(nt, sep.outputs["Z"], 0.0, 1.3, 1.0, 0.0, (-700, -300))
    dn = noise_node(nt, co.outputs["Object"], 9.0, 6.0, 0.6, (-900, -500)); dj = maprange(nt, dn.outputs["Fac"], 0.3, 0.7, 0.4, 1.0, (-700, -500))
    df = math_node(nt, "MULTIPLY", dirt.outputs["Result"], dj.outputs["Result"], loc=(-500, -400))
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.location = (-250, 0); mix.inputs["Color2"].default_value = (0.36, 0.34, 0.28, 1)
    nt.links.new(df.outputs[0], mix.inputs["Fac"]); nt.links.new(base.outputs["Color"], mix.inputs["Color1"]); nt.links.new(mix.outputs["Color"], p.inputs["Base Color"])
    return m


MAT = {
    "plaster": None,   # built below: weathered, darker toward the ground
    "timber":  flat("TimberDark", (0.13, 0.08, 0.05), rough=0.8),
    "tile":    flat("RoofTile", (0.40, 0.07, 0.035), rough=0.75, noise=(14.0, 0.14)),
    "thatch":  flat("Thatch", (0.36, 0.21, 0.06), rough=0.95, noise=(20.0, 0.16)),
    "stone":   flat("FurnaceStone", (0.55, 0.55, 0.52), rough=0.9, noise=(10.0, 0.12)),
    "canvas":  flat("Canvas", (0.88, 0.86, 0.80), rough=0.9),
    "orange":  flat("CanvasOrange", (0.85, 0.36, 0.08), rough=0.9),
    "banner":  flat("BannerRed", (0.72, 0.10, 0.08), rough=0.85),
    "ember":   emissive("Ember", (1.0, 0.35, 0.05), 12.0),
    "flame":   emissive("Flame", (1.0, 0.62, 0.15), 30.0),
    "pebble":  flat("Pebble", (0.42, 0.42, 0.40), rough=0.9),
    "deadwood": flat("DeadWood", (0.86, 0.84, 0.78), rough=0.85),
    "plank":   flat("Plank", (0.42, 0.28, 0.14), rough=0.85, noise=(12.0, 0.14)),
    "tilerow": flat("TileRow", (0.30, 0.05, 0.025), rough=0.75),
    "sigil":   flat("Sigil", (0.90, 0.88, 0.82), rough=0.8),
    "shutter": flat("Shutter", (0.30, 0.16, 0.08), rough=0.85),
    "brick":   flat("Brick", (0.40, 0.22, 0.16), rough=0.9, noise=(18.0, 0.18)),
    "needle_lo": flat("NeedleLow", (0.05, 0.12, 0.08), rough=0.95, noise=(3.0, 0.14)),
    "needle_hi": flat("NeedleHigh", (0.14, 0.26, 0.11), rough=0.95, noise=(3.0, 0.14)),
    "leaf_a":  flat("LeafOrange", (0.62, 0.25, 0.05), rough=0.9, noise=(4.0, 0.18)),
    "leaf_b":  flat("LeafGold", (0.66, 0.44, 0.08), rough=0.9, noise=(4.0, 0.18)),
    "leaf_c":  flat("LeafRust", (0.46, 0.14, 0.05), rough=0.9, noise=(4.0, 0.18)),
    "bush":    flat("Bush", (0.14, 0.28, 0.08), rough=0.95, noise=(4.0, 0.16)),
    "iron":    flat("Iron", (0.14, 0.14, 0.15), rough=0.5),
}
MAT["plaster"] = plaster_material()
for _m in MAT.values(): _m.use_fake_user = True          # the asset library's loader purges materials with no users yet

# ============================================================================ layout (metres; camera looks along +Y)
SITES = {   # name: (x, y, yaw, pad radius)
    "towers": (-13.0, 9.0, 0.35, 7.5),
    "hall":   (0.0, -3.0, 0.15, 7.0),
    "smithy": (14.0, 10.0, -0.25, 6.5),
    "tent":   (16.5, -9.0, 0.5, 0.0),
    "fire":   (-6.5, -13.0, 0.0, 0.0),
}
SAND = [(-18, -14, 12.0), (-2, -21, 9.0), (13, -23, 7.5), (-31, 2, 8.5), (-25, 15, 7.0), (7, 21, 6.0), (30, -9, 6.5), (33, 12, 5.5)]   # centre, radius
TRACK = [(-13, 4), (-6, 0), (0, 3), (8, 6), (14, 4)]                                                  # muddy path


def fbm(x, y, s=0, **kw): return T.fbm(x, y, seed=SEED + s, **kw)
def raw_h(x, y): return fbm(x, y, 1, octaves=3, freq=0.045) * 1.4 + fbm(x, y, 2, octaves=2, freq=0.012) * 1.6


def pad_w(x, y):
    """0..1 how much a point belongs to a building pad (flattened, cobbled)."""
    w = 0.0
    for name, (sx, sy, _, r) in SITES.items():
        if r <= 0: continue
        d = math.hypot(x - sx, y - sy)
        w = max(w, 1.0 - max(0.0, min(1.0, (d - r * 0.72) / (r * 0.28))))
    return w


def height(x, y):
    h = raw_h(x, y); w = 0.0
    for name, (sx, sy, _, r) in SITES.items():
        if r <= 0: continue
        d = math.hypot(x - sx, y - sy); k = 1.0 - max(0.0, min(1.0, (d - r) / (r * 0.9)))
        if k > w: w = k; ph = raw_h(sx, sy)
    return h if w == 0 else h * (1 - w) + ph * w


def sand_w(x, y):
    w = 0.0
    for (sx, sy, r) in SAND:
        d = math.hypot(x - sx, y - sy) + fbm(x, y, 3, octaves=2, freq=0.25) * 2.4
        w = max(w, 1.0 - max(0.0, min(1.0, (d - r * 0.6) / (r * 0.4))))
    return w


def mud_w(x, y):
    best = 99.0
    for (a, b) in zip(TRACK, TRACK[1:]):
        ax, ay = a; bx, by = b; vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)))
        best = min(best, math.hypot(x - ax - vx * t, y - ay - vy * t))
    best += fbm(x, y, 4, octaves=2, freq=0.5) * 0.6
    return 1.0 - max(0.0, min(1.0, (best - 0.9) / 0.9))


# ============================================================================ terrain
world = Model("World")
bm = bmesh.new(); res = 1.0
nx, ny = int(W / res), int(Dp / res)
grid = [[bm.verts.new((-W / 2 + i * res, -Dp / 2 + j * res, height(-W / 2 + i * res, -Dp / 2 + j * res))) for i in range(nx + 1)] for j in range(ny + 1)]
for j in range(ny):
    for i in range(nx):
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
col = bm.loops.layers.color.new("map")
for f in bm.faces:
    for l in f.loops:
        v = l.vert.co; l[col] = (sand_w(v.x, v.y), pad_w(v.x, v.y), mud_w(v.x, v.y), 1.0)
ground = obj_from_bm(world, "Ground", bm, ground_material(), bevel=0.0, smooth=True)
print(f"TERRAIN {nx}x{ny} cells")


# ============================================================================ buildings
def yaw_pt(x, y, cx, cy, yaw):
    c, s = math.cos(yaw), math.sin(yaw); return (cx + x * c - y * s, cy + x * s + y * c)


def plaster_box(m, name, cx, cy, yaw, sx, sy, h, z0, frame=True):
    """White walls with a dark timber frame: corner posts, a top and mid rail on every face, a brace or two."""
    out = []
    b = bmesh.new(); bm_box(b, sx, sy, h, (0, 0, h / 2))
    o = obj_from_bm(m, f"{name}_Walls", b, MAT["plaster"], bevel=0.02, loc=(cx, cy, z0)); o.rotation_euler.z = yaw; out.append(o)
    if frame:
        fb = bmesh.new(); t = 0.16
        for px in (-sx / 2, sx / 2):
            for py in (-sy / 2, sy / 2):
                bm_box(fb, t, t, h + 0.05, (px, py, h / 2))
        for z in (h - 0.08, h * 0.5):
            bm_box(fb, sx + t, t, t, (0, -sy / 2, z)); bm_box(fb, sx + t, t, t, (0, sy / 2, z))
            bm_box(fb, t, sy + t, t, (-sx / 2, 0, z)); bm_box(fb, t, sy + t, t, (sx / 2, 0, z))
        for k in range(1, 3):                              # studs
            bm_box(fb, t * 0.8, t, h, (-sx / 2 + sx * k / 3, -sy / 2, h / 2)); bm_box(fb, t * 0.8, t, h, (-sx / 2 + sx * k / 3, sy / 2, h / 2))
        o = obj_from_bm(m, f"{name}_Frame", fb, MAT["timber"], bevel=0.01, loc=(cx, cy, z0)); o.rotation_euler.z = yaw; out.append(o)
        # a door and a window on the front
        db = bmesh.new(); bm_box(db, 0.9, 0.12, 1.7, (-sx * 0.2, -sy / 2 - 0.02, 0.85)); bm_box(db, 0.8, 0.12, 0.8, (sx * 0.25, -sy / 2 - 0.02, h * 0.55))
        o = obj_from_bm(m, f"{name}_Door", db, MAT["timber"], bevel=0.01, loc=(cx, cy, z0)); o.rotation_euler.z = yaw; out.append(o)
        sh = bmesh.new()                                                       # shutters either side of every window, both long faces
        for face in (-1, 1):
            for wx in (sx * 0.25, -sx * 0.25) if face > 0 else (sx * 0.25,):
                for side in (-1, 1): bm_box(sh, 0.28, 0.10, 0.8, (wx + side * 0.56, face * (sy / 2 + 0.04), h * 0.55))
        o = obj_from_bm(m, f"{name}_Shutters", sh, MAT["shutter"], bevel=0.005, loc=(cx, cy, z0)); o.rotation_euler.z = yaw; out.append(o)
    return out


def gable_roof(m, name, cx, cy, yaw, sx, sy, z0, rise, over=0.45, mat=None):
    """A pitched roof, ridge along x, with an eave overhang and a thick edge so the tiles read."""
    b = bmesh.new(); hx, hy = sx / 2 + over, sy / 2 + over
    for side in (-1, 1):
        a = b.verts.new((-hx, side * hy, 0)); c = b.verts.new((hx, side * hy, 0))
        r0 = b.verts.new((-hx, 0, rise)); r1 = b.verts.new((hx, 0, rise))
        a2 = b.verts.new((-hx, side * hy, -0.22)); c2 = b.verts.new((hx, side * hy, -0.22))
        b.faces.new((a, c, r1, r0) if side > 0 else (c, a, r0, r1))
        b.faces.new((a, a2, c2, c) if side > 0 else (c, c2, a2, a))
    # gable ends
    for ex in (-hx, hx):
        e0 = b.verts.new((ex, -hy, 0)); e1 = b.verts.new((ex, hy, 0)); e2 = b.verts.new((ex, 0, rise))
        b.faces.new((e0, e1, e2) if ex > 0 else (e1, e0, e2))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    o = obj_from_bm(m, f"{name}_Roof", b, mat or MAT["tile"], bevel=0.02, loc=(cx, cy, z0)); o.rotation_euler.z = yaw
    if mat is None:   # tile rows: the reference reads its roofs by their courses
        rows = bmesh.new(); L = math.hypot(hy, rise)
        for k in range(1, 7):
            t = k / 7; y = hy * (1 - t); zz = rise * t
            for side in (-1, 1): bm_box(rows, 2 * hx + 0.04, 0.10, 0.07, (0, side * y, zz + 0.05))
        bm_box(rows, 2 * hx + 0.12, 0.26, 0.16, (0, 0, rise + 0.05))
        r = obj_from_bm(m, f"{name}_Rows", rows, MAT["tilerow"], bevel=0.0, loc=(cx, cy, z0)); r.rotation_euler.z = yaw
    return o


def pyramid_roof(m, name, cx, cy, yaw, w, z0, rise, mat, n=4, over=0.35):
    b = bmesh.new(); bm_cyl(b, w / 2 * 1.41 + over, rise, n, (0, 0, rise / 2), r_top=0.02)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    o = obj_from_bm(m, f"{name}_Roof", b, mat, bevel=0.0, loc=(cx, cy, z0)); o.rotation_euler.z = yaw + (math.pi / 4 if n == 4 else 0)
    return o


def build_towers(m, cx, cy, yaw):
    z = height(cx, cy)
    plaster_box(m, "tw_body", cx, cy, yaw, 7.6, 5.4, 3.2, z)
    gable_roof(m, "tw_body", cx, cy, yaw, 7.6, 5.4, z + 3.2, 2.2)
    for k, tx in enumerate((-2.4, 2.4)):
        px, py = yaw_pt(tx, 0.3, cx, cy, yaw)
        plaster_box(m, f"tw_tower{k}", px, py, yaw, 2.3, 2.3, 5.4, z)
        pyramid_roof(m, f"tw_tower{k}", px, py, yaw, 2.3, z + 5.4, 2.6, MAT["tile"])


def build_hall(m, cx, cy, yaw):
    z = height(cx, cy)
    plaster_box(m, "hall", cx, cy, yaw, 7.2, 7.2, 3.0, z)
    pyramid_roof(m, "hall", cx, cy, yaw, 7.2, z + 3.0, 5.2, MAT["thatch"], n=4, over=0.55)
    px, py = yaw_pt(1.4, 1.4, cx, cy, yaw)
    plaster_box(m, "hall_turret", px, py, yaw, 2.4, 2.4, 6.6, z, frame=False)
    pyramid_roof(m, "hall_turret", px, py, yaw, 2.4, z + 6.2, 2.4, MAT["thatch"], n=4, over=0.4)
    # banner on the front-left wall
    bx, by = yaw_pt(-2.0, -3.75, cx, cy, yaw)
    b = bmesh.new(); bm_box(b, 1.6, 0.06, 2.6, (0, 0, 1.3))
    o = obj_from_bm(m, "hall_Banner", b, MAT["banner"], bevel=0.0, loc=(bx, by, z + 0.8)); o.rotation_euler.z = yaw
    sg = bmesh.new(); bm_box(sg, 0.62, 0.05, 0.62, (0, -0.05, 1.4))
    o = obj_from_bm(m, "hall_Sigil", sg, MAT["sigil"], bevel=0.0, loc=(bx, by, z + 0.8)); o.rotation_euler = (0, math.pi / 4, yaw)


def build_smithy(m, cx, cy, yaw):
    z = height(cx, cy)
    plaster_box(m, "sm", cx, cy, yaw, 6.0, 5.0, 2.7, z)
    gable_roof(m, "sm", cx, cy, yaw, 6.0, 5.0, z + 2.7, 1.9)
    # the furnace: a fat stone cone with a chimney, in front and to the left
    fx, fy = yaw_pt(-4.6, -1.2, cx, cy, yaw)
    b = bmesh.new(); bm_cyl(b, 1.9, 3.4, 14, (0, 0, 1.7), r_top=0.9); bm_cyl(b, 0.55, 2.2, 10, (0, 0, 4.4), r_top=0.5)
    bm_cyl(b, 2.3, 0.5, 14, (0, 0, 0.25))
    obj_from_bm(m, "sm_Furnace", b, MAT["stone"], bevel=0.0, loc=(fx, fy, z))
    mb = bmesh.new(); bm_box(mb, 0.9, 0.7, 0.9, (0, -1.8, 0.45)); obj_from_bm(m, "sm_Mouth", mb, MAT["ember"], bevel=0.0, loc=(fx, fy, z))
    # a chimney on the house too
    hx, hy = yaw_pt(1.8, 0.0, cx, cy, yaw)
    cb = bmesh.new()
    for k in range(11): bm_box(cb, 0.72 + (0.06 if k % 2 else 0), 0.72 + (0.06 if k % 2 == 0 else 0), 0.42, (0, 0, 0.21 + k * 0.42))   # brick courses
    bm_box(cb, 0.95, 0.95, 0.18, (0, 0, 11 * 0.42 + 0.09))
    o = obj_from_bm(m, "sm_Chimney", cb, MAT["brick"], bevel=0.01, loc=(hx, hy, z)); o.rotation_euler.z = yaw
    # awning on posts over the anvil, barrels against the wall, a drying rack
    ax, ay = yaw_pt(-1.0, -3.9, cx, cy, yaw)
    for k, (px, py) in enumerate([(-2.6, -3.6), (0.6, -3.6)]):
        qx, qy = yaw_pt(px, py, cx, cy, yaw); pb = bmesh.new(); bm_box(pb, 0.16, 0.16, 2.3, (0, 0, 1.15)); obj_from_bm(m, f"sm_Post{k}", pb, MAT["timber"], bevel=0.0, loc=(qx, qy, z))
    aw = bmesh.new(); bm_box(aw, 3.6, 2.2, 0.12, (0, 0, 2.35)); o = obj_from_bm(m, "sm_Awning", aw, MAT["plank"], bevel=0.0, loc=(ax, ay, z)); o.rotation_euler = (math.radians(12), 0, yaw)
    an = bmesh.new(); bm_box(an, 0.7, 0.3, 0.3, (0, 0, 0.75)); bm_box(an, 0.35, 0.35, 0.6, (0, 0, 0.3)); obj_from_bm(m, "sm_Anvil", an, MAT["iron"], bevel=0.01, loc=(ax, ay, z))
    for k in range(3):
        bx, by = yaw_pt(2.2 + k * 0.75, -3.4, cx, cy, yaw); bb = bmesh.new(); bm_cyl(bb, 0.36, 0.9, 10, (0, 0, 0.45)); bm_cyl(bb, 0.38, 0.06, 10, (0, 0, 0.25)); bm_cyl(bb, 0.38, 0.06, 10, (0, 0, 0.7))
        obj_from_bm(m, f"sm_Barrel{k}", bb, MAT["plank"], bevel=0.0, loc=(bx, by, z))


def build_tent(m, cx, cy, yaw):
    z = height(cx, cy)
    b = bmesh.new(); bm_cyl(b, 3.0, 1.6, 12, (0, 0, 0.8), r_top=3.0); obj_from_bm(m, "tent_Skirt", b, MAT["canvas"], bevel=0.0, loc=(cx, cy, z))
    r = bmesh.new(); bm_cyl(r, 3.6, 2.6, 12, (0, 0, 1.6 + 1.3), r_top=0.15); obj_from_bm(m, "tent_Roof", r, MAT["canvas"], bevel=0.0, loc=(cx, cy, z))
    t = bmesh.new(); bm_cyl(t, 3.7, 0.5, 12, (0, 0, 1.6 + 0.25), r_top=3.1); obj_from_bm(m, "tent_Trim", t, MAT["orange"], bevel=0.0, loc=(cx, cy, z))
    p = bmesh.new(); bm_cyl(p, 0.06, 5.2, 6, (0, 0, 2.6)); obj_from_bm(m, "tent_Pole", p, MAT["timber"], bevel=0.0, loc=(cx, cy, z))
    for k in range(6):                                          # orange stripes hem to peak, and a dark open door facing the camera
        a = k * math.tau / 6 + yaw
        beam_between(m, f"tent_Stripe{k}", (cx + math.cos(a) * 3.55, cy + math.sin(a) * 3.55, z + 1.65), (cx + math.cos(a) * 0.2, cy + math.sin(a) * 0.2, z + 4.15), 0.34, 0.06, MAT["orange"], bevel=0.0)
    d = bmesh.new(); bm_box(d, 1.1, 0.2, 1.5, (0, -3.0, 0.75)); o = obj_from_bm(m, "tent_Door", d, MAT["timber"], bevel=0.0, loc=(cx, cy, z)); o.rotation_euler.z = yaw


def build_fire(m, cx, cy):
    z = height(cx, cy)
    for k in range(5):
        a = k * math.tau / 5; b = bmesh.new(); bm_cyl(b, 0.09, 1.1, 6, (0, 0, 0))
        o = obj_from_bm(m, f"fire_Log{k}", b, TK["bark"], bevel=0.0, loc=(cx, cy, z + 0.25))
        o.rotation_euler = (math.radians(58), 0, a)
    for k in range(7):
        a = k * math.tau / 7; b = bmesh.new(); bm_cyl(b, 0.22, 0.2, 7, (0, 0, 0.1))
        obj_from_bm(m, f"fire_Stone{k}", b, MAT["pebble"], bevel=0.0, loc=(cx + math.cos(a) * 0.75, cy + math.sin(a) * 0.75, z))
    f = bmesh.new()
    for k in range(4):                                                          # flame tongues, and a glow disc under them
        a = k * math.tau / 4; bm_cyl(f, 0.26, rnd.uniform(1.0, 1.7), 7, (math.cos(a) * 0.14, math.sin(a) * 0.14, 0.6), r_top=0.02)
    obj_from_bm(m, "fire_Flame", f, MAT["flame"], bevel=0.0, loc=(cx, cy, z + 0.25))
    g = bmesh.new(); bm_cyl(g, 0.6, 0.06, 12, (0, 0, 0.03)); obj_from_bm(m, "fire_Glow", g, MAT["ember"], bevel=0.0, loc=(cx, cy, z + 0.2))
    for k in range(3):                                                          # torches on poles around the camp
        tx, ty = [(-11.0, -2.0), (7.5, -10.0), (10.5, 15.5)][k]; tz = height(tx, ty)
        pb = bmesh.new(); bm_cyl(pb, 0.07, 2.6, 6, (0, 0, 1.3)); obj_from_bm(m, f"torch_Pole{k}", pb, MAT["timber"], bevel=0.0, loc=(tx, ty, tz))
        fl = bmesh.new(); bm_cyl(fl, 0.16, 0.55, 6, (0, 0, 2.8), r_top=0.02); obj_from_bm(m, f"torch_Flame{k}", fl, MAT["flame"], bevel=0.0, loc=(tx, ty, tz))


town = Model("Town")
build_towers(town, *SITES["towers"][:3]); build_hall(town, *SITES["hall"][:3]); build_smithy(town, *SITES["smithy"][:3])
build_tent(town, *SITES["tent"][:3]); build_fire(town, *SITES["fire"][:2])
print(f"TOWN {len(town.objects)} objects")

# ---- the library we already have: people, a well, crates, fences (PENDING B10 -- "why not use them also?")
lib = MG.AssetLibrary(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"))
for k, p in {"swordsman": "base/troops/models/swordsman.blend", "archer": "base/troops/models/archer.blend", "axeman": "base/troops/models/axeman.blend",
             "horseman": "base/troops/models/horseman.blend", "standard": "base/troops/models/standard.blend", "spearman": "base/troops/models/spearman.blend",
             "citizen": os.path.join(SCENE_DIR, "..", "citizen", "models", "citizen.blend"), "well": "base/outbuildings/models/well.blend"}.items():
    lib.load(k, p)
PEOPLE = [("citizen", -4.0, -9.5, 0.6), ("citizen", 5.5, 1.0, 2.4), ("citizen", -9.0, 3.0, 1.0), ("citizen", 9.0, -6.0, -0.4),
          ("swordsman", -8.5, 12.5, -0.6), ("archer", -6.5, 13.5, -0.9), ("axeman", 11.0, 5.0, 2.6), ("standard", -3.0, 5.5, 0.2),
          ("spearman", 20.0, -3.0, 2.2), ("horseman", 23.0, 17.0, 3.6), ("horseman", 27.0, 14.0, 3.2)]
for i, (k, x, y, yaw) in enumerate(PEOPLE):
    lib.place(k, (x, y, height(x, y)), rot_z=yaw, scale=1.55, name=f"p{i}_{k}")   # RTS scale: the reference draws people half a door taller than life
lib.place("well", (-6.5, 4.5, height(-6.5, 4.5)), rot_z=0.3, name="well")
props = Model("Props")
for (x, y, r) in [(-9.5, 5.5, 0.4), (-9.0, 6.2, 1.1), (17.2, 6.0, 0.2), (17.9, 6.6, 0.9), (-3.5, -7.5, 0.5), (20.0, -13.0, 0.7)]:
    crate(props, (x, y, height(x, y)), MAT["plank"], rot=r, slat_mat=MAT["timber"])
fence_run(props, [(19.0, -14.5, height(19, -14.5)), (23.0, -15.5, height(23, -15.5)), (26.0, -13.0, height(26, -13))], MAT["plank"], h=1.0)
fence_run(props, [(-18.0, 6.0, height(-18, 6)), (-19.5, 2.0, height(-19.5, 2)), (-18.5, -2.0, height(-18.5, -2))], MAT["plank"], h=1.0)
print(f"PEOPLE {len(PEOPLE)}  PROPS {len(props.objects)}")


# ============================================================================ trees, rocks, dressing
def fir(m, loc, h, name):
    """A spruce, not a cone: 8-10 irregular tiers, each a jagged star, dark below and lit at the tips, a real trunk."""
    out = []; tb = bmesh.new(); bm_cyl(tb, h * 0.045, h * 0.62, 7, (0, 0, h * 0.31), r_top=h * 0.012)
    out.append(obj_from_bm(m, f"{name}_Trunk", tb, TK["bark"], bevel=0.0, loc=loc))
    tiers = rnd.randint(8, 10); lo, hi = bmesh.new(), bmesh.new()
    for k in range(tiers):
        t = k / (tiers - 1); z = h * (0.16 + 0.80 * t); R = h * (0.30 * (1 - t) ** 1.15 + 0.025); drop = R * 0.55
        b = lo if t < 0.55 else hi; rot = rnd.uniform(0, math.tau); pts = []
        for i in range(9):
            a = rot + i * math.tau / 9; rr = R * rnd.uniform(0.62, 1.15); pts.append(b.verts.new((math.cos(a) * rr, math.sin(a) * rr, z - drop * rnd.uniform(0.7, 1.2))))
        top = b.verts.new((0, 0, z + h * 0.06))
        for i in range(9): b.faces.new((pts[i], pts[(i + 1) % 9], top))
        cen = b.verts.new((0, 0, z - drop * 1.3))
        for i in range(9): b.faces.new((pts[(i + 1) % 9], pts[i], cen))
    for b, mat, tag in ((lo, MAT["needle_lo"], "Lo"), (hi, MAT["needle_hi"], "Hi")):
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        out.append(obj_from_bm(m, f"{name}_{tag}", b, mat, bevel=0.0, loc=loc))
    return out


def autumn(m, loc, h, name):
    """A broadleaf in autumn: a leaning trunk with two limbs, and a crown of 12-16 displaced blobs in two tones."""
    out = []; base = Vector(loc); lean = Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 1)).normalized()
    top = base + lean * h * 0.55
    out.append(beam_between(m, f"{name}_Trunk", base, top, h * 0.07, h * 0.07, TK["bark"], bevel=0.02))
    for k in range(2):
        a = rnd.uniform(0, math.tau); tip = top + Vector((math.cos(a), math.sin(a), 0.9)).normalized() * h * 0.28
        out.append(beam_between(m, f"{name}_Limb{k}", top - lean * h * 0.08, tip, h * 0.035, h * 0.035, TK["bark"], bevel=0.01))
    mats = [MAT[rnd.choice(["leaf_a", "leaf_b"])], MAT[rnd.choice(["leaf_a", "leaf_c", "leaf_b"])]]
    for k in range(rnd.randint(12, 16)):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0.0, 1.0) ** 0.5 * h * 0.30
        c = top + Vector((math.cos(a) * r, math.sin(a) * r, rnd.uniform(-0.1, 0.42) * h))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=h * rnd.uniform(0.11, 0.19), location=c)
        o = C.object; o.name = f"{name}_Leaf{k}"; m.adopt(o); o.data.materials.append(mats[k % 2])
        o.scale = (1, 1, rnd.uniform(0.7, 0.95)); o.rotation_euler = (rnd.uniform(0, 1), rnd.uniform(0, 1), 0)
        for f in o.data.polygons: f.use_smooth = False
        out.append(o)
    return out


def bush(m, loc, size, name):
    for k in range(rnd.randint(3, 5)):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size * rnd.uniform(0.5, 0.9), location=(loc[0] + rnd.gauss(0, size * 0.5), loc[1] + rnd.gauss(0, size * 0.5), loc[2] + size * 0.35))
        o = C.object; o.name = f"{name}_{k}"; m.adopt(o); o.data.materials.append(MAT["bush"])
        for f in o.data.polygons: f.use_smooth = False

flora = Model("Flora")
n = dict(fir=0, broad=0, rock=0, mush=0, flow=0, log=0, dead=0)


def clear(x, y, extra=0.0):
    return all(math.hypot(x - sx, y - sy) > r * 1.05 + 1.5 + extra for (sx, sy, _, r) in SITES.values()) and mud_w(x, y) < 0.3


def forest_mask(x, y):
    edge = max(abs(x) / (W / 2), abs(y) / (Dp / 2))                                # woods thicken toward the frame edge...
    v = fbm(x, y, 5, octaves=3, freq=0.06) + 0.5                                     # ...but in CLUMPS, with meadow between
    return (0.18 + 0.82 * max(0.0, min(1.0, (edge - 0.40) * 2.4))) * max(0.0, min(1.0, (v - 0.46) * 3.6))


for _ in range(2600):
    x, y = rnd.uniform(-W / 2 + 1, W / 2 - 1), rnd.uniform(-Dp / 2 + 1, Dp / 2 - 1)
    if not clear(x, y, 2.5): continue
    r = rnd.random(); fm = forest_mask(x, y)
    if r < 0.60 * fm:
        h = rnd.uniform(7.0, 11.0); z = height(x, y)
        if rnd.random() < 0.62:
            fir(flora, (x, y, z - 0.1), h, f"fir{n['fir']}"); n["fir"] += 1
        else:
            autumn(flora, (x, y, z - 0.1), h * 0.68, f"broad{n['broad']}"); n["broad"] += 1
    elif r < 0.55 * fm + 0.012 and sand_w(x, y) < 0.3:
        T.mushrooms(flora, (x, y, height(x, y)), TK["mushroom"], TK["mush_stem"], rnd, f"mush{n['mush']}", n=rnd.randint(3, 6), size=0.14); n["mush"] += 1
    elif r < 0.55 * fm + 0.02 and sand_w(x, y) < 0.3:
        T.flowers(flora, (x, y, height(x, y)), TK[rnd.choice(["flower_blue", "flower_white"])], rnd, f"flow{n['flow']}", n=6, size=0.08); n["flow"] += 1
# pebble clusters and a few boulders, the way the reference scatters them in open ground
for k in range(16):
    for _ in range(60):
        x, y = rnd.uniform(-W / 2 + 4, W / 2 - 4), rnd.uniform(-Dp / 2 + 4, Dp / 2 - 4)
        if clear(x, y, 1.0) and forest_mask(x, y) < 0.3: break
    for j in range(rnd.randint(3, 6)):
        px, py = x + rnd.gauss(0, 0.7), y + rnd.gauss(0, 0.5)
        T.boulder(flora, (px, py, height(px, py) - 0.05), rnd.uniform(0.22, 0.48), MAT["pebble"], rnd, f"rock{n['rock']}", flat=True); n["rock"] += 1
for k in range(4):
    x, y = rnd.uniform(-W / 2 + 6, W / 2 - 6), rnd.uniform(-Dp / 2 + 6, Dp / 2 - 6)
    if clear(x, y, 2.0): T.boulder(flora, (x, y, height(x, y) - 0.3), rnd.uniform(0.9, 1.4), TK["rock"], rnd, f"boulder{k}"); n["rock"] += 1
for k in range(2):
    x, y = (-21.0, 12.0) if k == 0 else (26.0, -14.0)
    T.bare_tree(flora, (x, y, height(x, y)), 8.0, MAT["deadwood"], rnd, f"dead{k}", branches=6); n["dead"] += 1
T.fallen_log(flora, (-19.0, -3.0, height(-19, -3)), TK["bark"], rnd, length=2.8, r=0.24, name="log0")
for k in range(22):                                                             # bushes at the foot of the woods and by the pads
    for _ in range(40):
        x, y = rnd.uniform(-W / 2 + 3, W / 2 - 3), rnd.uniform(-Dp / 2 + 3, Dp / 2 - 3)
        if clear(x, y, 0.5) and 0.05 < forest_mask(x, y) < 0.5 and sand_w(x, y) < 0.3: break
    bush(flora, (x, y, height(x, y) - 0.15), rnd.uniform(0.55, 1.0), f"bush{k}")
print("FLORA " + " ".join(f"{k}={v}" for k, v in n.items()))

# grass: long, ochre, everywhere but the pads and the deep sand
GRASS = grass_material(new_mat, principled, maprange, green=(0.16, 0.24, 0.04, 1), olive=(0.30, 0.28, 0.07, 1), straw=(0.46, 0.38, 0.11, 1), translucency=0.4)
tufts = [make_tuft_mesh(f"Tuft{i}", rnd.randint(40, 60), 900 + i, GRASS, h_range=(0.22, 0.55), w_range=(0.0045, 0.009), bend_range=(0.10, 0.34)) for i in range(6)]
nt_ = 0
for _ in range(34000):
    x, y = rnd.uniform(-W / 2 + 0.5, W / 2 - 0.5), rnd.uniform(-Dp / 2 + 0.5, Dp / 2 - 0.5)
    if pad_w(x, y) > 0.25 or mud_w(x, y) > 0.45: continue
    if rnd.random() < sand_w(x, y) * 0.80: continue
    o = D.objects.new(f"Tuft_{nt_:05d}", rnd.choice(tufts)); C.scene.collection.objects.link(o)
    o.location = (x, y, height(x, y) - 0.04); s = rnd.uniform(0.9, 1.6); o.scale = (s, s, s * rnd.uniform(0.9, 1.5)); o.rotation_euler = (0, 0, rnd.uniform(0, math.tau))
    nt_ += 1
print(f"GRASS {nt_} tufts")


# ============================================================================ light, camera, render
daylight(sun_energy=2.4, sky_strength=0.40, elevation=57.0, rotation=215.0)
for o in D.objects:
    if o.type == "LIGHT" and o.data.type == "SUN": o.data.angle = math.radians(6.0); o.data.color = (1.0, 0.93, 0.82)
# a breath of haze: the far ground goes paler and bluer, which is most of what "depth" is in the reference.
# A BOX over the map, not a world volume: a world volume attenuates the sun over an infinite path and renders night.
hz_m, hz_nt, hz_out = new_mat("RefHaze"); hz_nt.nodes.remove([nd for nd in hz_nt.nodes if nd.type == "BSDF_PRINCIPLED"][0]) if any(nd.type == "BSDF_PRINCIPLED" for nd in hz_nt.nodes) else None
vol = hz_nt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Color"].default_value = (0.70, 0.80, 0.95, 1); vol.inputs["Density"].default_value = 0.0011; vol.inputs["Anisotropy"].default_value = 0.3
hz_nt.links.new(vol.outputs[0], hz_out.inputs["Volume"])
hb = bmesh.new(); bm_box(hb, W + 60, Dp + 60, 45, (0, 0, 22.5)); haze = obj_from_bm(world, "Haze", hb, hz_m, bevel=0.0); haze.display_type = "WIRE"
cam_d = D.cameras.new("Cam"); cam_d.lens = 40; cam = D.objects.new("Cam", cam_d); C.scene.collection.objects.link(cam); scene.camera = cam
pitch = math.radians(50.0); dist = 54.0
cam.location = (1.5, -dist * math.cos(pitch), dist * math.sin(pitch) + 1.0)
cam.rotation_euler = (math.pi / 2 - pitch, 0, math.radians(1.5))
out = os.path.join(SCENE_DIR, "renders", "ref_")
if QUALITY == "final": render_settings(scene, out + "final", res=(1920, 1170), samples=320, exposure=-2.1)
else: render_settings(scene, out + "preview", res=(1084, 660), samples=64, exposure=-2.1)
scene.view_settings.look = "AgX - Medium High Contrast"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENE_DIR, "map_ref.blend"))
print("BUILT", len(D.objects), "objects")
bpy.ops.render.render(write_still=True)
print("RENDERED", scene.render.filepath)
