INDUSTRIX — Frontend Developer Manual

**INDUSTRIX**

*Market Simulation Game*

**Frontend Developer Manual**

Production Engineering Department — Jadavpur University

Srijan 2026


# **1. Introduction and Overview**
Industrix is a turn-based market simulation game where teams act as CEOs of competing drone manufacturing companies. This document is the complete reference for frontend developers building the team-facing interface and the organiser dashboard.

The backend is a FastAPI application exposing a REST API. The frontend communicates exclusively through HTTP requests — there are no WebSockets, no push notifications, and no server-sent events. The frontend polls a single status endpoint to detect phase changes, and teams submit their decisions via PATCH requests at any time during the relevant phase.

## **1.1 The Two Interfaces**
Two separate frontend interfaces are required:

- Team Interface — used by the 5-20 competing teams. Each team authenticates with their team ID and PIN. They submit decisions and view their own inventory. During the backroom phase they view the leaderboard.
- Organiser Dashboard — used exclusively by the game organisers. Authenticated with a long random secret. Controls phase advancement, records deals, manages loans, and triggers game end.

## **1.2 The Product Being Manufactured**
Teams manufacture fire-fighting drones. Each drone is assembled from six components:

|**Airframe**|The physical body structure of the drone|
| :- | :- |
|**Propulsion**|Motors and rotors that provide lift and movement|
|**Avionics**|Navigation, control, and communication electronics|
|**Fire Suppression**|The actual fire-fighting payload (tank, nozzle, agent)|
|**Sensing & Safety**|Sensors, obstacle avoidance, emergency systems|
|**Battery**|Power source — capacity affects flight time and payload|

## **1.3 Quality Grades**
Every unit of raw material, every finished component, and every assembled drone has a quality grade from 1 to 100. The game uses three global thresholds to classify drones for sale:

|**Below qr\_hard**|REJECT — cannot be sold in regulated markets|
| :- | :- |
|**qr\_hard to qr\_soft**|SUBSTANDARD — can be sold at a discount|
|**qr\_soft to qr\_premium**|STANDARD — sold at the standard market price|
|**qr\_premium and above**|PREMIUM — sold at a premium price|

Default values: qr\_hard = 30, qr\_soft = 50, qr\_premium = 75. The organiser can change these between cycles.


# **2. Game Sequence and Phase Machine**
The game runs in cycles. Each cycle has exactly four phases, executed in strict order. The organiser controls all phase transitions — nothing advances automatically.

## **2.1 Phase Order**

|**Phase**|**Teams can...**|**Organiser does...**|
| :- | :- | :- |
|PROCUREMENT\_OPEN|Submit / update procurement decisions (which supplier, how many units, which transport)|Call /advance when ready to close procurement and trigger resolution|
|PRODUCTION\_OPEN|Submit / update production decisions (maintenance, R&D investments, machine upgrades, wage level, headcount)|Call /advance when ready to close production and trigger resolution|
|SALES\_OPEN|Submit / update sales decisions (what to do with each quality tier — sell, hold, scrap, black market)|Call /advance when ready to close sales and trigger resolution|
|BACKROOM|View the leaderboard only. No decision submission in this phase.|Record government deals, inter-team loans, global events. Then call /next to start a new cycle OR /end-game to finish.|

|**IMPORTANT**|Calling /advance closes the current phase AND immediately runs the resolution simulation for that phase. There is no separate 'run resolution' step. The moment the organiser calls /advance, all teams' current decisions are locked and processed.|
| :-: | :- |

## **2.2 Phase Transitions**
The complete state machine for one cycle, then the game-level controls:

|**PROCUREMENT\_OPEN**|→|**PRODUCTION\_OPEN**|→|...|
| :- | :- | :- | :- | :- |
|**PRODUCTION\_OPEN**|→|**SALES\_OPEN**|→|...|
|**SALES\_OPEN**|→|**BACKROOM**|→|next cycle or end|
|**BACKROOM + /next**|→|**New PROCUREMENT\_OPEN**||cycle repeats|
|**BACKROOM + /end-game**|→|**GAME\_OVER**||final leaderboard|

## **2.3 No Fixed Number of Cycles**
There is no preset number of cycles. The game runs until the organiser calls /end-game from the BACKROOM phase. This gives the organisers full control over the game length — they can extend or shorten on the fly based on how the competition is going.


# **3. Team Decisions by Phase**
This section details every decision a team can make in each phase. The frontend must present these options clearly and submit them via PATCH requests. All decisions use PATCH semantics — only changed fields need to be sent, everything else carries forward from the last cycle automatically.

