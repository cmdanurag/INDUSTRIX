"""
core/auth.py
============
Authentication dependencies for FastAPI endpoints.

Team auth  : x-team-id + x-team-pin headers.
             Server hashes the PIN and compares against stored hash.

Organiser  : x-organiser-secret header compared against
             the game's organiser_secret field.

Usage:
    @router.get("/something")
    def endpoint(team: Team = Depends(verify_team), db = Depends(get_db)):
        ...

    @router.post("/advance")
    def advance(game: Game = Depends(verify_organiser), db = Depends(get_db)):
        ...
"""
import hashlib
import os

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.config import ADMIN_CODE

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_team(
    x_team_id:  int = Header(..., description="Team numeric ID"),
    x_team_pin: str = Header(..., description="Raw PIN — server hashes it"),
    db: Session = Depends(get_db),
):
    """
    Returns the authenticated Team ORM object.
    Raises 401 on unknown ID or wrong PIN.
    Raises 403 if the team is inactive (bankrupt / disqualified).
    """
    # Import here to avoid circular import (models import Base from database)
    from models.game import Team

    team = db.query(Team).filter(Team.id == x_team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid credentials.")
    if _hash_pin(x_team_pin) != team.pin_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid credentials.")
    if not team.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Team is not active.")
    return team


def verify_organiser(
    x_organiser_secret: str = Header(..., description="Organiser master secret"),
    db: Session = Depends(get_db),
):
    """
    Returns the active Game object if the secret matches.
    There is only ever one active game at a time.
    """
    from models.game import Game

    game = db.query(Game).filter(Game.is_active == True).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No active game found.")
    if x_organiser_secret != ADMIN_CODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid organiser secret.")
    return game