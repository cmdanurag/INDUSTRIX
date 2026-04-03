**INDUSTRIX**

*Fire-Fighting Drone Manufacturing Simulation*

Complete Game Reference — Backend, Gameplay, Frontend & PR


**Srijan — Jadavpur University**

*Internal Document — Not for Public Distribution*


# **1. Game Overview**
**Industrix** is a competitive, multiplayer, turn-based business simulation event game. Each team of players takes on the role of the **CEO and management board of a drone manufacturing company** that specialises in fire-fighting drones. Teams compete over a series of production-and-sales cycles, making real decisions about supply chains, factory operations, labour, research, and market strategy — while simultaneously navigating a hidden layer of sabotage, bribery, and backroom dealing facilitated by a Game Organiser who plays the role of a corrupt, all-powerful government.

## **1.1 The Central Premise**
The game simulates the full value chain of a manufacturing business compressed into repeating cycles. In each cycle, teams must:

- Source and procure six categories of raw materials from external suppliers.
- Run their factory — managing machines, workers, automation, and R&D — to convert raw materials into finished drones.
- Sell those drones on a shared, competitive market, choosing price points and handling quality tiers.
- Optionally engage in backroom deals with the government (the Organiser) to sabotage rivals, receive subsidies, manipulate the market, or bribe their way to advantage.

The game ends after a fixed number of cycles (default: 6). The team with the highest composite score — weighted across liquid capital, brand reputation, cumulative revenue, and inventory efficiency — wins.

## **1.2 Key Design Pillars**

|**Pillar**|**What it means in play**|
| :- | :- |
|Information asymmetry|Teams receive vague output signals unless they pay for diagnostic intelligence. Rivals' exact figures are hidden.|
|Probabilistic outcomes|Every production run, every shipment, every discovery roll uses real statistical distributions. Decisions made under genuine uncertainty.|
|Compound decisions|Each decision (e.g., wage level) creates lasting consequences (morale decay, skill drift) that affect future cycles.|
|Competitive market|All teams sell into the same shared demand pool. Your rivals' quality and brand directly reduce your sales allocation.|
|Organiser as 'government'|The Organiser holds real power: can create global events, broker sabotage, give loans with strings attached, and trigger disasters.|
|Moral hazard|Teams can take shortcuts — dumping rejects on the black market, buying cheaper labour, ignoring maintenance — but each carries escalating risk of catastrophic discovery.|

## **1.3 The Currency**
All monetary values are denominated in **CU (Currency Units)**. Teams begin each game with 100,000 CU. There is no external bank or money-printer — capital must be earned through sales, preserved through operational discipline, or borrowed (at cost).

## **1.4 Number of Teams and Cycles**
- **Teams:** Any number. Market dynamics become more interesting with 4–8 teams.
- **Cycles:** Default 6. Organiser can configure this at game creation. Shorter games (4 cycles) favour early aggression; longer games (8+) reward long-term investment.
- **Cycle duration:** Approximately 20–35 minutes per cycle in a live event setting, depending on team size and decision complexity.


# **2. The Cycle — Phase by Phase**
Every cycle progresses through exactly eight phases. All transitions are manually triggered by the Organiser. Nothing advances automatically — this gives the Organiser full control over pacing, and allows them to extend any phase for drama, negotiation, or live commentary.

|**Phase**|**Who acts**|**What happens**|**Ends when**|
| :- | :- | :- | :- |
|PHASE1\_OPEN|Teams|Teams update procurement orders, machine maintenance decisions, labour decisions, R&D investments. Decisions carry from previous cycle unless changed.|Organiser clicks 'Close Phase 1'|
|PHASE1\_CLOSED|Organiser|Brief lock state. Teams cannot change decisions. Organiser reviews and then triggers processing.|Organiser clicks 'Run Phase 1'|
|PHASE1\_PROCESSING|Server|All procurement deliveries resolved. All production simulations run. Results written to database.|Automatic (seconds)|
|PHASE1\_DISPLAY|Teams + Organiser|Teams see production results. They can purchase paid diagnostics for deeper intelligence. Organiser brokers offline loan negotiations. Backroom deals can be offered here.|Organiser clicks 'Open Phase 2'|
|PHASE2\_OPEN|Teams|Phase 1 costs deducted. Teams now see their drone quality tier breakdown and submit sales decisions.|Organiser clicks 'Close Phase 2'|
|PHASE2\_CLOSED|Organiser|Sales decisions locked. Organiser reviews and triggers processing.|Organiser clicks 'Run Phase 2'|
|PHASE2\_PROCESSING|Server|Market simulated. Sales resolved. Financial statements written. Leaderboard computed (hidden).|Automatic (seconds)|
|COMPLETE|Organiser + Teams|Organiser reveals leaderboard. Backroom deals phase opens. Discovery rolls run. Next cycle created.|Organiser clicks 'Complete Cycle'|

## **2.1 The Backroom Deals Phase**
The Backroom Deals Phase sits between COMPLETE and the next cycle's PHASE1\_OPEN. It is not a formal phase in the state machine — it happens in the live room, facilitated by the Organiser, using the Organiser's admin tools.

During this window:

- The Organiser reveals the scored leaderboard for the completed cycle.
- Teams can approach the Organiser privately to purchase sabotage effects against rivals (e.g., destroy a machine, trigger a labour riot, sabotage a shipment).
- Teams can negotiate inter-team loans, which the Organiser records in the system.
- The Organiser can trigger or announce global events that will affect the next cycle.
- Fraud discovery rolls are run — any team engaged in ongoing black market sales or shady government deals may be caught, fined, and publicly exposed.

**Organiser Tip:** The backroom phase is the most theatrically rich part of the game. Keep it to 10–15 minutes. The Organiser should be visibly occupied — taking 'bribes', whispering with teams, and occasionally making cryptic announcements. This is where the drama lives.


# **3. Procurement — Sourcing Raw Materials**
## **3.1 The Six Components**
Every drone requires exactly six types of raw material components. A team must procure all six, or production will be bottlenecked at zero for the missing component.

|**Component**|**What it represents**|
| :- | :- |
|Airframe|The physical structural chassis of the drone — body, frame, arms.|
|Propulsion|Motors, propellers, and drive systems.|
|Avionics|Flight control computers, communication modules, navigation.|
|Fire Suppression|The payload system — tanks, nozzles, release mechanisms.|
|Sensing & Safety|Obstacle detection, thermal imaging, emergency shutoff systems.|
|Battery|Power storage and management systems.|

## **3.2 Raw Material Sources**
The Organiser pre-configures a catalogue of raw material suppliers before the game. Each source has a fixed component type, so teams must source each component separately. Source parameters are:

|**Parameter**|**Description**|
| :- | :- |
|quality\_mean|The average grade (1–100) of units from this source. Higher = better raw material.|
|quality\_sigma|The standard deviation of the quality distribution. Lower sigma = more consistent, predictable quality.|
|base\_cost\_per\_unit|The baseline cost per unit ordered from this source, before transport multipliers.|
|min\_order / max\_order|Minimum and maximum units per order (global: 1 to 10,000).|
|is\_available|Whether teams can currently order from this source. Organiser can disable a source to simulate supply chain disruptions.|

**Game Design Tip:** Configure 2–3 sources per component, varying in the quality/cost/consistency trade-off. A cheap, low-quality source vs. an expensive, premium source is a meaningful strategic choice. Avoid having one obviously dominant source.

## **3.3 Transport Modes**
When placing a procurement order, teams choose how to ship their materials. The three modes create a meaningful risk-vs-cost triangle:

|**Mode**|**Cost Multiplier**|**Damage Sigma Add**|**P(Partial Damage)**|**P(Total Loss)**|
| :- | :- | :- | :- | :- |
|Air|2\.5×|+1.0|5%|1%|
|Rail|1\.4×|+4.0|12%|3%|
|Road|1\.0×|+8.0|20%|5%|

**Partial damage:** 25% of units in the shipment have their quality grade reduced by 20 points. Units that drop below grade 1 are lost.

