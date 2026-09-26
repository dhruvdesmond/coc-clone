# REVIEW — world map build 2026-09-26 16:16 UTC

**PASS** · 103731 objects · build 185 s · review 1 s · device CUDA

| kind | expected | found | status | detail |
|---|---|---|---|---|
| tree | 1200 | 2676 | PASS | - |
| rock | 80 | 891 | PASS | - |
| bush | 30 | 466 | PASS | - |
| berry | 24 | 27 | PASS | - |
| stone | 12 | 12 | PASS | - |
| iron | 12 | 12 | PASS | - |
| coal | 20 | 24 | PASS | - |
| uran | 12 | 15 | PASS | - |
| oil | 3 | 3 | PASS | - |
| salt | 1 | 1 | PASS | - |
| shoal | 16 | 20 | PASS | - |
| dead | 8 | 115 | PASS | - |
| building | 28 | 32 | PASS | - |
| people | 10 | 11 | PASS | - |
| bridge | 1 | 1 | PASS | - |
| pier | 1 | 1 | PASS | - |
| rare | 18 | 20 | PASS | - |
| rubber | 6 | 8 | PASS | - |
| deer | 12 | 15 | PASS | - |
| horse_wild | 5 | 6 | PASS | - |
| rig | 1 | 1 | PASS | - |
| whale | 1 | 1 | PASS | - |
| dressing | 60 | 72 | PASS | - |
| overlap | 0 | 0 | PASS | - |

**Since the last review:** tree: 262 → 2676; rock: 136 → 891; bush: 45 → 466; dead: 14 → 115


## look (docs/16-look.md §5)

| crop | saturation | shadows | white pt | black | spread | median | verdict |
|---|---|---|---|---|---|---|---|
| hero | 0.41 ❌ | 0.047 194° ✅ | 0.00% ❌ | 0.00% ✅ | 9 ❌ | 0.07 ❌ | 2/6 |
| region_village | 0.34 ❌ | 0.049 173° ✅ | 0.00% ❌ | 0.00% ✅ | 9 ❌ | 0.15 ✅ | 3/6 |
| region_hamlet_steppe | 0.32 ❌ | 0.042 154° ✅ | 0.00% ❌ | 0.00% ✅ | 8 ❌ | 0.15 ✅ | 3/6 |
| region_hamlet_fishing | 0.32 ❌ | 0.111 130° ✅ | 0.00% ❌ | 0.00% ✅ | 10 ✅ | 0.19 ✅ | 4/6 |
| region_camp_mining | 0.33 ❌ | 0.036 192° ❌ | 0.00% ❌ | 0.01% ✅ | 8 ❌ | 0.13 ✅ | 2/6 |
| region_bridge | 0.47 ✅ | 0.009 185° ❌ | 0.00% ❌ | 1.02% ❌ | 8 ❌ | 0.12 ✅ | 2/6 |
| region_ford | 0.42 ❌ | 0.017 182° ❌ | 0.00% ❌ | 0.11% ✅ | 10 ✅ | 0.17 ✅ | 3/6 |
| region_mountain | 0.23 ❌ | 0.070 209° ✅ | 0.00% ❌ | 0.00% ✅ | 5 ❌ | 0.25 ✅ | 3/6 |
| region_volcano | 0.32 ❌ | 0.049 209° ✅ | 0.00% ❌ | 0.00% ✅ | 6 ❌ | 0.12 ✅ | 3/6 |
| region_desert_oil | 0.07 ❌ | 0.253 100° ❌ | 0.00% ❌ | 0.00% ✅ | 6 ❌ | 0.28 ✅ | 2/6 |
| region_salt | 0.13 ❌ | 0.186 98° ❌ | 0.00% ❌ | 0.00% ✅ | 9 ❌ | 0.25 ✅ | 2/6 |
| region_lake | 0.39 ❌ | 0.050 163° ✅ | 0.00% ❌ | 0.00% ✅ | 10 ✅ | 0.15 ✅ | 4/6 |
| region_forest | 0.64 ✅ | 0.006 188° ❌ | 0.00% ❌ | 2.61% ❌ | 5 ❌ | 0.02 ❌ | 1/6 |
| region_herd | 0.58 ✅ | 0.007 187° ❌ | 0.00% ❌ | 0.76% ❌ | 6 ❌ | 0.04 ❌ | 1/6 |
| region_steppe_horses | 0.39 ❌ | 0.029 177° ❌ | 0.00% ❌ | 0.01% ✅ | 8 ❌ | 0.14 ✅ | 2/6 |
| region_rig | 0.35 ❌ | 0.138 200° ✅ | 0.00% ❌ | 0.00% ✅ | 8 ❌ | 0.20 ✅ | 3/6 |
| region_geyser | 0.50 ✅ | 0.011 183° ❌ | 0.00% ❌ | 0.06% ✅ | 9 ❌ | 0.08 ❌ | 2/6 |
