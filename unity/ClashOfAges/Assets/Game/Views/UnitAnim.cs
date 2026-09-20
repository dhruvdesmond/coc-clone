using UnityEngine;

namespace COA.Game
{
    /// <summary>What a UnitView needs from whatever is animating the figure. Two implementations:
    /// RigAnimator (a real skeleton and authored clips) and FigureAnimator (limbs posed in code; the fallback).</summary>
    public abstract class UnitAnim : MonoBehaviour
    {
        /// <summary>What the unit is DOING. Which authored clip that becomes depends on what it is holding (Style).</summary>
        public enum Clip { Idle, Walk, Carry, Chop, Hammer, Attack, Shoot, Dead, Mine, Farm, Forage, Charge, Cheer, Flee }
        [System.NonSerialized] public Clip clip;
        [System.NonSerialized] public float speed;                // ground speed, m/s
        public abstract void Strike();                            // the sim said "this unit just attacked"
        public abstract void Die(float yaw);
        public virtual void Hit() { }                             // the sim said "this unit was just hurt"
        public virtual void Cheer(float seconds) { }

        /// <summary>The eight things the code-posed fallback knows how to do.</summary>
        protected static Clip Basic(Clip c)
        {
            switch (c)
            {
                case Clip.Mine: return Clip.Chop;
                case Clip.Farm: case Clip.Forage: return Clip.Hammer;
                case Clip.Charge: case Clip.Flee: return Clip.Walk;
                case Clip.Cheer: return Clip.Idle;
                default: return c;
            }
        }
    }

    /// <summary>
    /// Drives the Animator on a figure rigged by blender/scripts/rig_figure.py. Every humanoid shares ONE clip
    /// library and ONE controller (PROGRESS N12): the figures have the same rest pose, so a clip is just bone
    /// rotations. Clips are authored per WEAPON CLASS, not per unit (DL42) -- Style picks which set a figure uses.
    /// The controller has one state per clip and no transitions: state is decided by the sim, this cross-fades to it.
    /// </summary>
    public sealed class RigAnimator : UnitAnim
    {
        public enum Style { Worker, Sword, Spear, Bow }

        public const float AuthoredWalkSpeed = 3.34f;             // rig_figure.py WALK_SPEED: one 24-frame cycle
        public const float AuthoredRunSpeed = 4.40f;              // rig_figure.py RUN_SPEED:  one 20-frame cycle
        /// <summary>Hip-to-knee of the figure the library was authored on. FigureRigSetup asserts it against the FBX.
        /// The troops are ~20% bigger than the citizen, and a crouch that drops her pelvis 30 cm must drop theirs 36.</summary>
        public const float LibraryThigh = 0.4255f;

        Animator _a; Transform _rootBone; float _offsetScale = 1f; Vector3 _lastOut;
        Style _style; string _shown; bool _dead; float _busyUntil, _cheerUntil; int _strikes;
        static readonly int WalkSpeed = Animator.StringToHash("WalkSpeed");

        public static bool Supports(GameObject go) => go.GetComponentInChildren<SkinnedMeshRenderer>() != null;

        public static Style StyleFor(string model)
        {
            switch (model) { case "swordsman": return Style.Sword; case "spearman": return Style.Spear; case "archer": return Style.Bow; default: return Style.Worker; }
        }

        public void Init(RuntimeAnimatorController controller, Style style)
        {
            _style = style;
            // measured at REST, before the Animator has written a single pose
            Transform hip = Find(transform, "LegL"), knee = Find(transform, "ShinL"); _rootBone = Find(transform, "Root");
            if (hip != null && knee != null)
                _offsetScale = (knee.position - hip.position).magnitude / Mathf.Max(1e-4f, transform.lossyScale.y) / LibraryThigh;
            _a = GetComponent<Animator>(); if (_a == null) _a = gameObject.AddComponent<Animator>();
            _a.runtimeAnimatorController = controller;
            _a.applyRootMotion = false;
            _a.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
            _a.Update(0f);
            // so a squad does not march, chop or idle in unison
            _shown = "Idle"; _a.Play("Idle", 0, Random.value);
            foreach (var sk in GetComponentsInChildren<SkinnedMeshRenderer>()) sk.updateWhenOffscreen = false;
        }

