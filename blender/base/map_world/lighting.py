"""The world map's light, sky, clouds and haze -- docs/16-look.md §4, written once here so every render uses one rig.

    lighting.rig(scene, W, D, wind=(1, 0.3), clouds=True, haze=True)

Sun high (62°) with a wide disc, a multiple-scattering sky as the fill that turns shadows blue-grey, one cool shadowless
fill lamp from behind (Kargil's sky-fill rig, in Cycles), a cloud slab that casts real shadows and drifts with the wind,
and a thin world volume so far land goes pale and blue. Exposure is set for a white point of 0.5-2 % (measure.py checks).
"""
import math, os
import bpy
from mathutils import Vector

D, C = bpy.data, bpy.context

SUN_ELEV, SUN_AZ, SUN_ENERGY, SUN_ANGLE = 62.0, 205.0, 4.5, 6.0     # sun over sky: shadows must exist (sky 0.7 + fill 0.35 flattened everything)
SKY_STRENGTH = 0.45
FILL_ENERGY, FILL_COLOR = 0.15, (0.75, 0.85, 1.0)
HAZE_DENSITY, HAZE_COLOR = 0.0004, (0.60, 0.72, 0.85)      # 0.0035 in a 260 m box washed every crop grey (saturation 0.16); 0.0007 still paled the far half
EXPOSURE = -2.0                                            # -1.25 pushed sand and meadow into AgX's desaturated top (desert saturation 0.05)


def _sun(name, elev, az, energy, angle, color=(1.0, 0.94, 0.82), shadow=True):
    ld = D.lights.new(name, "SUN"); ld.energy = energy; ld.angle = math.radians(angle); ld.color = color
    try: ld.use_shadow = shadow
    except Exception: pass
    o = D.objects.new(name, ld); C.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90.0 - elev), 0.0, math.radians(az))
    return o


