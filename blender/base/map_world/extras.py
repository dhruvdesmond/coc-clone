"""The map's small extras (docs/14-world.md §2c): the nine rares' markers, the game and the wild herd, an offshore oil rig, a
geyser, a whale shoal.  Same contract as protos.py -- each builder fills a bmesh with material slots, base on z = 0 (or the
water line), and is registered once through the AssetLibrary and instanced with place().

Nothing here is a hero asset: each marker's job is to be READ from 60 m up as "that patch is worth holding".
"""
import bmesh, math
import bpy
from mathutils import Vector, Matrix
import protos as P

D, C = bpy.data, bpy.context


def _box(bm, sx, sy, sz, centre, mat=0, smooth=False, yaw=0.0):
    start = len(bm.faces); vstart = len(bm.verts)
    cx, cy, cz = centre; hx, hy, hz = sx / 2, sy / 2, sz / 2
    p = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    vs = [bm.verts.new((x, y, z)) for x, y, z in p]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]: bm.faces.new([vs[i] for i in f])
    bm.verts.ensure_lookup_table()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(yaw, 4, 'Z'), verts=bm.verts[vstart:])
    P._tag(bm, start, mat, smooth)


# ---------------------------------------------------------------------------- the rares (doc 12): one marker each
def furs(bm, rnd):
    """A trapper's drying rack: two posts, a crossbar, three pelts hanging. mats [timber, pelt]."""
    for x in (-1.1, 1.1): P._cyl(bm, 0.07, 2.0, 6, (x, 0, 1.0), mat=0)
    _box(bm, 2.5, 0.1, 0.1, (0, 0, 1.9), mat=0)
    for k, x in enumerate((-0.7, 0.0, 0.7)):
        _box(bm, 0.55, 0.06, rnd.uniform(0.7, 1.0), (x, 0.04, 1.35), mat=1)


def amber(bm, rnd):
    """Pale lumps on the shore. mats [amber]."""
    for k in range(6):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 1.4)
        P._blob(bm, (math.cos(a) * d, math.sin(a) * d, 0.12), rnd.uniform(0.12, 0.26), (1, 1, 0.7), 0.3, k * 3.1, sub=1, mat=0, smooth=False)


def bog_iron(bm, rnd):
    """A rust-red pool with a raised rim. mats [rust, rim]."""
    P._cyl(bm, 3.2, 0.08, 20, (0, 0, 0.04), mat=0)
    for k in range(10):
        a = k / 10 * math.tau; P._blob(bm, (math.cos(a) * 3.3, math.sin(a) * 3.3, 0.15), 0.35, (1, 1, 0.6), 0.3, k * 2.7, sub=1, mat=1, smooth=False)


def saltpetre(bm, rnd):
    """A cave mouth in a slab, white crust round it. mats [rock, crust]."""
    P._blob(bm, (0, 0, 1.4), 2.4, (1.3, 1.0, 0.8), 0.25, 5.0, sub=2, mat=0, smooth=False)
    P._blob(bm, (0, -1.9, 0.5), 1.0, (1.2, 0.5, 0.8), 0.15, 6.0, sub=1, mat=1, smooth=False)
    P._cyl(bm, 1.6, 0.05, 14, (0, -2.6, 0.02), mat=1)


def rubber_grove_leaf():
    return None   # the rubber grove is a broadleaf prototype with a pale leaf material -- built in build.py from protos.broadleaf


def gold_vein(bm, rnd):
    """A quartz rock with a gold seam: a boulder whose middle band of faces is the second material. mats [rock, gold]."""
    P.boulder(bm, rnd, flat=False, facets=2)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(c.x * 0.7 + c.z * 0.4) < 0.16: f.material_index = 1


def geyser(bm, rnd):
    """A sinter cone with a pool and a steam column. mats [sinter, water, steam]."""
    P._cyl(bm, 3.0, 0.9, 18, (0, 0, 0.45), r_top=1.6, mat=0)
    P._cyl(bm, 1.2, 0.06, 14, (0, 0, 0.92), mat=1)
    P._cyl(bm, 0.5, 5.0, 10, (0, 0, 3.4), r_top=1.4, mat=2, smooth=True)


