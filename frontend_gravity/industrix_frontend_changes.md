|<p>**INDUSTRIX**</p><p>Frontend Changes Specification</p><p>For: Antigravity (Frontend Team)</p><p>**Status: PENDING APPROVAL**</p><p>*Srijan 2026 · Production Engineering Dept · Jadavpur University*</p>|
| :- |

This document specifies all required changes to the Industrix team-facing frontend. It is based on a detailed review of the existing UI screenshots against the Frontend Developer Manual and the Complete Backend Reference. Changes are grouped by screen/component. This document must be approved before backend integration work begins.

|**WARNING**|Do NOT begin implementation until the organiser has approved this specification. Once approved, a separate Backend Integration Document will be issued.|
| :-: | :- |

## **Core Design Constraints — Non-Negotiable**
Before reading any individual change, every member of the frontend team must internalise the following constraints. These apply to every ADD, CHANGE, FIX, and REMOVE item in this document without exception.

|**Constraint**|**What This Means in Practice**|
| :- | :- |
|**Preserve the existing visual identity**|The current UI has a deliberate dark-theme aesthetic: dark backgrounds, monospaced labels, purple accent on active tabs, white text hierarchy. Do not change any of this. Every addition must look like it was always part of the original design.|
|**No font changes whatsoever**|Use the exact same font family, weights, and sizes already in use across the UI. Do not introduce any new typeface or size. New text elements must match the style of the nearest existing text element in the same screen area.|
|**No new colours**|Use only colours already present in the existing palette. The purple accent, dark card backgrounds, white/light-grey text, and amber/red for alerts are already established. New elements must draw from this palette exclusively. Do not introduce any new hex values.|
|**Minimal footprint**|Add only what is strictly necessary as listed in this document. Do not redesign, reposition, or restyle any existing element that is not explicitly listed as a CHANGE or FIX. If it is not mentioned in this document, leave it exactly as it is.|
|**Additive, not transformative**|New components must slot into the existing layout without displacing or resizing existing elements unless strictly unavoidable. Prefer adding below or alongside existing panels rather than restructuring them.|
|**All data from the backend — no hardcoding**|Every value shown to the team — funds, brand score, phase, cycle number, supplier list, machine condition, drone counts, quality thresholds — must come from the backend API. Nothing may be hardcoded or mocked. If the backend does not yet return a value, show a blank field or loading state, never a hardcoded placeholder.|
|**Field names must match the API exactly**|Every PATCH request body must use the exact field names defined in the backend spec: source\_id, quantity, transport, maintenance, rnd\_invest, upgrade\_to, wage\_level, target\_headcount, upgrade\_automation. Do not rename, abbreviate, or restructure these. The backend will silently ignore or reject mismatched keys.|
|**Phase values must match the API exactly**|Always compare the raw phase string: procurement\_open, production\_open, sales\_open, backroom, game\_over, waiting\_for\_first\_cycle, no\_active\_game. Never compare against display-formatted strings like 'Procurement Open'.|
|**PATCH semantics — send only changed fields**|The backend uses partial update (PATCH). Only send fields that the team has actually changed in a given submission. Sending the full form every time can overwrite carry-forward values unintentionally.|
|**Auth headers on every team request**|Every team endpoint call (GET and PATCH) requires x-team-id and x-team-pin as HTTP headers — not in the URL or request body. The public endpoints GET /team/status and GET /team/leaderboard require no headers.|

## **Change Legend**

|**Tag**|**Meaning**|**Action Required**|
| :- | :- | :- |
|**ADD**|New element|Build and add this — does not exist in current UI|
|**CHANGE**|Modify existing|Current behaviour is wrong or incomplete — replace it|
|**REMOVE**|Delete element|This element should not exist — remove entirely|
|**FIX**|Bug / logic fix|The element exists but its behaviour or data is wrong — fix the logic|

# **1. Global — Present on All Screens**
The following changes apply across the entire application regardless of which screen is active.