**Total loss:** The entire shipment is destroyed. All units are gone. The team still pays the procurement cost.

**Key Mechanic:** Transport mode is chosen per order, per cycle. A team might air-freight a critical component with low stock while road-shipping a buffer component. This is an active, recurring decision, not a one-time setting.

## **3.4 Quality Arrays — How Inventory is Stored**
All raw material inventory (and all drone production output) is stored as a 101-integer array. Index 0 represents lost or unusable units. Indices 1 through 100 represent the count of units at each quality grade. This allows the simulation to track the full distribution of your inventory's quality — not just an average.

*Example:* [0, 0, 0, …, 0, 15, 30, 42, 35, 20, 8, 0, …] means the team has 150 usable units, with the bulk clustered around grades 75–80.

## **3.5 Organiser-Triggered Source Events**
The Organiser can modify any source at any time between cycles. Every modification is logged. Events that can be applied:

- **Over-extraction:** Quality mean drops by 8 points, cost rises 20%. Simulates a source being depleted by heavy ordering.
- **Supply disruption:** Cost rises 35%. Simulates geopolitical or logistical events.
- **Source disabled:** Teams can no longer order from this source until re-enabled. Forces pivoting to alternatives.
- **Quality improvement:** Organiser can manually raise quality\_mean to simulate source investment. Reward for teams that stayed loyal.

## **3.6 Procurement API — Frontend Reference**

|**GET  /games/{game\_id}/sources**||
| :- | :- |
|*Fetch all available raw material sources. Teams use this to browse suppliers. Pass available\_only=true to hide disabled sources. Pass component= to filter by component type.*||
|**Parameter**|**Description**|
|**game\_id**|Integer. The game's ID.|
|**component**|Optional. Filter: airframe | propulsion | avionics | fire\_suppression | sensing\_safety | battery|
|**available\_only**|Boolean, default true. Hide disabled sources.|
|**Returns:** Array of source objects: { id, name, component, quality\_mean, quality\_sigma, base\_cost\_per\_unit, is\_available }||

|**GET  /teams/{team\_id}/procurement**||
| :- | :- |
|*Get the team's current standing procurement decisions for all six components, including estimated costs at current source prices.*||
|**Parameter**|**Description**|
|**team\_id**|Integer. The team's ID.|
|**Returns:** { team\_id, decisions: [{component, source\_id, source\_name, quantity, transport\_mode, estimated\_unit\_cost, estimated\_total\_cost}], estimated\_total\_cost }||

|**PATCH  /teams/{team\_id}/procurement/{component}**||
| :- | :- |
|*Update the procurement decision for one component. Only callable while Phase 1 is OPEN. PATCH semantics — only fields you send will change.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**component**|Path param: airframe | propulsion | avionics | fire\_suppression | sensing\_safety | battery|
|**source\_id**|Integer. ID of the chosen source.|
|**quantity**|Integer. Units to order (1–10,000).|
|**transport\_mode**|String: air | rail | road|
|**Returns:** Updated ProcurementDecisionOut object with new estimated costs.||

|**GET  /teams/{team\_id}/procurement/cost-estimate**||
| :- | :- |
|*Get a live cost breakdown for the team's current procurement decisions. Useful for a budget summary panel.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**Returns:** { total\_estimated\_cost, per\_component: { [component]: { source, quantity, unit\_cost, total\_cost } } }||

|**GET  /cycles/{cycle\_id}/procurement/{team\_id}**||
| :- | :- |
|*Full procurement report for a team after cycle resolution. Shows what actually arrived vs what was ordered, including quality arrays and any shipment events.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**team\_id**|Integer.|
|**Returns:** CycleProcurementReport with orders[], shipments[], total\_cost, total\_units\_ordered, total\_units\_arrived, total\_units\_lost, per\_component\_summary||

**Frontend Tip:** The procurement decision screen should display a live cost estimate that updates as teams tweak source, quantity, and transport mode. Use GET /cost-estimate to power this. Show a per-component table alongside a total-funds bar that dims as the estimate grows.


# **4. Production — The Factory Floor**
Production is the most mechanically complex part of Industrix. It transforms raw materials into finished drones through three interdependent subsystems: Machines, Labour, and R&D. Each is managed independently but they interact through shared formulas at resolution time.

## **4.1 Machines**
Each team starts with one machine per component (six machines total), all at Standard tier. Additional machines can be purchased during Phase 1.

### **4.1.1 Machine Tiers**

|**Tier**|**Starting Grade**|**Throughput (units/cycle)**|**Labour Required**|**Degradation/cycle**|**Purchase Cost**|**Scrap Value**|
| :- | :- | :- | :- | :- | :- | :- |
|Basic|40|200|10|4\.0 pts|15,000 CU|1,000 CU|
|Standard|60|400|8|3\.0 pts|35,000 CU|3,000 CU|
|Industrial|75|700|6|2\.0 pts|80,000 CU|8,000 CU|
|Precision|90|1,000|4|1\.2 pts|180,000 CU|25,000 CU|

**Machine grade:** The machine's intrinsic output quality on the 1–100 scale. A Precision machine (grade 90) will produce much higher quality components than a Basic machine (grade 40), all else equal.

**Throughput:** The maximum number of component units a machine can process per cycle. If a team has two Standard machines for Avionics, their combined throughput is 800 units.

**Labour required:** The baseline number of workers needed to operate this machine at full throughput. Modified by automation level (see §4.3).

### **4.1.2 Machine Condition and Degradation**
Every machine has a Condition score from 0 to 100, starting at 100 (perfect). Condition degrades each cycle based on maintenance choice:

|**Maintenance Level**|**Degradation Multiplier**|**Cost per Cycle**|**Special Effect**|
| :- | :- | :- | :- |
|None|1\.0× (full degradation)|0 CU|–|
|Basic|0\.5× (half degradation)|500 CU|–|
|Full|0\.0× (no degradation)|1,500 CU|–|
|Overhaul|0\.0× (no degradation)|5,000 CU|Recovers up to 20 condition points, up to original purchase condition.|

**Status thresholds:** Condition > 40 → OPERATIONAL. Condition ≤ 40 → DEGRADED (grade penalty applied). Condition = 0 → DESTROYED (machine removed permanently, only scrap value recovered).

**Effective grade formula: effective\_grade = machine.grade × (condition / 100)^0.6 + rnd\_quality\_bonus**. At condition 40 (the DEGRADED threshold), effective grade is approximately 64% of the machine's original grade.

**Critical:** A machine on 'None' maintenance will degrade 3–4 condition points per cycle. A Standard machine starts at condition 100 and will become DEGRADED (≤40) after roughly 15 cycles with zero maintenance. In a 6-cycle game, teams that neglect maintenance entirely face a meaningful quality hit by cycle 4–5.

### **4.1.3 Desired Throughput**
Teams can set a desired\_throughput on each machine below its maximum. This is useful for conserving raw materials when a team has limited stock for a given component. The machine runs at the requested rate rather than full capacity.

## **4.2 Research & Development (R&D)**
R&D investments are one of the highest-leverage decisions in the game. Each of the six components has three independent R&D focus areas:

|**Focus Area**|**Effect per Level**|**Max Levels**|**Time to Complete**|**Cost per Level**|
| :- | :- | :- | :- | :- |
|Quality|+3 to effective machine output grade mean|5|2 cycles|10,000 CU|
|Consistency|−2 from output sigma (tighter quality distribution)|5|2 cycles|10,000 CU|
|Yield|−4% raw material consumed per unit produced|5|2 cycles|10,000 CU|

R&D investments are multi-cycle — an investment started in Cycle 1 completes in Cycle 2 (takes 2 cycles from start). Teams must explicitly trigger each level's investment. R&D does not auto-repeat.

### **4.2.1 R&D Decay**
Each cycle, every R&D state with level > 0 has a 5% chance of losing one level. This models knowledge attrition from staff turnover and neglect. Maintaining a consistent investment strategy counters decay.

### **4.2.2 R&D Profile Multiplier**
At drone assembly time, a profile multiplier is computed based on the pattern of R&D investment across all six components' Quality focus areas:

