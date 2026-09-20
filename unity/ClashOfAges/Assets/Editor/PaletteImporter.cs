using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Rebuilds Blender's procedural materials in Unity from palette.json.
///
/// WHY: procedural Blender materials cannot be exported -- they arrive untextured grey.
/// Previously Unity kept its own hand-written colour table and the two drifted; seven
/// Norse materials silently arrived unmapped on the last project. blender/lib/materials.py
/// is now the single authority, exported by scripts/export_palette.py.
///
/// An unmapped material name is a LOUD failure: magenta plus a console error. The only
/// reason that bug was ever found is that the import printed what it could not map.
/// </summary>
public class PaletteImporter : AssetPostprocessor
{
    // Read from DISK, not Resources.Load. AssetPostprocessor import order is NOT
    // guaranteed: on a cold import the FBX is processed BEFORE palette.json exists as
    // a TextAsset, Resources.Load returns null, and every material comes out magenta.
    // File.ReadAllText has no such ordering dependency.
    const string PalettePath = "Assets/Resources/palette.json";
    const string MaterialDir     = "Assets/Materials/Generated";
    const string ModelRoot       = "Assets/Models/";
    const string WorldRoot       = "Assets/World/";

    static bool InScope(string p) =>
        p.StartsWith(ModelRoot, StringComparison.Ordinal) || p.StartsWith(WorldRoot, StringComparison.Ordinal);

    /// <summary>Blender dedups datablock names as "Leaf.001"; the palette key is "Leaf".</summary>
    static string Stem(string n)
    {
        int d = n.LastIndexOf('.');
        if (d > 0 && n.Length - d == 4 && char.IsDigit(n[d + 1]) && char.IsDigit(n[d + 2]) && char.IsDigit(n[d + 3]))
            return n.Substring(0, d);
        return n;
    }

    /// <summary>The 4K baked terrain albedo: Vale's .meta silently halved it to 2048.</summary>
    void OnPreprocessTexture()
    {
        if (!assetPath.StartsWith(WorldRoot, StringComparison.Ordinal)) return;
        var ti = (TextureImporter)assetImporter;
        ti.maxTextureSize = 4096;
        ti.sRGBTexture = true;
        ti.mipmapEnabled = true;
        ti.anisoLevel = 8;
        ti.wrapMode = TextureWrapMode.Clamp;
        ti.textureCompression = TextureImporterCompression.CompressedHQ;
    }

    // ------------------------------------------------------------------ palette
    [Serializable] class Entry { public float[] albedo; public float rough; public float metal;
                                 public float emissive; public string kit; public string key; }

    static Dictionary<string, Entry> _palette;
    static float _toneExponent = 0.62f;

    static Dictionary<string, Entry> Palette
    {
        get
        {
            if (_palette != null) return _palette;
            _palette = new Dictionary<string, Entry>();

            if (!File.Exists(PalettePath))
            {
                Debug.LogError($"[palette] {PalettePath} is MISSING. " +
                    "Run: blender -b --factory-startup --python scripts/export_palette.py");
                return _palette;
            }

            // Minimal hand-rolled parse: JsonUtility cannot read a dictionary, and pulling
            // in a JSON package for one generated file is not worth the dependency.
            var text = File.ReadAllText(PalettePath);
            int mi = text.IndexOf("\"materials\"", StringComparison.Ordinal);
            _toneExponent = ReadFloat(text, "\"toneExponent\"", 0.62f);
            if (mi < 0) { Debug.LogError("[palette] no \"materials\" block in palette.json"); return _palette; }

            foreach (var (name, body) in EnumerateObjects(text, mi))
            {
                var e = new Entry {
                    albedo   = ReadFloatArray(body, "\"albedo\""),
                    rough    = ReadFloat(body, "\"rough\"", 0.75f),
                    metal    = ReadFloat(body, "\"metal\"", 0f),
                    emissive = ReadFloat(body, "\"emissive\"", 0f),
                    kit      = body.Contains("\"kit\": \"troop\"") ? "troop" : "",
                };
                if (e.albedo != null && e.albedo.Length >= 3) _palette[name] = e;
            }
            Debug.Log($"[palette] loaded {_palette.Count} materials, toneExponent={_toneExponent}");
            return _palette;
        }
    }

