# INDUSTRIX — Frontend System UI Specification

> **Source of truth**: Stitch project `INDUSTRIX` (ID `6439295227128226073`)
> **Tech stack**: React · Zustand · TailwindCSS
> **This is NOT a design exploration.** This is a strict system UI specification aligned with backend APIs.

---

## Table of Contents

1. [Design Tokens & Theme](#1-design-tokens--theme)
2. [Global Layout](#2-global-layout)
3. [Shared Components](#3-shared-components)
4. [Page 1 — Raw Materials (Procurement)](#4-page-1--raw-materials-procurement)
5. [Page 2 — Production](#5-page-2--production)
6. [Page 3 — Inventory](#6-page-3--inventory)
7. [Page 4 — Results / Event](#7-page-4--results--event)
8. [State Management (Zustand)](#8-state-management-zustand)
9. [API Reference](#9-api-reference)
10. [UI Constraints — What NOT to Build](#10-ui-constraints--what-not-to-build)

---

## 1. Design Tokens & Theme

Derived from the Stitch INDUSTRIX design system ("Obsidian Architect" / Organic Brutalism).

### Colors

| Token               | Value       | Usage                                  |
|----------------------|-------------|----------------------------------------|
| `surface`            | `#111417`   | Main page background                   |
| `surface-low`        | `#191c1f`   | Sidebar, inset panels                  |
| `surface-container`  | `#1d2023`   | Card backgrounds                       |
| `surface-high`       | `#282a2e`   | Elevated cards, hover states           |
| `surface-highest`    | `#323539`   | Active tab, selected row               |
| `surface-bright`     | `#37393d`   | Hover state on dark containers         |
| `primary`            | `#dab9ff`   | Primary text accent, active tabs       |
| `primary-container`  | `#b072fb`   | Gradient end, button accent            |
| `on-surface`         | `#e1e2e7`   | Primary text                           |
| `on-surface-variant` | `#cec2d5`   | Secondary text (body copy, labels)     |
| `outline`            | `#978d9e`   | Muted borders, dividers                |
| `outline-variant`    | `#4b4453`   | Ghost borders (15% opacity)            |
| `tertiary`           | `#efc050`   | Warning accent, status chips           |
| `error`              | `#ffb4ab`   | Error text, overspend warnings         |
| `error-container`    | `#93000a`   | Critical state backgrounds             |

### Typography

| Role         | Font Family      | Usage                          |
|--------------|------------------|--------------------------------|
| Display/H1   | Space Grotesk    | Page titles, large metrics     |
| Headlines    | Space Grotesk    | Section headings, tab labels   |
| Body         | Inter            | Data values, descriptions      |
| Labels/Mono  | Inter            | Input labels, readouts, chips  |

**Rules:**
- Display-level text: **UPPERCASE** always
- All headings: **UPPERCASE**
- Body text, input values: normal case
- Numeric readouts: `label-md` weight

### Shape

- **Border radius: `0px` on everything.** No rounded corners. This is the industrial aesthetic.
- No `1px solid` borders to separate regions — use background color shifts instead.
- Ghost borders: `outline-variant` at `15%` opacity only when needed for accessibility.

### Elevation

- No drop shadows on static elements. Use tonal layering (`surface` → `surface-low` → `surface-high`).
- Floating elements (modals, tooltips): `box-shadow: 0 20px 40px rgba(5,7,10,0.4)`
- Glassmorphism on overlays: `surface-container-lowest` at 70% opacity + `backdrop-blur: 20px`

---

## 2. Global Layout

```
┌───────────────────────────────────────────────────────┐
│  TOP NAVBAR                                           │
│  HOME | MARKET | INVENTORY | EVENT         | LOGOUT   │
├──────────┬────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT AREA                        │
│          │                                            │
│ [icon]   │  ┌─────────────────────────────────────┐  │
│ RAW      │  │ COMPONENT TABS (when applicable)    │  │
│ MATERIALS│  └─────────────────────────────────────┘  │
│          │                                            │
│ [icon]   │  ┌──────────────────┬──────────────────┐  │
│ MARKETING│  │ INPUT PANEL      │ DETAILS PANEL    │  │
│          │  │ (left ~60%)      │ (right ~40%)     │  │
│ [icon]   │  │                  │                  │  │
│ AUTOMATION│ │                  │                  │  │
│ LEVEL    │  └──────────────────┴──────────────────┘  │
│          │                                            │
│          │  ┌─────────────────────────────────────┐  │
│          │  │ BOTTOM BAR (totals + action button) │  │
│          │  └─────────────────────────────────────┘  │
└──────────┴────────────────────────────────────────────┘
```

### Top Navbar

- Items: `HOME` · `MARKET` · `INVENTORY` · `EVENT` · `LOGOUT`
- Background: `surface-low` (`#191c1f`)
- Active item: text in `primary` (`#dab9ff`)
- Inactive items: text in `on-surface-variant`
- Font: Space Grotesk, uppercase, `label-md`
- `LOGOUT` is right-aligned, separated visually

### Left Sidebar

- Width: fixed, narrow (~200px)
- Background: `surface-low` (`#191c1f`)
- Items (top-to-bottom):
  1. **RAW MATERIALS** — icon: `factory` / `inventory_2`
  2. **MARKETING** — icon: `campaign`
  3. **AUTOMATION LEVEL** — icon: `precision_manufacturing`
- Active item: background `surface-highest`, text `primary`
- Inactive items: text `on-surface-variant`
- Font: Space Grotesk, uppercase, `label-sm`
- Items correspond to sidebar navigation within the current page context

### Component Tabs

Used on **Procurement** and **Production** pages.

- 6 tabs in a horizontal row:
  1. `AIRFRAME` — icon: `architecture`
  2. `PROPULSION` — icon: `earth_engine` (or rocket)
  3. `AVIONICS` — icon: `settings_input_component`
  4. `FIRE SUPPRESSION` — icon: `fire_extinguisher`
  5. `SENSING & SAFETY` — icon: `sensors`
  6. `BATTERY` — icon: `battery_full`
- Active tab: `surface-highest` background, `primary` text
- Inactive tabs: `surface-container` background, `on-surface-variant` text
- Font: Space Grotesk, uppercase, `label-sm`
- 0px border radius

**Backend mapping:**
```
Tab Label          → ComponentType enum value
─────────────────────────────────────────────
AIRFRAME           → "airframe"
PROPULSION         → "propulsion"
AVIONICS           → "avionics"
FIRE SUPPRESSION   → "fire_suppression"
SENSING & SAFETY   → "sensing_safety"
BATTERY            → "battery"
```

---

## 3. Shared Components

### `<SendDecisionsButton />`
- Label: **"SEND DECISIONS"**
- Style: solid gradient (`primary` → `primary-container`, 135°), `on-primary` text, 0px radius
- Full width of bottom bar
- Disabled state: reduced opacity, cursor not-allowed
- **Disabled when backend phase does not match the current page's expected phase**

### `<StatusChip />`
- Rectangular (0px radius)
- `label-sm` bold text
- Variants:
  - Active: `primary` background
  - Warning: `tertiary` background
  - Error: `error` background

### `<MetricCard />`
- Background: `surface-container`
- Label: `label-sm` uppercase, `on-surface-variant`
- Value: `headline-md` or `display-lg`, `on-surface`
- 0px radius, no border

### `<WarningBanner />`
- Background: `tertiary` at 10% opacity
- Border-left: 3px solid `tertiary`
- Text: `on-surface`, `body-sm`
- **Non-blocking** — never prevents "SEND DECISIONS"

---

## 4. Page 1 — Raw Materials (Procurement)

**Stitch reference screen:** "Refined Procurement Console"
**Active when:** `phase === "procurement_open"`

### Layout

```
┌──────────────────────────────────────────────────┐
│  COMPONENT TABS                                  │
├──────────────────────────────────────────────────┤
│  PROCUREMENT  (page heading, uppercase)          │
├───────────────────────────┬──────────────────────┤
│  INPUT SECTION (left)     │  SUPPLIER DETAILS    │
│                           │  (right panel)       │
│  ┌─ Supplier Dropdown ──┐ │                      │
│  │ [name ▾]             │ │  Name:  AeroStruc    │
│  │ quality | consistency│ │  Quality:     0.92   │
│  │ | cost               │ │  Consistency: 0.04   │
│  └──────────────────────┘ │  Cost/unit: $450.00  │
│                           │                      │
│  Quantity: [____] (input) │  Component Cost:     │
│                           │  $0.00               │
│  Transport Mode:          │                      │
│  [ROAD] [RAIL] [AIR]     │  Remaining Funds:    │
│                           │  $124,500.00         │
│                           │                      │
│  ┌─ WARNING AREA ───────────────────────────────┐│
│  │ ⚠ Spending exceeds 80% of available funds   ││
│  └──────────────────────────────────────────────┘│
├──────────────────────────────────────────────────┤
│  Total Procurement Cost: $14,250.00              │
│  Global Funds Remaining: $110,250.00             │
│  ┌──────────────────────────────────────────────┐│
│  │         SEND DECISIONS                       ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

### Component Structure

```
ProcurementPage
├── ComponentTabs              (shared)
├── ProcurementInputPanel
│   ├── SupplierDropdown       (per-component)
│   ├── QuantityInput          (number, editable)
│   └── TransportModeSelector  (ROAD | RAIL | AIR toggle)
├── SupplierDetailsPanel       (read-only, right side)
│   ├── SupplierName
│   ├── QualityDisplay
│   ├── ConsistencyDisplay
│   ├── CostPerUnitDisplay
│   ├── ComponentCostDisplay   (quantity × cost_per_unit × transport_multiplier)
│   └── RemainingFundsDisplay
├── WarningArea                (non-blocking notifications)
└── ProcurementBottomBar
    ├── TotalProcurementCost
    ├── GlobalFundsRemaining
    └── SendDecisionsButton
```

### Input Controls

| Control             | Type               | Backend Field                       | Notes                                  |
|----------------------|--------------------|------------------------------------|----------------------------------------|
| Supplier dropdown    | `<select>`         | `source_id` (int)                  | Options loaded from `GET /team/sources` filtered by component. Each option shows: name, quality_mean, quality_sigma, base_cost_per_unit |
| Quantity             | `<input number>`   | `quantity` (int, 0–10000)          | Editable. Stepped by 1.               |
| Transport mode       | Toggle group       | `transport` (enum: road/rail/air)  | Three toggle buttons. Default: `road`  |

### Supplier Dropdown — Option Display Format

Each option in the dropdown should display:
```
{name}  ·  Q: {quality_mean}  ·  σ: {quality_sigma}  ·  ${base_cost_per_unit}/unit
```

### Right Panel — Read-Only Fields

| Field               | Source                                                    |
|----------------------|----------------------------------------------------------|
| Name                 | `selectedSource.name`                                    |
| Quality              | `selectedSource.quality_mean`                            |
| Consistency          | `selectedSource.quality_sigma`                           |
| Cost per unit        | `selectedSource.base_cost_per_unit`                      |
| Component Cost       | `quantity × base_cost_per_unit × transport_cost_mult`    |
| Remaining Funds      | `inventory.funds − totalProcurementCost`                 |

**Transport cost multipliers** (from backend `core/config.py`):
| Mode   | Multiplier |
|--------|------------|
| `road` | `1.0`      |
| `rail` | `1.4`      |
| `air`  | `2.5`      |

### Warning Area

Shown below inputs. Non-blocking (warning only, does not disable submit).

| Condition                                              | Message                                         |
|--------------------------------------------------------|--------------------------------------------------|
| `totalProcurementCost > 0.8 × inventory.funds`        | "⚠ Spending exceeds 80% of available funds"     |
| `totalProcurementCost > inventory.funds`               | "⚠ OVERSPENDING: Total cost exceeds balance"    |

### Bottom Bar

| Element                   | Value                                           |
|----------------------------|-------------------------------------------------|
| Total Procurement Cost     | Sum of (quantity × cost × transport_mult) for all 6 components |
| Global Funds Remaining     | `inventory.funds − totalProcurementCost`        |
| Button                     | **SEND DECISIONS**                              |

### Behavior

- **Default values**: On page load, fetch `GET /team/procurement` → populate last-submitted decisions for each component
- **Editing**: User switches between component tabs, modifies supplier/quantity/transport per component
- **Local state only**: All edits are local. Nothing is persisted until "SEND DECISIONS" is clicked
- **Submit**: `PATCH /team/procurement` with full `decisions` map → shows success/error toast
- **Disabled state**: All inputs disabled when `phase !== "procurement_open"`

### State Variables (Zustand: `useProcurementStore`)

```typescript
interface ProcurementState {
  // Per-component decisions (local, uncommitted)
  decisions: Record<ComponentType, {
    source_id: number;
    quantity: number;
    transport: 'road' | 'rail' | 'air';
  }>;

  // Data
  sources: Source[];              // all suppliers, fetched once
  selectedComponent: ComponentType;

  // Computed (derived, not stored)
  // totalProcurementCost
  // componentCost (for current tab)
  // remainingFunds

  // Actions
  setComponent: (c: ComponentType) => void;
  setDecision: (component: ComponentType, field: string, value: any) => void;
  fetchSources: () => Promise<void>;
  fetchExistingDecisions: () => Promise<void>;
  submitDecisions: () => Promise<void>;
}
```

### API Interactions

| Action         | Method   | Endpoint              | Body                          |
|----------------|----------|-----------------------|-------------------------------|
| Load sources   | `GET`    | `/team/sources`*      | —                             |
| Load defaults  | `GET`    | `/team/procurement`   | —                             |
| Submit         | `PATCH`  | `/team/procurement`   | `{ decisions: { ... } }`     |
| Load funds     | `GET`    | `/team/me`            | —                             |

*Note: Sources endpoint needs to be confirmed from backend. Sources may be loaded from seed data or a dedicated endpoint.

---

## 5. Page 2 — Production

**Stitch reference screen:** "Final Production Console"
**Active when:** `phase === "production_open"`

### Layout

```
┌──────────────────────────────────────────────────┐
│  COMPONENT TABS                                  │
├──────────────────────────────────────────────────┤
│  PRODUCTION  (page heading, uppercase)           │
├───────────────────────────┬──────────────────────┤
│  INPUT SECTION (left)     │  COST SUMMARY        │
│                           │  (right panel)       │
│  MAINTENANCE              │                      │
│  [NONE] [BASIC] [FULL]    │  Maintenance Cost:   │
│                           │  $X                  │
│  R&D INVESTMENT           │                      │
│  [________] (number)      │  R&D Cost:           │
│                           │  $X                  │
│  WORKFORCE                │                      │
│  Wage Level:              │  Workforce Cost:     │
│  [LOW] [MARKET] [HIGH]    │  $X                  │
│                           │                      │
│  Headcount:               │  ────────────────    │
│  [________] (number)      │  TOTAL PRODUCTION    │
│                           │  COST: $X            │
│  AUTOMATION               │                      │
│  [MANUAL][SEMI-AUTO]      │                      │
│  [FULL-AUTO]              │                      │
├──────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐│
│  │         SEND DECISIONS                       ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

### Component Structure

```
ProductionPage
├── ComponentTabs              (shared)
├── ProductionInputPanel
│   ├── MaintenanceSelector    (NONE | BASIC | FULL toggle)
│   ├── RndInvestmentInput     (number input)
│   └── WorkforceSection
│       ├── WageLevelSelector  (LOW | MARKET | HIGH toggle)
│       ├── HeadcountInput     (number input, editable)
│       └── AutomationSelector (MANUAL | SEMI-AUTO | FULL-AUTO toggle)
├── CostSummaryPanel           (read-only, right side)
│   ├── MaintenanceCostDisplay
│   ├── RndCostDisplay
│   ├── WorkforceCostDisplay
│   └── TotalProductionCostDisplay
└── ProductionBottomBar
    └── SendDecisionsButton
```

### Input Controls

| Control             | Type             | Backend Field                            | Values / Mapping                             |
|----------------------|------------------|------------------------------------------|----------------------------------------------|
| Maintenance          | Toggle group     | `component_decisions[comp].maintenance`  | `none` · `basic` · `full`                    |
| R&D Investment       | `<input number>` | `component_decisions[comp].rnd_invest`   | `{ focus: RndFocus, levels: 1-5 }` — number maps to spend = `levels × 10000` |
| Wage Level           | Toggle group     | `wage_level` (top-level)                 | `below_market` · `market` · `above_market`   |
| Headcount            | `<input number>` | `target_headcount` (top-level, 0–500)    | Editable number                              |
| Automation           | Toggle group     | `upgrade_automation` (top-level)         | `manual` · `semi_auto` · `full_auto`         |

**Display label → Backend enum mapping:**

| UI Label     | Backend Value     |
|--------------|-------------------|
| LOW          | `below_market`    |
| MARKET       | `market`          |
| HIGH         | `above_market`    |
| MANUAL       | `manual`          |
| SEMI-AUTO    | `semi_auto`       |
| FULL-AUTO    | `full_auto`       |
| NONE         | `none`            |
| BASIC        | `basic`           |
| FULL         | `full`            |

### Right Panel — Cost Summary (Read-Only, Computed Locally)

| Field               | Computation                                                            |
|----------------------|------------------------------------------------------------------------|
| Maintenance Cost     | Sum of `MAINTENANCE_COST[level]` per component. Values: none=$0, basic=$500, full=$1500 |
| R&D Cost             | `levels × $10,000` per component with R&D                             |
| Workforce Cost       | `headcount × WAGE_COST_PER_WORKER[wage_level]`. Values: below_market=$300, market=$500, above_market=$750 |
| Total Production Cost| Sum of all above                                                       |

### Behavior

- **Default values**: On page load, fetch `GET /team/production` → populate last-submitted decisions
- **Component-level decisions**: Maintenance and R&D are per-component (user switches tabs)
- **Top-level decisions**: Wage level, headcount, automation are global (shared across all tabs)
- **Local state only**: Edits are local until "SEND DECISIONS"
- **Submit**: `PATCH /team/production` with merged payload
- **Disabled state**: All inputs disabled when `phase !== "production_open"`

### State Variables (Zustand: `useProductionStore`)

```typescript
interface ProductionState {
  // Per-component decisions
  componentDecisions: Record<ComponentType, {
    maintenance: 'none' | 'basic' | 'full';
    rnd_invest: { focus: string; levels: number } | null;
  }>;

  // Global decisions
  wageLevel: 'below_market' | 'market' | 'above_market';
  targetHeadcount: number;
  upgradeAutomation: 'manual' | 'semi_auto' | 'full_auto';

  selectedComponent: ComponentType;

  // Actions
  setComponent: (c: ComponentType) => void;
  setMaintenance: (comp: ComponentType, level: string) => void;
  setRndInvest: (comp: ComponentType, levels: number) => void;
  setWageLevel: (level: string) => void;
  setHeadcount: (count: number) => void;
  setAutomation: (level: string) => void;
  fetchExistingDecisions: () => Promise<void>;
  submitDecisions: () => Promise<void>;
}
```

### API Interactions

| Action         | Method   | Endpoint              | Body                                    |
|----------------|----------|-----------------------|-----------------------------------------|
| Load defaults  | `GET`    | `/team/production`    | —                                       |
| Submit         | `PATCH`  | `/team/production`    | `{ component_decisions, wage_level, target_headcount, upgrade_automation }` |

### What NOT to Include

- ❌ Machine tiers / upgrade systems (`MachineTier` enum exists in backend but is NOT in the simplified Stitch UI)
- ❌ Overhaul maintenance option (backend supports it, UI does not — use only NONE/BASIC/FULL)
- ❌ Extra dropdowns or complex nested controls
- ❌ Machine condition displays

---

## 6. Page 3 — Inventory

**Stitch reference screen:** "Simplified Inventory Console"
**Accessible during:** any phase (read-only page)

### Layout

```
┌──────────────────────────────────────────────────┐
│  INVENTORY  (page heading, uppercase)            │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌───────────────────┐  ┌───────────────────┐   │
│  │  GLOBAL FUNDS     │  │  BRAND SCORE      │   │
│  │  $124,500.00      │  │  72.4             │   │
│  │  CR               │  │  GOOD             │   │
│  └───────────────────┘  └───────────────────┘   │
│                                                  │
│  RAW MATERIALS STOCK                             │
│  ┌──────────────────────────────────────────┐   │
│  │ Component            │  Units            │   │
│  ├──────────────────────┼───────────────────┤   │
│  │ Airframe             │  0                │   │
│  │ Propulsion           │  0                │   │
│  │ Avionics             │  0                │   │
│  │ Fire Suppression     │  0                │   │
│  │ Sensing & Safety     │  0                │   │
│  │ Battery              │  0                │   │
│  └──────────────────────┴───────────────────┘   │
│                                                  │
│  FINISHED DRONES                                 │
│  ┌──────────────────────────────────────────┐   │
│  │ Total Units: 0                           │   │
│  ├──────────────────────────────────────────┤   │
│  │ Reject:       0                          │   │
│  │ Substandard:  0                          │   │
│  │ Standard:     0                          │   │
│  │ Premium:      0                          │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  SCRAP REJECT UNITS                      │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Component Structure

```
InventoryPage
├── PageHeading              ("INVENTORY")
├── MetricCardsRow
│   ├── MetricCard           (Global Funds + "CR" label)
│   └── MetricCard           (Brand Score + brand tier label)
├── RawMaterialsTable        (6 rows, read-only)
├── FinishedDronesSection
│   ├── TotalUnitsDisplay
│   └── TierBreakdown        (reject, substandard, standard, premium)
└── ActionSection
    └── ScrapRejectButton    ("SCRAP REJECT UNITS")
```

### Data Fields — All Read-Only

| Field               | Source (from `GET /team/me`)       | Notes                           |
|----------------------|------------------------------------|---------------------------------|
| Global Funds         | `inventory.funds`                 | Formatted as currency           |
| Brand Score          | `inventory.brand_score`           | Numeric, 0–100                  |
| Brand Tier           | `inventory.brand_tier`            | `poor`/`fair`/`good`/`excellent`|
| Drone Stock Total    | `inventory.drone_stock_total`     | Integer                         |
| Workforce Size       | `inventory.workforce_size`        | (displayed if needed)           |

**Raw Materials Stock**: Requires a separate endpoint or is part of inventory data. Display 6 rows:
- Component Name (human-readable) | Units (integer)

**Finished Drones Breakdown** (`drone_stock` array from inventory):
- Index 0: Reject
- Index 1: Substandard
- Index 2: Standard  
- Index 3: Premium

### Actions

| Button                 | Action                                  | Condition                        |
|------------------------|-----------------------------------------|----------------------------------|
| SCRAP REJECT UNITS     | `PATCH /team/sales` with `{ decisions: { reject: { action: "scrap" } } }` | Only active during `sales_open` phase. Disabled otherwise. |

### State Variables (Zustand: `useInventoryStore`)

```typescript
interface InventoryState {
  funds: number;
  brandScore: number;
  brandTier: string;
  droneStockTotal: number;
  droneBreakdown: {
    reject: number;
    substandard: number;
    standard: number;
    premium: number;
  };
  rawMaterialStocks: Record<ComponentType, number>;
  workforceSize: number;

  // Actions
  fetchInventory: () => Promise<void>;
  scrapRejectUnits: () => Promise<void>;
}
```

### API Interactions

| Action            | Method   | Endpoint            | Body                                                    |
|-------------------|----------|---------------------|---------------------------------------------------------|
| Load inventory    | `GET`    | `/team/me`          | —                                                       |
| Scrap rejects     | `PATCH`  | `/team/sales`       | `{ decisions: { reject: { action: "scrap" } } }`       |

### What NOT to Include

- ❌ Editing stock values
- ❌ Charts, graphs, analytics
- ❌ Trend lines
- ❌ Historical data

---

## 7. Page 4 — Results / Event

**Stitch reference screen:** "Round Results Leaderboard"

### Two States

#### State A: Round Results (during `backroom` phase)

```
┌──────────────────────────────────────────────────────────────┐
│  ROUND RESULTS  (page heading, uppercase)                    │
│  Cycle {N} Final Audit                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────┬────────────┬───────┬─────────┬────────┬────────┬──────────┬─────────┐
│  │ RANK │ TEAM       │ SCORE │ FUNDS   │ PROFIT │ BRAND  │ QUALITY  │ PENALTY │
│  ├──────┼────────────┼───────┼─────────┼────────┼────────┼──────────┼─────────┤
│  │ 1    │ Team Alpha │ 87.3  │ 142,000 │ 42,000 │ 78.5   │ 72.1     │ 1,200   │
│  │ 2    │ Team Beta  │ 73.1  │ 118,000 │ 18,000 │ 65.2   │ 68.4     │ 3,400   │
│  │ ...  │ ...        │ ...   │ ...     │ ...    │ ...    │ ...      │ ...     │
│  └──────┴────────────┴───────┴─────────┴────────┴────────┴──────────┴─────────┘
│                                                              │
│  * Own team row highlighted with primary accent              │
└──────────────────────────────────────────────────────────────┘
```

#### State B: Backroom Phase / Read-Only

- Same table layout
- **"READ ONLY" indicator**: Chip or banner at top-right, styled as `StatusChip` with `tertiary` color
- No interactive elements

### Component Structure

```
ResultsPage
├── PageHeading            ("ROUND RESULTS" + "Cycle {N} Final Audit")
├── ReadOnlyIndicator      (shown during backroom, chip/banner)
└── LeaderboardTable
    ├── TableHeader        (RANK | TEAM | SCORE | FUNDS | PROFIT | BRAND | QUALITY | PENALTY)
    └── TableRows
        └── LeaderboardRow (highlighted if own team)
```

### Table Columns

| Column   | Backend Field          | Format            |
|----------|------------------------|--------------------|
| RANK     | `rank`                | Integer            |
| TEAM     | `team_name`           | String             |
| SCORE    | `composite_score`     | 1 decimal place    |
| FUNDS    | `closing_funds`       | Currency, no cents |
| PROFIT   | `cumulative_profit`   | Currency, no cents |
| BRAND    | `brand_score`         | 1 decimal place    |
| QUALITY  | `quality_avg`         | 1 decimal place    |
| PENALTY  | `inventory_penalty`   | Currency, no cents |

### Row Highlighting

- Own team row: left border `3px solid primary`, background `primary` at 8% opacity
- Rank 1: subtle `tertiary` accent on rank number

### State Variables (Zustand: `useResultsStore`)

```typescript
interface ResultsState {
  cycleNumber: number;
  isFinal: boolean;
  rows: LeaderboardRow[];
  isReadOnly: boolean;        // true during backroom

  // Actions
  fetchLeaderboard: () => Promise<void>;
}

interface LeaderboardRow {
  rank: number;
  team_name: string;
  composite_score: number;
  closing_funds: number;
  cumulative_profit: number;
  brand_score: number;
  quality_avg: number;
  inventory_penalty: number;
}
```

### API Interactions

| Action         | Method | Endpoint               | Notes                                   |
|----------------|--------|------------------------|-----------------------------------------|
| Load results   | `GET`  | `/team/leaderboard`    | Only available during `backroom` or `game_over` |

### What NOT to Include

- ❌ Graphs or trend lines
- ❌ Historical round comparisons
- ❌ Per-team detail breakdowns
- ❌ Any extra analytics

---

## 8. State Management (Zustand)

### Store Architecture

```
stores/
├── useGameStore.ts          Global game state (phase, auth, polling)
├── useProcurementStore.ts   Page 1 state
├── useProductionStore.ts    Page 2 state
├── useInventoryStore.ts     Page 3 state
└── useResultsStore.ts       Page 4 state
```

### `useGameStore` — Global Game State

```typescript
interface GameState {
  // Auth
  teamId: number | null;
  teamName: string;
  pin: string;
  isLoggedIn: boolean;

  // Game phase (polled every 5–10 seconds)
  gameName: string;
  cycleNumber: number;
  phase: string;          // "procurement_open" | "production_open" | "sales_open" | "backroom" | "game_over"
  gameActive: boolean;

  // Actions
  login: (teamId: number, pin: string) => Promise<void>;
  logout: () => void;
  pollStatus: () => Promise<void>;
}
```

### Phase → Page Mapping

| Phase                | Active Page           | Inputs Enabled         |
|----------------------|-----------------------|------------------------|
| `procurement_open`   | Procurement           | Procurement inputs     |
| `production_open`    | Production            | Production inputs      |
| `sales_open`         | Inventory (for scrap) | Scrap button only      |
| `backroom`           | Results               | None (read-only)       |
| `game_over`          | Results               | None (read-only)       |

### Rules

1. **Each page manages its own local state.** Cross-page data (funds, phase) comes from `useGameStore`.
2. **Submission only on "SEND DECISIONS"** — clicking the button triggers the PATCH API call.
3. **Default values** — on page mount, fetch the last-submitted decisions from backend and hydrate local state.
4. **Inputs disabled** when backend phase doesn't match the page's expected phase.
5. **Phase polling** — `useGameStore.pollStatus()` runs on a 5–10 second interval. When phase changes, the UI updates which page is active and which inputs are enabled.

### Auth Headers

All authenticated requests include:
```
X-Team-Id: {teamId}
X-Team-Pin: {pin}
```

---

## 9. API Reference

### Authentication

| Endpoint           | Method | Auth     | Response                  |
|--------------------|--------|----------|---------------------------|
| `/team/login`      | POST   | Headers  | `{ team_id, team_name }`  |
| `/team/status`     | GET    | None     | `{ game_name, cycle_number, phase, game_active }` |
| `/team/me`         | GET    | Headers  | `InventoryOut` object     |

### Procurement

| Endpoint              | Method | Auth    | Request Body                    | Response          | Phase Required        |
|------------------------|--------|---------|----------------------------------|-------------------|-----------------------|
| `/team/procurement`    | GET    | Headers | —                                | `ProcurementMemoryOut` | Any                |
| `/team/procurement`    | PATCH  | Headers | `{ decisions: { [comp]: { source_id, quantity, transport } } }` | `OkResponse` | `procurement_open` |

### Production

| Endpoint              | Method | Auth    | Request Body                    | Response          | Phase Required        |
|------------------------|--------|---------|----------------------------------|-------------------|-----------------------|
| `/team/production`     | GET    | Headers | —                                | `ProductionMemoryOut` | Any               |
| `/team/production`     | PATCH  | Headers | `{ component_decisions, wage_level, target_headcount, upgrade_automation }` | `OkResponse` | `production_open` |

### Sales / Inventory Actions

| Endpoint              | Method | Auth    | Request Body                    | Response          | Phase Required        |
|------------------------|--------|---------|----------------------------------|-------------------|-----------------------|
| `/team/sales`          | GET    | Headers | —                                | `SalesMemoryOut`  | Any                   |
| `/team/sales`          | PATCH  | Headers | `{ decisions: { reject: { action: "scrap" } } }` | `OkResponse` | `sales_open`    |

### Leaderboard

| Endpoint              | Method | Auth    | Response          | Phase Required               |
|------------------------|--------|---------|-------------------|------------------------------|
| `/team/leaderboard`    | GET    | None    | `LeaderboardOut`  | `backroom` or `game_over`    |

---

## 10. UI Constraints — What NOT to Build

### Global

- ❌ No dashboards (unless already in Stitch)
- ❌ No charts, graphs, trend lines, sparklines
- ❌ No maps (the old frontend had a MaterialMap — do NOT carry forward)
- ❌ No animations or transitions beyond basic hover states
- ❌ No rounded corners (0px border-radius everywhere)
- ❌ No `1px solid` borders for section separation — use background color shifts
- ❌ No pure white (`#FFFFFF`) text — use `on-surface` (`#e1e2e7`) or `on-surface-variant` (`#cec2d5`)

### Per Page

| Page          | Explicitly Excluded                                                        |
|---------------|----------------------------------------------------------------------------|
| Procurement   | No map component, no geo-visualization, no supplier comparison charts      |
| Production    | No machine tiers, no upgrade systems, no machine condition displays, no overhaul option |
| Inventory     | No stock editing, no analytics, no historical data, no charts              |
| Results       | No per-team drilldowns, no trend graphs, no round history comparison       |

### Data Model

- There are exactly **6 components** — never add or remove
- Each component has **multiple suppliers** (loaded dynamically from backend JSON seed)
- **No restriction on procurement quantity** (up to 10,000 per component)
- **Overspending is allowed** — warn but don't block
- If something is not present in Stitch design or backend schema — **do NOT add it**

---

> **End of specification. Follow this document exactly. Do not deviate.**
