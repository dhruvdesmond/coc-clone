using UnityEngine;

namespace COA.Game
{
    /// <summary>What a UnitView needs from whatever is animating the figure. Two implementations:
    /// RigAnimator (a real skeleton and authored clips) and FigureAnimator (limbs posed in code; the fallback).</summary>
    public abstract class UnitAnim : MonoBehaviour
    {
        public enum Clip { Idle, Walk, Carry, Chop, Hammer, Attack, Shoot, Dead }
        [System.NonSerialized] public Clip clip;
        [System.NonSerialized] public float speed;                // ground speed, m/s
        public abstract void Strike();                            // the sim said "this unit just attacked"
        public abstract void Die(float yaw);
    }

    /// <summary>
    /// Drives the Animator on a figure rigged by blender/scripts/rig_figure.py: 11 bones, rigid skinning,
    /// eight authored clips. The controller has one state per clip and no transitions -- state is decided by the
    /// sim, so this just cross-fades to whatever the unit is doing.
    /// </summary>
    public sealed class RigAnimator : UnitAnim
    {
        public const float AuthoredWalkSpeed = 3.34f;             // rig_figure.py WALK_SPEED: one 24-frame cycle
        Animator _a; Clip _shown = (Clip)(-1); bool _dead;
        static readonly int WalkSpeed = Animator.StringToHash("WalkSpeed");

        public static bool Supports(GameObject go) => go.GetComponentInChildren<SkinnedMeshRenderer>() != null;

        public void Init(RuntimeAnimatorController controller)
        {
            _a = GetComponent<Animator>(); if (_a == null) _a = gameObject.AddComponent<Animator>();
            _a.runtimeAnimatorController = controller;
            _a.applyRootMotion = false;
            _a.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
            _a.Update(0f);
            // so a squad does not march, chop or idle in unison
            _a.Play("Idle", 0, Random.value);
            foreach (var sk in GetComponentsInChildren<SkinnedMeshRenderer>()) sk.updateWhenOffscreen = false;
        }

        public override void Strike()
        {
            if (_dead || _a == null) return;
            // violence does not ease (docs/09): no cross-fade, straight to frame 0
            _a.Play(clip == Clip.Shoot ? "Shoot" : "Attack", 0, 0f);
        }

        public override void Die(float yaw) { if (_a == null) return; _dead = true; clip = Clip.Dead; _a.CrossFadeInFixedTime("Death", 0.05f); }

        void Update()
        {
            if (_a == null || _dead) return;
            // cadence follows ground speed (and the figure's drawn scale), so feet do not skate
            _a.SetFloat(WalkSpeed, Mathf.Clamp(speed / (AuthoredWalkSpeed * transform.lossyScale.y), 0.5f, 1.8f));
            if (clip == _shown) return;
            bool wasViolent = _shown == Clip.Attack || _shown == Clip.Shoot;
            _shown = clip;
            if (clip == Clip.Attack || clip == Clip.Shoot) return;        // entered by Strike(), on the sim's beat
            _a.CrossFadeInFixedTime(clip == Clip.Dead ? "Death" : clip.ToString(), wasViolent ? 0.18f : 0.12f);
        }
    }
}
