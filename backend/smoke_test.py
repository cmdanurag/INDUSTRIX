"""
scripts/smoke_test.py
=====================
Full end-to-end test of one complete cycle.
Creates a game with 3 teams, runs all phases, enters backroom,
starts a second cycle, then ends the game.

Run against a FRESH database (after reset_db.py).
Does NOT use the HTTP layer — calls services directly.
Prints PASS / FAIL for each step.

Usage:
    python -m scripts.smoke_test
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.database import Base, SessionLocal, engine
import models  # noqa

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def check(label: str, fn):
    try:
        result = fn()
        print(f"  {PASS}  {label}")
        return result
    except Exception as e:
        print(f"  {FAIL}  {label}")
        traceback.print_exc()
        sys.exit(1)


def run():
    print("\n=== Industrix smoke test ===\n")

    # Fresh schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    from services.cycle import (
        add_team, advance_phase, create_game, create_cycle,
        end_game, start_next_cycle,
    )
    from models.game import Game, Cycle, Team
    from models.procurement import (
        ComponentSlot, Inventory, MemoryProcurement,
    )
    from models.production import MemoryProduction
    from models.sales import MemorySales
    from models.game import RawMaterialSource
    from core.enums import ComponentType, CyclePhase

    # ── 1. Create game ────────────────────────────────────────────────────────
    game = check("Create game", lambda: create_game(
        db, name="Smoke Test Game",
        qr_hard=30, qr_soft=50, qr_premium=75,
        starting_funds=100_000,
    ))

    # ── 2. Create sources ─────────────────────────────────────────────────────
    def _create_sources():
        for comp in ComponentType:
            db.add(RawMaterialSource(
                game_id=game.id, component=comp,
                name=f"{comp.value} Supplier",
                quality_mean=65.0, quality_sigma=10.0,
                base_cost_per_unit=50.0,
                min_order=1, max_order=5000, is_active=True,
            ))
        db.commit()
        return True

    check("Create sources (one per component)", _create_sources)

    # ── 3. Add teams ──────────────────────────────────────────────────────────
    teams = []
    for i in range(1, 4):
        t = check(f"Add team {i}", lambda i=i: add_team(db, game, f"Team {i}", f"pin{i}"))
        teams.append(t)

    # ── 4. Verify seeded rows ─────────────────────────────────────────────────
    def _verify_seeding():
        for t in teams:
            assert db.query(Inventory).filter(Inventory.team_id == t.id).count() == 1
            assert db.query(ComponentSlot).filter(ComponentSlot.team_id == t.id).count() == 6
            assert db.query(MemoryProcurement).filter(MemoryProcurement.team_id == t.id).count() == 1
            assert db.query(MemoryProduction).filter(MemoryProduction.team_id == t.id).count() == 1
            assert db.query(MemorySales).filter(MemorySales.team_id == t.id).count() == 1
        return True

    check("All seed rows created per team", _verify_seeding)

    # ── 5. Create cycle 1 ─────────────────────────────────────────────────────
    cycle1 = check("Create cycle 1", lambda: create_cycle(db, game))

    def _verify_phase(expected):
        db.refresh(cycle1)
        phase = cycle1.phase_log.current_phase
        assert phase == expected, f"Expected {expected}, got {phase}"
        return phase

    check("Cycle 1 starts at PROCUREMENT_OPEN",
          lambda: _verify_phase(CyclePhase.PROCUREMENT_OPEN))

    # ── 6. Seed procurement decisions ─────────────────────────────────────────
    def _seed_proc_decisions():
        sources = db.query(RawMaterialSource).filter(
            RawMaterialSource.game_id == game.id
        ).all()
        source_map = {s.component.value: s.id for s in sources}

        for team in teams:
            mem = db.query(MemoryProcurement).filter(
                MemoryProcurement.team_id == team.id
            ).first()
            mem.decisions = {
                comp: {
                    "source_id": source_map[comp],
                    "quantity":  200,
                    "transport": "road",
                }
                for comp in ComponentType
            }
        db.commit()
        return True

    check("Seed procurement decisions for all teams", _seed_proc_decisions)

    # ── 7. Advance: PROCUREMENT_OPEN → PRODUCTION_OPEN ────────────────────────
    pl = check("Advance → PRODUCTION_OPEN (procurement resolves)",
               lambda: advance_phase(db, game))
    check("Phase is now PRODUCTION_OPEN",
          lambda: _verify_phase(CyclePhase.PRODUCTION_OPEN))

    # Verify raw_stock received
    def _verify_raw_stock():
        for team in teams:
            slots = db.query(ComponentSlot).filter(
                ComponentSlot.team_id == team.id
            ).all()
            for slot in slots:
                assert sum(slot.raw_stock[1:]) > 0, \
                    f"Team {team.id} slot {slot.component} has empty raw_stock"
        return True

    check("Raw stock populated after procurement", _verify_raw_stock)

    # ── 8. Advance: PRODUCTION_OPEN → SALES_OPEN ─────────────────────────────
    check("Advance → SALES_OPEN (production resolves)",
          lambda: advance_phase(db, game))
    check("Phase is now SALES_OPEN",
          lambda: _verify_phase(CyclePhase.SALES_OPEN))

    # Verify drones were produced
    def _verify_drones():
        for team in teams:
            inv = db.query(Inventory).filter(Inventory.team_id == team.id).first()
            total = sum(inv.drone_stock[1:]) if inv.drone_stock else 0
            assert total > 0, f"Team {team.id} produced 0 drones"
        return True

    check("Drones produced and in drone_stock", _verify_drones)

    # ── 9. Advance: SALES_OPEN → BACKROOM ────────────────────────────────────
    check("Advance → BACKROOM (sales resolves)",
          lambda: advance_phase(db, game))
    check("Phase is now BACKROOM",
          lambda: _verify_phase(CyclePhase.BACKROOM))

    # Verify funds changed (sales revenue applied)
    def _verify_funds_changed():
        for team in teams:
            inv = db.query(Inventory).filter(Inventory.team_id == team.id).first()
            # Funds will have changed from procurement cost and sales revenue
            assert inv.funds != 100_000.0, \
                f"Team {team.id} funds unchanged — sales/procurement not applied"
        return True

    check("Funds updated after full cycle", _verify_funds_changed)

    # ── 10. Start cycle 2 ─────────────────────────────────────────────────────
    cycle2 = check("Start cycle 2 (/next)", lambda: start_next_cycle(db, game))

    def _verify_cycle2():
        assert cycle2.cycle_number == 2
        db.refresh(cycle2)
        assert cycle2.phase_log.current_phase == CyclePhase.PROCUREMENT_OPEN
        return True

    check("Cycle 2 at PROCUREMENT_OPEN with cycle_number=2", _verify_cycle2)

    # ── 11. End game ──────────────────────────────────────────────────────────
    # First advance cycle 2 through all phases
    check("Advance cycle 2 → PRODUCTION_OPEN", lambda: advance_phase(db, game))
    check("Advance cycle 2 → SALES_OPEN",      lambda: advance_phase(db, game))
    check("Advance cycle 2 → BACKROOM",         lambda: advance_phase(db, game))

    check("End game", lambda: end_game(db, game))

    def _verify_game_over():
        db.refresh(game)
        assert game.is_active == False
        db.refresh(cycle2)
        assert cycle2.phase_log.current_phase == CyclePhase.GAME_OVER
        return True

    check("Game deactivated and phase is GAME_OVER", _verify_game_over)

    # ── 12. Leaderboard ───────────────────────────────────────────────────────
    from industrix.services.leaderboard import compute_leaderboard
    rows = check("Compute leaderboard", lambda: compute_leaderboard(db, game, cycle2, is_final=True))

    def _verify_leaderboard():
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        assert rows[0]["rank"] == 1
        return True

    check("Leaderboard has 3 rows, rank 1 at top", _verify_leaderboard)

    db.close()

    print(f"\n=== All checks passed ===\n")
    print("Winner:", rows[0]["team_name"],
          f"(score: {rows[0]['composite_score']})")


if __name__ == "__main__":
    run()
