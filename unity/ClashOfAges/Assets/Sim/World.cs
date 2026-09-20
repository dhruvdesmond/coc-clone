using System;
using System.Collections.Generic;

namespace COA.Sim
{
    public enum UnitState { Idle, Moving, ToNode, Gathering, ToDropOff, ToBuild, Building, ToScholar, Scholar, Attacking, Dead }

    public sealed class Unit
    {
        public int id, owner; public UnitType type; public UnitDef def;
        public Vec2 pos; public float facing; public float hp, maxHp;
        public UnitState state = UnitState.Idle;

        // movement: the sim says WHERE and how close; a mover (built-in, or Unity's NavMesh) does the walking
        public bool hasMoveTarget; public Vec2 moveTarget; public float stopDistance = 0.4f; public bool blocked;

        public int nodeId = -1, buildingId = -1, targetUnit = -1, targetBuilding = -1;
        public bool attackMove; public Vec2 attackMoveDest;
        public Res carryRes; public float carry; public NodeKind lastKind;
        public float workTimer, cooldown, sinceCombat = 99f;
        public bool IsCitizen => type == UnitType.Citizen;
        public bool Alive => state != UnitState.Dead;
        public bool Hidden => state == UnitState.Scholar;
    }

    public sealed class Building
    {
        public int id, owner; public BuildingType type; public BuildingDef def;
        public Vec2 pos; public float rot; public float hp; public float progress; public bool complete; public bool destroyed;
        public readonly List<UnitType> queue = new List<UnitType>(); public float trainTimer;
        public Vec2 rally; public bool hasRally;
        public int scholars; public string researching; public float researchTimer; public bool researchingAge;
        public float towerCooldown; public int variant;
    }

    public sealed class Node
    {
        public int id; public NodeKind kind; public Vec2 pos; public float amount, max; public int treeEntity = -1;
        public int workers; public int farmBuilding = -1; public bool Depleted => amount <= 0f;
    }

    public sealed class Player
    {
        public int id; public readonly Stockpile stock = new Stockpile(); public int age = 1;
        public readonly HashSet<string> techs = new HashSet<string>();
        public int popUsed, popCap; public float gatherWoodFood = 1f, knowledgeMul = 1f, buildMul = 1f, soldierHpMul = 1f, towerMul = 1f;
        public float borderBonus; public int unitsLost, unitsKilled; public float gathered;
    }

    /// <summary>
    /// The whole game state and its 20 Hz tick. No UnityEngine anywhere in this assembly, so it
    /// runs and is tested headless. Presentation reads it and sends commands back; nothing here
    /// knows a camera exists.
    /// </summary>
    public sealed partial class World
    {
        public const float Dt = 0.05f;                    // 20 Hz
        public float time; public int tick;
        public readonly List<Unit> units = new List<Unit>();
        public readonly List<Building> buildings = new List<Building>();
        public readonly List<Node> nodes = new List<Node>();
        public readonly Player[] players = { new Player { id = 0 }, new Player { id = 1 }, new Player { id = 2 } };
        public readonly List<SimEvent> events = new List<SimEvent>();
        public Territory territory;
        public RaidDirector raids;
        public bool over, won;

        /// <summary>True for headless runs: units walk straight lines. Unity turns this off and drives
        /// positions from NavMeshAgents (DL32), so pathfinding is replaceable without touching the sim.</summary>
        public bool builtinMovement = true;

        /// <summary>Presentation's answer to "is this ground usable": slope, water, map edge. Null = always yes.</summary>
        public Func<Vec2, float, bool> siteOk;

        int _nextId = 1;
        readonly Dictionary<int, Unit> _unitById = new Dictionary<int, Unit>();
        readonly Dictionary<int, Building> _bldById = new Dictionary<int, Building>();
        readonly Dictionary<int, Node> _nodeById = new Dictionary<int, Node>();
        readonly Random _rng = new Random(12);

