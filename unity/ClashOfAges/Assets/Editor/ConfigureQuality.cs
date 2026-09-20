using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Quality configuration for the two targets we actually ship to:
///   * discrete NVIDIA (RTX 3060 floor, RTX 4070 target)
///   * Apple silicon MacBook Pro (M1 Pro floor, M4 Pro is the dev machine)
/// Integrated graphics are explicitly NOT a target, which is why MSAA is off, shadows
/// are 4096 with 4 cascades, and HDR + post-processing are always on.
///
///     unity run &lt;project&gt; --execute-method ConfigureQuality.Apply
/// </summary>
public static class ConfigureQuality
{
    const string PCAsset = "Assets/Settings/PC_RPAsset.asset";

    [MenuItem("Clash of Ages/Configure quality (desktop, discrete GPU)")]
    public static void Apply()
    {
        var rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PCAsset);
        if (rp == null) { Debug.LogError("[quality] " + PCAsset + " not found"); return; }

        var so = new SerializedObject(rp);

        // --- shadows -----------------------------------------------------------
        // doc 11 / DL15: Max Distance sets shadow pixel DENSITY, and is driven by the
        // camera's 18-90 m zoom band, never by the 240-640 m map extents. At 50 deg
        // pitch a 90 m height is ~117 m of view distance; 150 m covers it with margin.
        Set(so, "m_ShadowDistance", 150f);
        Set(so, "m_ShadowCascadeCount", 4);
        Set(so, "m_Cascade4Split", new Vector3(0.05f, 0.15f, 0.40f));
        Set(so, "m_CascadeBorder", 0.15f);          // cascade blending, hides the seams
        Set(so, "m_MainLightShadowmapResolution", 4096);
        Set(so, "m_SoftShadowsSupported", true);
        Set(so, "m_SoftShadowQuality", 2);          // High
        Set(so, "m_MainLightShadowsSupported", true);
        Set(so, "m_AdditionalLightShadowsSupported", true);
        Set(so, "m_AdditionalLightsShadowmapResolution", 2048);

        // --- image quality ------------------------------------------------------
        // DL19: MSAA is the MOST expensive AA in URP on desktop, cannot combine with
        // TAA, and fixes geometric edges only -- it will not stop grass shimmer. Off.
        // AA is chosen per-camera (SMAA now, TAA once there is motion to test it).
        Set(so, "m_MSAA", 1);                       // 1 = disabled
        Set(so, "m_SupportsHDR", true);
        Set(so, "m_RenderScale", 1.0f);
        Set(so, "m_ColorGradingMode", 1);           // High Dynamic Range grading
        Set(so, "m_ColorGradingLutSize", 32);
        Set(so, "m_UseSRPBatcher", true);
        Set(so, "m_SupportsDynamicBatching", false);   // SRP Batcher supersedes it
        Set(so, "m_OpaqueDownsampling", 0);
        Set(so, "m_RequireDepthTexture", true);
        Set(so, "m_RequireOpaqueTexture", false);

        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(rp);
        AssetDatabase.SaveAssets();

        Debug.Log("[quality] PC_RPAsset configured: shadows 4096/4 cascades/150 m, " +
                  "MSAA off, HDR on, SRP Batcher on, HDR grading");
    }

    static void Set(SerializedObject so, string prop, float v)
    {
        var p = so.FindProperty(prop);
        if (p == null) { Debug.LogWarning("[quality] no property " + prop); return; }
        p.floatValue = v;
    }
    static void Set(SerializedObject so, string prop, int v)
    {
        var p = so.FindProperty(prop);
        if (p == null) { Debug.LogWarning("[quality] no property " + prop); return; }
        p.intValue = v;
    }
    static void Set(SerializedObject so, string prop, bool v)
    {
        var p = so.FindProperty(prop);
        if (p == null) { Debug.LogWarning("[quality] no property " + prop); return; }
        p.boolValue = v;
    }
    static void Set(SerializedObject so, string prop, Vector3 v)
    {
        var p = so.FindProperty(prop);
        if (p == null) { Debug.LogWarning("[quality] no property " + prop); return; }
        p.vector3Value = v;
    }
}
