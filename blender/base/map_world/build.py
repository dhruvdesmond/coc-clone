"""THE WORLD MAP, in Blender only, built from what we already have (PENDING B12).

One continuous 260 x 190 m land in the library's own style: the Norse village in the middle, and around it every resource
the game will need, each in the biome where you would look for it.

    NW  MOUNTAINS + SNOW      stone, iron, coal            NE  VOLCANO + BADLANDS     uranium, obsidian, a lava lake
    W   FOREST                trees, game                  E   DRY STEPPE             more farmland, a second hamlet
    centre  GRASSLAND         the village, farms, berries, a lake with fish
    SW  COAST + SEA           fish shoals, the boathouse   SE  DESERT                 oil seeps + derricks, salt flat, dunes

Roads: grass PATHS to the berry bushes, a dirt ROAD from the village to the mine and the coast, a MUDDY road through the
marsh by the lake. All written into the ground's colour attribute so they follow the terrain.

    blender -b --factory-startup --python blender/base/map_world/build.py           # build + preview hero + plan
    QUALITY=final blender -b --factory-startup --python blender/base/map_world/build.py
"""
import bpy, bmesh, math, random, sys, os, time
T0 = time.time()
from mathutils import Vector

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCENE_DIR)                                          # protos.py, worldreview.py
REPO = os.path.dirname(os.path.dirname(os.path.dirname(SCENE_DIR)))   # clash-of-clans/
sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))
from nodeutils import new_mat, principled, noise_node, math_node, maprange   # noqa: E402
from meshkit import Model, obj_from_bm, bm_box, bm_cyl, beam_between, daylight, render_settings  # noqa: E402
from vegetation import make_tuft_mesh, grass_material                        # noqa: E402
import materials, terrain as T, mapgen as MG                                  # noqa: E402

SEED = 21
random.seed(SEED); rnd = random.Random(SEED)
D, C = bpy.data, bpy.context
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = C.scene
TK = materials.terrain_kit()
QUALITY = os.environ.get("QUALITY", "preview")
W, Dp = 260.0, 190.0
SEA = 0.0


