"""Export every shared material palette to JSON for Unity.

    blender -b --factory-startup --python scripts/export_palette.py -- --out <dir>

Builds kit() / modern_kit() / terrain_kit() / troop_kit() and walks each material's
node tree to read a representative Base Color, Roughness and Metallic off the
Principled BSDF.

WHY THIS EXISTS
    Procedural Blender materials cannot be exported. Unity rebuilds them from flat
    values instead. Previously the Unity side kept its own hand-written table and the
    two drifted -- seven Norse materials silently arrived unmapped. This script makes
    lib/materials.py the single authority.

COLOUR SPACE
    Values are written RAW, exactly as authored for Cycles (linear, viewed through
    AgX). The tone correction pow(v, TONE_EXPONENT) is NOT applied here -- it is
    applied once, in Unity, to every surface. Applying it in two places, or to some
    surfaces and not others, is the bug that produced orange timber on mint grass.
"""
import bpy, sys, os, json, pathlib

sys.path.insert(0, "/Users/dhruv/blender")
sys.path.insert(0, "/Users/dhruv/blender/lib")  # lib modules import each other flat
import materials as M   # noqa: E402

TONE_EXPONENT = 0.62
FALLBACK = (0.5, 0.5, 0.5)


def _argv():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


def _rgb(v):
    return (round(float(v[0]), 5), round(float(v[1]), 5), round(float(v[2]), 5))


def _probe_color(socket, depth=0):
    """A representative flat colour for a socket that may be driven by a node tree.

    Procedural materials link Base Color to noise/ramp/mix networks. Unity gets one
    flat colour per material, so walk upstream and pick a sensible middle value.
    """
    if depth > 12:
        return FALLBACK
    if not socket.is_linked:
        return _rgb(socket.default_value)

    n = socket.links[0].from_node
    t = n.bl_idname

    if t == "ShaderNodeRGB":
        return _rgb(n.outputs[0].default_value)

    if t == "ShaderNodeValToRGB":                      # ColorRamp -> midpoint
        return _rgb(n.color_ramp.evaluate(0.5))

    if t in ("ShaderNodeMixRGB", "ShaderNodeMix"):     # blend the two branches
        ins = [s for s in n.inputs if s.type == "RGBA"]
        if len(ins) >= 2:
            a, b = _probe_color(ins[0], depth + 1), _probe_color(ins[1], depth + 1)
            fac = n.inputs["Fac"] if "Fac" in n.inputs else None
            f = 0.5 if (fac is None or fac.is_linked) else float(fac.default_value)
            if n.bl_idname == "ShaderNodeMixRGB" and n.blend_type == "MULTIPLY":
                # multiply against a noise mask averages to roughly the base colour
                return a
            return tuple(round(a[i] * (1 - f) + b[i] * f, 5) for i in range(3))

    if t in ("ShaderNodeBrightContrast", "ShaderNodeHueSaturation",
             "ShaderNodeGamma", "ShaderNodeInvert"):
        for s in n.inputs:
            if s.type == "RGBA":
                return _probe_color(s, depth + 1)

    for s in n.inputs:                                  # last resort: first colour in
        if s.type == "RGBA":
            return _probe_color(s, depth + 1)
    return FALLBACK


def _scalar(socket, default):
    if socket is None:
        return default
    if socket.is_linked:
        n = socket.links[0].from_node
        if n.bl_idname == "ShaderNodeValue":
            return round(float(n.outputs[0].default_value), 4)
        return default
    return round(float(socket.default_value), 4)


def describe(mat):
    if not mat.use_nodes:
        return None
    bsdf = next((n for n in mat.node_tree.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        return None
    return {
        "albedo":  list(_probe_color(bsdf.inputs["Base Color"])),
        "rough":   _scalar(bsdf.inputs.get("Roughness"), 0.75),
        "metal":   _scalar(bsdf.inputs.get("Metallic"), 0.0),
        "emissive": _scalar(bsdf.inputs.get("Emission Strength"), 0.0),
    }


def main():
    args = _argv()
    out = args[args.index("--out") + 1] if "--out" in args else "/Users/dhruv/blender/export"
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)

    kits = {"norse": M.kit, "modern": M.modern_kit,
            "terrain": M.terrain_kit, "troop": M.troop_kit}

    entries, by_kit, failed = {}, {}, []
    for kit_name, fn in kits.items():
        try:
            built = fn(force=True)
        except Exception as e:                                   # noqa: BLE001
            failed.append(f"{kit_name}: {e}")
            continue
        names = []
        for key, mat in built.items():
            if mat is None:
                continue
            d = describe(mat)
            if d is None:
                failed.append(f"{kit_name}.{key} ({mat.name}): no Principled BSDF")
                continue
            if mat.name in entries and entries[mat.name]["albedo"] != d["albedo"]:
                failed.append(f"DUPLICATE NAME with different values: {mat.name}")
            d["kit"] = kit_name
            d["key"] = key
            entries[mat.name] = d
            names.append(mat.name)
        by_kit[kit_name] = sorted(names)

    doc = {
        "_comment": "GENERATED by blender/scripts/export_palette.py. Do not hand-edit. "
                    "Colours are raw linear Cycles values; Unity applies pow(v, toneExponent) "
                    "to EVERY surface exactly once.",
        "toneExponent": TONE_EXPONENT,
        "count": len(entries),
        "kits": by_kit,
        "materials": entries,
    }
    path = os.path.join(out, "palette.json")
    with open(path, "w") as f:
        json.dump(doc, f, indent=2, sort_keys=True)

    print(f"\n[palette] wrote {path}")
    print(f"[palette] {len(entries)} materials across {len(by_kit)} kits")
    for k, v in by_kit.items():
        print(f"[palette]   {k:8} {len(v):2}  {', '.join(v)}")
    if failed:
        print("\n[palette] PROBLEMS:")
        for x in failed:
            print("[palette]   ! " + x)
        sys.exit(1)
    print("[palette] OK")


main()
