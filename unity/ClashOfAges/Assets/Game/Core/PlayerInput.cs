using System.Collections.Generic;
using System.Linq;
using COA.Sim;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

namespace COA.Game
{
    /// <summary>
    /// Selection, orders and building placement. LEFT-CLICK IS SELECTION ONLY -- it is never
    /// bound to pan or to orders. Right-click is every contextual order. That split is the
    /// genre's muscle memory and breaking it is unforgivable.
    /// </summary>
    public sealed class PlayerInput : MonoBehaviour
    {
        public static PlayerInput I { get; private set; }

        public readonly List<int> units = new List<int>();
        public int building = -1, node = -1;
        public BuildingType? placing; public string placementProblem;
        public event System.Action<Vector3, bool> OnOrderIssued;        // world point, isAttack
        public event System.Action<string> OnRefused;
        public event System.Action OnSelectionChanged;

        GameRoot _g; World W => _g.World; Camera _cam;
        Vector2 _dragStart; bool _dragging; float _lastClickTime; int _lastClickUnit = -1;
        GameObject _ghost; float _ghostRot; Renderer[] _ghostRends; bool _ghostOk;
        readonly Dictionary<int, List<int>> _groups = new Dictionary<int, List<int>>();
        int _idleCursor;

        public Rect? DragRect { get; private set; }

        void Awake() { I = this; }
        void Start() { _g = GameRoot.I; _cam = Camera.main; }

        static bool OverUi() => EventSystem.current != null && EventSystem.current.IsPointerOverGameObject();

        void Update()
        {
            var mouse = Mouse.current; var kb = Keyboard.current;
            if (mouse == null || kb == null || _g == null || _g.paused) { DragRect = null; return; }
            Prune();
            Vector2 mp = mouse.position.ReadValue();

            if (placing.HasValue) { TickPlacement(mouse, kb, mp); return; }

            // ---------------- left: select ----------------
            if (mouse.leftButton.wasPressedThisFrame && !OverUi()) { _dragging = true; _dragStart = mp; }
            if (_dragging)
            {
                var r = Rect.MinMaxRect(Mathf.Min(_dragStart.x, mp.x), Mathf.Min(_dragStart.y, mp.y), Mathf.Max(_dragStart.x, mp.x), Mathf.Max(_dragStart.y, mp.y));
                DragRect = r.width > 6f || r.height > 6f ? r : (Rect?)null;
                if (mouse.leftButton.wasReleasedThisFrame)
                {
                    _dragging = false;
                    bool add = kb.shiftKey.isPressed;
                    if (DragRect.HasValue) BoxSelect(DragRect.Value, add); else ClickSelect(mp, add);
                    DragRect = null;
                }
            }

            // ---------------- right: every contextual order ----------------
            if (mouse.rightButton.wasPressedThisFrame && !OverUi()) _dragStart = mp;
            if (mouse.rightButton.wasReleasedThisFrame && !OverUi() && (mp - _dragStart).sqrMagnitude < 36f) ContextOrder(mp, kb);

            // ---------------- keys ----------------
            if (kb.escapeKey.wasPressedThisFrame) Clear();
            if (kb.periodKey.wasPressedThisFrame || kb.tabKey.wasPressedThisFrame) NextIdleCitizen();
            if (kb.hKey.wasPressedThisFrame && units.Count == 0 && building < 0) _cam.GetComponent<RTSCamera>().Frame(_g.HallWorldPos);
            if (kb.xKey.wasPressedThisFrame && units.Count > 0) W.CmdStop(units);
            var digits = new[] { kb.digit1Key, kb.digit2Key, kb.digit3Key, kb.digit4Key, kb.digit5Key };
            for (int i = 0; i < digits.Length; i++)
                if (digits[i].wasPressedThisFrame)
                {
                    if (kb.ctrlKey.isPressed || kb.leftCommandKey.isPressed) { _groups[i] = new List<int>(units); }
                    else if (_groups.TryGetValue(i, out var grp) && grp.Count > 0) { SetUnits(grp.Where(id => W.U(id) != null)); }
                }
        }