def whale(bm, rnd):
    """Back and fin breaking the surface. mats [hide]."""
    P._blob(bm, (0, 0, -0.5), 2.4, (2.4, 0.9, 0.7), 0.05, 1.0, sub=2, mat=0, smooth=True)
    _box(bm, 0.5, 0.08, 0.9, (0.6, 0, 0.8), mat=0)


def offshore_rig(bm, rnd):
    """A platform on four legs standing in shallow water, a derrick on top, a flare stack. Base at the sea bed (z = 0 = bed). mats [steel, deck, flame]."""
    for x in (-4, 4):
        for y in (-4, 4): P._cyl(bm, 0.35, 9.0, 8, (x, y, 4.5), mat=0)
    _box(bm, 11.0, 11.0, 0.5, (0, 0, 9.25), mat=1)
    for k in range(4):
        a = k * math.tau / 4 + 0.4; P._tube(bm, (math.cos(a) * 2.2, math.sin(a) * 2.2, 9.5), (0, 0, 20.0), 0.18, 0.12, n=5, mat=0)
    for zz in (12.5, 16.0):
        for k in range(4):
            a0 = k * math.tau / 4 + 0.4; a1 = a0 + math.tau / 4; rr = 2.2 * (1 - (zz - 9.5) / 10.5)
            P._tube(bm, (math.cos(a0) * rr, math.sin(a0) * rr, zz), (math.cos(a1) * rr, math.sin(a1) * rr, zz), 0.1, 0.1, n=4, mat=0)
    P._cyl(bm, 0.25, 8.0, 8, (4.6, -4.6, 13.5), mat=0)
    P._blob(bm, (4.6, -4.6, 18.4), 0.7, (1, 1, 1.4), 0.3, 9.0, sub=1, mat=2, smooth=True)
    _box(bm, 3.0, 2.0, 1.8, (-3.0, 3.0, 10.4), mat=1)


# ---------------------------------------------------------------------------- animals
def deer(bm, rnd, mats_idx=(0, 1)):
    """A small quadruped with antlers, built from boxes and blobs in the library's figure idiom. mats [hide, antler]. Base at z=0."""
    L, WH = 1.5, 1.25
    back = WH * 0.66
    P._blob(bm, (0, 0, back), WH * 0.19, (1.9, 0.9, 0.85), 0.08, 2.0, mat=0, smooth=True)                   # barrel
    P._tube(bm, (L * 0.30, 0, back + 0.05), (L * 0.42, 0, back + WH * 0.38), WH * 0.09, WH * 0.06, n=6, mat=0)   # neck
    P._blob(bm, (L * 0.47, 0, back + WH * 0.42), WH * 0.08, (1.5, 0.7, 0.8), 0.06, 3.0, sub=1, mat=0, smooth=True)   # head
    for s in (1, -1):
        for hx in (L * 0.26, -L * 0.28):
            P._tube(bm, (hx, s * WH * 0.12, back - WH * 0.1), (hx + 0.03, s * WH * 0.13, WH * 0.32), WH * 0.06, WH * 0.045, n=5, mat=0)
            P._tube(bm, (hx + 0.03, s * WH * 0.13, WH * 0.32), (hx + 0.06, s * WH * 0.13, 0.0), WH * 0.045, WH * 0.035, n=5, mat=0)
        # antlers: a beam with two tines
        base = Vector((L * 0.47, s * WH * 0.05, back + WH * 0.50))
        tip = base + Vector((-0.12, s * 0.16, 0.42))
        P._tube(bm, base, tip, 0.03, 0.015, n=4, mat=1)
        P._tube(bm, base + (tip - base) * 0.5, base + (tip - base) * 0.5 + Vector((0.16, s * 0.06, 0.18)), 0.02, 0.01, n=4, mat=1)
        P._tube(bm, tip, tip + Vector((0.14, s * 0.04, 0.12)), 0.018, 0.01, n=4, mat=1)
    _box(bm, 0.12, 0.08, 0.18, (-L * 0.36, 0, back + 0.02), mat=0)                                           # tail


def make(name, build, mats, rnd, **kw):
    bm = bmesh.new(); build(bm, rnd, **kw); return P.make_object(name, bm, mats)


