"""Sweep view-transform / look / exposure over the saved map and SCORE each, so the white-point and saturation fix
(plan B25, the two failing rows) is chosen from numbers, not taste.

    blender -b --factory-startup --python blender/base/map_world/looksweep.py -- [--crops village,desert_oil,hero]

Opens map_world.blend once and re-renders the chosen region crops small under each setting in SETTINGS, then prints the
measure.score() row for each. One build feeds the whole sweep (each crop is ~5-12 s), so a full colour exploration is minutes.
"""
import bpy, os, sys
SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCENE_DIR)
import measure

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = lambda k, d: args[args.index(k) + 1] if k in args else d
CROPS = opt("--crops", "village,desert_oil").split(",")

# (view_transform, look, exposure)
SETTINGS = [
    ("AgX", "AgX - Punchy", -1.4),               # current
    ("AgX", "AgX - Punchy", -0.8),               # brighter, to lift the white point
    ("AgX", "AgX - High Contrast", -1.0),
    ("Filmic", "High Contrast", -0.6),
    ("Standard", "None", -1.8),                  # no tone curve: saturated, clips easily -- the stylised option
    ("Standard", "None", -2.2),
]

bpy.ops.wm.open_mainfile(filepath=os.path.join(SCENE_DIR, "map_world.blend"))
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 640, 400
scene.cycles.samples = 48
out = os.path.join(SCENE_DIR, "renders", "sweep")
os.makedirs(out, exist_ok=True)
cams = {c: (bpy.data.objects.get("Hero") if c == "hero" else bpy.data.objects.get("R_" + c)) for c in CROPS}
missing = [c for c, o in cams.items() if o is None]
if missing:
    print("[sweep] cameras not found:", missing, "-- available:", [o.name for o in bpy.data.objects if o.name.startswith("R_")])

for vt, look, exp in SETTINGS:
    try:
        scene.view_settings.view_transform = vt
        scene.view_settings.look = look
    except Exception as e:
        print(f"[sweep] SKIP {vt}/{look}: {e}"); continue
    scene.view_settings.exposure = exp
    tag = f"{vt}_{look}_{exp}".replace(" ", "").replace("-", "")
    print(f"\n===== {vt} / {look} / exp {exp}")
    for c, cam in cams.items():
        if cam is None: continue
        scene.camera = cam
        p = os.path.join(out, f"{c}_{tag}.png")
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        s = measure.score(measure.load(p), f"{c} {tag}")
        print(f"   -> {c}: sat {s['sat']:.2f}{s['sat_ok']} white {s['white']:.2f}%{s['white_ok']} black {s['black']:.2f}%{s['black_ok']} median {s['p50']:.2f}{s['p50_ok']} = {s['passed']}/6")
print("\n[sweep] done", flush=True)
