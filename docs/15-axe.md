# 15 · The axe — the plan Dhruv asked for (PENDING P1c: B3 + B4)

> "sound of axe.. improve it.. we should only hear more clearly the more closer the camera goes to it right?" (B3) and
> "also review the citizen and axe animation once" (B4). He asked for a **plan first, not code**. This is it. Nothing below
> is built; the order at the end says what to do first. Written 2026-09-26.

## 1. What is there today

| Layer | Fact (measured in the code) | File |
|---|---|---|
| The sound | Synthesised at start-up: 0.16 s of white noise with a 2 ms attack / 50 ms decay, plus a 95 Hz sine with a 90 ms decay. No file. | `Assets/Game/Fx/Sfx.cs` (`Clip.Chop`) |
| When it fires | `Sfx.Work(nodeKind, at)` when the sim's work timer wraps; volume 0.7, pitch jitter ±10 %. | `Sfx.cs` |
| Distance | One rule for every sound: `v *= clamp01(1.15 − d / 75)` where `d` = flat distance from the **camera focus point** plus `0.35 × camera height`. Below 0.02 it is not played. All sources are 2D (`spatialBlend = 0`): no panning, no engine attenuation, no low-pass. | `Sfx.Play` |
| Mixer | None. An 18-voice pool of `AudioSource`s on one object, plus wind and music sources. No groups, no limiter, no concurrency cap. | `Sfx.cs` |
| The animation | Chop is a woodsman's side swing (session 10). The blow lands at the END of the loop so the thock and the chips coincide with the sim's impact (DL48). Knees give at impact; a rebound replaces the old frozen half-second. | `blender/scripts/rig_figure.py` (`clip_chop`, `_beat`) |
| The model | Axe is a separate grip-origin prop parented to the `ForeR` bone; empty hands when carrying. | `blender/base/citizen/build.py` |

**B4's seven findings, status:** (1) sound 0.5 s late — ✅ fixed by `_beat`; (2) overhead chop — ✅ side swing; (3) freeze after
the hit — ✅ rebound; (4) legs static — ✅ knee dip; (5) left hand off the haft — 🟡 partly (the two-hand grip is posed, not
constrained: at some frames the left hand floats 3–5 cm off the haft); (6) axe head oversized — ✅ new prop; (7) axe held while
carrying — ✅ empty hands. **So the animation side of P1c is nearly done; what is left is the sound.**

## 2. What "hear it more clearly the closer the camera goes" needs — and why today's rule cannot do it

Today's rule scales one *volume*. Real distance changes three things, and volume is the least of them:

1. **Loudness** — inverse-ish with distance, but the RTS camera is never "at" anything; the reference point is the ground the
   camera looks at, which the code already uses. Keep that.
2. **Brightness** — air absorbs highs. From 60 m up an axe is a dull *thud*; from 18 m it is a *crack* with the chip's snap. A
   low-pass filter whose cutoff falls with distance is the single change that makes zoom-in *sound* like zoom-in.
3. **Space** — near: dry, sharp, a little stereo width from where the tree is on screen; far: a hint of the valley (a short,
   quiet reflection) and mono-ish. This is what tells the ear "over there" instead of "in my headphones".

And two things that are about *many* axes, not one: when eight citizens chop, the sound must not become a wall of clicks
(concurrency cap + cooldown), and the eight must not be in phase (start-phase jitter is already in the animation; the sound
needs pitch and timing jitter too).

## 3. The spec sheet for the axe sound (the P5b(a) template, filled in)

| Field | Spec |
|---|---|
| What it is | An iron axe biting into standing softwood. Two events in one: the **bite** (a bright crack, 5–15 ms) and the **body** (the trunk's thud, 60–120 Hz, 80–150 ms). Optional third: a chip snap 40 ms after the bite, 1 in 3 hits. |
| Frequency character | Bite: broadband 1.5–6 kHz, fast decay. Body: 70–140 Hz fundamental with a 250 Hz knock. Nothing above 8 kHz matters at RTS distance. |
| Duration | 140–220 ms total. Never longer: the loop is 1.6 s and a long tail smears eight overlapping citizens. |
| Volume range | 0.55–0.80 at the focus point; silent beyond 90 m of focus distance. Never the loudest thing on screen: a raid must always beat work. |
| Spatial | Position on the horizontal plane from where the tree is on screen (pan ±0.6). Low-pass cutoff: 9 kHz at 0 m → 1.2 kHz at 80 m of "effective distance" (flat distance + 0.35 × height, the existing measure). Reverb send 0 near → 0.25 far. |
| Variations | 4 bites × 3 bodies, chosen at random, pitch ±8 %. Timing jitter ±25 ms on the body so a squad of choppers never clicks in unison. |
| Concurrency | Max 4 axe voices at once, nearest-to-focus wins; a 5th steals the farthest. Beyond that, one shared "distant work" bed. |
| Cooldown | 90 ms per source. No two axe hits from the same citizen inside a loop (there cannot be, but assert it). |
| Ages | I–III the same sound; IV+ a sawmill replaces the axe (doc 14 §3) and this spec retires. |

## 4. What changes, in order

1. **A mixer with three groups** (`unity:audio-setup-mixers` skill): `SFX`, `Ambience`, `Music`, plus a **`Work` child of SFX**
   with a low-pass and a send to a short reverb. The distance rule moves from a per-call volume to **three parameters per
   play**: volume (as now), low-pass cutoff (new), reverb send (new).
2. **`Sfx.Play` becomes positional**: `spatialBlend = 1` with a custom rolloff curve built from the existing `d` measure (not
   the engine's 3D distance, which would use the camera position and make everything quiet at the default zoom). Pan from
   the tree's screen x. This is a ~30-line change.
3. **The clip itself**: keep synthesis (there are no audio files and Dhruv has not asked for any), but split it into bite +
   body + chip with the parameters in §3, and generate the 4 × 3 variants at start-up like the death vocals.
4. **The voice cap**: a `Work` voice pool of 4 with nearest-wins stealing; a distant-work bed (filtered noise pulses at the
   average work rate) when more than 4 are audible. This is what stops a 12-citizen economy from clicking.
5. **The measurement**: the bot (`DemoVerify`) already fires the first chop; add an assertion that the chop's played volume
   at the default zoom is within 20 % of the value at 18 m of zoom *after* filtering — i.e. loud-and-bright near, quiet-and-dull
   far, never silent at the default view.
6. **Left hand on the haft** (the one open animation finding): a two-frame check in `rig_figure.py` that measures the left
   fist to the haft line at the wind-up and the bite and prints the gap; fix the pose numbers until both are under 2 cm.

Cost: one session, all local (Unity audio cannot be verified on the cloud box). Nothing here changes the sim or the clips.
