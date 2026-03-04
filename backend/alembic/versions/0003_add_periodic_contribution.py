"""add periodic contribution to backtest_runs

Revision ID: 0003_add_periodic_contribution
Revises: 0002_add_ohlcv_bars
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0003_add_periodic_contribution"
down_revision = "0002_add_ohlcv_bars"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("periodic_contribution", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("backtest_runs", "periodic_contribution")
