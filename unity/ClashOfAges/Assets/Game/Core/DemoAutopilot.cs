using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// Plays the demo without a human, takes screenshots at named beats, asserts, and quits.
    /// Dormant unless Temp/coa_autopilot.flag exists -- DemoVerify writes it before entering play mode.
    /// This is the visual regression check: if every beat renders, the whole pipeline is intact.
    /// </summary>
    public sealed class DemoAutopilot : MonoBehaviour
    {
        const string Flag = "Temp/coa_autopilot.flag";
        readonly List<string> _report = new List<string>();
        int _fail;

        IEnumerator Start()
        {
            if (!File.Exists(Flag)) yield break;
            string script = File.ReadAllText(Flag).Trim();
            File.Delete(Flag);
            var g = GameRoot.I; var w = g.World;
            Application.runInBackground = true; QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            g.paused = false; g.timeScale = 6f; g.maxTicksPerFrame = 60;
            yield return null; yield return null;
            Log("autopilot script: " + script);

            yield return Beat_FirstChop(g, w);
            if (script != "chop") yield return Beats_Full(g, w);

            File.WriteAllLines("Verification/autopilot.txt", _report);
            Debug.Log("AUTOPILOT_RESULT " + (_fail == 0 ? "PASS" : "FAIL:" + _fail));
#if UNITY_EDITOR
            UnityEditor.EditorApplication.Exit(_fail == 0 ? 0 : 1);
#endif
        }

        void Log(string s) { _report.Add(s); Debug.Log("[autopilot] " + s); }
        void Check(bool ok, string what) { Log((ok ? "PASS " : "FAIL ") + what); if (!ok) _fail++; }

        IEnumerator Shot(string name, Vector3 focus, float height, float yaw)
        {
            var rig = Camera.main.GetComponent<RTSCamera>();
            rig.Frame(focus, height, yaw);
            GameRoot.I.timeScale = 0.0001f;                       // freeze the moment, keep rendering
            for (int i = 0; i < 6; i++) yield return null;
            Directory.CreateDirectory("Verification");
            ScreenCapture.CaptureScreenshot("Verification/" + name + ".png", 1);
            for (int i = 0; i < 4; i++) yield return null;
            GameRoot.I.timeScale = 6f;
            Log("shot " + name);
        }

        IEnumerator WaitSim(float seconds)
        {
            float until = GameRoot.I.World.time + seconds;
            while (GameRoot.I.World.time < until && !GameRoot.I.World.over) yield return null;
        }

        IEnumerator Beat_FirstChop(GameRoot g, World w)
        {
            var c = w.units.First(u => u.owner == World.Human);
            var tree = w.nodes.Where(n => n.kind == NodeKind.Tree).OrderBy(n => Vec2.Dist(n.pos, c.pos)).First();
            yield return Shot("01_start", g.HallWorldPos, 30f, 30f);
            w.CmdGather(new[] { c.id }, tree.id);
            float t0 = w.time;
            while (c.state != UnitState.Gathering && w.time - t0 < 60f) yield return null;
            Check(c.state == UnitState.Gathering, "citizen reached the tree and is chopping (" + (w.time - t0).ToString("F1") + " s)");
            yield return WaitSim(1.0f);
            yield return Shot("02_first_chop", Ground.At(c.pos), 11f, 200f);
            float wood0 = w.Me.stock[Res.Wood];
            yield return WaitSim(45f);
            Check(w.Me.stock[Res.Wood] > wood0 + 9f, "wood was carried home and deposited: " + wood0.ToString("F0") + " -> " + w.Me.stock[Res.Wood].ToString("F0"));
        }

        /// <summary>A competent-but-plain bot plays the whole arc while the camera takes the named shots.</summary>
        IEnumerator Beats_Full(GameRoot g, World w)
        {
            var hall = w.buildings.First(b => b.owner == World.Human && b.type == BuildingType.Hall);
            var hallPos = hall.pos; Building rune = null, muster = null, tower = null; int huts = 0, storehouses = 0, farms = 0;
            bool shotHut = false, shotRune = false, shotBorder = false, shotAge = false, shotRaid = false; float last = -1f;
            g.timeScale = 8f; COA.UI.Hud.I.DismissTitle();
            Log("nodes: " + string.Join(" ", w.nodes.GroupBy(n => n.kind).Select(gr => gr.Key + "x" + gr.Count())));
            w.CmdRally(hall.id, hallPos + new Vec2(0, -10));

            while (!w.over && w.time < 60f * 40f)
            {
                yield return null;
                if (w.time - last < 1f) continue; last = w.time;
                var me = w.Me;
                if ((int)w.time % 60 == 0)
                    Log($"t={w.time / 60f:F0}m real={Time.realtimeSinceStartup:F0}s fps={1f / Time.unscaledDeltaTime:F0} cit={w.units.Count(u => u.owner == World.Human && u.IsCitizen)} sol={w.units.Count(u => u.owner == World.Human && !u.IsCitizen)} " +
                        $"F={me.stock[Res.Food]:F0} W={me.stock[Res.Wood]:F0} S={me.stock[Res.Stone]:F0} M={me.stock[Res.Metal]:F0} K={me.stock[Res.Knowledge]:F0} pop={me.popUsed}/{me.popCap} " +
                        $"bld={string.Join(",", w.buildings.Where(b => b.owner == World.Human).Select(b => b.type + (b.complete ? "" : "*")))} idle={w.units.Count(u => u.owner == World.Human && u.IsCitizen && u.state == UnitState.Idle)} raids={w.raids.raidsSent}");
                var citizens = w.units.Where(u => u.owner == World.Human && u.IsCitizen && u.Alive).ToList();
                var soldiers = w.units.Where(u => u.owner == World.Human && !u.IsCitizen && u.Alive).ToList();
                bool building = w.buildings.Any(b => b.owner == World.Human && !b.complete && !b.destroyed);
                Building Place(BuildingType t, float dist)
                {
                    var d = Catalog.Buildings[t]; if (!me.stock.CanAfford(d.cost) || building) return null;
                    for (int i = 0; i < 30; i++)
                    {
                        float a = i * 2.399f + (int)t; var p = hallPos + new Vec2(Mathf.Cos(a), Mathf.Sin(a)) * (dist + (i / 6) * 3f);
                        if (w.SiteProblem(World.Human, t, p) != null) continue;
                        var free = citizens.Where(c => c.state != UnitState.Scholar).OrderBy(c => Vec2.Dist(c.pos, p)).Take(2).Select(c => c.id).ToList();
                        var b = w.CmdPlace(World.Human, t, p, (i * 45) % 360, free, out _); if (b != null) { building = true; return b; }
                    }
                    return null;
                }

                if ((int)w.time % 60 == 0)
                {
                    Log("   states: " + string.Join(" ", citizens.GroupBy(c => c.state).Select(gr => gr.Key + "x" + gr.Count())));
                    foreach (var c in citizens.Where(c => c.hasMoveTarget).Take(4))
                    {
                        g.unitViews.TryGetValue(c.id, out var v); var ag = v != null ? v.GetComponent<UnityEngine.AI.NavMeshAgent>() : null;
                        Log($"   #{c.id} {c.state} dist={Vec2.Dist(c.pos, c.moveTarget):F2} stop={c.stopDistance:F2} blocked={c.blocked} " +
                            (ag != null && ag.isOnNavMesh ? $"path={ag.pathStatus} remaining={ag.remainingDistance:F2} vel={ag.velocity.magnitude:F2} stopped={ag.isStopped} agentStop={ag.stoppingDistance:F2}" : "NO AGENT/OFF MESH"));
                    }
                }
                if (hall.queue.Count == 0 && citizens.Count < 12) w.CmdTrain(hall.id, UnitType.Citizen);
                if (me.popCap - me.popUsed <= 1 && huts < 5 && Place(BuildingType.Hut, 15f) != null) huts++;
                if (storehouses == 0 && citizens.Count >= 4 && Place(BuildingType.Storehouse, 22f) != null) storehouses++;
                if (rune == null && citizens.Count >= 6) rune = Place(BuildingType.RuneHall, 17f);
                if (farms == 0 && rune != null && rune.complete && Place(BuildingType.Farm, 19f) != null) farms++;
                if (muster == null && rune != null && rune.complete) muster = Place(BuildingType.Muster, 20f);
                if (tower == null && muster != null) tower = Place(BuildingType.Tower, 24f);

                if (rune != null && rune.complete)
                {
                    if (rune.scholars < 2 && !w.units.Any(u => u.state == UnitState.ToScholar))
                        w.CmdScholar(citizens.Where(c => c.state != UnitState.Scholar && c.state != UnitState.Building).Take(2 - rune.scholars).Select(c => c.id).ToList(), rune.id);
                    if (rune.researching == null)
                    {
                        if (!me.techs.Contains("runelore")) w.CmdResearch(rune.id, "runelore");
                        else if (!me.techs.Contains("felling")) w.CmdResearch(rune.id, "felling");
                        else if (me.age < 2 && soldiers.Count >= 8) w.CmdResearch(rune.id, "age");
                        else if (!me.techs.Contains("shieldwall")) w.CmdResearch(rune.id, "shieldwall");
                        else if (!me.techs.Contains("allthing")) w.CmdResearch(rune.id, "allthing");
                    }
                }
                if (muster != null && muster.complete && muster.queue.Count == 0 && soldiers.Count < 14)
                {
                    w.CmdRally(muster.id, hallPos + new Vec2(6, -12));
                    var want = soldiers.Count % 3 == 0 ? UnitType.Spearman : soldiers.Count % 3 == 1 ? UnitType.Archer : UnitType.Swordsman;
                    if (w.CmdTrain(muster.id, want) != null) w.CmdTrain(muster.id, UnitType.Spearman);
                }

                int k = 0;
                foreach (var c in citizens.Where(c => c.state == UnitState.Idle))
                {
                    // a fixed split by citizen id: 4 food, 4 wood, 1 stone, 1 iron of every 10. ("Everyone to the
                    // berries while food is low" starved the wood economy forever, since food is ALWAYS low when spent.)
                    // by POSITION in the roster, not by id: ids are shared with buildings and nodes, so "id % 10 == 9"
                    // simply never occurred and nobody ever mined iron -- no metal, no Muster Hall, no army, defeat.
                    int slot = citizens.IndexOf(c) % 10; k++;
                    NodeKind want = slot < 4 ? NodeKind.Berry : slot < 8 ? NodeKind.Tree : slot == 8 ? NodeKind.Stone : NodeKind.Iron;
                    var n = w.nodes.Where(x => (x.kind == want || (want == NodeKind.Berry && x.kind == NodeKind.Farm)) && !x.Depleted && w.Claimed(x) < Catalog.NodeWorkerCap(x.kind))
                                   .OrderBy(x => Vec2.Dist(x.pos, c.pos)).FirstOrDefault()
                         ?? w.nodes.Where(x => x.kind == NodeKind.Tree && !x.Depleted).OrderBy(x => Vec2.Dist(x.pos, c.pos)).FirstOrDefault();
                    if (n != null) w.CmdGather(new[] { c.id }, n.id);
                }

                // ---- the named shots ----
                var firstHut = w.buildings.FirstOrDefault(b => b.owner == World.Human && b.type == BuildingType.Hut && b.complete);
                if (!shotHut && firstHut != null) { shotHut = true; yield return Shot("03_first_hut", Ground.At(firstHut.pos), 22f, 60f); }
                if (!shotRune && rune != null && rune.scholars >= 2) { shotRune = true; yield return Shot("04_rune_hall_staffed", Ground.At(rune.pos), 26f, 150f); }
                if (!shotBorder && tower != null && tower.complete) { shotBorder = true; yield return WaitSim(2f); yield return Shot("05_border", g.HallWorldPos, 62f, 20f); }
                if (!shotAge && me.age >= 2) { shotAge = true; yield return WaitSim(3f); yield return Shot("06_feudal_age", g.HallWorldPos, 40f, 110f); }
                var raider = w.units.FirstOrDefault(u => u.owner == World.Enemy && Vec2.Dist(u.pos, hallPos) < 22f);
                if (!shotRaid && raider != null && soldiers.Count > 0) { shotRaid = true; yield return WaitSim(2.5f); var r2 = w.units.FirstOrDefault(u => u.owner == World.Enemy) ?? raider; yield return Shot("07_raid", Ground.At(r2.pos), 17f, 150f); }
            }

            yield return new WaitForSecondsRealtime(1.5f);
            yield return Shot("08_end", g.HallWorldPos, 34f, 30f);
            var m = w.Me;
            Log($"end: time {w.time / 60f:F1} min  over={w.over} won={w.won}  age={m.age}  techs={m.techs.Count}  gathered={m.gathered:F0}  killed={m.unitsKilled}  lost={m.unitsLost}  raids={w.raids.raidsSent}");
            Check(shotHut, "a hut was built");
            Check(shotRune, "the rune hall was built and staffed");
            Check(m.age >= 2, "the Feudal Age was reached");
            Check(w.over && w.won, "the final raid was survived (victory)");
        }

    }
}
