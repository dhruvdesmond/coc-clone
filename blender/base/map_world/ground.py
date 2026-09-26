"""The world map's ground material, v2 -- docs/16-look.md §3 (palette) and §5 (the ground rows).

    ground.material(new_mat, principled, noise_node, math_node, maprange) -> bpy Material

Reads the terrain's "map" colour attribute: X = biome along the ramp, Y = road strength, Z = road kind / 3.
What it adds over v1 (one ramp times one noise):
  * a MEADOW that is painted, not flat: every ramp stop has a crest colour and a dip colour, mixed by a 20 m moisture noise
    (yellow-green crests, deeper green dips) -- the crest/dip pair is the "painted" look of the references;
  * ROAD EDGES: a worn straw shoulder each side of every road before the road colour itself; cobbles get sett joints;
  * DETAIL at 70 m: a 0.5 m brightness noise, a pebble mask (scree flecks) and a blade-scale bump;
  * SAND RIPPLES on the dunes, WET SAND at the shore, a MUD SHEEN in the marsh, SNOW BY ASPECT (north faces and hollows keep
    it, sun-facing ridges blow clear), rock on steep faces.
Every colour is from the palette table; nothing is tuned by eye in here.
"""
import math

PAL = {  # docs/16-look.md §3 -- (crest, dip) per ramp stop; the dip is the cooler, wetter, darker twin
    0.00: ((0.24, 0.20, 0.13), (0.18, 0.16, 0.11)),        # seabed
    0.14: ((0.62, 0.52, 0.34), (0.54, 0.44, 0.28)),        # sand, ochre
    0.28: ((0.55, 0.47, 0.22), (0.44, 0.40, 0.18)),        # dry steppe / worn
    0.42: ((0.42, 0.46, 0.12), (0.30, 0.38, 0.10)),        # meadow crest / dip
    0.50: ((0.26, 0.34, 0.10), (0.18, 0.26, 0.08)),        # marsh
    0.56: ((0.22, 0.32, 0.08), (0.14, 0.24, 0.06)),        # forest floor
    0.70: ((0.50, 0.48, 0.45), (0.40, 0.39, 0.37)),        # scree
    0.84: ((0.16, 0.14, 0.13), (0.11, 0.10, 0.09)),        # ash
    1.00: ((0.92, 0.94, 0.97), (0.78, 0.83, 0.90)),        # snow
}
ROAD = [(0.55, 0.47, 0.22), (0.38, 0.27, 0.15), (0.16, 0.11, 0.07), (0.34, 0.33, 0.30)]   # grass path, dirt, mud, cobbles
SHOULDER = (0.50, 0.44, 0.22)
SCREE = (0.50, 0.48, 0.45)
SNOW = (0.92, 0.94, 0.97)
ROCK = (0.46, 0.44, 0.41)


def _math(nt, op, a, b=None, loc=(0, 0)):
    """Math node whose inputs may be sockets OR numbers (nodeutils.math_node takes sockets only)."""
    m = nt.nodes.new("ShaderNodeMath"); m.location = loc; m.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): m.inputs[i].default_value = v
        else: nt.links.new(v, m.inputs[i])
    return m


def _ramp(nt, fac, stops, loc):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc; e = r.color_ramp.elements
    for _ in range(len(stops) - 2): e.new(0.5)
    for el, (pos, c) in zip(sorted(e, key=lambda s: s.position), stops):   # elements re-sort after new(): assign by sorted order
        el.position = pos; el.color = (*c, 1)
    nt.links.new(fac, r.inputs["Fac"]); return r


def _mix(nt, fac, a, b, loc, blend="MIX"):
    m = nt.nodes.new("ShaderNodeMixRGB"); m.location = loc; m.blend_type = blend
    if isinstance(fac, (int, float)): m.inputs["Fac"].default_value = fac
    else: nt.links.new(fac, m.inputs["Fac"])
    for sock, v in (("Color1", a), ("Color2", b)):
        if isinstance(v, tuple): m.inputs[sock].default_value = (*v, 1)
        else: nt.links.new(v, m.inputs[sock])
    return m


