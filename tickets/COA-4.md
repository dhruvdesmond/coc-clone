# COA-4 · Crossings — bridges, fords, ramps

**Epic:** COA-TILES · **Status:** TODO · **Depends:** COA-3 · **Tiles:** the crossing tiles (~4)

## Summary
The thing that just broke (B35): bridges and fords where the road actually **ramps onto the deck** instead of stepping,
the deck lands on both banks, and nothing blocks the mouth. Reviewed per crossing tile.

## Acceptance criteria
- [ ] The terrain **ramps** from the road up to the deck height on both banks — measured: no step > 0.3 m at the deck ends.
- [ ] The deck spans the water and lands ON both banks (deck ends within 0.3 m of terrain, both sides).
- [ ] **Keep-out:** no building or tree within 14 m of a bridge end or ford (assert).
- [ ] A proper bridge form (not a plain floating box); rails and abutments meet the ground.
- [ ] Each crossing tile reviewed close and passes; the road reads as continuous over the crossing.