        public const int Human = 1, Enemy = 2;
        public Player Me => players[Human];

        public World(float mapW, float mapH) { territory = new Territory(mapW, mapH); raids = new RaidDirector(this); }

        public Unit U(int id) => _unitById.TryGetValue(id, out var u) ? u : null;
        public Building B(int id) => _bldById.TryGetValue(id, out var b) ? b : null;
        public Node N(int id) => _nodeById.TryGetValue(id, out var n) ? n : null;
        void Emit(SimEventType t, int a = 0, int b = 0, Vec2 pos = default, float amount = 0, string text = null)
            => events.Add(new SimEvent { type = t, a = a, b = b, pos = pos, amount = amount, text = text });

        // ------------------------------------------------------------------ spawning
        public Unit SpawnUnit(int owner, UnitType type, Vec2 pos)
        {
            var d = Catalog.Units[type];
            var p = players[owner];
            float hp = d.hp * (type == UnitType.Citizen ? 1f : p.soldierHpMul);
            var u = new Unit { id = _nextId++, owner = owner, type = type, def = d, pos = pos, hp = hp, maxHp = hp };
            units.Add(u); _unitById[u.id] = u;
            p.popUsed += d.pop;
            Emit(SimEventType.UnitSpawned, u.id, owner, pos);
            return u;
        }

        public Building SpawnBuilding(int owner, BuildingType type, Vec2 pos, float rot, bool complete)
        {
            var d = Catalog.Buildings[type];
            var b = new Building { id = _nextId++, owner = owner, type = type, def = d, pos = pos, rot = rot,
                                   hp = complete ? d.hp : d.hp * 0.1f, progress = complete ? 1f : 0f, variant = _rng.Next(5) };
            buildings.Add(b); _bldById[b.id] = b;
            if (complete) OnComplete(b, silent: true);
            return b;
        }

        public Node SpawnNode(NodeKind kind, Vec2 pos, float amount, int treeEntity = -1)
        {
            var n = new Node { id = _nextId++, kind = kind, pos = pos, amount = amount, max = amount, treeEntity = treeEntity };
            nodes.Add(n); _nodeById[n.id] = n;
            return n;
        }

        void OnComplete(Building b, bool silent = false)
        {
            b.complete = true; b.progress = 1f; b.hp = Math.Max(b.hp, b.def.hp);
            RecountPop(b.owner);
            if (b.type == BuildingType.Farm)
            {
                var n = SpawnNode(NodeKind.Farm, b.pos, 1e9f); n.farmBuilding = b.id;
            }
            if (b.def.territory > 0f) RecomputeTerritory();
            if (!silent) Emit(SimEventType.BuildingComplete, b.id, b.owner, b.pos);
        }

        public void RecountPop(int owner)
        {
            int cap = 0;
            foreach (var b in buildings) if (b.owner == owner && b.complete && !b.destroyed) cap += b.def.popProvided;
            players[owner].popCap = Math.Min(cap, Catalog.HardPopCap);
        }

        public void RecomputeTerritory()
        {
            territory.Recompute(buildings, players);
            Emit(SimEventType.TerritoryChanged);
        }

        // ------------------------------------------------------------------ tick
        public void Tick()
        {
            if (over) return;
            time += Dt; tick++;

            for (int i = 0; i < units.Count; i++)
            {
                var u = units[i];
                if (!u.Alive) continue;
                u.cooldown = Math.Max(0f, u.cooldown - Dt);
                u.sinceCombat += Dt;
                if (u.IsCitizen) TickCitizen(u);
                TickCombat(u);
                if (builtinMovement) BuiltinMove(u);
                TickAttrition(u);
            }
            foreach (var b in buildings) if (!b.destroyed) TickBuilding(b);
            raids.Tick();
            units.RemoveAll(u => { if (u.state == UnitState.Dead) { _unitById.Remove(u.id); return true; } return false; });
            CheckEnd();
        }