        // ------------------------------------------------------------------ selection
        void Prune()
        {
            int before = units.Count;
            units.RemoveAll(id => { var u = W.U(id); return u == null || !u.Alive; });
            if (building >= 0) { var b = W.B(building); if (b == null || b.destroyed) building = -1; }
            if (node >= 0) { var n = W.N(node); if (n == null || n.Depleted) node = -1; }
            if (before != units.Count) OnSelectionChanged?.Invoke();
        }

        public void Clear() { SetUnits(new int[0]); SelectBuilding(-1); SelectNode(-1); }

        void SetUnits(IEnumerable<int> ids)
        {
            foreach (var id in units) if (_g.unitViews.TryGetValue(id, out var v)) v.SetSelected(false);
            units.Clear(); units.AddRange(ids);
            foreach (var id in units) if (_g.unitViews.TryGetValue(id, out var v)) v.SetSelected(true);
            if (units.Count > 0) { SelectBuilding(-1); SelectNode(-1); }
            OnSelectionChanged?.Invoke();
        }

        void SelectBuilding(int id)
        {
            if (building >= 0 && _g.buildingViews.TryGetValue(building, out var old)) old.SetSelected(false);
            building = id;
            if (id >= 0 && _g.buildingViews.TryGetValue(id, out var v)) v.SetSelected(true);
            OnSelectionChanged?.Invoke();
        }

        void SelectNode(int id)
        {
            if (node >= 0 && _g.nodeViews.TryGetValue(node, out var old)) old.SetSelected(false);
            node = id;
            if (id >= 0 && _g.nodeViews.TryGetValue(id, out var v)) v.SetSelected(true);
        }

        Unit UnitNear(Vector2 screen, float pixels, bool mineOnly, bool enemyOnly)
        {
            Unit best = null; float bd = pixels * pixels;
            foreach (var u in W.units)
            {
                if (!u.Alive || u.Hidden) continue;
                if (mineOnly && u.owner != World.Human) continue;
                if (enemyOnly && u.owner == World.Human) continue;
                var sp = _cam.WorldToScreenPoint(Ground.At(u.pos) + Vector3.up * 0.9f);
                if (sp.z < 0f) continue;
                float d = ((Vector2)sp - screen).sqrMagnitude;
                if (d < bd) { bd = d; best = u; }
            }
            return best;
        }

        void ClickSelect(Vector2 mp, bool add)
        {
            var u = UnitNear(mp, 34f, true, false);
            if (u != null)
            {
                bool dbl = Time.unscaledTime - _lastClickTime < 0.32f && _lastClickUnit == u.id;
                _lastClickTime = Time.unscaledTime; _lastClickUnit = u.id;
                if (dbl)     // double-click: everything of that type on screen
                    SetUnits(W.units.Where(o => o.Alive && !o.Hidden && o.owner == World.Human && o.type == u.type && OnScreen(o)).Select(o => o.id));
                else if (add) { var l = new List<int>(units); if (l.Contains(u.id)) l.Remove(u.id); else l.Add(u.id); SetUnits(l); }
                else SetUnits(new[] { u.id });
                return;
            }
            var ray = _cam.ScreenPointToRay(mp);
            if (Physics.Raycast(ray, out var hit, 2000f, ~0, QueryTriggerInteraction.Collide))
            {
                var bv = hit.collider.GetComponentInParent<BuildingView>();
                if (bv != null) { SetUnits(new int[0]); SelectNode(-1); SelectBuilding(bv.buildingId); return; }
                var nv = hit.collider.GetComponentInParent<NodeView>();
                if (nv != null) { SetUnits(new int[0]); SelectBuilding(-1); SelectNode(nv.nodeId); return; }
            }
            if (!add) Clear();
        }