|**Pattern**|**Effect**|**Strategy**|
| :- | :- | :- |
|Uniform high (all components near max)|+2% drone grade per minimum level across all components|Balanced investment — steady positive bonus|
|Deep specialisation (some max, others zero)|Convex bonus: scales as (max\_level − mean\_level)²|Double down on a few key components|
|Mediocre spread (some in 30–60% of max)|Penalty per component in the 'mediocre zone'|Avoid half-committing — go all-in or skip|

The multiplier is clamped to [0.80, 1.30] — so even terrible R&D strategy can't drop you below 80% of base drone grade, and outstanding strategy gives a 30% bonus.

## **4.3 Labour & Automation**
### **4.3.1 Labour State**
Every team has a unified Labour State with three tracked values:

- **Skill Score (0–100):** Reduces production output sigma (tighter quality). Grows passively when morale is high; declines when morale is low.
- **Morale Score (0–100):** Determines turnover rate and whether labour events (riots, strikes) fire. Driven by wage decisions and staffing levels.
- **Headcount:** Actual number of workers. If headcount < total labour required across all machines, understaffing occurs.

### **4.3.2 Labour Decisions (standing, per cycle)**

|**Decision**|**Options**|**Effect**|
| :- | :- | :- |
|Wage Level|below\_market / market / above\_market|below\_market: −10 morale/cycle, 300 CU/worker/cycle. market: 0 morale, 500 CU/worker. above\_market: +8 morale, 750 CU/worker.|
|Target Headcount|Integer (0 to any)|Adjusts actual headcount toward target. Understaffing reduces morale by 0.20 per 1% below required.|
|Training Investment|Boolean (one-shot)|If enabled this cycle: +8 skill points. Resets to false after each cycle. Costs declared separately.|

### **4.3.3 Automation Levels**

|**Level**|**Labour Headcount Multiplier**|**Output Sigma Multiplier**|**Upgrade Cost**|
| :- | :- | :- | :- |
|Manual|1\.0× (full headcount needed)|1\.0× (base sigma)|0 CU (default)|
|Semi-Auto|0\.6× (40% fewer workers)|0\.65× (tighter output)|20,000 CU (one-time)|
|Full-Auto|0\.25× (75% fewer workers)|0\.35× (very tight output)|60,000 CU (one-time)|

Automation can only be upgraded, never downgraded. The upgrade is per-machine. A team might automate their Precision avionics machine (high throughput, needs quality control) while keeping manual labour on the basic airframe machine.

### **4.3.4 Labour Events**
Events fire automatically based on morale, or can be triggered by the Organiser (via sabotage/backroom deals):

|**Event**|**Trigger**|**Effect**|
| :- | :- | :- |
|Riot|Morale ≤ 15, or organiser-triggered|Production = 0 this cycle. Morale −40.|
|Strike|Organiser-triggered only|50% production loss. Morale −15.|
|Mass Turnover|Morale ≤ 35 (low threshold)|Skill −12, Morale −10, Headcount −15%.|
|Poached|Organiser-triggered via deal|Skill −15 (default), Headcount −10%. Possible R&D level theft.|

## **4.4 The Production Formula**
Production resolution runs the following chain for each team:

1. **Step 1 — R&D bookkeeping:** Complete any R&D investments due this cycle. Apply probabilistic R&D decay.
1. **Step 2 — Machine condition update:** Apply maintenance. Apply sabotage hits. Compute new condition and status.
1. **Step 3 — Labour state update:** Compute morale delta from wages and understaffing. Determine if a labour event fires.
1. **Step 4 — Binding constraint:** Units to produce = min(total machine throughput, total usable RM stock). If any component has zero throughput or stock, units\_to\_make = 0.
1. **Step 5 — Per-component simulation:** For each component, sample raw materials, draw output from a Normal distribution centred at (0.4 × rm\_mean + 0.6 × machine\_grade), with sigma modified by automation and skill.
1. **Step 6 — Drone assembly:** Combine six component output arrays. For each drone, sample one unit from each component. Apply weakest-link formula.
1. **Step 7 — Costs:** Compute maintenance cost total and wage cost total for this cycle.

### **4.4.1 The Weakest-Link Assembly Formula**
This is the core quality mechanic. When assembling a drone from six components, the formula deliberately punishes having one bad component:

**raw\_avg = mean(six\_component\_grades)**\
**wl\_weights = softmax(−grades × 0.30)   ← lower-grade components get higher weight**\
**wl\_avg = dot(wl\_weights, grades)**\
**drone\_grade = 0.40 × raw\_avg + 0.60 × wl\_avg**

With lambda=0.60 and beta=0.30, a single component at grade 20 (out of six otherwise at grade 80) will drag the drone grade down by approximately 20–25 points compared to a drone built purely on the average. The message is simple: your chain is only as strong as its weakest link.

## **4.5 Production API — Frontend Reference**

|**GET  /teams/{team\_id}/machines**||
| :- | :- |
|*Get all active machines for a team, grouped by component. Returns current condition, tier, grade, status, and standing maintenance decision.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**Returns:** { machines: [MachineOut], by\_component: { [component]: [MachineOut] } }||

|**PATCH  /teams/{team\_id}/machines/{machine\_id}**||
| :- | :- |
|*Update the maintenance level or desired throughput for one machine. Only callable during Phase 1 OPEN. PATCH — only send fields you want to change.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**machine\_id**|Integer.|
|**maintenance\_level**|none | basic | full | overhaul|
|**desired\_throughput**|Integer ≤ machine.throughput. Null = use full throughput.|
|**Returns:** Updated MachineOut with new decision state.||

|**POST  /teams/{team\_id}/machines**||
| :- | :- |
|*Purchase a new machine. Machine is available from the NEXT cycle. Cost is deducted immediately.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**tier**|basic | standard | industrial | precision|
|**component**|airframe | propulsion | avionics | fire\_suppression | sensing\_safety | battery|
|**asset\_id**|String. A unique name for this machine, e.g. 'avionics\_2'. Team-scoped.|
|**automation\_level**|manual | semi\_auto | full\_auto (default: manual)|
|**Returns:** MachineOut for the new machine.||

|**POST  /teams/{team\_id}/machines/{machine\_id}/upgrade-automation**||
| :- | :- |
|*One-time upgrade of automation level on a specific machine. Cost deducted immediately. Cannot downgrade.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**machine\_id**|Integer.|
|**target\_level**|semi\_auto | full\_auto (must be higher than current)|
|**Returns:** Updated MachineOut.||

|**GET  /teams/{team\_id}/labour**||
| :- | :- |
|*Get current labour state (skill, morale, headcount) and standing decisions (wage level, target headcount, training). Also returns total\_labour\_required and staffing\_delta.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**Returns:** { state: LabourStateOut, decisions: LabourDecisionOut }||

|**PATCH  /teams/{team\_id}/labour**||
| :- | :- |
|*Update standing labour decisions. PATCH semantics. Only callable during Phase 1 OPEN.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**wage\_level**|below\_market | market | above\_market|
|**target\_headcount**|Integer.|
|**training\_investment**|Boolean. One-shot; resets after cycle.|
|**Returns:** Confirmation message.||

|**GET  /teams/{team\_id}/rnd**||
| :- | :- |
|*Get all R&D levels for all components and focus areas, plus active in-progress investments.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**Returns:** { levels: { [component]: { quality: int, consistency: int, yield: int } }, active\_investments: [{component, focus\_area, started\_cycle, completes\_cycle, cost\_paid}] }||

|**POST  /teams/{team\_id}/rnd/invest**||
| :- | :- |
|*Start a new R&D investment for one component/focus combination. Cost is included in Phase 1 cost deduction. Takes 2 cycles to complete. Fails if max level (5) reached or investment already in progress for this slot.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**component**|airframe | propulsion | avionics | fire\_suppression | sensing\_safety | battery|
|**focus\_area**|quality | consistency | yield|
|**Returns:** { component, focus\_area, current\_level, target\_level, started\_cycle, completes\_cycle, cost\_paid: 10000 }||

