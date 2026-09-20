using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>Shared scene-generation pieces: the sun, the post stack, water, and a capture that works.</summary>
public static class SceneKit
{
    /// <summary>DL14: one fully realtime directional sun. Values per docs/11-lighting.html, Age I mood.</summary>
    public static Light MakeSun()
    {
        var go = new GameObject("Sun");
        var sun = go.AddComponent<Light>();
        sun.type = LightType.Directional;
        sun.lightmapBakeType = LightmapBakeType.Realtime;
        sun.shadows = LightShadows.Soft;
        sun.intensity = 1.45f;
        sun.color = new Color(1.00f, 0.945f, 0.85f);
        go.transform.rotation = Quaternion.Euler(34f, 40f, 0f);
        var data = go.AddComponent<UniversalAdditionalLightData>();
        data.usePipelineSettings = false;            // URP 17: bias itself lives on the Light
        sun.shadowBias = 0.03f;
        sun.shadowNormalBias = 0.9f;
        sun.shadowNearPlane = 0.2f;
        sun.shadowStrength = 0.80f;               // full-strength shadows read as holes in a stylised palette

        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.30f, 0.36f, 0.46f);
        RenderSettings.ambientEquatorColor = new Color(0.22f, 0.23f, 0.21f);
        RenderSettings.ambientGroundColor = new Color(0.10f, 0.09f, 0.07f);
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogColor = new Color(0.62f, 0.70f, 0.78f);
        RenderSettings.fogStartDistance = 90f;
        RenderSettings.fogEndDistance = 420f;
        return sun;
    }

    /// <summary>Neutral tonemapping: ACES crushes saturated colour, which is what a flat palette is made of.</summary>
    public static Volume MakeVolume(string profilePath)
    {
        var go = new GameObject("Global Volume");
        var vol = go.AddComponent<Volume>();
        vol.isGlobal = true;
        var profile = ScriptableObject.CreateInstance<VolumeProfile>();
        var tm = profile.Add<Tonemapping>(true); tm.mode.overrideState = true; tm.mode.value = TonemappingMode.Neutral;
        var ca = profile.Add<ColorAdjustments>(true);
        ca.postExposure.overrideState = true; ca.postExposure.value = 0.15f;
        ca.contrast.overrideState = true; ca.contrast.value = 12f;
        ca.saturation.overrideState = true; ca.saturation.value = 14f;
        var bl = profile.Add<Bloom>(true);
        bl.threshold.overrideState = true; bl.threshold.value = 1.05f;
        bl.intensity.overrideState = true; bl.intensity.value = 0.4f;
        bl.scatter.overrideState = true; bl.scatter.value = 0.62f;
        var vg = profile.Add<Vignette>(true);
        vg.intensity.overrideState = true; vg.intensity.value = 0.22f;
        vg.smoothness.overrideState = true; vg.smoothness.value = 0.5f;
        AssetDatabase.DeleteAsset(profilePath);
        AssetDatabase.CreateAsset(profile, profilePath);
        foreach (var c in profile.components) AssetDatabase.AddObjectToAsset(c, profile);
        AssetDatabase.SaveAssets();
        vol.sharedProfile = profile;
        return vol;
    }

    /// <summary>
    /// Force every Blender model to re-resolve its materials from palette.json. An FBX that already
    /// stores a material remap never calls OnAssignMaterialModel again, so a material that came out
    /// wrong once (magenta, because the palette lacked it) stays wrong until the remap is cleared.
    /// </summary>
    [MenuItem("Clash of Ages/Palette - Refresh all models")]
    public static void RefreshModels()
    {
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Models", "Assets/World" }))
        {
            var p = AssetDatabase.GUIDToAssetPath(guid);
            if (!(AssetImporter.GetAtPath(p) is ModelImporter imp)) continue;
            foreach (var kv in imp.GetExternalObjectMap())
                if (kv.Key.type == typeof(Material)) imp.RemoveRemap(kv.Key);
            imp.SaveAndReimport();
        }
        PaletteImporter.SyncMaterials();
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
    }

    /// <summary>A saved URP/Lit material. Never `new Material()` without saving: an unsaved one leaked across renderers.</summary>
    public static Material SavedLit(string path, Color baseColor, float smoothness, float metallic = 0f,
                                    Texture baseMap = null, bool transparent = false)
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        bool isNew = mat == null;
        if (isNew) mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        mat.SetColor("_BaseColor", baseColor);
        mat.SetFloat("_Smoothness", smoothness);
        mat.SetFloat("_Metallic", metallic);
        if (baseMap != null) mat.SetTexture("_BaseMap", baseMap);
        if (transparent)
        {
            mat.SetFloat("_Surface", 1f); mat.SetFloat("_Blend", 0f);
            mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0f);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.renderQueue = (int)RenderQueue.Transparent;
        }
        mat.enableInstancing = true;
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        if (isNew) AssetDatabase.CreateAsset(mat, path); else EditorUtility.SetDirty(mat);
        return mat;
    }

    /// <summary>A saved URP/Unlit transparent material, for rings, markers, bars and ghosts.</summary>
    public static Material SavedUnlit(string path, Color color, bool transparent = true)
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        bool isNew = mat == null;
        var shader = Shader.Find("Universal Render Pipeline/Unlit");
        if (isNew) mat = new Material(shader); else mat.shader = shader;
        mat.SetColor("_BaseColor", color);
        if (transparent)
        {
            mat.SetFloat("_Surface", 1f); mat.SetFloat("_Blend", 0f);
            mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0f); mat.SetFloat("_Cull", 0f);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.renderQueue = (int)RenderQueue.Transparent + 10;
        }
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        if (isNew) AssetDatabase.CreateAsset(mat, path); else EditorUtility.SetDirty(mat);
        return mat;
    }

    /// <summary>
    /// Capture a camera to PNG. Three things learned the hard way, all required:
    /// RenderPipeline.SubmitRenderRequest (Camera.Render ignores materials under an SRP);
    /// SRP Batcher off for the capture (it mis-binds per-draw constants in a scripted request);
    /// and the Editor must NOT be in -batchmode (every draw would use one material).
    /// </summary>
    public static bool Capture(Camera cam, int w, int h, string path, System.Action beforeRender = null)
    {
        if (cam == null) return false;
        if (Application.isBatchMode)
            Debug.LogWarning("[capture] -batchmode: the image will be single-material. Re-run in GUI mode.");
        bool batch = GraphicsSettings.useScriptableRenderPipelineBatching;
        GraphicsSettings.useScriptableRenderPipelineBatching = false;
        var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
        try
        {
            beforeRender?.Invoke();
            var req = new UniversalRenderPipeline.SingleCameraRequest { destination = rt };
            if (!RenderPipeline.SupportsRenderRequest(cam, req)) return false;
            RenderPipeline.SubmitRenderRequest(cam, req);
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
            RenderTexture.active = null;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllBytes(path, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            return true;
        }
        finally
        {
            GraphicsSettings.useScriptableRenderPipelineBatching = batch;
            rt.Release();
        }
    }
}