        static Transform Find(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t) { var r = Find(c, name); if (r != null) return r; }
            return null;
        }

        string Guard => _style == Style.Sword ? "GuardIdle" : _style == Style.Spear ? "GuardSpear" : _style == Style.Bow ? "AimIdle" : "Idle";

        string StateFor(Clip c)
        {
            switch (c)
            {
                case Clip.Walk:   return "Walk";
                case Clip.Charge: return _style == Style.Sword || _style == Style.Spear ? "RunShield" : "Run";
                case Clip.Carry:  return "Carry";
                case Clip.Chop:   return "Chop";
                case Clip.Hammer: return "Hammer";
                case Clip.Mine:   return "Mine";
                case Clip.Farm:   return "Farm";
                case Clip.Forage: return "Forage";
                case Clip.Flee:   return "Flee";
                case Clip.Cheer:  return "Cheer";
                case Clip.Attack: case Clip.Shoot: return Guard;        // BETWEEN strikes. The strike itself is Strike().
                default:          return "Idle";
            }
        }

        public override void Strike()
        {
            if (_dead || _a == null) return;
            string s;
            switch (_style)
            {
                case Style.Bow:   s = "Shoot"; break;
                case Style.Spear: s = "Thrust"; break;
                case Style.Sword: s = (_strikes++ & 1) == 0 ? "Attack" : "Attack2"; break;   // two cuts in a row are not the same cut
                default:          s = "Attack"; break;
            }
            // violence does not ease (docs/09): no cross-fade, straight to frame 0
            _a.Play(s, 0, 0f); _shown = s; _busyUntil = Time.time + 0.62f;
        }

        public override void Hit()
        {
            if (_dead || _a == null || Time.time < _busyUntil) return;      // never flinch out of your own strike
            bool shield = _style == Style.Sword || _style == Style.Spear;
            string s = shield && Random.value < 0.5f ? "Block" : "HitReact";
            _a.CrossFadeInFixedTime(s, 0.04f); _shown = s; _busyUntil = Time.time + (s == "Block" ? 0.55f : 0.42f);
        }

        public override void Cheer(float seconds) { _cheerUntil = Time.time + seconds + Random.value * 0.6f; }

        public override void Die(float yaw)
        {
            if (_a == null) return;
            _dead = true; clip = Clip.Dead;
            _a.CrossFadeInFixedTime(Random.value < 0.5f ? "Death" : "DeathFront", 0.05f);
        }

        void Update()
        {
            if (_a == null || _dead) return;
            // cadence follows ground speed (and the figure's drawn scale), so feet do not skate
            float authored = clip == Clip.Charge || clip == Clip.Flee ? AuthoredRunSpeed : AuthoredWalkSpeed;
            _a.SetFloat(WalkSpeed, Mathf.Clamp(speed / (authored * transform.lossyScale.y * _offsetScale), 0.5f, 1.8f));
            if (Time.time < _busyUntil) return;                              // a strike, a flinch or a block is playing out
            var want = clip == Clip.Idle && Time.time < _cheerUntil ? "Cheer" : StateFor(clip);
            if (want == _shown) return;
            bool wasOneShot = _shown == "Attack" || _shown == "Attack2" || _shown == "Thrust" || _shown == "Shoot" || _shown == "Block" || _shown == "HitReact";
            _shown = want;
            _a.CrossFadeInFixedTime(want, wasOneShot ? 0.18f : 0.12f);
        }

        void LateUpdate()
        {
            // The library's pelvis offset rides on Root, which rests at the origin: scaling it is scaling the offset.
            // A culled Animator stops writing, so only scale a value the Animator has just written -- or it compounds.
            if (_rootBone == null || _offsetScale == 1f) return;
            var p = _rootBone.localPosition;
            if (p != _lastOut) { p *= _offsetScale; _rootBone.localPosition = p; _lastOut = p; }
        }
    }
}
