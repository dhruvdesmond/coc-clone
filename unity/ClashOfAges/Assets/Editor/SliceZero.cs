using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Slice 0 -- prove the Blender to Unity bridge before building a second asset.
///
/// Builds a verification scene from nothing, renders it to PNG, and asserts the things
/// that have silently broken before: scale, material mapping, renderer count, tone.
///
///     unity run &lt;project&gt; --execute-method SliceZero.Verify
///
/// Every expectation is read from the sidecar Blender wrote. Hardcoding them here would
/// be a second table of the same fact, which is precisely how the palette drifted.
/// </summary>
public static class SliceZero
{
    const string SceneDir  = "Assets/Scenes";
    const string ScenePath = SceneDir + "/SliceZero.unity";
    const string Sidecar   = "Assets/Models/hut_a.meta.json.txt";
    const string Fbx       = "Assets/Models/hut_a.fbx";
    const string ShotDir   = "Verification";

    [MenuItem("Clash of Ages/Slice 0 - Build verification scene")]
    public static void BuildScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // ---- sun -----------------------------------------------------------
        // DL14: one fully realtime directional sun. Shadowmask needs a static
        // GameObject and our ground cover has none, so it can never be shadowmasked.
        var sunGo = new GameObject("Sun");
        var sun = sunGo.AddComponent<Light>();
        sun.type             = LightType.Directional;
        sun.lightmapBakeType = LightmapBakeType.Realtime;
        sun.shadows          = LightShadows.Soft;
        sun.intensity        = 1.35f;
        sun.color            = new Color(1.00f, 0.957f, 0.878f);   // Age I: warm low gold
        sunGo.transform.rotation = Quaternion.Euler(28f, 35f, 0f); // 28 deg elevation

        // URP 17: usePipelineSettings=false puts this light on Custom bias; the values
        // themselves live on the Light component, not on the additional data.
        var sunData = sunGo.AddComponent<UniversalAdditionalLightData>();
        sunData.usePipelineSettings = false;
        sun.shadowBias       = 0.03f;   // doc 11: verified range 0.02-0.05
        sun.shadowNormalBias = 0.9f;    // doc 11: verified range 0.5-1.5
        sun.shadowNearPlane  = 0.2f;

        RenderSettings.ambientMode         = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor     = new Color(0.26f, 0.31f, 0.40f);
        RenderSettings.ambientEquatorColor = new Color(0.18f, 0.19f, 0.18f);
        RenderSettings.ambientGroundColor  = new Color(0.09f, 0.08f, 0.07f);
        RenderSettings.fog = false;

        // ---- post-processing -------------------------------------------------
        // Without tonemapping the render clipped to white: a 0.35 base colour under a
        // bright sun exceeds 1.0 and there is nothing to roll it off. Neutral is the
        // right default for a stylized palette -- ACES crushes saturated colour, which
        // is exactly what these flat kit materials are made of.
        var volGo = new GameObject("Global Volume");
        var vol = volGo.AddComponent<Volume>();
        vol.isGlobal = true;
        vol.priority = 0f;
        var profile = ScriptableObject.CreateInstance<VolumeProfile>();
        profile.name = "SliceZeroProfile";

        var tm = profile.Add<UnityEngine.Rendering.Universal.Tonemapping>(true);
        tm.mode.overrideState = true;
        tm.mode.value = TonemappingMode.Neutral;

        var ca = profile.Add<UnityEngine.Rendering.Universal.ColorAdjustments>(true);
        ca.postExposure.overrideState = true; ca.postExposure.value = 0.0f;
        ca.contrast.overrideState     = true; ca.contrast.value     = 8f;
        ca.saturation.overrideState   = true; ca.saturation.value   = 6f;

        var bl = profile.Add<UnityEngine.Rendering.Universal.Bloom>(true);
        bl.threshold.overrideState = true; bl.threshold.value = 1.1f;
        bl.intensity.overrideState = true; bl.intensity.value = 0.35f;
        bl.scatter.overrideState   = true; bl.scatter.value   = 0.6f;

        AssetDatabase.CreateAsset(profile, "Assets/Settings/SliceZeroProfile.asset");
        vol.sharedProfile = profile;

