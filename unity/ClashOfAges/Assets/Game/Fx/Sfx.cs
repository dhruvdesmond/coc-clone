using System;
using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// Every sound in the demo is SYNTHESISED at startup -- there are no audio assets in the repo.
    /// It is honest placeholder audio, but it is tuned: work sounds land on the animation's impact
    /// frame, deaths obey the voice limit and minimum gap from docs/09, and the horn is two notes
    /// a fifth apart because that reads as "danger" without a sample library.
    /// </summary>
    public sealed class Sfx : MonoBehaviour
    {
        public enum Clip { Chop, Hammer, Pick, Rustle, Deposit, Order, OrderAttack, Select, Place, Complete, Spawn, Clang, Arrow, Death, Collapse, TreeFall, Horn, Fanfare, Error, Count }
        public static Sfx I { get; private set; }
        const int Rate = 44100;
        AudioClip[] _clips; AudioSource[] _pool; int _next; AudioSource _music, _wind;
        float _lastDeath; int _deathVoices; float _deathWindow;
        readonly System.Random _rng = new System.Random(5);

        void Awake()
        {
            I = this;
            _clips = new AudioClip[(int)Clip.Count];
            _clips[(int)Clip.Chop]     = Make("chop", 0.16f, t => (Noise() * Env(t, 0.002f, 0.05f) * 0.8f + Sin(95f, t) * Env(t, 0.001f, 0.09f) * 0.9f));
            _clips[(int)Clip.Hammer]   = Make("hammer", 0.10f, t => (Sin(Mathf.Lerp(950f, 420f, t / 0.05f), t) * Env(t, 0.001f, 0.035f) * 0.7f + Noise() * Env(t, 0.001f, 0.02f) * 0.4f));
            _clips[(int)Clip.Pick]     = Make("pick", 0.20f, t => (Sin(1850f, t) * 0.4f + Sin(2740f, t) * 0.25f) * Env(t, 0.001f, 0.09f) + Noise() * Env(t, 0.001f, 0.015f) * 0.5f);
            _clips[(int)Clip.Rustle]   = Make("rustle", 0.18f, t => Noise() * Env(t, 0.03f, 0.10f) * 0.35f);
            _clips[(int)Clip.Deposit]  = Make("deposit", 0.22f, t => (Sin(660f, t) * Env(t, 0.004f, 0.07f) + Sin(990f, t - 0.07f) * Env(t - 0.07f, 0.004f, 0.10f)) * 0.5f);
            _clips[(int)Clip.Order]    = Make("order", 0.09f, t => Sin(520f, t) * Env(t, 0.002f, 0.05f) * 0.6f);
            _clips[(int)Clip.OrderAttack] = Make("orderAttack", 0.12f, t => Saw(330f, t) * Env(t, 0.002f, 0.07f) * 0.45f);
            _clips[(int)Clip.Select]   = Make("select", 0.05f, t => Sin(880f, t) * Env(t, 0.001f, 0.03f) * 0.4f);
            _clips[(int)Clip.Place]    = Make("place", 0.35f, t => Noise() * Env(t, 0.004f, 0.16f) * 0.6f + Sin(70f, t) * Env(t, 0.002f, 0.2f) * 0.8f);
            _clips[(int)Clip.Complete] = Make("complete", 0.9f, t => (Note(523.25f, t, 0f) + Note(659.25f, t, 0.10f) + Note(783.99f, t, 0.20f) + Note(1046.5f, t, 0.30f)) * 0.30f);
            _clips[(int)Clip.Spawn]    = Make("spawn", 0.3f, t => (Note(392f, t, 0f) + Note(523.25f, t, 0.09f)) * 0.35f);
            _clips[(int)Clip.Clang]    = Make("clang", 0.28f, t => (Sin(2130f, t) * 0.3f + Sin(3370f, t) * 0.22f + Sin(4890f, t) * 0.15f) * Env(t, 0.001f, 0.11f) + Noise() * Env(t, 0.001f, 0.02f) * 0.6f);
            _clips[(int)Clip.Arrow]    = Make("arrow", 0.25f, t => Noise() * Env(t, 0.05f, 0.09f) * 0.4f * (0.4f + 0.6f * Mathf.Sin(t * 60f)));
            _clips[(int)Clip.Death]    = Make("death", 0.42f, t => (Saw(Mathf.Lerp(190f, 105f, t / 0.4f), t) * 0.5f + Noise() * 0.25f) * Env(t, 0.02f, 0.18f) * Formant(t));
            _clips[(int)Clip.Collapse] = Make("collapse", 1.6f, t => Noise() * Env(t, 0.05f, 0.7f) * 0.7f * (0.5f + 0.5f * Mathf.Sin(t * 37f)) + Sin(48f, t) * Env(t, 0.02f, 0.9f));
            _clips[(int)Clip.TreeFall] = Make("treefall", 0.9f, t => Noise() * (Env(t, 0.002f, 0.04f) + Env(t - 0.12f, 0.002f, 0.05f) * 0.8f + Env(t - 0.45f, 0.01f, 0.2f) * 0.9f) * 0.6f + Sin(60f, t - 0.45f) * Env(t - 0.45f, 0.005f, 0.25f));
            _clips[(int)Clip.Horn]     = Make("horn", 2.6f, t => (Brass(146.83f, t) * Swell(t, 0f, 1.1f) + Brass(220f, t) * Swell(t, 1.0f, 1.5f)) * 0.5f);
            _clips[(int)Clip.Fanfare]  = Make("fanfare", 3.2f, t => (Brass(196f, t) * Swell(t, 0f, 0.5f) + Brass(261.63f, t) * Swell(t, 0.45f, 0.5f) + Brass(392f, t) * Swell(t, 0.9f, 2.2f) + Brass(523.25f, t) * Swell(t, 0.9f, 2.2f) * 0.5f) * 0.42f);
            _clips[(int)Clip.Error]    = Make("error", 0.16f, t => Saw(140f, t) * Env(t, 0.002f, 0.10f) * 0.4f);

            _pool = new AudioSource[18];
            for (int i = 0; i < _pool.Length; i++) { _pool[i] = gameObject.AddComponent<AudioSource>(); _pool[i].playOnAwake = false; _pool[i].spatialBlend = 0f; }

            // ambience: a wind bed and a drone a fifth wide. Both loop on whole cycles so there is no click.
            _wind = gameObject.AddComponent<AudioSource>(); _wind.loop = true; _wind.volume = 0.16f;
            float lp = 0f;
            _wind.clip = Make("wind", 8f, t => { lp += (Noise() - lp) * 0.035f; return lp * 3.2f * (0.55f + 0.45f * Mathf.Sin(t * Mathf.PI * 2f / 8f)); }); _wind.Play();
            _music = gameObject.AddComponent<AudioSource>(); _music.loop = true; _music.volume = 0.10f;
            _music.clip = Make("drone", 8f, t => (Sin(73.5f, t) * 0.5f + Sin(110.25f, t) * 0.32f + Sin(147f, t) * 0.2f + Sin(220.5f, t) * 0.08f) * (0.7f + 0.3f * Mathf.Sin(t * Mathf.PI * 2f / 4f))); _music.Play();
        }

        public void SetAge(int age) { _music.pitch = age >= 2 ? 1.122f : 1f; _music.volume = age >= 2 ? 0.13f : 0.10f; }   // up a whole tone: same world, new key

        float Noise() => (float)(_rng.NextDouble() * 2.0 - 1.0);
        static float Sin(float f, float t) => t < 0f ? 0f : Mathf.Sin(2f * Mathf.PI * f * t);
        static float Saw(float f, float t) => t < 0f ? 0f : 2f * (t * f - Mathf.Floor(0.5f + t * f));
        static float Env(float t, float attack, float decay) => t < 0f ? 0f : t < attack ? t / attack : Mathf.Exp(-(t - attack) / decay);
        static float Note(float f, float t, float at) => Sin(f, t - at) * Env(t - at, 0.004f, 0.22f);
        static float Brass(float f, float t) => Saw(f, t) * 0.55f + Sin(f, t) * 0.45f + Sin(f * 2f, t) * 0.12f;
        static float Swell(float t, float at, float len) { float u = (t - at) / len; return u < 0f || u > 1f ? 0f : Mathf.Sin(u * Mathf.PI) * Mathf.Min(1f, u * 6f); }
        static float Formant(float t) => 0.6f + 0.4f * Mathf.Sin(2f * Mathf.PI * 7f * t);

        AudioClip Make(string name, float seconds, Func<float, float> f)
        {
            int n = (int)(seconds * Rate); var data = new float[n];
            for (int i = 0; i < n; i++) data[i] = Mathf.Clamp(f(i / (float)Rate), -1f, 1f);
            for (int i = 0; i < 64 && i < n; i++) { data[n - 1 - i] *= i / 64f; }            // no click at the tail
            var c = AudioClip.Create(name, n, 1, Rate, false); c.SetData(data, 0); return c;
        }

        /// <summary>Volume falls off with distance from what the camera is looking at: grim up close, abstract from afar.</summary>
        public void Play(Clip clip, Vector3 at, float volume, float pitchJitter = 0.06f)
        {
            var cam = Camera.main; float v = volume;
            if (cam != null)
            {
                var rig = cam.GetComponent<RTSCamera>(); var focus = rig != null ? rig.Focus : cam.transform.position;
                float d = Vector3.Distance(new Vector3(at.x, 0, at.z), new Vector3(focus.x, 0, focus.z)) + cam.transform.position.y * 0.35f;
                v *= Mathf.Clamp01(1.15f - d / 75f);
            }
            if (v < 0.02f) return;
            var s = _pool[_next++ % _pool.Length]; s.pitch = 1f + UnityEngine.Random.Range(-pitchJitter, pitchJitter); s.PlayOneShot(_clips[(int)clip], v);
        }

        public void Play2D(Clip clip, float volume) { var s = _pool[_next++ % _pool.Length]; s.pitch = 1f; s.PlayOneShot(_clips[(int)clip], volume); }

        public void Work(int nodeKind, Vector3 at)
        {
            if (nodeKind == (int)NodeKind.Tree) Play(Clip.Chop, at, 0.7f, 0.10f);
            else if (nodeKind == (int)NodeKind.Stone || nodeKind == (int)NodeKind.Iron) Play(Clip.Pick, at, 0.5f, 0.08f);
            else if (nodeKind == -1) Play(Clip.Hammer, at, 0.6f, 0.10f);
            else Play(Clip.Rustle, at, 0.5f, 0.15f);
        }

        /// <summary>docs/09: at most 6 death voices in any half second, never two within 120 ms, pitch +/-8%.</summary>
        public void Death(Vector3 at)
        {
            float now = Time.unscaledTime;
            if (now - _deathWindow > 0.5f) { _deathWindow = now; _deathVoices = 0; }
            if (now - _lastDeath < 0.12f || _deathVoices >= 6) return;
            _lastDeath = now; _deathVoices++;
            Play(Clip.Death, at, 0.75f, 0.08f);
        }
    }
}
