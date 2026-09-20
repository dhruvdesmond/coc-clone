using System;
using System.Collections.Generic;
using System.Linq;
using COA.Game;
using COA.Sim;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace COA.UI
{
    /// <summary>The whole HUD. Reads the sim every frame; sends commands through World.Cmd* and PlayerInput.</summary>
    public sealed class Hud : MonoBehaviour
    {
        public static Hud I { get; private set; }
        GameRoot _g; World W => _g.World; PlayerInput _in; Canvas _canvas;

        readonly Dictionary<Res, Text> _res = new Dictionary<Res, Text>();
        readonly Dictionary<Res, float> _shown = new Dictionary<Res, float>();
        Text _pop, _age, _clock, _raid, _idle, _speed;
        RectTransform _cmdRoot; Text _selTitle, _selSub; Image _selHp; RectTransform _selHpRoot;
        readonly List<GameObject> _cmdButtons = new List<GameObject>();
        RectTransform _tooltip; Text _tipTitle, _tipBody;
        RectTransform _toastRoot; readonly List<(GameObject go, float until)> _toasts = new List<(GameObject, float)>();
        Image _banner; Text _bannerText, _bannerSub; float _bannerUntil;
        Image _dragBox; Text _placeHint;
        readonly List<Text> _objectives = new List<Text>();
        GameObject _title, _end;
        string _cmdSignature = "";

        static readonly (Res r, string name, Color c)[] ResDefs =
        {
            (Res.Food, "Food", new Color(0.55f, 0.85f, 0.40f)), (Res.Wood, "Wood", new Color(0.72f, 0.55f, 0.32f)),
            (Res.Stone, "Stone", new Color(0.72f, 0.72f, 0.76f)), (Res.Metal, "Metal", new Color(0.55f, 0.68f, 0.85f)),
            (Res.Knowledge, "Knowledge", new Color(0.74f, 0.58f, 1.00f)),
        };

        void Awake() { I = this; }

        void Start()
        {
            _g = GameRoot.I; _in = PlayerInput.I;
            BuildCanvas(); BuildTopBar(); BuildObjectives(); BuildCommandPanel(); BuildTooltip(); BuildToasts(); BuildBanner(); BuildOverlays();
            gameObject.AddComponent<Minimap>().Init(_canvas.transform);
            _g.OnSimEvent += OnSim;
            _in.OnRefused += s => Toast(s, UiKit.Bad);
        }

        void BuildCanvas()
        {
            var go = new GameObject("HUD Canvas"); go.transform.SetParent(transform, false);
            _canvas = go.AddComponent<Canvas>(); _canvas.renderMode = RenderMode.ScreenSpaceOverlay; _canvas.sortingOrder = 10;
            var sc = go.AddComponent<CanvasScaler>(); sc.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            sc.referenceResolution = new Vector2(1920, 1080); sc.matchWidthOrHeight = 1f;       // match HEIGHT: ultrawide gets more width, not bigger UI
            go.AddComponent<GraphicRaycaster>();
            if (FindFirstObjectByType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem"); es.AddComponent<EventSystem>(); es.AddComponent<InputSystemUIInputModule>();
            }
            _dragBox = UiKit.Box("DragBox", go.transform, Vector2.zero, Vector2.zero, Vector2.zero, Vector2.zero, Vector2.zero, new Color(0.4f, 1f, 0.5f, 0.14f));
            _dragBox.raycastTarget = false; _dragBox.gameObject.SetActive(false);
        }

        // ------------------------------------------------------------------ top bar
        void BuildTopBar()
        {
            var bar = UiKit.Box("TopBar", _canvas.transform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(0.5f, 1), Vector2.zero, new Vector2(0, 46), UiKit.Panel);
            float x = 18f;
            foreach (var d in ResDefs)
            {
                var chip = UiKit.Box("chip", bar.transform, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(x, 0), new Vector2(14, 14), d.c);
                chip.raycastTarget = false;
                UiKit.LabelAt("n", bar.transform, d.name, 12, UiKit.Dim, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(x + 20, 9), new Vector2(90, 16));
                _res[d.r] = UiKit.LabelAt("v", bar.transform, "0", 18, UiKit.Ink, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(x + 20, -8), new Vector2(90, 22), TextAnchor.MiddleLeft, FontStyle.Bold);
                _shown[d.r] = 0f; x += 128f;
            }
            _pop = UiKit.LabelAt("pop", bar.transform, "", 18, UiKit.Ink, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(x + 10, 0), new Vector2(170, 30), TextAnchor.MiddleLeft, FontStyle.Bold);
            _idle = UiKit.LabelAt("idle", bar.transform, "", 14, UiKit.Gold, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(x + 170, 0), new Vector2(220, 30));
            _age = UiKit.LabelAt("age", bar.transform, "", 18, UiKit.Gold, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(180, 0), new Vector2(260, 30), TextAnchor.MiddleCenter, FontStyle.Bold);
            _raid = UiKit.LabelAt("raid", bar.transform, "", 15, UiKit.Bad, new Vector2(1, 0.5f), new Vector2(1, 0.5f), new Vector2(1, 0.5f), new Vector2(-250, 0), new Vector2(250, 30), TextAnchor.MiddleRight, FontStyle.Bold);
            _clock = UiKit.LabelAt("clock", bar.transform, "", 16, UiKit.Dim, new Vector2(1, 0.5f), new Vector2(1, 0.5f), new Vector2(1, 0.5f), new Vector2(-150, 0), new Vector2(90, 30), TextAnchor.MiddleRight);
            var sp = UiKit.Button("speed", bar.transform, new Vector2(1, 0.5f), new Vector2(1, 0.5f), new Vector2(1, 0.5f), new Vector2(-14, 0), new Vector2(120, 30), "1x", 14, CycleSpeed);
            _speed = sp.GetComponentInChildren<Text>();
        }

        void CycleSpeed()
        {
            if (_g.paused) { _g.paused = false; _g.timeScale = 1f; }
            else if (_g.timeScale < 1.5f) _g.timeScale = 2f;
            else if (_g.timeScale < 3f) _g.timeScale = 4f;
            else { _g.paused = true; }
        }

        // ------------------------------------------------------------------ objectives
        static readonly string[] ObjectiveText =
        {
            "Send your citizen to chop wood  (right-click a tree)", "Train a second citizen at the Longhouse", "Build a Hut  (+5 population)",
            "Reach 6 citizens", "Build a Rune Hall and staff it with 2 scholars", "Research 2 technologies",
            "Build a Muster Hall and a Watchtower", "Advance to the Feudal Age", "Survive the final raid",
        };

        void BuildObjectives()
        {
            var p = UiKit.Box("Objectives", _canvas.transform, new Vector2(1, 1), new Vector2(1, 1), new Vector2(1, 1), new Vector2(-14, -60), new Vector2(430, 40 + ObjectiveText.Length * 24), UiKit.Panel);
            p.raycastTarget = false;
            UiKit.LabelAt("h", p.transform, "THE ROAD TO THE FEUDAL AGE", 12, UiKit.Gold, new Vector2(0, 1), new Vector2(1, 1), new Vector2(0, 1), new Vector2(14, -8), new Vector2(-20, 20), TextAnchor.MiddleLeft, FontStyle.Bold);
            for (int i = 0; i < ObjectiveText.Length; i++)
                _objectives.Add(UiKit.LabelAt("o" + i, p.transform, "", 14, UiKit.Dim, new Vector2(0, 1), new Vector2(1, 1), new Vector2(0, 1), new Vector2(14, -34 - i * 24), new Vector2(-20, 22)));
        }

        bool ObjectiveDone(int i)
        {
            var me = W.Me; var mine = W.buildings.Where(b => b.owner == World.Human && b.complete && !b.destroyed).ToList();
            int citizens = W.units.Count(u => u.owner == World.Human && u.IsCitizen);
            switch (i)
            {
                case 0: return me.gathered > 5f;
                case 1: return citizens >= 2;
                case 2: return mine.Any(b => b.type == BuildingType.Hut);
                case 3: return citizens >= 6;
                case 4: return mine.Any(b => b.type == BuildingType.RuneHall && b.scholars >= 2);
                case 5: return me.techs.Count >= 2;
                case 6: return mine.Any(b => b.type == BuildingType.Muster) && mine.Any(b => b.type == BuildingType.Tower);
                case 7: return me.age >= 2;
                default: return W.over && W.won;
            }
        }

        // ------------------------------------------------------------------ command panel
        void BuildCommandPanel()
        {
            var p = UiKit.Box("CommandPanel", _canvas.transform, new Vector2(0.5f, 0), new Vector2(0.5f, 0), new Vector2(0.5f, 0), new Vector2(0, 12), new Vector2(860, 172), UiKit.Panel);
            _selTitle = UiKit.LabelAt("title", p.transform, "", 20, UiKit.Ink, new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, 1), new Vector2(16, -10), new Vector2(300, 26), TextAnchor.MiddleLeft, FontStyle.Bold);
            _selSub = UiKit.LabelAt("sub", p.transform, "", 14, UiKit.Dim, new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, 1), new Vector2(16, -40), new Vector2(300, 100), TextAnchor.UpperLeft);
            _selHpRoot = UiKit.Box("hpBack", p.transform, new Vector2(0, 0), new Vector2(0, 0), new Vector2(0, 0), new Vector2(16, 14), new Vector2(290, 8), new Color(0, 0, 0, 0.6f)).rectTransform;
            _selHp = UiKit.Box("hp", _selHpRoot, new Vector2(0, 0), new Vector2(0, 1), new Vector2(0, 0.5f), Vector2.zero, new Vector2(290, 0), UiKit.Good);
            _cmdRoot = UiKit.Rect("cmds", p.transform, new Vector2(0, 0), new Vector2(1, 1), new Vector2(0, 0), new Vector2(330, 0), new Vector2(-330, 0));
        }

        struct Cmd { public string label, tipTitle, tipBody, problem; public Action run; public float progress; }

        List<Cmd> CommandsForSelection(out string signature)
        {
            var list = new List<Cmd>(); signature = "none";
            var me = W.Me;
            if (_in.units.Count > 0)
            {
                bool citizens = _in.units.Any(id => W.U(id) != null && W.U(id).IsCitizen);
                signature = citizens ? "citizens" : "soldiers";
                if (citizens)
                    foreach (var t in new[] { BuildingType.Hut, BuildingType.Storehouse, BuildingType.Farm, BuildingType.RuneHall, BuildingType.Muster, BuildingType.Tower })
                    {
                        var d = Catalog.Buildings[t]; var type = t;
                        list.Add(new Cmd { label = d.name + "\n<size=11>[" + d.hotkey + "]</size>", tipTitle = "Build " + d.name + "   [" + d.hotkey + "]", tipBody = d.cost + "   " + d.buildTime + " s with one builder\n" + d.blurb + "\nMore builders = faster: 2 is 1.6x, 3 is 2.2x, 4 is 2.8x.",
                                           problem = me.stock.CanAfford(d.cost) ? null : "Not enough resources", run = () => _in.BeginPlacement(type) });
                    }
                else list.Add(new Cmd { label = "Stop\n<size=11>[X]</size>", tipTitle = "Stop  [X]", tipBody = "Hold A while right-clicking to attack-move.", run = () => W.CmdStop(_in.units) });
                return list;
            }
            if (_in.building < 0) return list;
            var b = W.B(_in.building); if (b == null || b.owner != World.Human) return list;
            signature = "b" + b.id + (b.complete ? "c" : "u") + (b.researching ?? "-") + me.techs.Count + me.age;
            if (!b.complete) return list;

            foreach (var ut in b.def.trains)
            {
                var d = Catalog.Units[ut]; var type = ut; int bid = b.id;
                string problem = !me.stock.CanAfford(d.cost) ? "Not enough resources" : me.popUsed + d.pop > me.popCap ? "Build more huts" : null;
                list.Add(new Cmd { label = d.name + "\n<size=11>[" + d.hotkey + "]</size>", tipTitle = "Train " + d.name + "   [" + d.hotkey + "]",
                    tipBody = d.cost + "   " + d.trainTime + " s\n" + (int)d.hp + " HP   " + d.dps + " dmg/s   range " + d.range + " m", problem = problem,
                    run = () => { var why = W.CmdTrain(bid, type); if (why != null) Toast(why, UiKit.Bad); } });
            }
            if (b.def.scholarSlots > 0)
            {
                int bid = b.id;
                foreach (var t in Catalog.Techs)
                {
                    if (me.techs.Contains(t.id)) continue;
                    var tech = t;
                    string problem = b.researching != null ? "Already researching" : !me.stock.CanAfford(t.cost) ? "Not enough resources" : null;
                    list.Add(new Cmd { label = t.name + "\n<size=11>" + t.branch + "</size>", tipTitle = t.name + "   (" + t.branch + ")", tipBody = t.cost + "   " + t.time + " s\n" + t.blurb, problem = problem,
                        progress = b.researching == t.id ? 1f - b.researchTimer / t.time : 0f,
                        run = () => { var why = W.CmdResearch(bid, tech.id); if (why != null) Toast(why, UiKit.Bad); } });
                }
                if (me.age < 2)
                {
                    string problem = b.researching != null ? "Already researching" : me.techs.Count < Catalog.AgeAdvanceTechsRequired ? "Research " + Catalog.AgeAdvanceTechsRequired + " technologies first"
                                   : !me.stock.CanAfford(Catalog.AgeAdvanceCost) ? "Not enough resources" : null;
                    list.Add(new Cmd { label = "<color=#F6C453>FEUDAL AGE</color>", tipTitle = "Advance to the Feudal Age", problem = problem,
                        tipBody = Catalog.AgeAdvanceCost + "   " + Catalog.AgeAdvanceTime + " s\nNeeds " + Catalog.AgeAdvanceTechsRequired + " technologies. Borders grow, gathering improves -\nand the enemy will answer with everything they have.",
                        progress = b.researchingAge ? 1f - b.researchTimer / Catalog.AgeAdvanceTime : 0f,
                        run = () => { var why = W.CmdResearch(bid, "age"); if (why != null) Toast(why, UiKit.Bad); } });
                }
                if (b.scholars > 0) list.Add(new Cmd { label = "Eject\nscholar", tipTitle = "Eject a scholar", tipBody = "Send one scholar back to work.", run = () => W.CmdEject(bid) });
            }
            return list;
        }

        void RefreshCommandPanel()
        {
            var cmds = CommandsForSelection(out string sig);
            string full = sig + ":" + cmds.Count;
            if (full != _cmdSignature)
            {
                _cmdSignature = full;
                foreach (var go in _cmdButtons) Destroy(go);
                _cmdButtons.Clear();
                for (int i = 0; i < cmds.Count; i++)
                {
                    int idx = i; int col = i % 6, row = i / 6;
                    var btn = UiKit.Button("cmd" + i, _cmdRoot, new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, 1), new Vector2(col * 86 + 4, -10 - row * 78), new Vector2(80, 70), cmds[i].label, 13,
                        () => { var now = CommandsForSelection(out _); if (idx < now.Count) now[idx].run(); });
                    btn.GetComponentInChildren<Text>().supportRichText = true;
                    var bar = UiKit.Box("bar", btn.transform, new Vector2(0, 0), new Vector2(0, 0), new Vector2(0, 0), new Vector2(0, 0), new Vector2(0, 5), UiKit.Gold); bar.raycastTarget = false;
                    var tip = btn.gameObject.AddComponent<TipTarget>(); tip.hud = this; tip.index = idx;
                    _cmdButtons.Add(btn.gameObject);
                }
            }
            for (int i = 0; i < _cmdButtons.Count && i < cmds.Count; i++)
            {
                _cmdButtons[i].GetComponent<Button>().interactable = cmds[i].problem == null;
                _cmdButtons[i].transform.Find("bar").GetComponent<RectTransform>().sizeDelta = new Vector2(80f * Mathf.Clamp01(cmds[i].progress), 5);
            }
        }

        public void ShowTip(int index, RectTransform over)
        {
            var cmds = CommandsForSelection(out _);
            if (index < 0 || index >= cmds.Count) { HideTip(); return; }
            _tipTitle.text = cmds[index].tipTitle;
            _tipBody.text = cmds[index].tipBody + (cmds[index].problem != null ? "\n<color=#FF6152>" + cmds[index].problem + "</color>" : "");
            _tooltip.gameObject.SetActive(true);
            _tooltip.position = over.position + new Vector3(0, 84f * _canvas.scaleFactor, 0);
        }
        public void HideTip() { if (_tooltip != null) _tooltip.gameObject.SetActive(false); }

        void BuildTooltip()
        {
            var t = UiKit.Box("Tooltip", _canvas.transform, new Vector2(0, 0), new Vector2(0, 0), new Vector2(0.5f, 0), Vector2.zero, new Vector2(430, 112), new Color(0.03f, 0.025f, 0.05f, 0.97f));
            t.raycastTarget = false; _tooltip = t.rectTransform; t.rectTransform.sizeDelta = new Vector2(470, 132);
            _tipTitle = UiKit.LabelAt("t", t.transform, "", 16, UiKit.Gold, new Vector2(0, 1), new Vector2(1, 1), new Vector2(0, 1), new Vector2(12, -8), new Vector2(-20, 22), TextAnchor.MiddleLeft, FontStyle.Bold);
            _tipBody = UiKit.LabelAt("b", t.transform, "", 13, UiKit.Ink, new Vector2(0, 1), new Vector2(1, 1), new Vector2(0, 1), new Vector2(12, -34), new Vector2(-20, 72), TextAnchor.UpperLeft);
            _tipBody.supportRichText = true;
            _tooltip.gameObject.SetActive(false);
        }

        void UpdateSelectionInfo()
        {
            float hp = -1f;
            if (_in.placing.HasValue)
            {
                var d = Catalog.Buildings[_in.placing.Value];
                _selTitle.text = "Placing " + d.name;
                _selSub.text = (_in.placementProblem != null ? "<color=#FF6152>" + _in.placementProblem + "</color>" : "<color=#6BD98C>Good ground</color>")
                             + "\n\nLeft-click to build   R to rotate\nShift to place several   Esc to cancel";
                _selSub.supportRichText = true;
            }
            else if (_in.units.Count == 1)
            {
                var u = W.U(_in.units[0]);
                _selTitle.text = u.def.name; hp = u.hp / u.maxHp;
                _selSub.text = Describe(u) + "\n" + (int)u.hp + " / " + (int)u.maxHp + " HP";
            }
            else if (_in.units.Count > 1)
            {
                _selTitle.text = _in.units.Count + " units";
                _selSub.text = string.Join("   ", _in.units.Select(id => W.U(id)).Where(u => u != null).GroupBy(u => u.def.name).Select(g => g.Count() + " " + g.Key));
                hp = _in.units.Select(id => W.U(id)).Where(u => u != null).Average(u => u.hp / u.maxHp);
            }
            else if (_in.building >= 0)
            {
                var b = W.B(_in.building);
                _selTitle.text = b.def.name + (b.owner == World.Human ? "" : "  (enemy)"); hp = b.hp / b.def.hp;
                string s = b.def.blurb;
                if (!b.complete)
                {
                    int nb = W.BuildersOn(b); float left = W.SecondsLeft(b);
                    s = "Under construction  " + (int)(b.progress * 100) + "%\n" +
                        (nb == 0 ? "<color=#FF6152>No builders - right-click here with citizens</color>"
                                 : nb + (nb == 1 ? " builder" : " builders") + "  (" + World.BuildSpeed(nb).ToString("0.0") + "x)   " + Mathf.CeilToInt(left) + " s left") +
                        "\nRight-click with MORE citizens to build faster.";
                    _selSub.supportRichText = true;
                }
                if (b.complete && b.def.scholarSlots > 0)
                    s = "Scholars " + b.scholars + " / " + b.def.scholarSlots + "     +" + ((b.def.knowledgeBase + b.def.knowledgePerScholar * b.scholars) * W.Me.knowledgeMul).ToString("F2") + " Knowledge/s\nRight-click here with citizens to staff it.";
                if (b.queue.Count > 0) s += "\nTraining " + Catalog.Units[b.queue[0]].name + "  " + (int)(100 * b.trainTimer / Catalog.Units[b.queue[0]].trainTime) + "%   (+" + (b.queue.Count - 1) + " queued)";
                if (b.researching != null) s += "\nResearching...  " + Mathf.CeilToInt(b.researchTimer) + " s";
                _selSub.text = s;
            }
            else if (_in.node >= 0)
            {
                var n = W.N(_in.node);
                _selTitle.text = n.kind == NodeKind.Berry ? "Berry thicket" : n.kind == NodeKind.Stone ? "Stone outcrop" : "Iron ore";
                _selSub.text = (int)n.amount + " " + Catalog.ResourceOf(n.kind) + " left\nRight-click with citizens selected to gather.";
                hp = n.amount / n.max;
            }
            else { _selTitle.text = ""; _selSub.text = "Left-click or drag to select.\nRight-click to move, gather, build or attack.\n[.] next idle citizen    [H] home    [1-5] groups"; }
            _selHpRoot.gameObject.SetActive(hp >= 0f);
            if (hp >= 0f) { _selHp.rectTransform.sizeDelta = new Vector2(290f * Mathf.Clamp01(hp), 0); _selHp.color = Color.Lerp(UiKit.Bad, UiKit.Good, hp); }
        }

        string Describe(Unit u)
        {
            switch (u.state)
            {
                case UnitState.Gathering: return "Gathering " + u.carryRes + "   (" + (int)u.carry + " / " + (int)Catalog.CarryCapacity + ")";
                case UnitState.ToDropOff: return "Carrying " + (int)u.carry + " " + u.carryRes + " home";
                case UnitState.ToNode: return "Walking to work";
                case UnitState.Building: case UnitState.ToBuild: return "Building";
                case UnitState.Attacking: return "Fighting";
                case UnitState.Moving: return "Moving";
                default: return u.IsCitizen ? "Idle - give me something to do" : "Standing guard";
            }
        }

        // ------------------------------------------------------------------ toasts / banner
        void BuildToasts() { _toastRoot = UiKit.Rect("Toasts", _canvas.transform, new Vector2(0.5f, 1), new Vector2(0.5f, 1), new Vector2(0.5f, 1), new Vector2(0, -64), new Vector2(600, 10)); }

        public void Toast(string text, Color c)
        {
            foreach (var t in _toasts) if (t.go != null && t.go.GetComponentInChildren<Text>().text == text) return;      // no spam
            var box = UiKit.Box("toast", _toastRoot, new Vector2(0.5f, 1), new Vector2(0.5f, 1), new Vector2(0.5f, 1), new Vector2(0, -_toasts.Count * 38), new Vector2(520, 32), UiKit.Panel);
            box.raycastTarget = false;
            UiKit.Label("t", box.transform, text, 15, c, TextAnchor.MiddleCenter, FontStyle.Bold);
            _toasts.Add((box.gameObject, Time.unscaledTime + 3.2f));
        }

        void BuildBanner()
        {
            _banner = UiKit.Box("Banner", _canvas.transform, new Vector2(0, 0.5f), new Vector2(1, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 140), new Vector2(0, 120), new Color(0, 0, 0, 0.62f));
            _banner.raycastTarget = false;
            _bannerText = UiKit.LabelAt("t", _banner.transform, "", 44, UiKit.Gold, new Vector2(0, 0.5f), new Vector2(1, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 16), new Vector2(0, 56), TextAnchor.MiddleCenter, FontStyle.Bold);
            _bannerSub = UiKit.LabelAt("s", _banner.transform, "", 18, UiKit.Ink, new Vector2(0, 0.5f), new Vector2(1, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, -30), new Vector2(0, 28), TextAnchor.MiddleCenter);
            _banner.gameObject.SetActive(false);
        }

        public void Banner(string title, string sub, Color c, float seconds = 4.5f)
        {
            _bannerText.text = title; _bannerText.color = c; _bannerSub.text = sub;
            _banner.gameObject.SetActive(true); _bannerUntil = Time.unscaledTime + seconds;
        }

        void OnSim(SimEvent e)
        {
            switch (e.type)
            {
                case SimEventType.BuildingComplete: if (e.b == World.Human) Toast(W.B(e.a).def.name + " complete", UiKit.Good); break;
                case SimEventType.TechComplete: if (e.b == World.Human) Toast(e.text + " researched", UiKit.Gold); break;
                case SimEventType.AgeAdvanceStarted: Toast("Advancing to the Feudal Age - hold out for 60 seconds", UiKit.Gold); break;
                case SimEventType.AgeAdvanced: Banner("THE FEUDAL AGE", "Your borders grow. So does their interest in you.", UiKit.Gold, 6f); break;
                case SimEventType.RaidIncoming:
                    Banner(e.b == 1 ? "THE FINAL RAID" : "RAIDERS SIGHTED", (int)e.amount + " warriors are marching on your longhouse", UiKit.Bad); break;
                case SimEventType.RaidDefeated: Toast("The raid is broken", UiKit.Good); break;
                case SimEventType.BuildingDestroyed: if (e.b == World.Human) Toast("A building has fallen!", UiKit.Bad); break;
                case SimEventType.Victory: case SimEventType.Defeat: ShowEnd(e.type == SimEventType.Victory); break;
            }
        }

        // ------------------------------------------------------------------ title / end
        void BuildOverlays()
        {
            _placeHint = UiKit.LabelAt("placeHint", _canvas.transform, "", 16, UiKit.Ink, new Vector2(0.5f, 0), new Vector2(0.5f, 0), new Vector2(0.5f, 0), new Vector2(0, 196), new Vector2(700, 24), TextAnchor.MiddleCenter, FontStyle.Bold);

            var t = UiKit.Box("Title", _canvas.transform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero, new Color(0.03f, 0.02f, 0.05f, 0.80f));
            _title = t.gameObject;
            UiKit.LabelAt("k", t.transform, "A RISE OF NATIONS CLONE  ·  AGE I DEMO", 14, UiKit.Gold, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 250), new Vector2(900, 24), TextAnchor.MiddleCenter, FontStyle.Bold);
            UiKit.LabelAt("h", t.transform, "CLASH OF AGES", 78, UiKit.Ink, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 180), new Vector2(1100, 96), TextAnchor.MiddleCenter, FontStyle.Bold);
            UiKit.LabelAt("p", t.transform, "You have one citizen, a longhouse, and a border.\nGather. Build inside your border. Staff a Rune Hall. Reach the Feudal Age - and survive what it brings.",
                20, UiKit.Dim, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 88), new Vector2(1100, 70), TextAnchor.MiddleCenter);
            UiKit.LabelAt("c", t.transform,
                "LEFT-CLICK  select     DRAG  box-select     RIGHT-CLICK  move · gather · build · attack · staff\n" +
                "RIGHT-DRAG / ARROWS / screen edge  pan     SCROLL  zoom at cursor     Q E  rotate\n" +
                "[.]  next idle citizen     [H]  home     [X]  stop     [A]+right-click  attack-move     Ctrl+[1-5] / [1-5]  groups",
                16, UiKit.Ink, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, -30), new Vector2(1300, 96), TextAnchor.MiddleCenter);
            UiKit.Button("start", t.transform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, -150), new Vector2(300, 64), "BEGIN", 26, () => { _title.SetActive(false); _g.paused = false; });
        }

        void ShowEnd(bool won)
        {
            if (_end != null) return;
            var t = UiKit.Box("End", _canvas.transform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero, new Color(0.03f, 0.02f, 0.05f, 0.84f));
            _end = t.gameObject; var me = W.Me;
            UiKit.LabelAt("h", t.transform, won ? "THE FEUDAL AGE IS YOURS" : "THE LONGHOUSE HAS FALLEN", 60, won ? UiKit.Gold : UiKit.Bad, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 130), new Vector2(1400, 80), TextAnchor.MiddleCenter, FontStyle.Bold);
            UiKit.LabelAt("s", t.transform,
                "Time  " + Clock(W.time) + "        Resources gathered  " + (int)me.gathered + "        Border  " + (int)(W.territory.LandShare(World.Human) * 100) + "% of the map\n" +
                "Raiders slain  " + me.unitsKilled + "        Your dead  " + me.unitsLost + "        Technologies  " + me.techs.Count + " / " + Catalog.Techs.Length,
                20, UiKit.Ink, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, 20), new Vector2(1300, 70), TextAnchor.MiddleCenter);
            UiKit.Button("again", t.transform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0, -90), new Vector2(300, 60), "PLAY AGAIN", 22,
                () => UnityEngine.SceneManagement.SceneManager.LoadScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene().buildIndex));
        }

        public void DismissTitle() { if (_title != null) _title.SetActive(false); }
        static string Clock(float s) => ((int)s / 60) + ":" + ((int)s % 60).ToString("00");

        // ------------------------------------------------------------------ per-frame
        void Update()
        {
            if (_g == null) return;
            var me = W.Me;
            foreach (var d in ResDefs)
            {
                // business speed: the counter chases the value, it does not teleport
                float target = me.stock[d.r]; _shown[d.r] = Mathf.Lerp(_shown[d.r], target, 1f - Mathf.Exp(-10f * Time.unscaledDeltaTime));
                if (Mathf.Abs(_shown[d.r] - target) < 0.6f) _shown[d.r] = target;
                _res[d.r].text = ((int)_shown[d.r]).ToString();
            }
            _pop.text = "Pop " + me.popUsed + " / " + me.popCap; _pop.color = me.popUsed >= me.popCap ? UiKit.Bad : UiKit.Ink;
            int idle = _in.IdleCitizens; _idle.text = idle > 0 ? idle + " idle  [.]" : "";
            _age.text = me.age == 1 ? "SETTLEMENT AGE" : "FEUDAL AGE";
            _clock.text = Clock(W.time);
            float next = W.raids.SecondsToNextRaid;
            _raid.text = W.raids.LiveRaiders > 0 ? "RAID IN PROGRESS  (" + W.raids.LiveRaiders + ")" : next > 0 && next < 90 ? "Raid in " + Clock(next) : "";
            _speed.text = _g.paused || _g.timeScale < 0.01f ? "PAUSED" : _g.timeScale.ToString("0") + "x speed";

            for (int i = 0; i < _objectives.Count; i++)
            {
                bool done = ObjectiveDone(i);
                _objectives[i].text = (done ? "✓  " : "○  ") + ObjectiveText[i];
                _objectives[i].color = done ? UiKit.Good : (i == 0 || ObjectiveDone(i - 1) ? UiKit.Ink : UiKit.Dim);
            }

            RefreshCommandPanel(); UpdateSelectionInfo(); HandleHotkeys();

            for (int i = _toasts.Count - 1; i >= 0; i--)
                if (Time.unscaledTime > _toasts[i].until) { Destroy(_toasts[i].go); _toasts.RemoveAt(i); for (int k = 0; k < _toasts.Count; k++) ((RectTransform)_toasts[k].go.transform).anchoredPosition = new Vector2(0, -k * 38); }
            if (_banner.gameObject.activeSelf && Time.unscaledTime > _bannerUntil) _banner.gameObject.SetActive(false);

            var dr = _in.DragRect;
            _dragBox.gameObject.SetActive(dr.HasValue);
            if (dr.HasValue) { var rt = _dragBox.rectTransform; float s = _canvas.scaleFactor; rt.anchoredPosition = dr.Value.min / s; rt.sizeDelta = dr.Value.size / s; }
        }

        void HandleHotkeys()
        {
            var kb = UnityEngine.InputSystem.Keyboard.current; if (kb == null || _g.paused || _in.placing.HasValue) return;
            if (kb.ctrlKey.isPressed || kb.leftCommandKey.isPressed) return;
            var cmds = CommandsForSelection(out _);
            foreach (var key in kb.allKeys)
            {
                if (!key.wasPressedThisFrame || key.displayName == null || key.displayName.Length != 1) continue;
                foreach (var c in cmds)
                    if (c.tipTitle != null && c.tipTitle.EndsWith("[" + key.displayName.ToUpperInvariant() + "]") && c.problem == null) { c.run(); return; }
            }
        }
    }

    public sealed class TipTarget : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler
    {
        public Hud hud; public int index;
        public void OnPointerEnter(PointerEventData e) => hud.ShowTip(index, (RectTransform)transform);
        public void OnPointerExit(PointerEventData e) => hud.HideTip();
    }
}
