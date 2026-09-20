using COA.Game;
using COA.Sim;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace COA.UI
{
    /// <summary>North-up minimap: a one-off top-down render of the land, then borders, blips and the view frustum at 5 Hz.</summary>
    public sealed class Minimap : MonoBehaviour
    {
        const int W = 260, H = 210;
        RawImage _img; Texture2D _tex, _base; Color32[] _px, _basePx; float _next; bool _baseReady; int _frames;
        float _mapW, _mapH; RectTransform _rt; float _pingUntil; Vector2 _ping;

        public void Init(Transform canvas)
        {
            var frame = UiKit.Box("MinimapFrame", canvas, new Vector2(0, 0), new Vector2(0, 0), new Vector2(0, 0), new Vector2(12, 12), new Vector2(W + 10, H + 10), UiKit.Panel);
            _rt = UiKit.Rect("Minimap", frame.transform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(W, H));
            _img = _rt.gameObject.AddComponent<RawImage>();
            _tex = new Texture2D(W, H, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
            _px = new Color32[W * H]; _img.texture = _tex;
            var g = GameRoot.I; _mapW = g.mapSize.x; _mapH = g.mapSize.y;
            _rt.gameObject.AddComponent<MinimapClick>().map = this;
            g.OnSimEvent += e => { if (e.type == SimEventType.RaidIncoming) { _ping = new Vector2(e.pos.x, e.pos.z); _pingUntil = Time.unscaledTime + 8f; } };
        }

        /// <summary>Render the land once, from straight above, into the base layer.</summary>
        void BakeBase()
        {
            var go = new GameObject("MinimapBakeCam"); var cam = go.AddComponent<Camera>();
            cam.orthographic = true; cam.orthographicSize = _mapH * 0.5f; cam.aspect = _mapW / _mapH;
            cam.transform.SetPositionAndRotation(new Vector3(0, 120f, 0), Quaternion.Euler(90f, 0f, 0f));
            cam.nearClipPlane = 1f; cam.farClipPlane = 300f; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.10f, 0.20f, 0.26f);
            var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            cam.targetTexture = rt;
            GameRoot.I.instancedWorld.Render(cam);
            cam.Render();                                           // play mode, normal loop: fine here
            RenderTexture.active = rt;
            _base = new Texture2D(W, H, TextureFormat.RGBA32, false); _base.ReadPixels(new Rect(0, 0, W, H), 0, 0); _base.Apply();
            RenderTexture.active = null; cam.targetTexture = null; rt.Release(); Destroy(go);
            _basePx = _base.GetPixels32();
            for (int i = 0; i < _basePx.Length; i++)                // lift it: a minimap is read at a glance
            { var c = _basePx[i]; _basePx[i] = new Color32((byte)Mathf.Min(255, c.r * 1.35f + 12), (byte)Mathf.Min(255, c.g * 1.35f + 12), (byte)Mathf.Min(255, c.b * 1.35f + 12), 255); }
            _baseReady = true;
        }

        public Vector3 ToWorld(Vector2 local01) => new Vector3((local01.x - 0.5f) * _mapW, 0f, (local01.y - 0.5f) * _mapH);
        int Px(float wx) => Mathf.Clamp(Mathf.RoundToInt((wx / _mapW + 0.5f) * (W - 1)), 0, W - 1);
        int Py(float wz) => Mathf.Clamp(Mathf.RoundToInt((wz / _mapH + 0.5f) * (H - 1)), 0, H - 1);

        void Dot(float wx, float wz, int r, Color32 c)
        {
            int cx = Px(wx), cy = Py(wz);
            for (int y = -r; y <= r; y++) for (int x = -r; x <= r; x++)
            { int px = cx + x, py = cy + y; if (px >= 0 && py >= 0 && px < W && py < H) _px[py * W + px] = c; }
        }

        void Line(Vector3 a, Vector3 b, Color32 c)
        {
            int x0 = Px(a.x), y0 = Py(a.z), x1 = Px(b.x), y1 = Py(b.z); int n = Mathf.Max(Mathf.Abs(x1 - x0), Mathf.Abs(y1 - y0), 1);
            for (int i = 0; i <= n; i++) { int x = x0 + (x1 - x0) * i / n, y = y0 + (y1 - y0) * i / n; if (x >= 0 && y >= 0 && x < W && y < H) _px[y * W + x] = c; }
        }

        void Update()
        {
            if (!_baseReady) { if (++_frames > 3) BakeBase(); return; }
            if (Time.unscaledTime < _next) return; _next = Time.unscaledTime + 0.2f;
            var w = GameRoot.I.World; var t = w.territory;

            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++)
                {
                    int cx = Mathf.Min(t.w - 1, x * t.w / W), cz = Mathf.Min(t.h - 1, y * t.h / H);
                    byte o = t.owner[cz * t.w + cx]; var c = _basePx[y * W + x];
                    if (o != 0)
                    {
                        bool edge = (cx > 0 && t.owner[cz * t.w + cx - 1] != o) || (cx < t.w - 1 && t.owner[cz * t.w + cx + 1] != o)
                                 || (cz > 0 && t.owner[(cz - 1) * t.w + cx] != o) || (cz < t.h - 1 && t.owner[(cz + 1) * t.w + cx] != o);
                        var tint = o == 1 ? new Color32(70, 160, 255, 255) : new Color32(255, 80, 60, 255);
                        float k = edge ? 0.95f : 0.26f;
                        c = new Color32((byte)Mathf.Lerp(c.r, tint.r, k), (byte)Mathf.Lerp(c.g, tint.g, k), (byte)Mathf.Lerp(c.b, tint.b, k), 255);
                    }
                    _px[y * W + x] = c;
                }

            foreach (var b in w.buildings) if (!b.destroyed) Dot(b.pos.x, b.pos.z, b.type == BuildingType.Hall ? 3 : 2, b.owner == World.Human ? new Color32(150, 215, 255, 255) : new Color32(255, 120, 100, 255));
            foreach (var u in w.units) if (u.Alive && !u.Hidden) Dot(u.pos.x, u.pos.z, 1, u.owner == World.Human ? new Color32(255, 255, 255, 255) : new Color32(255, 40, 30, 255));
            if (Time.unscaledTime < _pingUntil && (int)(Time.unscaledTime * 4f) % 2 == 0) Dot(_ping.x, _ping.y, 5, new Color32(255, 230, 60, 255));

            var cam = Camera.main;                                    // the view frustum, as a trapezoid on the ground
            if (cam != null)
            {
                var corners = new Vector3[4]; var vp = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
                for (int i = 0; i < 4; i++)
                {
                    var ray = cam.ViewportPointToRay(vp[i]); float d = ray.direction.y < -0.01f ? -ray.origin.y / ray.direction.y : 400f;
                    corners[i] = ray.origin + ray.direction * Mathf.Min(d, 400f);
                }
                for (int i = 0; i < 4; i++) Line(corners[i], corners[(i + 1) % 4], new Color32(255, 255, 255, 255));
            }
            _tex.SetPixels32(_px); _tex.Apply(false);
        }

        public void Jump(Vector2 screen)
        {
            if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(_rt, screen, null, out var lp)) return;
            var uv = new Vector2(lp.x / _rt.rect.width + 0.5f, lp.y / _rt.rect.height + 0.5f);
            Camera.main.GetComponent<RTSCamera>().Frame(ToWorld(uv));
        }
    }

    public sealed class MinimapClick : MonoBehaviour, IPointerDownHandler, IDragHandler
    {
        public Minimap map;
        public void OnPointerDown(PointerEventData e) { if (e.button == PointerEventData.InputButton.Left) map.Jump(e.position); }
        public void OnDrag(PointerEventData e) { if (e.button == PointerEventData.InputButton.Left) map.Jump(e.position); }
    }
}
