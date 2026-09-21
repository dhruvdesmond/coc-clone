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
            World = new World(mapSize.x, mapSize.y) { builtinMovement = false, siteOk = Ground.SiteOk, groundProblem = Ground.FootprintProblem };
            Setup();
        }

        void Setup()
        {
            var w = World;
            // hallSite is a WISH. It was once taken as fact, and the longhouse stood with one gable in the lake (PENDING B1).
            var hallHalf = Catalog.Buildings[BuildingType.Hall].half;
            var hall = FindBuildingSite(new Vec2(hallSite.x, hallSite.y), hallHalf, out float hallRot);
            HallWorldPos = Ground.At(hall);

            // every exported tree is a wood node; chopping one removes it from the instanced renderer
            var trees = instancedWorld.World.trees;
            for (int i = 0; i < trees.Length; i++)
            {
                var p = trees[i].position;
                var node = w.SpawnNode(NodeKind.Tree, new Vec2(p.x, p.z), Mathf.Lerp(90f, 150f, Mathf.InverseLerp(3f, 9f, trees[i].height)), i);
                if (trees[i].radius > 0.1f) node.radius = trees[i].radius;
            }
            ClearPad(hall, hallRot, hallHalf);

            var enemy = FindCampSite(hall, hallHalf, out float enemyRot);
            EnemyCampPos = Ground.At(enemy);
            ClearPad(enemy, enemyRot, hallHalf);

            w.SpawnBuilding(World.Human, BuildingType.Hall, hall, hallRot, true);
            w.SpawnBuilding(World.Enemy, BuildingType.Hall, enemy, enemyRot, true);
            // the bot's first footprint check found this tower standing inside three spruces: same bug, never seen
            var towerHalf = Catalog.Buildings[BuildingType.Tower].half;
            var tower = FindBuildingSite(FreeSpotNear(enemy, 13f, 2.4f), towerHalf, out float towerRot);
            ClearPad(tower, towerRot, towerHalf);
            w.SpawnBuilding(World.Enemy, BuildingType.Tower, tower, towerRot, true);
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

        /// <summary>The nearest place to `wish` where this footprint really fits -- dry, flat, on the map -- trying the wish
        /// itself first, then rings outward, each at four headings. Trees do not disqualify a site: they are cleared.</summary>
        Vec2 FindBuildingSite(Vec2 wish, Vec2 half, out float rot)
        {
            float[] headings = { 0f, 90f, 45f, 135f };
            for (int ring = 0; ring < 30; ring++)
            {
                int steps = ring == 0 ? 1 : 6 + ring * 2;
                for (int k = 0; k < steps; k++)
                {
                    float a = k * Mathf.PI * 2f / steps;
                    var p = wish + new Vec2(Mathf.Cos(a), Mathf.Sin(a)) * (ring * 2.5f);
                    foreach (var h in headings)
                        if (Ground.FootprintProblem(p, h, half) == null && World.SiteProblemIgnoringBorder(p, Mathf.Max(half.x, half.z)) == null)
                        {
                            if (ring > 0 || h != 0f) Debug.Log($"[site] {wish.x:F1},{wish.z:F1} does not fit a {half.x * 2f:F1} x {half.z * 2f:F1} m footprint " +
                                                               $"({Ground.FootprintProblem(wish, 0f, half)}); moved {Vec2.Dist(p, wish):F1} m, heading {h:F0}");
                            rot = h; return p;
                        }
                }
            }
            Debug.LogError($"[site] FAIL no buildable site within 75 m of {wish.x:F1},{wish.z:F1}");
            rot = 0f; return wish;
        }

        /// <summary>World setup's version of what CmdPlace does: every tree whose canopy reaches the footprint goes, plus a
        /// little more so the pad reads as a clearing. Same rule (World.TreesOn), wider rectangle.</summary>
        void ClearPad(Vec2 pos, float rot, Vec2 half)
        {
            foreach (var n in World.TreesOn(pos, rot, new Vec2(half.x + 1.5f, half.z + 1.5f))) { instancedWorld.RemoveTree(n.treeEntity); n.amount = 0; }
            World.nodes.RemoveAll(n => n.Depleted);
        }

        /// <summary>The enemy's home: the place FARTHEST from yours where a longhouse really fits. The first version demanded
        /// "58 m away and a flat 9 m circle", which nothing on a 104 x 84 m map satisfies -- so it fell back, every game, silently,
        /// to a mirrored point 29 m from the player that nobody had checked. That was the house in the lake (PENDING B1).</summary>
        Vec2 FindCampSite(Vec2 hall, Vec2 half, out float rot)
        {
            Vec2 best = hall; float bestScore = float.MinValue; rot = 0f;
            float[] headings = { 0f, 90f, 45f, 135f };
            for (float x = -mapSize.x * 0.5f + 10f; x <= mapSize.x * 0.5f - 10f; x += 2f)
                for (float z = -mapSize.y * 0.5f + 10f; z <= mapSize.y * 0.5f - 10f; z += 2f)
                {
                    var p = new Vec2(x, z); float d = Vec2.Dist(p, hall);
                    float score = d - Mathf.Abs(Ground.Height(x, z) - 2.5f) * 4f;      // far, and not up on the snow
                    if (score <= bestScore) continue;
                    foreach (var h in headings)
                        if (Ground.FootprintProblem(p, h, half) == null) { bestScore = score; best = p; rot = h; break; }
                }
            float got = Vec2.Dist(best, hall);
            if (got < 40f) Debug.LogError($"[site] FAIL enemy camp is only {got:F1} m from the player's hall");
            else Debug.Log($"[site] enemy camp at {best.x:F1},{best.z:F1} heading {rot:F0}, {got:F1} m from the player's hall");
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
