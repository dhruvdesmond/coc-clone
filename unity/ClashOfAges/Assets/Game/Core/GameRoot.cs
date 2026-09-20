using System;
using System.Collections.Generic;
using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// Owns the sim World, ticks it at a fixed 20 Hz, mirrors entities into views, and turns sim
    /// events into C# events for FX, sound and UI. Nothing else mutates the world except via Cmd*.
    /// </summary>
    public sealed class GameRoot : MonoBehaviour
    {
        public static GameRoot I { get; private set; }
        public InstancedWorld instancedWorld;
        public ModelLibrary models;
        public Collider[] terrainColliders;
        public Vector2 mapSize = new Vector2(104f, 84f);
        public Vector2 hallSite = new Vector2(-8.9f, 11.4f);
        [Range(0f, 8f)] public float timeScale = 1f;
        public bool paused = true;                       // the title card unpauses
        [HideInInspector] public int maxTicksPerFrame = 12;

        public World World { get; private set; }
        public event Action<SimEvent> OnSimEvent;
        public readonly Dictionary<int, UnitView> unitViews = new Dictionary<int, UnitView>();
        public readonly Dictionary<int, BuildingView> buildingViews = new Dictionary<int, BuildingView>();
        public readonly Dictionary<int, NodeView> nodeViews = new Dictionary<int, NodeView>();
        public Vector3 HallWorldPos { get; private set; }
        public Vector3 EnemyCampPos { get; private set; }

        float _acc;

        void Awake()
        {
            I = this;
            Ground.colliders = terrainColliders;
            World = new World(mapSize.x, mapSize.y) { builtinMovement = false, siteOk = Ground.SiteOk };
            Setup();
        }

        void Setup()
        {
            var w = World;
            var hall = new Vec2(hallSite.x, hallSite.y);
            HallWorldPos = Ground.At(hall);

            // every exported tree is a wood node; chopping one removes it from the instanced renderer
            var trees = instancedWorld.World.trees;
            for (int i = 0; i < trees.Length; i++)
            {
                var p = trees[i].position;
                if (Vec2.Dist(new Vec2(p.x, p.z), hall) < 9.5f) { instancedWorld.RemoveTree(i); continue; }   // clear the hall's pad
                w.SpawnNode(NodeKind.Tree, new Vec2(p.x, p.z), Mathf.Lerp(90f, 150f, Mathf.InverseLerp(3f, 9f, trees[i].height)), i);
            }

            var enemy = FindCampSite(hall);
            EnemyCampPos = Ground.At(enemy);
            foreach (var n in new List<Node>(w.nodes))           // clear the camp too
                if (Vec2.Dist(n.pos, enemy) < 9.5f) { instancedWorld.RemoveTree(n.treeEntity); n.amount = 0; }
            w.nodes.RemoveAll(n => n.Depleted);

            w.SpawnBuilding(World.Human, BuildingType.Hall, hall, 0f, true);
            w.SpawnBuilding(World.Enemy, BuildingType.Hall, enemy, 180f, true);
            w.SpawnBuilding(World.Enemy, BuildingType.Tower, FreeSpotNear(enemy, 11f, 2.4f), 0f, true);
            w.raids.campPos = enemy; w.raids.targetPos = hall;

            // starting resources near home: berries, stone, iron -- placed on real, flat, dry ground
            var rng = new System.Random(7);
            PlaceNodes(NodeKind.Berry, 280f, hall, 13f, 21f, 4, rng);
            PlaceNodes(NodeKind.Stone, 300f, hall, 17f, 27f, 2, rng);
            PlaceNodes(NodeKind.Iron, 300f, hall, 18f, 29f, 2, rng);
            PlaceNodes(NodeKind.Berry, 280f, hall, 26f, 40f, 4, rng);
            PlaceNodes(NodeKind.Stone, 300f, hall, 30f, 44f, 2, rng);
            PlaceNodes(NodeKind.Iron, 300f, hall, 31f, 44f, 1, rng);

            w.Me.stock[Res.Food] = 200; w.Me.stock[Res.Wood] = 200;
            w.SpawnUnit(World.Human, UnitType.Citizen, FreeSpotNear(hall, 10f, 0.5f));
            SyncViews();
        }

        Vec2 FindCampSite(Vec2 hall)
        {
            Vec2 best = new Vec2(-hall.x, -hall.z); float bestScore = float.MinValue;
            for (float x = -mapSize.x * 0.5f + 12f; x < mapSize.x * 0.5f - 12f; x += 3f)
                for (float z = -mapSize.y * 0.5f + 12f; z < mapSize.y * 0.5f - 12f; z += 3f)
                {
                    var p = new Vec2(x, z); float d = Vec2.Dist(p, hall);
                    if (d < 58f || !Ground.SiteOk(p, 9f)) continue;
                    float score = d - Mathf.Abs(Ground.Height(x, z) - 2.5f) * 4f;      // far, and not up on the snow
                    if (score > bestScore) { bestScore = score; best = p; }
                }
            return best;
        }

        public Vec2 FreeSpotNear(Vec2 centre, float dist, float radius)
        {
            for (int i = 0; i < 40; i++)
            {
                float a = i * 2.399f;                                                 // golden angle: even coverage
                var p = centre + new Vec2(Mathf.Cos(a), Mathf.Sin(a)) * (dist + (i / 8) * 2f);
                if (Ground.SiteOk(p, Mathf.Max(radius, 1f)) && World.SiteProblemIgnoringBorder(p, radius) == null) return p;
            }
            return centre + new Vec2(dist, 0);
        }

        void PlaceNodes(NodeKind kind, float amount, Vec2 centre, float rMin, float rMax, int count, System.Random rng)
        {
            int placed = 0;
            for (int tries = 0; tries < 300 && placed < count; tries++)
            {
                float a = (float)rng.NextDouble() * Mathf.PI * 2f, r = Mathf.Lerp(rMin, rMax, (float)rng.NextDouble());
                var p = centre + new Vec2(Mathf.Cos(a), Mathf.Sin(a)) * r;
                if (Mathf.Abs(p.x) > mapSize.x * 0.5f - 6f || Mathf.Abs(p.z) > mapSize.y * 0.5f - 6f) continue;
                if (!Ground.SiteOk(p, 3f) || World.SiteProblemIgnoringBorder(p, 3.2f) != null) continue;
                bool nearTree = false;
                foreach (var n in World.nodes) if (Vec2.Dist(n.pos, p) < (n.kind == NodeKind.Tree ? 2.6f : 7f)) { nearTree = true; break; }
                if (nearTree) continue;
                World.SpawnNode(kind, p, amount); placed++;
            }
        }

        void Update()
        {
            if (!paused && !World.over)
            {
                _acc += Time.deltaTime * timeScale;
                int guard = 0;
                while (_acc >= World.Dt && guard++ < maxTicksPerFrame) { _acc -= World.Dt; PushPositions(); World.Tick(); }
                if (guard >= maxTicksPerFrame) _acc = 0f;
            }
            SyncViews();
            if (World.events.Count > 0)
            {
                var evs = World.events.ToArray(); World.events.Clear();
                foreach (var e in evs)
                {
                    if (e.type == SimEventType.TreeFelled && e.b >= 0) instancedWorld.RemoveTree(e.b);
                    OnSimEvent?.Invoke(e);
                }
            }
        }

        /// <summary>DL32: NavMeshAgents walk; the sim is told where each unit actually is before it ticks.</summary>
        void PushPositions() { foreach (var v in unitViews.Values) v.PushToSim(); }

        void SyncViews()
        {
            foreach (var u in World.units)
                if (!unitViews.ContainsKey(u.id)) unitViews[u.id] = UnitView.Create(this, u);
            foreach (var b in World.buildings)
                if (!buildingViews.ContainsKey(b.id)) buildingViews[b.id] = BuildingView.Create(this, b);
            foreach (var n in World.nodes)
                if (n.kind != NodeKind.Tree && n.kind != NodeKind.Farm && !nodeViews.ContainsKey(n.id)) nodeViews[n.id] = NodeView.Create(this, n);
        }

        public void Forget(UnitView v) { unitViews.Remove(v.unitId); }
    }
}
