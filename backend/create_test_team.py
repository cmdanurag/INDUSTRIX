import sys, hashlib
from core.database import SessionLocal, engine, Base
from models.game import Game, Team

Base.metadata.create_all(bind=engine)
db = SessionLocal()

game = db.query(Game).filter(Game.is_active == True).first()
if not game:
    game = Game(name="Test Game", is_active=True, qr_hard=30, qr_soft=50, qr_premium=75, market_demand_multiplier=1.0, starting_funds=100000.0)
    db.add(game)
    db.commit()

team = db.query(Team).filter(Team.name == "Alpha").first()
if not team:
    from services.cycle import add_team
    team = add_team(db, game, "Alpha", "123456")

print("TEAM ID:", team.id)
print("PIN:", "123456")
