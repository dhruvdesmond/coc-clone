"""The asserting review of the world map (plan, Phase 2): what got built, what did not, and whether each thing
stands where it should.  Called by build.py after placement; writes renders/REVIEW.md; returns ok.  The batch runs
Blender with --python-exit-code 1 and build.py raises on a failed review AFTER the renders, so the pictures exist
to look at and the batch rc still says FAIL.

`placed` is the list build.py collects: {kind, x, y, objs, name}.  `ctx` gives region(x, y), height(x, y),
raw_h(x, y), dry_flat(x, y, r), SEA, W, D.
"""
import os, re, time
import bpy
from mathutils import Vector

D, C = bpy.data, bpy.context

# kind -> (minimum count, allowed regions or "water" or "dry"); a region passes when its soft weight is >= 0.30.
# Rock-like kinds (rock, coal, uran) and small scatter (bush, dead) are placed half-buried on purpose: for them the check is
# "still shows above the ground", not floating/sunken.
BURIED_OK = ("rock", "coal", "uran", "bush", "dead", "rare", "dressing")
EXPECTED = {
    "tree":     (1200, ("grass", "forest", "mount")),
    "rock":     (80,  None),
    "bush":     (30,  None),
    "berry":    (24,  ("grass", "forest", "desert")),
    "stone":    (12,  ("grass", "mount", "forest", "volc")),
    "iron":     (12,  ("grass", "mount", "forest", "volc")),
    "coal":     (20,  ("mount",)),
    "uran":     (12,  ("volc",)),
    "oil":      (3,   ("desert",)),
    "salt":     (1,   ("desert",)),
    "shoal":    (16,  "water"),
    "dead":     (8,   ("volc", "desert")),
    "building": (28,  "dry"),
    "people":   (10,  "dry"),
    "bridge":   (1,   None),
    "pier":     (1,   None),
    "rare":     (18,  None),
    "rubber":   (6,   ("grass", "forest")),
    "deer":     (12,  ("forest", "grass")),
    "horse_wild": (5, ("grass", "desert")),
    "rig":      (1,   "water"),
    "whale":    (1,   "water"),
    "dressing": (60,  None),
}


def _bbox(objs):
    xs, ys, zs = [], [], []
    for o in objs:
        if o.type != 'MESH':
            continue
        M = o.matrix_world
        for c in o.bound_box:
            p = M @ Vector(c)
            xs.append(p.x); ys.append(p.y); zs.append(p.z)
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)) if xs else None