        void BuiltinMove(Unit u)
        {
            if (!u.hasMoveTarget || u.Hidden) return;
            var d = u.moveTarget - u.pos; float dist = d.Length;
            if (dist <= u.stopDistance) return;
            float step = Math.Min(u.def.speed * Dt, dist - u.stopDistance * 0.9f);
            u.pos = u.pos + d.Normalized * step;
            u.facing = (float)(Math.Atan2(d.x, d.z) * 180.0 / Math.PI);
        }

        public bool Arrived(Unit u) =>
            !u.hasMoveTarget || Vec2.Dist(u.pos, u.moveTarget) <= u.stopDistance + (u.blocked ? 1.6f + u.stopDistance * 0.25f : 0.15f);

        void MoveTo(Unit u, Vec2 target, float stop) { u.hasMoveTarget = true; u.moveTarget = target; u.stopDistance = stop; u.blocked = false; }
        void Halt(Unit u) { u.hasMoveTarget = false; }

        // ------------------------------------------------------------------ citizens
        void TickCitizen(Unit u)
        {
            switch (u.state)
            {
                case UnitState.Moving:
                    if (Arrived(u)) { Halt(u); u.state = UnitState.Idle; }
                    break;

                case UnitState.ToNode:
                {
                    var n = N(u.nodeId);
                    if (n == null || n.Depleted) { Retarget(u); break; }
                    if (Arrived(u))
                    {
                        if (n.workers >= Catalog.NodeWorkerCap(n.kind)) { Retarget(u, n); break; }
                        n.workers++; Halt(u); u.state = UnitState.Gathering; u.workTimer = 0f;
                        if (u.carryRes != Catalog.ResourceOf(n.kind)) u.carry = 0f;
                        u.carryRes = Catalog.ResourceOf(n.kind); u.lastKind = n.kind;
                    }
                    break;
                }

                case UnitState.Gathering:
                {
                    var n = N(u.nodeId);
                    if (n == null || n.Depleted) { if (n != null) n.workers = Math.Max(0, n.workers - 1); AfterNodeGone(u); break; }
                    var p = players[u.owner];
                    float rate = Catalog.GatherRate(n.kind) * (u.carryRes == Res.Wood || u.carryRes == Res.Food ? p.gatherWoodFood : 1f);
                    float got = Math.Min(rate * Dt, Math.Min(n.amount, Catalog.CarryCapacity - u.carry));
                    if (n.kind == NodeKind.Farm)
                    {
                        // Rise of Nations: a farmer does not carry. The farm IS the drop-off, so its food is banked
                        // where it grows -- which is also what makes a farm worth its wood over a berry bush.
                        p.stock[Res.Food] += got; p.gathered += got;
                        u.workTimer += Dt;
                        if (u.workTimer >= 1.6f) { u.workTimer = 0f; Emit(SimEventType.WorkImpact, u.id, (int)n.kind, n.pos); }
                        break;
                    }
                    u.carry += got; n.amount -= got;
                    u.workTimer += Dt;
                    if (u.workTimer >= 1.6f) { u.workTimer = 0f; Emit(SimEventType.WorkImpact, u.id, (int)n.kind, n.pos); }
                    if (n.Depleted) DepleteNode(n);
                    if (u.carry >= Catalog.CarryCapacity - 0.001f || n.Depleted)
                    {
                        n.workers = Math.Max(0, n.workers - 1);
                        GoDropOff(u);
                    }
                    break;
                }

                case UnitState.ToDropOff:
                {
                    var b = B(u.buildingId);
                    if (b == null || b.destroyed || !b.complete) { GoDropOff(u); break; }
                    if (Arrived(u))
                    {
                        players[u.owner].stock[u.carryRes] += u.carry;
                        players[u.owner].gathered += u.carry;
                        Emit(SimEventType.Deposit, u.id, (int)u.carryRes, b.pos, u.carry);
                        u.carry = 0f;
                        var n = N(u.nodeId);
                        if (n != null && !n.Depleted) { u.state = UnitState.ToNode; MoveTo(u, n.pos, Catalog.NodeRadius(n.kind) + 0.5f); }
                        else Retarget(u);
                    }
                    break;
                }

                case UnitState.ToBuild:
                {
                    var b = B(u.buildingId);
                    if (b == null || b.destroyed) { Halt(u); u.state = UnitState.Idle; break; }
                    if (b.complete) { AfterBuild(u, b); break; }
                    if (Arrived(u)) { Halt(u); u.state = UnitState.Building; u.workTimer = 0f; }
                    break;
                }

                case UnitState.Building:
                {
                    var b = B(u.buildingId);
                    if (b == null || b.destroyed) { u.state = UnitState.Idle; break; }
                    if (b.complete) { AfterBuild(u, b); break; }
                    int builders = 0;
                    foreach (var o in units) if (o.state == UnitState.Building && o.buildingId == b.id) builders++;
                    // the first builder counts fully, each extra one 60%: more hands help, with diminishing returns
                    float share = (1f + 0.6f * (builders - 1)) / Math.Max(1, builders);
                    b.progress += Dt * share * players[u.owner].buildMul / b.def.buildTime;
                    b.hp = Math.Min(b.def.hp, b.hp + Dt * share * b.def.hp / b.def.buildTime);
                    u.workTimer += Dt;
                    if (u.workTimer >= 1.1f) { u.workTimer = 0f; Emit(SimEventType.WorkImpact, u.id, -1, b.pos); }
                    if (b.progress >= 1f) OnComplete(b);
                    break;
                }

                case UnitState.ToScholar:
                {
                    var b = B(u.buildingId);
                    if (b == null || b.destroyed || !b.complete || b.scholars >= b.def.scholarSlots) { Halt(u); u.state = UnitState.Idle; break; }
                    if (Arrived(u)) { Halt(u); b.scholars++; u.state = UnitState.Scholar; }
                    break;
                }
            }
        }

