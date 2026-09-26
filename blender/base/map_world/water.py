"""The world map's water (plan B25 Phase E, docs/16-look.md §5 "Water"): a surface that moves.

    water.mesh(world, W, D, SEA, raw_h, obj_from_bm, res=4.0)  -> the water object with a "depth" attribute per vertex
    water.material(new_mat, ...)                              -> the shader

The old water was one 8-vertex box with a flat blue material. This one is a grid carrying the bed DEPTH under every vertex
(computed from raw_h at build), so the shader can ramp shallow teal to deep blue, put FOAM where the bed is within 0.5 m
(fords, the shore, the bridge piers, the lake edge), and drive two wave sets from the frame so the flythrough sees them
move and the sun glitter crawls. The same wave function as Unity's COA/Water (two sines, 6 s and 3.7 s periods).
"""
import bmesh, math
import bpy

D, C = bpy.data, bpy.context
SHALLOW, DEEP, FOAM = (0.22, 0.42, 0.46), (0.05, 0.16, 0.22), (0.92, 0.95, 0.96)


def mesh(world, W, Dp, SEA, raw_h, obj_from_bm, mat, res=4.0):
    bm = bmesh.new()
    nx, ny = int((W + 40) / res), int((Dp + 40) / res)
    x0, y0 = -(W + 40) / 2, -(Dp + 40) / 2
    grid = [[bm.verts.new((x0 + i * res, y0 + j * res, SEA - 0.03)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx): bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bm.verts.index_update()
    depth = bm.verts.layers.float.new("depth")
    for v in bm.verts: v[depth] = max(0.0, SEA - raw_h(v.co.x, v.co.y))          # 0 on land (the surface there is hidden by the ground)
    o = obj_from_bm(world, "Sea", bm, mat, bevel=0.0, smooth=True)
    return o


def material(new_mat, principled, noise_node, math_node, maprange, wind=(1.0, 0.3)):
    m, nt, out = new_mat("WorldWater")
    p = principled(nt, out, rough=0.06, spec=0.5)
    p.inputs["Base Color"].default_value = (*DEEP, 1)
    try: p.inputs["Transmission Weight"].default_value = 0.0
    except Exception: pass
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "depth"; at.location = (-1600, 300)
    dep = at.outputs["Fac"]
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-1200, 300); e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (*SHALLOW, 1); e[1].position, e[1].color = 1.0, (*DEEP, 1)
    dn = maprange(nt, dep, 0.0, 5.0, 0.0, 1.0, (-1400, 300)); nt.links.new(dn.outputs["Result"], ramp.inputs["Fac"])
    # waves: two animated noises pushed along the wind; the frame driver makes them move in the flythrough
    co = nt.nodes.new("ShaderNodeTexCoord"); co.location = (-1800, -200)
    off = nt.nodes.new("ShaderNodeCombineXYZ"); off.location = (-1800, -400)
    for sock, v in (("X", wind[0]), ("Y", wind[1])):
        drv = off.inputs[sock].driver_add("default_value").driver; drv.expression = f"frame * {v * 0.09:.4f}"
    add = nt.nodes.new("ShaderNodeVectorMath"); add.operation = "ADD"; add.location = (-1600, -300)
    nt.links.new(co.outputs["Object"], add.inputs[0]); nt.links.new(off.outputs["Vector"], add.inputs[1])
    w1 = noise_node(nt, add.outputs["Vector"], 0.35, 3.0, 0.5, (-1400, -200))
    w2 = noise_node(nt, add.outputs["Vector"], 1.6, 2.0, 0.5, (-1400, -450))
    ws = math_node(nt, "ADD", w1.outputs["Fac"], w2.outputs["Fac"], loc=(-1200, -300))
    bmp = nt.nodes.new("ShaderNodeBump"); bmp.location = (-900, -300); bmp.inputs["Strength"].default_value = 0.35; bmp.inputs["Distance"].default_value = 0.25
    nt.links.new(ws.outputs[0], bmp.inputs["Height"]); nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    # foam: where the bed is shallow, broken by the wave noise so it is not a hard line; also along the wave crests
    shallow = maprange(nt, dep, 0.55, 0.12, 0.0, 1.0, (-1400, 600))
    crest = maprange(nt, w2.outputs["Fac"], 0.62, 0.78, 0.0, 1.0, (-1200, 600))
    foam_s = math_node(nt, "MULTIPLY", shallow.outputs["Result"], crest.outputs["Result"], loc=(-1000, 600))
    foam_c = maprange(nt, ws.outputs[0], 1.30, 1.50, 0.0, 0.35, (-1000, 750))
    foam = math_node(nt, "MAXIMUM", foam_s.outputs[0], foam_c.outputs["Result"], loc=(-800, 650))
    # land verts (depth 0) would foam everywhere: mask them out
    isw = maprange(nt, dep, 0.0, 0.08, 0.0, 1.0, (-1000, 900)); foam2 = math_node(nt, "MULTIPLY", foam.outputs[0], isw.outputs["Result"], loc=(-650, 700))
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.location = (-400, 400)
    nt.links.new(foam2.outputs[0], mix.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], mix.inputs["Color1"]); mix.inputs["Color2"].default_value = (*FOAM, 1)
    nt.links.new(mix.outputs["Color"], p.inputs["Base Color"])
    rough = maprange(nt, foam2.outputs[0], 0.0, 1.0, 0.06, 0.6, (-400, 100)); nt.links.new(rough.outputs["Result"], p.inputs["Roughness"])
    return m
