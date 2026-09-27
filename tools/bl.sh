#!/bin/zsh
# Throttled LOCAL Blender for SMALL tasks (Dhruv 2026-09-27, B30). Keeps the Mac usable while it runs:
#   * capped to BL_THREADS cores (default 6 of 12) so Chrome + the desktop keep the rest;
#   * niced down so the UI always wins a contended core;
#   * Metal GPU for renders, which offloads work from the CPU entirely.
#
#   tools/bl.sh <blender args...>                         e.g. --python blender/base/figures/build.py
#   tools/bl.sh <file.blend> --python <script.py> -- <args>
#   BL_THREADS=4 tools/bl.sh ...                          leave even more headroom
#
# USE FOR: single-asset builds, figure builds, material/shader tests, low-res preview renders, measure.py.
# NOT FOR (send to tools/cloud/vast.sh): the full map build (build.py, 30k-100k objects), final 4K renders,
# the flythrough, big clip bakes -- they eat RAM and minutes and would make the Mac crawl.
BL=/Applications/Blender.app/Contents/MacOS/Blender
THREADS=${BL_THREADS:-6}
export BLENDER_GPU=${BLENDER_GPU:-METAL} BLENDER_LIB=${BLENDER_LIB:-/Users/dhruv/blender}
echo "[bl] local Blender, $THREADS threads, niced (heavy jobs -> tools/cloud/vast.sh)"
exec nice -n 10 "$BL" -b --factory-startup -t $THREADS "$@"
