"""
Load historical election results and demographics into PostgreSQL.

Reads:
  data/historical/johor_dun_results.json
  data/historical/johor_parlimen_results.json
  data/historical/johor_demographics.json

Usage:
    python scripts/ingest_historical.py

Requires:
    DATABASE_URL env var (or .env file at project root)
    PostgreSQL running with the schema already created (docker-compose up)
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not set. Check your .env file.")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

DATA_DIR = Path(__file__).parent.parent / "data" / "historical"


async def ingest(session: AsyncSession, data: dict, seat_type: str) -> tuple[int, int]:
    """
    Upsert all seat results from a JSON file into historical_results.
    Returns (inserted, skipped) counts.
    """
    from agents.base.models import HistoricalResult

    inserted = 0
    skipped = 0

    for code, seat in data["seats"].items():
        seat_name = seat["name"]
        for year_str, result in seat.get("results", {}).items():
            year = int(year_str)

            # Delete existing record for this constituency+year (upsert via delete+insert)
            await session.execute(
                delete(HistoricalResult).where(
                    HistoricalResult.constituency_code == code,
                    HistoricalResult.election_year == year,
                )
            )

            record = HistoricalResult(
                id=str(uuid.uuid4()),
                constituency_code=code,
                seat_type=seat_type,
                seat_name=seat_name,
                election_year=year,
                state="Johor",
                winner_name=result.get("winner_name"),
                winner_party=result.get("winner_party"),
                winner_coalition=result.get("winner_coalition"),
                winner_votes=result.get("winner_votes"),
                margin=result.get("margin"),
                margin_pct=result.get("margin_pct"),
                turnout_pct=result.get("turnout_pct"),
                total_voters=result.get("total_voters"),
                total_votes_cast=result.get("total_votes_cast"),
                num_candidates=result.get("num_candidates"),
                candidates=result.get("candidates"),
            )
            session.add(record)
            inserted += 1

        if not seat.get("results"):
            skipped += 1

    return inserted, skipped


async def ingest_demographics(session: AsyncSession, data: dict) -> int:
    """Upsert constituency demographics. Returns count inserted."""
    from agents.base.models import ConstituencyDemographics

    inserted = 0
    for code, seat in data["seats"].items():
        await session.execute(
            delete(ConstituencyDemographics).where(
                ConstituencyDemographics.constituency_code == code
            )
        )
        record = ConstituencyDemographics(
            id=str(uuid.uuid4()),
            constituency_code=code,
            seat_name=seat["name"],
            state=seat.get("state", "Johor"),
            malay_pct=seat.get("malay_pct"),
            chinese_pct=seat.get("chinese_pct"),
            indian_pct=seat.get("indian_pct"),
            others_pct=seat.get("others_pct"),
            urban_rural=seat.get("urban_rural"),
            region=seat.get("region"),
        )
        session.add(record)
        inserted += 1
    return inserted


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Ensure tables exist
    from agents.base.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Schema ready.")

    async with async_session() as session:
        async with session.begin():
            # DUN
            dun_path = DATA_DIR / "johor_dun_results.json"
            dun_data = json.loads(dun_path.read_text(encoding="utf-8"))
            dun_inserted, dun_skipped = await ingest(session, dun_data, "dun")
            print(f"DUN:      {dun_inserted} records inserted, {dun_skipped} seats skipped (no data)")

            # Parlimen
            par_path = DATA_DIR / "johor_parlimen_results.json"
            par_data = json.loads(par_path.read_text(encoding="utf-8"))
            par_inserted, par_skipped = await ingest(session, par_data, "parlimen")
            print(f"Parlimen: {par_inserted} records inserted, {par_skipped} seats skipped (no data)")

            # Demographics
            demo_path = DATA_DIR / "johor_demographics.json"
            demo_data = json.loads(demo_path.read_text(encoding="utf-8"))
            demo_inserted = await ingest_demographics(session, demo_data)
            print(f"Demo:     {demo_inserted} records inserted")

    # Quick verification query
    async with async_session() as session:
        result = await session.execute(
            text("SELECT seat_type, election_year, COUNT(*) FROM historical_results GROUP BY seat_type, election_year ORDER BY seat_type, election_year")
        )
        rows = result.fetchall()
        print("\n=== DB verification: historical_results ===")
        print(f"{'seat_type':<12} {'year':<8} {'count'}")
        for seat_type, year, count in rows:
            print(f"{seat_type:<12} {year:<8} {count}")

        result2 = await session.execute(
            text("SELECT seat_type, urban_rural, COUNT(*) FROM constituency_demographics JOIN historical_results USING (constituency_code) WHERE election_year = 2022 GROUP BY seat_type, urban_rural ORDER BY seat_type, urban_rural")
        )
        rows2 = result2.fetchall()
        print("\n=== DB verification: demographics ===")
        print(f"{'seat_type':<12} {'urban_rural':<14} {'count'}")
        for seat_type, urban_rural, count in rows2:
            print(f"{seat_type:<12} {urban_rural:<14} {count}")

    total = dun_inserted + par_inserted + demo_inserted
    print(f"\nTotal records loaded: {total}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
