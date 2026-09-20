using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// PROGRESS.md Q5 -- measure what Mouse.current.scroll ACTUALLY reports, per platform.
///
/// The received wisdom is that Windows reports mouse-wheel scroll in steps of +/-120
/// (inherited from WM_MOUSEWHEEL) while macOS reports small continuous values. A deep
/// research pass REFUTED that claim 0-3, twice. So the normalisation constant for
/// cross-platform zoom is genuinely unknown, and guessing it is how RTSCamera ends up
/// feeling wrong on one of the two platforms we ship.
///
/// This measures instead of guessing.
///
/// HOW TO RUN
///   Attach to any GameObject in a scene, press Play (or run a build), then:
///     1. one slow wheel notch        2. one fast wheel spin
///     3. macOS trackpad: slow two-finger drag     4. fast two-finger flick
///     5. pinch to zoom, if the device sends one
///   Press F9 to write the CSV. The path is printed to the console and shown on screen.
///
/// WHAT TO DO WITH THE RESULT
///   Set RTSCamera.scrollScale per platform so that one wheel notch and one comfortable
///   trackpad flick produce a similar zoom step. Record both numbers in PROGRESS.md and
///   close Q5.
/// </summary>
public class ScrollProbe : MonoBehaviour
{
    struct Sample { public float t; public float y; public float x; public string dev; }

    readonly List<Sample> _samples = new List<Sample>();
    readonly StringBuilder _hud = new StringBuilder();
    float _min = float.MaxValue, _max = float.MinValue, _absMin = float.MaxValue;
    int _events;
    string _written;

#if ENABLE_INPUT_SYSTEM
    void Update()
    {
        var mouse = Mouse.current;
        if (mouse == null) return;

        Vector2 s = mouse.scroll.ReadValue();
        if (Mathf.Abs(s.y) > 0.0001f || Mathf.Abs(s.x) > 0.0001f)
        {
            _samples.Add(new Sample {
                t = Time.realtimeSinceStartup, y = s.y, x = s.x,
                dev = mouse.displayName ?? mouse.name
            });
            _events++;
            float a = Mathf.Abs(s.y);
            if (s.y < _min) _min = s.y;
            if (s.y > _max) _max = s.y;
            if (a > 0.0001f && a < _absMin) _absMin = a;
        }

        if (Keyboard.current != null && Keyboard.current.f9Key.wasPressedThisFrame) Write();
        if (Keyboard.current != null && Keyboard.current.f8Key.wasPressedThisFrame) Reset();
    }
#endif

    void Reset()
    {
        _samples.Clear(); _events = 0;
        _min = float.MaxValue; _max = float.MinValue; _absMin = float.MaxValue;
        _written = null;
    }

    void Write()
    {
        if (_samples.Count == 0) { Debug.Log("[scrollprobe] nothing recorded"); return; }
        var dir = Path.Combine(Application.persistentDataPath, "scrollprobe");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir,
            $"scroll_{Application.platform}_{System.DateTime.Now:yyyyMMdd_HHmmss}.csv");

        var sb = new StringBuilder();
        sb.AppendLine("# platform,device,samples,minY,maxY,smallestNonZeroAbsY");
        sb.AppendLine($"# {Application.platform},{_samples[0].dev},{_samples.Count}," +
                      $"{F(_min)},{F(_max)},{F(_absMin)}");
        sb.AppendLine("t,scrollY,scrollX,device");
        foreach (var s in _samples)
            sb.AppendLine($"{F(s.t)},{F(s.y)},{F(s.x)},\"{s.dev}\"");
        File.WriteAllText(path, sb.ToString());

        _written = path;
        Debug.Log($"[scrollprobe] {_samples.Count} samples -> {path}\n" +
                  $"[scrollprobe] platform={Application.platform} minY={F(_min)} maxY={F(_max)} " +
                  $"smallestNonZero={F(_absMin)}\n" +
                  $"[scrollprobe] suggested RTSCamera.scrollScale = " +
                  $"{F(0.12f / Mathf.Max(0.0001f, Mathf.Abs(_absMin)))}  " +
                  "(gives ~12% height change on the smallest real event)");
    }

    static string F(float v) => v.ToString("G9", CultureInfo.InvariantCulture);

    void OnGUI()
    {
        _hud.Clear();
        _hud.AppendLine("SCROLL PROBE  —  PROGRESS.md Q5");
        _hud.AppendLine($"platform        {Application.platform}");
        _hud.AppendLine($"events          {_events}");
        _hud.AppendLine(_events > 0
            ? $"scrollY range   {F(_min)} .. {F(_max)}\nsmallest |Y|    {F(_absMin)}"
            : "scrollY range   —\nsmallest |Y|    —");
        _hud.AppendLine();
        _hud.AppendLine("wheel notch · wheel spin · trackpad drag · flick · pinch");
        _hud.AppendLine("F9 write CSV     F8 reset");
        if (_written != null) _hud.AppendLine($"\nwrote {_written}");

        var style = new GUIStyle(GUI.skin.label) { fontSize = 15, richText = false };
        style.normal.textColor = Color.white;
        GUI.Box(new Rect(12, 12, 660, 200), "");
        GUI.Label(new Rect(24, 22, 640, 180), _hud.ToString(), style);
    }
}
