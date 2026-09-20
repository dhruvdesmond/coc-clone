using COA.Sim;
using UnityEngine;

namespace COA.Game
{
    /// <summary>
    /// Procedural animation for a lib/figure.py humanoid exported by export_figure.py.
    ///
    /// The library has no armature and no clips, but every part is rigid and the limb objects
    /// pivot at the joints, so animation is ten local rotations layered on the authored bind pose.
    /// Three speeds, never blended (docs/09): world is linear and slow, business eases, VIOLENCE
    /// DOES NOT EASE -- the strike is a snap, which is the whole trick and it is free.
    /// </summary>
    public sealed class FigureAnimator : MonoBehaviour
    {
        public enum Clip { Idle, Walk, Carry, Chop, Hammer, Attack, Shoot, Dead }
        public Clip clip;
        public float speed;                      // m/s, drives walk cadence
        [HideInInspector] public float strike;   // set to 0 to start an attack swing

        Transform _body, _head, _armL, _foreL, _armR, _foreR, _legL, _shinL, _legR, _shinR;
        Quaternion[] _bind; Transform[] _all; Vector3 _bodyPos;
        // ABSOLUTE poses. These figures are not authored in a neutral stance (the archer is already
        // aiming, the swordsman already has his shield up), so adding angles to the bind pose sent the
        // bow arm straight up. Instead each limb's bind DIRECTION is read from its exported "_tip"
        // marker and corrected to "hanging straight down"; pose angles then mean the same thing on
        // every figure. _corr[i] maps a limb's mesh frame to that canonical frame.
        Quaternion[] _corr; static readonly int[] ParentOf = { -1, -1, -1, 2, -1, 4, -1, 6, -1, 8 };
        float _phase, _t, _deadT; float _deadYaw;

        static readonly string[] LimbNames = { "Body", "Head", "ArmL", "ForeL", "ArmR", "ForeR", "LegL", "ShinL", "LegR", "ShinR" };
        // skeleton parent of each limb: -1 = the figure root. (ParentOf, above, is a different thing: the limb whose
        // CORRECTION a child inherits. Arms and legs hang from the Body but are corrected independently of it.)
        static readonly int[] BoneParent = { -1, 0, 0, 2, 0, 4, 0, 6, 0, 8 };

        /// <summary>
        /// BUILD THE SKELETON HERE, not in the FBX. The exporter ships ten flat limb meshes whose origins are the
        /// joints, plus "_tip" empties. A first attempt shipped a nested FBX hierarchy and it arrived broken at the
        /// bind pose (children rotated 90 degrees, positions in another axis convention -- the citizen lay in
        /// pieces on the ground). Here each joint becomes a pivot with IDENTITY local rotation in the figure's own
        /// space, by construction; the imported mesh hangs under it keeping whatever rotation the importer gave it.
        /// </summary>
        void Awake()
        {
            var root = transform;
            var mesh = new Transform[LimbNames.Length];
            foreach (Transform c in root) for (int i = 0; i < LimbNames.Length; i++) if (c.name == LimbNames[i]) mesh[i] = c;

            _all = new Transform[LimbNames.Length];
            for (int i = 0; i < LimbNames.Length; i++)
            {
                if (mesh[i] == null) continue;
                var pivot = new GameObject(LimbNames[i] + "_pivot").transform;
                pivot.gameObject.layer = mesh[i].gameObject.layer;
                pivot.SetParent(root, false);
                pivot.position = mesh[i].position; pivot.rotation = root.rotation; pivot.localScale = Vector3.one;
                _all[i] = pivot;
            }
            // bind directions, measured in the figure's own space BEFORE anything is re-parented
            var dir = new Vector3[LimbNames.Length];
            for (int i = 2; i < LimbNames.Length; i++)
            {
                var tip = root.Find(LimbNames[i] + "_tip");
                if (tip == null || _all[i] == null) { dir[i] = Vector3.down; continue; }
                dir[i] = root.InverseTransformDirection(tip.position - _all[i].position).normalized;
            }
            for (int i = 0; i < LimbNames.Length; i++)
            {
                if (_all[i] == null) continue;
                mesh[i].SetParent(_all[i], true);                                               // mesh keeps its world pose
                if (BoneParent[i] >= 0 && _all[BoneParent[i]] != null) _all[i].SetParent(_all[BoneParent[i]], true);
            }
            foreach (var n in LimbNames) { var tip = root.Find(n + "_tip"); if (tip != null) Destroy(tip.gameObject); }

            _body = _all[0]; _head = _all[1]; _armL = _all[2]; _foreL = _all[3]; _armR = _all[4]; _foreR = _all[5];
            _legL = _all[6]; _shinL = _all[7]; _legR = _all[8]; _shinR = _all[9];
            _bind = new Quaternion[_all.Length];
            for (int i = 0; i < _all.Length; i++) _bind[i] = Quaternion.identity;
            if (_body != null) _bodyPos = _body.localPosition;

            _corr = new Quaternion[_all.Length];
            for (int i = 0; i < _all.Length; i++)
            {
                _corr[i] = Quaternion.identity;
                if (i < 2 || _all[i] == null) continue;                          // Body and Head keep their authored posture
                int p = ParentOf[i];
                _corr[i] = p < 0 ? Quaternion.FromToRotation(dir[i], Vector3.down)
                                 : Quaternion.FromToRotation(_corr[p] * dir[i], Vector3.down);
            }
            _phase = Random.value * 10f;            // so a group never marches in unison
            strike = 9f;
        }