## **1.1  Phase-Driven UI — The Most Critical Change**
Currently the UI exposes Procurement, Production, and Sales simultaneously as navigable tabs. This is fundamentally incorrect. The game has exactly one active phase at a time. Teams cannot access another phase's form while a different phase is open.

|**WARNING**|The phase string returned by GET /team/status every 5–10 seconds is the single source of truth. The entire UI must be driven by this value. Nothing else determines what is shown.|
| :-: | :- |

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**ADD**|**Phase navigation tabs**|Procurement / Production / Sales tabs are always visible and clickable|Remove all phase-level tabs. Render only the active phase form based on the phase value from polling. Teams must never be able to click into a phase that is not currently open.|
|**CHANGE**|**Phase state machine**|*— No polling or phase gating implemented*|Poll GET /team/status every 5 seconds. On phase change: immediately re-render the correct screen, reset to 5-second polling, and show a phase-change notification toast.|
|**ADD**|**Backroom lock state**|*— Not implemented*|When phase = 'backroom': show only the leaderboard. All decision forms must be hidden (not just disabled). Display a banner: 'Backroom phase — wait for the organiser. No submissions accepted.'|
|**ADD**|**Game over screen**|*— Not implemented*|When phase = 'game\_over': show final leaderboard with winner announcement. All forms permanently locked. No polling needed.|
|**ADD**|**Waiting screen**|*— Not implemented*|When phase = 'waiting\_for\_first\_cycle': show a holding screen — 'Game starting soon...' with a subtle animation. No forms rendered.|

## **1.2  Top Bar — Notifications & Status**
A persistent notification bar must be added below the existing top navigation bar. This is separate from the current nav bar (HOME / MARKET / INVENTORY / EVENT). It handles two responsibilities: real-time notifications and connection sync status.

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**ADD**|**Notification toast bar**|*— Does not exist*|A slim bar (max 40px height) pinned below the nav. Shows dismissible toast messages. Types: SUCCESS (green) for saved decisions, ERROR (red) for API failures, INFO (neutral) for phase changes, WARNING (amber) for negative funds. Auto-dismiss after 5 seconds. New toasts stack above previous.|
|**ADD**|**Sync status indicator**|*— Does not exist*|Right side of the notification bar: a small dot (green = synced, amber = stale >15s, red = no connection) + text 'Last synced Xs ago'. Counts up from last successful poll response.|
|**CHANGE**|**Phase label in top nav**|PHASE: PROCUREMENT OPEN already shown top-right|Keep this. Add cycle number next to it: 'PHASE: PROCUREMENT OPEN · CYCLE 2'. Use the cycle\_number from the polling response.|
|**ADD**|**Funds display**|Shown only on Inventory screen|Global funds must also appear in the top nav bar at all times (not just inventory). Turn the value RED when funds < 0.|

## **1.3  Phase Timer / Sync Indicator**
The game has no fixed phase duration — the organiser controls all transitions. A countdown timer is therefore not appropriate. What IS required is a sync freshness indicator, which is covered in section 1.2. No separate timer widget is needed.

|**NOTE**|Do not add a countdown timer. The organiser may advance the phase at any moment. Instead, the sync status indicator (section 1.2) communicates to teams how fresh their current data is.|
| :-: | :- |

