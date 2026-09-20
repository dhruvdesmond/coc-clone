using System.IO;
using COA.Game;
using Unity.AI.Navigation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Generates the demo scene from nothing. The scene is a BUILD ARTIFACT: never hand-edit it,
/// change this file. Builder regenerates it before every player build.
/// </summary>
public static class DemoSceneBuilder
{
    public const string ScenePath = "Assets/Scenes/Demo.unity";
    const string World = "Assets/World/";

    [MenuItem("Clash of Ages/Demo - Build scene")]
    public static void Build()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        SceneKit.MakeSun();
        SceneKit.MakeVolume("Assets/Settings/DemoProfile.asset");

        // ---- terrain: one mesh, one baked 4K albedo (biome blend + worn paths are in the pixels)
        var terrainPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(World + "terrain.fbx");
        var albedo = AssetDatabase.LoadAssetAtPath<Texture2D>(World + "terrain_albedo.png");
        if (terrainPrefab == null || albedo == null) { Debug.LogError("[demo] terrain assets missing"); return; }
        var terrain = (GameObject)PrefabUtility.InstantiatePrefab(terrainPrefab);
        terrain.name = "Terrain";
        var tmat = SceneKit.SavedLit("Assets/Materials/Terrain.mat", Color.white, 0.06f, 0f, albedo);
        var tb = new Bounds();
        bool first = true;
        foreach (var mr in terrain.GetComponentsInChildren<MeshRenderer>())
        {
            var mats = mr.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = tmat;
            mr.sharedMaterials = mats;
            mr.gameObject.AddComponent<MeshCollider>().sharedMesh = mr.GetComponent<MeshFilter>().sharedMesh;
            mr.gameObject.layer = LayerMask.NameToLayer("Default");
            if (first) { tb = mr.bounds; first = false; } else tb.Encapsulate(mr.bounds);
        }
        Debug.Log($"[demo] terrain bounds {tb.size.x:F3} x {tb.size.y:F3} x {tb.size.z:F3} m, centre {tb.center}");

        // ---- water
        var water = GameObject.CreatePrimitive(PrimitiveType.Plane);
        water.name = "Water";
        Object.DestroyImmediate(water.GetComponent<Collider>());
        water.transform.position = new Vector3(0f, -0.03f, 0f);
        water.transform.localScale = new Vector3(30f, 1f, 30f);
        water.GetComponent<MeshRenderer>().sharedMaterial =
            SceneKit.SavedLit("Assets/Materials/Water.mat", new Color(0.085f, 0.20f, 0.25f, 0.80f), 0.93f, 0.05f, null, true);
        water.GetComponent<MeshRenderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

        // ---- instanced world
        var wgo = new GameObject("InstancedWorld");
        var iw = wgo.AddComponent<InstancedWorld>();
        iw.data = AssetDatabase.LoadAssetAtPath<TextAsset>(World + "world.bytes");
        iw.meshesPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(World + "world_meshes.fbx");
        if (iw.data == null || iw.meshesPrefab == null) Debug.LogError("[demo] world.bytes / world_meshes.fbx missing");

        // ---- camera
        var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
        var cam = camGo.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.62f, 0.70f, 0.78f);
        cam.fieldOfView = 40f; cam.nearClipPlane = 0.5f; cam.farClipPlane = 600f;
        var cd = camGo.AddComponent<UniversalAdditionalCameraData>();
        cd.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;   // DL19: not MSAA
        cd.antialiasingQuality = AntialiasingQuality.High;
        cd.renderPostProcessing = true;
        camGo.AddComponent<AudioListener>();
        var rig = camGo.AddComponent<RTSCamera>();
        rig.mapSize = new Vector2(tb.size.x, tb.size.z);
        rig.minHeight = 9f; rig.maxHeight = 70f; rig.height = 32f;
        var rot = Quaternion.Euler(rig.pitch, rig.yaw, 0f);
        camGo.transform.SetPositionAndRotation(-(rot * Vector3.forward) * (rig.height / Mathf.Sin(rig.pitch * Mathf.Deg2Rad)), rot);

        // ---- navmesh: terrain collider in, lake bed out
        var nav = new GameObject("NavMesh");
        var surface = nav.AddComponent<NavMeshSurface>();
        surface.collectObjects = CollectObjects.All;
        surface.useGeometry = NavMeshCollectGeometry.PhysicsColliders;
        var wet = new GameObject("NotWalkable_Underwater").AddComponent<NavMeshModifierVolume>();
        wet.transform.SetParent(nav.transform);
        wet.center = new Vector3(0f, -10.12f, 0f);
        wet.size = new Vector3(400f, 20f, 400f);            // top face at y = -0.12
        wet.area = 1;                                        // Not Walkable
        surface.BuildNavMesh();
        AssetDatabase.DeleteAsset(World + "NavMesh.asset");
        AssetDatabase.CreateAsset(surface.navMeshData, World + "NavMesh.asset");
        var tri = NavMesh.CalculateTriangulation();
        Debug.Log($"[demo] navmesh {tri.indices.Length / 3} triangles");

        Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        Debug.Log("[demo] scene written to " + ScenePath);
    }

    /// <summary>Phase 1 check: three captures of the land. GUI mode only.</summary>
    public static void CaptureLand()
    {
        SceneKit.RefreshModels();
        Build();
        var cam = Camera.main;
        var iw = Object.FindFirstObjectByType<InstancedWorld>();
        Shot(cam, iw, new Vector3(0, 0, 0), 30f, 50f, 70f, "land_wide.png");
        Shot(cam, iw, new Vector3(-8f, 0, 6f), 120f, 38f, 24f, "land_mid.png");
        Shot(cam, iw, new Vector3(10f, 0, -12f), 210f, 30f, 11f, "land_close.png");
        Debug.Log($"[demo] chunks {iw.ChunkCount} drawn {iw.LastDrawnInstances} instances in {iw.LastDrawCalls} draw calls");
        Debug.Log("DEMO_CAPTURE done");
    }

    static void Shot(Camera cam, InstancedWorld iw, Vector3 focus, float yaw, float pitch, float height, string file)
    {
        var rot = Quaternion.Euler(pitch, yaw, 0f);
        cam.transform.SetPositionAndRotation(focus - rot * Vector3.forward * (height / Mathf.Sin(pitch * Mathf.Deg2Rad)), rot);
        bool ok = SceneKit.Capture(cam, 2048, 1152, "Verification/" + file, () => iw.Render(cam));
        Debug.Log("[demo] " + file + (ok ? " ok" : " FAILED"));
    }
}