        // ---- ground --------------------------------------------------------
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.localScale = new Vector3(4f, 1f, 4f);      // 40 x 40 m
        var gmat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Materials/Generated/GroundGrass.mat");
        if (gmat != null) ground.GetComponent<MeshRenderer>().sharedMaterial = gmat;

        // ---- the asset under test -------------------------------------------
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
        if (fbx == null) { Debug.LogError("[slice0] " + Fbx + " not found"); return; }
        var hut = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        hut.name = "hut_a";
        hut.transform.position = Vector3.zero;

        // ---- a 1 m reference cube. DL17: 1 Unity unit = 1 metre ---------------
        var refCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        refCube.name = "ONE_METRE_REFERENCE";
        refCube.transform.position   = new Vector3(5f, 0.5f, 0f);
        refCube.transform.localScale = Vector3.one;

        // ---- camera: the shipping RTS framing, 50 deg pitch --------------------
        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        var cam = camGo.AddComponent<Camera>();
        cam.clearFlags      = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.36f, 0.45f, 0.55f);
        cam.fieldOfView     = 45f;
        cam.nearClipPlane   = 0.3f;
        cam.farClipPlane    = 400f;
        var rot = Quaternion.Euler(50f, 30f, 0f);
        camGo.transform.SetPositionAndRotation(rot * new Vector3(0, 0, -20f), rot);
        var camData = camGo.AddComponent<UniversalAdditionalCameraData>();
        camData.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
        camData.antialiasingQuality = AntialiasingQuality.High;
        camData.renderPostProcessing = true;
        camGo.AddComponent<RTSCamera>();
        camGo.AddComponent<ScrollProbe>();

        Directory.CreateDirectory(SceneDir);
        EditorSceneManager.SaveScene(scene, ScenePath);
        Debug.Log("[slice0] scene written to " + ScenePath);
    }

    /// <summary>
    /// Delete the generated materials and clear every model's material remap, so the
    /// importer is forced to rebuild them from palette.json.
    ///
    /// WHY THIS IS NEEDED: OnAssignMaterialModel only fires when Unity actually needs to
    /// resolve a material. Once an FBX has a remap stored in its .meta pointing at an
    /// existing .mat, the callback is skipped entirely -- so materials created during a
    /// failed import (magenta, because the palette had not loaded yet) stay magenta
    /// forever, even after the palette is fixed. Clearing the remap is the only way to
    /// make the palette authoritative again.
    /// </summary>
    [MenuItem("Clash of Ages/Palette - Regenerate all materials")]
    public static void RegenerateMaterials()
    {
        const string genDir = "Assets/Materials/Generated";
        if (AssetDatabase.IsValidFolder(genDir))
        {
            AssetDatabase.DeleteAsset(genDir);
            Debug.Log("[slice0] deleted " + genDir);
        }
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Models" }))
        {
            var p = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(p) as ModelImporter;
            if (imp == null) continue;
            foreach (var kv in imp.GetExternalObjectMap())
                if (kv.Key.type == typeof(Material)) imp.RemoveRemap(kv.Key);
            imp.SaveAndReimport();
            Debug.Log("[slice0] cleared material remap and reimported " + p);
        }
        AssetDatabase.Refresh();
    }

    [MenuItem("Clash of Ages/Slice 0 - Verify (render + assert)")]
    public static void Verify()
    {
        var log = new StringBuilder();
        int fail = 0;
        void Check(bool ok, string what, string detail)
        {
            log.AppendLine("  [" + (ok ? "PASS" : "FAIL") + "] " + what + "  " + detail);
            if (!ok) fail++;
        }

        RegenerateMaterials();
        AssetDatabase.ImportAsset(Fbx, ImportAssetOptions.ForceUpdate);
        AssetDatabase.Refresh();
        BuildScene();   // leaves the scene open; do NOT reopen from disk

        log.AppendLine("\n================ SLICE 0 VERIFICATION ================");

        // ---- expectations from the sidecar, not from this file -----------------
        string side = File.ReadAllText(Sidecar);
        float ex = J(side, "\"x\""), ey = J(side, "\"y\""), ez = J(side, "\"z\"");
        int expectTris = (int)J(side, "\"triangles\"");
        int expectObjs = (int)J(side, "\"sourceObjects\"");
        log.AppendLine("  sidecar says: " + ex.ToString("F3") + " x " + ey.ToString("F3")
            + " x " + ez.ToString("F3") + " m, " + expectTris + " tris, "
            + expectObjs + " source objects");

        var hut = GameObject.Find("hut_a");
        var rends = hut != null ? hut.GetComponentsInChildren<MeshRenderer>()
                                : new MeshRenderer[0];
        var b = new Bounds();
        if (rends.Length > 0)
        {
            b = rends[0].bounds;
            foreach (var r in rends) b.Encapsulate(r.bounds);
        }

        // Blender Z-up -> Unity Y-up: Blender (x,y,z) becomes Unity (x,z,y)
        Check(Mathf.Abs(b.size.x - ex) < 0.15f, "width    ",
              b.size.x.ToString("F3") + " m (expect " + ex.ToString("F3") + ")");
        Check(Mathf.Abs(b.size.z - ey) < 0.15f, "depth    ",
              b.size.z.ToString("F3") + " m (expect " + ey.ToString("F3") + ")");
        Check(Mathf.Abs(b.size.y - ez) < 0.15f, "height   ",
              b.size.y.ToString("F3") + " m (expect " + ez.ToString("F3") + ")");

        int tris = 0, verts = 0, submeshes = 0;
        foreach (var mf in hut.GetComponentsInChildren<MeshFilter>())
            if (mf.sharedMesh != null)
            {
                tris      += mf.sharedMesh.triangles.Length / 3;
                verts     += mf.sharedMesh.vertexCount;
                submeshes += mf.sharedMesh.subMeshCount;
            }

        Check(rends.Length == 1, "renderers",
              rends.Length + " (expect 1 - " + expectObjs + " Blender objects joined)");
        Check(tris == expectTris, "triangles",
              tris + " verts " + verts + " (expect " + expectTris + ")");
        Check(submeshes == 6, "submeshes", submeshes + " (expect 6)");

        // ---- materials mapped, none magenta ------------------------------------
        int magenta = 0, mapped = 0;
        var names = new StringBuilder();
        foreach (var r in rends)
            foreach (var m in r.sharedMaterials)
            {
                if (m == null) { magenta++; continue; }
                var c = m.GetColor("_BaseColor");
                if (c.r > 0.9f && c.g < 0.1f && c.b > 0.9f) magenta++; else mapped++;
                names.Append(m.name + "(" + c.r.ToString("F2") + ","
                    + c.g.ToString("F2") + "," + c.b.ToString("F2") + ") ");
            }
        Check(magenta == 0, "materials", mapped + " mapped, " + magenta + " magenta");
        log.AppendLine("         " + names);

        // ---- tone correction actually applied ------------------------------------
        var timber = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Materials/Generated/Timber.mat");
        if (timber != null)
        {
            var c = timber.GetColor("_BaseColor");
            // raw linear 0.183 -> pow(.,0.62) = 0.349. Untoned would still read 0.183.
            Check(Mathf.Abs(c.r - 0.349f) < 0.02f, "tone     ",
                  "Timber base R=" + c.r.ToString("F3") + " (expect 0.349 toned, 0.183 raw)");
        }
        else Check(false, "tone     ", "Timber.mat was not generated");

        // ---- what is ACTUALLY bound at render time --------------------------------
        foreach (var r in rends)
        {
            var sm = r.sharedMaterials;
            for (int i = 0; i < sm.Length; i++)
            {
                var m = sm[i];
                log.AppendLine("         bound[" + i + "] "
                    + (m == null ? "NULL" : m.name
                        + " shader=" + (m.shader == null ? "NULL" : m.shader.name)
                        + " _BaseColor=" + m.GetColor("_BaseColor")
                        + " hasProp=" + m.HasProperty("_BaseColor")
                        + " path=" + AssetDatabase.GetAssetPath(m)));
            }
        }
        log.AppendLine("         active RP = " + (GraphicsSettings.currentRenderPipeline == null
            ? "NULL (built-in!)" : GraphicsSettings.currentRenderPipeline.name));
        log.AppendLine("         QualityLevel = " + QualitySettings.GetQualityLevel()
            + " " + QualitySettings.names[QualitySettings.GetQualityLevel()]);

        // ---- render it, so a human can LOOK at it ---------------------------------
        Directory.CreateDirectory(ShotDir);
        string shotPath = Path.Combine(ShotDir, "slice0.png");
        bool shot = RenderShot(2048, 1152, shotPath);
        Check(shot, "render   ", Path.GetFullPath(shotPath));

        log.AppendLine("================ "
            + (fail == 0 ? "ALL PASS" : fail + " FAILURE(S)") + " ================\n");
        Debug.Log(log.ToString());
        Debug.Log("SLICE0_RESULT " + (fail == 0 ? "PASS" : "FAIL:" + fail));
    }

    /// <summary>Pull one number out of the generated sidecar. Tiny on purpose.</summary>
    static float J(string s, string key)
    {
        int i = s.IndexOf(key, System.StringComparison.Ordinal);
        if (i < 0) return -1f;
        i = s.IndexOf(':', i + key.Length);
        if (i < 0) return -1f;
        int j = i + 1;
        while (j < s.Length && char.IsWhiteSpace(s[j])) j++;
        int k = j;
        while (k < s.Length && (char.IsDigit(s[k]) || s[k] == '.' || s[k] == '-')) k++;
        return float.TryParse(s.Substring(j, k - j), NumberStyles.Float,
                              CultureInfo.InvariantCulture, out var f) ? f : -1f;
    }

    static bool RenderShot(int w, int h, string path)
    {
        var cam = Camera.main;
        if (cam == null) return false;

        // MUST NOT run under -batchmode. In batchmode this renders correct geometry and
        // correct shadows but binds ONE material for every draw -- a pure red control
        // quad turned the entire scene red, and without it everything came out default
        // grey. Disabling the SRP Batcher does not help. Run the Editor in GUI mode.
        if (Application.isBatchMode)
            Debug.LogWarning("[slice0] running under -batchmode: the PNG will be a "
                + "single-material grey. Asset assertions above are still valid. "
                + "Re-run WITHOUT -batchmode to get a usable image.");

        // The SRP Batcher mis-binds per-draw constants during a scripted render
        // request: with it ON the capture comes out dark and flat, with it OFF the
        // materials and lighting are correct. Two GUI runs differing by ONLY this flag
        // is what isolated it. Off for the capture; ConfigureQuality leaves it ON for
        // the player, where the normal render loop is fine.
        bool srpBatch = GraphicsSettings.useScriptableRenderPipelineBatching;
        GraphicsSettings.useScriptableRenderPipelineBatching = false;
        try
        {
        var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32,
                                   RenderTextureReadWrite.sRGB)
        {
            antiAliasing = 1,   // AA comes from SMAA in the pipeline, not from the RT
        };
        rt.Create();

        // Camera.Render() is NOT supported under a Scriptable Render Pipeline. It runs,
        // produces geometry and shadows, and silently ignores materials -- a pure red
        // control quad came out grey. Unity 6 URP wants a render REQUEST instead.
        var request = new UniversalRenderPipeline.SingleCameraRequest { destination = rt };
        if (RenderPipeline.SupportsRenderRequest(cam, request))
        {
            RenderPipeline.SubmitRenderRequest(cam, request);
        }
        else
        {
            Debug.LogWarning("[slice0] SingleCameraRequest unsupported; " +
                             "falling back to Camera.Render() -- colours will be WRONG.");
            cam.targetTexture = rt;
            cam.Render();
        }
        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        cam.targetTexture = null;
        File.WriteAllBytes(path, tex.EncodeToPNG());
        Object.DestroyImmediate(tex);
        rt.Release();
        return File.Exists(path) && new FileInfo(path).Length > 4096;
        }
        finally
        {
            GraphicsSettings.useScriptableRenderPipelineBatching = srpBatch;
        }
    }
}
