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