        bool OnScreen(Unit u)
        {
            var sp = _cam.WorldToScreenPoint(Ground.At(u.pos));
            return sp.z > 0 && sp.x >= 0 && sp.y >= 0 && sp.x <= Screen.width && sp.y <= Screen.height;
        }

        void BoxSelect(Rect r, bool add)
        {
            var picked = new List<int>(add ? units : new List<int>());
            var inside = W.units.Where(u => u.Alive && !u.Hidden && u.owner == World.Human).Where(u =>
            {
                var sp = _cam.WorldToScreenPoint(Ground.At(u.pos) + Vector3.up * 0.9f);
                return sp.z > 0 && r.Contains((Vector2)sp);
            }).ToList();
            // a box that catches soldiers means "my army": leave the citizens at work
            if (inside.Any(u => !u.IsCitizen)) inside = inside.Where(u => !u.IsCitizen).ToList();
            foreach (var u in inside) if (!picked.Contains(u.id)) picked.Add(u.id);
            if (picked.Count > 0 || !add) SetUnits(picked);
        }

        void NextIdleCitizen()
        {
            var idle = W.units.Where(u => u.owner == World.Human && u.IsCitizen && u.state == UnitState.Idle).ToList();
            if (idle.Count == 0) { OnRefused?.Invoke("No idle citizens"); return; }
            var u = idle[_idleCursor++ % idle.Count];
            SetUnits(new[] { u.id });
            _cam.GetComponent<RTSCamera>().Frame(Ground.At(u.pos));
        }

        public int IdleCitizens => W.units.Count(u => u.owner == World.Human && u.IsCitizen && u.state == UnitState.Idle);

        // ------------------------------------------------------------------ orders
        void ContextOrder(Vector2 mp, Keyboard kb)
        {
            var ray = _cam.ScreenPointToRay(mp);
            if (!Ground.Raycast(ray, out var ground)) return;
            var gp = Ground.ToSim(ground);

            if (units.Count == 0)
            {
                if (building >= 0 && W.B(building).owner == World.Human) { W.CmdRally(building, gp); OnOrderIssued?.Invoke(ground, false); }
                return;
            }
            var citizens = units.Where(id => W.U(id).IsCitizen).ToList();

            var enemy = UnitNear(mp, 30f, false, true);
            if (enemy != null) { W.CmdAttack(units, enemy.id, -1); OnOrderIssued?.Invoke(Ground.At(enemy.pos), true); return; }

            if (Physics.Raycast(ray, out var hit, 2000f, ~0, QueryTriggerInteraction.Collide))
            {
                var bv = hit.collider.GetComponentInParent<BuildingView>();
                if (bv != null)
                {
                    var b = bv.Building;
                    if (b.owner != World.Human) { W.CmdAttack(units, -1, b.id); OnOrderIssued?.Invoke(bv.transform.position, true); return; }
                    if (citizens.Count > 0)
                    {
                        if (!b.complete) { W.CmdBuild(citizens, b.id); OnOrderIssued?.Invoke(bv.transform.position, false); return; }
                        if (b.def.scholarSlots > 0) { W.CmdScholar(citizens, b.id); OnOrderIssued?.Invoke(bv.transform.position, false); return; }
                        if (b.type == BuildingType.Farm)
                        {
                            var farm = W.nodes.FirstOrDefault(n => n.farmBuilding == b.id);
                            if (farm != null) { W.CmdGather(citizens, farm.id); OnOrderIssued?.Invoke(bv.transform.position, false); return; }
                        }
                    }
                }
                var nv = hit.collider.GetComponentInParent<NodeView>();
                if (nv != null && citizens.Count > 0) { W.CmdGather(citizens, nv.nodeId); OnOrderIssued?.Invoke(nv.transform.position, false); return; }
            }

            if (citizens.Count > 0)       // trees have no colliders: nearest trunk to the clicked ground
            {
                Node tree = null; float bd = 2.4f;
                foreach (var n in W.nodes)
                    if (n.kind == NodeKind.Tree && !n.Depleted) { float d = Vec2.Dist(n.pos, gp); if (d < bd) { bd = d; tree = n; } }
                if (tree != null)
                {
                    // spread a group over neighbouring trees instead of queueing on one trunk
                    var near = W.nodes.Where(n => n.kind == NodeKind.Tree && !n.Depleted && Vec2.Dist(n.pos, tree.pos) < 9f)
                                      .OrderBy(n => Vec2.Dist(n.pos, tree.pos)).ToList();
                    for (int i = 0; i < citizens.Count; i++) W.CmdGather(new[] { citizens[i] }, near[(i / 2) % near.Count].id);
                    OnOrderIssued?.Invoke(Ground.At(tree.pos), false); return;
                }
            }

            bool attackMove = kb.aKey.isPressed || kb.ctrlKey.isPressed;
            W.CmdMove(units, gp, attackMove);
            OnOrderIssued?.Invoke(ground, attackMove);
        }