# **2. Procurement Screen**
The procurement screen is shown only when phase = 'procurement\_open'. Most of the layout is correct — tabbed per-component view, supplier info, transport mode. The following specific changes are needed.

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**FIX**|**Form pre-population**|Forms appear blank / default on load|On screen mount: call GET /team/procurement. Pre-populate every field (supplier, quantity, transport) with the returned values. Teams see last cycle's decisions as the starting point.|
|**CHANGE**|**Supplier comparison**|Single supplier shown in a text field|Show ALL available suppliers for the selected component as a selectable list or table — each row showing: supplier name, quality mean (Q), sigma (σ), cost per unit. Highlight currently selected supplier.|
|**FIX**|**Total cost preview**|Shows component cost only on right panel|Below the six component tabs, show a running TOTAL PROCUREMENT SPEND that sums: quantity × base\_cost × transport\_multiplier for all six components. Update live as values change. Currently it shows $0.00 and does not update.|
|**ADD**|**Raw materials stock**|*— Not shown on procurement screen*|Add a small stock display per component tab: 'Current stock: X units'. Pull from GET /team/me or inventory endpoint. Helps teams decide how many units to order.|
|**CHANGE**|**Send Decisions button**|Button present, submits immediately|Add a confirmation dialog on click: 'Confirm procurement decisions? This cannot be undone until the next phase.' with Confirm / Cancel. After successful PATCH: show SUCCESS toast 'Decisions saved at HH:MM'.|
|**ADD**|**Transport cost display**|Multiplier not shown to teams|Next to each transport option (Road / Rail / Air), show the cost multiplier: Road 1.0×, Rail 1.4×, Air 2.5×. Also show risk hint on hover: partial damage % and total loss %.|
|**ADD**|**Last saved timestamp**|*— Not shown*|After a successful PATCH, display below the Send Decisions button: 'Last saved at HH:MM:SS'. Persists until the next save.|

# **3. Production Screen**
The production screen is shown only when phase = 'production\_open'. Several structural issues exist in the current implementation.

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**FIX**|**Workforce section placement**|Wage Level and Target Headcount appear inside per-component panels|CRITICAL: Move wage\_level, target\_headcount, and automation\_upgrade OUT of the component tabs. These are company-wide decisions. Place them in a separate 'Global Workforce & Infrastructure' section BELOW all six component tabs. They apply to the whole factory, not per component.|
|**FIX**|**Form pre-population**|Forms load with defaults, not last cycle values|On screen mount: call GET /team/production. Pre-populate all fields with returned values — maintenance level, R&D invest, upgrade selection, wage level, headcount, automation level.|
|**ADD**|**Machine condition display**|*— Not visible in current UI*|Per component tab: show a health bar for machine condition (0–100). Color: green above 70, amber 40–70, red below 40. Below 40: add text label 'DEGRADED — output quality penalty active'. Show current machine tier (Basic / Standard / Industrial / Precision).|
|**ADD**|**Maintenance cost preview**|Cost shown in right panel only|Each maintenance option (None / Basic / Full / Overhaul) must show its cost inline next to the button label before the team selects it.|
|**CHANGE**|**R&D investment form**|R&D field shows a single number input|R&D needs two inputs per component: (1) focus area dropdown — Quality / Consistency / Yield, and (2) number of levels (0–5). Show cost preview: levels × 10,000 CU. Add note: 'Takes 2 cycles to arrive.' Show current R&D level per focus area.|
|**CHANGE**|**Machine upgrade section**|Automation upgrade shown as Manual / Semi-Auto / Full-Auto toggle — inside component panel|Rename section. Machine upgrade (upgrade\_to) is per-component and stays in the component panel — but must show: current tier, available higher tiers with buy cost and stat comparison (throughput, labour req, degradation rate, buy cost). Automation upgrade is company-wide — move to the global section.|
|**FIX**|**Cost summary**|Shows Maintenance Cost, R&D Cost, Workforce Cost, Total|Keep the cost summary panel. Ensure all values update live as selections change. Add per-component breakdown tooltip.|
|**CHANGE**|**Send Decisions button**|Button present|Same confirmation dialog and last-saved timestamp as procurement. See section 2.|

# **4. Sales Screen**
The sales screen is shown only when phase = 'sales\_open'. This screen does not appear in the provided screenshots — it must be built. The following spec covers the complete required behaviour.

