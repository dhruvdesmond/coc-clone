"""THE WORLD MAP, in Blender only, built from what we already have (PENDING B12, B21) -- v3: the Standard 420 x 420 m land.

One continuous land in the library's own style: the village in the west-centre on the river's east bank, and around it every
resource the game will need, each in the biome where you would look for it (docs/14-world.md §2).

    NW  MOUNTAINS: two ridges, snow, cliffs at the foot     stone, iron, coal; the MINING CAMP
    NE  VOLCANO with a crater rim, badlands, obsidian       uranium
    W   FOREST                                              trees, (game)
    E   DRY STEPPE                                          farmland, the second hamlet
    centre  GRASSLAND                                       the VILLAGE, farms, berries, a LAKE with fish, a marsh south of it
    S   COAST + SEA                                         fish shoals, the FISHING HAMLET with a pier
    SE  DESERT                                              oil seeps + derricks, a salt flat, dunes to the beach
    a RIVER from the mountain to the sea, two FORDS, one BRIDGE (the doc 08 "river basin" classic)

Roads: grass PATHS, DIRT roads between the four settlements (over the bridge, through a ford), a MUDDY road through the marsh,
COBBLES in the village. All written into the ground's colour attribute so they follow the terrain.

Every tree, bush and rock is a prototype from protos.py instanced with obj.copy(); everything placed is recorded in PLACED
and checked by worldreview.py, which writes renders/REVIEW.md and fails the batch (after the renders) on a FAIL.

    blender -b --factory-startup --python-exit-code 1 --python blender/base/map_world/build.py    # preview: hero + plan + village
    REGIONS=1 …                                                                                   # + the 12 region crops
    QUALITY=final REGIONS=1 …                                                                     # 4K finals + crops (the 4090 job)
    TRIES=20000 GRASS=20000 …                                                                     # a quick, sparse build
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
REGIONS = os.environ.get("REGIONS", "1" if QUALITY == "final" else "0") == "1"
W, Dp = 420.0, 420.0
SEA = 0.0


# ============================================================================ the land
def fbm(x, y, s=0, **kw): return T.fbm(x, y, seed=SEED + s, **kw)
def sm(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def falloff(x, y, cx, cy, r, soft): return 1.0 - sm((math.hypot(x - cx, y - cy) - r) / soft)


def seg_dist(x, y, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]; L2 = vx * vx + vy * vy
    if L2 < 1e-6: return math.hypot(x - a[0], y - a[1])
    t = max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / L2))
    return math.hypot(x - a[0] - vx * t, y - a[1] - vy * t)


def poly_dist(x, y, pts): return min(seg_dist(x, y, a, b) for a, b in zip(pts, pts[1:]))


VOLCANO = (140.0, 120.0)        # NE
MOUNT = (-140.0, 105.0)         # NW, the massif's centre
RIDGES = [((-200.0, 60.0), (-96.0, 168.0)), ((-178.0, 158.0), (-104.0, 62.0))]      # two ridge lines through the massif
LAKE = (62.0, 4.0)              # centre-east, clear of the village
COAST_Y = lambda x: -150.0 + fbm(x, 0.0, 9, octaves=2, freq=0.012) * 22.0           # the shoreline along the south
RIVER = [(-112.0, 58.0), (-100.0, 40.0), (-78.0, 16.0), (-62.0, -18.0), (-48.0, -56.0), (-40.0, -94.0), (-30.0, -128.0), (-22.0, -176.0)]
BRIDGE = RIVER[2]                                # the road to the mining camp crosses here
FORDS = [RIVER[4], RIVER[6]]                     # shallow gravel bars: the road to the fishing hamlet crosses the first


def region(x, y):
    """Which world we are in, as soft weights that sum to about 1."""
    r = {}
    r["mount"] = max(falloff(x, y, *MOUNT, 46.0, 42.0), *[1.0 - sm((seg_dist(x, y, a, b) - 16.0) / 30.0) for a, b in RIDGES])
    r["volc"] = falloff(x, y, *VOLCANO, 34.0, 30.0)
    r["desert"] = sm((x - 55.0) / 50.0) * sm((-y - 30.0) / 45.0)
    r["forest"] = max(sm((-x - 55.0) / 40.0) * sm((y + 115.0) / 45.0) * sm((70.0 - y) / 40.0), falloff(x, y, 40.0, 100.0, 34.0, 26.0)) * (1.0 - r["mount"]) * (1.0 - r["volc"])
    r["sea"] = sm((COAST_Y(x) - y) / 12.0) * (1.0 - r["desert"] * 0.6)
    r["grass"] = max(0.0, 1.0 - sum(r.values()))
    return r


def raw_h(x, y):
    R = region(x, y)
    base = 2.2 + fbm(x, y, 1, octaves=4, freq=0.009) * 3.4 + fbm(x, y, 2, octaves=2, freq=0.045) * 0.8
    # mountains: a massif plus two ridge lines with peaks, up to ~40 m
    dm = math.hypot(x - MOUNT[0], y - MOUNT[1])
    ridge = max(sm(1.0 - seg_dist(x, y, a, b) / 26.0) for a, b in RIDGES)
    mount = R["mount"] * (8.0 + 20.0 * sm(1.0 - dm / 60.0) + 16.0 * ridge + abs(fbm(x, y, 3, octaves=4, freq=0.03)) * 12.0 * (0.5 + ridge))
    # volcano: a cone with a crater and a raised rim
    dv = math.hypot(x - VOLCANO[0], y - VOLCANO[1])
    cone = 30.0 * sm(1.0 - dv / 36.0) - 11.0 * sm(1.0 - dv / 9.0) + 3.5 * sm(1.0 - abs(dv - 10.0) / 4.0)
    volc = R["volc"] * cone + R["volc"] * fbm(x, y, 4, octaves=3, freq=0.08) * 1.6
    # desert: long low dunes
    dunes = R["desert"] * (1.5 + 1.8 * math.sin(x * 0.11 + y * 0.05 + fbm(x, y, 5, octaves=2, freq=0.02) * 3.0))
    # sea floor
    sea = -R["sea"] * (3.0 + 4.0 * sm((COAST_Y(x) - y) / 30.0))
    # lake basin
    lk = falloff(x, y, *LAKE, 20.0, 14.0)
    lake = -6.0 * lk * (0.6 + 0.4 * fbm(x, y, 6, octaves=2, freq=0.06))
    h = base + mount + volc + dunes + sea + lake
    if lk > 0.55: h = min(h, -1.5 - (lk - 0.55) * 6.0)                      # the lake core is always under water (an island once surfaced on its west side)
    # the river: a channel cut to a bed BELOW the sea level (the one water plane), gravel bars at the fords. It fades out inside
    # the mountain (a full-depth cut through 20 m of rock was a black gorge in the first render).
    d = poly_dist(x, y, RIVER)
    if d < 12.0:
        k = (1.0 - sm((d - 4.0) / 7.0)) * (1.0 - sm((R["mount"] - 0.25) / 0.35))
        ford = max(falloff(x, y, fx, fy, 4.0, 5.0) for fx, fy in FORDS)
        bed = -2.6 * (1.0 - ford) + 0.35 * ford
        if h > bed: h = h * (1.0 - k) + bed * k
    return h


PADS = []       # (x, y, r) flattened sites; only those registered BEFORE the terrain mesh is built flatten the ground
MESH_PADS = None   # frozen copy of PADS at mesh time -- pads added later (nodes, salt, rig) only keep things apart. Reviewing with
                   # the live list once "buried" rocks that the MESH had never raised.


def height(x, y):
    h = raw_h(x, y); w = 0.0; ph = h
    for (sx, sy, r) in (PADS if MESH_PADS is None else MESH_PADS):
        d = math.hypot(x - sx, y - sy); k = 1.0 - sm((d - r) / (r * 0.8))
        if k > w: w = k; ph = raw_h(sx, sy)
    return h * (1 - w) + ph * w


def slope(x, y, r=2.0):
    h = raw_h(x, y); return max(abs(raw_h(x + r, y) - h), abs(raw_h(x, y + r) - h)) / r


# biome index along one ramp so neighbours blend:  0 seabed/sand  .14 desert  .28 dry steppe  .42 grass  .50 marsh  .56 forest floor
#                                                  .70 rock  .84 volcanic ash  1.0 snow
def biome(x, y):
    R = region(x, y); h = raw_h(x, y)
    if R["sea"] > 0.5 or h < SEA + 0.6: return 0.02
    b = 0.42 + 0.14 * sm((fbm(x, y, 7, octaves=3, freq=0.03) + 0.2) * 2.0)           # grass -> forest floor by moisture
    b = b * (1 - R["forest"]) + 0.58 * R["forest"]
    b = b * (1 - R["desert"]) + (0.14 + 0.10 * sm((h - 2.0) / 3.0)) * R["desert"]
    if R["mount"] > 0.05:
        m = 0.70 + 0.30 * sm((h - 24.0) / 9.0)
        b = b * (1 - R["mount"]) + m * R["mount"]
    if R["volc"] > 0.05: b = b * (1 - R["volc"]) + 0.84 * R["volc"]
    if h < SEA + 1.6 and (R["sea"] > 0.1 or poly_dist(x, y, RIVER) < 12.0): b = min(b, 0.06 + 0.2 * (h - SEA))
    if falloff(x, y, LAKE[0], LAKE[1] - 34.0, 22.0, 14.0) > 0.4 and h < 4.0: b = min(b, 0.50)        # the marsh south of the lake
    if slope(x, y) > 0.55: b = max(b, 0.70) if b < 0.84 else b
    return max(0.0, min(1.0, b))


# ---- roads: (points, kind, half-width)  kind 0 = grass path, 1 = dirt road, 2 = muddy road, 3 = cobbles. Filled in after siting.
ROADS = []


def road_at(x, y):
    """(strength 0..1, kind)"""
    best, kind = 0.0, 0
    for pts, k, halfw in ROADS:
        for a, b in zip(pts, pts[1:]):
            d = seg_dist(x, y, a, b) + fbm(x, y, 8, octaves=2, freq=0.4) * 0.8
            s = 1.0 - sm((d - halfw) / (halfw * 0.9))
            if s > best: best, kind = s, k
    return best, kind


def world_material():
    """R = biome along the ramp, G = road strength, B = road kind / 3 (grass path, dirt, mud, cobbles). Snow and rock also by slope."""
    m, nt, out = new_mat("WorldGround")
    p = principled(nt, out, rough=0.94, spec=0.1)
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "map"; at.location = (-1600, 300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1400, 300); nt.links.new(at.outputs["Color"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-1200, 300)
    # the palette of docs/16-look.md §3: seabed, SAND (ochre), steppe (dry/worn), MEADOW CREST, marsh, MEADOW DIP, scree, ash, snow
    stops = [(0.00, (0.24, 0.20, 0.13)), (0.14, (0.62, 0.52, 0.34)), (0.28, (0.55, 0.47, 0.22)), (0.42, (0.42, 0.46, 0.12)),
             (0.50, (0.26, 0.34, 0.10)), (0.56, (0.20, 0.30, 0.08)), (0.70, (0.50, 0.48, 0.45)), (0.84, (0.16, 0.14, 0.13)), (1.00, (0.92, 0.94, 0.97))]
    els = ramp.color_ramp.elements; els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1); els[1].position, els[1].color = 1.0, (*stops[-1][1], 1)
    for pos, c in stops[1:-1]: e = els.new(pos); e.color = (*c, 1)
    nt.links.new(sep.outputs["X"], ramp.inputs["Fac"])
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-1600, -200)
    n = noise_node(nt, co.outputs["Object"], 0.6, 10.0, 0.62, (-1400, -200)); v = maprange(nt, n.outputs["Fac"], 0.32, 0.68, 0.72, 1.24, (-1200, -200))
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.location = (-950, 200); mul.blend_type = "MULTIPLY"; mul.inputs["Fac"].default_value = 1
    nt.links.new(ramp.outputs["Color"], mul.inputs["Color1"]); nt.links.new(v.outputs["Result"], mul.inputs["Color2"])
    # roads: four tones picked by B, applied by G
    # NOTE: color_ramp.elements re-sorts by position after every new(), so index by SORTED order at the end -- indexing e[1]
    # after two new() calls coloured the dirt stop and left the last stop at its default WHITE (the cobbled square rendered white).
    rk = nt.nodes.new("ShaderNodeValToRGB"); rk.location = (-1200, 700); e = rk.color_ramp.elements
    e.new(1 / 3); e.new(2 / 3)
    for el, pos, c in zip(sorted(e, key=lambda s: s.position), (0.0, 1 / 3, 2 / 3, 1.0),
                          [(0.55, 0.47, 0.22), (0.38, 0.27, 0.15), (0.16, 0.11, 0.07), (0.34, 0.33, 0.30)]):   # grass path (dry/worn), dirt, mud, cobbles -- docs/16-look.md §3
        el.position = pos; el.color = (*c, 1)
    nt.links.new(sep.outputs["Z"], rk.inputs["Fac"])
    rs = maprange(nt, sep.outputs["Y"], 0.25, 0.75, 0.0, 1.0, (-950, 700))
    road = nt.nodes.new("ShaderNodeMixRGB"); road.location = (-700, 300)
    nt.links.new(rs.outputs["Result"], road.inputs["Fac"]); nt.links.new(mul.outputs["Color"], road.inputs["Color1"]); nt.links.new(rk.outputs["Color"], road.inputs["Color2"])
    # steep faces go rock (unless snow)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1600, -600); nz = nt.nodes.new("ShaderNodeSeparateXYZ"); nz.location = (-1400, -600)
    nt.links.new(geo.outputs["Normal"], nz.inputs[0]); steep = maprange(nt, nz.outputs["Z"], 0.88, 0.60, 0.0, 1.0, (-1200, -600))
    rock = nt.nodes.new("ShaderNodeMixRGB"); rock.location = (-450, 300); rock.inputs["Color2"].default_value = (0.50, 0.48, 0.45, 1)
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
       "obsidian": flat("WObsidian", (0.05, 0.05, 0.07), 0.25), "fish": flat("WFish", (0.55, 0.62, 0.68), 0.35), "ripple": flat("WRipple", (0.22, 0.34, 0.40), 0.95),
       "timber": flat("WTimber", (0.32, 0.22, 0.12), 0.8), "stone": flat("WStone", (0.36, 0.35, 0.33), 0.9)}


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
    """Place near (x, y): the wish is tried first, then rings outward (to 60 m) until the footprint is dry and flat."""
    hx, hy, r = lib.footprint(key); pr = pad or max(4.0, r * 0.9)
    best = None
    for ring in range(0, 21):
        for k in range(1 if ring == 0 else 8):
            a = k * math.pi / 4; px, py = x + math.cos(a) * ring * 3.0, y + math.sin(a) * ring * 3.0
            if dry_flat(px, py, max(hx, hy) + 1.0) and all(math.hypot(px - sx, py - sy) > pr + sr + 1.5 for (sx, sy, sr) in PADS): best = (px, py); break
        if best: break
    if best is None: print(f"[site] ! no dry flat ground within 60 m of {key} at {x:.0f},{y:.0f}; placed anyway -- the review will fail it"); best = (x, y)
    elif best != (x, y): print(f"[site] {key} moved {math.hypot(best[0] - x, best[1] - y):.0f} m")
    x, y = best
    PADS.append((x, y, pr)); sites.append((key, x, y, rnd.uniform(0, math.tau) if yaw is None else yaw)); return (x, y)


# THE VILLAGE, on the grass, on the river's east bank, west of the lake
V = (-40.0, 10.0)
site("hall", V[0], V[1], 0.3, pad=10)
for k, (dx, dy) in zip(["hut_a", "hut_b", "hut_c", "hut_d", "hut_e"], [(-16, 10), (-14, -12), (8, 14), (-26, -2), (4, -18)]): site(k, V[0] + dx, V[1] + dy)
site("stabbur", V[0] - 4, V[1] + 16); site("forge", V[0] + 14, V[1] + 2); site("stable", V[0] - 24, V[1] - 16); site("well", V[0] + 2, V[1] - 8, pad=2.5)
site("runehall", V[0] + 20, V[1] - 14); site("muster", V[0] - 2, V[1] + 26)
for (dx, dy) in [(28, 12), (-38, 14), (-36, -30)]: site("farm", V[0] + dx, V[1] + dy, 0.0)
site("tower_a", V[0] + 34, V[1] + 30); site("tower_b", V[0] - 44, V[1] - 6); site("tower_c", 20.0, -40.0)
# the STEPPE HAMLET, east, beyond the lake
H2 = (130.0, -6.0)
site("hut_b", H2[0], H2[1]); site("hut_d", H2[0] + 12, H2[1] + 8); site("hut_e", H2[0] - 10, H2[1] - 10); site("farm", H2[0] - 6, H2[1] + 18, 0.4)
site("well", H2[0] + 6, H2[1] - 6, pad=2.5); site("stabbur", H2[0] + 16, H2[1] - 12)
# the FISHING HAMLET on the south coast: boathouse turned to the sea, a pier
H3 = (30.0, -134.0)
h3 = site("boathouse", H3[0], H3[1], math.pi / 2, pad=6); site("hut_a", H3[0] - 12, H3[1] + 8); site("hut_c", H3[0] + 12, H3[1] + 10); site("well", H3[0], H3[1] + 14, pad=2.5)
# the MINING CAMP at the mountain foot, across the river
H4 = (-76.0, 60.0)
h4 = site("forge", H4[0], H4[1]); site("hut_b", H4[0] + 12, H4[1] - 8); site("stabbur", H4[0] - 10, H4[1] - 10); site("tower_a", H4[0] + 4, H4[1] + 16)

# roads
FORD = FORDS[0]
ROADS.append(([V, (-58, 14), BRIDGE, (-90, 34), h4], 1, 1.6))                                           # dirt road west over the BRIDGE to the mining camp
ROADS.append(([V, (-32, -22), FORD, (-22, -88), h3], 1, 1.5))                                            # dirt road south through the FORD to the fishing hamlet
ROADS.append(([(V[0] + 16, V[1] - 2), (10, -10), (34, -22), (74, -34), (104, -18), H2], 1, 1.4))         # dirt road east, south of the lake, to the hamlet
ROADS.append(([(44, -30), (58, -38), (76, -40), (92, -32)], 2, 1.8))                                     # MUD through the marsh south of the lake
ROADS.append(([h3, (70, -112), (110, -118)], 1, 1.3))                                                    # the oil road along the coast
ROADS.append(([(V[0] - 8, V[1] - 4), (V[0] + 8, V[1] - 4), (V[0] + 8, V[1] + 6), (V[0] - 8, V[1] + 6), (V[0] - 8, V[1] - 4)], 3, 2.6))   # COBBLES round the hall
BERRIES = [(-24, 40), (-4, 24), (-84, -34), (98, 22), (152, -34), (46, -92), (-8, -100), (74, 62), (16, 40)]
for (px, py) in BERRIES[:3]: ROADS.append(([V, (px, py)], 0, 0.7))                                      # grass paths to the near berries
for k, x, y, yaw in sites:
    if (k.startswith("hut") or k in ("stabbur", "forge", "stable", "well", "runehall", "muster")) and math.hypot(x - V[0], y - V[1]) < 40:
        ROADS.append(([V, (x, y)], 0, 0.55))
    elif k.startswith("hut") and (math.hypot(x - H2[0], y - H2[1]) < 30 or math.hypot(x - H3[0], y - H3[1]) < 30 or math.hypot(x - H4[0], y - H4[1]) < 30):
        near = min((H2, H3, H4), key=lambda c: math.hypot(x - c[0], y - c[1])); ROADS.append(([near, (x, y)], 0, 0.55))

# ============================================================================ terrain mesh
world = Model("World")
res = 2.0; nx, ny = int(W / res), int(Dp / res)
bm = bmesh.new()
grid = [[bm.verts.new((-W / 2 + i * res, -Dp / 2 + j * res, height(-W / 2 + i * res, -Dp / 2 + j * res))) for i in range(nx + 1)] for j in range(ny + 1)]
for j in range(ny):
    for i in range(nx): bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
# FLOAT colour, not byte: a byte colour attribute is stored sRGB-encoded, so a biome index of 0.42 (grass) came back as 0.15
# (desert sand) and the whole grassland rendered as beach. 0 and 1 survive that; anything in between does not.
col = bm.loops.layers.float_color.new("map")
bm.verts.index_update()
vcol = {}                                                              # per VERTEX once, not per loop (4x fewer biome/road calls: 148 s -> ~40 s)
for v in bm.verts:
    rs, rk = road_at(v.co.x, v.co.y); vcol[v.index] = (biome(v.co.x, v.co.y), rs, rk / 3.0, 1.0)
for f in bm.faces:
    for l in f.loops: l[col] = vcol[l.vert.index]
MESH_PADS = list(PADS)
import ground as G                                                       # the v2 ground material (docs/16-look.md); world_material() above is v1, kept for reference
ground = obj_from_bm(world, "Terrain", bm, G.material(new_mat, principled, noise_node, math_node, maprange) if os.environ.get("GROUND", "2") == "2" else world_material(), bevel=0.0, smooth=True)
# water: one plane at sea level covers the sea, the lake basin and the river bed
wb = bmesh.new(); bm_box(wb, W + 40, Dp + 40, 0.06, (0, 0, SEA - 0.03)); obj_from_bm(world, "Sea", wb, TK["water"], bevel=0.0)
# lava lake in the crater, and a glow
lb = bmesh.new(); bm_cyl(lb, 8.0, 0.3, 24, (0, 0, 0)); obj_from_bm(world, "Lava", lb, MAT["lava"], bevel=0.0, loc=(VOLCANO[0], VOLCANO[1], raw_h(*VOLCANO) + 0.4))
print(f"TERRAIN {nx}x{ny} in {time.time() - T0:.0f} s", flush=True)

# ============================================================================ prototypes: every scatter kind built ONCE, instanced many
import protos as P
t_protos = time.time()
PROTO = {}


PZ = {}          # key -> (zmin, zmax) of the prototype mesh, so a rock can be sunk by a fraction of ITS height and always show


def proto(key, mats, build, *a, **kw):
    bm = bmesh.new(); build(bm, *a, **kw); o = P.make_object(f"proto_{key}", bm, mats)
    zs = [v.co.z for v in o.data.vertices]; PZ[key] = (min(zs), max(zs))
    lib.register(key, [o]); lib.offset[key] = Vector((0, 0, 0)); PROTO.setdefault(key.split(":")[0], []).append(key)


def rock(kind, key, x, y, s, k=0):
    """A rock-like prototype sunk so that 45 % of its height still shows (plus k steps for stacked cliff slabs)."""
    return put(kind, key, x, y, -0.55 * PZ[key][1] * s + k * 0.3, s)


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
for i in range(3): proto(f"cliff:{i}", [TK["rock"]], P.boulder, rnd, flat=True, facets=2)
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

# ---- the bridge: a timber deck on two stone abutments, square across the river at BRIDGE
bx, by = BRIDGE; rd = Vector((RIVER[3][0] - RIVER[1][0], RIVER[3][1] - RIVER[1][1], 0)).normalized(); across = Vector((-rd.y, rd.x, 0))
yaw_b = math.atan2(across.y, across.x); zb = max(raw_h(bx + across.x * 12, by + across.y * 12), raw_h(bx - across.x * 12, by - across.y * 12)) + 0.6
bridge = []
db = bmesh.new(); bm_box(db, 22.0, 3.6, 0.35, (0, 0, 0)); deck = obj_from_bm(res_m, "Bridge_Deck", db, MAT["timber"], bevel=0.0, loc=(bx, by, zb)); deck.rotation_euler.z = yaw_b; bridge.append(deck)
for side in (1, -1):
    ab = bmesh.new(); bm_box(ab, 3.0, 4.4, zb + 1.2, (0, 0, 0)); a = obj_from_bm(res_m, f"Bridge_Abut{side}", ab, MAT["stone"], bevel=0.0, loc=(bx + across.x * 10.5 * side, by + across.y * 10.5 * side, (zb - 0.4) / 2 - 0.6)); a.rotation_euler.z = yaw_b; bridge.append(a)
    rb = bmesh.new(); bm_box(rb, 22.0, 0.16, 0.9, (0, 0, 0)); r_ = obj_from_bm(res_m, f"Bridge_Rail{side}", rb, MAT["timber"], bevel=0.0, loc=(bx + rd.x * 1.7 * side, by + rd.y * 1.7 * side, zb + 0.6)); r_.rotation_euler.z = yaw_b; bridge.append(r_)
PADS.append((bx, by, 12.0)); PLACED.append({"kind": "bridge", "x": bx, "y": by, "objs": bridge, "name": "bridge"}); n["bridge"] = 1

# ---- the pier at the fishing hamlet: a deck out over the water on posts
px_, py_ = h3[0] + 10.0, COAST_Y(h3[0] + 10.0) + 3.0
pier = []
pb = bmesh.new(); bm_box(pb, 2.4, 16.0, 0.25, (0, 0, 0)); pd = obj_from_bm(res_m, "Pier_Deck", pb, MAT["timber"], bevel=0.0, loc=(px_, py_ - 6.0, SEA + 0.9)); pier.append(pd)
for k in range(5):
    for side in (1, -1):
        pp = bmesh.new(); bm_box(pp, 0.25, 0.25, 2.6, (0, 0, 0)); pier.append(obj_from_bm(res_m, f"Pier_Post{k}{side}", pp, MAT["timber"], bevel=0.0, loc=(px_ + side * 1.0, py_ - k * 3.6, SEA - 0.4)))
PADS.append((px_, py_ - 6.0, 6.0)); PLACED.append({"kind": "pier", "x": px_, "y": py_ - 6.0, "objs": pier, "name": "pier"}); n["pier"] = 1


def clear(x, y, extra=0.0):
    return all(math.hypot(x - sx, y - sy) > r + 2.0 + extra for (sx, sy, r) in PADS) and road_at(x, y)[0] < 0.3


def forest_density(x, y):
    R = region(x, y); v = fbm(x, y, 11, octaves=3, freq=0.025) + 0.5
    return (0.12 + 0.88 * R["forest"]) * max(0.0, min(1.0, (v - 0.40) * 3.0)) * (1 - R["desert"]) * (1 - R["volc"]) * (1 - R["sea"])


# ---- cliffs: clustered big slabs at the mountain foot (where the ore is) and obsidian at the volcano's
for (cx, cy, key, cnt) in [(-96, 52, "cliff", 9), (-70, 96, "cliff", 8), (-120, 22, "cliff", 7), (-52, 130, "cliff", 6), (-160, 40, "cliff", 8),
                           (108, 88, "obsidian", 7), (172, 150, "obsidian", 6), (118, 158, "obsidian", 6)]:
    for k in range(cnt):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 9.0); x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if raw_h(x, y) < SEA + 1.0 or not all(math.hypot(x - sx, y - sy) > r + 1.0 for (sx, sy, r) in PADS): continue
        rock("rock", pick(key), x, y, rnd.uniform(2.6, 5.0), k)

t_scatter = time.time()
for _ in range(int(os.environ.get("TRIES", 60000))):                 # ~1,800 trees at the current density; instancing makes tries cheap
    x, y = rnd.uniform(-W / 2 + 3, W / 2 - 3), rnd.uniform(-Dp / 2 + 3, Dp / 2 - 3)
    h = raw_h(x, y); R = region(x, y); s = slope(x, y)
    if h < SEA + 0.8 or not clear(x, y): continue
    r = rnd.random()
    if R["mount"] > 0.3 and h > 12:
        if r < 0.10 and s > 0.25: rock("rock", pick("rocksnow" if h > 26 else "rock"), x, y, rnd.uniform(0.8, 2.6))
        elif r < 0.16 and h < 22 and s < 0.5: put("tree", pick("firsnow" if h > 17 else "mfir"), x, y, -0.2, rnd.uniform(0.73, 1.27))
        continue
    if R["volc"] > 0.3:
        if r < 0.08: rock("rock", pick("obsidian"), x, y, rnd.uniform(0.6, 2.0))
        elif r < 0.10: put("dead", pick("bare"), x, y, 0.0, rnd.uniform(0.8, 1.2), tag="tree")
        continue
    if R["desert"] > 0.5:
        if r < 0.02: rock("rock", pick("rocksand"), x, y, rnd.uniform(0.5, 1.6))
        elif r < 0.03: put("dead", pick("bare"), x, y, 0.0, rnd.uniform(0.6, 1.0), tag="tree")
        continue
    fd = forest_density(x, y)
    if r < 0.55 * fd and s < 0.45:
        if rnd.random() < 0.72: put("tree", pick("fir" if rnd.random() < 0.6 else "firlight"), x, y, -0.15, rnd.uniform(0.77, 1.31))
        else: put("tree", pick("broad"), x, y, -0.15, rnd.uniform(0.82, 1.18))
    elif r < 0.55 * fd + 0.012: put("bush", pick("bush"), x, y, -0.1, rnd.uniform(0.6, 1.1))
    elif r < 0.55 * fd + 0.02 and s > 0.2: rock("rock", pick("rock"), x, y, rnd.uniform(0.5, 1.4))
print(f"SCATTER {time.time() - t_scatter:.1f} s", flush=True)


# ---- resources, each where you would look for it
def node(key, x, y, kind, r=2.2):
    """A resource node near (x, y): jittered until it stands clear of every pad and every other node (berries once grew in
    the stable yard and on top of each other)."""
    for k in range(24):
        px, py = (x, y) if k == 0 else (x + rnd.gauss(0, 4.0 + k * 0.3), y + rnd.gauss(0, 4.0 + k * 0.3))
        if raw_h(px, py) > SEA + 1.0 and all(math.hypot(px - sx, py - sy) > r + sr + 1.0 for (sx, sy, sr) in PADS) and road_at(px, py)[0] < 0.3: break
    else: print(f"[node] ! no clear ground for {kind} near {x:.0f},{y:.0f} -- NOT placed (the review counts it)"); return
    PADS.append((px, py, r)); put(kind, key, px, py, 0.0, 1.0)


for (x, y) in BERRIES:                                                                            # berries near the settlements
    for k in range(3): node("node_food", x, y, "berry")
for (x, y) in [(-88, 82), (-62, 100), (-116, 44), (-44, 124), (104, 72), (-140, 172)]:            # stone and iron at the mountain feet, both massifs
    for k in range(2): node("node_stone", x, y, "stone")
    for k in range(2): node("node_iron", x, y, "iron")
for (x, y) in [(-152, 58), (-176, 126), (-118, 154), (-84, 140)]:                                 # coal seams: black rock clusters, higher up
    for k in range(6): rock("coal", pick("coal"), x + rnd.gauss(0, 2.5), y + rnd.gauss(0, 2.5), rnd.uniform(0.5, 1.3))
for (x, y) in [(122, 154), (172, 102), (150, 78)]:                                                # uranium in the badlands: faintly glowing green rock, 3 deposits only
    for k in range(5): rock("uran", pick("uran"), x + rnd.gauss(0, 2.0), y + rnd.gauss(0, 2.0), rnd.uniform(0.4, 1.0))
for (x, y) in [(110, -120), (152, -88), (178, -140)]:                                             # oil in the desert: a black seep and a timber derrick
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
SALT = (165.0, -60.0)
sb = bmesh.new(); bm_cyl(sb, 16.0, 0.12, 24, (0, 0, 0.06)); salt = obj_from_bm(res_m, "SaltFlat", sb, MAT["salt"], bevel=0.0, loc=(SALT[0], SALT[1], height(*SALT) + 0.02))   # a salt flat
PADS.append((SALT[0], SALT[1], 16.0)); PLACED.append({"kind": "salt", "x": SALT[0], "y": SALT[1], "objs": [salt], "name": "SaltFlat"}); n["salt"] = 1
for (x, y) in [(-100, -166), (-60, -172), (0, -166), (60, -160), (120, -176), (-140, -180), (LAKE[0] + 4, LAKE[1] - 3), (LAKE[0] - 6, LAKE[1] + 4),
               (-44, -70), (-36, -112)]:                                                          # fish: shoals in the sea, the lake and the river
    for k in range(2):
        i = ids.get("shoal", 0); ids["shoal"] = i + 1
        for _t in range(40):                                                                  # in the WATER, not on the beach
            sx, sy = x + rnd.gauss(0, 3), y + rnd.gauss(0, 3)
            if raw_h(sx, sy) < SEA - 0.6: break
        fb = bmesh.new(); bm_cyl(fb, rnd.uniform(0.9, 1.4), 0.04, 14, (0, 0, 0)); o = obj_from_bm(res_m, f"shoal{i}", fb, MAT["ripple"], bevel=0.0, loc=(sx, sy, SEA + 0.02))
        objs = [o]
        for j in range(5):
            f = bmesh.new(); bm_box(f, 0.5, 0.12, 0.12, (rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)); fo = obj_from_bm(res_m, f"fish{i}_{j}", f, MAT["fish"], bevel=0.0, loc=(o.location.x, o.location.y, SEA - 0.25)); fo.rotation_euler.z = rnd.uniform(0, math.tau); objs.append(fo)
        PLACED.append({"kind": "shoal", "x": o.location.x, "y": o.location.y, "objs": objs, "name": f"shoal{i}"}); n["shoal"] = n.get("shoal", 0) + 1
# people: villagers, a patrol, a fisherman, a miner
for i, (k, x, y) in enumerate([("citizen", V[0] + 6, V[1] + 4), ("citizen", V[0] - 10, V[1] + 6), ("citizen", V[0] + 4, V[1] - 12), ("citizen", H2[0] + 4, H2[1] + 4),
                               ("citizen", h3[0] - 4, h3[1] + 6), ("citizen", h4[0] + 5, h4[1] + 3),
                               ("swordsman", V[0] + 20, V[1] + 20), ("spearman", V[0] + 22, V[1] + 22), ("archer", V[0] + 24, V[1] + 19), ("standard", V[0] + 22, V[1] + 25), ("horseman", -20, -30)]):
    put("people", k, x, y, 0.0, 1.4, tag=f"p{i}_{k}")
print("PLACED " + " ".join(f"{k}={v}" for k, v in sorted(n.items())), flush=True)

# ============================================================================ extras: the rares, the game, the wild herd, the rig (docs/14-world.md §2c)
import extras as X
import figure as F
TR = materials.troop_kit()
XM = {"pelt": flat("WPelt", (0.35, 0.24, 0.14)), "amber": emissive("WAmber", (1.0, 0.55, 0.12), 1.2), "rust": flat("WRust", (0.42, 0.18, 0.07), 0.6),
      "crust": flat("WCrust", (0.85, 0.85, 0.80)), "gold": flat("WGold", (0.95, 0.75, 0.25), 0.35), "sinter": flat("WSinter", (0.80, 0.74, 0.62)),
      "steam": emissive("WSteam", (0.9, 0.9, 0.92), 0.6), "whale": flat("WWhale", (0.12, 0.14, 0.17), 0.4), "deck": flat("WDeck", (0.55, 0.50, 0.40)),
      "flame": emissive("WFlame", (1.0, 0.5, 0.1), 12.0), "deer": flat("WDeerHide", (0.42, 0.28, 0.14)), "antler": flat("WAntler", (0.66, 0.60, 0.50)),
      "rbark": flat("WRubberBark", (0.62, 0.58, 0.48)), "rleaf": flat("WRubberLeaf", (0.50, 0.60, 0.28)), "pitch": emissive("WPitchblende", (0.55, 1.0, 0.25), 9.0)}


def xproto(key, build, mats, **kw):
    o = X.make(f"proto_{key}", build, mats, rnd, **kw); zs = [v.co.z for v in o.data.vertices]; PZ[key] = (min(zs), max(zs))
    lib.register(key, [o]); lib.offset[key] = Vector((0, 0, 0)); PROTO.setdefault(key.split(":")[0], []).append(key)


xproto("furs", X.furs, [TK["bark"], XM["pelt"]]); xproto("amber", X.amber, [XM["amber"]]); xproto("bogiron", X.bog_iron, [XM["rust"], TK["rock"]])
xproto("saltpetre", X.saltpetre, [TK["rock"], XM["crust"]]); xproto("gold", X.gold_vein, [TK["rock"], XM["gold"]]); xproto("geyser", X.geyser, [XM["sinter"], TK["water"], XM["steam"]])
xproto("whale", X.whale, [XM["whale"]]); xproto("rig", X.offshore_rig, [TR["iron"], XM["deck"], XM["flame"]])
for i in range(2): xproto(f"deer:{i}", X.deer, [XM["deer"], XM["antler"]])
for i in range(2): proto(f"rubber:{i}", [XM["rbark"], XM["rleaf"]], P.broadleaf, 6.0, 7, rnd)
proto("pitch:0", [XM["pitch"]], P.boulder, rnd)
# the wild horse is the library's own horse without a saddle: its parts are registered as one asset (bound boxes need an update first)
wild = Model("WildHorse"); wobjs, _ = F.horse(wild, (0, 0, 0), TR, hide="hide_gry", saddle=False, name="wildhorse", rnd=rnd)
C.view_layer.update(); lib.register("horse_wild", wobjs)


def shore(x, back=4.0): return (x, COAST_Y(x) + back)


def land(x, y, r=2.5, tries=30):
    """A dry, clear spot near (x, y), or None."""
    for k in range(tries):
        px, py = (x, y) if k == 0 else (x + rnd.gauss(0, 3.0 + k * 0.4), y + rnd.gauss(0, 3.0 + k * 0.4))
        if raw_h(px, py) > SEA + 1.0 and all(math.hypot(px - sx, py - sy) > r + sr + 1.0 for (sx, sy, sr) in PADS) and road_at(px, py)[0] < 0.3: return (px, py)
    print(f"[extras] ! no clear ground near {x:.0f},{y:.0f}"); return None


def sea(x, y, lo=-6.0, hi=-1.5, tries=40):
    """A point of sea bed between lo and hi metres off the shore at x: walk out from the coast until the bed is in range
    (a random search missed the band twice). Stays 14 m inside the map edge."""
    for dx in (0, 6, -6, 12, -12, 18, -18):
        px = x + dx
        for step in range(0, 60):
            py = COAST_Y(px) - 2.0 - step * 1.5
            if abs(py) > Dp / 2 - 14: break
            if lo < raw_h(px, py) < hi: return (px, py)
    return None


for key, (x, y) in [("furs", (-100, -24)), ("amber", shore(-110)), ("bogiron", (66, -46)), ("saltpetre", (-40, 112)), ("gold", (-150, 30)), ("geyser", (92, 62))]:
    p = land(x, y, 4.0)
    if p: PADS.append((p[0], p[1], 4.0)); put("rare", key, p[0], p[1], 0.0, 1.0, tag=key)
for k in range(4): rock("rare", "pitch:0", 160 + rnd.gauss(0, 2.5), 136 + rnd.gauss(0, 2.5), rnd.uniform(0.5, 1.0))     # pitchblende: a brighter uranium
for k in range(10): rock("rare", pick("coal"), -130 + rnd.gauss(0, 3.5), 130 + rnd.gauss(0, 3.5), rnd.uniform(0.7, 1.6))  # the rich coal seam
for k in range(8):                                                                                                            # the rubber grove, in the wettest corner
    p = land(-80 + rnd.gauss(0, 7), -130 + rnd.gauss(0, 7), 1.5)
    if p: put("rubber", pick("rubber"), p[0], p[1], -0.15, rnd.uniform(0.85, 1.15), tag="tree")
p = sea(72, -184)                                                                                                            # off the grass coast: the desert bay is never deeper than a metre
if p: put("rig", "rig", p[0], p[1], raw_h(*p) - height(*p), 1.0); PADS.append((p[0], p[1], 8.0))                             # base on the sea bed
else: print("[extras] ! no shallow sea for the rig")
p = sea(30, -195, lo=-12.0, hi=-3.0)
if p: put("whale", "whale", p[0], p[1], SEA - height(*p), 1.0)
for (hx, hy) in [(-90, -80), (-130, -20), (56, 86)]:                                                                        # deer herds in forest clearings
    for k in range(5):
        p = land(hx + rnd.gauss(0, 6), hy + rnd.gauss(0, 6), 1.2, tries=12)
        if p: put("deer", pick("deer"), p[0], p[1], 0.0, rnd.uniform(0.9, 1.1))
for k in range(6):                                                                                                           # the wild herd on the steppe (the Horses rare)
    p = land(150 + rnd.gauss(0, 7), 30 + rnd.gauss(0, 7), 1.6, tries=12)
    if p: put("horse_wild", "horse_wild", p[0], p[1], 0.0, 1.0)
print("EXTRAS " + " ".join(f"{k}={n.get(k, 0)}" for k in ("rare", "rubber", "rig", "whale", "deer", "horse_wild")), flush=True)

# ============================================================================ dressing: life around every pad (V9, docs/16-look.md §5)
XM["hay"] = flat("WHay", (0.72, 0.58, 0.22)); XM["cloth"] = flat("WCloth", (0.62, 0.56, 0.44)); XM["wool"] = flat("WWool", (0.86, 0.84, 0.78)); XM["dark"] = flat("WDark", (0.16, 0.13, 0.11))
smk = D.materials.new("WSmoke"); smk.use_nodes = True; _nt = smk.node_tree; _nt.nodes.clear()
_o = _nt.nodes.new("ShaderNodeOutputMaterial"); _v = _nt.nodes.new("ShaderNodeVolumeScatter"); _v.inputs["Color"].default_value = (0.75, 0.75, 0.78, 1)
_n = _nt.nodes.new("ShaderNodeTexNoise"); _n.inputs["Scale"].default_value = 0.9; _n.inputs["Detail"].default_value = 4.0
_m = _nt.nodes.new("ShaderNodeMapRange"); _m.inputs["From Min"].default_value = 0.45; _m.inputs["From Max"].default_value = 0.75; _m.inputs["To Max"].default_value = 0.35
_nt.links.new(_n.outputs["Fac"], _m.inputs["Value"]); _nt.links.new(_m.outputs["Result"], _v.inputs["Density"]); _nt.links.new(_v.outputs["Volume"], _o.inputs["Volume"])
XM["smoke"] = smk
xproto("fence", X.fence, [TK["bark"]]); xproto("cart", X.cart, [XM["rbark"], TR["iron"]]); xproto("barrels", X.barrels, [XM["rbark"], TR["iron"]])
xproto("rack", X.rack, [TK["bark"], XM["cloth"]]); xproto("woodpile", X.woodpile, [XM["rbark"]]); xproto("haystack", X.haystack, [XM["hay"], TK["bark"]])
xproto("smoke", X.smoke, [XM["smoke"]]); xproto("sheep", X.sheep, [XM["wool"], XM["dark"]])
KIT = {"hall": ["cart", "rack", "barrels", "woodpile", "smoke"], "runehall": ["barrels", "smoke"], "muster": ["rack", "barrels", "fence"], "forge": ["barrels", "woodpile", "smoke"],
       "stabbur": ["cart", "woodpile"], "stable": ["fence", "haystack", "cart"], "farm": ["fence", "fence", "haystack"], "boathouse": ["rack", "barrels", "rack"],
       "well": ["barrels"], "hut_a": ["woodpile", "fence"], "hut_b": ["woodpile", "rack"], "hut_c": ["fence", "barrels"], "hut_d": ["woodpile", "fence"], "hut_e": ["rack", "woodpile"]}


def dress(key, x, y, yaw):
    """Props on the pad's edge, facing the building, clear of every other pad and road."""
    hx, hy, r = lib.footprint(key)
    for j, prop in enumerate(KIT.get(key, [])):
        if prop == "smoke":
            put("dressing", "smoke", x, y, hy * 0.5 + 3.5, 1.0, tag="smoke", yaw=0.0); continue
        for k in range(12):
            a = yaw + (j + 1) * 1.1 + rnd.uniform(-0.4, 0.4) + k * 0.5; d = r + rnd.uniform(1.2, 3.0)
            px, py = x + math.cos(a) * d, y + math.sin(a) * d
            if raw_h(px, py) > SEA + 1.0 and road_at(px, py)[0] < 0.25 and all(math.hypot(px - sx, py - sy) > sr + 0.8 for (sx, sy, sr) in PADS if (sx, sy) != (x, y)):
                put("dressing", prop, px, py, 0.0, 1.0, tag=prop, yaw=a + math.pi / 2); break
