"""The world map's ground material -- the CLEAN pass (PENDING B28, docs/16-look.md §5).

The earlier version chased richness with per-pixel noise, pebble flecks, a blade bump and sand ripples, and it read as MUDDY
and BUSY next to the clean plateau-builder reference. That reference wins by SUBTRACTION: flat colour blocks, no surface
grain, crisp road edges, tidy ambient occlusion. So this version is deliberately flat:

  * flat colour by biome, with ONE soft large-scale (30 m) crest/dip mix -- no fine grain, no pebbles, no bump on the flats;
  * CRISP roads: a hard-edged mask, four flat tones, no muddy falloff;
  * clean contact AO darkening only where geometry meets (an AO node), which "grounds" objects like the reference;
  * flat, high roughness everywhere except wet sand and mud, so surfaces read as solid colour, not plastic.

Reads the terrain's "map" attribute: X = biome along the ramp, Y = road strength, Z = road kind / 3.
"""
PAL = {  # (crest, dip) per biome stop; the dip is a subtle darker twin, mixed softly (flat, not noisy)
    0.00: ((0.24, 0.20, 0.13), (0.20, 0.17, 0.11)),        # seabed
    0.14: ((0.80, 0.54, 0.16), (0.68, 0.44, 0.14)),        # sand, saturated ochre
    0.28: ((0.58, 0.50, 0.20), (0.48, 0.42, 0.17)),        # dry steppe
    0.42: ((0.46, 0.56, 0.12), (0.34, 0.46, 0.10)),        # meadow crest / dip -- clean vivid green
    0.50: ((0.30, 0.40, 0.11), (0.22, 0.32, 0.09)),        # marsh
    0.56: ((0.24, 0.36, 0.09), (0.18, 0.28, 0.07)),        # forest floor
    0.70: ((0.52, 0.50, 0.47), (0.44, 0.42, 0.39)),        # scree
    0.84: ((0.17, 0.15, 0.14), (0.12, 0.11, 0.10)),        # ash
    1.00: ((0.93, 0.95, 0.98), (0.82, 0.86, 0.92)),        # snow
}
ROAD = [(0.60, 0.52, 0.26), (0.44, 0.32, 0.17), (0.20, 0.14, 0.09), (0.40, 0.39, 0.36)]   # path, dirt, mud, cobbles
SHOULDER = (0.54, 0.47, 0.22)
SNOW = (0.93, 0.95, 0.98)
ROCK = (0.48, 0.46, 0.43)


def _ramp(nt, fac, stops, loc):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc; r.color_ramp.interpolation = "LINEAR"; e = r.color_ramp.elements
    for _ in range(len(stops) - 2): e.new(0.5)
    for el, (pos, c) in zip(sorted(e, key=lambda s: s.position), stops):
        el.position = pos; el.color = (*c, 1)
    nt.links.new(fac, r.inputs["Fac"]); return r


def _mix(nt, fac, a, b, loc, blend="MIX"):
    mx = nt.nodes.new("ShaderNodeMixRGB"); mx.location = loc; mx.blend_type = blend
    if isinstance(fac, (int, float)): mx.inputs["Fac"].default_value = fac
    else: nt.links.new(fac, mx.inputs["Fac"])
    for sock, v in (("Color1", a), ("Color2", b)):
        if isinstance(v, tuple): mx.inputs[sock].default_value = (*v, 1)
        else: nt.links.new(v, mx.inputs[sock])
    return mx


def _mr(nt, src, fmin, fmax, tmin, tmax, loc):
    r = nt.nodes.new("ShaderNodeMapRange"); r.location = loc; r.clamp = True
    r.inputs["From Min"].default_value = fmin; r.inputs["From Max"].default_value = fmax
    r.inputs["To Min"].default_value = tmin; r.inputs["To Max"].default_value = tmax
    if src is not None: nt.links.new(src, r.inputs["Value"])
    return r


def _m(nt, op, a, b=None, loc=(0, 0)):
    n = nt.nodes.new("ShaderNodeMath"); n.location = loc; n.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n


