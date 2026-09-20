using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

/// <summary>
/// For every rigged figure: ASSERT the import, then generate its AnimatorController.
///
/// The assertion matters more than the controller. Twice on this project a figure arrived in Unity broken
/// while looking perfect in Blender, and both times it went unseen for hours. So nothing here is assumed:
/// one SkinnedMeshRenderer, all twelve bones, every clip the sidecar promises at the promised length,
/// the promised height -- or an error that says exactly which of those failed.
/// </summary>
public static class FigureRigSetup
{
    const string Dir = "Assets/Animation";
    static readonly string[] Bones = { "Root", "Body", "Head", "ArmL", "ForeL", "ArmR", "ForeR", "LegL", "ShinL", "LegR", "ShinR" };

    [MenuItem("Clash of Ages/Rigs - Verify and build controllers")]
    public static Dictionary<string, RuntimeAnimatorController> Build()
    {
        var result = new Dictionary<string, RuntimeAnimatorController>();
        Directory.CreateDirectory(Dir);
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Models" }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            if (!PaletteImporter.IsRig(path)) continue;
            string name = Path.GetFileNameWithoutExtension(path);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var side = File.ReadAllText(Path.ChangeExtension(path, null) + ".meta.json.txt");
            int fail = 0;
            void Check(bool ok, string what) { if (!ok) { fail++; Debug.LogError($"[rig] {name}: FAIL {what}"); } }

            var skins = prefab.GetComponentsInChildren<SkinnedMeshRenderer>();
            Check(skins.Length == 1, $"expected 1 SkinnedMeshRenderer, found {skins.Length}");
            Check(prefab.GetComponentsInChildren<MeshRenderer>().Length == 0, "found loose MeshRenderers: the mesh is not fully skinned");
            var all = prefab.GetComponentsInChildren<Transform>().Select(t => t.name).ToList();
            foreach (var b in Bones) Check(all.Contains(b), "bone '" + b + "' is missing");
            if (skins.Length == 1)
            {
                Check(skins[0].bones.Length == Bones.Length, $"skin binds {skins[0].bones.Length} bones, expected {Bones.Length}");
                // Measure the MESH, not the renderer: Unity grows a skinned renderer's bounds to enclose its
                // animation, so a swordsman with his sword overhead reads "2.18 m tall" and a correct rig fails.
                // The skinned mesh stays in Blender's frame (Z up), so height is bounds.size.z.
                float h = skins[0].sharedMesh.bounds.size.z, want = Num(side, "\"z\"");
                // three decimals: a '0.00' once passed for an empty mesh when it was a 3 mm one
                Check(Mathf.Abs(h - want) < want * 0.02f, $"mesh height {h:F3} m, sidecar says {want:F3} m");
            }

            var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToList();
            var ctrlPath = $"{Dir}/{name}.controller";
            AssetDatabase.DeleteAsset(ctrlPath);
            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(ctrlPath);
            ctrl.AddParameter("WalkSpeed", AnimatorControllerParameterType.Float);
            var sm = ctrl.layers[0].stateMachine;
            foreach (var want in new[] { "Idle", "Walk", "Carry", "Chop", "Hammer", "Attack", "Shoot", "Death" })
            {
                var clip = clips.FirstOrDefault(c => c.name == want);
                Check(clip != null, "clip '" + want + "' is missing (have: " + string.Join(",", clips.Select(c => c.name)) + ")");
                if (clip == null) continue;
                float seconds = Num(side, "\"name\": \"" + want + "\"", "\"seconds\"");
                Check(Mathf.Abs(clip.length - seconds) < 0.05f, $"clip {want} is {clip.length:F3} s, sidecar says {seconds:F3} s");
                bool loop = want == "Idle" || want == "Walk" || want == "Carry" || want == "Chop" || want == "Hammer";
                Check(clip.isLooping == loop, $"clip {want} looping={clip.isLooping}, expected {loop}");
                var st = sm.AddState(want); st.motion = clip; st.writeDefaultValues = true;
                if (want == "Walk" || want == "Carry") { st.speedParameterActive = true; st.speedParameter = "WalkSpeed"; }
                if (want == "Idle") sm.defaultState = st;
            }
            EditorUtility.SetDirty(ctrl);
            result[name] = ctrl;
            Debug.Log($"[rig] {name}: {(fail == 0 ? "OK" : fail + " FAILURE(S)")}  bones {all.Count(n => Bones.Contains(n))}/{Bones.Length}  clips {clips.Count}  " +
                      (skins.Length == 1 ? $"mesh height {skins[0].sharedMesh.bounds.size.z:F3} m" : ""));
        }
        AssetDatabase.SaveAssets();
        Debug.Log("RIGS_RESULT " + result.Count + " controllers");
        return result;
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