for key, x, y, yaw in sites: dress(key, x, y, yaw)
for k in range(7):                                                                                                           # sheep by the steppe hamlet
    p = land(H2[0] - 22 + rnd.gauss(0, 5), H2[1] + 6 + rnd.gauss(0, 5), 0.8, tries=10)
    if p: put("dressing", "sheep", p[0], p[1], 0.0, rnd.uniform(0.9, 1.1), tag="sheep")
print(f"DRESSING {n.get('dressing', 0)}", flush=True)

# ---- grass on grass, straw on the steppe
t_grass = time.time()
GRASS = grass_material(new_mat, principled, maprange, green=(0.06, 0.15, 0.03, 1), olive=(0.13, 0.16, 0.04, 1), straw=(0.24, 0.20, 0.07, 1))
tufts = [make_tuft_mesh(f"Tuft{i}", rnd.randint(34, 52), 3000 + i, GRASS, h_range=(0.15, 0.45), w_range=(0.006, 0.013)) for i in range(6)]
nt_ = 0; cap = int(os.environ.get("GRASS", 90000)); pads_near = PADS[:80]
for _ in range(cap * 3):
    if nt_ >= cap: break
    x, y = rnd.uniform(-W / 2 + 1, W / 2 - 1), rnd.uniform(-Dp / 2 + 1, Dp / 2 - 1)
    b = biome(x, y); R = region(x, y)
    if raw_h(x, y) < SEA + 0.8 or b < 0.24 or b > 0.66 or R["volc"] > 0.4 or road_at(x, y)[0] > 0.5: continue
    if not all(math.hypot(x - sx, y - sy) > r * 0.6 for (sx, sy, r) in pads_near): continue
    o = D.objects.new(f"Tuft_{nt_:05d}", rnd.choice(tufts)); C.scene.collection.objects.link(o)
    o.location = (x, y, height(x, y) - 0.04); s_ = rnd.uniform(1.1, 2.4); o.scale = (s_, s_, s_ * rnd.uniform(0.9, 1.7)); o.rotation_euler = (0, 0, rnd.uniform(0, math.tau)); nt_ += 1