# ============================================================================ the land
def fbm(x, y, s=0, **kw): return T.fbm(x, y, seed=SEED + s, **kw)
def sm(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def falloff(x, y, cx, cy, r, soft): return 1.0 - sm((math.hypot(x - cx, y - cy) - r) / soft)


VOLCANO = (88.0, 62.0)          # NE
MOUNT = (-92.0, 58.0)           # NW
LAKE = (34.0, -2.0)             # centre-east, clear of the village
COAST_Y = lambda x: -66.0 + fbm(x, 0.0, 9, octaves=2, freq=0.02) * 14.0        # the shoreline, SW quadrant


def region(x, y):
    """Which world we are in, as soft weights that sum to about 1."""
    r = {}
    r["mount"] = falloff(x, y, *MOUNT, 30.0, 26.0)
    r["volc"] = falloff(x, y, *VOLCANO, 24.0, 22.0)
    r["desert"] = sm((x - 40.0) / 40.0) * sm((-y - 20.0) / 30.0)
    r["forest"] = sm((-x - 30.0) / 30.0) * (1.0 - r["mount"]) * sm((y + 40.0) / 40.0)
    r["sea"] = sm((COAST_Y(x) - y) / 10.0) * (1.0 - r["desert"] * 0.6)
    r["grass"] = max(0.0, 1.0 - sum(r.values()))
    return r


def raw_h(x, y):
    R = region(x, y)
    base = 2.2 + fbm(x, y, 1, octaves=4, freq=0.012) * 3.4 + fbm(x, y, 2, octaves=2, freq=0.045) * 0.8
    # mountains: a ridge with peaks, up to ~34 m
    dm = math.hypot(x - MOUNT[0], y - MOUNT[1])
    mount = R["mount"] * (10.0 + 24.0 * sm(1.0 - dm / 40.0) + abs(fbm(x, y, 3, octaves=4, freq=0.03)) * 12.0)
    # volcano: a cone with a crater
    dv = math.hypot(x - VOLCANO[0], y - VOLCANO[1])
    cone = 26.0 * sm(1.0 - dv / 28.0) - 9.0 * sm(1.0 - dv / 7.0)
    volc = R["volc"] * cone + R["volc"] * fbm(x, y, 4, octaves=3, freq=0.08) * 1.6
    # desert: long low dunes
    dunes = R["desert"] * (1.5 + 1.8 * math.sin(x * 0.11 + y * 0.05 + fbm(x, y, 5, octaves=2, freq=0.02) * 3.0))
    # sea floor
    sea = -R["sea"] * (3.0 + 4.0 * sm((COAST_Y(x) - y) / 24.0))
    # lake basin
    lake = -6.0 * falloff(x, y, *LAKE, 14.0, 12.0) * (0.6 + 0.4 * fbm(x, y, 6, octaves=2, freq=0.06))
    return base + mount + volc + dunes + sea + lake


PADS = []       # (x, y, r) flattened sites, registered before the mesh is built


def height(x, y):
    h = raw_h(x, y); w = 0.0; ph = h
    for (sx, sy, r) in PADS:
        d = math.hypot(x - sx, y - sy); k = 1.0 - sm((d - r) / (r * 0.8))
        if k > w: w = k; ph = raw_h(sx, sy)
    return h * (1 - w) + ph * w


def slope(x, y, r=2.0):
    h = raw_h(x, y); return max(abs(raw_h(x + r, y) - h), abs(raw_h(x, y + r) - h)) / r


# biome index along one ramp so neighbours blend:  0 seabed/sand  .14 desert  .28 dry steppe  .42 grass  .56 forest floor
#                                                  .70 rock  .84 volcanic ash  1.0 snow
def biome(x, y):
    R = region(x, y); h = raw_h(x, y)
    if R["sea"] > 0.5 or h < SEA + 0.6: return 0.02
    b = 0.42 + 0.14 * sm((fbm(x, y, 7, octaves=3, freq=0.03) + 0.2) * 2.0)           # grass -> forest floor by moisture
    b = b * (1 - R["forest"]) + 0.58 * R["forest"]
    b = b * (1 - R["desert"]) + (0.14 + 0.10 * sm((h - 2.0) / 3.0)) * R["desert"]
    if R["mount"] > 0.05:
        m = 0.70 if h < 24.0 else 1.0
        m = 0.70 + 0.30 * sm((h - 21.0) / 8.0)
        b = b * (1 - R["mount"]) + m * R["mount"]
    if R["volc"] > 0.05: b = b * (1 - R["volc"]) + 0.84 * R["volc"]
    if h < SEA + 1.6 and R["sea"] > 0.1: b = min(b, 0.06 + 0.2 * (h - SEA))
    if slope(x, y) > 0.55: b = max(b, 0.70) if b < 0.84 else b
    return max(0.0, min(1.0, b))


# ---- roads: (points, kind)  kind 0 = grass path, 1 = dirt road, 2 = muddy road. Filled in after siting.
ROADS = []


def road_at(x, y):
    """(strength 0..1, kind)"""
    best, kind = 0.0, 0
    for pts, k, halfw in ROADS:
        for a, b in zip(pts, pts[1:]):
            vx, vy = b[0] - a[0], b[1] - a[1]; L2 = vx * vx + vy * vy
            if L2 < 1e-6: continue
            t = max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / L2))
            d = math.hypot(x - a[0] - vx * t, y - a[1] - vy * t) + fbm(x, y, 8, octaves=2, freq=0.4) * 0.8
            s = 1.0 - sm((d - halfw) / (halfw * 0.9))
            if s > best: best, kind = s, k
    return best, kind