        void Set(int i, float x, float y = 0f, float z = 0f)
        {
            if (_all[i] == null) return;
            var e = Quaternion.Euler(x, y, z);
            if (i < 2) { _all[i].localRotation = _bind[i] * e; return; }
            int p = ParentOf[i];
            // top-level limb:  pose * correction.   child limb: the same, conjugated into the parent's
            // mesh frame, because the parent has itself been corrected and the hinge axis moved with it.
            _all[i].localRotation = p < 0 ? e * _corr[i]
                                          : Quaternion.Inverse(_corr[p]) * e * _corr[i] * _corr[p];
        }

        public void Die(float yaw) { clip = Clip.Dead; _deadT = 0f; _deadYaw = yaw; }

        void LateUpdate()
        {
            if (_body == null) return;
            float dt = Time.deltaTime; _t += dt; strike += dt;
            float bob = 0f;

            switch (clip)
            {
                case Clip.Idle:
                {
                    float s = Mathf.Sin((_t + _phase) * 1.3f);
                    Set(0, s * 1.2f); Set(1, s * -1.5f, Mathf.Sin((_t + _phase) * 0.37f) * 9f);
                    // arms hang a little forward and out, elbows soft; a slight open stance
                    Set(2, -6f + s * 2f, 0f, -8f); Set(3, -22f); Set(4, -6f - s * 2f, 0f, 8f); Set(5, -26f);
                    Set(6, -5f, 0f, -3f); Set(7, 6f); Set(8, 6f, 0f, 3f); Set(9, 3f);
                    break;
                }
                case Clip.Walk:
                case Clip.Carry:
                {
                    // cadence follows ground speed, so feet do not skate
                    _phase += dt * Mathf.Max(speed, 0.6f) * 2.35f;
                    float s = Mathf.Sin(_phase), c = Mathf.Cos(_phase);
                    float stride = Mathf.Lerp(14f, 27f, Mathf.InverseLerp(1f, 4.5f, speed));
                    Set(6, s * stride); Set(8, -s * stride);
                    Set(7, Mathf.Max(0f, -c) * stride * 1.25f); Set(9, Mathf.Max(0f, c) * stride * 1.25f);
                    bob = Mathf.Abs(c) * 0.035f;
                    Set(0, 5f, s * 3.5f); Set(1, -3f);
                    if (clip == Clip.Carry) { Set(2, -58f); Set(3, -48f); Set(4, -58f); Set(5, -48f); }   // arms forward, holding the load
                    else { Set(2, -s * stride * 0.8f, 0f, -6f); Set(3, -20f); Set(4, s * stride * 0.45f, 0f, 6f); Set(5, -32f); }   // the tool arm swings less: it is carrying something
                    break;
                }
                case Clip.Chop:
                case Clip.Hammer:
                {
                    // 1.6 s (chop) / 1.1 s (hammer) cycle matching the sim's WorkImpact timer:
                    // slow raise, a SNAP down with no easing, a short rest on the wood.
                    float period = clip == Clip.Chop ? 1.6f : 1.1f;
                    float u = ((_t + _phase) % period) / period;
                    float raise = u < 0.62f ? Mathf.SmoothStep(0f, 1f, u / 0.62f) : u < 0.70f ? 1f - (u - 0.62f) / 0.08f : 0f;
                    Set(4, Mathf.Lerp(-35f, -150f, raise)); Set(5, Mathf.Lerp(-25f, -70f, raise));
                    Set(2, Mathf.Lerp(-30f, -95f, raise)); Set(3, -40f);
                    Set(0, Mathf.Lerp(16f, -10f, raise), Mathf.Lerp(6f, -12f, raise)); Set(1, Mathf.Lerp(8f, -12f, raise));
                    Set(6, -8f); Set(8, 10f); Set(7, 8f); Set(9, 6f);
                    break;
                }
                case Clip.Attack:
                {
                    // anticipation (4 frames back), snap, recover. `strike` is reset by the view on each sim Attack event.
                    float a = strike;
                    float arm = a < 0.10f ? Mathf.Lerp(-40f, -155f, a / 0.10f)
                              : a < 0.16f ? Mathf.Lerp(-155f, 25f, (a - 0.10f) / 0.06f)
                              : Mathf.Lerp(25f, -40f, Mathf.Clamp01((a - 0.16f) / 0.45f));
                    float twist = a < 0.10f ? Mathf.Lerp(0f, -28f, a / 0.10f) : a < 0.16f ? Mathf.Lerp(-28f, 30f, (a - 0.10f) / 0.06f)
                                : Mathf.Lerp(30f, 0f, Mathf.Clamp01((a - 0.16f) / 0.45f));
                    Set(4, arm, 0f, -12f); Set(5, -30f); Set(0, 6f, twist); Set(2, -55f); Set(3, -70f);   // shield arm up
                    Set(6, -14f); Set(8, 16f); Set(7, 10f); Set(9, 4f); Set(1, 0f, -twist * 0.5f);
                    break;
                }
                case Clip.Shoot:
                {
                    float a = strike;                                   // draw - hold - release
                    float draw = a < 0.12f ? 1f - a / 0.12f : Mathf.Clamp01((a - 0.35f) / 0.7f);
                    Set(2, -88f, -8f); Set(3, -4f);                     // bow arm out
                    Set(4, -75f, 30f); Set(5, Mathf.Lerp(-20f, -95f, draw));
                    Set(0, 0f, -24f); Set(1, 0f, 22f); Set(6, -6f); Set(8, 8f); Set(7, 0); Set(9, 0);
                    break;
                }
                case Clip.Dead:
                {
                    _deadT += dt;
                    float f = Mathf.Clamp01(_deadT / 0.55f); f = f * f;  // accelerating fall, no ease-out
                    // falls onto his back: the body pitches, the legs stay near straight, the arms are thrown wide
                    Set(0, -86f * f, 0f, 6f * f); Set(1, -14f * f); Set(2, -30f * f, 0, -55f * f); Set(4, -20f * f, 0, 62f * f);
                    Set(3, -24f * f); Set(5, -35f * f); Set(6, 8f * f, 0, -9f * f); Set(8, -4f * f, 0, 11f * f); Set(7, 14f * f); Set(9, 26f * f);
                    bob = -0.80f * f;
                    break;
                }
            }
            _body.localPosition = _bodyPos + new Vector3(0f, bob, 0f);
        }
    }
}
