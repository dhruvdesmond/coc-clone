#!/bin/zsh
# Re-export every Blender asset the demo uses. Reads ~/blender (never writes there).
BL=/Applications/Blender.app/Contents/MacOS/Blender
R=/Users/dhruv/clash-of-clans; M=$R/unity/ClashOfAges/Assets/Models; B=~/blender/base
mkdir -p $M
asset()  { $BL -b --factory-startup $1 --python $R/blender/scripts/export_assets.py -- --name $2 --out $M 2>&1 | grep -E "^\[asset\] (joined|dims|!)|Traceback|Error" ; mv -f $M/$2.meta.json $M/$2.meta.json.txt 2>/dev/null }
figure() { $BL -b --factory-startup $1 --python $R/blender/scripts/export_figure.py -- --name $2 --out $M ${3:+--prefix} $3 2>&1 | grep -E "^\[figure\]|Traceback|Error|line [0-9]" ; mv -f $M/$2.meta.json $M/$2.meta.json.txt 2>/dev/null }
case ${1:-all} in
  figures|all)
    figure $B/starter/models/villager.blend villager
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
