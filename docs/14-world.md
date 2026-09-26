# 14 · The World — what the map must hold, and how big it must be

> **What this file is.** The one list of everything the *world* needs: how large the map is against Rise of Nations,
> every resource that sits on the ground, every building and unit type by age, the roads, and the animations and
> effects that happen on the map. Written 2026-09-26 from PENDING B18. It gathers what was spread across five design
> docs and PROGRESS §5b, and records the things **no document had** (roads and highways, helicopters, vehicles
> exploding, walls and towers as living objects, the RoN size comparison).
>
> **Status column:** ✅ exists (model or system built) · 📄 designed, not built · 🆕 first written down here — not yet a decision.
> Costs, rates and the counter triangle stay where they are; this file points, it does not duplicate them.

| Detail lives in | What it owns |
|---|---|
| `docs/03-resources.html` | the nine economy resources, gather rates, node capacities |
| `docs/04-roster.html` | every building and unit with cost, HP, the counter triangle |
| `docs/05-assets.html` | the asset manifest and build order (35 built / ~192 planned as of 2026-09-19) |
| `docs/08-map.html` | terrain features, biomes, archetypes, fog of war, planned map sizes |
| `docs/09-fx-audio.html` | the three speeds, weapon impacts, the missile timeline, blood, sound |
| `docs/12-territory.html` | borders, cities, rare resources, nations, Armageddon |
| `PROGRESS.md` §5b | the animation inventory: ~80 clips, 14 code-driven motions, 13 rigs |
| `blender/base/map_world/build.py` | the world map as it stands today (260 × 190 m, v2) |

---

## 1. Size — us against Rise of Nations

Rise of Nations measures maps in tiles. The comparison below is the one given in chat for PENDING B16; the
tile-to-metre conversion (~2.5 m per tile, from a citizen being roughly one tile long) is an **estimate**, so read the
ratios, not the metres.

| Map | Tiles | ≈ metres a side | ≈ area | Against our world map |
|---|---|---|---|---|
| RoN Arena (smallest) | 200 × 200 | ~500 | ~25 ha | 5× ours |
| RoN Big Huge (largest) | 400 × 400 | ~900–1000 | ~80–100 ha | 16–20× ours |
| **Ours — `map_world` v2** | — | **260 × 190** | **4.9 ha** | — |
| Ours — `map_village` (the demo) | — | 104 × 84 | 0.9 ha | |
| Planned Duel (doc 08) | — | 240 × 240 | 5.8 ha | ≈ Arena ÷ 4 |
| Planned Standard (doc 08) | — | 420 × 420 | 17.6 ha | ≈ Arena × 0.7 |
| Planned Grand (doc 08) | — | 640 × 640 | 41 ha | ≈ half a Big Huge |

**What this says.** Our current Blender world is a *sampler* of every biome, not a battlefield. To reach even the
planned Standard size the map must grow ~3.6× in area; to match RoN's largest, ~18×. Two things follow, both already
decided elsewhere and worth holding to:

1. **Scale is instances, not objects.** 553 trees today are 553 Blender objects and the build takes 6 minutes. A
   Standard map has ~2,000 trees and 15–20k ground-cover instances (doc 08). Blender must scatter through one mesh
   plus a transform list, as `export_nature.py` already ships to Unity, or the build time goes to hours.
2. **A big map only works with territory.** RoN's large maps are playable because borders, attrition and cities make
   most of the land *someone's*; an empty 900 m map with nothing to own is a walking simulator. Size and doc 12 land
   together, not size first.

**RoN's own answer to "what is on a big map":** more of the same resources in more places, 6–10 rares, more
chokepoints. It does not add resource *types* with size. We follow that: the type list in §2 is fixed; the count
scales with the map.

---

## 2. Resources on the ground

### 2a. The nine that the economy uses (doc 03) — and where they sit on the map

