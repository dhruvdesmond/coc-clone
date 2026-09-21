# PENDING — the queue, and the pointers

> **What this file is.** The single list of *what is not done yet*, in order, plus every **pointer** Dhruv gives
> — a bug seen while playing, a screenshot of something beautiful, a half-sentence of direction. Pointers are
> stored the moment they arrive and are never deleted, only marked done.
> **`PROGRESS.md` stays the history** (done, decisions and why, gotchas, session log) and holds the long detail
> this file links to. If the two ever disagree about what is pending, **this file wins.**
>
> Rules: newest pointer at the top of its section · every pointer keeps Dhruv's own words · every item says how we
> will know it is done · when something ships, mark it ✅ with the date and the commit, do not remove it.

---

## 1. Now — in flight

| # | What | Done when |
|---|---|---|
| ~~P1b~~ | ✅ **DONE 2026-09-21.** ~~Water that moves~~ (pointer B2). One custom shader: lapping shore foam, pale shallows → deep blue, crawling sun glitter, a slow swell, soft shadows instead of black ones. One wave function shared with C# so boats can bob in phase later. | ✅ bot: 52% of water samples change in 1.2 s, land control 0%. `art/verify_water_session9.png`. **Dhruv has not looked at it moving yet.** |
| **P1c** | **The axe** (pointers B3 + B4): he asked for a PLAN first. Review findings are in §5b B4. | He approves the plan. |
| ~~P1~~ | ✅ **DONE 2026-09-21.** ~~Buildings must never stand in water or inside trees~~ (pointer B1). Real rectangular footprints instead of circles; the starting Longhouse and the enemy hall sited through the same check as everything else; trees cleared by canopy, not trunk. | ✅ 3 new sim tests (13/13) · the bot asserts every building at start and end (**14 of 14 clean**) · bot still wins, 19.3 min · detail in PROGRESS session 9 / DL46. *Nothing is in flight now — next is P2.* |

## 2. Waiting on Dhruv