def run(placed, ctx, out_dir, t_build, device, extra_lines=()):
    C.view_layer.update()                                   # bound boxes of fresh copies are stale until this
    t0 = time.time()
    rows, fails = [], []
    by_kind = {}
    for p in placed:
        by_kind.setdefault(p["kind"], []).append(p)
    for kind, (need, where) in EXPECTED.items():
        items = by_kind.get(kind, [])
        bad_biome, floating, sunken, offmap = [], [], [], []
        for p in items:
            x, y = p["x"], p["y"]
            if abs(x) > ctx.W / 2 or abs(y) > ctx.D / 2:
                offmap.append(p["name"]); continue
            if where == "water":
                if ctx.raw_h(x, y) > ctx.SEA - 0.2: bad_biome.append(p["name"])
            elif where == "dry":                                     # on the FLATTENED ground (pads), above the water
                hh = ctx.height(x, y)
                if hh < ctx.SEA + 0.8: bad_biome.append(f"{p['name']}(h={hh:.2f}, raw={ctx.raw_h(x, y):.2f})")
            elif where:
                R = ctx.region(x, y)
                if max(R.get(k, 0.0) for k in where) < 0.30: bad_biome.append(p["name"])
            if where != "water" and kind not in ("bridge", "pier", "rig", "whale"):
                bb = _bbox(p["objs"])
                if bb:
                    gz = ctx.height(x, y)
                    if kind in BURIED_OK:
                        if bb[5] - gz < 0.05: sunken.append((p["name"], round(gz - bb[5], 2), "top", round(bb[5], 2), "ground", round(gz, 2), "at", round(x), round(y)))      # buried: nothing shows
                    else:
                        if bb[2] - gz > 0.6: floating.append((p["name"], round(bb[2] - gz, 2)))
                        if gz - bb[2] > 1.2: sunken.append((p["name"], round(gz - bb[2], 2)))
        found = len(items)
        ok = found >= need and not bad_biome and not floating and not sunken and not offmap
        why = []
        if found < need: why.append(f"only {found} of {need}")
        if bad_biome: why.append(f"{len(bad_biome)} in the wrong biome: {bad_biome[:3]}")
        if floating: why.append(f"{len(floating)} floating: {floating[:3]}")
        if sunken: why.append(f"{len(sunken)} sunken: {sunken[:3]}")
        if offmap: why.append(f"{len(offmap)} off-map: {offmap[:3]}")
        rows.append((kind, need, found, "PASS" if ok else "FAIL", "; ".join(why) or "-"))
        if not ok: fails.append(kind)
    # overlaps between buildings and between buildings and resource nodes (the B1 / B12 class of bug)
    solid = [p for p in placed if p["kind"] in ("building", "berry", "stone", "iron", "oil", "bridge", "pier")]
    boxes = [(p["name"], _bbox(p["objs"])) for p in solid]
    boxes = [(n, b) for n, b in boxes if b]
    overlaps = []
    for i in range(len(boxes)):
        ni, bi = boxes[i]
        for j in range(i + 1, len(boxes)):
            nj, bj = boxes[j]
            k = 0.80
            ax0, ay0 = (bi[0] + bi[3]) / 2 - (bi[3] - bi[0]) / 2 * k, (bi[1] + bi[4]) / 2 - (bi[4] - bi[1]) / 2 * k
            ax1, ay1 = (bi[0] + bi[3]) / 2 + (bi[3] - bi[0]) / 2 * k, (bi[1] + bi[4]) / 2 + (bi[4] - bi[1]) / 2 * k
            bx0, by0 = (bj[0] + bj[3]) / 2 - (bj[3] - bj[0]) / 2 * k, (bj[1] + bj[4]) / 2 - (bj[4] - bj[1]) / 2 * k
            bx1, by1 = (bj[0] + bj[3]) / 2 + (bj[3] - bj[0]) / 2 * k, (bj[1] + bj[4]) / 2 + (bj[4] - bj[1]) / 2 * k
            if not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0):
                overlaps.append((ni, nj))
    rows.append(("overlap", 0, len(overlaps), "PASS" if not overlaps else "FAIL", str(overlaps[:4]) if overlaps else "-"))
    if overlaps: fails.append("overlap")

    # what changed since the last committed review
    prev = {}
    path = os.path.join(out_dir, "REVIEW.md")
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r"\| (\w+) \| (\d+) \| (\d+) \|", line)
            if m: prev[m.group(1)] = int(m.group(3))
    ok = not fails
    lines = [f"# REVIEW — world map build {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", "",
             f"**{'PASS' if ok else 'FAIL: ' + ', '.join(fails)}** · {len(D.objects)} objects · build {t_build:.0f} s · review {time.time() - t0:.0f} s · device {device}", "",
             "| kind | expected | found | status | detail |", "|---|---|---|---|---|"]
    lines += [f"| {k} | {e} | {f} | {s} | {w} |" for k, e, f, s, w in rows]
    changed = [f"{k}: {prev[k]} → {f}" for k, e, f, s, w in rows if k in prev and prev[k] != f]
    lines += ["", "**Since the last review:** " + ("; ".join(changed) if changed else "no count changed" if prev else "first review"), ""]
    lines += list(extra_lines)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "PLACED.csv"), "w") as f:                    # every placement, for "what is THAT at (x, y)?"
        f.write("name,kind,x,y\n"); f.writelines(f"{p['name']},{p['kind']},{p['x']:.1f},{p['y']:.1f}\n" for p in placed)
    open(path, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[2:3] + lines[6:]), flush=True)
    print("REVIEW", "PASS" if ok else "FAIL", flush=True)
    return ok
