using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>Height, slope and "is this land" queries against the terrain collider. No layers needed.</summary>
    public static class Ground
    {
        public static Collider[] colliders = new Collider[0];
        public const float SeaLevel = 0f;

        public static bool Sample(float x, float z, out float y, out Vector3 normal)
        {
            var ray = new Ray(new Vector3(x, 200f, z), Vector3.down);
            foreach (var c in colliders)
                if (c != null && c.Raycast(ray, out var hit, 400f)) { y = hit.point.y; normal = hit.normal; return true; }
            y = 0f; normal = Vector3.up; return false;
        }

        public static float Height(float x, float z) => Sample(x, z, out var y, out _) ? y : 0f;
        public static Vector3 At(Vec2 p) => new Vector3(p.x, Height(p.x, p.z), p.z);
        public static Vector3 At(float x, float z) => new Vector3(x, Height(x, z), z);
        public static Vec2 ToSim(Vector3 v) => new Vec2(v.x, v.z);

        public static bool Raycast(Ray ray, out Vector3 point)
        {
            foreach (var c in colliders)
                if (c != null && c.Raycast(ray, out var hit, 2000f)) { point = hit.point; return true; }
            point = default; return false;
        }

        /// <summary>How far a wall must stay from the waterline, and how far above it the ground must be.</summary>
        public const float ShoreMargin = 1.2f, DryHeight = 0.25f;

        /// <summary>The WHOLE footprint, sampled every ~2 m across the turned rectangle plus a shore margin: null if a building
        /// can stand there, otherwise why not. The old test sampled a circle of 8 points, and a longhouse is not a circle --
        /// its gable stood in the lake with all nine samples dry (PENDING B1).</summary>
        public static string FootprintProblem(Vec2 centre, float rot, Vec2 half)
        {
            // 1. the SHORE: the outline pushed out by the margin must be dry. Water only -- a first version also measured slope
            //    out here, over a lower threshold, and the bot could no longer find anywhere to put a farm (2,175 refusals a minute).
            float mx = half.x + ShoreMargin, mz = half.z + ShoreMargin;
            int ex = Mathf.Max(2, Mathf.CeilToInt(2f * mx / 2.5f)), ez = Mathf.Max(2, Mathf.CeilToInt(2f * mz / 2.5f));
            for (int i = 0; i <= ex; i++)
                for (int side = -1; side <= 1; side += 2)
                { string p = Wet(Footprint.ToWorld(new Vec2(Mathf.Lerp(-mx, mx, i / (float)ex), side * mz), centre, rot)); if (p != null) return p; }
            for (int j = 1; j < ez; j++)
                for (int side = -1; side <= 1; side += 2)
                { string p = Wet(Footprint.ToWorld(new Vec2(side * mx, Mathf.Lerp(-mz, mz, j / (float)ez)), centre, rot)); if (p != null) return p; }

            // 2. the FLOOR: every ~2.5 m across the footprint itself -- dry, and no steeper than about ten degrees corner to corner
            int nx = Mathf.Max(3, Mathf.CeilToInt(2f * half.x / 2.5f) + 1), nz = Mathf.Max(3, Mathf.CeilToInt(2f * half.z / 2.5f) + 1);
            float lo = float.MaxValue, hi = float.MinValue;
            for (int i = 0; i < nx; i++)
                for (int j = 0; j < nz; j++)
                {
                    var p = Footprint.ToWorld(new Vec2(Mathf.Lerp(-half.x, half.x, i / (nx - 1f)), Mathf.Lerp(-half.z, half.z, j / (nz - 1f))), centre, rot);
                    if (!Sample(p.x, p.z, out float y, out _)) return "Off the edge of the map";
                    if (y < SeaLevel + DryHeight) return "Too close to water";
                    lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y);
                }
            float diagonal = 2f * Mathf.Sqrt(half.x * half.x + half.z * half.z);
            return hi - lo > 0.17f * diagonal + 0.3f ? "Ground too steep" : null;
        }

        static string Wet(Vec2 p) => !Sample(p.x, p.z, out float y, out _) ? "Off the edge of the map" : y < SeaLevel + DryHeight ? "Too close to water" : null;

        /// <summary>Buildable: on the map, above water, and flat enough across the whole footprint.</summary>
        public static bool SiteOk(Vec2 p, float radius)
        {
            if (!Sample(p.x, p.z, out float y0, out var n0) || y0 < SeaLevel + 0.25f) return false;
            if (Vector3.Angle(n0, Vector3.up) > 16f) return false;
            float lo = y0, hi = y0;
            for (int i = 0; i < 8; i++)
            {
                float a = i * Mathf.PI / 4f;
                if (!Sample(p.x + Mathf.Cos(a) * radius, p.z + Mathf.Sin(a) * radius, out float y, out _)) return false;
                if (y < SeaLevel + 0.2f) return false;
                lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y);
            }
            return hi - lo < 0.22f * radius + 0.5f;
        }
    }
}
