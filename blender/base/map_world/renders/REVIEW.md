# REVIEW — world map build 2026-09-26 16:30 UTC

**PASS** · 103731 objects · build 173 s · review 1 s · device CUDA

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

**Since the last review:** no count changed


## look (docs/16-look.md §5)

| crop | saturation | shadows | white pt | black | spread | median | verdict |
|---|---|---|---|---|---|---|---|
| hero | 0.36 ❌ | 0.029 186° ❌ | 0.00% ❌ | 0.03% ✅ | 10 ✅ | 0.15 ✅ | 3/6 |
| region_village | 0.38 ❌ | 0.037 169° ❌ | 0.00% ❌ | 0.05% ✅ | 8 ❌ | 0.16 ✅ | 2/6 |
| region_hamlet_steppe | 0.36 ❌ | 0.033 144° ❌ | 0.00% ❌ | 0.00% ✅ | 7 ❌ | 0.14 ✅ | 2/6 |
| region_hamlet_fishing | 0.36 ❌ | 0.096 125° ✅ | 0.00% ❌ | 0.00% ✅ | 8 ❌ | 0.17 ✅ | 3/6 |
| region_camp_mining | 0.38 ❌ | 0.032 188° ❌ | 0.00% ❌ | 0.07% ✅ | 9 ❌ | 0.13 ✅ | 2/6 |
| region_bridge | 0.48 ✅ | 0.006 183° ❌ | 0.00% ❌ | 2.78% ❌ | 8 ❌ | 0.12 ✅ | 2/6 |
| region_ford | 0.45 ❌ | 0.013 178° ❌ | 0.00% ❌ | 0.51% ❌ | 8 ❌ | 0.17 ✅ | 1/6 |
| region_mountain | 0.24 ❌ | 0.052 210° ✅ | 0.00% ❌ | 0.00% ✅ | 5 ❌ | 0.20 ✅ | 3/6 |
| region_volcano | 0.27 ❌ | 0.047 210° ✅ | 0.00% ❌ | 0.02% ✅ | 6 ❌ | 0.12 ❌ | 2/6 |
| region_desert_oil | 0.15 ❌ | 0.224 60° ✅ | 0.00% ❌ | 0.00% ✅ | 4 ❌ | 0.25 ✅ | 3/6 |
| region_salt | 0.20 ❌ | 0.175 76° ❌ | 0.00% ❌ | 0.00% ✅ | 7 ❌ | 0.24 ✅ | 2/6 |
| region_lake | 0.42 ❌ | 0.036 157° ❌ | 0.00% ❌ | 0.00% ✅ | 8 ❌ | 0.13 ✅ | 2/6 |
| region_forest | 0.59 ✅ | 0.005 184° ❌ | 0.00% ❌ | 5.15% ❌ | 6 ❌ | 0.01 ❌ | 1/6 |
| region_herd | 0.59 ✅ | 0.006 183° ❌ | 0.00% ❌ | 2.50% ❌ | 8 ❌ | 0.04 ❌ | 1/6 |
| region_steppe_horses | 0.44 ❌ | 0.021 173° ❌ | 0.00% ❌ | 0.08% ✅ | 7 ❌ | 0.13 ✅ | 2/6 |
| region_rig | 0.36 ❌ | 0.130 198° ✅ | 0.00% ❌ | 0.00% ✅ | 8 ❌ | 0.18 ✅ | 3/6 |
| region_geyser | 0.53 ✅ | 0.007 181° ❌ | 0.00% ❌ | 0.67% ❌ | 9 ❌ | 0.07 ❌ | 1/6 |
