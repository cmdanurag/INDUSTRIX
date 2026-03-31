import enum


# ── Procurement ───────────────────────────────────────────────────────────────

class ComponentType(str, enum.Enum):
    AIRFRAME         = "airframe"
    PROPULSION       = "propulsion"
    AVIONICS         = "avionics"
    FIRE_SUPPRESSION = "fire_suppression"
    SENSING_SAFETY   = "sensing_safety"
    BATTERY          = "battery"


class TransportMode(str, enum.Enum):
    AIR  = "air"
    RAIL = "rail"
    ROAD = "road"


class ShipmentEventType(str, enum.Enum):
    NONE      = "none"
    DAMAGED   = "damaged"
    LOST      = "lost"
    SABOTAGED = "sabotaged"


# ── Machines ──────────────────────────────────────────────────────────────────

class MachineTier(str, enum.Enum):
    BASIC      = "basic"
    STANDARD   = "standard"
    INDUSTRIAL = "industrial"
    PRECISION  = "precision"


class MachineStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    DEGRADED    = "degraded"
    DESTROYED   = "destroyed"


class MaintenanceLevel(str, enum.Enum):
    """
    NONE     -> normal degradation this cycle.
    BASIC    -> degradation rate halved this cycle.
    FULL     -> degradation stopped this cycle.
    OVERHAUL -> degradation stopped AND condition recovered up to the ratchet ceiling
                (lower of: condition at purchase / last overhaul).
    """
    NONE     = "none"
    BASIC    = "basic"
    FULL     = "full"
    OVERHAUL = "overhaul"


# ── Labour & Automation ────────────────────────────────────────────────────────

class AutomationLevel(str, enum.Enum):
    """Higher automation -> lower sigma, higher cost, lower labour headcount needed."""
    MANUAL    = "manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


class WageLevel(str, enum.Enum):
    BELOW_MARKET = "below_market"
    MARKET       = "market"
    ABOVE_MARKET = "above_market"


class LabourEventType(str, enum.Enum):
    NONE          = "none"
    RIOT          = "riot"
    MASS_TURNOVER = "mass_turnover"
    POACHED       = "poached"
    STRIKE        = "strike"


# ── R&D ───────────────────────────────────────────────────────────────────────

class RndFocusArea(str, enum.Enum):
    """Three R&D focus areas tracked independently per component."""
    QUALITY     = "quality"      # Raises effective machine output mean
    CONSISTENCY = "consistency"  # Reduces output sigma
    YIELD       = "yield"        # Reduces raw material consumed per output unit


# ── Government / Sabotage ─────────────────────────────────────────────────────

class SabotageTargetType(str, enum.Enum):
    MACHINE      = "machine"
    LABOUR_RIOT  = "labour_riot"
    LABOUR_POACH = "labour_poach"
    RND_THEFT    = "rnd_theft"


# ── Cycle phases ──────────────────────────────────────────────────────────────

class CyclePhase(str, enum.Enum):
    """
    Full cycle state machine.  All transitions are organiser-triggered — nothing
    advances automatically.  This lets the organiser extend any phase as needed.

    PHASE1_OPEN        Teams updating procurement / machine / labour decisions.
    PHASE1_CLOSED      Organiser has locked Phase 1 decisions; processing begins.
    PHASE1_PROCESSING  Server running production simulation (brief, server-side).
    PHASE1_DISPLAY     Results computed; teams viewing production report + vague signals.
                       Loan negotiation happens offline here.
    PHASE2_OPEN        Organiser has opened Phase 2; teams submitting sales decisions.
    PHASE2_CLOSED      Organiser has locked Phase 2 decisions; sales processing begins.
    PHASE2_PROCESSING  Server running sales + market simulation.
    COMPLETE           Cycle fully resolved; next cycle can be created.
    """
    PHASE1_OPEN       = "phase1_open"
    PHASE1_CLOSED     = "phase1_closed"
    PHASE1_PROCESSING = "phase1_processing"
    PHASE1_DISPLAY    = "phase1_display"
    PHASE2_OPEN       = "phase2_open"
    PHASE2_CLOSED     = "phase2_closed"
    PHASE2_PROCESSING = "phase2_processing"
    COMPLETE          = "complete"


# ── Sales ─────────────────────────────────────────────────────────────────────

class QualityTier(str, enum.Enum):
    """
    The four quality tiers defined by the three market thresholds.
    REJECT      < q_hard
    SUBSTANDARD  q_hard  <= grade < q_soft
    STANDARD     q_soft  <= grade < q_premium
    PREMIUM      grade   >= q_premium
    """
    REJECT      = "reject"
    SUBSTANDARD = "substandard"
    STANDARD    = "standard"
    PREMIUM     = "premium"