def world_material():
    """R = biome along the ramp, G = road strength, B = road kind (0 grass path, .5 dirt, 1 mud). Snow and rock also by slope."""
    m, nt, out = new_mat("WorldGround")
    p = principled(nt, out, rough=0.94, spec=0.1)
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "map"; at.location = (-1600, 300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1400, 300); nt.links.new(at.outputs["Color"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-1200, 300)
    stops = [(0.00, (0.30, 0.27, 0.18)), (0.14, (0.52, 0.42, 0.22)), (0.28, (0.30, 0.30, 0.10)), (0.42, (0.10, 0.24, 0.05)),
             (0.56, (0.05, 0.14, 0.03)), (0.70, (0.16, 0.15, 0.14)), (0.84, (0.05, 0.045, 0.045)), (1.00, (0.70, 0.74, 0.80))]
    els = ramp.color_ramp.elements; els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1); els[1].position, els[1].color = 1.0, (*stops[-1][1], 1)
    for pos, c in stops[1:-1]: e = els.new(pos); e.color = (*c, 1)
    nt.links.new(sep.outputs["X"], ramp.inputs["Fac"])
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-1600, -200)
    n = noise_node(nt, co.outputs["Object"], 0.6, 10.0, 0.62, (-1400, -200)); v = maprange(nt, n.outputs["Fac"], 0.32, 0.68, 0.72, 1.24, (-1200, -200))
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.location = (-950, 200); mul.blend_type = "MULTIPLY"; mul.inputs["Fac"].default_value = 1
    nt.links.new(ramp.outputs["Color"], mul.inputs["Color1"]); nt.links.new(v.outputs["Result"], mul.inputs["Color2"])
    # roads: three tones picked by B, applied by G
    rk = nt.nodes.new("ShaderNodeValToRGB"); rk.location = (-1200, 700); e = rk.color_ramp.elements
    e[0].position, e[0].color = 0.0, (0.22, 0.22, 0.09, 1)                # grass path: worn pale straw
    mid = e.new(0.5); mid.color = (0.26, 0.19, 0.12, 1)                   # dirt road
    e[1].position, e[1].color = 1.0, (0.10, 0.07, 0.045, 1)               # mud
    nt.links.new(sep.outputs["Z"], rk.inputs["Fac"])
    rs = maprange(nt, sep.outputs["Y"], 0.25, 0.75, 0.0, 1.0, (-950, 700))
    road = nt.nodes.new("ShaderNodeMixRGB"); road.location = (-700, 300)
    nt.links.new(rs.outputs["Result"], road.inputs["Fac"]); nt.links.new(mul.outputs["Color"], road.inputs["Color1"]); nt.links.new(rk.outputs["Color"], road.inputs["Color2"])
    # steep faces go rock (unless snow)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1600, -600); nz = nt.nodes.new("ShaderNodeSeparateXYZ"); nz.location = (-1400, -600)
    nt.links.new(geo.outputs["Normal"], nz.inputs[0]); steep = maprange(nt, nz.outputs["Z"], 0.88, 0.60, 0.0, 1.0, (-1200, -600))
    rock = nt.nodes.new("ShaderNodeMixRGB"); rock.location = (-450, 300); rock.inputs["Color2"].default_value = (0.13, 0.125, 0.12, 1)
    snowy = maprange(nt, sep.outputs["X"], 0.9, 1.0, 1.0, 0.0, (-1200, -800))
    sf = math_node(nt, "MULTIPLY", steep.outputs["Result"], snowy.outputs["Result"], loc=(-950, -700))
    nt.links.new(sf.outputs[0], rock.inputs["Fac"]); nt.links.new(road.outputs["Color"], rock.inputs["Color1"])
    nt.links.new(rock.outputs["Color"], p.inputs["Base Color"])
    bn = noise_node(nt, co.outputs["Object"], 30.0, 12.0, 0.7, (-950, -900)); bmp = nt.nodes.new("ShaderNodeBump"); bmp.location = (-200, -300)
    bmp.inputs["Strength"].default_value = 0.35; bmp.inputs["Distance"].default_value = 0.08
    nt.links.new(bn.outputs["Fac"], bmp.inputs["Height"]); nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    return m


def emissive(name, rgb, strength):
    m, nt, out = new_mat(name); e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0]); m.use_fake_user = True; return m


def flat(name, rgb, rough=0.9):
    m, nt, out = new_mat(name); principled(nt, out, base=(*rgb, 1), rough=rough, spec=0.2); m.use_fake_user = True; return m


MAT = {"lava": emissive("WLava", (1.0, 0.28, 0.03), 18.0), "coal": flat("WCoal", (0.03, 0.03, 0.035), 0.55), "uranium": emissive("WUranium", (0.55, 1.0, 0.25), 3.0),
       "oil": flat("WOil", (0.02, 0.02, 0.025), 0.08), "salt": flat("WSalt", (0.85, 0.86, 0.88), 0.9), "derrick": flat("WDerrick", (0.30, 0.20, 0.10), 0.85),
       "obsidian": flat("WObsidian", (0.05, 0.05, 0.07), 0.25), "fish": flat("WFish", (0.55, 0.62, 0.68), 0.35), "ripple": flat("WRipple", (0.22, 0.34, 0.40), 0.95)}