    // --------------------------------------------------------------- model import
    void OnPreprocessModel()
    {
        if (!InScope(assetPath)) return;
        var mi = (ModelImporter)assetImporter;

        // Blender writes FBX in centimetres. export_assets.py bakes scale with
        // FBX_SCALE_ALL, so useFileScale=true + globalScale=1 yields METRES.
        // Do not "helpfully" adjust this -- OnPostprocessModel asserts the result.
        mi.useFileScale       = true;
        mi.globalScale        = 1f;
        mi.importNormals      = ModelImporterNormals.Import;
        mi.importTangents     = ModelImporterTangents.CalculateMikk;
        // A RIG (rig_figure.py writes "kind": "rig" into its sidecar) keeps its skeleton and its clips.
        bool rig = IsRig(assetPath);
        mi.importAnimation    = rig;
        mi.animationType      = rig ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.None;
        if (rig) { mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel; mi.optimizeGameObjects = false;
                   mi.animationCompression = ModelImporterAnimationCompression.Off; mi.resampleCurves = true; }
        mi.importCameras      = false;
        mi.importLights       = false;
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        mi.materialLocation   = ModelImporterMaterialLocation.External;
        mi.meshOptimizationFlags = MeshOptimizationFlags.Everything;
        // World meshes are drawn with Graphics.RenderMeshInstanced and the terrain feeds
        // a MeshCollider + NavMesh bake; both want CPU-readable data.
        mi.isReadable         = assetPath.StartsWith(WorldRoot, StringComparison.Ordinal);
    }

    public static bool IsRig(string modelPath)
    {
        var sidecar = Path.ChangeExtension(modelPath, null) + ".meta.json.txt";
        return File.Exists(sidecar) && File.ReadAllText(sidecar).Contains("\"kind\": \"rig\"");
    }

    static readonly HashSet<string> Looping = new HashSet<string> { "Idle", "Walk", "Carry", "Chop", "Hammer" };

    /// <summary>Blender names takes "Rig|Walk"; strip the armature prefix and set loop flags from the clip name.</summary>
    void OnPreprocessAnimation()
    {
        if (!InScope(assetPath) || !IsRig(assetPath)) return;
        var mi = (ModelImporter)assetImporter;
        var clips = mi.defaultClipAnimations;
        foreach (var c in clips)
        {
            int bar = c.name.LastIndexOf('|');
            if (bar >= 0) c.name = c.name.Substring(bar + 1);
            c.loopTime = Looping.Contains(c.name);
            c.lockRootRotation = c.lockRootHeightY = c.lockRootPositionXZ = false;
        }
        mi.clipAnimations = clips;
    }

    /// <summary>Hand every FBX material slot a palette material instead of a grey default.</summary>
    Material OnAssignMaterialModel(Material material, Renderer renderer)
    {
        if (!InScope(assetPath)) return null;

        var name = Stem(material.name);
        // The terrain's own material is replaced by the baked albedo in DemoSceneBuilder.
        if (name == "VillageGround") return null;
        var path = $"{MaterialDir}/{name}.mat";
        Directory.CreateDirectory(MaterialDir);
        var shader = Shader.Find("Universal Render Pipeline/Lit");

        // Reuse the asset if it exists, but ALWAYS rewrite its properties from the
        // palette. Returning a cached material unchanged means a palette edit -- or a
        // material left magenta because the palette had not loaded yet -- stays wrong
        // forever.
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        bool isNew = mat == null;
        if (isNew) mat = new Material(shader) { name = name };
        else if (mat.shader != shader) mat.shader = shader;

        bool mapped = ApplyEntry(mat, name);
        if (!mapped)
            Debug.LogError($"[palette] UNMAPPED MATERIAL '{name}' in {assetPath}. " +
                "It is magenta on purpose. Either lib/materials.py does not define it, " +
                "or export_palette.py was not re-run.");

        mat.enableInstancing = true;   // everything may be drawn instanced
        if (isNew) AssetDatabase.CreateAsset(mat, path);
        else EditorUtility.SetDirty(mat);
        return mat;
    }