class SalesAction(str, enum.Enum):
    """
    What the team decides to do with units in a given quality tier.
    Not every action is valid for every tier (enforced in service layer).
    """
    SELL_MARKET      = "sell_market"       # Sell at market price for this tier
    SELL_PREMIUM     = "sell_premium"      # Sell above market (premium tier only) — boosts brand
    SELL_DISCOUNTED  = "sell_discounted"   # Sell below expected price — moves more volume
    HOLD             = "hold"              # Keep in inventory for next cycle
    SCRAP            = "scrap"             # Destroy; recover scrap value
    BLACK_MARKET     = "black_market"      # Illegal channel for rejects; risk of fine + brand hit


class BrandTier(str, enum.Enum):
    POOR      = "poor"
    FAIR      = "fair"
    GOOD      = "good"
    EXCELLENT = "excellent"


# ── Loans & financial transfers ───────────────────────────────────────────────

class LoanSource(str, enum.Enum):
    GOVERNMENT = "government"    # High interest; binding restrictions on borrower
    INTER_TEAM = "inter_team"    # Team-to-team; negotiated terms; organiser approves


class LoanStatus(str, enum.Enum):
    ACTIVE    = "active"
    REPAID    = "repaid"
    DEFAULTED = "defaulted"     # Team went bankrupt with outstanding gov loan


class TransferType(str, enum.Enum):
    """Type of organiser-executed asset transfer between teams."""
    MONEY       = "money"
    RND_LEVEL   = "rnd_level"
    RAW_MATERIAL = "raw_material"
    DRONE_STOCK  = "drone_stock"


# ── Backroom deals phase ───────────────────────────────────────────────────────

class EffectTarget(str, enum.Enum):
    """What a queued effect modifies."""
    SHIPMENT_DAMAGE_PROB    = "shipment_damage_prob"     # Force damage on a team's shipments
    SHIPMENT_LOSS_PROB      = "shipment_loss_prob"       # Force total loss on shipments
    SOURCE_COST_MULTIPLIER  = "source_cost_multiplier"   # Hike/slash a source's price
    SOURCE_QUALITY_DELTA    = "source_quality_delta"     # Degrade/improve source quality
    MACHINE_CONDITION_HIT   = "machine_condition_hit"    # Damage a machine at cycle start
    LABOUR_MORALE_DELTA     = "labour_morale_delta"      # Spike or crash morale
    LABOUR_SKILL_DELTA      = "labour_skill_delta"       # Steal or boost skill
    RND_LEVEL_DELTA         = "rnd_level_delta"          # Add or remove R&D levels
    FUNDS_DELTA             = "funds_delta"              # Direct money add/remove
    BRAND_DELTA             = "brand_delta"              # Add or remove brand score
    MARKET_DEMAND_DELTA     = "market_demand_delta"      # Spike or crash global demand
    QR_THRESHOLD_DELTA      = "qr_threshold_delta"       # Tighten or relax quality bars
    AUDIT_FORCE             = "audit_force"              # Force an audit on a team
    BLACK_MARKET_FINE_FORCE = "black_market_fine_force"  # Force discovery of BM activity
    INVENTORY_SEIZURE       = "inventory_seizure"        # Seize a fraction of drone stock
    CUSTOM                  = "custom"                   # Free-text organiser note only


class EffectScope(str, enum.Enum):
    """Whether an effect targets one team or all teams."""
    SINGLE = "single"   # Targets one specific team
    GLOBAL = "global"   # Affects all active teams


class FraudType(str, enum.Enum):
    """Types of fraudulent activity that can be discovered at cycle end."""
    BLACK_MARKET_SALES  = "black_market_sales"
    GOVT_DEAL_FRAUD     = "govt_deal_fraud"
    CARTEL_PRICING      = "cartel_pricing"


class DiscoveryOutcome(str, enum.Enum):
    """Outcome of a fraud discovery roll."""
    NOT_DISCOVERED   = "not_discovered"
    DISCOVERED_STD   = "discovered_std"        # Standard fine applied
    DISCOVERED_BOMBERICA = "discovered_bomberica"  # 🇺🇸🔥 easter egg


class GlobalEventType(str, enum.Enum):
    """Named global events the organiser can trigger."""
    WAR_DECLARED         = "war_declared"          # Procurement costs spike
    SUPPLY_CHAIN_CRISIS  = "supply_chain_crisis"   # Random sources become unavailable
    MARKET_BOOM          = "market_boom"            # Demand multiplier spikes
    MARKET_CRASH         = "market_crash"           # Demand multiplier crashes
    REGULATORY_CRACKDOWN = "regulatory_crackdown"  # QR thresholds tighten
    REGULATORY_RELAX     = "regulatory_relax"      # QR thresholds loosen
    TECH_BREAKTHROUGH    = "tech_breakthrough"     # All teams get a free R&D boost
    LABOUR_STRIKE_WAVE   = "labour_strike_wave"    # All teams take morale hit
    CUSTOM               = "custom"                 # Organiser writes their own flavour
