using System.Collections.Generic;

namespace COA.Sim
{
    public enum UnitType { Citizen, Swordsman, Spearman, Archer }
    public enum UnitClass { Worker, Light, Heavy, Ranged }
    public enum BuildingType { Hall, Hut, Storehouse, RuneHall, Muster, Tower, Farm }
    public enum NodeKind { Tree, Berry, Stone, Iron, Farm }
    public enum Branch { Civic, Commerce, Military, Science }

    public sealed class UnitDef
    {
        public UnitType type; public string name; public UnitClass cls; public Cost cost; public float trainTime;
        public float hp, dps, range, speed, cooldown; public int pop; public string model; public string hotkey;
    }

    public sealed class BuildingDef
    {
        public BuildingType type; public string name, model, blurb, hotkey; public Cost cost; public float buildTime, hp, radius;
        public int popProvided; public bool dropOff; public float territory; public UnitType[] trains = new UnitType[0];
        public float towerRange, towerDps; public int scholarSlots; public float knowledgeBase, knowledgePerScholar;
    }

    public sealed class TechDef
    {
        public string id, name, blurb; public Branch branch; public Cost cost; public float time;
    }

    /// <summary>
    /// ONE table. Sim, UI and placement all read this; numbers come from docs/03, 04 and 12.
    /// Two tables of the same fact is one table too many.
    /// </summary>
    public static class Catalog
    {
        /// <summary>docs/03 says 10. Measured: with 10, only 2-3 of 10 citizens were ever AT a node -- the rest were
        /// walking. 20 halves the trips. (Open question Q10: Rise of Nations citizens do not carry at all.)</summary>
        public const float CarryCapacity = 20f;
        public const int HardPopCap = 75;
        public const float AttritionPerSecond = 1.8f, RegenPerSecond = 1.0f, RegenDelay = 5f;
        public const float AgeAdvanceTime = 60f;
        public static readonly Cost AgeAdvanceCost = Cost.Of(food: 300, wood: 200, knowledge: 120);
        public const int AgeAdvanceTechsRequired = 2;
        public const float BorderTechBonus = 8f;

        public static readonly Dictionary<UnitType, UnitDef> Units = new Dictionary<UnitType, UnitDef>
        {
            [UnitType.Citizen]   = new UnitDef { type = UnitType.Citizen,   name = "Citizen",   cls = UnitClass.Worker, cost = Cost.Of(food: 50),            trainTime = 20, hp = 60,  dps = 3,  range = 1.2f, speed = 4.2f, cooldown = 1.0f, pop = 1, model = "villager",  hotkey = "C" },
            [UnitType.Swordsman] = new UnitDef { type = UnitType.Swordsman, name = "Swordsman", cls = UnitClass.Light,  cost = Cost.Of(food: 60, metal: 20), trainTime = 18, hp = 140, dps = 12, range = 1.4f, speed = 3.4f, cooldown = 0.9f, pop = 1, model = "swordsman", hotkey = "S" },
            [UnitType.Spearman]  = new UnitDef { type = UnitType.Spearman,  name = "Spearman",  cls = UnitClass.Heavy,  cost = Cost.Of(food: 50, wood: 15),  trainTime = 16, hp = 120, dps = 9,  range = 2.0f, speed = 3.2f, cooldown = 1.0f, pop = 1, model = "spearman",  hotkey = "P" },
            [UnitType.Archer]    = new UnitDef { type = UnitType.Archer,    name = "Archer",    cls = UnitClass.Ranged, cost = Cost.Of(food: 50, wood: 25),  trainTime = 20, hp = 80,  dps = 10, range = 14f,  speed = 3.0f, cooldown = 1.2f, pop = 1, model = "archer",    hotkey = "A" },
        };