|**GET  /cycles/{cycle\_id}/production/{team\_id}**||
| :- | :- |
|*Full production report for a team after Phase 1 resolution. Available from PHASE1\_DISPLAY onwards.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**team\_id**|Integer.|
|**Returns:** { units\_produced, binding\_constraint, skill\_at\_resolution, morale\_at\_resolution, labour\_event, drone\_output\_array (101 ints), component\_outputs: [{component, output\_array, total\_produced, total\_scrap, weighted\_mean, machine\_grade, sigma, rm\_mean, rnd\_bonuses}] }||

**Frontend Tip:** The production dashboard needs two modes. During Phase 1 OPEN: decisions panel (maintenance per machine, labour settings, R&D investments). During Phase 1 DISPLAY: results panel showing drone output array as a histogram, component breakdown table, and labour event notification. The output array is a 101-int array — render it as a grade distribution chart (x=grade, y=count).


# **5. Sales — Selling Your Drones**
## **5.1 Quality Thresholds**
After production, all drones in a team's combined pool (newly produced + carried from last cycle) are classified into four tiers using three game-level quality thresholds:

|**Tier**|**Grade Range**|**Default Thresholds**|
| :- | :- | :- |
|REJECT|< q\_hard|Grade < 30|
|SUBSTANDARD|q\_hard ≤ grade < q\_soft|30 ≤ grade < 50|
|STANDARD|q\_soft ≤ grade < q\_premium|50 ≤ grade < 75|
|PREMIUM|≥ q\_premium|Grade ≥ 75|

These thresholds are set by the Organiser at game creation and can be tightened or relaxed via global events. Brand score can effectively lower the q\_soft threshold by up to 15% for an 'Excellent' brand team — giving them a slight quality leniency on the standard market.

## **5.2 Sales Actions by Tier**
For each tier, teams choose one action. These decisions persist between cycles unless changed:

|**Action**|**Valid Tiers**|**Effect**|
| :- | :- | :- |
|SELL\_MARKET|SUBSTANDARD, STANDARD, PREMIUM|Sell at the default market price for that tier. Subject to market demand allocation.|
|SELL\_PREMIUM|PREMIUM only|Sell at the elevated premium price (4,800 CU/unit vs. 3,000 CU base). Boosts brand score.|
|SELL\_DISCOUNTED|Any|Sell below the default price. Team can set a custom price\_override. Improves price\_factor in market allocation.|
|HOLD|Any|Keep units in inventory for next cycle. Incurs holding cost of 40 CU/unit/cycle.|
|SCRAP|Any|Destroy units. Recover scrap value only (very low).|
|BLACK\_MARKET|REJECT only|Sell rejects through illegal channels at 600 CU/unit. Carries discovery risk and brand damage.|

**PR Advisory:** The black market option is intentionally presented without explicit moral framing in the UI. Teams discover the consequences through play. Marketing should describe it as 'an alternative distribution channel' — discovery-risk and consequences are part of the game design, not to be spoiled upfront.

## **5.3 The Market Simulation**
All teams sell into a single shared market. Market capacity is set by the Organiser (default: 2,000 units per cycle, modified by the market demand multiplier). The simulation allocates demand across teams using:

- **Brand weight:** Each team's share of demand is weighted by brand\_score^1.2. A team with brand score 80 vs. a team with brand score 40 gets roughly 2.3× more demand allocated.
- **Price factor:** Adjusted by (base\_price / actual\_price)^1.4. Selling below market price increases your demand share. Selling above decreases it.
- **Market share cap:** No single team can capture more than 70% of total market demand. Prevents total monopoly.
- **Supply constraint:** If total supply across all teams is less than market demand, all teams sell everything they offer. If supply exceeds demand, teams share proportionally.

## **5.4 Pricing Reference**

|**Tier**|**Action**|**Price (CU/unit)**|
| :- | :- | :- |
|REJECT|Scrap|~50 CU (from production scrap payout)|
|REJECT|Black Market|600 CU|
|SUBSTANDARD|SELL\_MARKET|1,400 CU|
|STANDARD|SELL\_MARKET|3,000 CU|
|PREMIUM|SELL\_MARKET|3,000 CU (brand signal, same price as Standard at market)|
|PREMIUM|SELL\_PREMIUM|4,800 CU|

## **5.5 Brand Score**
Brand is a persistent score (0–100) per team that decays slightly each cycle and is modified by sales behaviour. It affects market demand share allocation and provides quality threshold leniency.

|**Event**|**Brand Delta**|
| :- | :- |
|Sold units at SELL\_PREMIUM|+6.0|
|Sold units at SELL\_MARKET (Standard)|+1.5|
|Sold units at SUBSTANDARD tier|−5.0|
|Black market discovered|−25.0|
|Black market not discovered (ongoing)|−3.0 (per cycle risk signal)|
|Audit passed|+4.0|
|Audit failed|−18.0|
|Took a government loan|−8.0|
|Natural decay (each cycle)|× 0.94 (6% decay)|

|**Brand Tier**|**Score Range**|**Market Effect**|
| :- | :- | :- |
|POOR|0–24|Low demand weight. Visible signal to all teams of weakness.|
|FAIR|25–54|Average demand weight. Starting tier (brand starts at 50).|
|GOOD|55–79|Above-average demand weight. q\_soft leniency begins.|
|EXCELLENT|80–100|Maximum demand weight. Full 15% q\_soft leniency.|

## **5.6 Black Market — Risk System**
A team that assigns REJECT tier to BLACK\_MARKET faces a compounding risk structure:

**Base discovery probability: P = 0.55 × (black\_market\_units / total\_produced) × (1 − brand\_leniency)**

Additionally, each cycle a team continues black market sales, there is a separate 20% ongoing discovery roll (checked during the backroom phase).

**Standard discovery fine:** 3× the black market revenue from that cycle.

**Brand damage:** −25 brand score.

There is also a 25% chance that any discovery triggers the 'Bomberica' event — a comedic flavour escalation where the team's rejects are discovered to have been weaponised by a fictional micro-nation, resulting in a 15× fine multiplier instead of 3×. This is an easter egg designed to make a memorable, game-ending moment for teams that push the black market too aggressively.

## **5.7 Inventory Holding**
Units assigned the HOLD action remain in the drone\_stock inventory carried to the next cycle. A holding cost of 40 CU per unit per cycle is charged. Unsold premium inventory can be a deliberate strategy (waiting for better market conditions), but held stock counts against the leaderboard inventory score.

## **5.8 Diagnostics — Paid Intelligence**
During PHASE1\_DISPLAY, teams can purchase intelligence reports. Once bought, results persist for the cycle:

|**Type**|**Cost**|**What it reveals**|
| :- | :- | :- |
|production\_detail|2,000 CU|Your own exact component means, sigmas, R&D bonuses applied. Removes the vagueness from your own production report.|
|market\_intel|3,000 CU|Rival teams' brand scores, brand tiers, and last cycle's total units sold.|
|demand\_forecast|1,500 CU|Estimated market capacity for the next cycle based on current demand multiplier.|

**Design Intent:** Without buying diagnostics, teams operate on imprecise signal — they know roughly how many drones they produced and at what tier, but not their precise sigma or effective machine grade. Buying 'production\_detail' is most valuable for teams trying to optimise R&D spend. Buying 'market\_intel' is most valuable before choosing price strategy.

## **5.9 Sales API — Frontend Reference**

|**GET  /teams/{team\_id}/sales/preview**||
| :- | :- |
|*Preview how current drone stock splits across quality tiers, using this cycle's thresholds. Shows both produced-this-cycle and carried-from-previous. Available from PHASE1\_DISPLAY onwards.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**Returns:** { qr\_hard, qr\_soft, qr\_premium, total\_drones, produced\_this\_cycle, carried\_from\_previous, tier\_counts: {reject, substandard, standard, premium}, current\_decisions: {[tier]: {action, price\_override}} }||

|**GET  /teams/{team\_id}/sales**||
| :- | :- |
|*Get the team's current standing sales decisions for all four tiers.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**Returns:** { decisions: [{tier, action, price\_override, updated\_at}] }||

