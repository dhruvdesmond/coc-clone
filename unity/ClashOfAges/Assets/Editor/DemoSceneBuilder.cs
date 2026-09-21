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
        UnitSilhouette.EnsureLayer();
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
        // A grid, not Unity's Plane: scaled to this size the primitive's vertices are 30 m apart and a vertex swell does nothing.
        var water = new GameObject("Water");
        water.transform.position = new Vector3(0f, COA.Game.WaterSurface.Level, 0f);
        water.AddComponent<MeshFilter>().sharedMesh = SceneKit.SavedGrid("Assets/World/water_grid.asset", tb.size.x + 120f, tb.size.z + 120f, 2f);
        var wmr = water.AddComponent<MeshRenderer>();
        wmr.sharedMaterial = SceneKit.SavedWater("Assets/Materials/Water.mat", "Assets/Materials/WaterNoise.asset");
        wmr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; wmr.receiveShadows = true;
        water.AddComponent<COA.Game.WaterSurface>();

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
        rig.minHeight = 8f; rig.maxHeight = 70f; rig.height = 24f;
        var rot = Quaternion.Euler(rig.pitch, rig.yaw, 0f);
        camGo.transform.SetPositionAndRotation(-(rot * Vector3.forward) * (rig.height / Mathf.Sin(rig.pitch * Mathf.Deg2Rad)), rot);

        // ---- navmesh: terrain collider in, lake bed out
        var nav = new GameObject("NavMesh");
        var surface = nav.AddComponent<NavMeshSurface>();
        surface.collectObjects = CollectObjects.All;
        surface.useGeometry = NavMeshCollectGeometry.PhysicsColliders;
        var wet = new GameObject("NotWalkable_Underwater").AddComponent<NavMeshModifierVolume>();
        wet.transform.SetParent(nav.transform);
        wet.center = new Vector3(0f, -9.98f, 0f);
        wet.size = new Vector3(400f, 20f, 400f);            // top face at y = +0.02: raiders were wading the lake shallows
        wet.area = 1;                                        // Not Walkable
        surface.BuildNavMesh();
        AssetDatabase.DeleteAsset(World + "NavMesh.asset");
        AssetDatabase.CreateAsset(surface.navMeshData, World + "NavMesh.asset");
        var tri = NavMesh.CalculateTriangulation();
        Debug.Log($"[demo] navmesh {tri.indices.Length / 3} triangles");

        // ---- game: model library, root, autopilot
        var lib = new GameObject("ModelLibrary").AddComponent<ModelLibrary>();
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Models" }))
        {
            var p = AssetDatabase.GUIDToAssetPath(guid);
            lib.names.Add(Path.GetFileNameWithoutExtension(p));
            lib.prefabs.Add(AssetDatabase.LoadAssetAtPath<GameObject>(p));
        }
        // Catalog.half is a second copy of the model's size, so it is ASSERTED against the first: the sidecar Blender wrote.
        foreach (var d in COA.Sim.Catalog.Buildings.Values)
        {
            var side = "Assets/Models/" + d.model + ".meta.json.txt";
            if (!System.IO.File.Exists(side)) { Debug.LogError("[footprint] FAIL no sidecar for " + d.model); continue; }
            var m = System.Text.RegularExpressions.Regex.Match(System.IO.File.ReadAllText(side), @"""x"":\s*([\d.]+),\s*""y"":\s*([\d.]+)");
            float sx = float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture), sy = float.Parse(m.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture);
            bool ok = Mathf.Abs(d.half.x * 2f - sx) < sx * 0.06f && Mathf.Abs(d.half.z * 2f - sy) < sy * 0.06f;
            if (ok) Debug.Log($"[footprint] {d.name}: {d.half.x * 2f:F2} x {d.half.z * 2f:F2} m matches {d.model} ({sx:F2} x {sy:F2})");
            else Debug.LogError($"[footprint] FAIL {d.name}: Catalog says {d.half.x * 2f:F2} x {d.half.z * 2f:F2} m but {d.model} measures {sx:F2} x {sy:F2}");
        }
        foreach (var kv in FigureRigSetup.Build()) { lib.controllerNames.Add(kv.Key); lib.controllers.Add(kv.Value); }
        const string U = "Assets/Materials/UI/";
        lib.ring      = SceneKit.SavedUnlit(U + "Ring.mat",      new Color(0.35f, 0.95f, 0.45f, 0.95f));
        lib.ringEnemy = SceneKit.SavedUnlit(U + "RingEnemy.mat", new Color(1.00f, 0.25f, 0.20f, 0.85f));
        lib.teamDisc  = SceneKit.SavedUnlit(U + "TeamDisc.mat",  new Color(0.30f, 0.62f, 1.00f, 0.42f));
        lib.marker    = SceneKit.SavedUnlit(U + "Marker.mat",    new Color(1.00f, 0.85f, 0.30f, 0.95f));
        lib.ghostOk   = SceneKit.SavedUnlit(U + "GhostOk.mat",   new Color(0.35f, 1.00f, 0.50f, 0.45f));
        lib.ghostBad  = SceneKit.SavedUnlit(U + "GhostBad.mat",  new Color(1.00f, 0.25f, 0.20f, 0.45f));
        lib.blood     = SceneKit.SavedUnlit(U + "Blood.mat",     new Color(0.34f, 0.02f, 0.02f, 0.85f));
        lib.hpBack    = SceneKit.SavedUnlit(U + "HpBack.mat",    new Color(0.05f, 0.05f, 0.05f, 0.80f));
        lib.hpFill    = SceneKit.SavedUnlit(U + "HpFill.mat",    new Color(0.40f, 0.95f, 0.35f, 1.00f));
        lib.arrow     = SceneKit.SavedUnlit(U + "Arrow.mat",     new Color(0.85f, 0.80f, 0.65f, 1.00f), false);
        lib.particle  = SceneKit.SavedUnlit(U + "Particle.mat",  new Color(1f, 1f, 1f, 1f));
        lib.stump     = AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/Generated/Bark.mat");

        var root = new GameObject("GameRoot").AddComponent<GameRoot>();
        root.instancedWorld = iw; root.models = lib;
        root.terrainColliders = terrain.GetComponentsInChildren<Collider>();
        root.mapSize = new Vector2(tb.size.x, tb.size.z);
        root.gameObject.AddComponent<DemoAutopilot>();
        root.gameObject.AddComponent<PlayerInput>();
        root.gameObject.AddComponent<Sfx>();
        root.gameObject.AddComponent<Fx>();
        root.gameObject.AddComponent<AgeDirector>();
        var border = root.gameObject.AddComponent<BorderRenderer>();
        var bmat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/UI/Border.mat");
        if (bmat == null) { bmat = new Material(Shader.Find("COA/Border")); AssetDatabase.CreateAsset(bmat, "Assets/Materials/UI/Border.mat"); }
        bmat.shader = Shader.Find("COA/Border");
        bmat.SetFloat("_Fill", 0.018f); bmat.SetFloat("_Glow", 0.26f);        // the saved asset keeps old values otherwise
        border.material = bmat; lib.border = bmat;
        root.gameObject.AddComponent<COA.UI.Hud>();

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