        public static readonly Dictionary<BuildingType, BuildingDef> Buildings = new Dictionary<BuildingType, BuildingDef>
        {
            [BuildingType.Hall]       = new BuildingDef { type = BuildingType.Hall, name = "Longhouse", model = "hall", hotkey = "",
                blurb = "Town centre. Trains citizens, takes every resource, anchors your border.",
                cost = Cost.Of(food: 200, wood: 200, stone: 100), buildTime = 90, hp = 2400, radius = 7.5f, popProvided = 5,
                dropOff = true, territory = 38f, trains = new[] { UnitType.Citizen },
                towerRange = 12f, towerDps = 5f },     // an RoN city defends itself a little: the first raid is a scare, not a wipe
            [BuildingType.Hut]        = new BuildingDef { type = BuildingType.Hut, name = "Hut", model = "hut_a", hotkey = "H",
                blurb = "+5 population.", cost = Cost.Of(wood: 40), buildTime = 15, hp = 400, radius = 3.2f, popProvided = 5 },
            [BuildingType.Storehouse] = new BuildingDef { type = BuildingType.Storehouse, name = "Storehouse", model = "stabbur", hotkey = "T",
                blurb = "Resource drop-off. Put it next to what you are gathering.",
                cost = Cost.Of(wood: 60), buildTime = 20, hp = 500, radius = 3.8f, dropOff = true },
            [BuildingType.RuneHall]   = new BuildingDef { type = BuildingType.RuneHall, name = "Rune Hall", model = "runehall", hotkey = "R",
                blurb = "Makes Knowledge - the only way to the next age. Staff it with scholars.",
                cost = Cost.Of(wood: 120, stone: 40), buildTime = 40, hp = 700, radius = 5.2f,
                scholarSlots = 2, knowledgeBase = 0.20f, knowledgePerScholar = 0.15f },
            [BuildingType.Muster]     = new BuildingDef { type = BuildingType.Muster, name = "Muster Hall", model = "muster", hotkey = "M",
                blurb = "Trains swordsmen, spearmen and archers.",
                cost = Cost.Of(wood: 100, metal: 30), buildTime = 30, hp = 900, radius = 6.2f,
                trains = new[] { UnitType.Swordsman, UnitType.Spearman, UnitType.Archer } },
            [BuildingType.Tower]      = new BuildingDef { type = BuildingType.Tower, name = "Watchtower", model = "tower_a", hotkey = "W",
                blurb = "Shoots raiders and pushes your border out by 22 m.",
                cost = Cost.Of(wood: 60, stone: 40), buildTime = 25, hp = 800, radius = 2.4f,
                territory = 22f, towerRange = 16f, towerDps = 8f },
            [BuildingType.Farm]       = new BuildingDef { type = BuildingType.Farm, name = "Farm", model = "farm", hotkey = "F",
                blurb = "Slow food that never runs out. Two workers.",
                cost = Cost.Of(wood: 50), buildTime = 18, hp = 300, radius = 4.3f },
        };

        public static readonly TechDef[] Techs =
        {
            new TechDef { id = "allthing",  name = "The Allthing",  branch = Branch.Civic,    cost = Cost.Of(food: 80, knowledge: 30),  time = 30, blurb = "Borders +8 m. Citizens build 25% faster." },
            new TechDef { id = "felling",   name = "Felling Axes",  branch = Branch.Commerce, cost = Cost.Of(wood: 60, knowledge: 25),  time = 25, blurb = "Wood and food gathered 20% faster." },
            new TechDef { id = "shieldwall",name = "Shield Wall",   branch = Branch.Military, cost = Cost.Of(metal: 40, knowledge: 30), time = 30, blurb = "Soldiers +20% health. Towers +25% damage." },
            new TechDef { id = "runelore",  name = "Rune Lore",     branch = Branch.Science,  cost = Cost.Of(stone: 30, knowledge: 20), time = 25, blurb = "Knowledge +35%." },
        };

        /// <summary>
        /// DL33. docs/03's rates assume perfect play and no walking. Measured in the running game -- real
        /// NavMesh paths, 10 carried per trip, raids -- they gave about HALF the documented pace: a plain bot
        /// had 8 citizens at minute 12, not minute 8, and lost every time with food and wood pinned at zero.
        /// The demo scales gathering rather than quietly editing the design numbers, so the gap stays visible.
        /// </summary>
        public const float DemoEconomyScale = 1.4f;

        /// <summary>Per citizen, per second, at the node. Base numbers are docs/03-resources.html.</summary>
        public static float GatherRate(NodeKind k) => DemoEconomyScale *
            (k == NodeKind.Tree ? 0.55f : k == NodeKind.Berry ? 0.50f : k == NodeKind.Stone ? 0.35f
           : k == NodeKind.Iron ? 0.30f : 0.42f);

        public static Res ResourceOf(NodeKind k) =>
            k == NodeKind.Tree ? Res.Wood : k == NodeKind.Stone ? Res.Stone : k == NodeKind.Iron ? Res.Metal : Res.Food;

        public static float NodeRadius(NodeKind k) => k == NodeKind.Tree ? 0.9f : k == NodeKind.Farm ? 2.6f : 2.2f;
        public static int NodeWorkerCap(NodeKind k) => k == NodeKind.Tree ? 2 : k == NodeKind.Farm ? 2 : 4;

        /// <summary>Light beats ranged, ranged beats heavy, heavy beats light. docs/04. Do not add a fourth corner.</summary>
        public static float CounterBonus(UnitClass attacker, UnitClass target) =>
            (attacker == UnitClass.Light && target == UnitClass.Ranged) ||
            (attacker == UnitClass.Ranged && target == UnitClass.Heavy) ||
            (attacker == UnitClass.Heavy && target == UnitClass.Light) ? 1.75f : 1f;   // 1.5 was not enough: a
        // swordsman still beat a spearman 10.0 s to 10.4 s, so the triangle did not actually hold. Tested.
    }
}
