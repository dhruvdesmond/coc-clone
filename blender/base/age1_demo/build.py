"""The three Age I buildings the demo needs and the library did not have: Rune Hall, Muster Hall, Farm.

Lives in the clash-of-clans repo, NOT in ~/blender: that tree is shared with a live mobile
session and is not under version control. This script only READS ~/blender/lib.

Rebuild:  blender -b --factory-startup --python blender/base/age1_demo/build.py
Preview:  RENDER_QUALITY=preview blender -b --factory-startup blender/base/age1_demo/age1_demo.blend \
              --python ~/blender/scripts/render.py -f 1
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))

from nodeutils import new_mat, principled, noise_node, math_node, maprange  # noqa: E402
import materials, norse as N                                               # noqa: E402

BLEND = os.path.join(SCENE_DIR, "age1_demo.blend")
random.seed(131)
D, C = bpy.data, bpy.context
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = C.scene
MAT = materials.kit()
TROOP = materials.troop_kit()


def shell(m, roof, seed, base_z=0.0, door=None, open_gable=None, skip_long=(), buttress=0,
          rafters=8, plinth_h=0.30, horns=True, rows=16, cols=16):
    """Same shell the outbuildings use, so these read as the same village."""
    if plinth_h:
        N.plinth(m, roof, MAT["stone"], h=plinth_h, margin=0.34, seed=seed)
    N.plank_walls(m, roof, MAT["timber"], seed=seed, plank_w=0.28, thick=0.14,
                  base_z=base_z, door=door, open_gable=open_gable, skip_long=skip_long)
    N.corner_posts(m, roof, MAT["beam"], w=0.24, base_z=base_z, lift=0.10)
    N.wall_plates(m, roof, MAT["beam"], w=0.20, h=0.18)
    N.shingle_roof(m, roof, MAT["shingle"], rows=rows, cols=cols, seed=seed * 29, lo=0.072, hi=0.018)
    N.barge_boards(m, roof, MAT["beam"], w=0.19, h=0.36, horns=horns, v_end=1.24)
    N.ridge_cap(m, roof, MAT["beam"], w=0.23, h=0.16, lift=0.08)
    N.rafter_tails(m, roof, MAT["beam"], n=rafters, w=0.085, h=0.105)
    if buttress:
        N.buttresses(m, roof, MAT["beam"], n=buttress, out_dist=1.15, w=0.16)


def slab(m, name, loc, w, d, h, mat, lean=(0.0, 0.0), bevel=0.03):
    """A standing stone: a tapered slab, slightly off true. Nothing old stands straight."""
    bm = bmesh.new()
    N.bm_box(bm, w, d, h, (0, 0, h / 2))
    for v in bm.verts:
        if v.co.z > h * 0.5:
            v.co.x *= 0.72; v.co.y *= 0.80
            v.co.x += lean[0]; v.co.y += lean[1]
    return N.obj_from_bm(m, name, bm, mat, bevel=bevel, loc=loc)


# ------------------------------------------------------------------ rune hall
def build_runehall(origin, rot):
    """Knowledge. A steep narrow hall -- taller for its footprint than anything else in the
    village -- behind an arc of standing rune stones. The silhouette must say 'not a house'."""
    m = N.Model("runehall", origin=origin, rot_z=rot)
    roof = N.Roof(5.4, 4.0, 2.35, 6.10, over_x=0.80, over_y=0.85, rise=0.70, rise_e=0.30, flare=1.26, splay=0.05)
    shell(m, roof, 41, base_z=0.34, door=(1, 1.30, 2.10), buttress=2, rafters=9, plinth_h=0.34, rows=20, cols=15)
    N.doorway(m, roof, MAT["beam"], MAT["darkwood"], side=1, width=1.30, height=2.10, base_z=0.34, straps_mat=MAT["iron"])
    N.window_slit(m, roof, MAT["darkwood"], -1, 0.0, 2.2, w=0.40, h=0.62)

    rnd = random.Random(7)
    n = 7
    for i in range(n):                                   # the arc of stones in front of the door
        a = math.radians(-62 + i * (124 / (n - 1)))
        r = 4.9
        x, y = roof.L / 2 + 0.6 + math.cos(a) * r * 0.62, math.sin(a) * r
        h = rnd.uniform(1.5, 2.5) * (1.25 if i == n // 2 else 1.0)
        slab(m, f"runehall_Stone{i}", (x, y, -0.08), rnd.uniform(0.55, 0.80), rnd.uniform(0.20, 0.28), h,
             MAT["stone"], lean=(rnd.uniform(-0.08, 0.08), rnd.uniform(-0.06, 0.06)))
        # a carved band: one dark inlay across each stone
        bm = bmesh.new(); N.bm_box(bm, 0.30, 0.30, 0.07)
        N.obj_from_bm(m, f"runehall_Rune{i}", bm, MAT["iron"], bevel=0.006, loc=(x, y, h * 0.62))
    # the speaking stone: a low flat table at the centre of the arc
    bm = bmesh.new(); N.bm_cyl(bm, 0.78, 0.34, 9, (0, 0, 0), r_top=0.70)
    N.obj_from_bm(m, "runehall_Table", bm, MAT["stone"], bevel=0.03, loc=(roof.L / 2 + 2.3, 0, 0.17))
    # twin carved posts flanking the door, taller than the eave
    for s in (1, -1):
        N.beam_between(m, f"runehall_Post{s}", (roof.L / 2 + 0.75, s * 1.25, 0.0), (roof.L / 2 + 0.75, s * 1.25, 3.5), 0.26, 0.26, MAT["beam"])
        bm = bmesh.new(); N.bm_box(bm, 0.40, 0.40, 0.16)
        N.obj_from_bm(m, f"runehall_PostCap{s}", bm, MAT["iron"], bevel=0.02, loc=(roof.L / 2 + 0.75, s * 1.25, 3.55))
    return m


# ---------------------------------------------------------------- muster hall
def build_muster(origin, rot):
    """War. Long, low and OPEN at one gable so the yard and the hall are one space; weapon rack,
    shields on the wall, a pell to strike. Wider than it is tall -- the opposite of the rune hall."""
    m = N.Model("muster", origin=origin, rot_z=rot)
    roof = N.Roof(7.6, 4.8, 2.10, 4.55, over_x=0.85, over_y=0.95, rise=0.46, rise_e=0.22, flare=1.20, splay=0.05)
    shell(m, roof, 53, base_z=0.26, open_gable=1, buttress=4, rafters=11, plinth_h=0.26, rows=17, cols=20)

    x0 = roof.L / 2 + 1.6                                # the yard, in front of the open end
    for i in range(6):                                   # spear rack: a rail on two posts, spears leaning
        y = -1.5 + i * 0.6
        N.beam_between(m, f"muster_Spear{i}", (x0 + 0.55, y, 0.0), (x0 + 0.05, y, 2.35), 0.045, 0.045, TROOP["wood"], bevel=0.004)
        bm = bmesh.new(); N.bm_cyl(bm, 0.035, 0.30, 6, (0, 0, 0), r_top=0.004)
        N.obj_from_bm(m, f"muster_SpearHead{i}", bm, TROOP["steel"], bevel=0.0, loc=(x0 + 0.02, y, 2.50))
    for s in (1, -1):
        N.beam_between(m, f"muster_RackPost{s}", (x0 + 0.18, s * 1.85, 0.0), (x0 + 0.18, s * 1.85, 1.75), 0.14, 0.14, MAT["beam"])
    N.beam_between(m, "muster_RackRail", (x0 + 0.18, -1.95, 1.62), (x0 + 0.18, 1.95, 1.62), 0.10, 0.10, MAT["beam"])

    shield_mats = [TROOP["shield_r"], TROOP["shield_b"], TROOP["shield_y"], TROOP["shield_w"]]
    for i in range(5):                                   # shields hung along the long wall
        x = -2.6 + i * 1.3
        bm = bmesh.new(); N.bm_cyl(bm, 0.44, 0.06, 18, (0, 0, 0))
        o = N.obj_from_bm(m, f"muster_Shield{i}", bm, shield_mats[i % 4], bevel=0.008, loc=(x, -(roof.W / 2 + 0.10), 1.35))
        o.rotation_euler.x = math.radians(90)
        bm = bmesh.new(); N.bm_cyl(bm, 0.10, 0.10, 10, (0, 0, 0), r_top=0.05)
        o = N.obj_from_bm(m, f"muster_Boss{i}", bm, TROOP["steel"], bevel=0.004, loc=(x, -(roof.W / 2 + 0.17), 1.35))
        o.rotation_euler.x = math.radians(90)

    # the pell: a hacked-up striking post with a crossbar
    N.beam_between(m, "muster_Pell", (x0 + 2.4, 1.2, 0.0), (x0 + 2.4, 1.2, 1.9), 0.22, 0.22, MAT["darkwood"])
    N.beam_between(m, "muster_PellArm", (x0 + 2.4, 0.65, 1.45), (x0 + 2.4, 1.75, 1.45), 0.10, 0.10, MAT["darkwood"])
    # banner pole
    N.beam_between(m, "muster_Pole", (x0 + 2.2, -1.9, 0.0), (x0 + 2.2, -1.9, 5.4), 0.10, 0.10, MAT["beam"])
    bm = bmesh.new(); N.bm_box(bm, 0.04, 0.95, 1.45)
    N.obj_from_bm(m, "muster_Banner", bm, TROOP["tunic_r"], bevel=0.004, loc=(x0 + 2.2, -1.38, 4.55))
    N.barrel(m, (x0 - 0.9, 2.0, 0.34), MAT["timber"], MAT["iron"])
    return m


# ------------------------------------------------------------------------ farm
def build_farm(origin, rot):
    """Food that never runs out. A fenced plot that must read from a 50-degree camera: strong
    parallel furrows, a fence you can see as a line, one small shed, one haystack."""
    m = N.Model("farm", origin=origin, rot_z=rot)
    L, W = 7.4, 6.0
    soil, crop = MAT["darkwood"], MAT["thatch"]
    rows = 8
    for i in range(rows):
        y = -W / 2 + 0.55 + i * (W - 1.1) / (rows - 1)
        bm = bmesh.new(); N.bm_box(bm, L - 1.2, 0.42, 0.16)
        N.obj_from_bm(m, f"farm_Furrow{i}", bm, soil, bevel=0.05, loc=(-0.2, y, 0.06))
        rnd = random.Random(90 + i)
        for k in range(15):                              # the crop: uneven sheaves along each furrow
            x = -L / 2 + 0.8 + k * (L - 1.9) / 14 + rnd.uniform(-0.08, 0.08)
            h = rnd.uniform(0.42, 0.72)
            bm = bmesh.new(); N.bm_cyl(bm, 0.10, h, 6, (0, 0, 0), r_top=0.15)
            N.obj_from_bm(m, f"farm_Crop{i}_{k}", bm, crop, bevel=0.0, loc=(x - 0.2, y, 0.14 + h / 2))

    def fence(p0, p1, tag):
        p0, p1 = Vector(p0), Vector(p1)
        n = max(2, int((p1 - p0).length / 1.25))
        for k in range(n + 1):
            p = p0.lerp(p1, k / n)
            N.beam_between(m, f"farm_Post{tag}{k}", (p.x, p.y, 0.0), (p.x, p.y, 1.05), 0.12, 0.12, MAT["beam"], bevel=0.01)
        for z in (0.45, 0.85):
            N.beam_between(m, f"farm_Rail{tag}{z}", (p0.x, p0.y, z), (p1.x, p1.y, z), 0.07, 0.09, MAT["timber"], bevel=0.006)

    hx, hy = L / 2, W / 2
    fence((-hx, -hy, 0), (hx, -hy, 0), "S"); fence((-hx, hy, 0), (hx, hy, 0), "N")
    fence((-hx, -hy, 0), (-hx, hy, 0), "W"); fence((hx, -hy, 0), (hx, -0.9, 0), "Ea"); fence((hx, 0.9, 0), (hx, hy, 0), "Eb")

    roof = N.Roof(2.3, 1.9, 1.35, 2.35, over_x=0.35, over_y=0.40, rise=0.18, rise_e=0.08, flare=1.12, splay=0.03)
    shed = N.Model("farm", origin=tuple(m.place((hx - 1.35, hy - 1.25, 0.0))), rot_z=rot)
    shell(shed, roof, 71, base_z=0.0, open_gable=-1, rafters=5, plinth_h=0, horns=False, rows=9, cols=8)

    bm = bmesh.new()                                     # haystack
    N.bm_cyl(bm, 0.95, 0.9, 12, (0, 0, 0.45), r_top=0.78); N.bm_cyl(bm, 0.78, 0.8, 12, (0, 0, 1.30), r_top=0.06)
    N.obj_from_bm(m, "farm_Hay", bm, crop, bevel=0.04, loc=(hx - 1.5, -hy + 1.4, 0.0))
    return m, shed


models = []
models.append(build_runehall((-11.0, 0.0, 0.0), 0.0))
models.append(build_muster((0.0, 0.0, 0.0), 0.0))
farm, shed = build_farm((11.5, 0.0, 0.0), 0.0)

os.makedirs(os.path.join(SCENE_DIR, "models"), exist_ok=True)
for mdl in models:
    N.export_model(mdl, os.path.join(SCENE_DIR, "models", f"{mdl.name}.blend"))

# the farm is two Models (plot + shed); write both into one asset file
farm_objs = list(farm.coll.objects) + list(shed.coll.objects)
bpy.data.libraries.write(os.path.join(SCENE_DIR, "models", "farm.blend"), set(farm_objs), fake_user=True)

bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0))
C.object.name = "Ground"
C.object.data.materials.append(N.turf_material(new_mat, principled, noise_node, math_node, maprange,
                               lush=(0.042, 0.112, 0.026, 1), dry=(0.082, 0.118, 0.034, 1)))
N.daylight(sun_energy=2.6, sky_strength=0.30, elevation=44.0, rotation=34.0)
N.lineup_camera(30.0, center=(0.4, 0.6, 2.2), lens=85, elev=0.62, back=2.45)
N.render_settings(scene, os.path.join(SCENE_DIR, "renders", "age1_demo_"))
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("BUILT", len(D.objects), "objects")
