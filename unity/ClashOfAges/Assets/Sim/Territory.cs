using System;
using System.Collections.Generic;

namespace COA.Sim
{
    /// <summary>
    /// Borders. One byte per 1 m cell holding the owning player (0 = nobody). A cell belongs to
    /// whoever has the most "radius weight" there: the sum over that player's border sources of
    /// (radius - distance). Deterministic, no flicker at the seam, and recomputed only when a
    /// border source changes -- a handful of times per match, never per frame. docs/12-territory.
    /// </summary>
    public sealed class Territory
    {
        public readonly int w, h; public readonly float originX, originZ;
        public readonly byte[] owner;
        public int version;

        public Territory(float mapW, float mapH)
        {
            w = (int)Math.Ceiling(mapW); h = (int)Math.Ceiling(mapH);
            originX = -mapW * 0.5f; originZ = -mapH * 0.5f;
            owner = new byte[w * h];
        }

        public int OwnerAt(Vec2 p)
        {
            int cx = (int)Math.Floor(p.x - originX), cz = (int)Math.Floor(p.z - originZ);
            return cx < 0 || cz < 0 || cx >= w || cz >= h ? 0 : owner[cz * w + cx];
        }

        public void Recompute(List<Building> buildings, Player[] players)
        {
            var weight = new float[w * h];
            Array.Clear(owner, 0, owner.Length);
            // two passes (one per owner) accumulating weight, then compare
            var acc = new float[3][]; acc[1] = new float[w * h]; acc[2] = new float[w * h];
            foreach (var b in buildings)
            {
                if (b.destroyed || !b.complete || b.def.territory <= 0f || b.owner < 1 || b.owner > 2) continue;
                float r = b.def.territory + players[b.owner].borderBonus;
                int x0 = Math.Max(0, (int)(b.pos.x - r - originX)), x1 = Math.Min(w - 1, (int)(b.pos.x + r - originX));
                int z0 = Math.Max(0, (int)(b.pos.z - r - originZ)), z1 = Math.Min(h - 1, (int)(b.pos.z + r - originZ));
                var a = acc[b.owner];
                for (int z = z0; z <= z1; z++)
                    for (int x = x0; x <= x1; x++)
                    {
                        float dx = x + 0.5f + originX - b.pos.x, dz = z + 0.5f + originZ - b.pos.z;
                        float d = (float)Math.Sqrt(dx * dx + dz * dz);
                        if (d < r) a[z * w + x] += r - d;
                    }
            }
            for (int i = 0; i < owner.Length; i++)
            {
                float a = acc[1][i], e = acc[2][i];
                owner[i] = a <= 0f && e <= 0f ? (byte)0 : a >= e ? (byte)1 : (byte)2;
            }
            version++;
        }

        public float LandShare(int player)
        {
            int n = 0; foreach (var o in owner) if (o == player) n++;
            return n / (float)owner.Length;
        }
    }
}