| Resource | Map object | Biome / where | Age | In `map_world` v2 | Node model |
|---|---|---|---|---|---|
| Food | berry bushes | grassland edges | I | ✅ berries | `node_food` ✅ |
| Food | deer / game herds | forest clearings | I | 📄 (no deer model, no herd) | 🆕 `node_deer` + Deer rig |
| Food | farmland | flat grass by the village | I | ✅ 3 farms + hamlet | `farm` ✅ (age1_demo) |
| Food | fish shoals | lake and sea | I | ✅ shoals (discs) | 📄 `node_fish` |
| Wood | trees | forest W; scattered | I | ✅ 553 | library trees; chopped + stump variants 📄 |
| Stone | surface rocks → quarry | mountain feet, scree | I → II | ✅ `node_stone` | ✅ |
| Metal | ore outcrop → mine | mountain feet | I → II | ✅ `node_iron` | ✅ |
| Knowledge | — generated, never on the map | — | I | — | — |
| Gold | — markets, caravans, trade routes | — | II | — | 🆕 optional **gold vein** as a rare (§2c) |
| Coal | coal seam → colliery | mountain flank, badlands | IV | ✅ seam (black discs) | 📄 seam mesh + colliery |
| Oil | oil seep → land derrick; **offshore rig** | desert SE; shallow sea | V | ✅ 3 derricks, seep | 📄 derrick model; 🆕 offshore rig |
| Uranium | 2–3 deposits, glowing | volcano flank | VI | ✅ deposits (green) | 📄 `node_uranium` + refinery |

### 2b. Landscape features that are resources in disguise (doc 08)

| Feature | Why it matters | In v2 |
|---|---|---|
| Lake | fish, water for the mud road, a border you cannot walk across | ✅ |
| Sea + coast | fish, ports, offshore oil, naval | ✅ |
| River + fords + bridges | the classic chokepoint map; bridges are a Feudal build and a target | 📄 not in v2 — the biggest missing landform |
| Mountains + snow | stone / iron / coal at the feet, cliffs as walls | ✅ one blob; needs ridges |
| Volcano + lava lake + ash | uranium lives here; ash fall cuts vision map-wide | ✅ cone + lava; crater flat |
| Forest with edges and clearings | wood, hides units, blocks vehicles | ✅ |
| Desert, dunes, salt flat | oil, open ground for armour | ✅ |
| Marsh / bog | slows everything; the muddy road runs through it | ✅ mud road only |
| Cliffs and outcrops (V10) | a landmass you path around; where the ore is | 📄 |

### 2c. Extras — RoN-style rares and flavour (doc 12 has the rares list)

Doc 12 already defines nine rares (furs, amber, bog iron, horses, salt, saltpetre, rich coal, rubber, pitchblende),
6–10 per Standard map, each needing a Market or Trading Post to activate. Each one needs a **small map object** so
the player can see what they are fighting over. Nothing below is modelled.

| Rare / extra | Map object | Note |
|---|---|---|
| Furs | a trapper's rack + pelts by a forest edge | I |
| Amber | pale lumps on a shore | I |
| Bog iron | rust-red pool in the marsh | I |
| Horses | a wild herd on the steppe | II — also the first animal after deer |
| Salt | the salt flat (✅ in v2, as ground only) | II |
| Saltpetre | white crust in a cave mouth | III |
| Rich coal seam | a bigger, darker seam | IV |
| Rubber | a grove of pale trees in the wettest corner | V |
| Pitchblende | a second uranium glow, brighter | VI |
| 🆕 Gold vein | quartz seam in rock | would give Gold a place on the map; RoN's gold comes from a rare (gold) and from trade |
| 🆕 Geyser / hot spring | steam column, a healing spot | flavour + a place worth holding |
| 🆕 Obsidian field | black glass around the volcano (build.py already has the material) | flavour |
| 🆕 Whales / offshore shoal | deep-sea food for the Harbour | III |

---

## 3. Buildings — the full list by age, and what Dhruv named

Roster and costs are in doc 04 (39 building types). The columns here are the ones doc 04 does not have: **model
status** and **what it needs on the map** (a pad, a resource under it, a road). Assets marked ✅ are in `~/blender/base/`
or `blender/base/age1_demo/`.