|**PATCH  /teams/{team\_id}/sales/{tier}**||
| :- | :- |
|*Update the sales decision for one quality tier. Only callable during PHASE2\_OPEN.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**tier**|reject | substandard | standard | premium|
|**action**|sell\_market | sell\_premium | sell\_discounted | hold | scrap | black\_market|
|**price\_override**|Float CU/unit (optional). Null = use default tier price.|
|**Returns:** Confirmation with updated decision.||

|**POST  /teams/{team\_id}/diagnostics**||
| :- | :- |
|*Purchase a paid diagnostic during PHASE1\_DISPLAY. Cost deducted immediately from funds.*||
|**Parameter**|**Description**|
|**team\_id**|Integer.|
|**diag\_type**|production\_detail | market\_intel | demand\_forecast|
|**Returns:** { diagnostic\_type, cost\_paid, result: {} } — result is the actual data for that diagnostic type.||

|**GET  /cycles/{cycle\_id}/sales/{team\_id}**||
| :- | :- |
|*Full sales report for a team after Phase 2 resolution.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**team\_id**|Integer.|
|**Returns:** { produced\_this\_cycle, carried\_from\_stock, counts\_by\_tier, revenue\_by\_tier, black\_market\_units, black\_market\_discovered, total\_units\_sold, total\_revenue, holding\_cost, brand\_before, brand\_after, brand\_delta }||

|**GET  /cycles/{cycle\_id}/financials/{team\_id}**||
| :- | :- |
|*Complete income statement for a team for a single cycle. Available after Phase 2 resolution.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**team\_id**|Integer.|
|**Returns:** { opening\_funds, revenue: {sales, scrap, black\_market, total}, costs: {procurement, maintenance, wages, rnd, diagnostics, inventory\_holding, black\_market\_fine, interest\_gov, interest\_inter, total}, net\_this\_cycle, closing\_funds, is\_solvent }||

**Frontend Tip:** The sales decision screen should show the tier preview prominently (as a stacked bar or pie), then four decision rows — one per tier — each with an action selector and an optional price input (only shown if SELL\_DISCOUNTED is chosen). A running revenue estimate based on current decisions and current tier counts adds value.


# **6. The Backroom Deals Phase**
The Backroom Deals Phase is Industrix's political layer. It runs between cycles, in the physical space of the event, facilitated by the Organiser. It is partially supported by the backend (deal logging, effect queue, discovery rolls) and partially run as live theatre (teams approaching the government table, making verbal offers).

## **6.1 How It Works in a Live Event**
- After Phase 2 completes, the Organiser opens the backroom phase and reveals the leaderboard.
- Teams can approach the Organiser and make offers: 'We'll pay 5,000 CU for a riot at Team Nexus's factory next cycle.'
- The Organiser privately evaluates the offer, negotiates terms, and if accepted: takes the CU (via the funds transfer system), records the deal, and queues the effect.
- Teams can also offer bribes to reduce their own discovery probability, negotiate loans from the government, or request the Organiser trigger a global event favourable to them.
- At the end of the backroom phase, the Organiser runs the fraud discovery rolls — any ongoing fraud may be publicly exposed.
- The Organiser then creates the next cycle, and play resumes.

**The Organiser's Role:** The Organiser is simultaneously a fair referee and a corrupt government. They should feel empowered to play favourites, create drama, and accept apparently ridiculous deals — this is by design. The most skilled Organiser will use the tools to create a story arc across the game, not just mechanically process requests.

## **6.2 The Effect Queue**
Effects are the Organiser's primary sabotage toolkit. Any queued effect fires automatically at the start of the specified cycle. The full list of effect types:

|**Effect Target**|**What it does**|**Payload Example**|
| :- | :- | :- |
|SHIPMENT\_DAMAGE\_PROB|Force damage probability on a team's component shipment|{ component: 'avionics', force\_prob: 1.0 }|
|SHIPMENT\_LOSS\_PROB|Force total loss probability on a component shipment|{ component: 'battery', force\_prob: 1.0 }|
|SOURCE\_COST\_MULTIPLIER|Raise or lower a source's price by multiplier|{ source\_id: 3, multiplier: 1.5 }|
|SOURCE\_QUALITY\_DELTA|Shift a source's quality mean up or down|{ source\_id: 3, delta: -15.0 }|
|MACHINE\_CONDITION\_HIT|Damage a specific machine's condition|{ machine\_asset\_id: 'avionics\_2', hit: 60.0 }|
|LABOUR\_MORALE\_DELTA|Spike or crash a team's workforce morale|{ delta: -30.0 }|
|LABOUR\_SKILL\_DELTA|Boost or steal skill points from a team's workforce|{ delta: -15.0 }|
|RND\_LEVEL\_DELTA|Remove or add R&D levels from a component/focus|{ component: 'avionics', focus: 'quality', delta: -1 }|
|FUNDS\_DELTA|Directly add or remove money from a team|{ amount: -10000.0 }|
|BRAND\_DELTA|Add or remove brand score|{ delta: -20.0 }|
|MARKET\_DEMAND\_DELTA|Globally shift market demand multiplier|{ delta: -0.3 }|
|QR\_THRESHOLD\_DELTA|Tighten or relax quality thresholds for all teams|{ qr\_soft\_delta: 10.0 }|
|AUDIT\_FORCE|Force a compliance audit on a team|{ team\_id: 2 }|
|BLACK\_MARKET\_FINE\_FORCE|Force discovery of black market activity|{ team\_id: 4 }|
|INVENTORY\_SEIZURE|Confiscate a fraction of a team's drone stock|{ fraction: 0.40 }|
|CUSTOM|Flavour text only — no mechanical effect|{ note: 'Regulatory memo issued.' }|

Effects can be scoped to SINGLE (one team) or GLOBAL (all teams). The attacker's cost is deducted at effect creation time. Effects can be cancelled (refund issued) if not yet applied.

## **6.3 Global Events**
The Organiser can declare global events that affect all teams. These can be pre-scheduled or applied immediately. Events include:

|**Event Type**|**Default Effect**|
| :- | :- |
|WAR\_DECLARED|Procurement costs spike across all sources.|
|SUPPLY\_CHAIN\_CRISIS|Random sources become unavailable for 1+ cycles.|
|MARKET\_BOOM|Market demand multiplier increases — more drones can be sold.|
|MARKET\_CRASH|Market demand multiplier crashes — oversupply hits all teams.|
|REGULATORY\_CRACKDOWN|Quality thresholds tighten — more drones fall into REJECT/SUBSTANDARD.|
|REGULATORY\_RELAX|Quality thresholds loosen — more drones qualify as STANDARD/PREMIUM.|
|TECH\_BREAKTHROUGH|All teams gain a free R&D level boost in a specified component.|
|LABOUR\_STRIKE\_WAVE|All teams take a morale hit this cycle.|
|CUSTOM|Organiser writes their own flavour text and applies effects manually.|

## **6.4 Government Loans**
The Organiser can extend government loans to struggling teams. These come with strings attached:

- **Interest rate:** 15% per cycle on outstanding principal. Auto-deducted each cycle.
- **Quality floor restriction:** If the borrowing team's drone weighted mean grade falls below 25 in any cycle while the loan is active, they go bankrupt (eliminated).
- **Brand penalty:** −8 brand score at time of loan (market signal of financial distress).
- **Restrictions:** Gov loan borrowers are restricted from certain backroom deals (the backend records this as a restrictions list on the loan).

Inter-team loans are also supported. These are negotiated between teams in the live space. The Organiser records them, the system disburses funds and tracks interest payments. Inter-team loan interest rates must be between 2% and 12% per cycle.

## **6.5 Discovery Rolls**
At the end of each backroom phase, the Organiser runs the discovery function. For each team with ongoing fraud:

|**Fraud Type**|**Base Discovery Probability per Cycle**|
| :- | :- |
|Black Market Sales (ongoing)|20% per cycle|
|Government Deal Fraud|15% per cycle|
|Cartel Pricing Arrangement|12% per cycle|

