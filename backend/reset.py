"""
scripts/reset_db.py
===================
Drop all tables and recreate them from scratch.
Run this before the event to start with a clean database.

Usage:
    python -m scripts.reset_db
"""
import sys
import os

from models.game import Game

sys.path.insert(0, os.path.dirname(__file__))

from core.database import Base, engine
import models  # noqa: F401 — triggers all model imports


def reset():
    confirm = input("Type RESET to wipe the entire database: ").strip()
    if confirm != "RESET":
        print("Aborted.")
        sys.exit(0)

    Base.metadata.reflect(bind=engine)
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Database is empty and ready.")


if __name__ == "__main__":
    reset()