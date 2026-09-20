using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// Desktop RTS camera. Fixed pitch, orbiting yaw, zoom toward the cursor.
///
/// DESIGN CONSTRAINTS (docs/08-map.html)
///   * LEFT-CLICK IS SELECTION ONLY. It is never bound to pan. Non-negotiable.
///   * Zoom goes toward the cursor, not the screen centre.
///   * Bounds and zoom limits respond to aspect ratio -- a camera tuned for a fixed
///     aspect shows the edge of the world at 21:9.
///
/// SCROLL NORMALISATION IS UNRESOLVED (PROGRESS.md Q5)
///   The widely repeated "Windows reports scroll in steps of +/-120" claim was REFUTED
///   0-3, twice. There is no verified constant to divide by. So this class does not
///   hardcode one: it reads <see cref="scrollScale"/>, which ScrollProbe measures per
///   platform. Until that measurement exists the default is a conservative guess and
///   zoom feel WILL be wrong on one platform or the other.
/// </summary>
[RequireComponent(typeof(Camera))]
public class RTSCamera : MonoBehaviour
{
    [Header("Framing")]
    public float pitch = 50f;
    public float yaw   = 30f;

    [Header("Zoom (metres above the focus point)")]
    public float minHeight = 18f;
    public float maxHeight = 90f;
    public float height    = 45f;

    [Header("Speed")]
    public float panSpeed       = 26f;   // m/s at max zoom-out, scaled by height
    public float dragSensitivity = 1.0f;
    public float yawStep        = 45f;
    public float smoothing      = 12f;

    [Tooltip("UNMEASURED -- see PROGRESS.md Q5. ScrollProbe writes the real value per platform.")]
    public float scrollScale = 0.01f;

    [Header("Edge pan")]
    public bool  edgePanEnabled = true;
    [Tooltip("Fraction of the SHORTER screen dimension, so the band is the same " +
             "physical size at 16:9 and at 21:9.")]
    public float edgeBandFraction = 0.015f;

    [Header("Bounds (world metres, map extent)")]
    public Vector2 mapSize = new Vector2(420f, 420f);

    Camera _cam;
    Vector3 _focus;          // the point on the ground the camera looks at
    Vector3 _focusTarget;
    float   _heightTarget;
    float   _yawTarget;
    Vector2 _lastMouse;
    bool    _dragging;