Discovered fraud results in fines (multipliers of 3–5× the relevant revenue) and brand damage. The Bomberica easter egg has a 25% chance of firing on any black market discovery, applying a 15× fine multiplier instead.

## **6.6 Leaderboard and Scoring**
The leaderboard is computed after Phase 2 but kept hidden until the Organiser opens the backroom phase. Teams discover their standings at the same moment, maximising drama. The composite score:

|**Component**|**Weight**|**How measured**|
| :- | :- | :- |
|Liquid Capital (Funds)|40%|Team's share of total funds across all teams.|
|Brand Score|30%|Brand score / 100.|
|Cumulative Revenue|20%|Team's share of total revenue earned across all cycles.|
|Inventory Efficiency|10%|Penalty for holding excess unsold inventory.|

## **6.7 Backroom API — Frontend Reference**

|**POST  /cycles/{cycle\_id}/backroom/open**||
| :- | :- |
|*Reveal the leaderboard and open the backroom deals phase. Call this after Phase 2 is complete.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** { message, teams\_ranked, top\_team }||

|**GET  /cycles/{cycle\_id}/leaderboard**||
| :- | :- |
|*Get the scored leaderboard. If team\_id is provided, only returns data if the leaderboard has been revealed. Organiser can always read it.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**team\_id**|Optional integer. If provided, checks reveal status.|
|**Returns:** { is\_revealed, standings: [{rank, team\_id, team\_name, composite\_score, score\_breakdown, raw}] }||

|**POST  /games/{game\_id}/effects**||
| :- | :- |
|*Queue a new effect for a future cycle. Attacker's funds are deducted at queue time.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**target\_type**|EffectTarget enum value — see §6.2|
|**scope**|single | global|
|**target\_team\_id**|Integer (required for SINGLE scope)|
|**apply\_at\_cycle**|Integer. Cycle number when effect fires.|
|**cost\_paid**|Float. Amount deducted from attacker\_team\_id.|
|**payload**|JSON object. Content depends on target\_type.|
|**Returns:** { effect\_id, type, fires\_at\_cycle, cost\_deducted }||

|**POST  /cycles/{cycle\_id}/backroom/run-discovery**||
| :- | :- |
|*Run fraud discovery rolls for all teams with ongoing fraudulent activity. Apply fines and brand damage. Returns public discovery events.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** { public\_events: [{team\_id, fraud\_type, outcome, fine, flavour}], total\_events }||

|**POST  /games/{game\_id}/admin/fine**||
| :- | :- |
|*Instantly fine a team. Can also be queued for next cycle.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**team\_id**|Integer.|
|**amount**|Float CU.|
|**reason**|String label.|
|**next\_cycle**|Boolean. If true, queues as an effect rather than applying immediately.|
|**Returns:** Confirmation with new balance or effect ID.||

|**POST  /games/{game\_id}/events**||
| :- | :- |
|*Declare a global event. To apply immediately, call /apply after creation.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**event\_type**|GlobalEventType enum.|
|**fires\_at\_cycle**|Integer.|
|**title**|String.|
|**params**|JSON. Event-specific parameters.|
|**Returns:** { event\_id, type, fires\_at\_cycle, title }||


# **7. Cycle Control — Organiser API**
All cycle phase transitions are manual. These endpoints are for the Organiser dashboard only — teams should never call them directly.

|**POST  /games/{game\_id}/cycles**||
| :- | :- |
|*Create the next cycle. Snapshots current market parameters. Opens Phase 1. Fails if a previous cycle is not complete.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**Returns:** { cycle\_id, cycle\_number, phase: 'phase1\_open' }||

|**GET  /cycles/{cycle\_id}/phase**||
| :- | :- |
|*Get current phase and all transition timestamps. Use this to poll cycle state on the Organiser dashboard.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** { current\_phase, timestamps: { phase1\_opened, phase1\_closed, phase1\_processed, phase2\_opened, ... } }||

|**POST  /cycles/{cycle\_id}/phase/close-phase1**||
| :- | :- |
|*Lock Phase 1 decisions. Teams can no longer change procurement, machine, or labour decisions.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** Confirmation.||

|**POST  /cycles/{cycle\_id}/phase/run-phase1**||
| :- | :- |
|*Run the full Phase 1 simulation. Procurement deliveries resolved, production simulated. Advances to PHASE1\_DISPLAY automatically. Returns summary per team (units produced, costs, can\_afford).*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** { message, team\_summary: { [team\_id]: { produced, phase1\_costs, current\_funds, can\_afford, shortfall } } }||

|**POST  /cycles/{cycle\_id}/phase/open-phase2**||
| :- | :- |
|*End the display/loan window and open Phase 2. Phase 1 costs are deducted. Loan interest is processed. Pass deduct\_phase1\_costs=false to skip deduction (e.g., for testing).*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**deduct\_phase1\_costs**|Boolean, default true.|
|**Returns:** Confirmation.||

|**POST  /cycles/{cycle\_id}/phase/close-phase2**||
| :- | :- |
|*Lock Phase 2 (sales) decisions.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** Confirmation.||

|**POST  /cycles/{cycle\_id}/phase/run-phase2**||
| :- | :- |
|*Run market simulation and sales resolution. Financial statements written. Leaderboard computed (hidden). Advances to COMPLETE.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** { team\_summary: { [team\_id]: { revenue, closing\_funds, brand, solvent } } }||

|**POST  /cycles/{cycle\_id}/phase/complete**||
| :- | :- |
|*Mark cycle fully complete. Required before creating the next cycle.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** Confirmation.||

|**GET  /games/{game\_id}/leaderboard**||
| :- | :- |
|*Simple funds-ranked standings. No scoring formula — just raw funds, brand, and revenue. Use for a quick live scoreboard during play.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**Returns:** { standings: [{rank, team\_name, funds, brand\_score, brand\_tier, has\_gov\_loan, total\_revenue, is\_active}] }||

|**GET  /cycles/{cycle\_id}/market**||
| :- | :- |
|*Post-resolution market summary. Organiser use only.*||
|**Parameter**|**Description**|
|**cycle\_id**|Integer.|
|**Returns:** { market\_capacity, total\_supply\_offered, total\_demand\_met, constraint\_type, team\_allocations }||


# **8. Game Setup — Before Play Begins**
## **8.1 What the Organiser Must Configure**
Before the game starts, the Organiser (usually the backend administrator) must:

1. **Create the game:** Set name, total cycles (default 6), and the three quality thresholds (qr\_hard, qr\_soft, qr\_premium). Also set market\_demand\_multiplier (default 1.0).
1. **Add teams:** Create each team with a name, PIN, and initial funds (default 100,000 CU). The system auto-seeds all default state (machines, labour, R&D, procurement decisions, sales decisions, inventory).
1. **Configure sources:** Add at least one source per component, ideally 2–3 per component for meaningful choice. Set quality\_mean, quality\_sigma, base\_cost\_per\_unit.
1. **Pre-plan global events:** Optionally schedule global events (market booms, crises) for specific cycles in advance. These can be kept secret and revealed dramatically.

## **8.2 Default Starting State for Each Team**

|**State Item**|**Default Value**|
| :- | :- |
|Initial Funds|100,000 CU|
|Starting Brand Score|50 (FAIR tier)|
|Machines|One STANDARD machine per component (6 total). Condition 100, Manual automation.|
|Labour|50 workers. Morale 60. Skill 40. Wage: Market.|
|R&D|All components at level 0 for all three focus areas.|
|Drone Inventory|Empty (0 drones).|
|Raw Material Stock|Empty (no carried inventory for Cycle 1).|

## **8.3 Setup API**

|**POST  /games/{game\_id}/sources**||
| :- | :- |
|*Add a raw material source. Can be called at any time, including between cycles.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**name**|String. Display name for this source.|
|**component**|Component type enum.|
|**quality\_mean**|Float 1–100.|
|**quality\_sigma**|Float >0. Spread of quality distribution.|
|**base\_cost\_per\_unit**|Float CU/unit.|
|**Returns:** SourceOut object.||