# ---------------------------------------------------------------------------- the dressing kit (docs/16-look.md §5 "Dressing", V9)
def fence(bm, rnd, length=6.0, posts=4):
    """A post-and-rail run along +X, base at z=0. mats [timber]."""
    for k in range(posts):
        x = -length / 2 + k * length / (posts - 1)
        _box(bm, 0.14, 0.14, 1.1, (x, 0, 0.55), mat=0)
    for z in (0.45, 0.85): _box(bm, length, 0.06, 0.10, (0, 0, z), mat=0)


def cart(bm, rnd):
    """A two-wheel hand cart, shafts down. mats [timber, iron]."""
    _box(bm, 1.6, 1.0, 0.08, (0, 0, 0.62), mat=0)
    for y in (-0.5, 0.5): _box(bm, 1.6, 0.06, 0.32, (0, y, 0.80), mat=0)
    _box(bm, 0.06, 1.0, 0.32, (0.8, 0, 0.80), mat=0)
    for y in (-0.62, 0.62): P._cyl(bm, 0.42, 0.08, 12, (0, y, 0.42), mat=1); 
    for s in (1, -1): P._tube(bm, (-0.8, s * 0.35, 0.62), (-1.9, s * 0.3, 0.12), 0.04, 0.03, n=5, mat=0)


def barrels(bm, rnd, n=3):
    """A cluster of barrels with iron hoops. mats [timber, iron]."""
    for k in range(n):
        a = k / n * math.tau; x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
        P._cyl(bm, 0.32, 0.9, 10, (x, y, 0.45), r_top=0.30, mat=0)
        for z in (0.2, 0.7): P._cyl(bm, 0.335, 0.05, 10, (x, y, z), mat=1)


def rack(bm, rnd):
    """A drying rack with three hanging cloths / fish. mats [timber, cloth]."""
    for x in (-1.0, 1.0): P._cyl(bm, 0.06, 1.8, 6, (x, 0, 0.9), mat=0)
    _box(bm, 2.2, 0.08, 0.08, (0, 0, 1.75), mat=0)
    for x in (-0.6, 0.0, 0.6): _box(bm, 0.45, 0.05, rnd.uniform(0.6, 0.9), (x, 0.03, 1.3), mat=1)


def woodpile(bm, rnd):
    """Split logs stacked between two posts. mats [timber]."""
    for x in (-0.9, 0.9): _box(bm, 0.12, 0.12, 1.1, (x, 0, 0.55), mat=0)
    for row in range(4):
        for k in range(5):
            P._tube(bm, (-0.8 + k * 0.4 + (row % 2) * 0.2, -0.45, 0.12 + row * 0.24), (-0.8 + k * 0.4 + (row % 2) * 0.2, 0.45, 0.12 + row * 0.24), 0.11, 0.11, n=6, mat=0)


def haystack(bm, rnd):
    """A round stack on a pole. mats [hay, timber]."""
    P._blob(bm, (0, 0, 1.1), 1.3, (1.0, 1.0, 0.9), 0.12, 4.0, sub=2, mat=0, smooth=True)
    P._cyl(bm, 0.05, 3.2, 6, (0, 0, 1.6), mat=1)


def smoke(bm, rnd, h=9.0):
    """A chimney's smoke: a soft cone the volume shader fills, base at the chimney top (z = 0). mats [smokevol]."""
    P._cyl(bm, 0.35, h, 10, (0.6, 0.2, h / 2), r_top=2.2, mat=0, smooth=True)


def sheep(bm, rnd):
    """A small woolly quadruped. mats [wool, dark]."""
    P._blob(bm, (0, 0, 0.62), 0.42, (1.5, 0.9, 0.85), 0.15, 8.0, sub=1, mat=0, smooth=True)
    P._blob(bm, (0.58, 0, 0.72), 0.16, (1.3, 0.8, 0.9), 0.05, 9.0, sub=1, mat=1, smooth=True)
    for s in (1, -1):
        for x in (0.3, -0.3): P._tube(bm, (x, s * 0.16, 0.5), (x, s * 0.17, 0.0), 0.045, 0.04, n=4, mat=1)
