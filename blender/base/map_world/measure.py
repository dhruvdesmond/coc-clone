"""Measure a render (or a reference) so the look is judged by numbers, not taste (plan B25, docs/16-look.md).

    blender -b --factory-startup --python blender/base/map_world/measure.py -- img1.png img2.jpeg ...

Prints, per image: luma percentiles (p5 / p50 / p95), the white point (% of pixels above 250), the black floor (% below 12),
the SHADOW tone (mean colour and hue of the darkest 15 % of ground pixels -- blue-grey passes, black fails), mean saturation,
the spread of ground tones (how many distinct hue-luma bins hold >1 % of pixels: a painted meadow has many, a flat green has
two), and the dominant colours (k-means, 6 seeds) so a palette can be READ off a reference.
Uses Blender's Python only for image loading; the maths is numpy.
"""
import sys, os
import numpy as np
import bpy


def load(path):
    img = bpy.data.images.load(os.path.abspath(path))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3]
    if img.colorspace_settings.name != "sRGB": pass
    return np.clip(px, 0, 1)          # display-referred sRGB floats


def srgb_to_lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def stats(px, name):
    lin = srgb_to_lin(px)
    luma = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    l8 = px.max(axis=2) * 255
    mx, mn = px.max(axis=2), px.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    # hue in degrees
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    # the darkest 15 % by luma: what colour are the shadows?
    thr = np.percentile(luma, 15)
    sh = px[luma <= thr]
    sh_mean = sh.mean(axis=0)
    sh_hue = float(np.degrees(np.arctan2(*[np.mean(f(np.radians(hue[luma <= thr]))) for f in (np.sin, np.cos)])) % 360)
    # tone spread: hue (12 bins) x luma (5 bins), count bins holding > 1 % of pixels
    hb = (hue // 30).astype(int).ravel(); lb = np.minimum((luma * 5).astype(int), 4).ravel()
    bins = np.bincount(hb * 5 + lb, minlength=60) / hb.size
    spread = int((bins > 0.01).sum())
    # dominant colours, 6 seeds, 8 iterations of k-means on a 40k-pixel sample
    rng = np.random.default_rng(3); samp = px.reshape(-1, 3)[rng.choice(px.shape[0] * px.shape[1], 40000, replace=False)]
    cent = samp[rng.choice(40000, 6, replace=False)].copy()
    for _ in range(8):
        lab = np.argmin(((samp[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2), axis=1)
        for k in range(6):
            if (lab == k).any(): cent[k] = samp[lab == k].mean(axis=0)
    share = np.bincount(lab, minlength=6) / lab.size
    order = np.argsort(-share)
    print(f"== {name}  {px.shape[1]}x{px.shape[0]}")
    print(f"   luma p5/p50/p95 (linear): {np.percentile(luma, 5):.3f} / {np.percentile(luma, 50):.3f} / {np.percentile(luma, 95):.3f}")
    print(f"   white point >250: {100 * (l8 > 250).mean():.2f} %   black floor <12: {100 * (l8 < 12).mean():.2f} %")
    print(f"   shadows (darkest 15 %): mean sRGB ({sh_mean[0]:.2f}, {sh_mean[1]:.2f}, {sh_mean[2]:.2f}) hue {sh_hue:.0f}°  -> {'blue-grey' if 180 <= sh_hue <= 260 else 'green' if 70 < sh_hue < 180 else 'warm/neutral'}")
    print(f"   mean saturation: {sat.mean():.2f}   tone spread (bins >1 %): {spread}")
    print("   dominant: " + "  ".join(f"({cent[k][0]:.2f},{cent[k][1]:.2f},{cent[k][2]:.2f}) {100 * share[k]:.0f}%" for k in order))
    return dict(sat=float(sat.mean()), sh_luma=float(np.percentile(luma, 15)), sh_hue=sh_hue, white=float(100 * (l8 > 250).mean()),
                black=float(100 * (l8 < 12).mean()), spread=spread, p50=float(np.percentile(luma, 50)))


def score(px, name="crop"):
    """The numeric rows of the look table (docs/16-look.md §5) as pass/fail marks."""
    s = stats(px, name)
    s["sat_ok"] = "✅" if s["sat"] >= 0.45 else "❌"
    s["sh_ok"] = "✅" if s["sh_luma"] >= 0.04 and (180 <= s["sh_hue"] <= 260 or s["sh_hue"] < 70 or s["sh_hue"] > 300) else "❌"
    s["white_ok"] = "✅" if 0.5 <= s["white"] <= 2.0 else "❌"
    s["black_ok"] = "✅" if s["black"] < 0.3 else "❌"
    s["spread_ok"] = "✅" if s["spread"] >= 10 else "❌"
    s["p50_ok"] = "✅" if 0.12 <= s["p50"] <= 0.35 else "❌"
    s["passed"] = sum(1 for k in ("sat_ok", "sh_ok", "white_ok", "black_ok", "spread_ok", "p50_ok") if s[k] == "✅")
    return s


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for p in args:
        stats(load(p), os.path.basename(p))