        // ------------------------------------------------------------------ placement
        public void BeginPlacement(BuildingType type)
        {
            CancelPlacement();
            if (!W.Me.stock.CanAfford(Catalog.Buildings[type].cost)) { OnRefused?.Invoke("Not enough resources"); return; }
            placing = type;
            var prefab = _g.models.Get(type == BuildingType.Hut ? "hut_a" : Catalog.Buildings[type].model);
            _ghost = prefab != null ? Instantiate(prefab) : GameObject.CreatePrimitive(PrimitiveType.Cube);
            _ghost.name = "PlacementGhost";
            foreach (var c in _ghost.GetComponentsInChildren<Collider>()) Destroy(c);
            _ghostRends = _ghost.GetComponentsInChildren<Renderer>();
            foreach (var r in _ghostRends) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            _ghostOk = true; PaintGhost(false);
        }

        public void CancelPlacement() { placing = null; placementProblem = null; if (_ghost != null) Destroy(_ghost); _ghost = null; }

        void PaintGhost(bool ok)
        {
            if (ok == _ghostOk && _ghostRends != null && _ghostRends.Length > 0 && _ghostRends[0].sharedMaterial == (ok ? _g.models.ghostOk : _g.models.ghostBad)) return;
            _ghostOk = ok;
            foreach (var r in _ghostRends)
            {
                var mats = new Material[r.sharedMaterials.Length];
                for (int i = 0; i < mats.Length; i++) mats[i] = ok ? _g.models.ghostOk : _g.models.ghostBad;
                r.sharedMaterials = mats;
            }
        }

        void TickPlacement(Mouse mouse, Keyboard kb, Vector2 mp)
        {
            if (kb.escapeKey.wasPressedThisFrame || mouse.rightButton.wasPressedThisFrame) { CancelPlacement(); return; }
            if (kb.rKey.wasPressedThisFrame) _ghostRot = (_ghostRot + 45f) % 360f;
            if (!Ground.Raycast(_cam.ScreenPointToRay(mp), out var ground)) return;
            var type = placing.Value; var gp = Ground.ToSim(ground);
            _ghost.transform.SetPositionAndRotation(Ground.At(gp), Quaternion.Euler(0f, _ghostRot, 0f));

            placementProblem = W.SiteProblem(World.Human, type, gp, _ghostRot);
            if (placementProblem == null && !W.Me.stock.CanAfford(Catalog.Buildings[type].cost)) placementProblem = "Not enough resources";
            PaintGhost(placementProblem == null);

            if (mouse.leftButton.wasPressedThisFrame && !OverUi())
            {
                var builders = units.Where(id => W.U(id) != null && W.U(id).IsCitizen).ToList();
                var b = W.CmdPlace(World.Human, type, gp, _ghostRot, builders, out var why);
                if (b == null) { OnRefused?.Invoke(why); return; }
                OnOrderIssued?.Invoke(ground, false);
                if (!kb.shiftKey.isPressed) CancelPlacement();
            }
        }
    }
}
