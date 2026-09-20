using COA.Sim;
using UnityEngine;
using UnityEngine.AI;

namespace COA.Game
{
    /// <summary>One per sim building: the model, the rise-from-the-ground construction, the nav obstacle, the collapse.</summary>
    public sealed class BuildingView : MonoBehaviour
    {
        public int buildingId; public bool selected;
        GameRoot _root; Building _b; Transform _model; GameObject _ring; HealthBar _hp; NavMeshObstacle _obstacle;
        float _shownProgress = -1f; bool _wasComplete, _collapsing; float _collapseT; float _fullHeight = 4f; float _pop;

        public Building Building => _b;

        static readonly string[] HutModels = { "hut_a", "hut_b", "hut_c", "hut_d", "hut_e" };

        public static BuildingView Create(GameRoot root, Building b)
        {
            var go = new GameObject(b.def.name + "_" + b.id);
            var v = go.AddComponent<BuildingView>(); v._root = root; v._b = b; v.buildingId = b.id;
            go.transform.SetPositionAndRotation(Ground.At(b.pos), Quaternion.Euler(0f, b.rot, 0f));

            string model = b.type == BuildingType.Hut ? HutModels[b.variant % HutModels.Length] : b.def.model;
            var prefab = root.models.Get(model);
            GameObject m;
            if (prefab != null) m = Instantiate(prefab, go.transform);
            else { m = GameObject.CreatePrimitive(PrimitiveType.Cube); m.transform.SetParent(go.transform, false); m.transform.localScale = new Vector3(b.def.radius * 1.4f, 3f, b.def.radius * 1.4f); m.transform.localPosition = Vector3.up * 1.5f; }
            m.transform.localPosition = prefab != null ? Vector3.zero : m.transform.localPosition;
            v._model = m.transform;

            var bounds = new Bounds(go.transform.position, Vector3.zero); bool first = true;
            foreach (var r in m.GetComponentsInChildren<Renderer>()) { if (first) { bounds = r.bounds; first = false; } else bounds.Encapsulate(r.bounds); }
            v._fullHeight = Mathf.Max(1f, bounds.size.y);

            // click target + nav obstacle from the model's real footprint (a hall is long, not round)
            var local = go.transform.InverseTransformPoint(bounds.center);
            var size = Quaternion.Inverse(go.transform.rotation) * bounds.size;
            size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z));
            var box = go.AddComponent<BoxCollider>(); box.center = local; box.size = size; box.isTrigger = true;
            v._obstacle = go.AddComponent<NavMeshObstacle>();
            v._obstacle.shape = NavMeshObstacleShape.Box; v._obstacle.center = local;
            v._obstacle.size = new Vector3(size.x * 0.86f, size.y, size.z * 0.86f);
            v._obstacle.carving = true; v._obstacle.carveOnlyStationary = false;

            v._ring = MeshKit.Make("Ring", MeshKit.Ring, b.owner == World.Human ? root.models.ring : root.models.ringEnemy, go.transform);
            v._ring.transform.localPosition = new Vector3(0f, 0.10f, 0f);
            v._ring.transform.localScale = Vector3.one * (b.def.radius + 0.4f);
            v._ring.SetActive(false);
            v._hp = HealthBar.Create(go.transform, v._fullHeight + 1.0f, Mathf.Clamp(b.def.radius * 0.7f, 1.6f, 4.5f), root.models);
            v._wasComplete = b.complete;
            v.Apply(true);
            return v;
        }

        public void SetSelected(bool on) { selected = on; _ring.SetActive(on); }

        void Update()
        {
            if (_collapsing)
            {
                _collapseT += Time.deltaTime;
                float f = Mathf.Clamp01(_collapseT / 1.6f);
                _model.localPosition = new Vector3(0f, -_fullHeight * f * f, 0f);              // accelerates: it FALLS
                _model.localRotation = Quaternion.Euler(f * 5f, 0f, f * -7f);
                if (_collapseT > 2.2f) Destroy(gameObject);
                return;
            }
            if (_b.destroyed) { _collapsing = true; _obstacle.enabled = false; _ring.SetActive(false); _hp.Set(0, false); GetComponent<Collider>().enabled = false; return; }
            Apply(false);
            _hp.Set(_b.hp / _b.def.hp, selected || (_b.complete && _b.hp < _b.def.hp - 1f));
        }

        /// <summary>Construction: the building rises out of the ground, then lands with a small overshoot.</summary>
        void Apply(bool force)
        {
            if (_b.complete && !_wasComplete) { _wasComplete = true; _pop = 0.35f; }
            if (_pop > 0f)
            {
                _pop -= Time.deltaTime;
                float k = 1f + Mathf.Sin((1f - _pop / 0.35f) * Mathf.PI) * 0.06f;           // business speed: overshoot and settle
                _model.localScale = new Vector3(1f, k, 1f);
            }
            else if (_b.complete) _model.localScale = Vector3.one;

            float p = _b.complete ? 1f : Mathf.Clamp01(_b.progress);
            if (!force && Mathf.Abs(p - _shownProgress) < 0.002f) return;
            _shownProgress = p;
            _model.localPosition = new Vector3(0f, -_fullHeight * (1f - Mathf.Lerp(0.12f, 1f, p)), 0f);
        }
    }

    /// <summary>Berry, stone and iron nodes. (Trees are instanced; farms are buildings.)</summary>
    public sealed class NodeView : MonoBehaviour
    {
        public int nodeId; Node _n; Transform _model; float _shown = -1f; GameObject _ring;
        public Node Node => _n;

        public static NodeView Create(GameRoot root, Node n)
        {
            var go = new GameObject(n.kind + "_" + n.id);
            var v = go.AddComponent<NodeView>(); v._n = n; v.nodeId = n.id;
            go.transform.SetPositionAndRotation(Ground.At(n.pos), Quaternion.Euler(0f, (n.id * 73) % 360, 0f));
            var prefab = root.models.Get(n.kind == NodeKind.Berry ? "node_food" : n.kind == NodeKind.Stone ? "node_stone" : "node_iron");
            var m = prefab != null ? Instantiate(prefab, go.transform) : GameObject.CreatePrimitive(PrimitiveType.Sphere);
            m.transform.SetParent(go.transform, false);
            // the library's nodes are authored ~6 m across; a gatherable patch should read as ~4 m
            m.transform.localScale = Vector3.one * (n.kind == NodeKind.Berry ? 0.55f : 0.62f);
            v._model = m.transform;
            var col = go.AddComponent<SphereCollider>(); col.radius = 2.2f; col.center = Vector3.up * 0.8f; col.isTrigger = true;
            v._ring = MeshKit.Make("Ring", MeshKit.Ring, root.models.marker, go.transform);
            v._ring.transform.localPosition = new Vector3(0, 0.08f, 0); v._ring.transform.localScale = Vector3.one * 2.4f; v._ring.SetActive(false);
            return v;
        }

        public void SetSelected(bool on) { _ring.SetActive(on); }

        void Update()
        {
            // everything finite is VISIBLY finite (docs/03): the patch shrinks as it is worked
            float f = Mathf.Clamp01(_n.amount / _n.max);
            if (Mathf.Abs(f - _shown) > 0.01f)
            {
                _shown = f;
                float baseScale = _n.kind == NodeKind.Berry ? 0.55f : 0.62f;
                _model.localScale = Vector3.one * baseScale * Mathf.Lerp(0.35f, 1f, f);
            }
            if (_n.Depleted) { GameRoot.I.nodeViews.Remove(nodeId); Destroy(gameObject); }
        }
    }
}