    /// <summary>
    /// Rewrite every generated material from palette.json. Needed because Unity resolves an
    /// EXISTING external material by name without ever calling OnAssignMaterialModel -- so a
    /// material created magenta before its palette entry existed stays magenta through any
    /// number of reimports. Grass did exactly that.
    /// </summary>
    public static int SyncMaterials()
    {
        _palette = null;                                   // re-read the file
        int fixedUp = 0;
        if (!AssetDatabase.IsValidFolder(MaterialDir)) return 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { MaterialDir }))
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
            if (mat == null) continue;
            if (!ApplyEntry(mat, mat.name)) Debug.LogError("[palette] no palette entry for generated material " + mat.name);
            mat.enableInstancing = true;
            EditorUtility.SetDirty(mat);
            fixedUp++;
        }
        AssetDatabase.SaveAssets();
        Debug.Log("[palette] synced " + fixedUp + " generated materials from palette.json");
        return fixedUp;
    }

    /// <summary>Palette entry -> URP/Lit properties. Returns false (and paints magenta) when unmapped.</summary>
    static bool ApplyEntry(Material mat, string name)
    {
        if (Palette.TryGetValue(name, out var e))
        {
            // Raw linear Cycles colour -> display-referred, approximating AgX.
            // Applied here, to EVERY surface, exactly once. Applying it to some
            // surfaces and not others gave orange timber on mint grass last time.
            var c = new Color(
                Mathf.Pow(e.albedo[0], _toneExponent),
                Mathf.Pow(e.albedo[1], _toneExponent),
                Mathf.Pow(e.albedo[2], _toneExponent), 1f);

            // Units must separate from the ground they stand on. The troop palette is authored for close Cycles
            // renders and is dark (leather 0.03); at game distance a figure in it is a silhouette. Lift value, keep hue.
            if (e.kit == "troop")
            {
                Color.RGBToHSV(c, out float hh, out float ss, out float vv);
                c = Color.HSVToRGB(hh, Mathf.Clamp01(ss * 1.08f), Mathf.Clamp01(vv * 1.45f + 0.06f)); c.a = 1f;
            }
            mat.SetColor("_BaseColor", c);
            mat.SetFloat("_Smoothness", Mathf.Clamp01(1f - e.rough));   // URP uses smoothness
            mat.SetFloat("_Metallic",   Mathf.Clamp01(e.metal));

            // Blades and petals are single planes: one-sided, half of them face away from the
            // sun and the camera and read as dark twigs. Draw foliage two-sided.
            bool foliage = name == "Grass" || name.StartsWith("Flower") || name.StartsWith("Leaf");
            mat.SetFloat("_Cull", foliage ? 0f : 2f);
            mat.doubleSidedGI = foliage;
            if (name == "Grass")    // the ramp midpoint probes as dry olive; the meadow is greener
                mat.SetColor("_BaseColor", Color.Lerp(c, new Color(0.30f, 0.44f, 0.16f), 0.55f));
            if (e.emissive > 0f)
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", c * e.emissive);
            }
            return true;
        }
        mat.SetColor("_BaseColor", Color.magenta);          // LOUD failure. Never a silent grey.
        return false;
    }

    /// <summary>Assert the imported size matches what Blender measured, in metres.</summary>
    void OnPostprocessModel(GameObject go)
    {
        if (!assetPath.StartsWith(ModelRoot, StringComparison.Ordinal)) return;

        var sidecar = Path.ChangeExtension(assetPath, null) + ".meta.json.txt";
        if (!File.Exists(sidecar)) return;
        var json = File.ReadAllText(sidecar);

        float ex = ReadFloat(json, "\"x\"", -1f);
        float ey = ReadFloat(json, "\"y\"", -1f);
        float ez = ReadFloat(json, "\"z\"", -1f);
        float tol = ReadFloat(json, "\"toleranceFraction\"", 0.02f);
        int expectTris = (int)ReadFloat(json, "\"triangles\"", -1f);
        if (ex < 0) return;

        if (IsRig(assetPath)) return;          // rigs are asserted by FigureRigSetup against the MESH bounds
        var b = WorldBounds(go);
        // Blender Z-up -> Unity Y-up: Blender (x, y, z) becomes Unity (x, z, y).
        float gx = b.size.x, gy = b.size.z, gz = b.size.y;

        int tris = 0;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            if (mf.sharedMesh != null) tris += mf.sharedMesh.triangles.Length / 3;
        foreach (var sk in go.GetComponentsInChildren<SkinnedMeshRenderer>())
            if (sk.sharedMesh != null) tris += sk.sharedMesh.triangles.Length / 3;

        // Three decimals and a vertex count, deliberately: a log that printed
        // "bounds (0.00, 0.00, 0.00)" at two decimals was once read as "empty mesh"
        // and used to REVERSE a correct fix. It was a 3 mm mesh.
        string got = $"{gx:F3} x {gy:F3} x {gz:F3} m";
        string want = $"{ex:F3} x {ey:F3} x {ez:F3} m";

        bool ok = Near(gx, ex, tol) && Near(gy, ey, tol) && Near(gz, ez, tol);
        if (!ok)
        {
            float ratio = ex > 0.0001f ? gx / ex : 0f;
            Debug.LogError(
                $"[palette] SCALE MISMATCH on {assetPath}\n" +
                $"          imported {got}  (verts { CountVerts(go) }, tris {tris})\n" +
                $"          expected {want}\n" +
                $"          ratio {ratio:F4}  -- 0.01 means the prefab root's 100x was " +
                "dropped; 100 means it was applied twice (lossyScale already IS the " +
                "whole chain from the root down).");
        }
        else
        {
            Debug.Log($"[palette] {Path.GetFileName(assetPath)}  {got}  " +
                      $"tris {tris}" + (expectTris > 0 ? $"/{expectTris}" : "") +
                      $"  renderers {go.GetComponentsInChildren<MeshRenderer>().Length}  OK");
        }
    }

    // ---------------------------------------------------------------- helpers
    static bool Near(float a, float b, float tol) => Mathf.Abs(a - b) <= Mathf.Max(tol * b, 0.001f);

    static int CountVerts(GameObject go)
    {
        int v = 0;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            if (mf.sharedMesh != null) v += mf.sharedMesh.vertexCount;
        return v;
    }

    static Bounds WorldBounds(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return new Bounds(Vector3.zero, Vector3.zero);
        var b = rs[0].bounds;
        for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
        return b;
    }

    static float ReadFloat(string s, string key, float fallback)
    {
        int i = s.IndexOf(key, StringComparison.Ordinal);
        if (i < 0) return fallback;
        i = s.IndexOf(':', i + key.Length);
        if (i < 0) return fallback;
        int j = i + 1;
        while (j < s.Length && (s[j] == ' ' || s[j] == '\n' || s[j] == '\r' || s[j] == '\t')) j++;
        int k = j;
        while (k < s.Length && (char.IsDigit(s[k]) || s[k] == '.' || s[k] == '-' || s[k] == '+' ||
                                s[k] == 'e' || s[k] == 'E')) k++;
        return float.TryParse(s.Substring(j, k - j), NumberStyles.Float,
                              CultureInfo.InvariantCulture, out var f) ? f : fallback;
    }

    static float[] ReadFloatArray(string s, string key)
    {
        int i = s.IndexOf(key, StringComparison.Ordinal);
        if (i < 0) return null;
        int a = s.IndexOf('[', i), b = s.IndexOf(']', a);
        if (a < 0 || b < 0) return null;
        var parts = s.Substring(a + 1, b - a - 1).Split(',');
        var outv = new float[parts.Length];
        for (int k = 0; k < parts.Length; k++)
            float.TryParse(parts[k].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out outv[k]);
        return outv;
    }

    /// <summary>Yield (name, body) for each object inside the "materials" block.</summary>
    static IEnumerable<(string, string)> EnumerateObjects(string text, int from)
    {
        int i = text.IndexOf('{', from);
        if (i < 0) yield break;
        int depth = 0, p = i;
        while (p < text.Length)
        {
            char c = text[p];
            if (c == '{') depth++;
            else if (c == '}') { depth--; if (depth == 0) break; }
            else if (c == '"' && depth == 1)
            {
                int nameEnd = text.IndexOf('"', p + 1);
                if (nameEnd < 0) break;
                string name = text.Substring(p + 1, nameEnd - p - 1);
                int braceOpen = text.IndexOf('{', nameEnd);
                if (braceOpen < 0) break;
                int d2 = 0, q = braceOpen;
                while (q < text.Length)
                {
                    if (text[q] == '{') d2++;
                    else if (text[q] == '}') { d2--; if (d2 == 0) break; }
                    q++;
                }
                yield return (name, text.Substring(braceOpen, q - braceOpen + 1));
                p = q;
            }
            p++;
        }
    }
}
