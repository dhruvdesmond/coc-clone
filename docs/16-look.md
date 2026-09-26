# 16 · The Look — what the world has to look like, and how a render passes or fails

> The standard for every render of the world map, written the way Kargil's `LOOK-REFERENCE.md` was: references you chose,
> a palette that binds, a light rig, and a table a render is **scored** against (`map_world/measure.py`), not admired.
> Direction (PENDING B25, 2026-09-26): *beauty is the motive; Ladakh is one example, not the ceiling; water that moves,
> clouds, sandstorms, snowstorms; imagine the frame, then replicate it.* Stylised, not realistic: saturated, chunky, readable
> at 60 m. No image textures (rule 2 stands).

## 1. The frame we are aiming at

High noon over the village. The ground is a **meadow, not a green**: yellow-green on the crests, deeper green in the dips,
dry ochre where the paths wear through, grey scree at the rock feet; at 70 m it is visibly made of blades and pebbles.
Shadows are short and **blue-grey, never black**. A cloud's shadow crosses the fields; the clouds have form and drift. The
river has a **current**: foam at the fords, ripples against the bridge piers, sun glitter that crawls. Smoke rises from the
hall. Fences, carts and drying racks sit around every pad; the farms have crop rows. Far away the desert is an **amber
haze** where a sandstorm walks the dunes, and the massif is half lost in a **snowstorm** whose streaks blow off the ridges.
Far land is paler and bluer than near land. Everything reads at a glance.

## 2. The references, and what to take from each

| # | Reference | Take | Leave |
|---|---|---|---|
| R1 | **Rise of Nations, Industrial age** — `art/reference/ron_industrial.jpeg` | the ground: painted yellow-green grass (dominant `0.42,0.45,0.12`), dirt roads with edges, fields with rows, cliffs with strata; saturation **0.58**; nothing on screen washed out | the 2003 sprite buildings, the flat sea |
| R2 | **Northgard camp** — `art/reference/northgard_camp.png` | pads of trodden earth under every building, chunky roofs, warm shadows (`0.22,0.21,0.16`), a **white point** (1.1 % of pixels clip), life around each pad | tile territory |
| R3 | **Kargil / Nubra** (`~/game-ideas/docs/LOOK-REFERENCE.md`) | *contrast is the subject*: vivid green against ochre; shadows blue-grey because a bright sky fills them; a sky-fill light rig; stylised beats half-finished realism | the cold-desert flora |
| R4 | **Weather** — Dhruv to pick one (a sandstorm or snowstorm frame he likes) | how a storm reads at distance: a moving wall with a lit edge, not fog | — |

**Where we stand (measured 2026-09-26, `measure.py`):** our village crop has saturation **0.33**, shadows `0.08,0.15,0.12`
(green-black, luma p5 = 0.011), **no** white point (0.00 %), dominant ground `0.68,0.77,0.54` (pale mint). The desert crop
is a beige sheet: median luma 0.71, saturation **0.15**, four tone bins. The hero has 1 % of pixels at black.

## 3. The palette — binding

Derived from R1–R3. Linear-ish sRGB as the shader base colours; the rendered pixel will differ with light, which is why the
render is scored on saturation and spread, not on matching these numbers.

| class | colour | why |
|---|---|---|
| **meadow crest** | `0.42, 0.46, 0.12` | R1's grass: yellow-green, not mint. The most-seen colour in the game |
| **meadow dip** | `0.20, 0.30, 0.08` | deeper, cooler, wetter; the crest/dip pair IS the "painted" look |
| **dry / worn** | `0.55, 0.47, 0.22` | straw-ochre where paths wear through; roads' shoulders |
| **dirt road** | `0.38, 0.27, 0.15` | darker than the shoulder so the road has an edge |
| **cobble** | `0.34, 0.33, 0.30` | grey setts; never white |
| **scree** | `0.50, 0.48, 0.45` | grey, deliberately not ochre (Kargil) |
| **sand** | `0.62, 0.52, 0.34` | **ochre**, R3's barren; today's `0.90,0.86,0.77` was the fault |
| **ash / badlands** | `0.16, 0.14, 0.13` | near-black warm, with obsidian glints |
| **snow** | `0.92, 0.94, 0.97` | bright, faintly blue, never grey |
| **water** | `0.05, 0.16, 0.22` deep → `0.22, 0.42, 0.46` shallow | teal-blue, opaque, foam white at the edge |
| **thatch / timber** | `0.55, 0.42, 0.20` | warm; buildings must be warmer than the ground |
| **shingle** | `0.18, 0.18, 0.17` | dark cool; roofs are the readable part (V7) |
| **team blue** | `0.15, 0.30, 0.75` | the citizen; saturated against everything above |

