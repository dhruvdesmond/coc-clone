#!/bin/zsh
# Unity runner with the two guards this project keeps needing.
#   tools/u.sh compile              batchmode compile check -- exits non-zero and prints errors
#   tools/u.sh gui  <Class.Method>  GUI-mode run (needed for correct pixels) with a watchdog
#   tools/u.sh batch <Class.Method> batchmode run (fine for anything that does not render)
# WHY: in GUI mode a compile error opens a "Safe Mode?" dialog and Unity never exits -- a run once
# hung for 10 minutes on it. So `gui` always compile-checks in batchmode first.
UE=/Applications/Unity/Hub/Editor/6000.0.83f1/Unity.app/Contents/MacOS/Unity
P=/Users/dhruv/clash-of-clans/unity/ClashOfAges
LOG=/tmp/coa_$1.log
compile() {
  $UE -batchmode -projectPath $P -logFile /tmp/coa_compile.log -quit >/dev/null 2>&1
  if grep -qE "error CS[0-9]+" /tmp/coa_compile.log; then
    grep -E "error CS[0-9]+" /tmp/coa_compile.log | sort -u | head -20; return 1; fi
  echo "compile OK"
}
case $1 in
  compile) compile ;;
  batch)   $UE -batchmode -projectPath $P -executeMethod $2 -logFile $LOG -quit >/dev/null 2>&1; echo "log: $LOG" ;;
  gui)     compile || exit 1
           $UE -projectPath $P -executeMethod $2 -logFile $LOG -quit >/dev/null 2>&1 &
           pid=$!; ( sleep ${3:-420}; kill -9 $pid 2>/dev/null && echo "WATCHDOG killed Unity" ) &
           wd=$!; wait $pid 2>/dev/null; kill $wd 2>/dev/null; echo "log: $LOG" ;;
  play)    compile || exit 1
           $UE -projectPath $P -executeMethod $2 -logFile $LOG >/dev/null 2>&1 &
           pid=$!; ( sleep ${3:-600}; kill -9 $pid 2>/dev/null && echo "WATCHDOG killed Unity" ) &
           wd=$!; wait $pid 2>/dev/null; kill $wd 2>/dev/null; echo "log: $LOG" ;;
esac
