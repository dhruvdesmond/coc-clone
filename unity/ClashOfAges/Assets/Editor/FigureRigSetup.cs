using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using COA.Game;

/// <summary>
/// ONE clip library, ONE controller, every humanoid (PROGRESS N12). And for every rigged figure: ASSERT the import.
///
/// The assertions matter more than the controller. Twice on this project a figure arrived in Unity broken while
/// looking perfect in Blender, and both times it went unseen for hours. So nothing here is assumed: one
/// SkinnedMeshRenderer, all eleven bones, the promised height, and -- the claim the shared library rests on --
/// a REST POSE identical to the library's, bone for bone. If a figure's rest pose drifts, every clip is wrong on
/// it by exactly that much, and nothing else would say so.
/// </summary>
public static class FigureRigSetup
{
    const string Dir = "Assets/Animation", ClipDir = "Assets/Animation/Clips", CtrlPath = "Assets/Animation/humanoid.controller";
    static readonly string[] Bones = { "Root", "Body", "Head", "ArmL", "ForeL", "ArmR", "ForeR", "LegL", "ShinL", "LegR", "ShinR" };
    static readonly HashSet<string> SpeedDriven = new HashSet<string> { "Walk", "Carry", "Run", "RunShield", "Flee", "BannerWalk" };

    [MenuItem("Clash of Ages/Rigs - Verify and build controllers")]
    public static Dictionary<string, RuntimeAnimatorController> Build()
    {
        var result = new Dictionary<string, RuntimeAnimatorController>();
        Directory.CreateDirectory(ClipDir);
        int fail = 0;
        void Check(bool ok, string who, string what) { if (!ok) { fail++; Debug.LogError($"[rig] {who}: FAIL {what}"); } }

        // ---------------------------------------------------------------- the library
        string libPath = PaletteImporter.ClipLibrary;
        var lib = AssetDatabase.LoadAssetAtPath<GameObject>(libPath);
        if (lib == null) { Debug.LogError("[rig] FAIL no clip library at " + libPath + " -- run tools/export_all.sh figures"); return result; }
        var libSide = File.ReadAllText(Path.ChangeExtension(libPath, null) + ".meta.json.txt");
        var promised = Regex.Matches(libSide, "\"name\":\\s*\"(\\w+)\",\\s*\"frames\":\\s*\\d+,\\s*\"seconds\":\\s*([\\d.]+),\\s*\"loop\":\\s*(true|false)")
                            .Cast<Match>().Select(m => (name: m.Groups[1].Value,
                                                        seconds: float.Parse(m.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture),
                                                        loop: m.Groups[3].Value == "true")).ToList();
        Check(promised.Count >= 28, "library", $"sidecar lists {promised.Count} clips, expected at least 28");
        var source = AssetDatabase.LoadAllAssetsAtPath(libPath).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToList();

        var ctrl = AssetDatabase.LoadAssetAtPath<AnimatorController>(CtrlPath);
        if (ctrl != null) AssetDatabase.DeleteAsset(CtrlPath);
        ctrl = AnimatorController.CreateAnimatorControllerAtPath(CtrlPath);
        ctrl.AddParameter("WalkSpeed", AnimatorControllerParameterType.Float);
        var sm = ctrl.layers[0].stateMachine;
        int kept = 0, dropped = 0;
        foreach (var want in promised)
        {
            var src = source.FirstOrDefault(c => c.name == want.name);
            Check(src != null, "library", "clip '" + want.name + "' is missing (have: " + string.Join(",", source.Select(c => c.name)) + ")");
            if (src == null) continue;
            Check(Mathf.Abs(src.length - want.seconds) < 0.05f, "library", $"clip {want.name} is {src.length:F3} s, sidecar says {want.seconds:F3} s");

            // A PORTABLE copy. An FBX bake keys position and scale on every bone, which would stamp the library
            // figure's limb lengths onto everyone who plays the clip. Keep rotations, and Root's position (Root rests
            // at the origin on every figure; it carries the pelvis offset). Nothing else.
            string clipPath = $"{ClipDir}/{want.name}.anim";
            var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            if (clip == null) { clip = new AnimationClip(); AssetDatabase.CreateAsset(clip, clipPath); }
            clip.ClearCurves(); clip.frameRate = src.frameRate;
            foreach (var b in AnimationUtility.GetCurveBindings(src))
            {
                bool rot = b.propertyName.StartsWith("m_LocalRotation");
                bool rootPos = b.propertyName.StartsWith("m_LocalPosition") && (b.path == "Root" || b.path.EndsWith("/Root"));
                if (!rot && !rootPos) { dropped++; continue; }
                AnimationUtility.SetEditorCurve(clip, b, AnimationUtility.GetEditorCurve(src, b)); kept++;
            }
            var set = AnimationUtility.GetAnimationClipSettings(clip);
            set.loopTime = want.loop; set.stopTime = src.length;
            AnimationUtility.SetAnimationClipSettings(clip, set);
            EditorUtility.SetDirty(clip);
            Check(clip.isLooping == want.loop, "library", $"clip {want.name} looping={clip.isLooping}, expected {want.loop}");

            var st = sm.AddState(want.name); st.motion = clip; st.writeDefaultValues = true;
            if (SpeedDriven.Contains(want.name)) { st.speedParameterActive = true; st.speedParameter = "WalkSpeed"; }
            if (want.name == "Idle") sm.defaultState = st;
        }
        EditorUtility.SetDirty(ctrl);
        var libRest = Rest(lib);
        float thigh = Thigh(lib);
        Check(Mathf.Abs(thigh - RigAnimator.LibraryThigh) < 0.002f, "library", $"thigh is {thigh:F4} m but RigAnimator.LibraryThigh = {RigAnimator.LibraryThigh:F4}");
        Debug.Log($"[rig] library: {promised.Count} clips -> {ClipDir}, {kept} curves kept, {dropped} position/scale curves dropped, thigh {thigh:F4} m");

        // ---------------------------------------------------------------- every figure
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Models" }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            if (!PaletteImporter.IsRig(path) || path == libPath) continue;
            string name = Path.GetFileNameWithoutExtension(path);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var side = File.ReadAllText(Path.ChangeExtension(path, null) + ".meta.json.txt");
            int before = fail;

            var skins = prefab.GetComponentsInChildren<SkinnedMeshRenderer>();
            Check(skins.Length == 1, name, $"expected 1 SkinnedMeshRenderer, found {skins.Length}");
            Check(prefab.GetComponentsInChildren<MeshRenderer>().Length == 0, name, "found loose MeshRenderers: the mesh is not fully skinned");
            var all = prefab.GetComponentsInChildren<Transform>().Select(t => t.name).ToList();
            foreach (var b in Bones) Check(all.Contains(b), name, "bone '" + b + "' is missing");
            if (skins.Length == 1)
            {
                Check(skins[0].bones.Length == Bones.Length, name, $"skin binds {skins[0].bones.Length} bones, expected {Bones.Length}");
                // Measure the MESH, not the renderer: Unity grows a skinned renderer's bounds to enclose its animation.
                // The skinned mesh stays in Blender's frame (Z up), so height is bounds.size.z.
                float h = skins[0].sharedMesh.bounds.size.z, want = Num(side, "\"z\"");
                // three decimals: a '0.00' once passed for an empty mesh when it was a 3 mm one
                Check(Mathf.Abs(h - want) < want * 0.02f, name, $"mesh height {h:F3} m, sidecar says {want:F3} m");
            }
            int own = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Count(c => !c.name.StartsWith("__preview__"));
            Check(own == 0, name, $"carries {own} clips of its own; figures play the shared library");

            // THE claim: same rest pose as the library, bone for bone.
            float worst = 0f; string worstBone = "";
            foreach (var kv in Rest(prefab))
            {
                if (!libRest.TryGetValue(kv.Key, out var q)) { Check(false, name, "bone path '" + kv.Key + "' is not in the library"); continue; }
                float a = Quaternion.Angle(q, kv.Value); if (a > worst) { worst = a; worstBone = kv.Key; }
            }
            Check(worst < 0.5f, name, $"rest pose differs from the library by {worst:F2} deg at {worstBone}: shared clips will be wrong on this figure");

            result[name] = ctrl;
            Debug.Log($"[rig] {name}: {(fail == before ? "OK" : (fail - before) + " FAILURE(S)")}  bones {all.Count(n => Bones.Contains(n))}/{Bones.Length}  " +
                      $"rest pose within {worst:F3} deg of the library  thigh x{Thigh(prefab) / thigh:F3}  " +
                      (skins.Length == 1 ? $"mesh height {skins[0].sharedMesh.bounds.size.z:F3} m" : ""));
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"RIGS_RESULT {result.Count} figures, 1 controller, {promised.Count} shared clips, {fail} failures");
        return result;
    }

    /// <summary>bone path -> local rotation AT BIND, read from the skin and not from the transforms: an FBX that carries
    /// animation imports its transforms posed (measured: the library "differed" from the villager it was built from by
    /// 88 degrees), and the bind pose is what a clip actually plays against.</summary>
    static Dictionary<string, Quaternion> Rest(GameObject prefab)
    {
        var d = new Dictionary<string, Quaternion>();
        var skin = prefab.GetComponentInChildren<SkinnedMeshRenderer>(); if (skin == null) return d;
        var bind = new Dictionary<Transform, Matrix4x4>();
        for (int i = 0; i < skin.bones.Length; i++) bind[skin.bones[i]] = skin.sharedMesh.bindposes[i].inverse;
        foreach (var kv in bind)
            if (kv.Key.parent != null && bind.TryGetValue(kv.Key.parent, out var parent))
                d[AnimationUtility.CalculateTransformPath(kv.Key, prefab.transform)] = (parent.inverse * kv.Value).rotation;
        return d;
    }

    static float Thigh(GameObject prefab)
    {
        var ts = prefab.GetComponentsInChildren<Transform>();
        var hip = ts.FirstOrDefault(t => t.name == "LegL"); var knee = ts.FirstOrDefault(t => t.name == "ShinL");
        return hip == null || knee == null ? -1f : (knee.position - hip.position).magnitude;
    }

    /// <summary>First number after `key` that follows `anchor` in a small generated JSON file.</summary>
    static float Num(string s, string anchor, string key = null)
    {
        int i = s.IndexOf(anchor, System.StringComparison.Ordinal); if (i < 0) return -1f;
        if (key != null) { i = s.IndexOf(key, i, System.StringComparison.Ordinal); if (i < 0) return -1f; i += key.Length; } else i += anchor.Length;
        i = s.IndexOf(':', i); int j = i + 1; while (j < s.Length && char.IsWhiteSpace(s[j])) j++;
        int k = j; while (k < s.Length && (char.IsDigit(s[k]) || s[k] == '.' || s[k] == '-')) k++;
        return float.TryParse(s.Substring(j, k - j), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var f) ? f : -1f;
    }
}
