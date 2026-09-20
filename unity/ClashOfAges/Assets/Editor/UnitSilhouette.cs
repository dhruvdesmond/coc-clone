using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>
/// A unit behind a tree or a longhouse vanishes, and an RTS unit you cannot see is one you cannot
/// command. Two URP RenderObjects passes on the "Units" layer fix that:
///
///   1. "Units"           draws the layer normally and writes stencil = 1 wherever a unit is VISIBLE.
///   2. "Occluded Units"  draws it again, flat-tinted, only where depth FAILS and stencil != 1.
///
/// The stencil is the whole point. The first version had no mask, so a unit's own arm -- behind its own
/// torso -- passed the "something is in front of me" test and every figure was covered in pale shards.
/// The layer is removed from the renderer's default opaque mask so pass 1 is the only normal draw.
/// Corpses leave the layer (UnitView), or the ground they sink into would outline them forever.
/// </summary>
public static class UnitSilhouette
{
    public const string LayerName = "Units";
    const string RendererPath = "Assets/Settings/PC_Renderer.asset";

    public static int EnsureLayer()
    {
        int existing = LayerMask.NameToLayer(LayerName);
        if (existing >= 0) return existing;
        var tm = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        var layers = tm.FindProperty("layers");
        for (int i = 8; i < layers.arraySize; i++)
            if (string.IsNullOrEmpty(layers.GetArrayElementAtIndex(i).stringValue))
            {
                layers.GetArrayElementAtIndex(i).stringValue = LayerName;
                tm.ApplyModifiedPropertiesWithoutUndo();
                AssetDatabase.SaveAssets();
                return i;
            }
        Debug.LogError("[silhouette] no free layer slot");
        return 0;
    }

    static RenderObjects Feature(ScriptableRendererData data, string name)
    {
        foreach (var f in data.rendererFeatures) if (f != null && f.name == name) return (RenderObjects)f;
        var feature = ScriptableObject.CreateInstance<RenderObjects>(); feature.name = name;
        AssetDatabase.AddObjectToAsset(feature, data);
        data.rendererFeatures.Add(feature);
        // the renderer keeps a parallel list of local file ids; without it the feature is dropped on reload
        var so = new SerializedObject(data);
        var map = so.FindProperty("m_RendererFeatureMap");
        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feature, out _, out long localId);
        map.arraySize++; map.GetArrayElementAtIndex(map.arraySize - 1).longValue = localId;
        so.ApplyModifiedPropertiesWithoutUndo();
        return feature;
    }

    [MenuItem("Clash of Ages/Configure occluded-unit silhouette")]
    public static void Apply()
    {
        int layer = EnsureLayer();
        var data = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
        if (data == null) { Debug.LogError("[silhouette] " + RendererPath + " not found"); return; }

        data.opaqueLayerMask &= ~(1 << layer);                 // pass 1 below is now the only normal draw of this layer

        var draw = Feature(data, "Units");
        draw.settings.Event = RenderPassEvent.AfterRenderingOpaques;
        draw.settings.filterSettings.RenderQueueType = RenderQueueType.Opaque;
        draw.settings.filterSettings.LayerMask = 1 << layer;
        draw.settings.overrideMaterial = null;
        draw.settings.overrideDepthState = false;
        draw.settings.stencilSettings.overrideStencilState = true;
        draw.settings.stencilSettings.stencilReference = 1;
        draw.settings.stencilSettings.stencilCompareFunction = CompareFunction.Always;
        draw.settings.stencilSettings.passOperation = StencilOp.Replace;
        draw.settings.stencilSettings.failOperation = StencilOp.Keep;
        draw.settings.stencilSettings.zFailOperation = StencilOp.Keep;

        var ghost = Feature(data, "Occluded Units");
        ghost.settings.Event = RenderPassEvent.AfterRenderingOpaques;
        ghost.settings.filterSettings.RenderQueueType = RenderQueueType.Opaque;
        ghost.settings.filterSettings.LayerMask = 1 << layer;
        ghost.settings.overrideMaterial = SceneKit.SavedUnlit("Assets/Materials/UI/Silhouette.mat", new Color(0.78f, 0.92f, 1.0f, 0.42f));
        ghost.settings.overrideDepthState = true;
        ghost.settings.depthCompareFunction = CompareFunction.Greater;   // only where something is in front
        ghost.settings.enableWrite = false;
        ghost.settings.stencilSettings.overrideStencilState = true;
        ghost.settings.stencilSettings.stencilReference = 1;
        ghost.settings.stencilSettings.stencilCompareFunction = CompareFunction.NotEqual;   // ...and no unit is visible there
        ghost.settings.stencilSettings.passOperation = StencilOp.Keep;
        ghost.settings.stencilSettings.failOperation = StencilOp.Keep;
        ghost.settings.stencilSettings.zFailOperation = StencilOp.Keep;

        EditorUtility.SetDirty(draw); EditorUtility.SetDirty(ghost); EditorUtility.SetDirty(data);
        AssetDatabase.SaveAssets();
        Debug.Log("[silhouette] two-pass stencil silhouette configured on layer " + layer);
    }
}
