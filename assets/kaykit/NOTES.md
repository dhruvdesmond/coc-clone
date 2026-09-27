# KayKit Adventurers — the character pipeline (CC0), 2026-09-27 (B32)

Source: github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0 (CC0, no attribution required).

## What it gives us (solves "the human" + "the skeleton" + "the x animation")
- **5 rigged, detailed, clean-stylized characters**: Barbarian, Knight, Rogue, Rogue_Hooded, Mage (`Characters/gltf/*.glb`).
- **A proper 41-bone humanoid rig** (`hand.l/r`, `handslot.l/r` weapon slots, IK), vs our old 11-bone figure.
- **76 animations baked in EACH glb**, incl. `Idle`, `Walking_A`, `Running_A/B`, `1H_Melee_Attack_Chop` (the tree-cutting
  swing, 26f), `2H_Melee_Attack_Chop`, Slice/Stab/Spin, `Block_*`, `Hit_A/B`, `Death_A/B`, `Cheer`, `PickUp`, `Interact`.
- **25+ accessories** (`Assets/gltf/*.gltf`): `axe_1handed`, `axe_2handed`, swords, shields, crossbow, staff, wand, quiver...

## How to use it (proven locally, tools/bl.sh)
- Import a character `.glb` -> armature `Rig` + mesh + all 76 actions.
- Attach a weapon: import `axe_1handed.gltf`, then `axe.parent=arm; parent_type='BONE'; parent_bone='handslot.r';
  matrix_basis=Identity` -> it snaps into the grip (KayKit weapons are authored for the slot).
- Play an action: `arm.animation_data.action = bpy.data.actions["1H_Melee_Attack_Chop"]`. Render frames, loop in ffmpeg.
- Chop video: `art/barbarian_chop.mp4`.

## Next (the character rollout, part of P10)
Map our unit roster (docs/04) onto these 5 + accessories: citizen/woodcutter = Barbarian or Knight + axe; swordsman =
Knight + sword+shield; archer = Rogue + crossbow; etc. Their animation names map onto our clip needs, so `rig_figure.py`,
`export_figure.py`, the figure-kit and the 11-bone rig are RETIRED for the game (kept only as history). Unity: the same
glb imports with its animations; wire our `RigAnimator` state -> KayKit action names.