def material(new_mat, principled, noise_node, math_node, maprange):
    m, nt, out = new_mat("WorldGround")
    p = principled(nt, out, rough=0.95, spec=0.04)               # flat, matte: no plastic sheen
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "map"; at.location = (-1800, 300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1600, 300); nt.links.new(at.outputs["Color"], sep.inputs[0])
    biome, road_s, road_k = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-1800, -200); P = co.outputs["Object"]
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1800, -600)
    nrm = nt.nodes.new("ShaderNodeSeparateXYZ"); nrm.location = (-1600, -600); nt.links.new(geo.outputs["Normal"], nrm.inputs[0])

    # 1. flat base: crest & dip ramps mixed by ONE soft variation -- no fine grain
    crest = _ramp(nt, biome, [(k, v[0]) for k, v in sorted(PAL.items())], (-1400, 500))
    dip = _ramp(nt, biome, [(k, v[1]) for k, v in sorted(PAL.items())], (-1400, 250))
    moist = noise_node(nt, P, 0.045, 2.0, 0.5, (-1600, 0)); mf = _mr(nt, moist.outputs["Fac"], 0.40, 0.60, 0.0, 1.0, (-1400, 0))
    base = _mix(nt, mf.outputs["Result"], crest.outputs["Color"], dip.outputs["Color"], (-1150, 400))

    # 2. CRISP roads: a shoulder band, then a hard-edged core; cobbles get flat sett joints
    kind = _ramp(nt, road_k, [(0.0, ROAD[0]), (1 / 3, ROAD[1]), (2 / 3, ROAD[2]), (1.0, ROAD[3])], (-1400, 800))
    sh = _mr(nt, road_s, 0.06, 0.30, 0.0, 1.0, (-1150, 900)); shouldered = _mix(nt, sh.outputs["Result"], base.outputs["Color"], SHOULDER, (-900, 500))
    core = _mr(nt, road_s, 0.40, 0.52, 0.0, 1.0, (-1150, 750))         # tight range = crisp edge
    sett = nt.nodes.new("ShaderNodeTexVoronoi"); sett.location = (-1400, 1050); sett.inputs["Scale"].default_value = 1.6
    try: sett.feature = "DISTANCE_TO_EDGE"
    except Exception: pass
    nt.links.new(P, sett.inputs["Vector"])
    joint = _mr(nt, sett.outputs["Distance"], 0.0, 0.05, 0.62, 1.0, (-1150, 1050))
    iscob = _mr(nt, road_k, 0.8, 1.0, 0.0, 1.0, (-1150, 1200))
    jointk = _mix(nt, iscob.outputs["Result"], (1.0, 1.0, 1.0), joint.outputs["Result"], (-950, 1100))
    kind_j = _mix(nt, 1.0, kind.outputs["Color"], jointk.outputs["Color"], (-800, 900), blend="MULTIPLY")
    roaded = _mix(nt, core.outputs["Result"], shouldered.outputs["Color"], kind_j.outputs["Color"], (-650, 500))

    # 3. snow by aspect and rock on steep faces -- clean, no noise
    snowband = _mr(nt, biome, 0.86, 0.96, 0.0, 1.0, (-1150, -400))
    aspect = _m(nt, "ADD", _m(nt, "MULTIPLY", nrm.outputs["Y"], 0.6, loc=(-1400, -450)).outputs[0],
                _m(nt, "MULTIPLY", nrm.outputs["Z"], 0.9, loc=(-1400, -550)).outputs[0], loc=(-1250, -500))
    snowk = _mr(nt, aspect.outputs[0], 0.35, 0.85, 0.0, 1.0, (-1100, -500))
    snowf = _m(nt, "MULTIPLY", snowband.outputs["Result"], snowk.outputs["Result"], loc=(-950, -450))
    rocky = _mix(nt, snowband.outputs["Result"], roaded.outputs["Color"], ROCK, (-450, 400))
    snowed = _mix(nt, snowf.outputs[0], rocky.outputs["Color"], SNOW, (-250, 400))
    steep = _mr(nt, nrm.outputs["Z"], 0.86, 0.58, 0.0, 1.0, (-1100, -650))
    notsnow = _m(nt, "SUBTRACT", 1.0, snowf.outputs[0], loc=(-950, -650)); steepf = _m(nt, "MULTIPLY", steep.outputs["Result"], notsnow.outputs[0], loc=(-800, -650))
    colored = _mix(nt, steepf.outputs[0], snowed.outputs["Color"], ROCK, (0, 400))

    # 4. clean contact AO: darken only where geometry meets, the tidy grounding the reference has
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.location = (-250, -100); ao.inputs["Distance"].default_value = 0.6
    aof = _mr(nt, ao.outputs["AO"], 0.4, 1.0, 0.72, 1.0, (0, -100))     # the AO node output is "AO", not "Fac", in Blender 5
    shaded = _mix(nt, 1.0, colored.outputs["Color"], aof.outputs["Result"], (200, 300), blend="MULTIPLY")
    nt.links.new(shaded.outputs["Color"], p.inputs["Base Color"])

    # 5. roughness: flat matte everywhere; mud and wet sand a little glossy so water reads
    marsh = _mr(nt, biome, 0.47, 0.50, 0.0, 1.0, (-1150, -900)); marsh2 = _mr(nt, biome, 0.53, 0.50, 0.0, 1.0, (-1150, -1000))
    marshf = _m(nt, "MULTIPLY", marsh.outputs["Result"], marsh2.outputs["Result"], loc=(-950, -950))
    wetsand = _mr(nt, biome, 0.16, 0.10, 0.0, 1.0, (-1150, -1100))
    shine = _m(nt, "MAXIMUM", marshf.outputs[0], wetsand.outputs["Result"], loc=(-800, -1000))
    rough = _mr(nt, shine.outputs[0], 0.0, 1.0, 0.95, 0.5, (-600, -1000)); nt.links.new(rough.outputs["Result"], p.inputs["Roughness"])
    return m
