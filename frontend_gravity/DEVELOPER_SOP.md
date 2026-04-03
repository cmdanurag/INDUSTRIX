# Developer SOP & Architecture Guide: `frontend_gravity`

Welcome to the `frontend_gravity` documentation! This guide is designed to help fellow developers understand the structure, routing, state management, and Standard Operating Procedures (SOPs) for maintaining and extending this React application.

---

## 1. Overview & Tech Stack

This project is the frontend client for the **Industrix** game/prototype, built around simulation and resource management concepts. 

**Core Technologies:**
- **Framework:** React + Vite
- **Language:** TypeScript
- **Routing:** `react-router-dom`
- **Styling:** Tailwind CSS + custom CSS (`App.css`, `index.css`)
- **State Management:** Zustand
- **API Interfacing:** Custom fetch/Axios implementations mapped to an external backend

---

## 2. Directory Structure

Everything relevant to the active source code is contained within the `src/` directory.

```text
frontend_gravity/
├── src/
│   ├── api/            # API client configuration and network request handlers
│   ├── assets/         # Static visual assets (images, icons, etc.)
│   ├── components/     # Reusable UI components and Shared Layouts
│   ├── pages/          # Top-level Page components mapped directly to routes
│   ├── store/          # Zustand store definitions for global state management
│   ├── types/          # Global TypeScript interfaces and type definitions
│   ├── App.css         # Global application styling
│   ├── App.tsx         # Root component containing routing logic
│   ├── index.css       # Tailwind directives and base CSS
│   └── main.tsx        # Application entry point
├── tailwind.config.js  # Tailwind CSS configuration rules
├── vite.config.ts      # Vite bundler configuration
└── package.json        # Dependencies and scripts (npm run dev, etc.)
```

---

## 3. Routing & Pages Configuration

Routing is configured at the root level within `src/App.tsx`. We use standard `React-Router` nested routing, alongside a `SharedLayout` that presumably wraps the authenticated/dashboard views.

### Current Routes:
| Path | Component | Description |
| :--- | :--- | :--- |
| `/login` | `<Login />` | Authentication page. Outside the `SharedLayout` wrapper. |
| `/` | `<Procurement />` | Default landing page post-login. Handles resource purchasing logic. |
| `/market` | `<Production />` | Market/Production view where resources are converted/sold. |
| `/inventory` | `<Inventory />` | View for managing current stock, assets, and resources. |
| `/event` | `<Results />` | Displays round results, global events, and summary metrics. |

**Observation:** `SharedLayout` wraps all routes *except* `/login`. This means any global navigation bars, sidebars, or footer components intended for the main game interface are housed within `SharedLayout.tsx`.

---

## 4. State Management (Zustand)

Global state is managed via [Zustand](https://github.com/pmndrs/zustand). The state is logically separated into different domains inside `src/store/`:

- **`useGameStore.ts`**: Manages top-level game state (e.g., current round, game ID, player score/balance, active status).
- **`useProcurementStore.ts`**: State strictly related to the `/` Procurement route (e.g., resources available to buy, pending carts).
- **`useProductionStore.ts`**: State tied to the `/market` route (e.g., recipes, market demands, active production tasks).
- **`useInventoryStore.ts`**: Holds the current ledger of user inventories (what the player currently owns).
- **`useResultsStore.ts`**: State for recent event history, leaderboards, and immediate previous round results.
- **`index.ts`**: Often used as a barrel file to export all stores cleanly for easier importing.

---

## 5. API Integration Layer

The `src/api/` directory centralizes all backend communications:

- **`client.ts`**: Likely contains the base HTTP client configuration (e.g., base URL injection, attaching bearer tokens to headers, robust error interceptors).
- **`index.ts`**: Exports specific, named asynchronous functions (e.g., `loginUser()`, `fetchInventory()`, `submitTurn()`). 

*Tip: Pages and Components should NEVER make raw `fetch` calls directly. They should invoke the functions exported from `src/api/index.ts`.*

---

## 6. Standard Operating Procedures (SOP)

If you are a new developer making changes to this repository, please adhere to the following workflow patterns:

### A. Adding a New Page/Route
1. Create the new component in `src/pages/NewPage.tsx`.
2. Ensure the component utilizes a standard functional component structure.
3. Open `src/App.tsx`.
4. Import your `NewPage` component.
5. Add a `<Route path="/new-path" element={<NewPage />} />` inside the `<Routes>` block. If it requires global navigation, place it inside the `<Route element={<SharedLayout />}>` block.

### B. Adding/Modifying Global State
1. Do not use React `useState` if the data needs to be shared across completely decoupled or sibling pages.
2. Open the relevant file in `src/store/` (or create a new one, e.g., `useSettingsStore.ts`).
3. Define the Typescript interface for both the State and the Actions (functions that modify the state).
4. Update the Zustand `set` hook accordingly.
5. In your component, access state specifically to avoid unnecessary re-renders: `const data = useGameStore((state) => state.data);` 

### C. Integrating a New Backend Endpoint
1. Open `src/api/index.ts`.
2. Define any specific Request or Response TypeScript interfaces if they don't exist in `src/types/index.ts`.
3. Create an exported asynchronous function utilizing the base client (from `client.ts`).
4. Handle your error states cleanly (throw errors or return formatted error objects).
5. Only import and use this new `.api/` function inside your target Page or Store.

### D. Styling Conventions
- Rely heavily on **Tailwind CSS** utility classes directly in the `.tsx` files (`className="..."`).
- If you have highly customized animations or non-standard Tailwind behavior, place it in `src/index.css` via the `@layer components` or `@layer utilities` directives.
- Avoid creating standalone `.css` files unless absolutely necessary for complex, isolated components.

---

## 7. Running the Project Locally

To get started with local development:

```bash
# 1. Ensure you are in the correct directory
cd frontend_gravity

# 2. Install dependencies (ensure node_modules is populated)
npm install

# 3. Start the Vite development server
npm run dev
```

*For build testing before deployment, run `npm run build` to catch explicit TypeScript or Vite compilation errors.*
