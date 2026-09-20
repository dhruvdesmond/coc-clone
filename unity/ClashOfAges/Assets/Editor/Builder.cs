using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

/// <summary>Headless build entry points. The scene is ALWAYS regenerated first --
/// a hand-edit to a generated scene is destroyed on the next build, silently.</summary>
public static class Builder
{
    const string Scene = "Assets/Scenes/SliceZero.unity";

    [MenuItem("Clash of Ages/Build/macOS")]
    public static void PerformMacBuild()     => Build(BuildTarget.StandaloneOSX, "ClashOfAges.app");

    [MenuItem("Clash of Ages/Build/Windows")]
    public static void PerformWindowsBuild() => Build(BuildTarget.StandaloneWindows64, "ClashOfAges.exe");

    static void Build(BuildTarget target, string outName)
    {
        SliceZero.BuildScene();          // regenerate, never trust the saved scene
        AssetDatabase.SaveAssets();

        var dir = Path.Combine("Build", target.ToString());
        Directory.CreateDirectory(dir);

        var opts = new BuildPlayerOptions {
            scenes = new[] { Scene },
            locationPathName = Path.Combine(dir, outName),
            target = target,
            options = BuildOptions.None,
        };

        var report = BuildPipeline.BuildPlayer(opts);
        var s = report.summary;
        Debug.Log($"[build] {target} {s.result}  {s.totalSize / 1048576} MB  " +
                  $"{s.totalTime.TotalSeconds:F1}s  errors {s.totalErrors}");
        if (s.result != BuildResult.Succeeded)
            EditorApplication.Exit(1);
    }
}
