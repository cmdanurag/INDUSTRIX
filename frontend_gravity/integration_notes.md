# INDUSTRIX Frontend Integration Notes
*Location: `/frontend_gravity/integration_notes.md`*

## Missing API Endpoints
1. **`GET /team/sources`**: 
   - **Issue:** The `design.md` specifies loading raw material sources into the dropdown (displaying quality mean, sigma, and base cost). However, a search of the backend routers reveals there is no endpoint exposing `RawMaterialSource` data to the teams.
   - **Impact:** The Procurement page dropdowns cannot be dynamically populated with supplier options without backend modifications to expose the sources.
   - **Workaround Required:** Either the backend needs a new public/team endpoint, or the frontend must use a hardcoded fallback (`sources.json`) temporarily.

## Field Mismatches & UI/Backend Inconsistencies
2. **Production Upgrades Disabled in UI:**
   - **Issue:** The backend `ProductionPatch` scheme and game logic support `upgrade_to` (Machine Tiers) and `overhaul` maintenance. However, `design.md` explicitly forbids building these UI controls.
   - **Impact:** Teams will never be able to upgrade machines or overhaul them unless the organiser manually intervenes or the default actions persist. The frontend simply will not send these fields.

3. **Sales Actions Hidden:**
   - **Issue:** The `SalesPatch` allows specifying `sell_market`, `sell_premium`, `sell_discounted`, `hold`, and `scrap`, along with `price_override` per tier. Yet, the UI specification for Inventory only permits "SCRAP REJECT UNITS".
   - **Impact:** All other tiers (Substandard, Standard, Premium) will automatically fall back to their backend defaults (e.g., Substandard -> sell discounted at 1400 CU, Premium -> sell market at 3000 CU) without any team control.

## Data Structures
4. **Finished Drones Breakdown:**
   - The backend stores `drone_stock` as an array where index 0 = Reject, index 1 = Substandard, index 2 = Standard, index 3 = Premium. The frontend must explicitly slice and map this array linearly to display the counts. 
