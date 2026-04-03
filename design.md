# INDUSTRIX — Frontend System UI Specification

> **Source of truth**: Stitch project `INDUSTRIX`
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
9. [UI Constraints — What NOT to Build](#9-ui-constraints--what-not-to-build)

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

### Shape & Elevation

- **Border radius: `0px` on everything.** No rounded corners. This is the industrial aesthetic.
- No `1px solid` borders to separate regions — use background color shifts instead.
- Ghost borders: `outline-variant` at `15%` opacity only when needed for accessibility.
- No drop shadows on static elements. Use tonal layering (`surface` → `surface-low` → `surface-high`).

---

## 2. Global Layout

```text
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

### Top Navbar & Sidebar

- Sidebar Items: RAW MATERIALS, MARKETING, AUTOMATION LEVEL
- Navbar Items: HOME, MARKET, INVENTORY, EVENT, LOGOUT

### Component Tabs (Procurement & Production)

- 6 tabs: AIRFRAME, PROPULSION, AVIONICS, FIRE SUPPRESSION, SENSING & SAFETY, BATTERY

---

## 3. Shared Components

### `<SendDecisionsButton />`
- Label: **"SEND DECISIONS"**
- Style: solid gradient, `on-primary` text, 0px radius
- Disabled when backend phase does not match current page phase

### `<WarningBanner />`
- **Non-blocking** notifications below input areas (never prevents sending decisions)
- Shows warning levels (e.g. overspend warnings)

---

## 4. Page 1 — Raw Materials (Procurement)

**Active when:** `phase === "procurement_open"`

### Requirements & Fixes
- **Must use a "SEND DECISIONS" button**
- **Must include notification/warning area** (overspending + high spend) below inputs. Does not block submission.
- **Must allow multiple submissions** (submitting updates last decisions during open phase).
- **Default values must come from previous cycle** (fetch on mount).

### Input Controls
- Supplier dropdown (displays Q, σ, Cost)
- Quantity (number input)
- Transport mode (Toggle: ROAD, RAIL, AIR)

---

## 5. Page 2 — Production

**Active when:** `phase === "production_open"`

### Requirements & Fixes
- **Only include these controls:**
  - Maintenance (`NONE`, `BASIC`, `FULL`)
  - R&D investment (number input)
  - Wage level (Toggle: `LOW`, `MARKET`, `HIGH`)
  - Headcount (editable number input)
  - Automation (Toggle: `MANUAL`, `SEMI-AUTO`, `FULL-AUTO`)
- **NO machine tiers.**
- **NO upgrade components.**

---

## 6. Page 3 — Inventory

**Accessible during:** any phase

### Requirements & Fixes
- **Everything is strictly read-only EXCEPT:**
  - The **"SCRAP REJECT UNITS"** button.

### Display Sections
- Global Funds
- Brand Score
- Raw Materials Stock (table)
- Finished Drones (total, reject, substandard, standard, premium counts)

---

## 7. Page 4 — Results / Event

**Active when:** `phase === "backroom" || phase === "game_over"`

### Requirements & Fixes
- **Only include the leaderboard table.**
- **NO formulas, NO audit logs, NO graphs.**
- Own team row highlighted.

---

## 8. State Management (Zustand)

```
stores/
├── useGameStore.ts          (Global state)
├── useProcurementStore.ts   (Page 1 state)
├── useProductionStore.ts    (Page 2 state)
├── useInventoryStore.ts     (Page 3 state)
└── useResultsStore.ts       (Page 4 state)
```

**Rules:**
1. Cross-page data (funds, phase) comes from `useGameStore`.
2. Component-specific data resides in its own store.
3. Edits are strictly local. Submit ONLY via "SEND DECISIONS".

---

## 9. UI Constraints — What NOT to Build

- ❌ No dashboards, charts, analytics, sparklines, or graphs.
- ❌ No maps (do not carry material-map over).
- ❌ No rounded corners.
- ❌ No 1px solid borders for separation.
- ❌ No machine tiers or overhaul systems in Production.
- ❌ No stock editing in Inventory.
- ❌ No trend lines or detail panes in Results.
