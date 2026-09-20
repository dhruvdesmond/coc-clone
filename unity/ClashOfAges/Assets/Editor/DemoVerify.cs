using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;

/// <summary>
/// Visual verification in PLAY mode. Run WITHOUT -batchmode and WITHOUT -quit:
///     tools/u.sh play DemoVerify.Chop
/// It regenerates the scene, drops a flag file, enters play mode; DemoAutopilot does the rest and exits Unity.
/// </summary>
public static class DemoVerify
{
    public static void Chop() => Run("chop");
    public static void Full() => Run("full");

    static void Run(string script)
    {
        DemoSceneBuilder.Build();
        EditorSceneManager.OpenScene(DemoSceneBuilder.ScenePath);
        Directory.CreateDirectory("Temp");
        File.WriteAllText("Temp/coa_autopilot.flag", script);
        EditorApplication.EnterPlaymode();
    }
}