### 3a. Universal — six model variants each (24 models)

| Building | I | II | III | IV | V | VI | Have |
|---|---|---|---|---|---|---|---|
| Town Centre | Longhouse | Keep | Town Hall | Exchange | City Hall | Command Centre | `hall` ✅ · `command` ✅ |
| House | Hut | Cottage | Townhouse | Terrace | Apartment | Block | `hut_a..e` ✅ |
| Barracks | Muster | Barracks | Drill Yard | Depot | Barracks | Garrison | `muster` ✅ · `barracks` ✅ (V) · `depot` ✅ (age5 lib) |
| **Wall + gate** | Palisade | Stone | Bastion | Brick | Concrete | Blast wall | `wall_bastion` ✅ (age4 lib) only. **Dhruv: "walls"** — see §6 for the wall as a living object |

### 3b. By age

| Age | Building | Have | Needs on the map |
|---|---|---|---|
| I | Storehouse · Rune Hall · Forge · **Watchtower** · Well · Stable · Boathouse · Farm | `stabbur` `runehall` `forge` `tower_a/b/c` `well` `stable` `boathouse` `farm` ✅ — Age I is complete | tower: a sightline; boathouse: shore |
| I | 🆕 **Woodcutter's lodge** ("wood chopper house") | `hut_woodcutter` ✅ exists in the library (age1) — not in the roster | a wood drop-off placed at the forest edge, like RoN's Lumber Mill. Adds a reason to hold the forest. |
| I | 🆕 Hunter's camp | — | a food drop-off near game; pairs with deer |
| II | Market · Caravan post · Quarry · Mine · Chapel · Archery range · Siege workshop · **Bridge** | none | quarry on rock cluster, mine on ore vein, bridge across a ford |
| III | University · Harbour · Cannon foundry · Bastion · Powder mill | `powder_mill` ✅ (age4 lib) | harbour: deep water |
| IV | Factory · Colliery · Rail depot · Artillery park · 🆕 **Sawmill** ("wood chipping unit") | none | colliery on a coal seam; sawmill = the Age IV woodcutter, converts wood faster, needs a road |
| V | Command Centre · Barracks · **Airfield** · Hangar · Field hospital · **Derrick** · Power plant · **Tank works** · AA battery · Bunker · Radio post | `command` `barracks` `airport` `hangar` `medical` ✅ · `bunker` `radio_post` `field_hospital` `artillery` ✅ (age4/5 lib) | airfield: 120 m of flat; derrick on an oil seep; **offshore rig** 🆕 on shallow sea |
| V–VI | 🆕 **Helipad / heliport** | — | **Dhruv: "helicopter"** — not in the roster at all; see §4 |
| VI | Laboratory · Uranium refinery · Radar station · **Missile silo** · ABM site | none — the silo is "the single highest-value model in the project" (doc 05) | silo: closed / opening / open states, missile a separate object |
| VI | 🆕 Oil refinery | — | RoN has one; doc 03 says oil is gathered straight from derricks. Decide: derrick-only (simpler) or derrick + refinery (a second target). |

---

## 4. Units — the full list by age, and what Dhruv named

Sixty unit types in doc 04; ten Age I models exist plus `musketeer` (age4 lib). The rows below are the ones Dhruv
asked about, with the rest summarised by the counter triangle (light > ranged > heavy > light; siege, air, naval,
support alongside).