def material(new_mat, principled, noise_node, math_node, maprange):
    m, nt, out = new_mat("WorldGround")
    p = principled(nt, out, rough=0.92, spec=0.08)
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "map"; at.location = (-2200, 300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-2000, 300); nt.links.new(at.outputs["Color"], sep.inputs[0])
    biome, road_s, road_k = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-2200, -300); P = co.outputs["Object"]
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-2200, -700)
    nrm = nt.nodes.new("ShaderNodeSeparateXYZ"); nrm.location = (-2000, -700); nt.links.new(geo.outputs["Normal"], nrm.inputs[0])
    pos = nt.nodes.new("ShaderNodeSeparateXYZ"); pos.location = (-2000, -500); nt.links.new(P, pos.inputs[0])

    # 1. the painted base: crest ramp and dip ramp mixed by a 20 m moisture noise
    crest = _ramp(nt, biome, [(k, v[0]) for k, v in sorted(PAL.items())], (-1700, 500))
    dip = _ramp(nt, biome, [(k, v[1]) for k, v in sorted(PAL.items())], (-1700, 250))
    moist = noise_node(nt, P, 0.05, 3.0, 0.55, (-1900, 0)); mf = maprange(nt, moist.outputs["Fac"], 0.38, 0.62, 0.0, 1.0, (-1700, 0))
    base = _mix(nt, mf.outputs["Result"], crest.outputs["Color"], dip.outputs["Color"], (-1450, 400))

    # 2. detail at 70 m: 0.5 m brightness noise, pebble flecks, blade-scale bump
    fine = noise_node(nt, P, 2.2, 4.0, 0.6, (-1900, -150)); fv = maprange(nt, fine.outputs["Fac"], 0.35, 0.65, 0.80, 1.18, (-1700, -150))
    detailed = _mix(nt, 1.0, base.outputs["Color"], fv.outputs["Result"], (-1250, 400), blend="MULTIPLY")
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.location = (-1900, -350); vor.inputs["Scale"].default_value = 1.6
    nt.links.new(P, vor.inputs["Vector"])
    peb = maprange(nt, vor.outputs["Distance"], 0.05, 0.11, 1.0, 0.0, (-1700, -350))          # small cells' centres = pebbles
    # pebbles only on land that is not snow or water: biome 0.1..0.9
    pebband = maprange(nt, biome, 0.08, 0.16, 0.0, 1.0, (-1700, -450)); pebmask = _math(nt, "MULTIPLY", peb.outputs["Result"], pebband.outputs["Result"], loc=(-1500, -400))
    pebmask2 = _math(nt, "MULTIPLY", pebmask.outputs[0], 0.55, loc=(-1350, -400))
    pebbled = _mix(nt, pebmask2.outputs[0], detailed.outputs["Color"], SCREE, (-1100, 400))

    # 3. roads: a worn shoulder band, then the road colour; cobbles get sett joints
    kind = _ramp(nt, road_k, [(0.0, ROAD[0]), (1 / 3, ROAD[1]), (2 / 3, ROAD[2]), (1.0, ROAD[3])], (-1700, 800))
    sh = maprange(nt, road_s, 0.04, 0.38, 0.0, 1.0, (-1450, 900)); shouldered = _mix(nt, sh.outputs["Result"], pebbled.outputs["Color"], SHOULDER, (-900, 500))
    core = maprange(nt, road_s, 0.42, 0.80, 0.0, 1.0, (-1450, 750))
    sett = nt.nodes.new("ShaderNodeTexVoronoi"); sett.location = (-1700, 1050); sett.inputs["Scale"].default_value = 1.4
    try: sett.feature = "DISTANCE_TO_EDGE"
    except Exception: pass
    nt.links.new(P, sett.inputs["Vector"])
    joint = maprange(nt, sett.outputs["Distance"], 0.0, 0.07, 0.55, 1.0, (-1450, 1050))
    iscob = maprange(nt, road_k, 0.8, 1.0, 0.0, 1.0, (-1450, 1200))
    jointk = _mix(nt, iscob.outputs["Result"], (1.0, 1.0, 1.0), joint.outputs["Result"], (-1250, 1100))
    kind_j = _mix(nt, 1.0, kind.outputs["Color"], jointk.outputs["Color"], (-1100, 900), blend="MULTIPLY")
    roaded = _mix(nt, core.outputs["Result"], shouldered.outputs["Color"], kind_j.outputs["Color"], (-700, 500))

    # 4. sand ripples on the dunes (biome < 0.2), wet sand at the shore (z < 1.2), mud sheen in the marsh
    rip = _math(nt, "SINE", _math(nt, "ADD", _math(nt, "MULTIPLY", pos.outputs["X"], 1.3, loc=(-1900, -900)).outputs[0],
                                                     _math(nt, "MULTIPLY", pos.outputs["Y"], 0.5, loc=(-1900, -1000)).outputs[0], loc=(-1750, -950)).outputs[0], loc=(-1600, -950))
    ripv = maprange(nt, rip.outputs[0], -1.0, 1.0, 0.90, 1.08, (-1450, -950))
    sandband = maprange(nt, biome, 0.24, 0.10, 0.0, 1.0, (-1450, -1100))
    ripm = _mix(nt, sandband.outputs["Result"], (1.0, 1.0, 1.0), ripv.outputs["Result"], (-1250, -1000))
    rippled = _mix(nt, 1.0, roaded.outputs["Color"], ripm.outputs["Color"], (-500, 500), blend="MULTIPLY")
    wet = maprange(nt, pos.outputs["Z"], 1.4, 0.3, 0.0, 1.0, (-1450, -1250)); wetm = _math(nt, "MULTIPLY", wet.outputs["Result"], sandband.outputs["Result"], loc=(-1250, -1250))
    wetc = _mix(nt, wetm.outputs[0], rippled.outputs["Color"], (0.40, 0.33, 0.22), (-300, 500))

    # 5. snow by aspect and rock on steep faces: north faces (+Y normal) and flats keep snow; sun-facing ridges blow clear
    snowband = maprange(nt, biome, 0.86, 0.96, 0.0, 1.0, (-1450, -1450))
    aspect = _math(nt, "ADD", _math(nt, "MULTIPLY", nrm.outputs["Y"], 0.6, loc=(-1700, -1500)).outputs[0],
                       _math(nt, "MULTIPLY", nrm.outputs["Z"], 0.9, loc=(-1700, -1600)).outputs[0], loc=(-1550, -1550))
    snowk = maprange(nt, aspect.outputs[0], 0.35, 0.85, 0.0, 1.0, (-1400, -1550))
    snowf = _math(nt, "MULTIPLY", snowband.outputs["Result"], snowk.outputs["Result"], loc=(-1250, -1500))
    rocky = _mix(nt, snowband.outputs["Result"], wetc.outputs["Color"], ROCK, (-100, 500))              # the snow band's bare ground is rock
    snowed = _mix(nt, snowf.outputs[0], rocky.outputs["Color"], SNOW, (100, 500))
    steep = maprange(nt, nrm.outputs["Z"], 0.86, 0.58, 0.0, 1.0, (-1400, -1750))
    notsnow = _math(nt, "SUBTRACT", 1.0, snowf.outputs[0], loc=(-1250, -1750)); steepf = _math(nt, "MULTIPLY", steep.outputs["Result"], notsnow.outputs[0], loc=(-1100, -1750))
    final = _mix(nt, steepf.outputs[0], snowed.outputs["Color"], ROCK, (300, 500))
    nt.links.new(final.outputs["Color"], p.inputs["Base Color"])

    # roughness: mud and wet sand shine a little, snow is matte-bright
    marsh = maprange(nt, biome, 0.47, 0.50, 0.0, 1.0, (-1450, -1900)); marsh2 = maprange(nt, biome, 0.53, 0.50, 0.0, 1.0, (-1450, -2000))
    marshf = _math(nt, "MULTIPLY", marsh.outputs["Result"], marsh2.outputs["Result"], loc=(-1250, -1950))
    shine = _math(nt, "MAXIMUM", marshf.outputs[0], wetm.outputs[0], loc=(-1100, -1950))
    rough = maprange(nt, shine.outputs[0], 0.0, 1.0, 0.92, 0.45, (-900, -1950)); nt.links.new(rough.outputs["Result"], p.inputs["Roughness"])

    # bump: blade / grain scale plus the pebbles
    bn = noise_node(nt, P, 38.0, 8.0, 0.65, (-900, -700)); bmp = nt.nodes.new("ShaderNodeBump"); bmp.location = (-200, -600)
    bmp.inputs["Strength"].default_value = 0.42; bmp.inputs["Distance"].default_value = 0.06
    bsum = _math(nt, "ADD", bn.outputs["Fac"], pebmask2.outputs[0], loc=(-500, -650))
    nt.links.new(bsum.outputs[0], bmp.inputs["Height"]); nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    return m