print(f"GRASS {nt_} in {time.time() - t_grass:.0f} s", flush=True)

# ---- review before pixels: worldreview writes renders/REVIEW.md; a FAIL raises AFTER the renders below so the pictures exist
import worldreview
CTX = type("Ctx", (), {"region": staticmethod(region), "height": staticmethod(height), "raw_h": staticmethod(raw_h), "dry_flat": staticmethod(dry_flat), "SEA": SEA, "W": W, "D": Dp})
REVIEW_OK = worldreview.run(PLACED, CTX, os.path.join(SCENE_DIR, "renders"), time.time() - T0, os.environ.get("BLENDER_GPU", "METAL"))

# ============================================================================ light, cameras, render (docs/16-look.md §4: lighting.py is the one rig)
import lighting


def camera(name, loc, rot, lens=35, ortho=None):
    cd = D.cameras.new(name); cd.clip_end = 3000.0
    if ortho: cd.type = "ORTHO"; cd.ortho_scale = ortho
    else: cd.lens = lens
    o = D.objects.new(name, cd); C.scene.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; return o


hero = camera("Hero", (16, -300, 330), (math.radians(56), 0, math.radians(-4)), lens=35)         # pitched down: the frame is land, not sky
plan = camera("Plan", (0, 0, 500), (0, 0, 0), ortho=W + 10)
vil = camera("Village", (V[0] + 8, V[1] - 62, 46), (math.radians(50), 0, math.radians(6)), lens=40)
# the twelve region crops the review looks at, one per thing that must read
REGION_CAMS = [("village", V), ("hamlet_steppe", H2), ("hamlet_fishing", h3), ("camp_mining", h4), ("bridge", BRIDGE), ("ford", FORD),
               ("mountain", (-130, 110)), ("volcano", VOLCANO), ("desert_oil", (150, -110)), ("salt", SALT), ("lake", LAKE), ("forest", (-110, -40)),
               ("herd", (-90, -80)), ("steppe_horses", (150, 30)), ("rig", (72, -184)), ("geyser", (92, 62))]