| # | What | Why it cannot be done for him |
|---|---|---|
| W1 | **Keep playing the demo** (PROGRESS N8) and keep sending screenshots — zoom feel on wheel and trackpad, is the first raid fair, is 15–20 min right. | Everything before 2026-09-21 was verified by a bot. The first ten minutes of a human playing found a bug the bot never would (B1). |
| W2 | `sudo xcodebuild -license accept` | Needs his password. Until then `python3` is dead on this Mac and every scripted edit goes through perl. |
| W3 | Q3 campaign or skirmish first · Q4 Steam or portfolio · Q10 should citizens carry at all (RoN's do not) · Q2 retire the mobile Norse RTS? | Product decisions. Detail in PROGRESS §8. |

## 3. Next builds — in this order

| # | What | Detail |
|---|---|---|
| **P2** | **The look.** Work through the visual pointers in §5, top to bottom. The first three (ground pads, softer light, painted ground) are cheap and change every screenshot. | §5 below |
| P3 | **A real opponent** replacing the scripted `RaidDirector` — it must gather, build, and decide. | PROGRESS N9 · `docs/06-ai.html` |
| P4 | **Cities, rare resources, 6 nations, the Armageddon counter** — what makes territory a *choice*. | PROGRESS N10 · `docs/12-territory.html` |
| P5 | **Remaining Age I assets**: palisade, longship, fishing boat, remaining nodes. There are no boats at all yet. | PROGRESS N7 |
| P5b | **Borrowed from the skills review (B6), no installs:** (a) an **SFX spec sheet** per sound, starting with the axe; (b) a **playtest report template** for Dhruv's sessions; (c) a **matchup matrix from the headless sim** — N battles per unit pair, assert none worse than 30/70 and the counter triangle is circular; (d) an **art bible** distilled from pointers V1–V14 so new assets share one look. | `CLAUDE.md` §2 "Third-party skills" |
| P6 | **Tool swapping** — the citizen holds an axe while farming and mining. Pick, hoe, basket, hammer as swappable hand props. | found in session 8 |
| P7 | **Animation Tier 2** — 29 clips, 8 rigs: riders, horse, elephant, deer, trebuchet, ram, gate, oars and sails. Then Tier 3 (16: firearms, crews, cannon) and Tier 4 (6: rocket truck, silo, derrick, missile launch). 29 of ~80 done. | PROGRESS §5b |
| P8 | **Code-driven motion** — 12 of 14 systems unbuilt: wheels, tracks, suspension, turret traverse, recoil, propellers, aircraft banking, ship bob/roll/sinking, radar and windmill, cloth sway, tree fall. | PROGRESS §5b G |
| P9 | Units for the 7 clips nothing plays yet: an axeman (2H×3), a standard bearer (Banner×2, and a banner pole needs an *upright* canonical facing), a Brace order, a Flee state. | PROGRESS N13 |

## 4. Backlog — unscheduled

Ages II–VI (~157 assets, `docs/05-assets.html`) · missile silo + the blast · the 35-second map showcase render · campaign ·
a real audio pass (everything is synthesised today) · **Windows build, never attempted** · save/load · multiplayer is out of scope.
Technical unknowns: shadow cascades across the zoom range (Q6) · APV probes across era swaps (Q7) · a 200-unit
stress scene on an RTX card (Q8) · no published asset-count benchmark for an indie RTS exists (Q9).

---

## 5. Pointers — what Dhruv has pointed at

### 5a. Visual reference — "see this.. how beautiful it is" (2026-09-21)
**Northgard** (`art/reference/northgard_village.png` — ⚠ NOT SAVED YET: the screenshot was in a macOS temp folder Claude cannot read. Dhruv: drop it and `bug_longhouse_in_lake.png` into `art/reference/`.) — (Shiro Games). Same subject as ours: a Norse village, an
RTS camera, territory on the map. What it does that we do not, most valuable first. Each line is a thing to build,
not a mood.

| # | What the reference does | Where we are | Cost |
|---|---|---|---|
| V1 | **Every building sits on a cleared pad** of pale trodden earth that fades into the grass. Nothing stands on raw lawn. This one trick is most of why the village looks *settled* rather than *placed*. | Buildings stand directly on grass; the Longhouse stood in a lake. P1 computes the footprint this needs. | low — a soft decal per building, sized from the footprint |
| V2 | **Light is soft and high-key.** Shadows are short, blue-tinted and maybe 35 % dark. Nothing on screen is black. | Our shadows are long and near-black and swallow a third of the frame (see `bug_longhouse_in_lake.png`). | low — sun elevation, shadow strength, ambient, a touch of fill |
| V3 | **The ground is painted**, not one colour: warm yellow-green on the crests, deeper green in the dips, dry ochre patches, grey scree by the rocks. | One grass material plus instanced tufts. | medium — a terrain shader blending 3–4 tones by height, slope and noise |
| V4 | **Trees come in stands, in three or four species and two seasons**: dark conifers, light broadleaf, and a scatter of **orange autumn** trees as accents. The orange is what makes the green read. | 310 trees, mostly one palette. We do have a few orange ones — use them deliberately, as accents at about 1 in 8. | low — palette + scatter rule in the map script |
| V5 | **The unknown is cloud, not black.** Fog of war is a soft volumetric mist that the land emerges from; the map's edge is sea-mist. | No fog of war at all. Map edge is a hard plane of water. | medium-high — a fog-of-war grid exists in design only |
| V6 | **The border is a quiet dashed white line** on the ground, following the terrain. | Ours is a glowing colour band with a fill tint. RoN uses colour, so keep colour — but thinner, calmer, and consider the dash. | low — shader parameters |
| V7 | **Roofs are the readable part**, and there are two families: golden thatch for economy, dark slate for housing/military. At this camera angle a building *is* its roof. | Our roofs are all dark green-black shingle; building types are told apart by shape only. | medium — roof material per building class, in `lib/materials.py` |
| V8 | **Chunky proportions.** Roofs oversized and steep, walls short, posts thick, everything slightly bowed. Reads from 60 m. | Ours are closer to real proportions and go thin at distance. | high — it is a modelling style; apply to NEW assets, do not redo old ones |
| V9 | **Life around every building**: crates, a cart, a table, a fence, drying racks, a tilled field with a fence, **chimney smoke**. | A few outbuildings and racks. No smoke, no carts, no per-building dressing. | medium — a dressing kit scattered around the pad (V1), plus a smoke particle |
| V10 | **Rock is a landmass**: big clustered blue-grey blocks forming a cliff you path around, and it is where the ore is. | Scattered single boulders. | medium — a cliff/outcrop generator in the map script |
| V11 | **Relief you can see**: the village is on a hill, land falls away to a misty shore. Height sells the 3D. | The terrain has height but the camera and flat lighting hide it. | low once V2 is done; then raise the relief near home |
| V12 | **Units are small but never lost**: a saturated tunic colour, and a hard rim against the ground. | Done in session 5 (silhouette pass, team disc, 1.38× scale). Keep. | — |
| V13 | **UI**: resources in one top strip with **+rate** beside each number · a **season/calendar** widget that warns ("Prepare for winter!") · a building card with portrait, **worker slots** and one-line purpose · a roster of civilians by job · a territory-coloured minimap. | Top strip without rates; command panel; minimap with borders. No rates, no portrait card, no job roster. | medium — `Hud.cs`; +rate is the cheap, high-value one |
| V14 | **A slight tilt-shift / depth haze** — far land is paler and bluer. | None. | low — URP fog + a volume tweak |

**What NOT to copy.** Northgard is tile-territory with a fixed building count per tile and no free borders. We are a Rise of
Nations clone: borders are *continuous colour* that grows from cities. Take the craft (V1–V14), not the rules.

### 5b. Bugs and notes from playing
| # | Date | Dhruv's words | Status |
|---|---|---|---|
| B6 | 2026-09-21 | "go over these skills, see if anything would be useful for our game development, and add it to our claude.md in this gaming folder. tell me also about those skills" | ✅ 2026-09-21 — six read file by file, none installed; verdicts + three borrowed ideas in `CLAUDE.md` §2; follow-ups are P5b |
| B5 | 2026-09-21 | "any skll it there online for these amimations and game design? tell me.." | ✅ checked 2026-09-21 (web search limit raised to 1000 in `~/.claude/settings.json`). **Installed already:** official `unity` plugin — has `audio-setup-mixers` + `optimize-audio` (use for B3), **no animation skill**. **Found online, none installed, all third-party — read the SKILL.md before installing:** `CoplayDev/unity-mcp` (MIT, 47 tools, drives the live Editor incl. an animation tool group; Unity also has an official MCP now) · `ahujasid/blender-mcp` (drives live Blender; reviews say weak at rigging/precise dimensions — our headless scripts already beat it there) · Unity skill packs (`Besty0728/Unity-Skills`, a 35-skill Unity 6 set on claudepluginhub incl. animation/Animancer/audio) · game DESIGN: `baxatron-git/claude-game-design-suite` (22 skills, vision→delivery), `Donchitos/Claude-Code-Game-Studios`, `agent-skills-hub` game-design. **Verdict:** nothing replaces our own pipeline for procedural clips; worth trying = unity-mcp (see the game while editing) and one game-design pack for balance/feel reviews. |
| B4 | 2026-09-21 | "also reivew the citizen and axe animation once.. jsut that.." | ✅ reviewed 2026-09-21, nothing changed. **Findings:** (1) the "thock" and the wood chips fire **~0.5 s AFTER the axe lands** — the clip lands at 70% of its 1.6 s loop, the sim fires its impact at 100%; same fault in Hammer and Mine. (2) It is an **overhead splitting chop**; a standing tree wants a **diagonal side swing into the trunk** with the torso turning — overhead is right for Mine, wrong here. (3) After the hit he **freezes for 0.5 s**: no rebound, no settle. (4) Legs never move: no knee dip or weight shift at impact. (5) The left hand is not on the haft. (6) The axe head is oversized and reads as a spade from above (model, not animation). (7) While carrying wood he still holds the axe upright in front of him. |
| B3 | 2026-09-21 | "sound of axe.. improve it.. we should only hear more clearly the more closer the camera goes to it right?" | 🟡 he asked for a PLAN first, not code |
| B2 | 2026-09-21 | "animation for water?" — the lake and sea are a static, near-black plane | ✅ 2026-09-21 — `COA/Water` shader + `WaterSurface.cs`. Deliberately left for later, as pointers: boat wakes · ripples round wading units · a river with a flow direction · waterfalls · rain rings · refraction · sea-mist at the map edge (that one is V5) |
| B1 | 2026-09-21 | "house on lake.. and on trees also.." (`art/reference/bug_longhouse_in_lake.png`) | ✅ fixed 2026-09-21. It was the **enemy's** hall: the camp search could never succeed on this map and silently fell back to an unchecked point 29 m from the player. Also found by the new check: the enemy tower stood inside 3 trees. |

### 5c. Standing direction (things he has said that outlive a session)
- 2026-09-21 — "store more and more pointers." → this file. Every screenshot and remark lands in §5 first, work second.
- 2026-09-20 — "best possible quality.. for nvidia graphic cards and macbook pro quality.. not integrated graphics."
- 2026-09-20 — "dont wait for me.. make best possible assumptions on your own."
- 2026-09-20 — it is a **Rise of Nations** clone; the folder keeps the `clash-of-clans` name.
- 2026-09-20 — "THIS IS THE CITIZEN? lets fix it first.." → when he shows something ugly, it jumps the queue.
- From the first brief, not yet built: boats · a missile silo and its blast · blood that stays 10–15 s ✅ · death sounds ✅ · a 35-second showcase of the map.
