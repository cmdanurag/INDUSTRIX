# Integration Notes

This file logs mismatches between `design.md`, `industrix_frontend_manual.txt`, and actual backend implementation in `backend/`.

## Logged mismatches

1. **Missing supplier endpoint for team UI**
   - `design.md` expects `GET /team/sources` for procurement dropdown.
   - Backend has no `/team/sources` route.
   - Impact: procurement UI cannot render supplier metadata (name, quality_mean, quality_sigma, base_cost_per_unit) from API.

2. **Inventory endpoint lacks raw material stock and tier breakdown**
   - `design.md` inventory page expects per-component raw stock and reject/substandard/standard/premium breakdown.
   - `GET /team/me` currently returns:
     - `funds`, `brand_score`, `brand_tier`, `drone_stock_total`, `workforce_size`, `skill_level`, `morale`, `automation_level`, `has_gov_loan`
   - Impact: inventory page cannot show backend-accurate raw stock table or full tier breakdown from current team endpoint.

3. **Procurement cost estimation source mismatch**
   - `design.md` cost UI relies on supplier unit cost.
   - Without supplier metadata endpoint, exact frontend-side estimate cannot match backend.
   - Temporary implementation uses local fallback estimate logic and logs mismatch.

4. **Production maintenance option mismatch**
   - `design.md` restricts maintenance controls to `none|basic|full`.
   - Backend schema accepts `overhaul` as well.
   - Impact: UI intentionally does not expose `overhaul` per design.

5. **Production machine upgrade mismatch**
   - `design.md` says no machine-tier/condition UI.
   - Backend production schema includes optional `upgrade_to` in component decisions.
   - Impact: UI intentionally omits `upgrade_to` to follow design constraints.

6. **Phase-to-page simplification**
   - Backend phases: `procurement_open`, `production_open`, `sales_open`, `backroom`, `game_over`.
   - `design.md` maps these to 4 pages; current app auto-navigates by phase.
   - No conflict, but logged because navigation is fully phase-driven and may override manual route changes.
