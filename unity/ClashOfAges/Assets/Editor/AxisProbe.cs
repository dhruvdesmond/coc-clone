using UnityEditor;
using UnityEngine;
/// <summary>Measures the Blender->Unity world axis mapping through the FBX path. Kept as a regression check.</summary>
public static class AxisProbe
{
    public static void Run()
    {
        var go = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/World/axis_probe.fbx");
        var inst = Object.Instantiate(go);
        foreach (var r in inst.GetComponentsInChildren<MeshRenderer>())
        {
            var c = r.bounds.center; var t = r.transform;
            Debug.Log($"AXISPROBE {r.name} world=({c.x:F3},{c.y:F3},{c.z:F3}) localRot={t.localEulerAngles} localScale={t.localScale} lossy={t.lossyScale}");
        }
        Object.DestroyImmediate(inst);
    }
}
