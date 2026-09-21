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

    /// <summary>The water material (COA/Water) and the tileable ripple map it needs. Both are GENERATED: no image comes from disk.</summary>
    public static Material SavedWater(string matPath, string noisePath)
    {
        var shader = Shader.Find("COA/Water");
        if (shader == null) { Debug.LogError("[water] FAIL shader COA/Water not found"); return SavedLit(matPath, new Color(0.085f, 0.20f, 0.25f, 0.8f), 0.9f, 0f, null, true); }
        var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat == null) { mat = new Material(shader); Directory.CreateDirectory(Path.GetDirectoryName(matPath)); AssetDatabase.CreateAsset(mat, matPath); }
        mat.shader = shader;                                     // the asset used to be URP/Lit; and a saved asset keeps old values otherwise
        mat.SetTexture("_Noise", SavedRippleMap(noisePath, 256));
        mat.renderQueue = (int)RenderQueue.Transparent - 40;
        EditorUtility.SetDirty(mat);
        return mat;
    }

    /// <summary>RG = the surface normal's x/z packed 0..1, B = height. Tileable: every octave's lattice wraps at the edge, so the
    /// map can slide forever with no seam. Linear, mip-mapped (it is seen from 90 m).</summary>
    public static Texture2D SavedRippleMap(string path, int size)
    {
        var h = new float[size * size]; var rng = new System.Random(19);
        float amp = 1f, total = 0f;
        for (int period = 4; period <= 64; period *= 2, amp *= 0.55f)
        {
            var lattice = new float[period * period]; for (int i = 0; i < lattice.Length; i++) lattice[i] = (float)rng.NextDouble();
            float cell = size / (float)period;
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float fx = x / cell, fy = y / cell; int x0 = (int)fx, y0 = (int)fy; float tx = fx - x0, ty = fy - y0;
                    tx = tx * tx * (3f - 2f * tx); ty = ty * ty * (3f - 2f * ty);
                    int x1 = (x0 + 1) % period, y1 = (y0 + 1) % period; x0 %= period; y0 %= period;
                    float a = Mathf.Lerp(lattice[y0 * period + x0], lattice[y0 * period + x1], tx), b = Mathf.Lerp(lattice[y1 * period + x0], lattice[y1 * period + x1], tx);
                    h[y * size + x] += Mathf.Lerp(a, b, ty) * amp;
                }
            total += amp;
        }
        var px = new Color[size * size];
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float H(int xx, int yy) => h[((yy + size) % size) * size + ((xx + size) % size)] / total;
                float dx = (H(x + 1, y) - H(x - 1, y)) * 6f, dy = (H(x, y + 1) - H(x, y - 1)) * 6f;
                px[y * size + x] = new Color(Mathf.Clamp01(dx * 0.5f + 0.5f), Mathf.Clamp01(dy * 0.5f + 0.5f), H(x, y), 1f);
            }
        // stretch the height channel to the full 0..1: the shader thresholds it, and raw fbm huddles around 0.5
        float lo = 1f, hi = 0f; foreach (var c in px) { lo = Mathf.Min(lo, c.b); hi = Mathf.Max(hi, c.b); }
        for (int i = 0; i < px.Length; i++) px[i].b = Mathf.InverseLerp(lo, hi, px[i].b);

        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        bool isNew = tex == null || tex.width != size;
        if (isNew) tex = new Texture2D(size, size, TextureFormat.RGBA32, true, true);
        tex.wrapMode = TextureWrapMode.Repeat; tex.filterMode = FilterMode.Trilinear; tex.anisoLevel = 4;
        tex.SetPixels(px); tex.Apply(true, false);
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        if (isNew) { AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(tex, path); } else EditorUtility.SetDirty(tex);
        return tex;
    }

    /// <summary>A flat XZ grid centred on the origin, facing up.</summary>
    public static Mesh SavedGrid(string path, float sizeX, float sizeZ, float cell)
    {
        int nx = Mathf.CeilToInt(sizeX / cell), nz = Mathf.CeilToInt(sizeZ / cell);
        var v = new Vector3[(nx + 1) * (nz + 1)]; var tri = new int[nx * nz * 6];
        for (int z = 0; z <= nz; z++)
            for (int x = 0; x <= nx; x++) v[z * (nx + 1) + x] = new Vector3(-sizeX * 0.5f + x * sizeX / nx, 0f, -sizeZ * 0.5f + z * sizeZ / nz);
        for (int z = 0, t = 0; z < nz; z++)
            for (int x = 0; x < nx; x++)
            {
                int i = z * (nx + 1) + x;
                tri[t++] = i; tri[t++] = i + nx + 1; tri[t++] = i + 1; tri[t++] = i + 1; tri[t++] = i + nx + 1; tri[t++] = i + nx + 2;
            }
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        bool isNew = mesh == null; if (isNew) mesh = new Mesh(); else mesh.Clear();
        mesh.name = "water_grid"; mesh.indexFormat = v.Length > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16;
        mesh.vertices = v; mesh.triangles = tri; mesh.RecalculateNormals();
        var bounds = mesh.bounds; bounds.Expand(new Vector3(0f, 1f, 0f)); mesh.bounds = bounds;       // the swell moves vertices in the shader
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        if (isNew) AssetDatabase.CreateAsset(mesh, path); else EditorUtility.SetDirty(mesh);
        Debug.Log($"[water] grid {nx} x {nz} cells, {v.Length} vertices, {sizeX:F0} x {sizeZ:F0} m");
        return mesh;
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
