using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace COA.Game
{
    /// <summary>
    /// Draws the map's ~19,700 instanced objects -- ground cover, trees, rocks, logs -- with
    /// Graphics.RenderMeshInstanced. No GameObjects: on the last port 17,834 of them were
    /// spawned for the same content, and cover then drew at every distance with no thinning.
    ///
    /// Instances are sorted by ground cell and cut into chunks of at most 1023 (the API limit),
    /// so each chunk is spatially tight and can be frustum-culled as a unit. Cover chunks are
    /// shuffled internally, which makes "draw the first k" a uniform thinning by distance.
    /// Trees are removable per entity (chopped), which is why entity ids ride along.
    /// </summary>
    [ExecuteAlways]
    public sealed class InstancedWorld : MonoBehaviour
    {
        public TextAsset data;
        public GameObject meshesPrefab;          // Assets/World/world_meshes.fbx
        public float cellSize = 14f;
        [Tooltip("Cover is fully dense inside this camera distance...")]
        public float coverFullDistance = 55f;
        [Tooltip("...and thinned to coverMinDensity by this distance.")]
        public float coverFarDistance = 150f;
        [Range(0.05f, 1f)] public float coverMinDensity = 0.22f;

        sealed class Chunk
        {
            public Mesh mesh; public RenderParams[] rp; public Matrix4x4[] matrices; public int[] entity;
            public int count; public Bounds bounds; public bool cover;
        }

        readonly List<Chunk> _chunks = new List<Chunk>();
        readonly Plane[] _planes = new Plane[6];
        WorldData _world;

        public WorldData World { get { EnsureBuilt(); return _world; } }
        public int ChunkCount => _chunks.Count;
        public int LastDrawnInstances { get; private set; }
        public int LastDrawCalls { get; private set; }

        void OnEnable() { _world = null; _chunks.Clear(); }

        void EnsureBuilt()
        {
            if (_world != null || data == null || meshesPrefab == null) return;
            _world = WorldData.Parse(data.bytes);

            // Per unique mesh: the Mesh, its materials, and the imported child's own transform
            // (Unity's FBX importer leaves a -90 X rotation on the child; it must be applied
            // under the instance matrix or every tree lies on its side).
            var root = meshesPrefab.transform;
            var meshes = new Mesh[_world.meshCount];
            var mats = new Material[_world.meshCount][];
            var childL2W = new Matrix4x4[_world.meshCount];
            for (int i = 0; i < _world.meshCount; i++)
            {
                var child = root.Find("m_" + i.ToString("000"));
                if (child == null) { Debug.LogError("[world] missing mesh child m_" + i.ToString("000")); continue; }
                meshes[i] = child.GetComponent<MeshFilter>().sharedMesh;
                mats[i] = child.GetComponent<MeshRenderer>().sharedMaterials;
                childL2W[i] = root.worldToLocalMatrix * child.localToWorldMatrix;
            }

            // bucket: (mesh, cover?) -> instances sorted by cell
            var buckets = new Dictionary<int, List<int>>();
            for (int i = 0; i < _world.instances.Length; i++)
            {
                int key = _world.instances[i].mesh;
                if (!buckets.TryGetValue(key, out var list)) buckets[key] = list = new List<int>();
                list.Add(i);
            }

            var rng = new System.Random(12);
            foreach (var kv in buckets)
            {
                int mi = kv.Key;
                if (meshes[mi] == null) continue;
                var list = kv.Value;
                list.Sort((a, b) => CellKey(_world.instances[a].matrix).CompareTo(CellKey(_world.instances[b].matrix)));

                for (int start = 0; start < list.Count; start += 1023)
                {
                    int n = Mathf.Min(1023, list.Count - start);
                    bool cover = _world.instances[list[start]].layer == WorldData.LayerCover;
                    var c = new Chunk { mesh = meshes[mi], matrices = new Matrix4x4[n], entity = new int[n],
                                        count = n, cover = cover };
                    var order = new int[n];
                    for (int k = 0; k < n; k++) order[k] = list[start + k];
                    if (cover)                                      // Fisher-Yates: uniform thinning
                        for (int k = n - 1; k > 0; k--) { int j = rng.Next(k + 1); (order[k], order[j]) = (order[j], order[k]); }

                    var mb = meshes[mi].bounds;
                    for (int k = 0; k < n; k++)
                    {
                        var inst = _world.instances[order[k]];
                        var m = inst.matrix * childL2W[mi];
                        c.matrices[k] = m; c.entity[k] = inst.entity;
                        var wb = TransformBounds(m, mb);
                        if (k == 0) c.bounds = wb; else c.bounds.Encapsulate(wb);
                    }

                    for (int s = 0; s < mats[mi].Length; s++)
                        if (mats[mi][s] == null && start == 0)
                            Debug.LogError("[world] mesh m_" + mi.ToString("000") + " slot " + s + " has NO material");
                    c.rp = new RenderParams[mats[mi].Length];
                    for (int s = 0; s < c.rp.Length; s++)
                        c.rp[s] = new RenderParams(mats[mi][s])
                        {
                            shadowCastingMode = cover ? ShadowCastingMode.Off : ShadowCastingMode.On,
                            receiveShadows = true,
                            worldBounds = c.bounds,
                            layer = gameObject.layer,
                        };
                    _chunks.Add(c);
                }
            }
            Debug.Log("[world] " + _world.instances.Length + " instances in " + _chunks.Count + " chunks, "
                      + _world.trees.Length + " trees");
        }

        long CellKey(Matrix4x4 m)
        {
            long cx = Mathf.FloorToInt(m.m03 / cellSize) + 4096, cz = Mathf.FloorToInt(m.m23 / cellSize) + 4096;
            return cz * 8192 + cx;
        }

        static Bounds TransformBounds(Matrix4x4 m, Bounds b)
        {
            var c = m.MultiplyPoint3x4(b.center);
            var e = b.extents;
            var ax = m.MultiplyVector(new Vector3(e.x, 0, 0)); var ay = m.MultiplyVector(new Vector3(0, e.y, 0));
            var az = m.MultiplyVector(new Vector3(0, 0, e.z));
            return new Bounds(c, 2f * new Vector3(Mathf.Abs(ax.x) + Mathf.Abs(ay.x) + Mathf.Abs(az.x),
                                                  Mathf.Abs(ax.y) + Mathf.Abs(ay.y) + Mathf.Abs(az.y),
                                                  Mathf.Abs(ax.z) + Mathf.Abs(ay.z) + Mathf.Abs(az.z)));
        }

        /// <summary>Remove every part of one tree. Swap-remove keeps the arrays dense.</summary>
        public void RemoveTree(int entity)
        {
            EnsureBuilt();
            foreach (var c in _chunks)
            {
                if (c.cover) continue;
                for (int k = c.count - 1; k >= 0; k--)
                    if (c.entity[k] == entity)
                    {
                        c.count--;
                        c.matrices[k] = c.matrices[c.count];
                        c.entity[k] = c.entity[c.count];
                    }
            }
        }

        void Update() { Render(Camera.main); }

        /// <summary>Queue this frame's draws. Public so an editor capture can call it just before rendering.</summary>
        public void Render(Camera cam)
        {
            EnsureBuilt();
            if (_world == null) return;
            bool cull = cam != null && Application.isPlaying;
            if (cull) GeometryUtility.CalculateFrustumPlanes(cam, _planes);
            Vector3 eye = cam != null ? cam.transform.position : Vector3.zero;

            int drawn = 0, calls = 0;
            foreach (var c in _chunks)
            {
                if (c.count == 0) continue;
                if (cull && !GeometryUtility.TestPlanesAABB(_planes, c.bounds)) continue;
                int n = c.count;
                if (c.cover && cam != null)
                {
                    float d = Mathf.Sqrt(c.bounds.SqrDistance(eye));
                    float t = Mathf.InverseLerp(coverFullDistance, coverFarDistance, d);
                    n = Mathf.Max(1, Mathf.RoundToInt(n * Mathf.Lerp(1f, coverMinDensity, t)));
                }
                for (int s = 0; s < c.rp.Length && s < c.mesh.subMeshCount; s++)
                {
                    if (c.rp[s].material == null) continue;      // reported once at build time
                    Graphics.RenderMeshInstanced(c.rp[s], c.mesh, s, c.matrices, n);
                    calls++;
                }
                drawn += n;
            }
            LastDrawnInstances = drawn; LastDrawCalls = calls;
        }
    }
}
