"""
scripts/seed_game.py
====================
Create the game and seed all sources from seed_data/market.json
and seed_data/sources.json.

Run AFTER reset_db.py and BEFORE seed_teams.py.

Usage:
    python -m scripts.seed_game
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from core.database import SessionLocal
from models.game import Game, RawMaterialSource
from services.cycle import create_game

SEED_DIR = os.path.join(os.path.dirname(__file__), "seed_data")


def load_json(filename: str) -> dict:
    path = os.path.join(SEED_DIR, filename)
    with open(path) as f:
        return json.load(f)


def seed():
    db = SessionLocal()
    try:
        market  = load_json("market.json")
        sources = load_json("sources.json")

        # Create game
        game = create_game(
            db                       = db,
            name                     = market["game_name"],
            qr_hard                  = market["qr_hard"],
            qr_soft                  = market["qr_soft"],
            qr_premium               = market["qr_premium"],
            market_demand_multiplier = market.get("market_demand_multiplier", 1.0),
            starting_funds           = market.get("starting_funds", 100_000.0),
        )
        print(f"Game created: id={game.id}")
        print("  (Store this secret — you need it for all admin requests)")

        # Create sources
        for src in sources:
            source = RawMaterialSource(
                game_id            = game.id,
                component          = src["component"],
                name               = src["name"],
                quality_mean       = src["quality_mean"],
                quality_sigma      = src["quality_sigma"],
                base_cost_per_unit = src["base_cost_per_unit"],
                distance        = src.get("distance", 500.0),
                min_order          = src.get("min_order", 1),
                max_order          = src.get("max_order", 10_000),
                is_active          = True,
            )
            db.add(source)

        db.commit()
        print(f"  {len(sources)} sources created.")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()