using System;
using System.Collections.Generic;

namespace COA.Sim
{
    /// <summary>Everything the player (or a bot, or the AI) can ask the world to do. Returns a reason on refusal.</summary>
    public sealed partial class World
    {
        public void CmdMove(IList<int> ids, Vec2 dest, bool attackMove = false)
        {
            int n = ids.Count, cols = Math.Max(1, (int)Math.Ceiling(Math.Sqrt(n)));
            for (int i = 0; i < n; i++)
            {
                var u = U(ids[i]); if (u == null || !u.Alive) continue;
                if (u.state == UnitState.Scholar) EjectOne(u);
                ReleaseWork(u);
                // a loose grid around the click, so a group does not fight over one point
                var off = new Vec2((i % cols - (cols - 1) * 0.5f) * 1.3f, (i / cols - (n / cols) * 0.5f) * 1.3f);
                u.targetUnit = u.targetBuilding = -1; u.nodeId = -1;
                u.attackMove = attackMove && !u.IsCitizen; u.attackMoveDest = dest + off;
                u.state = UnitState.Moving; MoveTo(u, dest + off, 0.45f);
            }
        }

        public void CmdStop(IList<int> ids)
        {
            foreach (var id in ids) { var u = U(id); if (u == null || u.Hidden) continue; ReleaseWork(u); Halt(u); u.state = UnitState.Idle; u.targetUnit = u.targetBuilding = -1; u.attackMove = false; }
        }

        public void CmdGather(IList<int> ids, int nodeId)
        {
            var n = N(nodeId); if (n == null || n.Depleted) return;
            foreach (var id in ids) { var u = U(id); if (u != null && u.Alive && u.IsCitizen) { if (u.state == UnitState.Scholar) EjectOne(u); OrderGather(u, n); } }
        }

        public void CmdBuild(IList<int> ids, int buildingId)
        {
            var b = B(buildingId); if (b == null || b.destroyed || b.complete) return;
            foreach (var id in ids) { var u = U(id); if (u != null && u.Alive && u.IsCitizen) { if (u.state == UnitState.Scholar) EjectOne(u); OrderBuild(u, b); } }
        }

        public void CmdAttack(IList<int> ids, int targetUnit, int targetBuilding)
        {
            foreach (var id in ids)
            {
                var u = U(id); if (u == null || !u.Alive || u.Hidden) continue;
                ReleaseWork(u);
                u.targetUnit = targetUnit; u.targetBuilding = targetBuilding; u.attackMove = false; u.state = UnitState.Attacking;
            }
        }

        public void CmdScholar(IList<int> ids, int buildingId)
        {
            var b = B(buildingId); if (b == null || !b.complete || b.def.scholarSlots == 0) return;
            int room = b.def.scholarSlots - b.scholars;
            foreach (var o in units) if (o.state == UnitState.ToScholar && o.buildingId == b.id) room--;
            foreach (var id in ids)
            {
                if (room <= 0) break;
                var u = U(id); if (u == null || !u.Alive || !u.IsCitizen || u.state == UnitState.Scholar) continue;
                ReleaseWork(u);
                u.buildingId = b.id; u.state = UnitState.ToScholar; MoveTo(u, b.pos, b.def.radius + 0.7f); room--;
            }
        }

        void EjectOne(Unit u)
        {
            var b = B(u.buildingId);
            if (b != null) { b.scholars = Math.Max(0, b.scholars - 1); u.pos = b.pos + new Vec2(0.7f, -0.7f).Normalized * (b.def.radius + 1.0f); }
            u.state = UnitState.Idle;
        }

        public void CmdEject(int buildingId)
        {
            foreach (var u in units) if (u.state == UnitState.Scholar && u.buildingId == buildingId) { EjectOne(u); return; }
        }

        public void CmdRally(int buildingId, Vec2 p) { var b = B(buildingId); if (b != null) { b.rally = p; b.hasRally = true; } }

        /// <summary>Why a site is refused, or null if it is fine. One function, used by the ghost AND the command.</summary>
        public string SiteProblem(int owner, BuildingType type, Vec2 pos)
        {
            var d = Catalog.Buildings[type];
            if (type != BuildingType.Hall && territory.OwnerAt(pos) != owner) return "Outside your border";
            if (siteOk != null && !siteOk(pos, d.radius)) return "Ground too steep or wet";
            foreach (var b in buildings)
                if (!b.destroyed && Vec2.Dist(b.pos, pos) < b.def.radius + d.radius + 0.6f) return "Too close to " + b.def.name;
            foreach (var n in nodes)
                if (!n.Depleted && n.kind != NodeKind.Tree && n.kind != NodeKind.Farm &&
                    Vec2.Dist(n.pos, pos) < Catalog.NodeRadius(n.kind) + d.radius) return "Blocked by a resource";
            return null;
        }