def sky(scene):
    w = scene.world or D.worlds.new("World"); scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = SKY_STRENGTH
    sk = nt.nodes.new("ShaderNodeTexSky"); sk.sky_type = "MULTIPLE_SCATTERING"
    sk.sun_elevation = math.radians(SUN_ELEV); sk.sun_rotation = math.radians(SUN_AZ); sk.sun_disc = False
    sk.altitude = 300; sk.air_density = 1.2; sk.aerosol_density = 1.6; sk.ozone_density = 1.0
    try: sk.ground_albedo = 0.22
    except Exception: pass
    nt.links.new(sk.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return w, nt, out


def haze(scene, W, Dp, top=150.0):
    """Distance reads as depth (V14). A BOUNDED box of scattering volume over the land, thinning with height -- NOT a world
    volume: in Cycles a world volume attenuates the sun over an infinite path and the land goes black (measured: 98 % of
    pixels under 12/255 with a 0.0035 world haze)."""
    import bmesh
    me = D.meshes.new("HazeBox"); bm = bmesh.new()
    hx, hy = W * 1.4, Dp * 1.4
    vs = [bm.verts.new((x, y, z)) for x in (-hx, hx) for y in (-hy, hy) for z in (-20.0, top)]
    for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]: bm.faces.new([vs[i] for i in f])
    bm.to_mesh(me); bm.free()
    o = D.objects.new("Haze", me); C.scene.collection.objects.link(o)
    m = D.materials.new("HazeVolume"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Color"].default_value = (*HAZE_COLOR, 1.0)
    try: vol.inputs["Anisotropy"].default_value = 0.35
    except Exception: pass
    co = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(co.outputs["Object"], sep.inputs[0])
    fall = nt.nodes.new("ShaderNodeMapRange"); fall.inputs["From Min"].default_value = 0.0; fall.inputs["From Max"].default_value = top
    fall.inputs["To Min"].default_value = HAZE_DENSITY; fall.inputs["To Max"].default_value = HAZE_DENSITY * 0.15; fall.clamp = True
    nt.links.new(sep.outputs["Z"], fall.inputs["Value"]); nt.links.new(fall.outputs["Result"], vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"]); me.materials.append(m)
    return o


def clouds(scene, W, Dp, wind, base=420.0, thick=160.0, density=0.06, cover=0.42, seed=7):
    """A cloud slab: a box of scattering volume whose density is a wind-drifted noise. It casts shadows on the land,
    which is most of why a map reads as outdoors. `cover` 0..1 is roughly the sky fraction under cloud."""
    me = D.meshes.new("CloudSlab")
    import bmesh
    bm = bmesh.new()
    hx, hy, hz = W * 1.2, Dp * 1.2, thick / 2
    vs = [bm.verts.new((x, y, z)) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]: bm.faces.new([vs[i] for i in f])
    bm.to_mesh(me); bm.free()
    o = D.objects.new("Clouds", me); C.scene.collection.objects.link(o); o.location = (0, 0, base + thick / 2)
    m = D.materials.new("CloudVolume"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Color"].default_value = (0.95, 0.95, 0.97, 1.0)
    try: vol.inputs["Anisotropy"].default_value = 0.2
    except Exception: pass
    co = nt.nodes.new("ShaderNodeTexCoord")
    drift = nt.nodes.new("ShaderNodeVectorMath"); drift.operation = "ADD"
    # the wind: a per-frame offset driven from the scene frame so the flythrough sees the clouds move (frame * wind / 24)
    off = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, (sock, v) in enumerate(zip(("X", "Y", "Z"), (wind[0], wind[1], 0.0))):
        drv = off.inputs[sock].driver_add("default_value").driver; drv.expression = f"frame * {v * 0.35:.4f}"
    nt.links.new(co.outputs["Object"], drift.inputs[0]); nt.links.new(off.outputs["Vector"], drift.inputs[1])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.0035; n1.inputs["Detail"].default_value = 6.0
    n1.inputs["Roughness"].default_value = 0.62; n1.noise_dimensions = "3D"
    try: n1.inputs["Lacunarity"].default_value = 2.2
    except Exception: pass
    nt.links.new(drift.outputs["Vector"], n1.inputs["Vector"])
    # coverage: everything below the threshold is clear sky; the ramp above it gives the cloud a soft edge and a dense core
    ramp = nt.nodes.new("ShaderNodeMapRange"); ramp.inputs["From Min"].default_value = 0.62 - cover * 0.25
    ramp.inputs["From Max"].default_value = 0.62 - cover * 0.25 + 0.16; ramp.inputs["To Min"].default_value = 0.0; ramp.inputs["To Max"].default_value = density
    ramp.clamp = True
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Value"])
    # thinner at the slab's top and bottom so the cloud has a rounded form, not a slice
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(co.outputs["Object"], sep.inputs[0])
    prof = nt.nodes.new("ShaderNodeMath"); prof.operation = "ABSOLUTE"; nt.links.new(sep.outputs["Z"], prof.inputs[0])
    pr2 = nt.nodes.new("ShaderNodeMapRange"); pr2.inputs["From Min"].default_value = hz * 0.35; pr2.inputs["From Max"].default_value = hz
    pr2.inputs["To Min"].default_value = 1.0; pr2.inputs["To Max"].default_value = 0.0; pr2.clamp = True
    nt.links.new(prof.outputs[0], pr2.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; nt.links.new(ramp.outputs["Result"], mul.inputs[0]); nt.links.new(pr2.outputs["Result"], mul.inputs[1])
    nt.links.new(mul.outputs[0], vol.inputs["Density"]); nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    me.materials.append(m)
    o.visible_camera = True
    return o


def rig(scene, W, Dp, wind=(1.0, 0.3), with_clouds=True, with_haze=True):
    for o in list(D.objects):
        if o.type == "LIGHT": D.objects.remove(o)
    _sun("Sun", SUN_ELEV, SUN_AZ, SUN_ENERGY, SUN_ANGLE)
    _sun("SkyFill", 55.0, SUN_AZ + 180.0, FILL_ENERGY, 40.0, color=FILL_COLOR, shadow=False)
    w, nt, out = sky(scene)
    if with_haze: haze(scene, W, Dp)
    if with_clouds: clouds(scene, W, Dp, wind)
    if os.environ.get("STORMS", "1") == "1": storms(scene, wind)
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = EXPOSURE
    try:
        scene.cycles.volume_step_rate = 1.0; scene.cycles.volume_max_steps = 256; scene.cycles.volume_bounces = 1
    except Exception as ex: print("[light] volume settings:", ex)
    print(f"[light] sun {SUN_ELEV}° az {SUN_AZ}° e{SUN_ENERGY} · sky {SKY_STRENGTH} · fill {FILL_ENERGY} · haze {HAZE_DENSITY if with_haze else 0} · clouds {with_clouds} · exposure {EXPOSURE}")


def _volume_box(name, centre, size, color, density_socket_fn):
    """A box of scattering volume; `density_socket_fn(nt, coord_socket)` returns the density socket."""
    import bmesh
    me = D.meshes.new(name); bm = bmesh.new()
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    vs = [bm.verts.new((x, y, z)) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]: bm.faces.new([vs[i] for i in f])
    bm.to_mesh(me); bm.free()
    o = D.objects.new(name, me); C.scene.collection.objects.link(o); o.location = centre
    m = D.materials.new(name + "Vol"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Color"].default_value = (*color, 1.0)
    try: vol.inputs["Anisotropy"].default_value = 0.3
    except Exception: pass
    co = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(density_socket_fn(nt, co.outputs["Object"]), vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"]); me.materials.append(m)
    return o


def _drifting_noise(nt, coord, wind, speed, scale, detail, shear=0.0):
    """Noise pushed along the wind by the frame, optionally sheared so streaks lean downwind with height."""
    off = nt.nodes.new("ShaderNodeCombineXYZ")
    for sock, v in (("X", wind[0]), ("Y", wind[1])):
        drv = off.inputs[sock].driver_add("default_value").driver; drv.expression = f"frame * {v * speed:.4f}"
    add = nt.nodes.new("ShaderNodeVectorMath"); add.operation = "ADD"; nt.links.new(coord, add.inputs[0]); nt.links.new(off.outputs["Vector"], add.inputs[1])
    src = add.outputs["Vector"]
    if shear:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(src, sep.inputs[0])
        sx = nt.nodes.new("ShaderNodeMath"); sx.operation = "MULTIPLY_ADD"; nt.links.new(sep.outputs["Z"], sx.inputs[0]); sx.inputs[1].default_value = shear * wind[0]; nt.links.new(sep.outputs["X"], sx.inputs[2])
        sy = nt.nodes.new("ShaderNodeMath"); sy.operation = "MULTIPLY_ADD"; nt.links.new(sep.outputs["Z"], sy.inputs[0]); sy.inputs[1].default_value = shear * wind[1]; nt.links.new(sep.outputs["Y"], sy.inputs[2])
        cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(sx.outputs[0], cmb.inputs["X"]); nt.links.new(sy.outputs[0], cmb.inputs["Y"]); nt.links.new(sep.outputs["Z"], cmb.inputs["Z"])
        src = cmb.outputs["Vector"]
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.noise_dimensions = "3D"
    nt.links.new(src, n.inputs["Vector"])
    return n.outputs["Fac"]


def _height_fade(nt, coord, z0, z1):
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(coord, sep.inputs[0])
    r = nt.nodes.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = z0; r.inputs["From Max"].default_value = z1
    r.inputs["To Min"].default_value = 1.0; r.inputs["To Max"].default_value = 0.0; r.clamp = True
    nt.links.new(sep.outputs["Z"], r.inputs["Value"]); return r.outputs["Result"]


def storms(scene, wind=(1.0, 0.3), sand_centre=(140.0, -120.0), sand_size=(180.0, 180.0, 50.0), snow_centre=(-140.0, 120.0), snow_size=(180.0, 170.0, 90.0), snow_base=14.0):
    """docs/16-look.md §6: a SANDSTORM over the desert (amber, wind-sheared, dense near the ground) and a SNOWSTORM over the
    massif (white, fine, streaking off the ridges). Both drift with the shared wind so the whole sky moves one way."""
    def sand_density(nt, coord):
        f = _drifting_noise(nt, coord, wind, 0.6, 0.012, 5.0, shear=0.8)
        r = nt.nodes.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = 0.42; r.inputs["From Max"].default_value = 0.72
        r.inputs["To Min"].default_value = 0.0; r.inputs["To Max"].default_value = 0.06; r.clamp = True; nt.links.new(f, r.inputs["Value"])
        fade = _height_fade(nt, coord, 6.0, sand_size[2] / 2)
        m = nt.nodes.new("ShaderNodeMath"); m.operation = "MULTIPLY"; nt.links.new(r.outputs["Result"], m.inputs[0]); nt.links.new(fade, m.inputs[1]); return m.outputs[0]

    def snow_density(nt, coord):
        f = _drifting_noise(nt, coord, wind, 1.1, 0.05, 6.0, shear=1.4)
        r = nt.nodes.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = 0.48; r.inputs["From Max"].default_value = 0.70
        r.inputs["To Min"].default_value = 0.0; r.inputs["To Max"].default_value = 0.05; r.clamp = True; nt.links.new(f, r.inputs["Value"])
        fade = _height_fade(nt, coord, 10.0, snow_size[2] / 2)
        m = nt.nodes.new("ShaderNodeMath"); m.operation = "MULTIPLY"; nt.links.new(r.outputs["Result"], m.inputs[0]); nt.links.new(fade, m.inputs[1]); return m.outputs[0]

    s = _volume_box("Sandstorm", (sand_centre[0], sand_centre[1], sand_size[2] / 2 + 2.0), sand_size, (0.78, 0.60, 0.34), sand_density)
    n = _volume_box("Snowstorm", (snow_centre[0], snow_centre[1], snow_base + snow_size[2] / 2), snow_size, (0.92, 0.94, 0.98), snow_density)
    print("[light] storms: sandstorm over the desert, snowstorm over the massif, wind", wind)
    return s, n
