using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// The age advance, made visible. DL16: the six era moods are driven by the REALTIME sun, fog and
    /// ambient -- not baked lighting scenarios, which an in-place building swap would invalidate.
    /// The demo has no Age II models, so light is the whole of the change, and it is stated as such.
    /// </summary>
    public sealed class AgeDirector : MonoBehaviour
    {
        struct Mood { public Color sun; public float intensity, elevation, azimuth; public Color fog, sky, equator; }
        static readonly Mood Settlement = new Mood { sun = new Color(1.00f, 0.945f, 0.85f), intensity = 1.45f, elevation = 34f, azimuth = 40f,
            fog = new Color(0.62f, 0.70f, 0.78f), sky = new Color(0.44f, 0.46f, 0.50f), equator = new Color(0.36f, 0.36f, 0.33f) };
        static readonly Mood Feudal = new Mood { sun = new Color(1.00f, 0.985f, 0.95f), intensity = 1.62f, elevation = 47f, azimuth = 62f,
            fog = new Color(0.70f, 0.76f, 0.80f), sky = new Color(0.48f, 0.50f, 0.53f), equator = new Color(0.39f, 0.39f, 0.37f) };

        Light _sun; float _t = 1f; Mood _from, _to;

        void Start()
        {
            foreach (var l in FindObjectsByType<Light>(FindObjectsSortMode.None)) if (l.type == LightType.Directional) _sun = l;
            _from = _to = Settlement; Apply(Settlement);
            GameRoot.I.OnSimEvent += e => { if (e.type == SimEventType.AgeAdvanced && e.b == World.Human) { _from = Settlement; _to = Feudal; _t = 0f; Sfx.I.SetAge(2); } };
        }

        void Update()
        {
            if (_t >= 1f) return;
            _t = Mathf.Min(1f, _t + Time.deltaTime / 5f);                 // world speed: five seconds, linear
            Apply(Lerp(_from, _to, _t));
        }

        static Mood Lerp(Mood a, Mood b, float t) => new Mood { sun = Color.Lerp(a.sun, b.sun, t), intensity = Mathf.Lerp(a.intensity, b.intensity, t),
            elevation = Mathf.Lerp(a.elevation, b.elevation, t), azimuth = Mathf.Lerp(a.azimuth, b.azimuth, t),
            fog = Color.Lerp(a.fog, b.fog, t), sky = Color.Lerp(a.sky, b.sky, t), equator = Color.Lerp(a.equator, b.equator, t) };

        void Apply(Mood m)
        {
            if (_sun != null) { _sun.color = m.sun; _sun.intensity = m.intensity; _sun.transform.rotation = Quaternion.Euler(m.elevation, m.azimuth, 0f); }
            RenderSettings.fogColor = m.fog; RenderSettings.ambientSkyColor = m.sky; RenderSettings.ambientEquatorColor = m.equator;
            var cam = Camera.main; if (cam != null) cam.backgroundColor = m.fog;
        }
    }
}