| Kind | I | II | III | IV | V | VI | Have | Moves by |
|---|---|---|---|---|---|---|---|---|
| **Tanks / armour** | — | — | — | Armoured car | **Tank** | **Main battle tank** | none | code: tracks, turret, recoil, suspension |
| **Planes** | — | — | — | Observation balloon | **Fighter · Bomber** | **Jet · Strategic bomber** | none | code: bank-and-pitch, propeller |
| 🆕 **Helicopter** | — | — | — | — | (late V) | **Gunship · Transport heli** | none — **not in the roster**. Proposed: Age VI, the AT-missile counter to the MBT, and a transport that lifts a squad over walls. Needs a heliport (§3) and a rotor-spin motion (already in the code-driven list). |
| Siege / missiles | Axeman ✅ | Trebuchet · Ram | Bombard | Howitzer | Rocket truck | **Ballistic missile** (from the silo) | none | rigs + code |
| Cavalry / mobile | Horseman ✅ Horsearcher ✅ | Lancer ✅ Knight | Dragoon | Hussar | Half-track | APC | 3 of 8 | horse rig; wheels |
| Infantry (light / ranged / heavy) | Swordsman ✅ Archer ✅ Spearman ✅ Berserker ✅ | Man-at-arms Crossbow Pikeman | Musketeer ✅ Arquebus Pike & shot | Line infantry Rifleman Grenadier | Rifleman MG AT gun | Special forces Missile team AT missile | 5 of 18 | ONE humanoid rig, clips by weapon class |
| Naval | Longship | Cog | Galleon · Frigate | Ironclad | Destroyer · Carrier | Missile cruiser · Sub | none — **no boats exist at all** | hull rigs + bob/roll/sink code |
| Support | Standard ✅ | Monk | Surgeon | Engineer | Medic · Engineer | Radar truck | 1 | |
| Workers | Citizen ✅ (this repo) | | | | | 🆕 Oil worker? (doc 03: derricks are autonomous) | | |
| Animals | 🆕 Deer (hunt) · 🆕 wild horses (rare) · 🆕 fish (surface only) | | | | | | none | deer rig 📄 |

---

## 5. Roads, highways, rail, bridges — 🆕 not in any doc until now

Doc 08 says roads "written into the wear channel", and doc 04 has the Rail depot. Nothing says what road *kinds*
exist, what they do, or when. Rise of Nations has **no player-built roads** (its roads are decorative, painted by the
map); its logistics are rail-free too. So roads are our addition, and they must earn their place under the
territory rule: **a road only exists inside your borders, and it is where your attrition does not apply to you.**

| Kind | Age | Look | In `map_world` v2 | Gameplay (proposal) |
|---|---|---|---|---|
| Grass path | I | worn ground, no edge | ✅ paths to the berries | none — it is where citizens walk, painted by traffic |
| Dirt road | I–II | pale packed earth, 1.5 m | ✅ village → mine, coast, east | +10 % speed for everything on it |
| Muddy road | I–II | dark, ruts, puddles, through marsh | ✅ south of the lake | slower than open ground in rain / marsh; the honest "bad road" |
| Cobbled street | II–III | stone setts inside the walls | — | inside a city only; the city's own pad |
| Paved road / **highway** | IV–VI | grey asphalt, kerbs, lines from V | — | +30 % speed for wheels and tracks; vehicles **cannot** leave it in forest or marsh, so the highway *is* the front line. Painted with the same wear channel, one more band. |
| Rail | IV–VI | two rails, sleepers, between depots | — | doc 04: +60 % transport, instant resource move between depots |
| Bridge | II | timber, then stone (III), then steel (IV) | — | the only crossing that is not a ford; a target |
| Pier / dock | I | timber deck into the water | — | boathouse and harbour need one |
| Airstrip | V | flat pale strip, lights | — | part of the airfield model, not a road |

Runtime rule (doc 08): every kind is one more value in the terrain's wear channel, so roads conform to the ground for
free and z-fight with nothing. Highways and rail are the two that need *geometry* (kerbs, rails) on top of the paint.

---

## 6. Animations and effects on the map — what Dhruv named, against docs 09 and PROGRESS §5b

