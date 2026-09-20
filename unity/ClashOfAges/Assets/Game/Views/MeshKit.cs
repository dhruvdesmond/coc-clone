using UnityEngine;

namespace COA.Game
{
    public static class MeshKit
    {
        static Mesh _ring, _quad, _disc;

        public static Mesh Ring
        {
            get
            {
                if (_ring != null) return _ring;
                const int seg = 40; const float inner = 0.86f;
                var v = new Vector3[seg * 2]; var t = new int[seg * 6];
                for (int i = 0; i < seg; i++)
                {
                    float a = i * Mathf.PI * 2f / seg; var d = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                    v[i * 2] = d * inner; v[i * 2 + 1] = d;
                    int n = (i + 1) % seg, k = i * 6;
                    t[k] = i * 2; t[k + 1] = i * 2 + 1; t[k + 2] = n * 2 + 1; t[k + 3] = i * 2; t[k + 4] = n * 2 + 1; t[k + 5] = n * 2;
                }
                _ring = new Mesh { name = "Ring", vertices = v, triangles = t }; _ring.RecalculateNormals(); _ring.RecalculateBounds();
                return _ring;
            }
        }

        public static Mesh Disc
        {
            get
            {
                if (_disc != null) return _disc;
                const int seg = 28; var v = new Vector3[seg + 1]; var uv = new Vector2[seg + 1]; var t = new int[seg * 3];
                v[0] = Vector3.zero; uv[0] = new Vector2(0.5f, 0.5f);
                for (int i = 0; i < seg; i++)
                {
                    float a = i * Mathf.PI * 2f / seg; v[i + 1] = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                    uv[i + 1] = new Vector2(0.5f + Mathf.Cos(a) * 0.5f, 0.5f + Mathf.Sin(a) * 0.5f);
                    t[i * 3] = 0; t[i * 3 + 1] = (i + 1) % seg + 1; t[i * 3 + 2] = i + 1;
                }
                _disc = new Mesh { name = "Disc", vertices = v, uv = uv, triangles = t }; _disc.RecalculateNormals(); _disc.RecalculateBounds();
                return _disc;
            }
        }

        /// <summary>Unit quad in XY, pivot at the LEFT edge centre -- so scaling X shrinks a health bar toward the left.</summary>
        public static Mesh Quad
        {
            get
            {
                if (_quad != null) return _quad;
                _quad = new Mesh { name = "BarQuad",
                    vertices = new[] { new Vector3(0, -0.5f, 0), new Vector3(1, -0.5f, 0), new Vector3(1, 0.5f, 0), new Vector3(0, 0.5f, 0) },
                    uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) },
                    triangles = new[] { 0, 2, 1, 0, 3, 2 } };
                _quad.RecalculateNormals(); _quad.RecalculateBounds();
                return _quad;
            }
        }

        public static GameObject Make(string name, Mesh mesh, Material mat, Transform parent)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
            return go;
        }
    }

    /// <summary>Two quads that face the camera. Shown when hurt or selected.</summary>
    public sealed class HealthBar : MonoBehaviour
    {
        Transform _fill; float _width;
        public static HealthBar Create(Transform parent, float height, float width, ModelLibrary lib)
        {
            var go = new GameObject("HealthBar"); go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(0f, height, 0f);
            var hb = go.AddComponent<HealthBar>(); hb._width = width;
            var back = MeshKit.Make("Back", MeshKit.Quad, lib.hpBack, go.transform);
            back.transform.localPosition = new Vector3(-width * 0.5f - 0.03f, 0f, 0.002f);
            back.transform.localScale = new Vector3(width + 0.06f, 0.16f, 1f);
            var fill = MeshKit.Make("Fill", MeshKit.Quad, lib.hpFill, go.transform);
            fill.transform.localPosition = new Vector3(-width * 0.5f, 0f, 0f);
            hb._fill = fill.transform;
            go.SetActive(false);
            return hb;
        }
        public void Set(float frac, bool visible)
        {
            if (gameObject.activeSelf != visible) gameObject.SetActive(visible);
            if (!visible) return;
            _fill.localScale = new Vector3(Mathf.Max(0.001f, _width * Mathf.Clamp01(frac)), 0.10f, 1f);
            var cam = Camera.main; if (cam != null) transform.rotation = cam.transform.rotation;
        }
    }
}
