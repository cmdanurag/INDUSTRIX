# scripts/reset_and_seed.py

from core.database import Base, engine, SessionLocal
from models import procurement  # import only what exists so far

def reset():
    confirm = input("Type RESET to wipe database: ")
    if confirm != "RESET":
        print("Aborted.")
        return

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Seeding...")
    seed()
    print("Done.")

def seed():
    db = SessionLocal()
    try:
        # Create a game
        game = procurement.Game(
            name                     = "Test Game",
            qr_hard                  = 30.0,
            qr_soft                  = 50.0,
            qr_premium               = 75.0,
            market_demand_multiplier = 1.0,
            total_cycles             = 6,
        )
        db.add(game)
        db.flush()

        # Create teams
        import hashlib
        for i in range(1, 4):
            team = procurement.Team(
                game_id  = game.id,
                name     = f"Team {i}",
                pin_hash = f"hash-{i}",
                is_active = True,
            )
            db.add(team)
            db.flush()
            t = db.query(procurement.Team).filter(procurement.Team.name == f"Team {i}").first()
            print(f"team id: {t.id}")
            print(f"team hash: {t.pin_hash}")

        # Create suppliers — one per component
        from core.enums import ComponentType, TransportMode
        components = list(ComponentType)
        for comp in components:
            source = procurement.RawMaterialSource(
                game_id          = game.id,
                component        = comp,
                name             = f"{comp.value.title()} Supplier A",
                quality_mean     = 65.0,
                quality_sigma    = 10.0,
                base_cost_per_unit = 50.0,
                is_available        = True,
            )
            db.add(source)

        db.commit()
        print(f"  Game id={game.id}")
        print(f"  Teams: 3")
        print(f"  Sources: {len(components)}")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    reset()