| Asked for | Status | What exists | What is missing |
|---|---|---|---|
| **Firing bullets** | 📄 designed | doc 09: muzzle flash 2 frames / 60 ms, smoke puff, shell eject from Age IV, MG flash every 3rd round + tracer every 5th, tank gun flash + recoil + dust sheet. §5b: Fire / KneelFire / Aim clips (0 of 8 firearm clips done) | the 8 firearm clips; a **tracer** mesh; bullet **impact** on ground / wood / stone / metal / flesh (doc 09 has arrow-stick and shell-impact only); ricochet sparks |
| **Missiles exploding** | 📄 for the warhead only | doc 09: the 14-second silo → detonation → mushroom sequence, second by second, with the delayed boom | 🆕 the *small* missiles: AT missile (streak + hit flash on armour), missile-team salvo, rocket truck barrage (rockets in a fan, smoke trails), **ABM intercept** (two streaks meet, an airburst, no ground blast), cruiser missiles. None specified. |
| **Tanks exploding** | 🆕 nothing | doc 09 specifies *buildings* destroyed (3 chunks, fire 20 s, rubble stays) and *bodies* (12 s, decal) | **vehicle death** is unspecified: flash → turret pops (a separate object thrown 3 m) → black smoke column 20 s → **burning wreck stays** as a permanent obstacle until evicted (same budget idea as corpses). Planes: spiral, trail, crater on impact. Ships: list and sink (sinking is in the code-driven list). |
| **Walls** | 📄 partly | doc 04: six variants; §5b: Gate Open/Close clips; build rise + collapse are code (done) | 🆕 the wall as a living object: **breach** (one segment crumbles to a gap with rubble, units path through), **repair** by a citizen, **garrison** — archers on the wall-walk firing over it, **scorch** on the outside face from artillery. The doc 02 beat "walls stop working in Age III" needs the *look* of a wall being shot through by cannon. |
| **Watchtower** | ✅ model, 📄 rest | `tower_a/b/c` exist; doc 04: vision + garrisoned archers | 🆕 archers visible on top when garrisoned, arrows from the top, a torch/brazier at night, a **lookout turn** idle, collapse into its own footprint (a tall thing must fall, not vanish), a flag showing the owner's colour |
| Oil (asked with "oil ..") | ✅ derricks in v2, 📄 pump clip | §5b: Derrick Pump clip; doc 03: autonomous, destructible | 🆕 **oil fire** when a derrick dies (a tall black column, 60 s — the one destruction you can see across the map), the seep as a dark slick, the offshore rig's flare |
| Explosions in general | 📄 shell impact | doc 09: flash → debris → smoke column → permanent crater decal | a **size ladder** (grenade · shell · bomb · rocket · warhead) so every explosion is the same effect at a different scale, and the "violence speed" rule (60–180 ms, no easing) applied to all of them |

Everything in this table that is a *clip* joins PROGRESS §5b when it is decided; everything that is an *effect*
belongs in doc 09's "Weapons and impacts" table. This file only records that they are needed.

---

## 7. The gaps this file closes — carry these into the docs when decided

1. **Roads have kinds and rules** (§5). Doc 08 needs a "Roads" table; doc 04 needs road, highway and bridge as
   builds with costs.
2. **Helicopters** are absent from the roster (§4). Adding them means a heliport, a rotor motion and an Age VI counter
   shift; it is a roster decision for doc 04, not an art decision.
3. **Vehicles dying** is unspecified (§6). Doc 09 has buildings and bodies; it needs a vehicle row and a wreck budget.
4. **Walls and towers as living objects** (§6): breach, garrison, repair, collapse.
5. **Small missiles and the ABM intercept** have no effect spec (§6).
6. **Woodcutter's lodge, sawmill, hunter's camp** (§3): the library already has `hut_woodcutter`; the roster does not.
7. **Offshore oil rig and an oil refinery** (§3): decide derrick-only or derrick + refinery.
8. **Rares need map objects** (§2c): nine rares in doc 12, none with a model.
9. **The size gap** (§1): the world map is 1/16–1/20 of RoN's largest. Growth is an instancing job in Blender and a
   territory job in the sim, both already on the queue (PENDING P4, doc 08).

Clash of Ages — a Rise of Nations clone. Changes here must be mirrored in the Decisions log in `PROGRESS.md`,
with the reason. Last updated 2026-09-26.