        public int BuildersOn(Building b)
        {
            int k = 0; foreach (var o in units) if (o.state == UnitState.Building && o.buildingId == b.id) k++;
            return k;
        }

        /// <summary>The first builder counts fully, each extra one 60%: 1x, 1.6x, 2.2x, 2.8x ...</summary>
        public static float BuildSpeed(int builders) => builders <= 0 ? 0f : 1f + 0.6f * (builders - 1);

        public float SecondsLeft(Building b)
        {
            float s = BuildSpeed(BuildersOn(b)) * players[b.owner].buildMul;
            return s <= 0f ? -1f : (1f - b.progress) * b.def.buildTime / s;
        }

        void AfterBuild(Unit u, Building done)
        {
            // keep building anything else unfinished nearby; otherwise farmers farm, the rest idle
            Building next = null; float best = 30f;
            foreach (var b in buildings)
                if (b.owner == u.owner && !b.complete && !b.destroyed && Vec2.Dist(b.pos, u.pos) < best)
                { best = Vec2.Dist(b.pos, u.pos); next = b; }
            if (next != null) { OrderBuild(u, next); return; }
            if (done.type == BuildingType.Farm)
                foreach (var n in nodes) if (n.farmBuilding == done.id) { OrderGather(u, n); return; }
            Halt(u); u.state = UnitState.Idle;
        }

        void DepleteNode(Node n)
        {
            Emit(n.kind == NodeKind.Tree ? SimEventType.TreeFelled : SimEventType.NodeDepleted, n.id, n.treeEntity, n.pos);
        }

        /// <summary>Workers AT the node plus those already walking to it. Counting only the first let nine
        /// citizens all head for one "free" berry bush, find it full on arrival, and thrash between bushes forever.</summary>
        public int Claimed(Node n, Unit except = null)
        {
            int c = n.workers;
            foreach (var o in units) if (o != except && o.state == UnitState.ToNode && o.nodeId == n.id) c++;
            return c;
        }