    void Awake()
    {
        _cam = GetComponent<Camera>();
        _heightTarget = height;
        _yawTarget = yaw;
        _focus = _focusTarget = transform.position + transform.forward *
                 (height / Mathf.Max(0.01f, Mathf.Sin(pitch * Mathf.Deg2Rad)));
        _focus.y = _focusTarget.y = 0f;
    }

#if ENABLE_INPUT_SYSTEM
    void Update()
    {
        var mouse = Mouse.current;
        var kb = Keyboard.current;
        float dt = Mathf.Max(Time.unscaledDeltaTime, 0.0001f);

        // pan speed scales with height: the same mouse travel should move the same
        // fraction of the visible world regardless of zoom
        float speed = panSpeed * (height / maxHeight) * 2f;
        Vector3 fwd   = Quaternion.Euler(0f, _yawTarget, 0f) * Vector3.forward;
        Vector3 right = Quaternion.Euler(0f, _yawTarget, 0f) * Vector3.right;
        Vector3 move = Vector3.zero;

        // ---- keyboard ----
        if (kb != null)
        {
            if (kb.wKey.isPressed || kb.upArrowKey.isPressed)    move += fwd;
            if (kb.sKey.isPressed || kb.downArrowKey.isPressed)  move -= fwd;
            if (kb.dKey.isPressed || kb.rightArrowKey.isPressed) move += right;
            if (kb.aKey.isPressed || kb.leftArrowKey.isPressed)  move -= right;
            if (kb.qKey.wasPressedThisFrame) _yawTarget -= yawStep;
            if (kb.eKey.wasPressedThisFrame) _yawTarget += yawStep;
        }

        if (mouse != null)
        {
            // ---- right / middle drag pan (NEVER left) ----
            bool wantDrag = mouse.rightButton.isPressed || mouse.middleButton.isPressed;
            Vector2 pos = mouse.position.ReadValue();
            if (wantDrag && !_dragging) { _dragging = true; _lastMouse = pos; }
            else if (!wantDrag) _dragging = false;

            if (_dragging)
            {
                Vector2 d = pos - _lastMouse;
                _lastMouse = pos;
                // convert pixel travel to world travel at the focus plane
                float worldPerPixel = (2f * height * Mathf.Tan(_cam.fieldOfView * 0.5f * Mathf.Deg2Rad))
                                      / Mathf.Max(1, Screen.height);
                _focusTarget -= (right * d.x + fwd * d.y) * worldPerPixel * dragSensitivity;
            }
            else if (edgePanEnabled && Application.isFocused)
            {
                // band is a fraction of the SHORTER dimension so ultrawide behaves
                float band = Mathf.Min(Screen.width, Screen.height) * edgeBandFraction;
                band = Mathf.Max(band, 4f);
                if (pos.x >= 0 && pos.x <= Screen.width && pos.y >= 0 && pos.y <= Screen.height)
                {
                    if (pos.x < band)                 move -= right;
                    if (pos.x > Screen.width  - band) move += right;
                    if (pos.y < band)                 move -= fwd;
                    if (pos.y > Screen.height - band) move += fwd;
                }
            }

            // ---- zoom toward the cursor ----
            float scroll = mouse.scroll.ReadValue().y * scrollScale;
            if (Mathf.Abs(scroll) > 0.0001f)
            {
                float before = _heightTarget;
                _heightTarget = Mathf.Clamp(_heightTarget * Mathf.Exp(-scroll), minHeight, maxHeight);
                float factor = 1f - (_heightTarget / Mathf.Max(0.001f, before));

                // keep the ground point under the cursor fixed
                Ray ray = _cam.ScreenPointToRay(pos);
                var plane = new Plane(Vector3.up, Vector3.zero);
                if (Mathf.Abs(factor) > 0.0001f && plane.Raycast(ray, out float enter))
                {
                    Vector3 under = ray.GetPoint(enter);
                    _focusTarget += (under - _focusTarget) * factor;
                }
            }
        }

        if (move.sqrMagnitude > 0f) _focusTarget += move.normalized * speed * dt;

        // ---- aspect-aware bounds ----
        // half the visible ground extent, so the clamp lets you see the map edge but
        // not a void beyond it -- and it differs at 16:9 and 21:9
        float halfV = height * Mathf.Tan(_cam.fieldOfView * 0.5f * Mathf.Deg2Rad);
        float halfH = halfV * _cam.aspect;
        float limX = Mathf.Max(0f, mapSize.x * 0.5f - halfH * 0.35f);
        float limZ = Mathf.Max(0f, mapSize.y * 0.5f - halfV * 0.35f);
        _focusTarget.x = Mathf.Clamp(_focusTarget.x, -limX, limX);
        _focusTarget.z = Mathf.Clamp(_focusTarget.z, -limZ, limZ);
        _focusTarget.y = 0f;

        // ---- apply ----
        float k = 1f - Mathf.Exp(-smoothing * dt);
        _focus  = Vector3.Lerp(_focus, _focusTarget, k);
        height  = Mathf.Lerp(height, _heightTarget, k);
        yaw     = Mathf.LerpAngle(yaw, _yawTarget, k);

        var rot = Quaternion.Euler(pitch, yaw, 0f);
        float dist = height / Mathf.Max(0.01f, Mathf.Sin(pitch * Mathf.Deg2Rad));
        transform.SetPositionAndRotation(_focus - rot * Vector3.forward * dist, rot);
    }
#else
    void Update() { }   // Input System backend not enabled
#endif
}
