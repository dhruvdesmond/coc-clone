using UnityEngine;
using UnityEngine.UI;

namespace COA.UI
{
    /// <summary>uGUI built entirely in code: no prefabs, nothing for a generated scene to lose.</summary>
    public static class UiKit
    {
        public static readonly Color Panel = new Color(0.055f, 0.045f, 0.085f, 0.90f);
        public static readonly Color Panel2 = new Color(0.12f, 0.10f, 0.18f, 0.95f);
        public static readonly Color Gold = new Color(0.965f, 0.77f, 0.33f);
        public static readonly Color Ink = new Color(0.96f, 0.94f, 0.90f);
        public static readonly Color Dim = new Color(0.62f, 0.58f, 0.70f);
        public static readonly Color Bad = new Color(1f, 0.38f, 0.32f);
        public static readonly Color Good = new Color(0.42f, 0.85f, 0.55f);

        static Font _font;
        public static Font Font => _font != null ? _font : (_font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"));
        static Sprite _white;
        public static Sprite White
        {
            get
            {
                if (_white != null) return _white;
                var t = new Texture2D(4, 4); var px = new Color[16]; for (int i = 0; i < 16; i++) px[i] = Color.white; t.SetPixels(px); t.Apply();
                return _white = Sprite.Create(t, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f));
            }
        }

        public static RectTransform Rect(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax, Vector2 pivot, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform)); go.transform.SetParent(parent, false);
            var rt = (RectTransform)go.transform; rt.anchorMin = anchorMin; rt.anchorMax = anchorMax; rt.pivot = pivot;
            rt.anchoredPosition = pos; rt.sizeDelta = size; return rt;
        }

        public static Image Box(string name, Transform parent, Vector2 aMin, Vector2 aMax, Vector2 pivot, Vector2 pos, Vector2 size, Color c)
        {
            var rt = Rect(name, parent, aMin, aMax, pivot, pos, size);
            var img = rt.gameObject.AddComponent<Image>(); img.sprite = White; img.color = c; return img;
        }

        public static Text Label(string name, Transform parent, string text, int size, Color c, TextAnchor align = TextAnchor.MiddleLeft, FontStyle style = FontStyle.Normal)
        {
            var rt = Rect(name, parent, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Font; t.text = text; t.fontSize = size; t.color = c; t.alignment = align; t.fontStyle = style;
            t.horizontalOverflow = HorizontalWrapMode.Wrap; t.verticalOverflow = VerticalWrapMode.Overflow; t.raycastTarget = false;
            return t;
        }

        public static Text LabelAt(string name, Transform parent, string text, int size, Color c, Vector2 aMin, Vector2 aMax, Vector2 pivot, Vector2 pos, Vector2 sizeDelta, TextAnchor align = TextAnchor.MiddleLeft, FontStyle style = FontStyle.Normal)
        {
            var t = Label(name, parent, text, size, c, align, style);
            var rt = t.rectTransform; rt.anchorMin = aMin; rt.anchorMax = aMax; rt.pivot = pivot; rt.anchoredPosition = pos; rt.sizeDelta = sizeDelta;
            return t;
        }

        public static Button Button(string name, Transform parent, Vector2 aMin, Vector2 aMax, Vector2 pivot, Vector2 pos, Vector2 size, string label, int fontSize, System.Action onClick)
        {
            var img = Box(name, parent, aMin, aMax, pivot, pos, size, Panel2);
            var b = img.gameObject.AddComponent<Button>();
            var cb = b.colors; cb.normalColor = Color.white; cb.highlightedColor = new Color(1.5f, 1.4f, 1.1f); cb.pressedColor = new Color(0.7f, 0.7f, 0.7f);
            cb.disabledColor = new Color(0.45f, 0.45f, 0.45f, 0.8f); cb.fadeDuration = 0.06f; b.colors = cb;
            b.targetGraphic = img;
            if (onClick != null) b.onClick.AddListener(() => onClick());
            var t = Label("Text", img.transform, label, fontSize, Ink, TextAnchor.MiddleCenter, FontStyle.Bold);
            t.rectTransform.offsetMin = new Vector2(3, 2); t.rectTransform.offsetMax = new Vector2(-3, -2);
            return b;
        }
    }
}
