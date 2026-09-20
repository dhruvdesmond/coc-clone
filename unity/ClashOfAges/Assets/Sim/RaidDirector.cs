using System;
using System.Collections.Generic;

namespace COA.Sim
{
    /// <summary>
    /// The demo's opponent. SCRIPTED, and says so: escalating raids from an enemy camp, not the
    /// three-layer utility AI in docs/06. It exists so the demo is a game and the border/attrition
    /// rules have something to act on.
    /// </summary>
    public sealed class RaidDirector
    {
        readonly World _w;
        public bool enabled = true;
        public Vec2 campPos, targetPos;
        public float firstRaidAt = 420f, interval = 180f;
        public int raidsSent; public float nextRaidAt; public bool finalSent; public float finalAt = -1f;
        readonly List<int> _live = new List<int>();

        public RaidDirector(World w) { _w = w; nextRaidAt = firstRaidAt; }
        public bool FinalRaidDefeated { get; private set; }
        public int LiveRaiders => _live.Count;
        public float SecondsToNextRaid => finalSent ? -1f : (finalAt > 0f ? Math.Min(nextRaidAt, finalAt) : nextRaidAt) - _w.time;

        public void Tick()
        {
            if (!enabled) return;
            bool hadLive = _live.Count > 0;
            _live.RemoveAll(id => _w.U(id) == null || !_w.U(id).Alive);
            if (hadLive && _live.Count == 0)
            {
                _w.events.Add(new SimEvent { type = SimEventType.RaidDefeated, a = raidsSent });
                if (finalSent) FinalRaidDefeated = true;
            }

            // reaching Feudal summons the last, largest raid a minute later
            if (finalAt < 0f && _w.players[World.Human].age >= 2) finalAt = _w.time + 60f;

            if (!finalSent && finalAt > 0f && _w.time >= finalAt) { Send(5, 4, 3, true); return; }
            if (!finalSent && _w.time >= nextRaidAt)
            {
                int k = raidsSent;
                Send(2 + k, k >= 1 ? 1 + k / 2 : 0, k >= 2 ? k - 1 : 0, false);
                nextRaidAt = _w.time + interval;
            }
        }

        void Send(int swords, int spears, int archers, bool final)
        {
            raidsSent++; if (final) finalSent = true;
            var ids = new List<int>();
            void Spawn(UnitType t, int n)
            {
                for (int i = 0; i < n; i++)
                {
                    var u = _w.SpawnUnit(World.Enemy, t, campPos + new Vec2((ids.Count % 4) * 1.4f - 2f, (ids.Count / 4) * 1.4f + 6f));
                    ids.Add(u.id); _live.Add(u.id);
                }
            }
            Spawn(UnitType.Swordsman, swords); Spawn(UnitType.Spearman, spears); Spawn(UnitType.Archer, archers);
            _w.players[World.Enemy].popCap = 999;
            _w.CmdMove(ids, targetPos, attackMove: true);
            _w.events.Add(new SimEvent { type = SimEventType.RaidIncoming, a = raidsSent, b = final ? 1 : 0, pos = campPos, amount = ids.Count });
        }
    }
}