## 4. The light — one rig, written down

| Element | Value | Why |
|---|---|---|
| Sun | elevation **62°**, azimuth 205°, energy 3.2, angle 6° | high noon: short shadows; a wider disc softens edges |
| Sky | `ShaderNodeTexSky` multiple-scattering, strength 0.7 | the fill that turns shadows blue-grey |
| Fill | one cool sun lamp from behind, energy 0.35, `cast_shadow = False`, colour `0.75, 0.85, 1.0` | Kargil's sky-fill: art-directable, almost free |
| Clouds | a volume slab 400–600 m up, noise density, wind vector, **casts shadows** | cloud shadows are what make a map "outdoors" |
| Haze | world volume, density 0.004, height falloff, colour `0.60, 0.72, 0.85` | far land paler and bluer (V14) |
| Exposure | set so **0.5–2 %** of pixels clip white; AgX, look Medium High Contrast | the white point is the single most measurable light fault |
| Camera | pitch 58° for the hero (today 50° = a third sky), 50° for crops | the frame is land |

## 5. The table — every render is scored against this

`measure.py` prints the numbers; `REVIEW.md` gets a `look` section with one line per row. Thresholds come from R1/R2.

| row | pass | fail | measured by |
|---|---|---|---|
| **Saturation** | crop mean ≥ **0.45** | ≤ 0.35 (today: 0.33) | mean saturation |
| **Shadows** | darkest-15 % luma ≥ 0.04 (R1: 0.02 at p5, so no darker than the references) **and** hue 180–260° (blue-grey) or neutral | luma < 0.04, or green-black (today: hue 160°, luma 0.011) | shadow tone |
| **White point** | 0.5–2 % of pixels > 250 | 0 % (today) or > 4 % | white point |
| **Black floor** | < 0.3 % of pixels < 12 | ≥ 1 % (today's hero: 0.99 %) | black floor |
| **Ground tone spread** | ≥ 10 hue-luma bins > 1 % in a land crop | ≤ 6 (today's desert: 4) | tone spread |
| **Desert** | dominant ochre, saturation ≥ 0.35 | beige, saturation 0.15 | dominant colours |
| **Contrast** | median luma 0.12–0.35 (R1 0.14, R2 0.28) | > 0.40 (washed, today's village: 0.42) | luma p50 |
| **Road edge** | a shoulder band visible at 70 m | a hard paint line | eye, village crop |
| **Ground detail** | blades/pebbles visible at 70 m | flat colour | eye, ford crop |
| **Dressing** | every pad has ≥ 3 props and a fence or smoke | bare pads | placement count per building |
| **Water** | shallow-to-deep ramp, foam at edges, glitter | flat blue plane | eye, ford + lake crops |
| **Sky** | clouds with form, a cloud shadow on land | empty flat sky | eye, hero |
| **Haze** | the far massif paler and bluer than the near forest | same tone at every distance | luma/sat of far vs near patch |
| **Weather** | storm reads as a moving wall with a lit edge | uniform fog | eye, desert + mountain crops |
| **Silhouette** | trees, buildings, citizens identifiable in a 40-px thumbnail | blobs | eye, 40-px test |
| **Nothing black** | black floor row | | |

## 6. The three weather states, and where each lives

| state | where | how it is made (Blender) | Unity counterpart |
|---|---|---|---|
| **Clear with clouds** | everywhere | two volume slabs (dense low with shadows, thin high), one wind vector | URP volumetric clouds (HDRP-only) → a cloud-shadow cookie on the sun + a skybox layer |
| **Sandstorm** | the desert quarter | a volume box on the dunes, wind-sheared noise, amber scatter, animated; dead trees lean; derricks fade in and out | a local fog volume + a particle sheet, VFX Graph |
| **Snowstorm** | the massif | fine noise volume with a strong wind vector, streaks off the ridges (a thin aligned volume), snow cover pushed lower on the storm side | local fog volume + VFX streaks; snow cover as a terrain layer |
| Water | river, lake, sea | two wave sets by frame time, flow along the river, foam under 0.4 m depth, glitter | `COA/Water` already shares the wave function |
| Smoke | halls, forges | a thin volume cone per chimney, drifting with the wind | a particle system per building |

## 7. Order of work (plan B25)

A this standard → **B light + sky** (every pixel) → **C ground** (every pixel) → D dressing → E water → F weather → G the
30-second flythrough on the cloud (the one job that loads the GPU near 100 %). Each phase ends with the 16 crops scored.

Clash of Ages — a Rise of Nations clone. Changes here must be mirrored in the Decisions log in `PROGRESS.md`. 2026-09-26.