        void AfterNodeGone(Unit u) { if (u.carry > 0.5f) GoDropOff(u); else Retarget(u); }

        /// <summary>The node is gone or full: find the nearest one of the same kind, or go idle.</summary>
        void Retarget(Unit u, Node full = null)
        {
            Node best = null; float bd = 28f;
            NodeKind want = full != null ? full.kind : u.lastKind;
            foreach (var n in nodes)
            {
                if (n.Depleted || n == full || n.kind != want) continue;
                if (Claimed(n, u) >= Catalog.NodeWorkerCap(n.kind)) continue;
                float d = Vec2.Dist(n.pos, u.pos);
                if (d < bd) { bd = d; best = n; }
            }
            if (best != null) OrderGather(u, best);
            else { Halt(u); u.state = UnitState.Idle; u.nodeId = -1; }
        }

        void GoDropOff(Unit u)
        {
            Building best = null; float bd = float.MaxValue;
            foreach (var b in buildings)
            {
                if (b.owner != u.owner || !b.complete || b.destroyed || !b.def.dropOff) continue;
                float d = Vec2.Dist(b.pos, u.pos);
                if (d < bd) { bd = d; best = b; }
            }
            if (best == null) { Halt(u); u.state = UnitState.Idle; return; }
            u.buildingId = best.id; u.state = UnitState.ToDropOff;
            MoveTo(u, best.pos, best.def.radius + 0.7f);
        }

        void ReleaseWork(Unit u)
        {
            if (u.state == UnitState.Gathering) { var n = N(u.nodeId); if (n != null) n.workers = Math.Max(0, n.workers - 1); }
            if (u.state == UnitState.Scholar) { var b = B(u.buildingId); if (b != null) b.scholars = Math.Max(0, b.scholars - 1); }
        }

        void OrderGather(Unit u, Node n)
        {
            ReleaseWork(u);
            // ordered onto a node that is already spoken for: take the nearest free one of the same kind instead,
            // so a group right-clicked onto one bush spreads itself over the thicket
            if (Claimed(n, u) >= Catalog.NodeWorkerCap(n.kind))
            {
                Node alt = null; float bd = 30f;
                foreach (var o in nodes)
                    if (o != n && !o.Depleted && o.kind == n.kind && Claimed(o, u) < Catalog.NodeWorkerCap(o.kind) && Vec2.Dist(o.pos, n.pos) < bd)
                    { bd = Vec2.Dist(o.pos, n.pos); alt = o; }
                if (alt != null) n = alt;
            }
            u.nodeId = n.id; u.lastKind = n.kind; u.state = UnitState.ToNode; u.targetUnit = u.targetBuilding = -1; u.attackMove = false;
            MoveTo(u, n.pos, Catalog.NodeRadius(n.kind) + 0.5f);
        }

        void OrderBuild(Unit u, Building b)
        {
            ReleaseWork(u);
            u.buildingId = b.id; u.state = UnitState.ToBuild; u.targetUnit = u.targetBuilding = -1; u.attackMove = false;
            MoveTo(u, b.pos, b.def.radius + 0.8f);
        }

