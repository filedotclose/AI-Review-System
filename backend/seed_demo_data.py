#!/usr/bin/env python3
import asyncio
import os
import sys
import argparse
from datetime import datetime

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.base import Base, engine, async_session
import app.models  # Register all models on Base.metadata
from app.db.seed_data import seed_database


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Seed ODIPKS Construction OS database with realistic civil infrastructure operations data."
    )
    parser.add_argument(
        "--force",
        "--reset",
        action="store_true",
        dest="force",
        help="Purge existing operational demo data and repopulate fresh realistic dataset.",
    )
    return parser.parse_args()


async def run_seed(force: bool = False):
    print("=" * 72)
    print("   ODIPKS CONSTRUCTION OS - DATABASE SEED & RESTORATION ENGINE")
    print("=" * 72)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Engine URL: {engine.url.render_as_string(hide_password=True)}")
    print(f"Force Mode: {'ENABLED (Purge & Reseed)' if force else 'DISABLED (Safe / Check only)'}")
    print("-" * 72)

    if force:
        print("* Dropping and recreating all database tables for clean state...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("[OK] Database tables recreated successfully.")
    else:
        print("* Ensuring all database tables exist in target database...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[OK] Database tables verified.")

    print("* Running seeding engine with realistic civil infrastructure data...")
    async with async_session() as session:
        stats = await seed_database(session, force=force)

    print("-" * 72)
    if stats.get("status") == "skipped":
        print("ℹ [SKIPPED] Database already populated with records.")
        print("  To wipe existing demo records and reseed with fresh data, run:")
        print("    python seed_demo_data.py --force")
        print("  Or on AWS EC2 (Docker):")
        print("    docker exec -it construction_os_backend python seed_demo_data.py --force")
    else:
        print("[SUCCESS] Database successfully populated with realistic ODIPKS Infra data!")
        print("\nSummary of Seeded Data:")
        for entity, count in stats.items():
            print(f"  * {entity.replace('_', ' ').title():<28}: {count}")

        print("\n" + "=" * 72)
        print("  PRE-CONFIGURED USER CREDENTIALS FOR TESTING & DEMONSTRATION")
        print("=" * 72)
        print(f"  {'Role':<18} | {'Email':<22} | {'Phone':<12} | {'PIN':<6} | {'Password'}")
        print("-" * 72)
        print(f"  {'OWNER':<18} | {'owner@odipks.com':<22} | {'9800000001':<12} | {'1234':<6} | {'password123'}")
        print(f"  {'FINANCE_HEAD':<18} | {'finance@odipks.com':<22} | {'9800000002':<12} | {'1234':<6} | {'password123'}")
        print(f"  {'PROJECT_MANAGER':<18} | {'engineer@odipks.com':<22} | {'9811122233':<12} | {'9999':<6} | {'password123'}")
        print(f"  {'SITE_ENGINEER':<18} | {'rajesh@odipks.com':<22} | {'9876543210':<12} | {'1234':<6} | {'password123'}")
        print(f"  {'SUPERVISOR':<18} | {'supervisor@odipks.com':<22} | {'9876543211':<12} | {'1234':<6} | {'password123'}")
        print(f"  {'SITE_ENGINEER (Kochi)':<18} | {'amit@odipks.com':<22} | {'9876543212':<12} | {'1234':<6} | {'password123'}")
        print("=" * 72)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_seed(force=args.force))
