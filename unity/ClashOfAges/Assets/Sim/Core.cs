using System;

namespace COA.Sim
{
    /// <summary>Ground-plane vector. The sim is 2D; height is presentation.</summary>
    public struct Vec2
    {
        public float x, z;
        public Vec2(float x, float z) { this.x = x; this.z = z; }
        public static Vec2 operator +(Vec2 a, Vec2 b) => new Vec2(a.x + b.x, a.z + b.z);
        public static Vec2 operator -(Vec2 a, Vec2 b) => new Vec2(a.x - b.x, a.z - b.z);
        public static Vec2 operator *(Vec2 a, float k) => new Vec2(a.x * k, a.z * k);
        public float Length => (float)Math.Sqrt(x * x + z * z);
        public float SqrLength => x * x + z * z;
        public Vec2 Normalized { get { float l = Length; return l > 1e-6f ? new Vec2(x / l, z / l) : new Vec2(0, 0); } }
        public static float Dist(Vec2 a, Vec2 b) => (a - b).Length;
        public override string ToString() => $"({x:F1},{z:F1})";
    }

    public enum Res { Food, Wood, Stone, Metal, Knowledge, Gold }

    public struct Cost
    {
        public int food, wood, stone, metal, knowledge, gold;
        public static Cost Of(int food = 0, int wood = 0, int stone = 0, int metal = 0, int knowledge = 0, int gold = 0)
            => new Cost { food = food, wood = wood, stone = stone, metal = metal, knowledge = knowledge, gold = gold };
        public int this[Res r] => r == Res.Food ? food : r == Res.Wood ? wood : r == Res.Stone ? stone
                                : r == Res.Metal ? metal : r == Res.Knowledge ? knowledge : gold;
        public override string ToString()
        {
            var s = "";
            foreach (Res r in Enum.GetValues(typeof(Res))) if (this[r] > 0) s += (s.Length > 0 ? "  " : "") + this[r] + " " + r;
            return s.Length > 0 ? s : "free";
        }
    }

    public sealed class Stockpile
    {
        readonly float[] _v = new float[6];
        public float this[Res r] { get => _v[(int)r]; set => _v[(int)r] = value; }
        public bool CanAfford(Cost c)
        {
            foreach (Res r in Enum.GetValues(typeof(Res))) if (_v[(int)r] + 0.001f < c[r]) return false;
            return true;
        }
        public void Pay(Cost c) { foreach (Res r in Enum.GetValues(typeof(Res))) _v[(int)r] -= c[r]; }
        public void Refund(Cost c) { foreach (Res r in Enum.GetValues(typeof(Res))) _v[(int)r] += c[r]; }
    }

    public enum EventType
    {
        Deposit, NodeDepleted, TreeFelled, BuildingPlaced, BuildingComplete, BuildingDestroyed, UnitSpawned, UnitDied,
        Attack, Hit, WorkImpact, TechComplete, AgeAdvanceStarted, AgeAdvanced, RaidIncoming, RaidDefeated,
        PopCapped, Toast, Victory, Defeat, TerritoryChanged,
    }

    public struct SimEvent
    {
        public EventType type; public int a, b; public Vec2 pos; public float amount; public string text;
    }
}
