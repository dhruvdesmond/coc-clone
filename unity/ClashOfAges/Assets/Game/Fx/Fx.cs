using System.Collections.Generic;
using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// Everything that happens because the sim said so: debris, arrows, blood, floating numbers,
    /// stumps, order markers. Violence does not ease (docs/09) -- bursts start at full speed.
    /// </summary>
    public sealed class Fx : MonoBehaviour
    {
        public static bool Blood = true;                      // Settings -> Blood. Cheap now, painful to retrofit.
        GameRoot _g; ModelLibrary _lib; Mesh _cube;
        struct Bit { public Transform t; public Vector3 v; public float life, max, size; public MeshRenderer r; }
        readonly List<Bit> _bits = new List<Bit>(); readonly Stack<Transform> _pool = new Stack<Transform>();
        struct Arrow { public Transform t; public Vector3 a, b; public float u, dur; }
        readonly List<Arrow> _arrows = new List<Arrow>();
        struct Float { public TextMesh tm; public float life; }
        readonly List<Float> _floats = new List<Float>();
        struct Decal { public Transform t; public MeshRenderer r; public float age; }
        readonly List<Decal> _decals = new List<Decal>();
        struct Marker { public Transform t; public float life; }
        readonly List<Marker> _markers = new List<Marker>();
        MaterialPropertyBlock _mpb;

        static readonly Color Wood = new Color(0.72f, 0.52f, 0.30f), Dust = new Color(0.62f, 0.56f, 0.46f), Rock = new Color(0.55f, 0.55f, 0.58f),
                              Leafy = new Color(0.35f, 0.55f, 0.25f), Red = new Color(0.55f, 0.03f, 0.03f), Spark = new Color(1f, 0.85f, 0.45f);

        void Start()
        {
            _g = GameRoot.I; _lib = _g.models; _mpb = new MaterialPropertyBlock();
            var tmp = GameObject.CreatePrimitive(PrimitiveType.Cube); _cube = tmp.GetComponent<MeshFilter>().sharedMesh; Destroy(tmp);
            _g.OnSimEvent += OnSim;
            PlayerInput.I.OnOrderIssued += (p, attack) => SpawnMarker(p, attack);
        }

        void OnSim(SimEvent e)
        {
            var w = _g.World;
            switch (e.type)
            {
                case SimEventType.WorkImpact:
                {
                    var p = Ground.At(e.pos) + Vector3.up * 0.9f;
                    if (e.b == (int)NodeKind.Tree) Burst(p, Wood, 7, 3.2f, 0.07f);
                    else if (e.b == (int)NodeKind.Stone || e.b == (int)NodeKind.Iron) Burst(p, Rock, 6, 3.0f, 0.08f);
                    else if (e.b == (int)NodeKind.Berry) Burst(p, Leafy, 4, 1.8f, 0.06f);
                    else if (e.b == -1) { var u = w.U(e.a); if (u != null) Burst(Ground.At(u.pos) + Vector3.up * 0.8f, Dust, 4, 2.0f, 0.07f); }
                    Sfx.I.Work(e.b, p);
                    break;
                }
                case SimEventType.Deposit:
                    FloatText(Ground.At(e.pos) + Vector3.up * 4.2f, "+" + Mathf.RoundToInt(e.amount) + " " + (Res)e.b, new Color(1f, 0.95f, 0.7f));
                    Sfx.I.Play(Sfx.Clip.Deposit, Ground.At(e.pos), 0.5f);
                    break;
                case SimEventType.TreeFelled:
                {
                    var p = Ground.At(e.pos);
                    Burst(p + Vector3.up * 1.2f, Leafy, 16, 4.5f, 0.12f); Burst(p + Vector3.up * 0.4f, Wood, 8, 3f, 0.09f);
                    var stump = GameObject.CreatePrimitive(PrimitiveType.Cylinder); Destroy(stump.GetComponent<Collider>());
                    stump.transform.SetParent(transform); stump.transform.position = p + Vector3.up * 0.16f;
                    stump.transform.localScale = new Vector3(0.42f, 0.18f, 0.42f); stump.GetComponent<MeshRenderer>().sharedMaterial = _lib.stump;
                    Sfx.I.Play(Sfx.Clip.TreeFall, p, 0.9f);
                    break;
                }
                case SimEventType.Attack:
                {
                    if (e.a > 0 && _g.unitViews.TryGetValue(e.a, out var av)) av.Strike();
                    Vector3 from = e.a > 0 ? Ground.At(w.U(e.a)?.pos ?? e.pos) + Vector3.up * 1.4f : Ground.At(e.pos) + Vector3.up * 5.2f;
                    Vector3 to = e.b > 0 ? Ground.At(w.U(e.b)?.pos ?? e.pos) + Vector3.up * 1.1f : Ground.At(w.B(-e.b)?.pos ?? e.pos) + Vector3.up * 1.5f;
                    if (e.amount > 0.5f) { SpawnArrow(from, to); Sfx.I.Play(Sfx.Clip.Arrow, from, 0.55f); }
                    else Sfx.I.Play(Sfx.Clip.Clang, from, 0.6f);
                    break;
                }
                case SimEventType.Hit:
                {
                    var u = w.U(e.a); if (u == null) break;
                    if (_g.unitViews.TryGetValue(e.a, out var hv)) hv.Hit();
                    var p = Ground.At(u.pos) + Vector3.up * 1.1f;
                    if (Blood) Burst(p, Red, 5, 2.4f, 0.05f); else Burst(p, Spark, 3, 2.0f, 0.04f);
                    break;
                }
                case SimEventType.UnitDied:
                {
                    var p = Ground.At(e.pos);
                    if (Blood) { Burst(p + Vector3.up * 1.0f, Red, 8, 2.8f, 0.06f); SpawnDecal(p); }
                    Sfx.I.Death(p);
                    break;
                }
                case SimEventType.BuildingPlaced: Burst(Ground.At(e.pos) + Vector3.up * 0.3f, Dust, 14, 3.5f, 0.14f); Sfx.I.Play(Sfx.Clip.Place, Ground.At(e.pos), 0.7f); break;
                case SimEventType.BuildingComplete: Burst(Ground.At(e.pos) + Vector3.up * 0.5f, Dust, 22, 5f, 0.16f); if (e.b == World.Human) Sfx.I.Play(Sfx.Clip.Complete, Ground.At(e.pos), 0.8f); break;
                case SimEventType.BuildingDestroyed: Burst(Ground.At(e.pos) + Vector3.up * 1.5f, Dust, 40, 7f, 0.22f); Burst(Ground.At(e.pos) + Vector3.up, Wood, 20, 6f, 0.14f); Sfx.I.Play(Sfx.Clip.Collapse, Ground.At(e.pos), 1f); break;
                case SimEventType.UnitSpawned: if (e.b == World.Human && w.time > 1f) Sfx.I.Play(Sfx.Clip.Spawn, Ground.At(e.pos), 0.5f); break;
                case SimEventType.TechComplete: if (e.b == World.Human) Sfx.I.Play2D(Sfx.Clip.Complete, 0.8f); break;
                case SimEventType.RaidIncoming: Sfx.I.Play2D(Sfx.Clip.Horn, 0.95f); break;
                case SimEventType.RaidDefeated: Sfx.I.Play2D(Sfx.Clip.Complete, 0.7f); break;
                case SimEventType.AgeAdvanced:
                    Sfx.I.Play2D(Sfx.Clip.Fanfare, 1f);
                    foreach (var u in w.units) if (u.owner == e.b && _g.unitViews.TryGetValue(u.id, out var cv)) cv.Cheer(4.5f);   // whoever is idle, cheers
                    break;
                case SimEventType.Victory: Sfx.I.Play2D(Sfx.Clip.Fanfare, 1f); break;
                case SimEventType.Defeat: Sfx.I.Play2D(Sfx.Clip.Horn, 1f); break;
            }
        }

        // ------------------------------------------------------------------ debris
        public void Burst(Vector3 pos, Color c, int count, float speed, float size)
        {
            for (int i = 0; i < count; i++)
            {
                Transform t;
                if (_pool.Count > 0) { t = _pool.Pop(); t.gameObject.SetActive(true); }
                else { if (_bits.Count > 420) return; t = MeshKit.Make("bit", _cube, _lib.particle, transform).transform; }
                var r = t.GetComponent<MeshRenderer>();
                var col = c * Random.Range(0.75f, 1.2f); col.a = 1f; _mpb.SetColor("_BaseColor", col); r.SetPropertyBlock(_mpb);
                t.position = pos; t.rotation = Random.rotation; float s = size * Random.Range(0.6f, 1.4f); t.localScale = Vector3.one * s;
                var dir = Random.onUnitSphere; dir.y = Mathf.Abs(dir.y) * 1.3f + 0.3f;
                _bits.Add(new Bit { t = t, r = r, v = dir.normalized * speed * Random.Range(0.5f, 1f), life = 0f, max = Random.Range(0.45f, 0.9f), size = s });
            }
        }

        void SpawnArrow(Vector3 a, Vector3 b)
        {
            var t = MeshKit.Make("arrow", _cube, _lib.arrow, transform).transform; t.localScale = new Vector3(0.035f, 0.035f, 0.85f);
            _arrows.Add(new Arrow { t = t, a = a, b = b, u = 0f, dur = Mathf.Max(0.12f, Vector3.Distance(a, b) / 30f) });
        }

        void FloatText(Vector3 pos, string text, Color c)
        {
            var go = new GameObject("float"); go.transform.SetParent(transform); go.transform.position = pos;
            var tm = go.AddComponent<TextMesh>(); tm.text = text; tm.fontSize = 48; tm.characterSize = 0.075f; tm.anchor = TextAnchor.MiddleCenter; tm.color = c;
            tm.font = COA.UI.UiKit.Font; go.GetComponent<MeshRenderer>().sharedMaterial = tm.font.material;
            _floats.Add(new Float { tm = tm, life = 0f });
        }

        /// <summary>docs/09: grows over 0.6 s, holds, fades to 35% after 12 s and stays. 250 budget, oldest evicted.</summary>
        void SpawnDecal(Vector3 p)
        {
            if (_decals.Count >= 250) { Destroy(_decals[0].t.gameObject); _decals.RemoveAt(0); }
            var go = MeshKit.Make("blood", MeshKit.Disc, _lib.blood, transform);
            Ground.Sample(p.x, p.z, out float y, out var n);
            go.transform.position = new Vector3(p.x, y + 0.05f, p.z); go.transform.rotation = Quaternion.FromToRotation(Vector3.up, n) * Quaternion.Euler(0, Random.value * 360f, 0);
            go.transform.localScale = Vector3.zero;
            _decals.Add(new Decal { t = go.transform, r = go.GetComponent<MeshRenderer>(), age = 0f });
        }

        void SpawnMarker(Vector3 p, bool attack)
        {
            var go = MeshKit.Make("marker", MeshKit.Ring, attack ? _lib.ringEnemy : _lib.marker, transform);
            go.transform.position = Ground.At(p.x, p.z) + Vector3.up * 0.12f;
            _markers.Add(new Marker { t = go.transform, life = 0f });
            Sfx.I.Play2D(attack ? Sfx.Clip.OrderAttack : Sfx.Clip.Order, 0.35f);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            for (int i = _bits.Count - 1; i >= 0; i--)
            {
                var b = _bits[i]; b.life += dt; b.v += Vector3.down * 11f * dt; b.t.position += b.v * dt;
                b.t.localScale = Vector3.one * b.size * Mathf.Clamp01(1f - b.life / b.max + 0.15f);
                if (b.life >= b.max) { b.t.gameObject.SetActive(false); _pool.Push(b.t); _bits.RemoveAt(i); } else _bits[i] = b;
            }
            for (int i = _arrows.Count - 1; i >= 0; i--)
            {
                var a = _arrows[i]; a.u += dt / a.dur;
                if (a.u >= 1f) { Destroy(a.t.gameObject); _arrows.RemoveAt(i); continue; }
                Vector3 P(float u) => Vector3.Lerp(a.a, a.b, u) + Vector3.up * Mathf.Sin(u * Mathf.PI) * Vector3.Distance(a.a, a.b) * 0.12f;
                var p = P(a.u); a.t.position = p; var d = P(Mathf.Min(1f, a.u + 0.03f)) - p; if (d.sqrMagnitude > 1e-6f) a.t.rotation = Quaternion.LookRotation(d);
                _arrows[i] = a;
            }
            var cam = Camera.main;
            for (int i = _floats.Count - 1; i >= 0; i--)
            {
                var f = _floats[i]; f.life += dt;
                if (f.life > 1.3f) { Destroy(f.tm.gameObject); _floats.RemoveAt(i); continue; }
                f.tm.transform.position += Vector3.up * 1.1f * dt; if (cam != null) f.tm.transform.rotation = cam.transform.rotation;
                var c = f.tm.color; c.a = Mathf.Clamp01(1.6f - f.life * 1.3f); f.tm.color = c; _floats[i] = f;
            }
            for (int i = 0; i < _decals.Count; i++)
            {
                var d = _decals[i]; d.age += dt;
                d.t.localScale = Vector3.one * Mathf.Lerp(0f, 0.85f, Mathf.Clamp01((d.age - 0.4f) / 0.6f));
                if (d.age > 12f && d.age < 14.2f) { _mpb.SetColor("_BaseColor", new Color(0.34f, 0.02f, 0.02f, Mathf.Lerp(0.85f, 0.30f, (d.age - 12f) / 2f))); d.r.SetPropertyBlock(_mpb); }
                _decals[i] = d;
            }
            for (int i = _markers.Count - 1; i >= 0; i--)
            {
                var m = _markers[i]; m.life += Time.unscaledDeltaTime;
                if (m.life > 0.55f) { Destroy(m.t.gameObject); _markers.RemoveAt(i); continue; }
                m.t.localScale = Vector3.one * Mathf.Lerp(1.5f, 0.35f, m.life / 0.55f); _markers[i] = m;
            }
        }
    }
}