crops = [(camera(f"R_{nm}", (cx + 6, cy - 70, 56), (math.radians(50), 0, math.radians(5)), lens=40), nm) for nm, (cx, cy) in REGION_CAMS] if REGIONS else []

out = os.path.join(SCENE_DIR, "renders", "world_")
final = QUALITY == "final"
render_settings(scene, out, res=(3840, 2400) if final else (1200, 750), samples=1024 if final else 48, exposure=-1.6)
lighting.rig(scene, W, Dp, wind=(1.0, 0.3), with_clouds=os.environ.get("CLOUDS", "1") == "1", with_haze=os.environ.get("HAZE", "1") == "1")   # after render_settings: the rig owns exposure
try: scene.cycles.denoiser = "OPTIX" if os.environ.get("BLENDER_GPU", "METAL") == "OPTIX" else "OPENIMAGEDENOISE"
except Exception as ex: print("[render] denoiser:", ex)
scene.render.use_persistent_data = True                                  # sync the 100k-object scene ONCE for all 19 frames, not per frame
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENE_DIR, "map_world.blend"))
print("BUILT", len(D.objects), "objects", f"in {time.time() - T0:.0f} s", flush=True)
shots = [(hero, "hero", (3840, 2400), 1024), (plan, "plan", (4200, 4200), 512), (vil, "village", (3840, 2400), 1024)] + [(c, f"region_{nm}", (1920, 1200), 256) for c, nm in crops]
for cam, tag, res_f, spp in shots:
    scene.camera = cam; scene.render.filepath = out + tag + ("_final" if final else "_preview") + ".png"
    if final: scene.render.resolution_x, scene.render.resolution_y = res_f
    else: scene.render.resolution_x, scene.render.resolution_y = (1400, 1400) if tag == "plan" else (960, 600) if tag.startswith("region") else (1200, 750)
    scene.cycles.samples = spp if final else 48
    t_r = time.time(); bpy.ops.render.render(write_still=True); print("RENDERED", scene.render.filepath, f"{time.time() - t_r:.0f} s", flush=True)
