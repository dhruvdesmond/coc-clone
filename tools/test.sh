#!/bin/zsh
# Headless sim tests. Safe in batchmode: no pixels involved.
P=${P:-${0:A:h:h}/unity/ClashOfAges}
${UE:-/Applications/Unity/Hub/Editor/6000.0.83f1/Unity.app/Contents/MacOS/Unity} -batchmode -projectPath ${P:-${0:A:h:h}/unity/ClashOfAges} -runTests -testPlatform EditMode -testResults ${LOGDIR:-/tmp}/coa_tests.xml -logFile ${LOGDIR:-/tmp}/coa_tests.log >/dev/null 2>&1
grep -E "error CS[0-9]+" ${LOGDIR:-/tmp}/coa_tests.log | sort -u | head
grep -o '<test-run [^>]*' ${LOGDIR:-/tmp}/coa_tests.xml | grep -oE '(total|passed|failed)="[0-9]+"' | tr '\n' ' '; echo
perl -0777 -ne 'while(/<test-case[^>]*\bname="([^"]+)"[^>]*result="Failed".*?<message><!\[CDATA\[(.*?)\]\]>/sg){print "FAIL $1: $2\n"}' ${LOGDIR:-/tmp}/coa_tests.xml | cut -c1-260
grep -ohE "TIMELINE[^<\]]*" ${LOGDIR:-/tmp}/coa_tests.xml | sort -u
