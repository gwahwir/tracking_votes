"""SQLAlchemy ORM models for Johor Election Monitor database."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Article(Base):
    """News article record from scraping."""

    __tablename__ = "articles"

    id = Column(String(36), primary_key=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    source = Column(String(128), nullable=False, index=True)  # e.g. "thestar", "malaysiakini"
    content = Column(Text, nullable=True)
    scraped_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Tagging and scoring
    constituency_ids = Column(JSON, nullable=True)  # List of "P.157", "N.01", etc.
    reliability_score = Column(Float, nullable=True)  # 0-100, set by scorer_agent
    source_authority = Column(Float, nullable=True)
    accuracy_signals = Column(Float, nullable=True)
    bias_indicators = Column(Float, nullable=True)
    score_rationale = Column(Text, nullable=True)
    score_flags = Column(JSON, nullable=True)  # List of flag strings

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Analysis(Base):
    """Multi-perspective analysis result for an article."""

    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True)
    article_id = Column(String(36), nullable=False, index=True)  # Foreign key to Article
    lens_name = Column(String(64), nullable=False)  # "political", "demographic", "historical", "strategic", "factcheck", "bridget_welsh"

    # Analysis output
    direction = Column(String(64), nullable=True)  # Leading party / signal direction ("DAP", "BN", "PN", etc.)
    strength = Column(Float, nullable=True)  # 0-100 signal strength
    summary = Column(Text, nullable=True)  # Narrative summary from LLM
    full_result = Column(JSON, nullable=True)  # Full LLM output as JSON

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SeatPrediction(Base):
    """Win-likelihood prediction for a constituency."""

    __tablename__ = "seat_predictions"

    id = Column(String(36), primary_key=True)
    constituency_code = Column(String(16), nullable=False, index=True)  # "P.157", "N.01", etc.

    # Prediction result
    leading_party = Column(String(64), nullable=True)  # "DAP", "BN", "PN", etc.
    confidence = Column(Integer, nullable=True)  # 0-100

    # Signal breakdown (one entry per lens)
    signal_breakdown = Column(JSON, nullable=True)  # {
    #   "political": {"direction": "DAP", "strength": 80, "summary": "..."},
    #   "demographic": {"direction": "DAP", "strength": 70, "summary": "..."},
    #   ... (up to 6 lenses)
    # }

    # Caveats and metadata
    caveats = Column(JSON, nullable=True)  # ["Only 3 articles", "Candidate unannounced"]
    num_articles = Column(Integer, nullable=True)  # Count of articles used in this prediction

    # Metadata — server_default avoids asyncpg tz-mismatch when DB column is TIMESTAMP WITHOUT TIME ZONE
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HistoricalResult(Base):
    """Historical election result for a constituency."""

    __tablename__ = "historical_results"

    id = Column(String(36), primary_key=True)
    constituency_code = Column(String(16), nullable=False, index=True)  # "N.01", "P.140"
    seat_type = Column(String(16), nullable=False)  # "dun" or "parlimen"
    seat_name = Column(String(128), nullable=False)
    election_year = Column(Integer, nullable=False, index=True)
    state = Column(String(64), nullable=False, default="Johor")

    winner_name = Column(String(256), nullable=True)
    winner_party = Column(String(64), nullable=True)
    winner_coalition = Column(String(64), nullable=True)
    winner_votes = Column(Integer, nullable=True)

    margin = Column(Integer, nullable=True)
    margin_pct = Column(Float, nullable=True)
    turnout_pct = Column(Float, nullable=True)
    total_voters = Column(Integer, nullable=True)
    total_votes_cast = Column(Integer, nullable=True)
    num_candidates = Column(Integer, nullable=True)

    candidates = Column(JSON, nullable=True)  # [{name, party, coalition, votes}, ...]

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ConstituencyDemographics(Base):
    """Demographic profile for a constituency."""

    __tablename__ = "constituency_demographics"

    id = Column(String(36), primary_key=True)
    constituency_code = Column(String(16), nullable=False, unique=True, index=True)
    seat_name = Column(String(128), nullable=False)
    state = Column(String(64), nullable=False, default="Johor")

    malay_pct = Column(Float, nullable=True)
    chinese_pct = Column(Float, nullable=True)
    indian_pct = Column(Float, nullable=True)
    others_pct = Column(Float, nullable=True)
    urban_rural = Column(String(32), nullable=True)  # "urban", "semi-urban", "rural"
    region = Column(String(32), nullable=True)       # "north", "central", "south"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class RegisteredAgent(Base):
    """Agent registration record (for persistence + observability)."""

    __tablename__ = "registered_agents"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), nullable=False, unique=True)  # "news_agent", "scorer_agent", etc.
    type_id = Column(String(128), nullable=False, index=True)  # Agent type for routing
    url = Column(String(512), nullable=False)  # Current instance URL

    # Health status
    is_healthy = Column(Integer, default=1)  # 1 = healthy, 0 = unhealthy
    last_seen = Column(DateTime, nullable=True)  # Last successful health check

    # Metadata
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ============================================================================
# Database connection helpers
# ============================================================================


async def get_async_engine(database_url: str):
    """Create async SQLAlchemy engine for PostgreSQL."""
    # Convert postgresql:// to postgresql+asyncpg:// for async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,  # Verify connections before use
    )
    return engine


async def init_db(engine):
    """Create all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(engine) -> sessionmaker:
    """Get async session maker."""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
