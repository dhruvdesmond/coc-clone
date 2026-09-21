using System;

namespace COA.Sim
{
    /// <summary>
    /// A building's footprint: a rectangle, turned. It used to be a circle, and a 15.8 x 9.3 m longhouse does not fit
    /// in its own 7.5 m circle -- both gables stuck out, one into a lake and one into a spruce (PENDING B1).
    /// `rot` is the building's yaw in degrees, the same number the view feeds to Quaternion.Euler(0, rot, 0).
    /// </summary>
    public static class Footprint
    {
        /// <summary>World offset -> the building's own axes (x along the ridge, z across it).</summary>
        public static Vec2 ToLocal(Vec2 p, Vec2 centre, float rot)
        {
            float a = rot * (float)Math.PI / 180f, c = (float)Math.Cos(a), s = (float)Math.Sin(a);
            float dx = p.x - centre.x, dz = p.z - centre.z;
            return new Vec2(dx * c - dz * s, dx * s + dz * c);
        }

        public static Vec2 ToWorld(Vec2 local, Vec2 centre, float rot)
        {
            float a = rot * (float)Math.PI / 180f, c = (float)Math.Cos(a), s = (float)Math.Sin(a);
            return new Vec2(centre.x + local.x * c + local.z * s, centre.z - local.x * s + local.z * c);
        }

        /// <summary>Distance from a point to the rectangle. 0 anywhere inside it.</summary>
        public static float Dist(Vec2 p, Vec2 centre, float rot, Vec2 half)
        {
            var l = ToLocal(p, centre, rot);
            float ox = Math.Max(0f, Math.Abs(l.x) - half.x), oz = Math.Max(0f, Math.Abs(l.z) - half.z);
            return (float)Math.Sqrt(ox * ox + oz * oz);
        }
    }
}