        // ------------------------------------------------------------------ buildings
        void TickBuilding(Building b)
        {
            if (!b.complete) return;
            var p = players[b.owner];

            if (b.def.scholarSlots > 0)
                p.stock[Res.Knowledge] += (b.def.knowledgeBase + b.def.knowledgePerScholar * b.scholars) * p.knowledgeMul * Dt;

            if (b.queue.Count > 0)
            {
                var d = Catalog.Units[b.queue[0]];
                if (b.trainTimer < d.trainTime) b.trainTimer += Dt;
                if (b.trainTimer >= d.trainTime)
                {
                    // No cap check here: population was RESERVED when the unit was queued. Checking
                    // again counted the reservation against itself and nothing ever spawned.
                    {
                        b.queue.RemoveAt(0); b.trainTimer = 0f;
                        p.popUsed -= d.pop;                                    // was reserved at queue time
                        var dir = b.hasRally ? (b.rally - b.pos).Normalized : new Vec2(0.6f, -0.8f);
                        if (dir.SqrLength < 0.01f) dir = new Vec2(0.6f, -0.8f);
                        var u = SpawnUnit(b.owner, d.type, b.pos + dir * (b.def.radius + 1.2f));
                        if (b.hasRally) { u.state = UnitState.Moving; MoveTo(u, b.rally + Jitter(1.5f), 0.5f); }
                    }
                }
            }

            if (b.researching != null)
            {
                b.researchTimer -= Dt;
                if (b.researchTimer <= 0f) FinishResearch(b);
            }

            if (b.def.towerRange > 0f)
            {
                b.towerCooldown -= Dt;
                if (b.towerCooldown <= 0f)
                {
                    Unit best = null; float bd = b.def.towerRange;
                    foreach (var u in units)
                        if (u.Alive && !u.Hidden && u.owner != b.owner && Vec2.Dist(u.pos, b.pos) < bd) { bd = Vec2.Dist(u.pos, b.pos); best = u; }
                    if (best != null)
                    {
                        b.towerCooldown = 1.5f;
                        Emit(SimEventType.Attack, -b.id, best.id, b.pos, 1f);
                        Damage(best, b.def.towerDps * 1.5f * p.towerMul, b.owner);
                    }
                }
            }
        }

        Vec2 Jitter(float r) => new Vec2((float)(_rng.NextDouble() * 2 - 1) * r, (float)(_rng.NextDouble() * 2 - 1) * r);

        // ------------------------------------------------------------------ combat
        void TickCombat(Unit u)
        {
            if (u.Hidden) return;
            bool soldier = !u.IsCitizen;

            // resolve explicit targets
            Unit tu = u.targetUnit >= 0 ? U(u.targetUnit) : null;
            Building tb = u.targetBuilding >= 0 ? B(u.targetBuilding) : null;
            if (tu != null && (!tu.Alive || tu.Hidden)) { tu = null; u.targetUnit = -1; }
            if (tb != null && tb.destroyed) { tb = null; u.targetBuilding = -1; }

            // acquire: soldiers when idle or attack-moving; citizens never start a fight
            if (tu == null && tb == null && soldier && (u.state == UnitState.Idle || u.attackMove))
            {
                float bd = 13f;
                foreach (var o in units)
                    if (o.Alive && !o.Hidden && o.owner != u.owner && Vec2.Dist(o.pos, u.pos) < bd) { bd = Vec2.Dist(o.pos, u.pos); tu = o; }
                if (tu == null && u.attackMove)
                {
                    bd = 16f;
                    foreach (var b in buildings)
                        if (!b.destroyed && b.owner != u.owner && b.owner != 0 && Vec2.Dist(b.pos, u.pos) - b.def.radius < bd &&
                            (b.type == BuildingType.Hall || b.type == BuildingType.Tower))
                        { bd = Vec2.Dist(b.pos, u.pos) - b.def.radius; tb = b; }
                }
                if (tu != null) u.targetUnit = tu.id; else if (tb != null) u.targetBuilding = tb.id;
            }

            if (tu == null && tb == null)
            {
                if (u.state == UnitState.Attacking)
                {
                    if (u.attackMove) { u.state = UnitState.Moving; MoveTo(u, u.attackMoveDest, 1.0f); }
                    else { u.state = UnitState.Idle; Halt(u); }
                }
                else if (u.attackMove && u.state == UnitState.Moving && Arrived(u)) { u.attackMove = false; u.state = UnitState.Idle; Halt(u); }
                else if (!u.IsCitizen && u.state == UnitState.Moving && Arrived(u)) { u.state = UnitState.Idle; Halt(u); }
                return;
            }

            Vec2 tp = tu != null ? tu.pos : tb.pos;
            float reach = u.def.range + (tb != null ? tb.def.radius : 0.4f);
            float dist = Vec2.Dist(u.pos, tp);
            u.state = UnitState.Attacking;
            if (dist > reach) { MoveTo(u, tp, reach * 0.92f); return; }

            Halt(u);
            var d = tp - u.pos; u.facing = (float)(Math.Atan2(d.x, d.z) * 180.0 / Math.PI);
            if (u.cooldown > 0f) return;
            u.cooldown = u.def.cooldown; u.sinceCombat = 0f;
            float dmg = u.def.dps * u.def.cooldown;
            if (tu != null)
            {
                dmg *= Catalog.CounterBonus(u.def.cls, tu.def.cls);
                Emit(SimEventType.Attack, u.id, tu.id, u.pos, u.def.range > 3f ? 1f : 0f);
                Damage(tu, dmg, u.owner);
                if (tu.Alive && tu.targetUnit < 0 && tu.targetBuilding < 0 && !tu.IsCitizen &&
                    (tu.state == UnitState.Idle || tu.attackMove)) tu.targetUnit = u.id;     // fight back
            }
            else
            {
                Emit(SimEventType.Attack, u.id, -tb.id, u.pos, u.def.range > 3f ? 1f : 0f);
                DamageBuilding(tb, dmg * (u.def.cls == UnitClass.Ranged ? 0.35f : 0.8f), u.owner);
            }
        }

