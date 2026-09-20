using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// Drapes a 0.5 m grid over the terrain and shades it from the sim's territory grid. The mask is
    /// rebuilt only when Territory.version changes -- a handful of times per match -- and eased
    /// toward the new shape, so a border BLOOMS outward instead of snapping.
    /// </summary>
    public sealed class BorderRenderer : MonoBehaviour
    {
        public Material material;
        const int Up = 2;                                  // mask texels per sim cell
        Texture2D _mask; Color32[] _px; float[] _cur, _target; int _w, _h, _version = -1; float _bloom; bool _dirty;
        public Texture2D Mask => _mask;

        void Start()
        {
            var g = GameRoot.I; var t = g.World.territory;
            _w = t.w * Up; _h = t.h * Up;
            _mask = new Texture2D(_w, _h, TextureFormat.RGBA32, false, true) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            _px = new Color32[_w * _h]; _cur = new float[_w * _h * 2]; _target = new float[_w * _h * 2];
            material = new Material(material);             // per-scene instance: _Mask and _Bloom are runtime state
            material.SetTexture("_Mask", _mask);
            BuildMesh(t);
            g.OnSimEvent += e => { if (e.type == SimEventType.AgeAdvanced) _bloom = 1f; };
        }

        void BuildMesh(Territory t)
        {
            const float step = 0.5f;
            int nx = Mathf.RoundToInt(t.w / step) + 1, nz = Mathf.RoundToInt(t.h / step) + 1;
            var v = new Vector3[nx * nz]; var uv = new Vector2[nx * nz]; var tri = new int[(nx - 1) * (nz - 1) * 6];
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    float wx = t.originX + x * step, wz = t.originZ + z * step;
                    float y = Mathf.Max(Ground.Height(wx, wz), Ground.SeaLevel) + 0.16f;      // floats over water too
                    v[z * nx + x] = new Vector3(wx, y, wz); uv[z * nx + x] = new Vector2(x / (float)(nx - 1), z / (float)(nz - 1));
                }
            int k = 0;
            for (int z = 0; z < nz - 1; z++)
                for (int x = 0; x < nx - 1; x++)
                {
                    int i = z * nx + x;
                    tri[k++] = i; tri[k++] = i + nx; tri[k++] = i + 1; tri[k++] = i + 1; tri[k++] = i + nx; tri[k++] = i + nx + 1;
                }
            var mesh = new Mesh { name = "BorderDrape", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32, vertices = v, uv = uv, triangles = tri };
            mesh.RecalculateBounds();
            var go = MeshKit.Make("BorderDrape", mesh, material, transform);
            go.transform.position = Vector3.zero;
        }

        void Rebuild(Territory t)
        {
            // upsample the owner grid, then two box-blur passes: the 0.5 contour becomes a smooth curve
            var a = new float[_w * _h * 2];
            for (int z = 0; z < _h; z++)
                for (int x = 0; x < _w; x++)
                {
                    byte o = t.owner[(z / Up) * t.w + (x / Up)];
                    a[(z * _w + x) * 2] = o == 1 ? 1f : 0f; a[(z * _w + x) * 2 + 1] = o == 2 ? 1f : 0f;
                }
            for (int pass = 0; pass < 2; pass++) a = Blur(a, 3);
            _target = a;
        }

        float[] Blur(float[] src, int r)
        {
            var tmp = new float[src.Length]; var dst = new float[src.Length]; float inv = 1f / (2 * r + 1);
            for (int c = 0; c < 2; c++)
            {
                for (int z = 0; z < _h; z++)
                    for (int x = 0; x < _w; x++)
                    {
                        float s = 0; for (int d = -r; d <= r; d++) s += src[(z * _w + Mathf.Clamp(x + d, 0, _w - 1)) * 2 + c];
                        tmp[(z * _w + x) * 2 + c] = s * inv;
                    }
                for (int z = 0; z < _h; z++)
                    for (int x = 0; x < _w; x++)
                    {
                        float s = 0; for (int d = -r; d <= r; d++) s += tmp[(Mathf.Clamp(z + d, 0, _h - 1) * _w + x) * 2 + c];
                        dst[(z * _w + x) * 2 + c] = s * inv;
                    }
            }
            return dst;
        }

        void Update()
        {
            var t = GameRoot.I.World.territory;
            if (t.version != _version)
            {
                bool first = _version < 0;
                _version = t.version; Rebuild(t);
                // The FIRST border must appear, not ease in: easing from zero sends every texel of the nation through
                // the 0.5 "frontier" value at the same moment, and the whole map flashes as one giant border line.
                if (first) System.Array.Copy(_target, _cur, _cur.Length);
                _dirty = true;
            }

            // business speed: ease toward the new border over ~0.8 s
            float k = 1f - Mathf.Exp(-3.2f * Time.deltaTime); bool moving = false;
            for (int i = 0; i < _cur.Length; i++)
            {
                float d = _target[i] - _cur[i];
                if (d > 0.002f || d < -0.002f) { _cur[i] += d * k; moving = true; }
            }
            if (moving || _dirty)
            {
                _dirty = false;
                for (int i = 0; i < _px.Length; i++) _px[i] = new Color32((byte)(_cur[i * 2] * 255f), (byte)(_cur[i * 2 + 1] * 255f), 0, 255);
                _mask.SetPixels32(_px); _mask.Apply(false);
            }
            if (_bloom > 0f) { _bloom = Mathf.Max(0f, _bloom - Time.deltaTime * 0.45f); material.SetFloat("_Bloom", _bloom * _bloom); }
        }
    }
}
