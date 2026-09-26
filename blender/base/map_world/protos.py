"""Prototype meshes for the world map: every tree, bush and rock kind is built ONCE here as a single mesh
(bmesh only -- no bpy.ops, no per-object Displace textures), then instanced thousands of times with obj.copy()
through mapgen.AssetLibrary.register()/place().  That is the difference between a 6-minute build (553 trees as
~2,000 bpy.ops objects) and a 1-minute one (2,000 trees as 2,000 copies of ~40 meshes).

Every prototype is authored at the origin with its base on z = 0 (rocks: centre on the origin), so a placement
coordinate means what it says and the AssetLibrary offset is zero.
"""
import bmesh, math
import bpy
from mathutils import Vector, Matrix, noise

D, C = bpy.data, bpy.context


def _tag(bm, start, mat, smooth):
    """Material slot + shading for every face created since `start`."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = mat
        f.smooth = smooth


def _cyl(bm, r, h, n, centre, r_top=None, mat=0, smooth=False):
    start = len(bm.faces)
    r_top = r if r_top is None else r_top
    cx, cy, cz = centre
    bot, top = [], []
    for i in range(n):
        a = i / n * math.tau
        bot.append(bm.verts.new((cx + math.cos(a) * r, cy + math.sin(a) * r, cz - h / 2)))
        top.append(bm.verts.new((cx + math.cos(a) * r_top, cy + math.sin(a) * r_top, cz + h / 2)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    _tag(bm, start, mat, smooth)


def _tube(bm, p0, p1, r0, r1, n=6, mat=0, smooth=True):
    """Tapered tube between two points -- trunks and limbs."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    vstart = len(bm.verts)
    _cyl(bm, r0, L, n, (0, 0, L / 2), r_top=r1, mat=mat, smooth=smooth)
    bm.verts.ensure_lookup_table()
    M = Matrix.Translation(p0) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[vstart:])


def _blob(bm, centre, radius, scale, amp, seed, sub=2, mat=1, smooth=True, freq=0.6):
    """Icosphere pushed in and out by 3D noise -- a canopy clump or a rock."""
    start = len(bm.faces)
    centre = Vector(centre)
    M = Matrix.Translation(centre) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=radius, matrix=M)
    off = Vector((seed * 7.1, seed * 3.7, seed * 5.3))
    for v in res["verts"]:
        d = v.co - centre
        L = d.length or 1.0
        nz = noise.noise((v.co + off) / (radius * freq))
        v.co += d / L * (nz * amp * radius)
    _tag(bm, start, mat, smooth)


# ---------------------------------------------------------------------------- the kinds
def fir(bm, h, tiers, rnd):
    """Conifer: mats [bark, needle]. Base at z=0."""
    _cyl(bm, h * 0.035, h * 0.45, 8, (0, 0, h * 0.225), r_top=h * 0.022, mat=0)
    for k in range(tiers):
        t = k / tiers
        z = h * (0.22 + 0.70 * t)
        r = h * 0.26 * (1.0 - 0.78 * t) + h * 0.03
        seg = h * (0.70 / tiers) * 1.55
        _cyl(bm, r * rnd.uniform(0.92, 1.08), seg, 9, (0, 0, z + seg / 2), r_top=r * 0.18, mat=1)


def broadleaf(bm, h, blobs, rnd, lean=0.10):
    """Deciduous: leaning trunk, two limbs, a cluster of noisy canopy blobs. mats [bark, leaf]."""
    tilt = Vector((rnd.uniform(-lean, lean), rnd.uniform(-lean, lean), 1.0)).normalized()
    top = tilt * (h * 0.58)
    _tube(bm, (0, 0, 0), top, h * 0.045, h * 0.02, n=6, mat=0)
    for b in range(2):
        a = rnd.uniform(0, math.tau)
        d = Vector((math.cos(a) * 0.7, math.sin(a) * 0.7, 0.75)).normalized()
        _tube(bm, top - tilt * h * 0.16, top + d * h * 0.16, h * 0.030, h * 0.015, n=5, mat=0)
    for k in range(blobs):
        a = rnd.uniform(0, math.tau)
        rad = h * rnd.uniform(0.115, 0.175)
        off = Vector((math.cos(a) * h * rnd.uniform(0.04, 0.20), math.sin(a) * h * rnd.uniform(0.04, 0.20), h * rnd.uniform(-0.04, 0.22)))
        _blob(bm, top + off, rad, (1.0, rnd.uniform(0.85, 1.15), rnd.uniform(0.72, 0.95)), 0.36, rnd.random() * 100, mat=1)


def bare(bm, h, branches, rnd):
    """Leafless tree: trunk plus forking limbs, one material."""
    _cyl(bm, h * 0.045, h * 0.62, 7, (0, 0, h * 0.31), r_top=h * 0.022, mat=0, smooth=True)

    def limb(p, direction, length, r, depth):
        end = p + direction * length
        _tube(bm, p, end, r, r * 0.35, n=5, mat=0)
        if depth > 0:
            for _ in range(2):
                d2 = (direction + Vector((rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), rnd.uniform(0.1, 0.5)))).normalized()
                limb(end, d2, length * rnd.uniform(0.55, 0.75), r * 0.6, depth - 1)

    top = Vector((0, 0, h * 0.60))
    for b in range(branches):
        a = b / branches * math.tau + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a) * 0.75, math.sin(a) * 0.75, rnd.uniform(0.55, 1.0))).normalized()
        limb(top + Vector((0, 0, rnd.uniform(-0.12, 0.12) * h)), d, h * rnd.uniform(0.22, 0.34), h * 0.028, 1)


def bush(bm, size, rnd, blobs=4):
    """Low shrub: a few noisy blobs, one material. Base at z=0."""
    for k in range(blobs):
        c = (rnd.uniform(-size * .5, size * .5), rnd.uniform(-size * .5, size * .5), size * rnd.uniform(0.3, 0.7))
        _blob(bm, c, size * rnd.uniform(0.5, 0.9), (1.0, rnd.uniform(0.8, 1.2), rnd.uniform(0.6, 0.85)), 0.30, rnd.random() * 100, mat=0)


def boulder(bm, rnd, flat=False, facets=2):
    """Angular rock of radius 1 around the origin: scale at placement. Faceted (flat shading) so it reads as rock."""
    if flat:
        sc = (rnd.uniform(1.1, 1.8), rnd.uniform(0.9, 1.5), rnd.uniform(0.32, 0.55))
    else:
        sc = (rnd.uniform(0.9, 1.4), rnd.uniform(0.85, 1.3), rnd.uniform(0.7, 1.15))
    _blob(bm, (0, 0, 0), 1.0, sc, 0.40, rnd.random() * 100, sub=facets, mat=0, smooth=False, freq=0.45)
    bm.verts.ensure_lookup_table()
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rnd.uniform(-0.25, 0.25), 3, 'X') @ Matrix.Rotation(rnd.uniform(-0.25, 0.25), 3, 'Y'), verts=bm.verts)


def make_object(name, bm, mats):
    """One mesh object, several material slots, not linked to any collection (AssetLibrary.register links it)."""
    me = D.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    return D.objects.new(name, me)