        public void Damage(Unit t, float dmg, int byOwner)
        {
            if (!t.Alive) return;
            t.hp -= dmg; t.sinceCombat = 0f;
            Emit(SimEventType.Hit, t.id, 0, t.pos, dmg);
            if (t.hp > 0f) return;
            ReleaseWork(t);
            t.state = UnitState.Dead; t.hasMoveTarget = false;
            players[t.owner].popUsed -= t.def.pop; players[t.owner].unitsLost++; players[byOwner].unitsKilled++;
            Emit(SimEventType.UnitDied, t.id, t.owner, t.pos, t.facing);
        }

        public void DamageBuilding(Building b, float dmg, int byOwner)
        {
            if (b.destroyed) return;
            b.hp -= dmg;
            if (b.hp > 0f) return;
            b.destroyed = true; b.complete = false;
            foreach (var u in units)
                if (u.state == UnitState.Scholar && u.buildingId == b.id) { u.state = UnitState.Idle; u.pos = b.pos + Jitter(b.def.radius); }
            foreach (var q in b.queue) players[b.owner].popUsed -= Catalog.Units[q].pop;
            b.queue.Clear();
            nodes.RemoveAll(n => { if (n.farmBuilding == b.id) { _nodeById.Remove(n.id); return true; } return false; });
            RecountPop(b.owner);
            if (b.def.territory > 0f) RecomputeTerritory();
            Emit(SimEventType.BuildingDestroyed, b.id, b.owner, b.pos);
        }

        /// <summary>docs/12: enemies bleed inside your borders; your own units heal there once out of combat.</summary>
        void TickAttrition(Unit u)
        {
            if (u.Hidden) return;
            int land = territory.OwnerAt(u.pos);
            if (land == 0) return;
            if (land != u.owner) { if (tick % 10 == 0) Damage(u, Catalog.AttritionPerSecond * Dt * 10f, land); }
            else if (u.sinceCombat > Catalog.RegenDelay && u.hp < u.maxHp) u.hp = Math.Min(u.maxHp, u.hp + Catalog.RegenPerSecond * Dt);
        }

        void CheckEnd()
        {
            bool myHall = false, theirHall = false;
            foreach (var b in buildings)
                if (b.type == BuildingType.Hall && !b.destroyed) { if (b.owner == Human) myHall = true; else if (b.owner == Enemy) theirHall = true; }
            if (!myHall) { over = true; won = false; Emit(SimEventType.Defeat); }
            else if (!theirHall || raids.FinalRaidDefeated) { over = true; won = true; Emit(SimEventType.Victory); }
        }
    }
}