        /// <summary>Overlap only -- for world setup, where there is no border yet.</summary>
        public string SiteProblemIgnoringBorder(Vec2 pos, float radius)
        {
            foreach (var b in buildings)
                if (!b.destroyed && Vec2.Dist(b.pos, pos) < b.def.radius + radius + 0.6f) return "Too close to " + b.def.name;
            foreach (var n in nodes)
                if (!n.Depleted && n.kind != NodeKind.Tree && Vec2.Dist(n.pos, pos) < Catalog.NodeRadius(n.kind) + radius) return "Blocked by a resource";
            return null;
        }

        public Building CmdPlace(int owner, BuildingType type, Vec2 pos, float rot, IList<int> builders, out string problem)
        {
            var d = Catalog.Buildings[type];
            problem = SiteProblem(owner, type, pos);
            if (problem == null && !players[owner].stock.CanAfford(d.cost)) problem = "Not enough resources";
            if (problem != null) return null;
            players[owner].stock.Pay(d.cost);
            var b = SpawnBuilding(owner, type, pos, rot, false);
            // trees standing on the footprint are cleared (and refunded as a little wood)
            foreach (var n in nodes)
                if (n.kind == NodeKind.Tree && !n.Depleted && Vec2.Dist(n.pos, pos) < d.radius + 0.8f)
                { players[owner].stock[Res.Wood] += 10; n.amount = 0; DepleteNode(n); }
            Emit(SimEventType.BuildingPlaced, b.id, owner, pos);
            if (builders != null) CmdBuild(builders, b.id);
            return b;
        }

        public string CmdTrain(int buildingId, UnitType type)
        {
            var b = B(buildingId); if (b == null || !b.complete) return "Not ready";
            if (Array.IndexOf(b.def.trains, type) < 0) return "Cannot train that here";
            if (b.queue.Count >= 5) return "Queue is full";
            var d = Catalog.Units[type]; var p = players[b.owner];
            if (!p.stock.CanAfford(d.cost)) return "Not enough resources";
            if (p.popUsed + d.pop > p.popCap) return "Build more huts";
            p.stock.Pay(d.cost); p.popUsed += d.pop;             // pop is reserved now, so the queue cannot overshoot the cap
            b.queue.Add(type);
            return null;
        }

        // ------------------------------------------------------------------ research
        public int TechsDone(int owner) => players[owner].techs.Count;

        public string CmdResearch(int buildingId, string techId)
        {
            var b = B(buildingId); if (b == null || !b.complete || b.def.scholarSlots == 0) return "Needs a Rune Hall";
            if (b.researching != null) return "Already researching";
            var p = players[b.owner];
            if (techId == "age")
            {
                if (p.age >= 2) return "Already Feudal";
                if (TechsDone(b.owner) < Catalog.AgeAdvanceTechsRequired) return "Research " + Catalog.AgeAdvanceTechsRequired + " technologies first";
                if (!p.stock.CanAfford(Catalog.AgeAdvanceCost)) return "Not enough resources";
                p.stock.Pay(Catalog.AgeAdvanceCost);
                b.researching = "age"; b.researchingAge = true; b.researchTimer = Catalog.AgeAdvanceTime;
                Emit(SimEventType.AgeAdvanceStarted, b.id, b.owner, b.pos);
                return null;
            }
            var t = Array.Find(Catalog.Techs, x => x.id == techId);
            if (t == null) return "Unknown technology";
            if (p.techs.Contains(techId)) return "Already known";
            foreach (var o in buildings) if (o.researching == techId) return "Already researching";
            if (!p.stock.CanAfford(t.cost)) return "Not enough resources";
            p.stock.Pay(t.cost);
            b.researching = techId; b.researchingAge = false; b.researchTimer = t.time;
            return null;
        }

        void FinishResearch(Building b)
        {
            var p = players[b.owner]; string id = b.researching;
            b.researching = null; b.researchingAge = false;
            if (id == "age")
            {
                p.age = 2; p.borderBonus += Catalog.BorderTechBonus; p.gatherWoodFood *= 1.10f;
                RecomputeTerritory();
                Emit(SimEventType.AgeAdvanced, b.id, b.owner, b.pos, 2);
                return;
            }
            p.techs.Add(id);
            switch (id)
            {
                case "allthing":   p.borderBonus += Catalog.BorderTechBonus; p.buildMul *= 1.25f; RecomputeTerritory(); break;
                case "felling":    p.gatherWoodFood *= 1.20f; break;
                case "runelore":   p.knowledgeMul *= 1.35f; break;
                case "shieldwall":
                    p.soldierHpMul *= 1.20f; p.towerMul *= 1.25f;
                    foreach (var u in units) if (u.owner == b.owner && !u.IsCitizen) { u.maxHp *= 1.20f; u.hp *= 1.20f; }
                    break;
            }
            Emit(SimEventType.TechComplete, b.id, b.owner, b.pos, 0, Array.Find(Catalog.Techs, x => x.id == id).name);
        }
    }
}