|**WARNING**|The sales screen is entirely absent from the current UI. It must be built from scratch.|
| :-: | :- |

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**ADD**|**Sales screen**|*— Does not exist*|Build the entire sales screen. It must show four quality tier sections: REJECT, SUBSTANDARD, STANDARD, PREMIUM. Shown only when phase = 'sales\_open'.|
|**ADD**|**Per-tier drone count**|*— Does not exist*|Each tier section shows: units produced this cycle + units carried from stock = total available. Pull from GET /team/me.|
|**ADD**|**Action selector per tier**|*— Does not exist*|Per tier: dropdown or button group for action. REJECT: scrap or black\_market. SUBSTANDARD: sell\_market (discounted) or hold or scrap. STANDARD: sell\_market or hold or scrap. PREMIUM: sell\_market, sell\_premium, hold, or scrap. Pre-populate from GET /team/sales.|
|**ADD**|**Price override input**|*— Does not exist*|For sell\_discounted action: show a numeric input for price\_override. For sell\_premium (PREMIUM only): show the premium price (4,800 CU) for reference.|
|**ADD**|**Black market warning**|*— Does not exist*|When black\_market is selected for REJECT tier: show a prominent red warning — 'Black market sale: risk of discovery. If caught, fine = 3× revenue + severe brand hit.'|
|**ADD**|**Revenue estimate**|*— Does not exist*|Below all four tiers: show estimated total revenue for this cycle (computed client-side based on action and unit count). Note it as an estimate — actual depends on market share allocation.|
|**ADD**|**Brand score display**|*— Does not exist*|Show current brand score and tier (Poor / Fair / Good / Excellent) prominently. Add note: 'Brand score affects your share of market demand.'|
|**ADD**|**Default actions note**|*— Does not exist*|Show a note with the default actions if team does not submit: REJECT → scrap, SUBSTANDARD → sell discounted at 1,400 CU, STANDARD → sell at 3,000 CU, PREMIUM → sell at 3,000 CU (not premium price).|
|**ADD**|**Send Decisions button**|*— Does not exist*|Same confirmation dialog and saved timestamp pattern as other phases.|

# **5. Inventory & Logistics Screen**
The inventory screen (accessible via INVENTORY tab in top nav) looks largely correct. A few additions are required.

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**FIX**|**Funds color**|Funds shown in white regardless of value|If global funds < 0: display the funds value in RED with a warning label 'NEGATIVE — contact organiser'. If funds >= 0: keep current styling.|
|**ADD**|**Drone stock breakdown**|Shows Reject / Substandard / Standard / Premium counts|Keep this. Add: produced this cycle vs carried from previous cycle breakdown. Teams often forget about old inventory.|
|**FIX**|**Scrap Reject Units**|Button exists but greyed out|Button should be active and functional during all phases (not just procurement). Scrapping rejects is always allowed. Wire to the appropriate action or at minimum make it visually clear when it is available.|
|**ADD**|**Holding cost warning**|*— Not shown*|If team has unsold drones (Standard or Premium held): show a note — 'Holding cost: 40 CU per unsold drone per cycle.' with the total holding cost for current inventory.|
|**ADD**|**Government loan badge**|*— Not shown*|If team has an active government loan: show a visible badge or banner — 'GOVERNMENT LOAN ACTIVE — backroom deals blocked. Brand score penalty active.'|

# **6. Backroom Phase — Leaderboard**
During phase = 'backroom', teams see only the leaderboard. No decision forms are shown. The current round results screen (Image 4) is close to correct but needs the following changes.

|**Tag**|**Component**|**Current**|**Required**|
| :- | :- | :- | :- |
|**CHANGE**|**Own team highlight**|All rows shown identically|Highlight the viewing team's own row with a distinct accent colour (e.g. purple left border + subtle background tint) so teams can find themselves instantly.|
|**FIX**|**Score breakdown**|Shows: Score, Funds, Profit, Brand, Quality, Penalty|Keep these columns. Ensure they match the API response fields: composite\_score, closing\_funds, cumulative\_profit, brand\_score, quality\_avg, inventory\_penalty.|
|**ADD**|**Backroom banner**|*— No message shown*|Display a prominent banner at the top: 'Backroom phase — no submissions accepted. Approach the organiser desk to negotiate deals.' This phase = 'backroom' banner replaces all decision forms.|
|**CHANGE**|**Final leaderboard**|*— Not differentiated from mid-game*|When phase = 'game\_over' AND is\_final = true in API response: change heading to 'FINAL RESULTS' and show a winner announcement for rank 1 team.|
|**FIX**|**Cycle label**|Shows 'Cycle 1 Final Audit'|Pull cycle\_number from polling endpoint and show dynamically: 'Cycle N — Final Audit'.|

