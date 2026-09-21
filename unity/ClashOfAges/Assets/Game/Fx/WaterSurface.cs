using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// The ONE definition of the water's swell. The shader (COA/Water) reads these waves as globals and moves its vertices;
    /// anything that floats asks HeightAt() and gets the same number, so a boat bobs in phase with the water it is drawn on.
    ///
    /// Time is UNSCALED and is ours: the water keeps moving while the game is paused, and does not race at the bot's 8x.
    /// </summary>
    public sealed class WaterSurface : MonoBehaviour
    {
        public const float Level = -0.03f;                       // where DemoSceneBuilder puts the plane. Ground.SeaLevel (0) is the RULE, this is the picture.

        // direction (x, z) · wavelength m · amplitude m.  A 5 cm swell on a shallow shore moves the waterline about half a metre.
        static readonly Vector4[] Waves =
        {
            Wave(new Vector2( 1.00f,  0.30f), 23f, 0.022f),
            Wave(new Vector2(-0.45f,  1.00f), 14f, 0.016f),
            Wave(new Vector2( 0.70f, -0.80f),  9f, 0.010f),
        };
        static Vector4 _speeds;
        static float _time;

        static Vector4 Wave(Vector2 dir, float wavelength, float amplitude)
        { dir.Normalize(); return new Vector4(dir.x, dir.y, 2f * Mathf.PI / wavelength, amplitude); }

        static readonly int TimeId = Shader.PropertyToID("_WaterTime"), WavesId = Shader.PropertyToID("_WaterWaves"), SpeedsId = Shader.PropertyToID("_WaterSpeeds");

        void OnEnable()
        {
            // deep-water dispersion (w = sqrt(g k)), slowed: this is a sheltered lake, not the North Sea
            for (int i = 0; i < 3; i++) _speeds[i] = Mathf.Sqrt(9.81f * Waves[i].z) * 0.6f;
            Push();
        }

        void Update() { _time += Time.unscaledDeltaTime; Push(); }

        static void Push()
        {
            Shader.SetGlobalFloat(TimeId, _time);
            Shader.SetGlobalVectorArray(WavesId, Waves);
            Shader.SetGlobalVector(SpeedsId, _speeds);
        }

        /// <summary>World height of the water surface at (x, z), now. The same sum the vertex shader does.</summary>
        public static float HeightAt(float x, float z)
        {
            float y = Level;
            for (int i = 0; i < 3; i++) y += Waves[i].w * Mathf.Sin((Waves[i].x * x + Waves[i].y * z) * Waves[i].z + _speeds[i] * _time);
            return y;
        }
    }
}