# ---- the LOOK score (docs/16-look.md §5): measure the crops and append a look table to REVIEW.md. Informational until the
#      standard is met; the batch rc stays with the placement review.
import measure
look_rows = []
for cam, tag, res_f, spp in shots:
    if not tag.startswith("region") and tag != "hero": continue
    p = out + tag + ("_final" if final else "_preview") + ".png"
    try: look_rows.append((tag, measure.score(measure.load(p))))
    except Exception as ex: print("[look]", tag, ex)
if look_rows:
    with open(os.path.join(SCENE_DIR, "renders", "REVIEW.md"), "a") as f:
        f.write("\n## look (docs/16-look.md §5)\n\n| crop | saturation | shadows | white pt | black | spread | median | verdict |\n|---|---|---|---|---|---|---|---|\n")
        for tag, s in look_rows:
            f.write(f"| {tag} | {s['sat']:.2f} {s['sat_ok']} | {s['sh_luma']:.3f} {s['sh_hue']:.0f}° {s['sh_ok']} | {s['white']:.2f}% {s['white_ok']} | {s['black']:.2f}% {s['black_ok']} | {s['spread']} {s['spread_ok']} | {s['p50']:.2f} {s['p50_ok']} | {s['passed']}/6 |\n")
    print("LOOK " + " ".join(f"{tag}={s['passed']}/6" for tag, s in look_rows), flush=True)
print(f"BUILD+RENDER {time.time() - T0:.0f} s")
if not REVIEW_OK: raise RuntimeError("REVIEW FAILED -- see renders/REVIEW.md")
