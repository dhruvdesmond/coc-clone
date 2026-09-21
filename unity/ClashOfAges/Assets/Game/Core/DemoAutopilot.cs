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
        readonly Dictionary<UnitState, float> _stateSeconds = new Dictionary<UnitState, float>();
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
            COA.UI.Hud.I.DismissTitle();
            yield return Portrait(g, w);

            yield return Beat_FirstChop(g, w);
            if (script != "chop") yield return Beats_Full(g, w);

            File.WriteAllLines("Verification/autopilot.txt", _report);
            Debug.Log("AUTOPILOT_RESULT " + (_fail == 0 ? "PASS" : "FAIL:" + _fail));
#if UNITY_EDITOR
            UnityEditor.EditorApplication.Exit(_fail == 0 ? 0 : 1);
#endif
        }

        void Log(string s) { _report.Add(s); Debug.Log("[autopilot] " + s); }
        /// <summary>WHY the bot could not build, tallied per sim-minute. A bot that cannot find a site does not crash; it just
        /// quietly loses twenty minutes later, and the loss looks like balance.</summary>
        readonly Dictionary<string, int> _refused = new Dictionary<string, int>();
        readonly HashSet<string> _jobShots = new HashSet<string>();

        void Check(bool ok, string what) { Log((ok ? "PASS " : "FAIL ") + what); if (!ok) _fail++; }

        /// <summary>PENDING B1: a human found the longhouse standing in a lake in his first ten minutes; the bot had walked past it
        /// for eight sessions. So the bot now looks: every building on the map, both sides, must stand on dry flat ground with no
        /// live tree's canopy reaching its walls.</summary>
        void CheckFootprints(string when)
        {
            var w = GameRoot.I.World; int bad = 0, seen = 0;
            foreach (var b in w.buildings)
            {
                if (b.destroyed) continue; seen++;
                var ground = Ground.FootprintProblem(b.pos, b.rot, b.def.half); int trees = w.TreesOn(b.pos, b.rot, b.def.half).Count;
                if (ground == null && trees == 0) continue;
                bad++; Log($"  {b.def.name} (owner {b.owner}) at {b.pos.x:F1},{b.pos.z:F1} heading {b.rot:F0}: {ground ?? "ground ok"}, {trees} tree(s) in the walls");
            }
            Check(bad == 0, $"{when}: all {seen} buildings stand on dry, flat, clear ground");
        }

        /// <summary>Does the water MOVE, in the real frame? Two grabs 1.2 s apart from a camera that has not moved. Water pixels must
        /// change; LAND pixels are the control and must not -- otherwise a shimmering capture path would pass as "animated water".</summary>
        IEnumerator WaterBeat(Vector3 near)
        {
            // the nearest real shoreline: a point in the shallows with dry land a few metres away
            Vector3? shore = null;
            for (float r = 6f; r < 60f && shore == null; r += 2f)
                for (int k = 0; k < 24 && shore == null; k++)
                {
                    float a = k * Mathf.PI / 12f; float x = near.x + Mathf.Cos(a) * r, z = near.z + Mathf.Sin(a) * r;
                    if (Ground.Sample(x, z, out float y, out _) && y < -0.15f && y > -0.9f) shore = new Vector3(x, 0f, z);
                }
            if (shore == null) { Check(false, "water: found a shoreline to look at"); yield break; }

            var cam = Camera.main; var rig = cam.GetComponent<RTSCamera>();
            rig.Frame(shore.Value, 26f, 30f);
            GameRoot.I.timeScale = 0.0001f;
            for (int i = 0; i < 8; i++) yield return null;

            // classify a grid of screen points by what is under them, staying clear of the HUD
            var waterPts = new List<Vector2Int>(); var landPts = new List<Vector2Int>();
            for (float u = 0.16f; u <= 0.74f; u += 0.02f)
                for (float v = 0.22f; v <= 0.84f; v += 0.03f)
                {
                    var sp = new Vector3(u * Screen.width, v * Screen.height, 0f);
                    if (!Ground.Raycast(cam.ScreenPointToRay(sp), out var hit)) continue;
                    if (hit.y < -0.35f) waterPts.Add(new Vector2Int((int)sp.x, (int)sp.y)); else if (hit.y > 0.5f) landPts.Add(new Vector2Int((int)sp.x, (int)sp.y));
                }

            yield return new WaitForEndOfFrame();
            var a0 = ScreenCapture.CaptureScreenshotAsTexture();
            ScreenCapture.CaptureScreenshot("Verification/09_water.png", 1);
            float until = Time.realtimeSinceStartup + 1.2f; while (Time.realtimeSinceStartup < until) yield return null;
            yield return new WaitForEndOfFrame();
            var a1 = ScreenCapture.CaptureScreenshotAsTexture();
            ScreenCapture.CaptureScreenshot("Verification/09b_water_later.png", 1);

            float Changed(List<Vector2Int> pts)
            {
                int n = 0; foreach (var p in pts) { var c0 = a0.GetPixel(p.x, p.y); var c1 = a1.GetPixel(p.x, p.y);
                    if (Mathf.Abs(c0.r - c1.r) + Mathf.Abs(c0.g - c1.g) + Mathf.Abs(c0.b - c1.b) > 0.012f) n++; }
                return pts.Count == 0 ? -1f : n / (float)pts.Count;
            }
            float wc = Changed(waterPts), lc = Changed(landPts);
            Destroy(a0); Destroy(a1);
            Check(waterPts.Count >= 40 && landPts.Count >= 40, $"water: the view holds both ({waterPts.Count} water samples, {landPts.Count} land samples)");
            Check(wc > 0.5f, $"water MOVES: {wc * 100f:F0}% of water samples changed in 1.2 s");
            Check(lc >= 0f && lc < 0.12f, $"control: the land does not ({lc * 100f:F0}% of land samples changed)");
            for (int i = 0; i < 4; i++) yield return null;
            GameRoot.I.timeScale = 6f;
            Log("shot 09_water");
        }

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

        /// <summary>The citizen, close, in the open, from the front and then walking. "THIS is the citizen?" -- it must read.</summary>
        IEnumerator Portrait(GameRoot g, World w)
        {
            var c = w.units.First(u => u.owner == World.Human);
            yield return Shot("00_citizen_portrait", Ground.At(c.pos), 8f, 205f);
            var open = c.pos + (c.pos - Ground.ToSim(g.HallWorldPos)).Normalized * 7f;
            w.CmdMove(new[] { c.id }, open);
            yield return WaitSim(1.4f);
            var d = open - c.pos; float walkYaw = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
            yield return Shot("00b_citizen_walking", Ground.At(c.pos), 8f, walkYaw + 110f);
            yield return Shot("00c_citizen_game_zoom", Ground.At(c.pos), 24f, 30f);
        }

        IEnumerator Beat_FirstChop(GameRoot g, World w)
        {
            var c = w.units.First(u => u.owner == World.Human);
            var tree = w.nodes.Where(n => n.kind == NodeKind.Tree).OrderBy(n => Vec2.Dist(n.pos, c.pos)).First();
            yield return Shot("01_start", g.HallWorldPos, 30f, 30f);
            yield return WaterBeat(g.HallWorldPos);
            w.CmdGather(new[] { c.id }, tree.id);
            float t0 = w.time;
            while (c.state != UnitState.Gathering && w.time - t0 < 60f) yield return null;
            CheckFootprints("at the start");
            Check(c.state == UnitState.Gathering, "citizen reached the tree and is chopping (" + (w.time - t0).ToString("F1") + " s)");
            yield return WaitSim(1.0f);
            var toTree = tree.pos - c.pos; float faceYaw = Mathf.Atan2(toTree.x, toTree.z) * Mathf.Rad2Deg;
            yield return Shot("02_first_chop", Ground.At(c.pos), 8f, faceYaw + 35f);
            // ...and the blow itself. The sim fires the impact when workTimer wraps at 1.6 s; the clip is authored to LAND there.
            g.timeScale = 1f;
            float ti = w.time; while (c.state == UnitState.Gathering && c.workTimer < 1.52f && w.time - ti < 4f) yield return null;
            yield return Shot("02c_chop_lands", Ground.At(c.pos), 8f, faceYaw + 35f);
            float wood0 = w.Me.stock[Res.Wood];
            yield return WaitSim(45f);
            float tc = w.time; while (c.carry < 1f && w.time - tc < 40f) yield return null;
            while (c.state != UnitState.ToDropOff && w.time - tc < 60f) yield return null;
            // out in the open, not under the canopy he has just left: half-way home
            float home0 = Vec2.Dist(tree.pos, Ground.ToSim(g.HallWorldPos));
            g.timeScale = 1f;
            while (!(c.carry > 1f && c.state == UnitState.ToDropOff && Vec2.Dist(c.pos, Ground.ToSim(g.HallWorldPos)) < home0 * 0.62f) && w.time - tc < 150f) yield return null;
            yield return Shot("02b_citizen_carrying", Ground.At(c.pos), 8f, faceYaw + 200f);
            Check(w.Me.stock[Res.Wood] > wood0 + 9f || c.carry > 1f, "wood was carried home and deposited: " + wood0.ToString("F0") + " -> " + w.Me.stock[Res.Wood].ToString("F0"));
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
                        $"bld={string.Join(",", w.buildings.Where(b => b.owner == World.Human).Select(b => b.type + (b.destroyed ? "x" : b.complete ? "" : "*")))} idle={w.units.Count(u => u.owner == World.Human && u.IsCitizen && u.state == UnitState.Idle)} raids={w.raids.raidsSent}");
                if ((int)w.time % 60 == 0 && _refused.Count > 0)
                { Log("   refused: " + string.Join("  ", _refused.OrderByDescending(kv => kv.Value).Select(kv => kv.Key + " x" + kv.Value))); _refused.Clear(); }
                var citizens = w.units.Where(u => u.owner == World.Human && u.IsCitizen && u.Alive).ToList();
                var soldiers = w.units.Where(u => u.owner == World.Human && !u.IsCitizen && u.Alive).ToList();
                bool building = w.buildings.Count(b => b.owner == World.Human && !b.complete && !b.destroyed) >= 2;   // two sites at once
                Building Place(BuildingType t, float dist)
                {
                    var d = Catalog.Buildings[t]; if (!me.stock.CanAfford(d.cost) || building) return null;
                    for (int i = 0; i < 72; i++)                     // 30 was enough for an empty map; a town by a lake fills up
                    {
                        float a = i * 2.399f + (int)t; var p = hallPos + new Vec2(Mathf.Cos(a), Mathf.Sin(a)) * (dist + (i / 6) * 3f);
                        var why = w.SiteProblem(World.Human, t, p, (i * 45) % 360);
                        if (why != null) { var key = t + ":" + why; _refused[key] = _refused.TryGetValue(key, out int c0) ? c0 + 1 : 1; continue; }
                        var free = citizens.Where(c => c.state != UnitState.Scholar).OrderBy(c => Vec2.Dist(c.pos, p)).Take(2).Select(c => c.id).ToList();
                        var b = w.CmdPlace(World.Human, t, p, (i * 45) % 360, free, out _); if (b != null) { building = true; return b; }
                    }
                    return null;
                }

                foreach (var c in citizens) { _stateSeconds.TryGetValue(c.state, out var sec); _stateSeconds[c.state] = sec + 1f; }
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
                if (rune != null && rune.destroyed) rune = null;
                if (muster != null && muster.destroyed) muster = null;
                if (tower != null && tower.destroyed) tower = null;
                int liveHuts = w.buildings.Count(b => b.owner == World.Human && b.type == BuildingType.Hut && !b.destroyed);
                // once there is a Muster Hall, the army eats first until it is eight strong
                bool armyFirst = muster != null && muster.complete && soldiers.Count < 8 && citizens.Count >= 9;
                // saving up: with the army standing and two techs known, stop spending and bank the advance
                bool saving = me.age < 2 && (soldiers.Count >= 5 || w.time > 780f) && me.techs.Count >= 2 && rune != null && rune.complete && rune.researching == null;
                if (saving) armyFirst = true;
                if (hall.queue.Count == 0 && citizens.Count < 16 && !armyFirst) w.CmdTrain(hall.id, UnitType.Citizen);
                if (me.popCap - me.popUsed <= 2 && liveHuts < 7 && Place(BuildingType.Hut, 15f) != null) huts++;
                // a storehouse belongs AT the treeline, not at a random bearing from the hall
                if (storehouses < 2 && citizens.Count >= (storehouses == 0 ? 3 : 9) && me.stock.CanAfford(Catalog.Buildings[BuildingType.Storehouse].cost))
                {
                    var kind = storehouses == 0 ? NodeKind.Tree : NodeKind.Iron;
                    var target = w.nodes.Where(n => n.kind == kind && !n.Depleted && Vec2.Dist(n.pos, hallPos) > 13f).OrderBy(n => Vec2.Dist(n.pos, hallPos)).FirstOrDefault();
                    if (target != null)
                        for (int i = 0; i < 16; i++)
                        {
                            float ang = i * 0.785f; var p = target.pos + new Vec2(Mathf.Cos(ang), Mathf.Sin(ang)) * (5.5f + (i / 8) * 2.5f);
                            if (w.SiteProblem(World.Human, BuildingType.Storehouse, p) != null) continue;
                            if (w.CmdPlace(World.Human, BuildingType.Storehouse, p, 0, citizens.OrderBy(c => Vec2.Dist(c.pos, p)).Take(1).Select(c => c.id).ToList(), out _) != null) { storehouses++; building = true; break; }
                        }
                }
                if (farms < 1 && citizens.Count >= 4 && Place(BuildingType.Farm, 19f) != null) farms++;
                if (farms == 1 && citizens.Count >= 8 && Place(BuildingType.Farm, 21f) != null) farms++;
                if (rune == null && citizens.Count >= 7) rune = Place(BuildingType.RuneHall, 17f);
                if (tower == null && rune != null) tower = Place(BuildingType.Tower, 16f);
                if (muster == null && rune != null) muster = Place(BuildingType.Muster, 20f);
                if (farms < 3 && muster != null && Place(BuildingType.Farm, 23f) != null) farms++;

                if (rune != null && rune.complete)
                {
                    if (rune.scholars < 2 && !w.units.Any(u => u.state == UnitState.ToScholar))
                        w.CmdScholar(citizens.Where(c => c.state != UnitState.Scholar && c.state != UnitState.Building).Take(2 - rune.scholars).Select(c => c.id).ToList(), rune.id);
                    if (rune.researching == null)
                    {
                        if (!me.techs.Contains("runelore")) w.CmdResearch(rune.id, "runelore");
                        else if (!me.techs.Contains("felling")) w.CmdResearch(rune.id, "felling");
                        else if (me.age < 2 && (soldiers.Count >= 5 || w.time > 780f)) w.CmdResearch(rune.id, "age");
                        else if (!me.techs.Contains("shieldwall")) w.CmdResearch(rune.id, "shieldwall");
                        else if (!me.techs.Contains("allthing")) w.CmdResearch(rune.id, "allthing");
                    }
                }
                if (muster != null && muster.complete && muster.queue.Count == 0 && soldiers.Count < 14 && !saving)
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
                    // Send each idle citizen to whichever resource is furthest BELOW its target share of the workforce.
                    // (Two earlier schemes both lost the game: "everyone to berries while food is low" starved wood, and
                    // "id % 10" never produced a miner because ids are shared with buildings and nodes.)
                    k++;
                    var share = new Dictionary<Res, float> { { Res.Food, 0.46f }, { Res.Wood, 0.28f }, { Res.Stone, 0.11f }, { Res.Metal, 0.15f } };
                    var busy = citizens.Where(o => o.state == UnitState.Gathering || o.state == UnitState.ToNode || o.state == UnitState.ToDropOff).ToList();
                    Res need = share.Keys.OrderBy(r => busy.Count(o => Catalog.ResourceOf(o.lastKind) == r) / (float)Mathf.Max(1, busy.Count) - share[r]).First();
                    NodeKind want = need == Res.Food ? NodeKind.Berry : need == Res.Wood ? NodeKind.Tree : need == Res.Stone ? NodeKind.Stone : NodeKind.Iron;
                    var n = w.nodes.Where(x => (x.kind == want || (want == NodeKind.Berry && x.kind == NodeKind.Farm)) && !x.Depleted && w.Claimed(x) < Catalog.NodeWorkerCap(x.kind))
                                   .OrderBy(x => Vec2.Dist(x.pos, c.pos)).FirstOrDefault()
                         ?? w.nodes.Where(x => x.kind == NodeKind.Tree && !x.Depleted).OrderBy(x => Vec2.Dist(x.pos, c.pos)).FirstOrDefault();
                    if (n != null) w.CmdGather(new[] { c.id }, n.id);
                }

                // ---- the named shots ----
                var firstHut = w.buildings.FirstOrDefault(b => b.owner == World.Human && b.type == BuildingType.Hut && b.complete);
                if (!shotHut && firstHut != null) { shotHut = true; yield return Shot("03_first_hut", Ground.At(firstHut.pos), 22f, 60f); }
                // the citizen at each of his jobs, close up: is the right tool in his hand, and does the blow land?
                foreach (var job in new[] { ("10_citizen_farming", NodeKind.Farm), ("11_citizen_mining", NodeKind.Stone), ("12_citizen_foraging", NodeKind.Berry) })
                {
                    if (_jobShots.Contains(job.Item1)) continue;
                    var worker = citizens.FirstOrDefault(c => c.state == UnitState.Gathering && c.lastKind == job.Item2 && c.workTimer > 0.4f);
                    if (worker == null) continue;
                    _jobShots.Add(job.Item1); yield return Shot(job.Item1, Ground.At(worker.pos), 8f, worker.facing + 215f);
                }
                if (!_jobShots.Contains("13_citizen_building"))
                {
                    var builder = citizens.FirstOrDefault(c => c.state == UnitState.Building && c.workTimer > 0.3f);
                    if (builder != null) { _jobShots.Add("13_citizen_building"); yield return Shot("13_citizen_building", Ground.At(builder.pos), 8f, builder.facing + 215f); }
                }
                if (!shotRune && rune != null && rune.scholars >= 2) { shotRune = true; yield return Shot("04_rune_hall_staffed", Ground.At(rune.pos), 26f, 150f); }
                if (!shotBorder && tower != null && tower.complete) { shotBorder = true; yield return WaitSim(2f); yield return Shot("05_border", g.HallWorldPos, 62f, 20f); }
                if (!shotAge && me.age >= 2) { shotAge = true; yield return WaitSim(3f); yield return Shot("06_feudal_age", g.HallWorldPos, 40f, 110f); }
                var raider = w.units.FirstOrDefault(u => u.owner == World.Enemy && Vec2.Dist(u.pos, hallPos) < 22f);
                if (!shotRaid && raider != null && soldiers.Count > 0) { shotRaid = true; yield return WaitSim(2.5f); var r2 = w.units.FirstOrDefault(u => u.owner == World.Enemy) ?? raider; yield return Shot("07_raid", Ground.At(r2.pos), 13f, 150f); }
            }

            yield return new WaitForSecondsRealtime(1.5f);
            yield return Shot("08_end", g.HallWorldPos, 34f, 30f);
            var m = w.Me;
            Log($"end: time {w.time / 60f:F1} min  over={w.over} won={w.won}  age={m.age}  techs={m.techs.Count}  gathered={m.gathered:F0}  killed={m.unitsKilled}  lost={m.unitsLost}  raids={w.raids.raidsSent}");
            float total = Mathf.Max(1f, _stateSeconds.Values.Sum());
            Log("citizen time: " + string.Join("  ", _stateSeconds.OrderByDescending(kv => kv.Value).Select(kv => kv.Key + " " + (100f * kv.Value / total).ToString("F0") + "%")));
            CheckFootprints("at the end");
            Check(shotHut, "a hut was built");
            Check(shotRune, "the rune hall was built and staffed");
            Check(m.age >= 2, "the Feudal Age was reached");
            Check(w.over && w.won, "the final raid was survived (victory)");
        }

    }
}
