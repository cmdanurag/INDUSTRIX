export type ComponentType =
  | "airframe"
  | "propulsion"
  | "avionics"
  | "fire_suppression"
  | "sensing_safety"
  | "battery";

export type TransportMode = "road" | "rail" | "air";
export type WageLevel = "below_market" | "market" | "above_market";
export type AutomationLevel = "manual" | "semi_auto" | "full_auto";
export type MaintenanceLevel = "none" | "basic" | "full";
export type RndFocus = "quality" | "consistency" | "yield";
export type SalesTier = "reject" | "substandard" | "standard" | "premium";
export type SalesAction =
  | "sell_market"
  | "sell_premium"
  | "sell_discounted"
  | "hold"
  | "scrap"
  | "black_market";

export type GamePhase =
  | "procurement_open"
  | "production_open"
  | "sales_open"
  | "backroom"
  | "game_over"
  | "waiting_for_first_cycle"
  | "no_active_game";

export const COMPONENTS: ComponentType[] = [
  "airframe",
  "propulsion",
  "avionics",
  "fire_suppression",
  "sensing_safety",
  "battery",
];

export const COMPONENT_LABELS: Record<ComponentType, string> = {
  airframe: "AIRFRAME",
  propulsion: "PROPULSION",
  avionics: "AVIONICS",
  fire_suppression: "FIRE SUPPRESSION",
  sensing_safety: "SENSING & SAFETY",
  battery: "BATTERY",
};
