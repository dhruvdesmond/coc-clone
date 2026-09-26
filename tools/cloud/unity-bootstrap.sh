#!/bin/bash
# Unity on the cloud box (plan Phase 4): what CAN run headless on Linux -- the 13 EditMode sim tests, the compile check,
# the SliceZero asset asserts and (later) the Windows build. What CANNOT: DemoVerify's play-mode screenshots and the
# water pixel-diff, which need a GUI editor on a real GPU display; those stay on the Mac.
#
#   tools/cloud/vast.sh run 'bash tools/cloud/unity-bootstrap.sh install'   # Unity CLI + editor 6000.0.83f1 + Windows Mono module (~4 GB)
#   tools/cloud/vast.sh run 'bash tools/cloud/unity-bootstrap.sh login'     # prints a URL: Dhruv opens it once in his browser
#   tools/cloud/vast.sh run 'bash tools/cloud/unity-bootstrap.sh license'   # Unity Personal, EULA accepted
#   tools/cloud/vast.sh run 'bash tools/cloud/unity-bootstrap.sh test'      # tools/test.sh on the box (first run imports Library, ~15 min)
#
# The licence token is sealed to the machine, so a fresh rental means a fresh login; a stopped-not-destroyed box keeps it.
set -e
export UNITY_NON_INTERACTIVE=1 UNITY_NO_BANNER=1
VER=6000.0.83f1
export UE=${UE:-$HOME/Unity/Hub/Editor/$VER/Editor/Unity}
export P=/work/repo/unity/ClashOfAges
export LOGDIR=/work/logs
case ${1:-help} in
  install)
    command -v unity >/dev/null || curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
    export PATH="$HOME/.unity/bin:$PATH"
    unity --version
    unity install $VER --module windows-mono --yes --accept-eula
    unity editors --installed --format json | head -40
    ;;
  login)   export PATH="$HOME/.unity/bin:$PATH"; unity auth login ;;                 # prints the sign-in URL (headless-aware)
  license) export PATH="$HOME/.unity/bin:$PATH"; unity license activate --personal --accept-eula; unity license status ;;
  test)    mkdir -p $LOGDIR; cd /work/repo && zsh tools/test.sh ;;
  compile) mkdir -p $LOGDIR; cd /work/repo && zsh tools/u.sh compile ;;
  windows) mkdir -p $LOGDIR; cd /work/repo && zsh tools/u.sh batch Builder.PerformWindowsBuild && ls -la unity/ClashOfAges/Build/ ;;
  *) sed -n '2,12p' "$0" ;;
esac