|**POST  /games/{game\_id}/transfers**||
| :- | :- |
|*Execute a direct asset transfer between teams (or from/to government). Used for loan disbursements, penalties, subsidies, and deal settlements.*||
|**Parameter**|**Description**|
|**game\_id**|Integer.|
|**from\_team\_id**|Integer or null (government source).|
|**to\_team\_id**|Integer or null (government destination).|
|**transfer\_type**|money | rnd\_level | raw\_material | drone\_stock|
|**payload**|JSON. { amount: 5000 } for money. See §6.2 for others.|
|**reason**|String. Audit trail note.|
|**Returns:** { transfer\_id, type, applied }||


# **9. Frontend Architecture Guide**
This section is written specifically for frontend developers. It describes the views required, how they map to API endpoints, and design principles for each.

## **9.1 Authentication Model**
Authentication is lightweight, appropriate for a controlled live event:

- **Teams:** Identify using team\_id (integer) passed in requests. PIN is stored as a SHA-256 hash. For this event's scale, the frontend should store team\_id and (optionally) verify PIN on login, then persist team\_id in session/local storage.
- **Organiser:** Organiser endpoints have no auth in the current backend. The Organiser dashboard should be deployed on a separate path, accessible only from the organiser's device, or protected by a simple environment-level secret.

## **9.2 State Polling**
The frontend must poll **GET /cycles/{cycle\_id}/phase** to detect phase transitions. Recommended poll interval: 5 seconds during active phases, 15 seconds between phases. When the phase changes, refresh all relevant data for the new phase.

## **9.3 Views — Team Application**

### **9.3.1 Dashboard / Home**
Persistent across all phases. Always shows:

- Current funds (from GET /teams/{team\_id}/sales/preview → use inventory.funds, or better: track from last financial log).
- Brand score + tier badge.
- Current cycle number and phase indicator.
- A simple 'what can I do now?' status message based on phase.

### **9.3.2 Procurement Screen (PHASE1\_OPEN)**
Six component rows. For each:

- Source selector: dropdown populated from GET /games/{game\_id}/sources?component=X
- Quantity input field (integer, 1–10,000).
- Transport mode selector: Air | Rail | Road.
- Estimated cost (live, from GET /teams/{team\_id}/procurement/cost-estimate).
- Submit button PATCH /teams/{team\_id}/procurement/{component}

- Total estimated procurement cost bar across all six components.
- Available funds minus estimated procurement cost (show 'deficit' warning if negative).

### **9.3.3 Factory Screen (PHASE1\_OPEN)**
Three tabs: Machines | Labour | R&D

**Machines tab:** 

- Card per machine showing: asset\_id, tier badge, grade, condition bar, status indicator, automation level, throughput.
- Maintenance level selector per machine (None / Basic / Full / Overhaul).
- Desired throughput input per machine.
- 'Buy Machine' button → modal with tier, component, asset\_id, automation\_level inputs.
- 'Upgrade Automation' button per machine (shown if not yet Full-Auto).

**Labour tab:** 

- Current state display: skill bar, morale bar, headcount, total labour required, staffing delta (surplus or deficit).
- Wage level selector: Below Market | Market | Above Market (with CU/worker/cycle shown).
- Target headcount number input.
- Training investment toggle (one-shot; shows +8 skill preview).
- Projected morale delta calculation shown live.

**R&D tab:** 

- 6×3 grid: one row per component, three columns (Quality / Consistency / Yield), showing current level (0–5) and a progress bar.
- For each cell: 'Invest' button (if level < 5 and no active investment). Show completion cycle if investment is in progress.
- Total R&D spend this cycle shown at bottom.

### **9.3.4 Production Results Screen (PHASE1\_DISPLAY)**
- Top: drone output histogram — bar chart with x=quality grade (1–100), y=unit count.
- Key stats: total produced, binding constraint (machine vs RM), units at each tier preview.
- Per-component table: component, output mean, scrap count, effective machine grade, sigma.
- Labour event notification (if riot/strike/etc fired).
- Procurement report: per-component, what arrived vs ordered, mean grade of shipment, any events (damaged / lost / sabotaged).
- Diagnostics panel: three purchase buttons with costs. Each expands to show result after purchase.

### **9.3.5 Sales Screen (PHASE2\_OPEN)**
- Top: tier breakdown panel (from GET /teams/{team\_id}/sales/preview).
- Four tier rows: REJECT | SUBSTANDARD | STANDARD | PREMIUM.
- Each row shows: unit count in that tier, action selector, optional price input (if SELL\_DISCOUNTED).
- Revenue estimate (live) based on current decisions and unit counts.
- 'Submit' button → PATCH /teams/{team\_id}/sales/{tier} for each changed tier.

### **9.3.6 Financial Report (after PHASE2\_PROCESSING)**
- Income statement layout: Revenue (sales / scrap / black market) − Costs (procurement / maintenance / wages / R&D / diagnostics / holding / fines / interest) = Net. Opening → Closing.
- Sales detail: units sold per tier, revenue per tier, held units, brand movement.
- Data from GET /cycles/{cycle\_id}/financials/{team\_id} and GET /cycles/{cycle\_id}/sales/{team\_id}.

### **9.3.7 Leaderboard (Backroom Phase only)**
- Only shown when is\_revealed = true (poll GET /cycles/{cycle\_id}/leaderboard?team\_id={team\_id}).
- Ranked table: rank, team name, composite score, breakdown bars (funds / brand / revenue / inventory).
- Highlight own team's row.

## **9.4 Views — Organiser Dashboard**

### **9.4.1 Cycle Control Panel**
- Current cycle number, current phase display, last transition timestamp.
- One large button for the next valid action: 'Close Phase 1' → 'Run Phase 1' → 'Open Phase 2' → 'Close Phase 2' → 'Run Phase 2' → 'Complete Cycle' → 'Create Next Cycle'.
- After Run Phase 1: team summary table (produced units, can\_afford boolean, shortfall).
- After Run Phase 2: team summary table (revenue, closing funds, solvent boolean).

### **9.4.2 Team Overview**
- Card per team: name, funds, brand score/tier, machines (condition summary), gov loan indicator, is\_active.
- Click team → full drill-down (machines detail, labour state, R&D levels, procurement decisions, current inventory).

### **9.4.3 Sources Manager**
- Table of all sources. Organiser can PATCH to change quality\_mean, quality\_sigma, base\_cost\_per\_unit, or toggle is\_available.
- Event log per source (expandable).

### **9.4.4 Backroom Toolkit**
- Effect queue panel: list of pending effects, create new effect form, cancel button per effect.
- Quick actions: Fine team | Bonus team | Destroy machine | Morale hit | Sabotage shipment.
- Global event creator.
- Loan manager: create loan, view active loans, record repayments.
- Discovery panel: 'Run Discovery Rolls' button, results table.

## **9.5 Key UX Principles**

|**Principle**|**Implementation**|
| :- | :- |
|Phase-aware UI|Every control that is only valid in certain phases must be disabled with a clear reason when the phase doesn't allow it. Don't hide controls — grey them out with a tooltip.|
|Live cost estimates|Procurement and R&D spend should show a running total that updates as decisions change, before submission. Teams should never be surprised by their costs.|
|Quality arrays as histograms|The 101-int quality array is the core data structure. Wherever it appears (shipment results, production results, drone stock), render it as a distribution chart, not a table.|
|Phase transition notifications|When the phase changes (detected by polling), show a full-screen or prominent notification: 'Phase 2 is now open — submit your sales decisions.'|
|Carry-forward indicators|For standing decisions (procurement, sales, maintenance), always show whether the displayed decision is new or carried from last cycle. Prevents confusion.|
|Financial feedback loop|After Phase 2, show a clear before/after funds view with the income statement breakdown. This is the most important feedback moment in the game.|


# **10. PR & Marketing Guide**
This section is written for the PR team and management. It describes how to explain the game to participants, sponsors, and press — at varying levels of depth.

