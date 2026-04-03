"""
services/leaderboard.py
=======================
compute_leaderboard(db, game, cycle, is_final)
    Compute composite scores for all active teams.
    Returns a sorted list of LeaderboardRow dicts.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from core.config import LEADERBOARD_NORMALISE, LEADERBOARD_WEIGHTS
from models.game import Team
from models.procurement import Inventory


def compute_leaderboard(
    db: Session, game, cycle, is_final: bool = False
) -> List[Dict]:
    teams: List[Team] = (
        db.query(Team)
        .filter(Team.game_id == game.id, Team.is_active == True)
        .all()
    )

    rows = []
    for team in teams:
        inv: Inventory = (
            db.query(Inventory).filter(Inventory.team_id == team.id).first()
        )
        if inv is None:
            continue

        drone_stock       = inv.drone_stock or [0] * 101
        inventory_penalty = float(sum(drone_stock[1:]))

        # Quality weighted average from drone_stock
        total_units = sum(drone_stock[1:])
        if total_units > 0:
            quality_avg = sum(g * drone_stock[g] for g in range(1, 101)) / total_units
        else:
            quality_avg = 0.0

        raw = {
            "closing_funds":     inv.funds,
            "cumulative_profit": inv.cumulative_profit,
            "brand_score":       inv.brand_score,
            "quality_avg":       quality_avg,
            "inventory_penalty": inventory_penalty,
        }

        norm = {
            k: v / LEADERBOARD_NORMALISE.get(k, 1.0)
            for k, v in raw.items()
        }

        composite = sum(
            norm[k] * w for k, w in LEADERBOARD_WEIGHTS.items()
        )
        composite = max(-1.0, composite)

        rows.append({
            "team_id":          team.id,
            "team_name":        team.name,
            "composite_score":  round(composite, 4),
            **{k: round(v, 2) for k, v in raw.items()},
        })

    rows.sort(key=lambda r: r["composite_score"], reverse=True)

    prev_score = None
    prev_rank  = 0
    for i, row in enumerate(rows, start=1):
        if row["composite_score"] != prev_score:
            prev_rank  = i
            prev_score = row["composite_score"]
        row["rank"] = prev_rank

    return rows