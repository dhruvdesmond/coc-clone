"""The 30-second flythrough (plan B25 Phase G) -- the one job that loads the GPU near 100 %, and the only proof that the
water, the clouds and the storms MOVE.  Opens the map the last build saved (map_world.blend: every driver in the light rig
and the water reads the frame), flies a camera along a path through everything the look doc names, renders a PNG sequence,
and assembles an MP4 with ffmpeg if it is on the box.

    blender -b --factory-startup --python-exit-code 1 --python blender/base/map_world/showcase.py -- [--seconds 30] [--fps 24] [--spp 128] [--res 1920x1080] [--every 1]

    --every 24   renders every 24th frame only: a contact sheet in a minute, to check the path before the full job
"""
import bpy, math, os, sys, time, subprocess, shutil
from mathutils import Vector

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = lambda k, d: args[args.index(k) + 1] if k in args else d
SECONDS, FPS, SPP = float(opt("--seconds", 30)), int(opt("--fps", 24)), int(opt("--spp", 128))
RX, RY = (int(v) for v in opt("--res", "1920x1080").split("x"))
EVERY = int(opt("--every", 1))
OUT = os.path.join(SCENE_DIR, "renders", "showcase")

bpy.ops.wm.open_mainfile(filepath=os.path.join(SCENE_DIR, "map_world.blend"))
scene = bpy.context.scene
D, C = bpy.data, bpy.context

# ---- the path: (time s, camera position, look-at) -- docs/09's sequence, for the Blender-only world
PATH = [
    (0.0,  (40, -235, 30),   (30, -150, 2)),       # low over the sea toward the fishing hamlet
    (4.0,  (20, -150, 40),   (-20, -90, 2)),       # over the hamlet, up the river valley
    (8.0,  (-30, -70, 48),   (-48, -56, 0)),       # the ford
    (11.0, (-56, -20, 42),   (-78, 16, 3)),        # the bridge
    (14.0, (-70, 30, 40),    (-40, 10, 4)),        # orbit the village...
    (17.0, (-10, 50, 44),    (-40, 10, 4)),
    (20.0, (10, -20, 52),    (62, 4, 0)),          # ...to the lake
    (23.0, (80, 40, 80),     (140, 120, 20)),      # the volcano
    (26.0, (-20, 80, 130),   (-140, 105, 30)),     # pull back to the massif in its snowstorm
    (30.0, (100, -40, 90),   (140, -120, 6)),      # end on the desert in its sandstorm
]
cam_d = D.cameras.new("Fly"); cam_d.lens = 32; cam_d.clip_end = 3000
cam = D.objects.new("Fly", cam_d); scene.collection.objects.link(cam)
aim = D.objects.new("FlyAim", None); scene.collection.objects.link(aim)
con = cam.constraints.new("TRACK_TO"); con.target = aim; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
for t, pos, look in PATH:
    f = int(round(t * FPS))
    cam.location = pos; cam.keyframe_insert("location", frame=f)
    aim.location = look; aim.keyframe_insert("location", frame=f)
for o in (cam, aim):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "BEZIER"; kp.easing = "AUTO"
scene.camera = cam
scene.frame_start, scene.frame_end = 0, int(SECONDS * FPS)
scene.frame_step = EVERY
scene.render.resolution_x, scene.render.resolution_y = RX, RY; scene.render.resolution_percentage = 100
scene.cycles.samples = SPP; scene.cycles.use_denoising = True; scene.render.use_persistent_data = True
scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_depth = "8"
os.makedirs(OUT, exist_ok=True)
scene.render.filepath = os.path.join(OUT, "f_")
print(f"SHOWCASE {SECONDS}s x {FPS} fps = {scene.frame_end + 1} frames, every {EVERY}, {RX}x{RY} @ {SPP} spp -> {OUT}", flush=True)
t0 = time.time()
bpy.ops.render.render(animation=True)
n = len([f for f in os.listdir(OUT) if f.startswith("f_") and f.endswith(".png")])
print(f"SHOWCASE rendered {n} frames in {time.time() - t0:.0f} s ({(time.time() - t0) / max(1, n):.1f} s/frame)", flush=True)
if EVERY == 1 and shutil.which("ffmpeg"):
    mp4 = os.path.join(SCENE_DIR, "renders", "showcase.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(OUT, "f_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4], capture_output=True)
    print("SHOWCASE mp4", "ok" if r.returncode == 0 else r.stderr.decode()[-300:], mp4, flush=True)
