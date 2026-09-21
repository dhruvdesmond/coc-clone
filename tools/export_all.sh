#!/bin/zsh
# Re-export every Blender asset the demo uses. Reads ~/blender (never writes there).
BL=/Applications/Blender.app/Contents/MacOS/Blender
R=/Users/dhruv/clash-of-clans; M=$R/unity/ClashOfAges/Assets/Models; B=~/blender/base
mkdir -p $M
asset()  { $BL -b --factory-startup $1 --python $R/blender/scripts/export_assets.py -- --name $2 --out $M 2>&1 | grep -E "^\[asset\] (joined|dims|!)|Traceback|Error" ; mv -f $M/$2.meta.json $M/$2.meta.json.txt 2>/dev/null }
figure() { $BL -b --factory-startup $1 --python $R/blender/scripts/rig_figure.py -- --name $2 --out $M ${=3} 2>&1 | grep -E "^\[rig\]|^\[figure\] normals|Traceback|Error|line [0-9]" ; mv -f $M/$2.meta.json $M/$2.meta.json.txt 2>/dev/null }
case ${1:-all} in
  figures|all)
    # ONE clip library for every humanoid (PROGRESS N12): same rig, plus the clips. Figures carry none.
    figure $B/starter/models/villager.blend humanoid_clips "--prefix villager --with-clips"
    # the citizen is authored in THIS repo (blender/base/citizen/build.py); the library keeps the old villager as its body
    $BL -b --factory-startup --python $R/blender/base/citizen/build.py 2>&1 | grep -E "^BUILT|Traceback|Error"
    figure $R/blender/base/citizen/models/citizen.blend villager "--prefix citizen"
    for t in axe pick hoe hammer; do
      $BL -b --factory-startup $R/blender/base/citizen/models/tool_$t.blend --python $R/blender/scripts/export_assets.py -- --name tool_$t --out $M --keep-origin --recalc-normals 2>&1 | grep -E "^\[asset\] (joined|dims|!)|Traceback|Error"
      mv -f $M/tool_$t.meta.json $M/tool_$t.meta.json.txt 2>/dev/null
    done
    for u in swordsman spearman archer; do figure $B/troops/models/$u.blend $u; done ;|
  buildings|all)
    asset $B/hall/models/hall.blend hall
    for h in a b c d e; do asset $B/huts/models/hut_$h.blend hut_$h; done
    for o in stabbur forge well stable; do asset $B/outbuildings/models/$o.blend $o; done
    asset $B/towers/models/tower_a.blend tower_a ;|
  new|all)
    for n in runehall muster farm; do asset $R/blender/base/age1_demo/models/$n.blend $n; done ;|
  nodes|all)
    for n in wood stone iron food; do asset $B/starter/models/node_$n.blend node_$n; done ;;
esac