## **10.1 Elevator Pitch (15 seconds)**
*"Industrix is a real-time business war game. You run a drone company, you compete to sell the best drones on the market, and you can bribe the government to destroy your rivals' factories. Every decision from procurement to pricing has real mathematical consequences. May the best CEO win."*

## **10.2 Event Description (for registration page / posters)**
**INDUSTRIX — The Drone Manufacturing War**\
Compete as the CEO of a fire-fighting drone company in this high-stakes management simulation. Procure raw materials, run your factory, manage your workforce, and outmanoeuvre your rivals in a shared marketplace — all while navigating a corrupt government that's willing to sell its influence to the highest bidder.\
\
Industrix is not a board game. It is a live, software-driven simulation where your decisions have real consequences, calculated by real formulas. The drone you sell is as good as the raw materials you bought, the machines you maintain, and the workers you keep happy.\
\
Make alliances. Break them. Bribe the government. Survive.

## **10.3 What Makes Industrix Different**

|**Compared to…**|**Industrix is different because…**|
| :- | :- |
|Generic business case simulations|Every number is calculated by an actual statistical model. The drone quality you produce is drawn from a Normal distribution. The market allocation uses competitive demand weighting. This isn't roleplay — it's applied business mathematics.|
|Board games like Monopoly or Catan|There is no fixed board, no dice for luck, no predetermined paths. The competitive landscape is emergent — shaped entirely by teams' collective decisions.|
|Stock market simulations|Industrix is an operational game, not a financial instruments game. Teams create value through production, not speculation. Understanding your own production system is as important as understanding the market.|

## **10.4 Key Talking Points for Management**
- **Academically grounded:** The simulation uses concepts from operations management (bottleneck analysis, throughput constraints), supply chain management (transport mode trade-offs, supplier quality variance), industrial economics (price elasticity, brand demand curves), and game theory (information asymmetry, competitive market dynamics).
- **Original software:** Industrix is a purpose-built simulation backend developed by Srijan's own engineering team. It is not a licensed or adapted product.
- **Scalable event:** The game can accommodate 4 to 20+ teams simultaneously. Each team can have 1–6 players managing different functions (procurement lead, factory manager, finance, sales). This makes it suitable for inter-college competitions.
- **Replayable:** No two games play out identically. The Organiser's event choices, teams' strategy divergence, and probabilistic production outcomes ensure every event is unique.

## **10.5 What to Emphasise for Different Audiences**

|**Audience**|**Emphasise**|
| :- | :- |
|Engineering / CS students|The backend simulation model: Normal distributions, weakest-link softmax assembly, demand allocation with elasticity. The technical depth is real.|
|Management / MBA students|The operational decisions: capital allocation, capacity planning, workforce management, brand strategy, competitive pricing.|
|General participants|The drama: a corrupt government, industrial espionage, the possibility of getting caught selling illegal drones to a fictional nation.|
|Faculty / Academic audience|The pedagogical design: learning by doing in a low-stakes, high-feedback environment. Operations, finance, and strategy integrated into a single experience.|
|Sponsors|The scale and repeatability: a flagship event that can grow, the branding opportunity in a technically sophisticated student-built product.|

## **10.6 What Not to Say**
- Do not describe Industrix as 'a drone game' or 'a factory game' — it is a complete business simulation. The drone manufacturing theme is flavour.
- Do not promise participants that the game is 'easy to learn'. It is deliberately complex. The correct pitch is: 'You will figure it out fast, and the depth reveals itself over rounds.'
- Do not describe the black market mechanic in marketing materials without framing it as risk. The game teaches that moral shortcuts have compounding consequences.


# **11. Appendix — Quick Reference**
## **11.1 All Game Constants**

|**Constant**|**Value**|**Where it applies**|
| :- | :- | :- |
|Starting funds|100,000 CU|Each team at game start|
|Quality grade range|0–100|All quality arrays|
|Machine starting condition|100|All machines at purchase|
|DEGRADED threshold|40|Below this = grade penalty|
|Max R&D level per focus|5|Per component per focus area|
|R&D cycles to complete|2 cycles|From investment to level gain|
|R&D decay probability|5% per cycle|Per level-above-0 per cycle|
|RM weight in output formula|40%|0\.40 × rm\_mean + 0.60 × machine\_grade|
|Base output sigma|15|Before automation/skill/R&D|
|Assembly lambda (weakest link)|0\.60|1\.0 = pure weakest-link, 0.0 = pure average|
|Assembly beta (softmax sharp.)|0\.30|Higher = sharper weakest-link|
|Market demand capacity|2,000 units/cycle (default)|Adjusted by demand multiplier|
|Price elasticity|1\.4|Demand response to price deviation|
|Brand demand exponent|1\.2|Demand weight = brand\_score^1.2|
|Max market share per team|70%|No monopoly cap|
|Brand decay per cycle|×0.94 (6%)|Applied before new brand deltas|
|Black market price|600 CU/unit|REJECT tier only|
|Holding cost|40 CU/unit/cycle|Unsold drones in inventory|
|BM discovery base prob.|55%|Modulated by volume fraction and brand|
|BM standard fine|3× BM revenue|On discovery|
|Bomberica probability|25%|On any BM discovery|
|Bomberica fine|15× BM revenue|On Bomberica trigger|
|Gov loan interest rate|15%/cycle|On outstanding principal|
|Gov loan quality floor|25|Drone mean below this = bankrupt|
|Score weight: funds|40%|Composite leaderboard|
|Score weight: brand|30%|Composite leaderboard|
|Score weight: revenue|20%|Composite leaderboard|
|Score weight: inventory|10%|Composite leaderboard (penalty)|

## **11.2 Component Enum Values**
Use these exact strings in all API calls:

|**Display Name**|**API Value**|
| :- | :- |
|Airframe|airframe|
|Propulsion|propulsion|
|Avionics|avionics|
|Fire Suppression|fire\_suppression|
|Sensing & Safety|sensing\_safety|
|Battery|battery|

## **11.3 Cycle Phase Flow Diagram**
Phases in order, with the triggering action for each transition:

|**From Phase**|**Trigger**|**To Phase**|
| :- | :- | :- |
|—|POST /games/{id}/cycles|PHASE1\_OPEN|
|PHASE1\_OPEN|POST /cycles/{id}/phase/close-phase1|PHASE1\_CLOSED|
|PHASE1\_CLOSED|POST /cycles/{id}/phase/run-phase1|PHASE1\_DISPLAY (via PROCESSING)|
|PHASE1\_DISPLAY|POST /cycles/{id}/phase/open-phase2|PHASE2\_OPEN|
|PHASE2\_OPEN|POST /cycles/{id}/phase/close-phase2|PHASE2\_CLOSED|
|PHASE2\_CLOSED|POST /cycles/{id}/phase/run-phase2|COMPLETE (via PROCESSING)|
|COMPLETE|POST /cycles/{id}/phase/complete|Cycle done; create next|

## **11.4 What Teams Know vs. What They Don't**

|**Teams always know**|**Teams do NOT know (without buying diagnostics)**|
| :- | :- |
|Their own funds, brand score, brand tier|Their exact component output sigma or machine effective grade|
|Their own procurement decisions and costs|Rivals' brand scores or sales volumes|
|Their own drone output array (histogram)|Next cycle's market demand capacity|
|Their own tier breakdown (REJECT/etc.)|Whether their black market activity has been detected|
|Their own labour state (morale, skill)|Exact R&D bonus amounts applied to this cycle's production|
|Their own R&D levels and investments|Whether the Organiser has queued an effect targeting them|
|The quality thresholds (qr\_hard, soft, premium)|Other teams' machine conditions or maintenance choices|

## **11.5 Bankruptcy Conditions**
- A team with an active government loan whose drone quality weighted mean falls below 25 in any cycle is immediately declared bankrupt (team.is\_active = false). They are excluded from all subsequent cycles.
- There is no bankruptcy from funds alone (funds floor at 0 CU). A team can survive with zero funds but cannot pay for anything — effectively crippled.
- The Organiser can manually eliminate a team using a FUNDS\_DELTA effect of a large negative amount if desired.