|<p>**Phase 1: Procurement**</p><p>*Teams decide what to buy, from whom, and how to ship it*</p>|
| :-: |

### **3.1.1 What Teams Decide**
For each of the six components, the team sets three parameters:

|**source\_id**|Which supplier to buy from. Multiple suppliers exist per component with different quality means, quality variance (sigma), and base cost. Teams must choose strategically — high quality costs more and may have less volume available.|
| :- | :- |
|**quantity**|How many units to order. Range: 0 to 10,000 per component. Setting 0 skips procurement for that component this cycle (but last cycle's raw stock carries over).|
|**transport**|Shipping mode. Three options: air, rail, or road. See table below.|

**Transport Mode Comparison**

|**Mode**|**Cost multiplier**|**Quality variance**|**Partial damage risk**|**Total loss risk**|
| :- | :- | :- | :- | :- |
|Air|2\.5× base cost|Low (+1.0 sigma)|5%|1%|
|Rail|1\.4× base cost|Medium (+4.0 sigma)|12%|3%|
|Road|1\.0× base cost|High (+8.0 sigma)|20%|5%|

|**NOTE**|Partial damage affects 25% of units, reducing their grade by 20 points. Total loss destroys the entire shipment — the team still pays for it. These are random events; the team cannot prevent them but can mitigate by choosing safer transport.|
| :-: | :- |

### **3.1.2 What the Frontend Must Show**
- A panel for each of the six components showing: current source selection, current quantity, current transport mode
- A list of available suppliers per component, showing their name, quality mean, quality sigma (as a hint about consistency), and cost per unit
- The current raw material stock for each component (carried over from previous cycles) — shown as a total unit count
- Total estimated procurement cost for this cycle (compute client-side: sum of quantity × base\_cost × transport\_multiplier for each component)
- A 'Send Decisions' button that PATCHes only the changed components
- A confirmation showing last saved timestamp

|**UI TIP**|Consider showing a supplier comparison table per component so teams can see quality vs cost trade-offs at a glance. A scatter plot of quality\_mean vs cost\_per\_unit per supplier is very effective for quick decision-making.|
| :-: | :- |

|<p>**Phase 2: Production**</p><p>*Teams decide how to run their factory this cycle*</p>|
| :-: |

### **3.2.1 Per-Component Decisions**
For each of the six components, the team sets:

|**maintenance**|How well to maintain the machine this cycle. Options: none, basic, full, overhaul. Higher maintenance preserves machine condition and costs more. Overhaul actively recovers condition. Neglecting maintenance degrades the machine, reducing output quality over time.|
| :- | :- |
|**rnd\_invest**|Optional: invest in R&D for this component. Specify focus area (quality, consistency, or yield) and number of levels. R&D takes 2 cycles to complete. Quality R&D raises output mean. Consistency R&D reduces variance. Yield R&D reduces raw material consumed per unit.|
|**upgrade\_to**|Optional: buy a new machine of a higher tier (basic, standard, industrial, precision). The new machine starts at full condition. One-time cost deducted immediately.|

**Machine Tiers**

|**Tier**|**Grade**|**Throughput/cycle**|**Labour req.**|**Degrades/cycle**|**Buy cost**|**Scrap value**|
| :- | :- | :- | :- | :- | :- | :- |
|Basic|40|200 units|10 workers|4\.0 pts|15,000 CU|1,000 CU|
|Standard|60|400 units|8 workers|3\.0 pts|35,000 CU|3,000 CU|
|Industrial|75|700 units|6 workers|2\.0 pts|80,000 CU|8,000 CU|
|Precision|90|1000 units|4 workers|1\.2 pts|180,000 CU|25,000 CU|

### **3.2.2 Team-Wide Labour Decisions**
These apply to the whole company, not per component:

|**wage\_level**|below\_market, market, or above\_market. Affects morale. Below market saves money but drops morale, eventually causing strikes. Above market costs more but boosts morale and skill retention.|
| :- | :- |
|**target\_headcount**|How many workers to employ. If headcount falls below the labour required by machines, output is proportionally reduced and morale drops from understaffing.|
|**upgrade\_automation**|Optional: upgrade the factory's automation level (manual → semi\_auto → full\_auto). One-time cost. Reduces labour required and tightens output variance.|

**Automation Levels**

|**Level**|**Labour multiplier**|**Output variance**|**Upgrade cost**|
| :- | :- | :- | :- |
|Manual|1\.0× (full labour needed)|1\.0× base sigma|Free (default)|
|Semi-auto|0\.6× (fewer workers)|0\.65× base sigma|20,000 CU|
|Full-auto|0\.25× (skeleton crew)|0\.35× base sigma|60,000 CU|

### **3.2.3 What the Frontend Must Show**
- Per-component panel showing: current machine tier, current machine condition (0-100, shown as a health bar), current R&D levels for all three focus areas
- Maintenance level selector per component with cost preview
- R&D investment form per component: focus area dropdown + levels input + cost preview (10,000 CU per level). Show that it takes 2 cycles to arrive.
- Machine upgrade selector per component: show tiers above current with buy cost and stat comparison
- Labour section: wage level selector with morale impact hint, headcount input, automation upgrade option
- Running total of all production costs this cycle

|**UI TIP**|Show machine condition as a coloured health bar: green above 70, amber 40-70, red below 40. At below 40 the machine enters DEGRADED status and output quality drops. This makes the consequence of neglecting maintenance immediately visible.|
| :-: | :- |

|<p>**Phase 3: Sales**</p><p>*Teams decide what to do with each tier of finished drones*</p>|
| :-: |

### **3.3.1 Per-Tier Decisions**
Teams set an action and optional price override for each of the four quality tiers. The frontend shows the team how many drones they have in each tier this cycle (computed from the drone stock and the current thresholds).

|**sell\_market**|Sell at the standard market price for this tier. Most common action.|
| :- | :- |
|**sell\_premium**|PREMIUM tier only. Sell above the standard premium price (4,800 CU vs 3,000 CU). Boosts brand score significantly.|
|**sell\_discounted**|Sell below the standard price. Helps move volume in a crowded market. The team sets a price\_override to control exactly how deep the discount goes.|
|**hold**|Keep drones in inventory for next cycle. Costs 40 CU per unit per cycle in holding costs. Useful if the team expects better market conditions next cycle.|
|**scrap**|Destroy the drones and recover 200 CU per unit in scrap value. Clears inventory but earns almost nothing.|
|**black\_market**|REJECT tier only. Sell rejects illegally for 600 CU per unit. Risk of discovery — if caught, a fine of 3× the black market revenue is applied and brand score takes a severe hit.|

**Default Tier Actions (if team sends no decision)**

|**REJECT**|Scrap — always safe default|
| :- | :- |
|**SUBSTANDARD**|Sell discounted at 1,400 CU|
|**STANDARD**|Sell at market price 3,000 CU|
|**PREMIUM**|Sell at standard premium price 3,000 CU (not the premium price — team must explicitly choose sell\_premium)|

### **3.3.2 Market Mechanics (informational — backend handles this)**
The backend runs a market simulation when sales are resolved. Teams compete for a share of the total market capacity. Market share is allocated proportionally by brand score. A team with a higher brand score gets a larger slice of the market. The organiser controls the total market capacity between cycles.

- Market capacity default: 2,000 drones per cycle across all teams
- No single team can capture more than 70% of the market
- If all teams offer fewer drones than the market capacity, it is a sellers' market and everything sells
- If total supply exceeds capacity, teams with higher brand scores sell more

### **3.3.3 What the Frontend Must Show**
- For each tier: unit count available this cycle, current action selection, price override input (if applicable), estimated revenue
- Total estimated revenue for this cycle
- Current brand score and tier (poor, fair, good, excellent) — brand affects market share
- Current drone stock (units carried from previous cycles) clearly distinguished from units produced this cycle

|**UI TIP**|Show a simple breakdown: Produced This Cycle + Carried From Stock = Total Available, then split into the four tiers with their counts. Teams often forget they have old stock sitting in inventory.|
| :-: | :- |


# **4. Backroom Phase**
The backroom phase is the most strategically rich part of the game. Teams see the leaderboard for the first time this cycle. Offline, teams may approach the organisers to negotiate deals. The organisers record all deals through the admin dashboard.

## **4.1 What Teams See**
- Full leaderboard with all teams ranked by composite score
- Their own rank, composite score, and the breakdown of each metric
- Other teams' brand scores and composite scores — but not their internal state

Teams cannot submit any decisions in this phase. The team interface shows the leaderboard only.

## **4.2 Leaderboard Scoring**
The composite score is a weighted combination of five metrics, each normalised to a 0-1 scale:

|**Metric**|**Weight**|**Direction**|**Notes**|
| :- | :- | :- | :- |
|Cumulative profit|30%|Higher = better|Sum of net profit across all cycles|
|Closing funds|25%|Higher = better|Current liquid capital|
|Brand score|20%|Higher = better|0-100 scale|
|Quality weighted avg|15%|Higher = better|Sales-weighted mean drone grade|
|Inventory penalty|-10%|Lower = better|Unsold drones sitting in stock — subtracted|

## **4.3 What Happens Offline (Deals)**
During the backroom phase, teams physically approach the organisers and negotiate deals. The organiser records the agreed terms in the admin dashboard. Teams are not informed of deals through the system — the organisers tell them verbally. The effects of deals take place at the start of the next cycle.

## **4.4 Financial Distress**
There are no automatic bankruptcy checks during procurement or production. Teams are allowed to go into negative funds during these phases — they will simply have a negative balance. When the game reaches the backroom phase, the organisers review the standings and approach struggling teams with three options:

- Accept a government loan — high interest rate (15% per cycle), but the team stays in the game. Accepting a government loan blocks the team from backroom deals while the loan is active. The brand score takes a hit.
- Accept a loan from another team — negotiated interest rate (2-12%), terms agreed offline and recorded by the organiser.
- Forfeit — the team is eliminated from the competition. Their company is declared insolvent.

This is entirely organiser-managed. The frontend just needs to show the current funds balance clearly, including when it is negative.


# **5. Organiser Dashboard**
The organiser dashboard is the control plane of the game. It is only used by the competition organisers — never by teams. It requires the organiser secret in every request header.

## **5.1 Game Setup (before the game starts)**
Before the first cycle, the organiser must:

1. Create the game via POST /organiser/game/create (uses a one-time bootstrap secret from .env)
1. Add all teams via POST /organiser/teams/add (one call per team)
1. Create the first cycle via POST /organiser/cycle/create

This is typically done by running the seed scripts (seed\_game.py, seed\_teams.py) rather than through the dashboard UI, but the endpoints are available if needed.

## **5.2 Phase Control**
The organiser dashboard must have a single prominent ADVANCE button that moves the game forward. This is the most frequently used action during the competition. The advance endpoint runs the resolution for the current phase and moves to the next one.

|**IMPORTANT**|Resolution is irreversible. Once the organiser clicks advance, that phase's decisions are locked and the simulation runs. There is an emergency force-phase endpoint to correct mistakes, but it does not undo the simulation — use it only when the phase got stuck, not to replay a resolution.|
| :-: | :- |

## **5.3 Backroom Phase Actions**
All deal recording happens here. The organiser dashboard must provide forms for:

### **5.3.1 Government Deals**
The organiser records deals negotiated offline between a team and the government. 23 deal types are available in five categories:

- Procurement: sabotage a rival's supply, inflate their costs, get subsidised inputs, secure priority supply
- Infrastructure: sabotage a rival's machine, delay their upgrades, fast-track your own infra
- Labour & R&D: force a strike on a rival, poach their workers, steal their R&D, grant skilled labour or research funding
- Sales & Market: limit a rival's market access, suppress their demand, boost your own demand, guarantee a government purchase
- Legal & Regulatory: force an audit on a rival, impose an arbitrary fine, buy audit immunity, get a quality waiver, arrange tax evasion

For each deal the organiser enters: the buyer team, the deal type, the bribe amount (must meet the floor for that deal type), the target team (for offensive deals), and any override parameters (e.g. for a government purchase, the organiser specifies the units and price).

The bribe is deducted immediately from the buyer's funds. The effect activates at the start of the next cycle. Discovery probability is computed automatically and rolled at the next backroom phase close.

### **5.3.2 Inter-Team Loans**
Two teams have agreed offline that one will lend money to another. The organiser records the terms: borrower, lender, principal amount, interest rate (2-12% per cycle), and duration in cycles. The principal is transferred immediately. Interest is charged each cycle automatically.

### **5.3.3 Government Loans**
The organiser extends a government loan to a struggling team. Principal is set by the organiser. Interest rate is fixed at 15% per cycle. While the loan is active, the team cannot make backroom deals, and their brand score takes a hit.

### **5.3.4 Global Events**
The organiser can inject a global event that affects all teams. Examples: 'market demand drops 20% for 2 cycles', 'qr\_hard threshold raised by 5 points next cycle', 'all road transport disrupted this cycle'. These are recorded in the event ledger and applied automatically at cycle start.

The organiser tells teams about global events verbally during the backroom phase. The effects start next cycle.

## **5.4 Next Cycle vs End Game**
From the backroom phase, the organiser has two choices:

- POST /organiser/cycle/next — rolls discovery on all pending deals, closes the current cycle, creates the next cycle. The game continues.
- POST /organiser/cycle/end-game — rolls discovery, ends the game. The leaderboard becomes final. The GAME\_OVER phase is set.

## **5.5 Team Monitoring**
The organiser dashboard should show a live team overview: all teams' current funds, brand score, whether they have a government loan active, and their current rank. This helps the organiser spot teams in financial distress before they reach crisis.


# **6. Polling and State Management**
The frontend uses a polling architecture. There are no WebSockets. The frontend periodically calls the status endpoint and reacts to phase changes.

## **6.1 The Polling Endpoint**
GET /team/status returns the current game phase and cycle number. No authentication required. Call this every 5-10 seconds.

|**game\_name**|Name of the game|
| :- | :- |
|**cycle\_number**|Current cycle number (integer). 0 means no cycle has been created yet.|
|**phase**|Current phase string. One of: procurement\_open, production\_open, sales\_open, backroom, game\_over, waiting\_for\_first\_cycle, no\_active\_game|
|**game\_active**|Boolean. False once end-game has been called.|

## **6.2 Recommended Polling Strategy**
Use exponential backoff to reduce server load during long idle periods:

- Poll every 5 seconds by default
- If the phase has not changed for 2 minutes, back off to polling every 15 seconds
- The moment the phase changes, reset to 5-second polling immediately
- Show teams a visual indicator of their connection status (last updated X seconds ago)

## **6.3 Phase-Driven UI**
The phase string from the polling endpoint should drive what the team interface shows:

|**Phase**|**Show to teams**|
| :- | :- |
|procurement\_open|Procurement decision form with submit button enabled|
|production\_open|Production decision form with submit button enabled|
|sales\_open|Sales decision form with submit button enabled|
|backroom|Leaderboard. All decision forms locked. Message: 'Backroom phase — wait for the organiser'|
|game\_over|Final leaderboard with winner announcement. All forms locked.|
|waiting\_for\_first\_cycle|'Game starting soon...' holding screen|


# **7. Complete API Reference**
All endpoints. Auth headers are sent as HTTP headers, not in the body or URL.

|**AUTH HEADERS**|Team endpoints: x-team-id (integer) and x-team-pin (raw PIN string). Organiser endpoints: x-organiser-secret (the long hex string generated at game creation). The status and leaderboard endpoints require no authentication.|
| :-: | :- |

## **7.1 Public Endpoints (no auth)**

|**Method**|**Endpoint**|**Auth**|**Description**|
| :- | :- | :- | :- |
|GET|/health|None|Health check — returns {status: ok}|
|GET|/team/status|None|Current phase and cycle number — the polling endpoint|
|GET|/team/leaderboard|None|Leaderboard — only returns data during backroom and game\_over phases|

## **7.2 Team Endpoints**

|**Method**|**Endpoint**|**Auth**|**Description**|
| :- | :- | :- | :- |
|POST|/team/login|Team|Verify credentials. Returns team\_id and team\_name.|
|GET|/team/me|Team|Return team's own inventory: funds, brand score, drone stock total, workforce, skill, morale, automation level, gov loan status.|
|GET|/team/procurement|Team|Return current procurement decisions (all six components).|
|PATCH|/team/procurement|Team|Update procurement decisions. Partial update — send only changed components.|
|GET|/team/production|Team|Return current production decisions.|
|PATCH|/team/production|Team|Update production decisions. Partial update.|
|GET|/team/sales|Team|Return current sales decisions.|
|PATCH|/team/sales|Team|Update sales decisions. Partial update.|

## **7.3 Organiser — Cycle Control**

|**Method**|**Endpoint**|**Auth**|**Description**|
| :- | :- | :- | :- |
|POST|/organiser/cycle/create|Organiser|Create a new cycle (or the first cycle). Applies pending deals and ticks the event ledger.|
|POST|/organiser/cycle/advance|Organiser|Advance to next phase. Runs resolution for the phase being closed. Most-used endpoint during the game.|
|POST|/organiser/cycle/next|Organiser|From BACKROOM: roll discovery, close cycle, start a new one.|
|POST|/organiser/cycle/end-game|Organiser|From BACKROOM: roll discovery, end the game. Sets GAME\_OVER.|
|GET|/organiser/cycle/status|Organiser|Full cycle status: cycle number, phase, qr thresholds, demand multiplier.|
|PATCH|/organiser/cycle/force-phase|Organiser|Emergency: set phase manually. Query param: phase\_value. Does not rerun resolution.|
|PATCH|/organiser/game/settings|Organiser|Update qr\_hard, qr\_soft, qr\_premium, market\_demand\_multiplier. Takes effect next cycle.|

## **7.4 Organiser — Deals and Events**

|**Method**|**Endpoint**|**Auth**|**Description**|
| :- | :- | :- | :- |
|POST|/organiser/deals/gov|Organiser|Record a government deal. Body: buyer\_team\_id, deal\_type, bribe\_amount, target\_team\_id (for RED deals), override\_params, notes.|
|POST|/organiser/deals/inter-team|Organiser|Record an inter-team loan. Body: borrower\_team\_id, lender\_team\_id, principal, interest\_rate, duration\_cycles.|
|POST|/organiser/deals/gov-loan|Organiser|Issue a government loan. Body: borrower\_team\_id, principal, duration\_cycles.|
|POST|/organiser/deals/global-event|Organiser|Record a global event. Body: event\_type=global\_event, cycles\_duration, payload (effects dict), notes.|
|GET|/organiser/deals|Organiser|List all deals for the current cycle.|
|DELETE|/organiser/deals/{deal\_id}|Organiser|Cancel a PENDING deal. No refund.|
|POST|/organiser/deals/discover|Organiser|Manually trigger discovery rolls for all pending deals right now.|

## **7.5 Organiser — Team Management**

|**Method**|**Endpoint**|**Auth**|**Description**|
| :- | :- | :- | :- |
|POST|/organiser/game/create|Bootstrap secret|Create the game. One-time use. Returns game record including organiser\_secret.|
|POST|/organiser/teams/add|Organiser|Add a team. Body: name, pin. Seeds all inventory and memory rows.|
|GET|/organiser/teams|Organiser|List all teams with funds, brand score, gov loan status.|
|GET|/organiser/teams/{team\_id}/inventory|Organiser|Full inventory for one team including all component slots and R&D levels.|
|POST|/organiser/teams/{team\_id}/reset-pin|Organiser|Reset a team's PIN. Query param: new\_pin.|


# **8. Request and Response Examples**

## **8.1 Team Login**
**Request headers:**

|**x-team-id**|3|
| :- | :- |
|**x-team-pin**|gamma2026|

**Response:**

{ "team\_id": 3, "team\_name": "Team Gamma", "message": "Login successful." }

## **8.2 Polling the Status Endpoint**
**Request: GET /team/status (no headers)**

**Response during procurement phase:**

{ "game\_name": "Industrix - Srijan 2026", "cycle\_number": 2, "phase": "procurement\_open", "game\_active": true }

## **8.3 Submitting Procurement Decisions (PATCH)**
**Request headers: x-team-id: 3, x-team-pin: gamma2026**

**Request body (only send changed components):**

{ "decisions": { "airframe": { "source\_id": 1, "quantity": 400, "transport": "rail" }, "battery": { "source\_id": 12, "quantity": 300, "transport": "air" } } }

**Response:**

{ "ok": true, "message": "Procurement decisions updated." }

## **8.4 Advancing Phase (Organiser)**
**Request: POST /organiser/cycle/advance**

**Request header: x-organiser-secret: a3f9c2...**

**Response:**

{ "previous\_phase": "resolved", "current\_phase": "production\_open", "cycle\_number": 2 }

## **8.5 Recording a Government Deal**
**Request: POST /organiser/deals/gov**

**Request body:**

{ "buyer\_team\_id": 3, "deal\_type": "red\_machine\_sabotage", "bribe\_amount": 12000, "target\_team\_id": 1, "notes": "Negotiated after cycle 2 backroom session" }

**Response: returns the GovDeal record with computed discovery\_probability and effect\_payload.**

## **8.6 Leaderboard Response**
**Request: GET /team/leaderboard (no auth, only works during backroom/game\_over)**

**Response:**

{ "cycle\_number": 3, "is\_final": false, "rows": [ { "rank": 1, "team\_name": "Team Alpha", "composite\_score": 0.6821, "closing\_funds": 142500, "cumulative\_profit": 87300, "brand\_score": 72.4, "quality\_avg": 68.1, "inventory\_penalty": 45 }, ... ] }


# **9. Inventory, Memory, and Carry-over**

## **9.1 What Persists Between Cycles**
The game is designed so teams carry over both assets and decisions between cycles. Nothing resets to zero between cycles except what is explicitly consumed or sold.

|**What carries over**|**How**|
| :- | :- |
|Funds|Updated at each resolution. Can go negative during procurement/production. Rectified in backroom.|
|Raw material stock|Per-component 101-int arrays. Unconsumed materials carry to next cycle automatically.|
|Finished component stock|Components produced but not yet assembled into drones carry forward.|
|Drone stock|Unsold drones carry forward. Holding cost (40 CU/unit/cycle) is deducted each cycle.|
|Machine condition|Degrades each cycle by the tier's degradation rate. Maintenance slows or stops degradation.|
|R&D levels|Carry forward permanently once earned. In-progress R&D arrives after 2 cycles.|
|Brand score|Decays by 6% per cycle passively. Boosted by good sales, harmed by substandard sales and black market.|
|Workforce skill and morale|Skill grows with high morale, drops with low morale. Morale affected by wages and understaffing.|
|Decisions (Memory tables)|All decisions from last cycle are the default for this cycle. Teams only need to send changes.|

## **9.2 The Memory System**
The backend stores one memory row per team per subsystem (procurement, production, sales). When a team sends a PATCH, only the changed fields are written. Everything else keeps its last value.

This means in cycle 2, if a team only wants to change the quantity for airframe and nothing else, they send a PATCH with only the airframe decision. All other components, all maintenance levels, all sales actions — they all carry forward unchanged from cycle 1.

The GET endpoints for each decision type return the current full memory row, so the frontend can always show the team their complete current decision state.

|**UI TIP**|On the decision forms, pre-populate every field with the values returned by the GET endpoint. This way teams see their last cycle's choices as the starting point and only need to change what they want to adjust. This is much better UX than blank forms each cycle.|
| :-: | :- |


# **10. Event System and Deals**

## **10.1 The Event Ledger**
Any obligation that spans multiple cycles lives in the event ledger: loans, in-progress R&D investments, active global events, and backroom deal effects. Each row has a cycles\_remaining counter that ticks down each cycle. When it hits zero, the event is resolved and removed.

Teams do not interact with the event ledger directly — its effects are applied automatically by the backend at the start of each new cycle. The frontend just needs to show teams the consequences (their funds being reduced by interest payments, R&D levels arriving, etc.) through the inventory endpoint.

## **10.2 Government Deals — Deal Types Reference**
23 deal types across five categories. Red deals are offensive (hurt a target team). Green deals are defensive self-buffs.

### **Procurement Category**

||**Deal type**|**Effect**|
| :- | :- | :- |
|**RED**|red\_supply\_sabotage|Destroys a fraction of the target's incoming shipment for one component|
|**RED**|red\_price\_inflation|Multiplies the target's procurement cost for one cycle|
|**GRN**|green\_priority\_supply|Raises buyer's raw material quality mean for one component|
|**GRN**|green\_subsidised\_inputs|Reduces buyer's procurement cost by a percentage for one cycle|

### **Infrastructure Category**

||**Deal type**|**Effect**|
| :- | :- | :- |
|**RED**|red\_machine\_sabotage|Reduces machine condition on the target's weakest machine|
|**RED**|red\_infra\_delay|Blocks target's next machine upgrade for N cycles|
|**GRN**|green\_fast\_track\_infra|Buyer's next machine purchase gets a bonus to starting condition and quality|

### **Labour & R&D Category**

||**Deal type**|**Effect**|
| :- | :- | :- |
|**RED**|red\_labour\_strike|Forces a strike on target next cycle, halving production output|
|**RED**|red\_labour\_poach|Reduces target's workforce skill level|
|**RED**|red\_rnd\_sabotage|Reduces target's R&D level in a specified component and focus area|
|**GRN**|green\_skilled\_labour|Raises buyer's skill level immediately|
|**GRN**|green\_research\_grant|Grants buyer an immediate R&D level in a specified component and focus|

### **Sales & Market Category**

||**Deal type**|**Effect**|
| :- | :- | :- |
|**RED**|red\_market\_limit|Blocks a fraction of the target's drones from the regulated market|
|**RED**|red\_demand\_suppression|Reduces the target's effective brand weight in market allocation|
|**RED**|red\_price\_pressure|Caps target's standard/premium selling price at the substandard price|
|**GRN**|green\_demand\_boost|Increases the buyer's effective brand weight in market allocation|
|**GRN**|green\_gov\_purchase|Government commits to buying a specified number of drones from buyer at a guaranteed price|

### **Legal & Regulatory Category**

||**Deal type**|**Effect**|
| :- | :- | :- |
|**RED**|red\_targeted\_audit|Forces an audit on the target next backroom phase|
|**RED**|red\_arbitrary\_fine|Imposes a direct financial penalty on the target|
|**GRN**|green\_audit\_immunity|Exempts buyer from audits for N cycles|
|**GRN**|green\_quality\_waiver|Lowers the effective qr\_hard threshold for the buyer for one cycle|
|**GRN**|green\_tax\_evasion|Refunds a fraction of the buyer's total costs as a tax rebate|

## **10.3 Discovery Risk**
Every government deal has a discovery probability computed from three factors: the base rate for that deal type, a size component (larger bribes are riskier), and a stacking component (repeating the same deal type doubles the risk). Discovery is rolled at the next backroom phase close.

If discovered: the buyer pays a fine of 2.5× the original bribe amount, the brand score drops by 20 points, and the deal effect is nullified. The discovery roll decays each cycle the deal survives undiscovered — so a deal from two cycles ago has lower risk than a fresh one.


# **11. Quick Reference**

## **11.1 Key Numbers**

|**Quality scale**|1 to 100 (0 = scrap bucket)|
| :- | :- |
|**Components**|6: airframe, propulsion, avionics, fire\_suppression, sensing\_safety, battery|
|**Default qr\_hard**|30 — below this is REJECT|
|**Default qr\_soft**|50 — below this is SUBSTANDARD|
|**Default qr\_premium**|75 — above this is PREMIUM|
|**Default market capacity**|2,000 drones per cycle across all teams|
|**Max market share**|70% — no team can capture more than this|
|**Starting funds**|100,000 CU per team|
|**Government loan rate**|15% per cycle|
|**Brand decay per cycle**|6% (brand\_score × 0.94 each cycle)|
|**Holding cost**|40 CU per unsold drone per cycle|
|**Max R&D level**|5 per focus area per component|
|**R&D delivery time**|2 cycles after investment|
|**Machine condition**|0-100, starts at 100, degrades each cycle|
|**DEGRADED threshold**|Below 40 condition — output quality penalty applies|

## **11.2 Pre-Event Setup Sequence**
1. docker compose up -d
1. python -m scripts.reset\_db (type RESET)
1. Edit seed\_data/market.json with game name and thresholds
1. Edit seed\_data/sources.json with supplier configurations
1. Edit seed\_data/teams.json with team names and PINs
1. python -m scripts.seed\_game (note the organiser\_secret printed)
1. python -m scripts.seed\_teams
1. python -m scripts.smoke\_test (should all pass)
1. Share team IDs and PINs with respective teams
1. Organiser creates cycle 1 via dashboard: POST /organiser/cycle/create

## **11.3 During the Event — Organiser Sequence per Cycle**
1. Announce: Procurement phase is open
1. Teams submit procurement decisions
1. When satisfied: POST /organiser/cycle/advance (procurement resolves, production opens)
1. Announce: Production phase is open
1. Teams submit production decisions
1. When satisfied: POST /organiser/cycle/advance (production resolves, sales opens)
1. Announce: Sales phase is open
1. Teams submit sales decisions
1. When satisfied: POST /organiser/cycle/advance (sales resolves, backroom opens)
1. Teams view leaderboard. Offline deal negotiations happen.
1. Organiser records deals, loans, events via dashboard
1. Decision: POST /organiser/cycle/next OR POST /organiser/cycle/end-game

## **11.4 Emergency Procedures**
- Phase stuck / wrong state: POST /organiser/cycle/force-phase?phase\_value=procurement\_open
- Team locked out (forgot PIN): POST /organiser/teams/{id}/reset-pin?new\_pin=newpin
- Database backup: python -m scripts.backup (run after every cycle)
- Full reset: python -m scripts.reset\_db then re-seed


# **12. Notes for Frontend Developers**
A few final recommendations based on the game design:

- Never hardcode phase names. Always drive the UI from the phase string returned by the polling endpoint.
- Always pre-populate decision forms from the GET endpoint. Blank forms each cycle break the carry-forward UX.
- Show funds prominently at all times. Teams need to know if they are overspending. Show it in red if negative.
- The six-component structure is repetitive. Consider a tabbed or accordion layout so teams can focus on one component at a time rather than scrolling through all six.
- For the organiser dashboard, a live team overview table (funds, brand, loan status, rank) should be always visible — probably a persistent sidebar or top strip.
- The advance button should require confirmation. Clicking it accidentally mid-phase is game-breaking.
- Show teams their last submission time. 'Decisions saved at 14:32' is more reassuring than a green tick.
- In the backroom leaderboard, highlight the viewing team's own row so they can find themselves quickly.
- During the backroom phase, the team interface should clearly say 'No submissions in this phase' to avoid confusion.
- Error messages from the API are plain English strings in the 'detail' field. Show them directly to users — they are written to be readable.

Good luck. Build something the teams will remember.
Page 
