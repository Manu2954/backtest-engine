"""
Robustness analysis database models.

Tracks parameter sensitivity, Monte Carlo, walk-forward, and other robustness tests.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class RobustnessAnalysis(Base):
    """
    Tracks robustness analyses performed on strategies.

    Supports multiple analysis types:
    - PARAMETER_SENSITIVITY: Vary indicator parameters, measure stability
    - MONTE_CARLO: Randomized entry/exit timing, measure confidence intervals
    - WALK_FORWARD: Rolling optimization windows, detect overfitting
    - FULL_ANALYSIS: Combined analysis with robustness score
    """
    __tablename__ = "robustness_analyses"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False
    )
    analysis_type = Column(String(50), nullable=False)  # PARAMETER_SENSITIVITY, etc.
    status = Column(String(20), nullable=False)  # PENDING, RUNNING, COMPLETE, FAILED
    params = Column(JSONB, nullable=False)  # Analysis configuration
    report = Column(JSONB, nullable=True)  # Results/report data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    strategy = relationship("Strategy", back_populates="robustness_analyses")
    variant_backtests = relationship(
        "RobustnessVariantBacktest",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )


class RobustnessVariantBacktest(Base):
    """
    Links individual backtest runs to robustness analyses.

    For parameter sensitivity: tracks each parameter variant tested.
    For Monte Carlo: tracks each simulation run.
    For walk-forward: tracks each window's train/test run.
    """
    __tablename__ = "robustness_variant_backtests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("robustness_analyses.id", ondelete="CASCADE"),
        nullable=False
    )
    backtest_run_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False
    )
    variant_label = Column(String(255), nullable=False)  # Human-readable description
    variant_params = Column(JSONB, nullable=False)  # Specific variant parameters

    # Relationships
    analysis = relationship("RobustnessAnalysis", back_populates="variant_backtests")
    backtest_run = relationship("BacktestRun")