# **7. Polling & State Management**
This section specifies the exact polling behaviour the frontend must implement. The backend has no WebSockets or push notifications — all state changes are detected by polling.

### **Polling Rules**
- Default poll interval: every 5 seconds on GET /team/status
- If phase has not changed for 2 continuous minutes: back off to 15-second interval
- The moment the phase changes: immediately reset to 5-second polling
- On every poll response: update the sync status indicator (section 1.2) with current timestamp
- On phase change: show a toast notification — e.g. 'Phase changed: Production is now open'
- On connection failure (network error): show red sync indicator, do not show stale data without warning

### **Phase → Screen Mapping**

|**phase value**|**Screen to render**|
| :- | :- |
|**procurement\_open**|Procurement decision form — all inputs enabled, Send Decisions active|
|**production\_open**|Production decision form — all inputs enabled, Send Decisions active|
|**sales\_open**|Sales decision form — all inputs enabled, Send Decisions active|
|**backroom**|Leaderboard only. All forms hidden. Backroom banner displayed.|
|**game\_over**|Final leaderboard with winner announcement. All forms hidden permanently.|
|**waiting\_for\_first\_cycle**|Holding screen: 'Game starting soon…'. No forms.|
|**no\_active\_game**|Error screen: 'No active game found. Contact the organiser.'|

# **8. Implementation Checklist**
Use this as a sign-off checklist before returning the build for review.

|**#**|**Item**|**Section**|**Status**|
| :- | :- | :- | :- |
|1|Phase-driven rendering — only active phase form shown|1\.1||
|2|Polling implemented at 5s default with backoff|7||
|3|Phase change triggers toast notification|1\.2||
|4|Sync status indicator (dot + timestamp) in top bar|1\.2||
|5|Notification toast bar (success/error/info/warn)|1\.2||
|6|Funds shown in top nav bar at all times, red when negative|1\.2||
|7|Cycle number shown next to phase label|1\.2||
|8|Procurement: form pre-populated from GET /team/procurement|2||
|9|Procurement: all suppliers shown per component|2||
|10|Procurement: live total cost preview|2||
|11|Procurement: raw material stock per component visible|2||
|12|Procurement: transport multiplier and risk shown|2||
|13|Procurement: confirmation dialog on Send Decisions|2||
|14|Procurement: last saved timestamp shown after submit|2||
|15|Production: workforce section is GLOBAL (not per-component)|3||
|16|Production: form pre-populated from GET /team/production|3||
|17|Production: machine condition health bar per component|3||
|18|Production: maintenance cost shown inline per option|3||
|19|Production: R&D has focus area dropdown + level input|3||
|20|Production: machine upgrade shows tier comparison table|3||
|21|Production: live cost summary updates as inputs change|3||
|22|Sales screen built from scratch|4||
|23|Sales: four tier sections with drone counts|4||
|24|Sales: correct action options per tier|4||
|25|Sales: black market warning shown|4||
|26|Sales: revenue estimate shown|4||
|27|Sales: brand score displayed|4||
|28|Inventory: funds red when negative|5||
|29|Inventory: holding cost warning shown|5||
|30|Inventory: government loan badge shown when active|5||
|31|Backroom: all forms hidden, banner shown|6||
|32|Backroom: own team row highlighted in leaderboard|6||
|33|Backroom: FINAL RESULTS state when game\_over + is\_final|6||
|34|Waiting screen shown for waiting\_for\_first\_cycle|1\.1||
|35|Game over screen shown for game\_over|1\.1||

|<p>**PENDING ORGANISER APPROVAL**</p><p>Do not begin implementation until this document is approved. Backend integration spec will follow separately.</p>|
| :-: |

