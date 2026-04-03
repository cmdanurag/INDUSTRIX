"""
scripts/seed_teams.py
=====================
Add all teams from seed_data/teams.json to the active game.
Seeds Inventory, ComponentSlot × 6, and all three Memory tables.

Run AFTER seed_game.py.

Usage:
    python -m scripts.seed_teams
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from core.database import SessionLocal
from models.game import Game
from services.cycle import add_team

SEED_DIR = os.path.join(os.path.dirname(__file__), "seed_data")


def load_json(filename: str):
    with open(os.path.join(SEED_DIR, filename)) as f:
        return json.load(f)


def seed():
    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.is_active == True).first()
        if not game:
            print("No active game found. Run seed_game.py first.")
            sys.exit(1)

        teams_data = load_json("teams.json")

        for entry in teams_data:
            team = add_team(db, game, entry["name"], entry["pin"])
            print(f"  Team created: id={team.id}  name='{team.name}'")

        print(f"\n{len(teams_data)} teams seeded successfully.")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()