# ============================================================================ the library
lib = MG.AssetLibrary(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"))
LIB = {"hall": "base/hall/models/hall.blend", "hut_a": "base/huts/models/hut_a.blend", "hut_b": "base/huts/models/hut_b.blend", "hut_c": "base/huts/models/hut_c.blend",
       "hut_d": "base/huts/models/hut_d.blend", "hut_e": "base/huts/models/hut_e.blend", "stabbur": "base/outbuildings/models/stabbur.blend",
       "forge": "base/outbuildings/models/forge.blend", "stable": "base/outbuildings/models/stable.blend", "well": "base/outbuildings/models/well.blend",
       "boathouse": "base/outbuildings/models/boathouse.blend", "tower_a": "base/towers/models/tower_a.blend", "tower_b": "base/towers/models/tower_b.blend",
       "tower_c": "base/towers/models/tower_c.blend", "node_wood": "base/starter/models/node_wood.blend", "node_stone": "base/starter/models/node_stone.blend",
       "node_iron": "base/starter/models/node_iron.blend", "node_food": "base/starter/models/node_food.blend",
       "swordsman": "base/troops/models/swordsman.blend", "archer": "base/troops/models/archer.blend", "spearman": "base/troops/models/spearman.blend",
       "horseman": "base/troops/models/horseman.blend", "standard": "base/troops/models/standard.blend",
       "runehall": os.path.join(REPO, "blender/base/age1_demo/models/runehall.blend"), "muster": os.path.join(REPO, "blender/base/age1_demo/models/muster.blend"),
       "farm": os.path.join(REPO, "blender/base/age1_demo/models/farm.blend"), "citizen": os.path.join(REPO, "blender/base/citizen/models/citizen.blend")}
for k, p in LIB.items(): lib.load(k, p)
print(f"LOADED {len(LIB)} assets; materials {len(D.materials)}")

# ============================================================================ siting (before the mesh)
sites = []       # (key, x, y, yaw)


def dry_flat(x, y, r):
    """Every point of the footprint above the waterline and the site not too steep -- the lesson of the house in the lake."""
    return all(raw_h(x + math.cos(a) * r, y + math.sin(a) * r) > SEA + 1.2 for a in [k * math.pi / 4 for k in range(8)]) and raw_h(x, y) > SEA + 1.5 and slope(x, y) < 0.22


def site(key, x, y, yaw=None, pad=None):
    """Place near (x, y): the wish is tried first, then rings outward until the footprint is dry and flat."""
    hx, hy, r = lib.footprint(key); pr = pad or max(4.0, r * 0.9)
    best = None
    for ring in range(0, 12):
        for k in range(1 if ring == 0 else 8):
            a = k * math.pi / 4; px, py = x + math.cos(a) * ring * 3.0, y + math.sin(a) * ring * 3.0
            if dry_flat(px, py, max(hx, hy) + 1.0) and all(math.hypot(px - sx, py - sy) > pr + sr + 1.5 for (sx, sy, sr) in PADS): best = (px, py); break
        if best: break
    if best is None: print(f"[site] ! no dry flat ground near {key} at {x:.0f},{y:.0f}; placed anyway"); best = (x, y)
    elif best != (x, y): print(f"[site] {key} moved {math.hypot(best[0] - x, best[1] - y):.0f} m")
    x, y = best
    PADS.append((x, y, pr)); sites.append((key, x, y, rnd.uniform(0, math.tau) if yaw is None else yaw)); return (x, y)


# the village, on the grass, west of the lake
V = (-18.0, -4.0)
site("hall", V[0], V[1], 0.3, pad=10)
for k, (dx, dy) in zip(["hut_a", "hut_b", "hut_c", "hut_d", "hut_e"], [(-16, 10), (-14, -12), (8, 14), (-26, -2), (4, -18)]): site(k, V[0] + dx, V[1] + dy)
site("stabbur", V[0] - 4, V[1] + 16); site("forge", V[0] + 14, V[1] + 2); site("stable", V[0] - 24, V[1] - 16); site("well", V[0] + 2, V[1] - 8, pad=2.5)
site("runehall", V[0] + 20, V[1] - 14); site("muster", V[0] - 2, V[1] + 26)
for (dx, dy) in [(28, 12), (-38, 14), (-36, -30)]: site("farm", V[0] + dx, V[1] + dy, 0.0)
site("tower_a", V[0] + 34, V[1] + 30); site("tower_b", V[0] - 44, V[1] - 6); site("tower_c", 30.0, -40.0)
# a second hamlet on the dry steppe, east
H2 = (78.0, -6.0)
site("hut_b", H2[0], H2[1]); site("hut_d", H2[0] + 12, H2[1] + 8); site("farm", H2[0] - 6, H2[1] + 16, 0.4); site("well", H2[0] + 6, H2[1] - 6, pad=2.5)
# the boathouse on the coast
bx = -40.0; by = COAST_Y(bx) + 4.0; site("boathouse", bx, by, math.pi / 2, pad=6)

# roads
MINE = (-62.0, 40.0)
ROADS.append(([V, (V[0] + 12, V[1] + 24), (-40, 34), MINE], 1, 1.6))                                    # dirt road to the mine
ROADS.append(([V, (-30, -30), (bx + 2, by - 2)], 1, 1.5))                                                 # dirt road to the coast
ROADS.append(([(V[0] + 16, V[1] - 2), (36, -12), (58, -8), H2], 1, 1.4))                                  # dirt road east, past the lake
ROADS.append(([(20, -20), (30, -24), (42, -22), (50, -16)], 2, 1.8))                                       # MUD through the marsh south of the lake
for (px, py) in [(-8, 22), (-36, 8), (2, 10)]: ROADS.append(([V, (px, py)], 0, 0.7))                     # grass paths to the berries
for k, x, y, yaw in sites:
    if k.startswith("hut") or k in ("stabbur", "forge", "stable", "well", "runehall", "muster") and math.hypot(x - V[0], y - V[1]) < 40:
        ROADS.append(([V, (x, y)], 0, 0.55))

# ============================================================================ terrain mesh
world = Model("World")
res = 1.6; nx, ny = int(W / res), int(Dp / res)
bm = bmesh.new()
grid = [[bm.verts.new((-W / 2 + i * res, -Dp / 2 + j * res, height(-W / 2 + i * res, -Dp / 2 + j * res))) for i in range(nx + 1)] for j in range(ny + 1)]
for j in range(ny):
    for i in range(nx): bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
# FLOAT colour, not byte: a byte colour attribute is stored sRGB-encoded, so a biome index of 0.42 (grass) came back as 0.15
# (desert sand) and the whole grassland rendered as beach. 0 and 1 survive that; anything in between does not.
col = bm.loops.layers.float_color.new("map")
for f in bm.faces:
    for l in f.loops:
        v = l.vert.co; rs, rk = road_at(v.x, v.y); l[col] = (biome(v.x, v.y), rs, rk * 0.5, 1.0)
ground = obj_from_bm(world, "Ground", bm, world_material(), bevel=0.0, smooth=True)
# water: one plane at sea level covers the sea and the lake basin
wb = bmesh.new(); bm_box(wb, W + 40, Dp + 40, 0.06, (0, 0, SEA - 0.03)); obj_from_bm(world, "Water", wb, TK["water"], bevel=0.0)
# lava lake in the crater, and a glow
lb = bmesh.new(); bm_cyl(lb, 7.5, 0.3, 24, (0, 0, 0)); obj_from_bm(world, "Lava", lb, MAT["lava"], bevel=0.0, loc=(VOLCANO[0], VOLCANO[1], raw_h(*VOLCANO) + 0.4))
print(f"TERRAIN {nx}x{ny}", flush=True)

# ============================================================================ prototypes: every scatter kind built ONCE, instanced many
import protos as P
t_protos = time.time()
PROTO = {}


def proto(key, mats, build, *a, **kw):
    bm = bmesh.new(); build(bm, *a, **kw); o = P.make_object(f"proto_{key}", bm, mats)
    lib.register(key, [o]); lib.offset[key] = Vector((0, 0, 0)); PROTO.setdefault(key.split(":")[0], []).append(key)


for i in range(4): proto(f"fir:{i}", [TK["bark"], TK["needle_dark"]], P.fir, 6.5, rnd.randint(4, 6), rnd)
for i in range(2): proto(f"firlight:{i}", [TK["bark"], TK["needle"]], P.fir, 6.5, rnd.randint(4, 6), rnd)
for i in range(2): proto(f"firsnow:{i}", [TK["bark"], TK["needle_snow"]], P.fir, 5.5, 5, rnd)
for i in range(2): proto(f"mfir:{i}", [TK["bark"], TK["needle_dark"]], P.fir, 5.5, 5, rnd)
for i, leaf in enumerate(["leaf_green", "leaf_green", "leaf_green", "leaf_lime", "leaf_autumn", "leaf_autumn", "leaf_gold"]): proto(f"broad:{i}", [TK["bark"], TK[leaf]], P.broadleaf, 5.5, 8, rnd)
for i in range(3): proto(f"bare:{i}", [TK["bark"]], P.bare, 5.0, rnd.randint(4, 6), rnd)
for i in range(3): proto(f"bush:{i}", [TK["leafy"]], P.bush, 1.0, rnd)
for i in range(3): proto(f"rock:{i}", [TK["rock"]], P.boulder, rnd, flat=i == 2)
for i in range(2): proto(f"rocksnow:{i}", [TK["rock_snow"]], P.boulder, rnd)
for i in range(2): proto(f"rocksand:{i}", [TK["sand"]], P.boulder, rnd, flat=True)
for i in range(2): proto(f"obsidian:{i}", [MAT["obsidian"]], P.boulder, rnd)
for i in range(2): proto(f"coal:{i}", [MAT["coal"]], P.boulder, rnd, flat=i == 0)
for i in range(2): proto(f"uran:{i}", [MAT["uranium"]], P.boulder, rnd)
print(f"PROTOS {sum(len(v) for v in PROTO.values())} kinds in {time.time() - t_protos:.1f} s", flush=True)

# ============================================================================ placements
PLACED = []      # {kind, x, y, objs, name} -- everything the review checks
ids = {}
n = {}


def put(kind, key, x, y, dz, s, tag=None, yaw=None):
    """Instance a prototype or a library asset at (x, y) on the ground. `tag` is the name prefix export_nature reads (tree, rock, ...)."""
    tag = tag or kind; i = ids.get(tag, 0); ids[tag] = i + 1
    objs = lib.place(key, (x, y, height(x, y) + dz), rot_z=rnd.uniform(0, math.tau) if yaw is None else yaw, scale=s, name=f"{tag}{i}")
    PLACED.append({"kind": kind, "x": x, "y": y, "objs": objs, "name": f"{tag}{i}"}); n[kind] = n.get(kind, 0) + 1
    return objs


def pick(group): return rnd.choice(PROTO[group])


for key, x, y, yaw in sites:
    objs = lib.place(key, (x, y, height(x, y)), rot_z=yaw, name=f"{key}@{int(x)},{int(y)}")
    PLACED.append({"kind": "building", "x": x, "y": y, "objs": objs, "name": f"{key}@{int(x)},{int(y)}"})
print(f"SITES {len(sites)}", flush=True)
res_m = Model("Resources")


def clear(x, y, extra=0.0):
    return all(math.hypot(x - sx, y - sy) > r + 2.0 + extra for (sx, sy, r) in PADS) and road_at(x, y)[0] < 0.3


def forest_density(x, y):
    R = region(x, y); v = fbm(x, y, 11, octaves=3, freq=0.025) + 0.5
    return (0.12 + 0.88 * R["forest"]) * max(0.0, min(1.0, (v - 0.40) * 3.0)) * (1 - R["desert"]) * (1 - R["volc"]) * (1 - R["sea"])


t_scatter = time.time()
for _ in range(int(os.environ.get("TRIES", 17000))):                 # ~900 trees at the current density; instancing makes tries cheap
    x, y = rnd.uniform(-W / 2 + 3, W / 2 - 3), rnd.uniform(-Dp / 2 + 3, Dp / 2 - 3)
    h = raw_h(x, y); R = region(x, y); s = slope(x, y)
    if h < SEA + 0.8 or not clear(x, y): continue
    r = rnd.random()
    if R["mount"] > 0.3 and h > 12:
        if r < 0.10 and s > 0.25: sz = rnd.uniform(0.8, 2.6); put("rock", pick("rocksnow" if h > 24 else "rock"), x, y, -0.15 * sz, sz)
        elif r < 0.16 and h < 20 and s < 0.5: put("tree", pick("firsnow" if h > 16 else "mfir"), x, y, -0.2, rnd.uniform(0.73, 1.27))
        continue
    if R["volc"] > 0.3:
        if r < 0.08: sz = rnd.uniform(0.6, 2.0); put("rock", pick("obsidian"), x, y, -0.15 * sz, sz)
        elif r < 0.10: put("dead", pick("bare"), x, y, 0.0, rnd.uniform(0.8, 1.2), tag="tree")
        continue
    if R["desert"] > 0.5:
        if r < 0.02: sz = rnd.uniform(0.5, 1.6); put("rock", pick("rocksand"), x, y, -0.15 * sz, sz)
        elif r < 0.03: put("dead", pick("bare"), x, y, 0.0, rnd.uniform(0.6, 1.0), tag="tree")
        continue
    fd = forest_density(x, y)
    if r < 0.55 * fd and s < 0.45:
        if rnd.random() < 0.72: put("tree", pick("fir" if rnd.random() < 0.6 else "firlight"), x, y, -0.15, rnd.uniform(0.77, 1.31))
        else: put("tree", pick("broad"), x, y, -0.15, rnd.uniform(0.82, 1.18))
    elif r < 0.55 * fd + 0.012: put("bush", pick("bush"), x, y, -0.1, rnd.uniform(0.6, 1.1))
    elif r < 0.55 * fd + 0.02 and s > 0.2: sz = rnd.uniform(0.5, 1.4); put("rock", pick("rock"), x, y, -0.15 * sz, sz)
print(f"SCATTER {time.time() - t_scatter:.1f} s", flush=True)


# ---- resources, each where you would look for it
def node(key, x, y, kind, r=2.2):
    """A resource node near (x, y): jittered until it stands clear of every pad and every other node (berries once grew in
    the stable yard and on top of each other)."""
    for k in range(24):
        px, py = (x, y) if k == 0 else (x + rnd.gauss(0, 4.0 + k * 0.3), y + rnd.gauss(0, 4.0 + k * 0.3))
        if raw_h(px, py) > SEA + 1.0 and all(math.hypot(px - sx, py - sy) > r + sr + 1.0 for (sx, sy, sr) in PADS) and road_at(px, py)[0] < 0.3: break
    else: print(f"[node] ! no clear ground for {kind} near {x:.0f},{y:.0f}")
    PADS.append((px, py, r)); put(kind, key, px, py, 0.0, 1.0)


for (x, y) in [(-8, 22), (-36, 8), (2, 10), (-58, -12), (40, 14), (62, -22), (90, 12)]:         # berries near the village and the hamlet
    for k in range(3): node("node_food", x, y, "berry")
for (x, y) in [MINE, (-70, 26), (-50, 52), (12, 46)]:                                             # stone and iron at the mountain foot
    for k in range(2): node("node_stone", x, y, "stone")
    for k in range(2): node("node_iron", x, y, "iron")
for (x, y) in [(-78, 34), (-104, 40), (-56, 66)]:                                                 # coal seams: black rock clusters, higher up
    for k in range(6): sz = rnd.uniform(0.5, 1.3); put("coal", pick("coal"), x + rnd.gauss(0, 2.5), y + rnd.gauss(0, 2.5), -0.15 * sz, sz)
for (x, y) in [(64, 74), (110, 46), (84, 30)]:                                                    # uranium in the badlands: faintly glowing green rock
    for k in range(5): sz = rnd.uniform(0.4, 1.0); put("uran", pick("uran"), x + rnd.gauss(0, 2.0), y + rnd.gauss(0, 2.0), -0.15 * sz, sz)
for (x, y) in [(70, -60), (96, -44), (112, -70)]:                                                 # oil in the desert: a black seep and a timber derrick
    z = height(x, y); PADS.append((x, y, 6.0)); i = ids.get("oil", 0); ids["oil"] = i + 1
    ob = bmesh.new(); bm_cyl(ob, rnd.uniform(3.0, 4.5), 0.1, 18, (0, 0, 0.05)); objs = [obj_from_bm(res_m, f"oil{i}", ob, MAT["oil"], bevel=0.0, loc=(x, y, z))]
    top = Vector((x + 5.5, y, z + 9.0))
    for k in range(4):
        a = k * math.tau / 4 + 0.4; objs.append(beam_between(res_m, f"derrick{i}_{k}", (x + 5.5 + math.cos(a) * 2.6, y + math.sin(a) * 2.6, z), top, 0.22, 0.22, MAT["derrick"], bevel=0.0))
    for zz in (3.0, 6.0):
        for k in range(4):
            a0 = k * math.tau / 4 + 0.4; a1 = a0 + math.tau / 4; rr = 2.6 * (1 - zz / 9.0)
            objs.append(beam_between(res_m, f"derrick{i}_r{k}{int(zz)}", (x + 5.5 + math.cos(a0) * rr, y + math.sin(a0) * rr, z + zz), (x + 5.5 + math.cos(a1) * rr, y + math.sin(a1) * rr, z + zz), 0.14, 0.14, MAT["derrick"], bevel=0.0))
    PLACED.append({"kind": "oil", "x": x, "y": y, "objs": objs, "name": f"oil{i}"}); n["oil"] = n.get("oil", 0) + 1
sb = bmesh.new(); bm_cyl(sb, 14.0, 0.12, 24, (0, 0, 0.06)); salt = obj_from_bm(res_m, "SaltFlat", sb, MAT["salt"], bevel=0.0, loc=(118, -36, height(118, -36) + 0.02))   # a salt flat, well inside the desert
PLACED.append({"kind": "salt", "x": 118, "y": -36, "objs": [salt], "name": "SaltFlat"}); n["salt"] = 1
for (x, y) in [(-60, -80), (-20, -84), (10, -78), (LAKE[0] + 3, LAKE[1] - 2), (LAKE[0] - 5, LAKE[1] + 3)]:                            # fish: shoals in the sea and the lake
    for k in range(2):
        i = ids.get("shoal", 0); ids["shoal"] = i + 1
        for _t in range(30):                                                                  # in the WATER, not on the beach
            sx, sy = x + rnd.gauss(0, 3), y + rnd.gauss(0, 3)
            if raw_h(sx, sy) < SEA - 0.6: break
        fb = bmesh.new(); bm_cyl(fb, rnd.uniform(0.9, 1.4), 0.04, 14, (0, 0, 0)); o = obj_from_bm(res_m, f"shoal{i}", fb, MAT["ripple"], bevel=0.0, loc=(sx, sy, SEA + 0.02))
        objs = [o]
        for j in range(5):
            f = bmesh.new(); bm_box(f, 0.5, 0.12, 0.12, (rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)); fo = obj_from_bm(res_m, f"fish{i}_{j}", f, MAT["fish"], bevel=0.0, loc=(o.location.x, o.location.y, SEA - 0.25)); fo.rotation_euler.z = rnd.uniform(0, math.tau); objs.append(fo)
        PLACED.append({"kind": "shoal", "x": o.location.x, "y": o.location.y, "objs": objs, "name": f"shoal{i}"}); n["shoal"] = n.get("shoal", 0) + 1
# people: a few villagers and a patrol
for i, (k, x, y) in enumerate([("citizen", V[0] + 6, V[1] + 4), ("citizen", V[0] - 10, V[1] + 6), ("citizen", V[0] + 4, V[1] - 12), ("citizen", H2[0] + 4, H2[1] + 4),
                               ("swordsman", V[0] + 20, V[1] + 20), ("spearman", V[0] + 22, V[1] + 22), ("archer", V[0] + 24, V[1] + 19), ("standard", V[0] + 22, V[1] + 25), ("horseman", -50, -34)]):
    put("people", k, x, y, 0.0, 1.4, tag=f"p{i}_{k}")
print("PLACED " + " ".join(f"{k}={v}" for k, v in sorted(n.items())), flush=True)

# ---- grass on grass, straw on the steppe
GRASS = grass_material(new_mat, principled, maprange, green=(0.06, 0.15, 0.03, 1), olive=(0.13, 0.16, 0.04, 1), straw=(0.24, 0.20, 0.07, 1))
tufts = [make_tuft_mesh(f"Tuft{i}", rnd.randint(34, 52), 3000 + i, GRASS, h_range=(0.15, 0.45), w_range=(0.006, 0.013)) for i in range(6)]
nt_ = 0
for _ in range(60000):
    x, y = rnd.uniform(-W / 2 + 1, W / 2 - 1), rnd.uniform(-Dp / 2 + 1, Dp / 2 - 1)
    b = biome(x, y); R = region(x, y)
    if raw_h(x, y) < SEA + 0.8 or b < 0.24 or b > 0.66 or R["volc"] > 0.4 or road_at(x, y)[0] > 0.5: continue
    if not all(math.hypot(x - sx, y - sy) > r * 0.6 for (sx, sy, r) in PADS[:40]): continue
    o = D.objects.new(f"Tuft_{nt_:05d}", rnd.choice(tufts)); C.scene.collection.objects.link(o)
    o.location = (x, y, height(x, y) - 0.04); s_ = rnd.uniform(1.1, 2.4); o.scale = (s_, s_, s_ * rnd.uniform(0.9, 1.7)); o.rotation_euler = (0, 0, rnd.uniform(0, math.tau)); nt_ += 1
print(f"GRASS {nt_}", flush=True)

# ---- review before pixels: worldreview writes renders/REVIEW.md; a FAIL raises AFTER the renders below so the pictures exist
import worldreview
CTX = type("Ctx", (), {"region": staticmethod(region), "height": staticmethod(height), "raw_h": staticmethod(raw_h), "dry_flat": staticmethod(dry_flat), "SEA": SEA, "W": W, "D": Dp})
REVIEW_OK = worldreview.run(PLACED, CTX, os.path.join(SCENE_DIR, "renders"), time.time() - T0, os.environ.get("BLENDER_GPU", "METAL"))

# ============================================================================ light, cameras, render
daylight(sun_energy=2.6, sky_strength=0.36, elevation=48.0, rotation=205.0)
for o in D.objects:
    if o.type == "LIGHT" and o.data.type == "SUN": o.data.angle = math.radians(4.0)
hero_d = D.cameras.new("Hero"); hero_d.lens = 35; hero = D.objects.new("Hero", hero_d); C.scene.collection.objects.link(hero)
hero.location = (10, -215, 150); hero.rotation_euler = (math.radians(50), 0, math.radians(-4))
plan_d = D.cameras.new("Plan"); plan_d.type = "ORTHO"; plan_d.ortho_scale = W + 10; plan = D.objects.new("Plan", plan_d); C.scene.collection.objects.link(plan)
plan.location = (0, 0, 300); plan.rotation_euler = (0, 0, 0)
out = os.path.join(SCENE_DIR, "renders", "world_")
final = QUALITY == "final"
render_settings(scene, out, res=(1920, 1200) if final else (1200, 750), samples=256 if final else 48, exposure=-1.6)
scene.view_settings.look = "AgX - Medium High Contrast"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENE_DIR, "map_world.blend"))
print("BUILT", len(D.objects), "objects")
vil_d = D.cameras.new("Village"); vil_d.lens = 40; vil = D.objects.new("Village", vil_d); C.scene.collection.objects.link(vil)
vil.location = (V[0] + 8, V[1] - 62, 46); vil.rotation_euler = (math.radians(50), 0, math.radians(6))
for cam, tag in ((hero, "hero"), (plan, "plan"), (vil, "village")):
    scene.camera = cam; scene.render.filepath = out + tag + ("_final" if final else "_preview") + ".png"
    scene.render.resolution_x, scene.render.resolution_y = ((2600, 1900) if final else (1300, 950)) if tag == "plan" else ((1920, 1200) if final else (1200, 750))
    bpy.ops.render.render(write_still=True); print("RENDERED", scene.render.filepath)
print(f"BUILD+RENDER {time.time() - T0:.0f} s")
if not REVIEW_OK: raise RuntimeError("REVIEW FAILED -- see renders/REVIEW.md")
