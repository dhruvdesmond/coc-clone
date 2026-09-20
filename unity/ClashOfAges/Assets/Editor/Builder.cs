using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

/// <summary>Headless build entry points. The scene is ALWAYS regenerated first -- a hand-edit to a generated
/// scene is destroyed on the next build, silently.</summary>
public static class Builder
{
    [MenuItem("Clash of Ages/Build/macOS")]
    public static void PerformMacBuild() => Build(BuildTarget.StandaloneOSX, "ClashOfAges.app");

    [MenuItem("Clash of Ages/Build/Windows")]
    public static void PerformWindowsBuild() => Build(BuildTarget.StandaloneWindows64, "ClashOfAges.exe");

    static void Build(BuildTarget target, string outName)
    {
        PaletteImporter.SyncMaterials();
        UnitSilhouette.Apply();
        DemoSceneBuilder.Build();
        AssetDatabase.SaveAssets();

        // Mono, not IL2CPP: IL2CPP on macOS shells out to Xcode, and `sudo xcodebuild -license accept`
        // has never been run on this machine. Mono needs nothing.
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
        PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080;
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed; PlayerSettings.resizableWindow = true;

        var dir = Path.Combine("Build", target.ToString());
        Directory.CreateDirectory(dir);
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { DemoSceneBuilder.ScenePath }, locationPathName = Path.Combine(dir, outName),
            target = target, options = BuildOptions.None });
        var s = report.summary;
        Debug.Log($"[build] {target} {s.result}  {s.totalSize / 1048576} MB  {s.totalTime.TotalSeconds:F0}s  errors {s.totalErrors}");
        if (s.result != BuildResult.Succeeded) EditorApplication.Exit(1);
    }
}
