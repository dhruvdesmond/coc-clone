using COA.Sim;
using UnityEngine;
using UnityEngine.AI;

namespace COA.Game
{
    /// <summary>One per sim unit. Walks it on the NavMesh, poses it, and reports where it really is.</summary>
    public sealed class UnitView : MonoBehaviour
    {
        public const float UnitScale = 1.38f;
        public int unitId; public bool selected;
        GameObject _disc; GameRoot _root; Unit _u; NavMeshAgent _agent; UnitAnim _anim; GameObject _ring, _load; HealthBar _hp;
        Vector3 _lastDest = new Vector3(9999, 0, 9999); float _stuck; bool _dead; float _deadT; Renderer[] _rends;
        Vector3 _vel; Vector3 _prev;

        public Unit Unit => _u;

        // ---- the citizen's hands. Tools are separate props parented to his forearm bone; he holds the one the job needs and
        //      NOTHING while he carries. (The old figure had an axe welded to its hand: he farmed, mined and hauled with it.)
        static readonly string[] ToolNames = { "tool_axe", "tool_pick", "tool_hoe", "tool_hammer" };
        readonly GameObject[] _tools = new GameObject[4]; int _tool = -1; Transform _loadSocket;

        static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t) { var r = FindDeep(c, name); if (r != null) return r; }
            return null;
        }

        /// <summary>MUST run while the figure is still at rest (before the Animator poses it): props are placed square to the
        /// FIGURE, then handed to a bone. Done later, "square to the figure" would mean square to whatever pose he was in.</summary>
        void AttachProps(int layer)
        {
            var fore = FindDeep(transform, "ForeR"); var body = FindDeep(transform, "Body");
            if (fore != null && _u.IsCitizen && _root.models.Grip(_u.def.model, out var grip))
                for (int i = 0; i < ToolNames.Length; i++)
                {
                    var prefab = _root.models.Get(ToolNames[i]); if (prefab == null) continue;
                    var t = Instantiate(prefab, transform); t.name = ToolNames[i];
                    t.transform.localPosition = grip; t.transform.localRotation = Quaternion.identity; t.transform.localScale = Vector3.one;
                    t.transform.SetParent(fore, true);
                    // on the Units layer WITH him: the occluded-silhouette pass skips pixels a unit already drew. Left off it, a
                    // prop in front of his body made the pass paint his hidden torso over the prop -- the "ghost log".
                    foreach (var c in t.GetComponentsInChildren<Transform>(true)) c.gameObject.layer = layer;
                    t.SetActive(false); _tools[i] = t;
                }
            if (body != null)
            {
                _loadSocket = new GameObject("LoadSocket").transform; _loadSocket.SetParent(transform, false);
                _loadSocket.localPosition = new Vector3(0f, 1.06f, 0.33f);           // lying across both forearms (Carry clip)
                _loadSocket.SetParent(body, true);
            }
        }

        void UpdateTool()
        {
            int want = -1;
            if (_u.IsCitizen && !_dead && _u.carry <= 0.5f)
            {
                bool work = _u.state == UnitState.Gathering || _u.state == UnitState.ToNode;
                if (_u.state == UnitState.Building || _u.state == UnitState.ToBuild) want = 3;
                else if (work)
                {   // the node he is HEADING for, not the last one he worked: lastKind is only set on arrival
                    var node = _root.World.N(_u.nodeId); var kind = node != null ? node.kind : _u.lastKind;
                    want = kind == NodeKind.Tree ? 0 : kind == NodeKind.Farm ? 2 : kind == NodeKind.Berry ? -1 : 1;
                }
            }
            if (want == _tool) return;
            if (_tool >= 0 && _tools[_tool] != null) _tools[_tool].SetActive(false);
            if (want >= 0 && _tools[want] != null) _tools[want].SetActive(true);
            _tool = want;
        }

        public static UnitView Create(GameRoot root, Unit u)
        {
            var prefab = root.models.Get(u.def.model);
            var go = prefab != null ? Instantiate(prefab) : GameObject.CreatePrimitive(PrimitiveType.Capsule);
            go.name = u.def.name + "_" + u.id;
            int unitsLayer = LayerMask.NameToLayer("Units");             // the occluded-silhouette pass draws this layer
            if (unitsLayer >= 0) foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = unitsLayer;
            var v = go.AddComponent<UnitView>();
            v._root = root; v._u = u; v.unitId = u.id;
            go.transform.position = Ground.At(u.pos);
            // RTS convention: figures are drawn larger than life. A true-scale 1.75 m citizen seen from 30 m is a
            // dark speck (Dhruv: "THIS is the citizen?"). Buildings stay true scale; the sim is unaffected.
            go.transform.localScale = Vector3.one * UnitScale;

            v._agent = go.AddComponent<NavMeshAgent>();
            v._agent.radius = 0.34f; v._agent.height = 1.8f; v._agent.speed = u.def.speed;
            v._agent.acceleration = 40f; v._agent.angularSpeed = 720f; v._agent.autoBraking = true;
            v._agent.obstacleAvoidanceType = ObstacleAvoidanceType.MedQualityObstacleAvoidance;
            v._agent.avoidancePriority = 30 + (u.id % 40);
            if (NavMesh.SamplePosition(go.transform.position, out var hit, 6f, NavMesh.AllAreas)) v._agent.Warp(hit.position);

            // a real skeleton if the model has one (rig_figure.py), otherwise limbs posed in code
            v.AttachProps(unitsLayer >= 0 ? unitsLayer : 0);                     // while he is still at rest
            var controller = root.models.Controller(u.def.model);
            if (controller != null && RigAnimator.Supports(go)) { var ra = go.AddComponent<RigAnimator>(); ra.Init(controller, RigAnimator.StyleFor(u.def.model)); v._anim = ra; }
            else v._anim = go.AddComponent<FigureAnimator>();
            v._ring = MeshKit.Make("Ring", MeshKit.Ring, u.owner == World.Human ? root.models.ring : root.models.ringEnemy, go.transform);
            v._ring.transform.localPosition = new Vector3(0f, 0.06f, 0f);
            v._ring.transform.localScale = Vector3.one * 0.62f;
            v._ring.SetActive(u.owner != World.Human);           // enemies always wear their colour
            if (u.owner == World.Human)
            {   // your own people stand on a soft disc of your border colour: findable at a glance, not loud
                var disc = MeshKit.Make("TeamDisc", MeshKit.Disc, root.models.teamDisc, go.transform);
                disc.transform.localPosition = new Vector3(0f, 0.015f, 0f); disc.transform.localScale = Vector3.one * 0.44f;
                v._disc = disc;
            }
            v._hp = HealthBar.Create(go.transform, 2.15f, 0.9f, root.models);
            v._rends = go.GetComponentsInChildren<Renderer>();
            v._prev = go.transform.position;
            return v;
        }

        /// <summary>Called just before each sim tick: the sim must reason about where the unit actually is.</summary>
        public void PushToSim()
        {
            if (_dead || _u.Hidden || !_agent.isOnNavMesh) return;
            var p = transform.position; _u.pos = new Vec2(p.x, p.z);
            // a partial path that has gone still is "as close as it gets": let the sim accept a looser arrival
            bool still = _agent.velocity.sqrMagnitude < 0.02f && !_agent.pathPending;
            _stuck = _u.hasMoveTarget && still ? _stuck + World.Dt : 0f;
            // standing on the perimeter point we asked for IS arrival: do not make every delivery wait out the stuck timer
            bool atGoal = _u.hasMoveTarget && !_agent.pathPending && _agent.hasPath && _agent.remainingDistance <= _agent.stoppingDistance + 0.2f;
            _u.blocked = _stuck > 0.8f || (atGoal && _u.stopDistance > 2.5f);
        }

        public void SetSelected(bool on)
        {
            selected = on;
            if (_u.owner == World.Human) _ring.SetActive(on);
        }

        void Update()
        {
            if (_dead) { TickDead(); return; }
            if (!_u.Alive) { BeginDeath(); return; }

            bool hidden = _u.Hidden;
            foreach (var r in _rends) if (r != null && r.enabled == hidden) r.enabled = !hidden;
            _agent.enabled = !hidden;
            if (hidden) { transform.position = Ground.At(_u.pos); return; }
            if (!_agent.isOnNavMesh)
            {
                if (NavMesh.SamplePosition(Ground.At(_u.pos), out var hit, 8f, NavMesh.AllAreas)) _agent.Warp(hit.position);
                return;
            }

            if (_u.hasMoveTarget)
            {
                var centre = Ground.At(_u.moveTarget);
                if ((centre - _lastDest).sqrMagnitude > 0.09f)
                {
                    _lastDest = centre;
                    if (_u.stopDistance > 2.5f)
                    {
                        // A building, a node, or a ranged target. Do NOT path to its centre: that is inside
                        // the carved obstacle, the NavMesh snaps the destination to the near edge, the agent
                        // measures "remaining" to THAT point and stops -- while the sim still sees it metres
                        // short of the centre. Every citizen froze outside the longhouse that way. Walk to a
                        // reachable point on the perimeter, on the side we are coming from, and stop ON it.
                        var dir = transform.position - centre; dir.y = 0f;
                        if (dir.sqrMagnitude < 0.01f) dir = Vector3.forward;
                        var p = centre + dir.normalized * (_u.stopDistance * 0.85f);
                        if (NavMesh.SamplePosition(p, out var near, 5f, NavMesh.AllAreas)) p = near.position;
                        _agent.SetDestination(p); _agent.stoppingDistance = 0.2f;
                    }
                    else { _agent.SetDestination(centre); _agent.stoppingDistance = Mathf.Max(0.05f, _u.stopDistance * 0.9f); }
                }
                _agent.isStopped = false;
            }
            else { if (!_agent.isStopped) { _agent.isStopped = true; _agent.ResetPath(); } _lastDest = new Vector3(9999, 0, 9999); }

            // face the work / the enemy when standing still
            float speed = _agent.velocity.magnitude;
            if (speed < 0.25f)
            {
                Vector3? look = null;
                if (_u.state == UnitState.Gathering) { var n = _root.World.N(_u.nodeId); if (n != null) look = Ground.At(n.pos); }
                else if (_u.state == UnitState.Building) { var b = _root.World.B(_u.buildingId); if (b != null) look = Ground.At(b.pos); }
                else if (_u.state == UnitState.Attacking)
                {
                    var t = _root.World.U(_u.targetUnit); var tb = _root.World.B(_u.targetBuilding);
                    if (t != null) look = Ground.At(t.pos); else if (tb != null) look = Ground.At(tb.pos);
                }
                if (look.HasValue)
                {
                    var d = look.Value - transform.position; d.y = 0f;
                    if (d.sqrMagnitude > 0.01f)
                        transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(d), 540f * Time.deltaTime);
                }
            }

            // pose
            _anim.speed = speed;
            bool ranged = _u.def.range > 3f;
            if (speed > 0.3f) _anim.clip = _u.carry > 0.5f ? UnitAnim.Clip.Carry
                                         : _u.state == UnitState.Attacking && _u.def.cls != UnitClass.Worker ? UnitAnim.Clip.Charge   // closing on an enemy: run
                                         : UnitAnim.Clip.Walk;
            else if (_u.state == UnitState.Gathering)
                _anim.clip = _u.lastKind == NodeKind.Tree ? UnitAnim.Clip.Chop : _u.lastKind == NodeKind.Farm ? UnitAnim.Clip.Farm
                           : _u.lastKind == NodeKind.Berry ? UnitAnim.Clip.Forage : UnitAnim.Clip.Mine;
            else if (_u.state == UnitState.Building) _anim.clip = UnitAnim.Clip.Hammer;
            else if (_u.state == UnitState.Attacking) _anim.clip = ranged ? UnitAnim.Clip.Shoot : UnitAnim.Clip.Attack;
            else _anim.clip = UnitAnim.Clip.Idle;

            UpdateLoad();
            UpdateTool();
            SitOnTheGround();
            _hp.Set(_u.hp / _u.maxHp, selected || _u.hp < _u.maxHp - 0.5f);
        }

        public void Strike() { if (_anim != null) _anim.Strike(); }
        public void Hit() { if (_anim != null) _anim.Hit(); }
        public void Cheer(float seconds) { if (_anim != null) _anim.Cheer(seconds); }

        /// <summary>The thing being carried must be readable: a log, a berry basket, a stone, an ingot.</summary>
        /// <summary>The NavMesh is a voxelised approximation of the terrain and can sit 10-20 cm under it; a figure standing on
        /// the NavMesh stands IN the ground, and his boots disappear into the team disc ("blue feet"). Stand him on the terrain.</summary>
        void SitOnTheGround()
        {
            if (_agent == null || !_agent.enabled || _dead) return;
            float navY = transform.position.y - _agent.baseOffset;
            float want = Mathf.Clamp(Ground.Height(transform.position.x, transform.position.z) - navY, -0.5f, 0.5f);
            _agent.baseOffset = Mathf.Lerp(_agent.baseOffset, want, 1f - Mathf.Exp(-12f * Time.deltaTime));
        }

        void UpdateLoad()
        {
            bool want = _u.carry > 0.5f;
            if (want && _load == null)
            {
                _load = GameObject.CreatePrimitive(_u.carryRes == Res.Wood ? PrimitiveType.Cylinder : PrimitiveType.Cube);
                Destroy(_load.GetComponent<Collider>());
                _load.transform.SetParent(_loadSocket != null ? _loadSocket : transform, false);
                _load.layer = gameObject.layer;                                     // with him in the silhouette pass: no ghost over the log
                var mr = _load.GetComponent<MeshRenderer>();
                mr.sharedMaterial = _root.models.Get(_u.carryRes == Res.Wood ? "node_wood" : _u.carryRes == Res.Food ? "node_food"
                                  : _u.carryRes == Res.Stone ? "node_stone" : "node_iron")?.GetComponentInChildren<MeshRenderer>()?.sharedMaterials[0];
                if (_u.carryRes == Res.Wood) { _load.transform.localScale = new Vector3(0.16f, 0.42f, 0.16f); _load.transform.localRotation = Quaternion.Euler(0, 0, 90f); }
                else _load.transform.localScale = new Vector3(0.30f, 0.24f, 0.26f);
                _load.transform.localPosition = _loadSocket != null ? Vector3.zero : new Vector3(0f, 1.02f, 0.40f);
            }
            if (_load != null && _load.activeSelf != want) _load.SetActive(want);
            if (!want && _load != null && _u.carry <= 0f) { Destroy(_load); _load = null; }
        }

        void BeginDeath()
        {
            _dead = true; _deadT = 0f;
            if (_disc != null) _disc.SetActive(false);
            // a corpse leaves the Units layer: it sinks into the ground, and the ground would "occlude" it forever
            foreach (var t in GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 0;
            if (_agent != null) _agent.enabled = false;
            if (_ring != null) _ring.SetActive(false);
            _hp.Set(0, false);
            if (_load != null) Destroy(_load);
            _anim.Die(transform.eulerAngles.y);
            _root.Forget(this);
        }

        /// <summary>docs/09: the body holds 12 s, then sinks 0.3 m over 2 s and is gone.</summary>
        void TickDead()
        {
            _deadT += Time.deltaTime;
            if (_deadT > 12f) transform.position += Vector3.down * (0.35f / 2f) * Time.deltaTime;
            if (_deadT > 14f) Destroy(gameObject);
        }
    }
}
