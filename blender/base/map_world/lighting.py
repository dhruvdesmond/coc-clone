"""The world map's light, sky, clouds and haze -- docs/16-look.md §4, written once here so every render uses one rig.

    lighting.rig(scene, W, D, wind=(1, 0.3), clouds=True, haze=True)

Sun high (62°) with a wide disc, a multiple-scattering sky as the fill that turns shadows blue-grey, one cool shadowless
fill lamp from behind (Kargil's sky-fill rig, in Cycles), a cloud slab that casts real shadows and drifts with the wind,
and a thin world volume so far land goes pale and blue. Exposure is set for a white point of 0.5-2 % (measure.py checks).
"""
import math
import bpy
from mathutils import Vector

D, C = bpy.data, bpy.context

SUN_ELEV, SUN_AZ, SUN_ENERGY, SUN_ANGLE = 62.0, 205.0, 3.2, 6.0
SKY_STRENGTH = 0.7
FILL_ENERGY, FILL_COLOR = 0.35, (0.75, 0.85, 1.0)
HAZE_DENSITY, HAZE_COLOR = 0.0035, (0.60, 0.72, 0.85)
EXPOSURE = -1.25


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


def haze(nt, out):
    """A thin world volume: distance reads as depth (V14). Height falloff keeps the sky itself clear."""
    vol = nt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Color"].default_value = (*HAZE_COLOR, 1.0)
    vol.inputs["Density"].default_value = HAZE_DENSITY
    try: vol.inputs["Anisotropy"].default_value = 0.35
    except Exception: pass
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])


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
    if with_haze: haze(nt, out)
    if with_clouds: clouds(scene, W, Dp, wind)
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = EXPOSURE
    try:
        scene.cycles.volume_step_rate = 1.0; scene.cycles.volume_max_steps = 256; scene.cycles.volume_bounces = 1
    except Exception as ex: print("[light] volume settings:", ex)
    print(f"[light] sun {SUN_ELEV}° az {SUN_AZ}° e{SUN_ENERGY} · sky {SKY_STRENGTH} · fill {FILL_ENERGY} · haze {HAZE_DENSITY if with_haze else 0} · clouds {with_clouds} · exposure {EXPOSURE}")
