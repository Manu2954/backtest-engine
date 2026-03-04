"""add ohlcv bars

Revision ID: 0002_add_ohlcv_bars
Revises: 0001_init
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0002_add_ohlcv_bars"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ohlcv_bars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("asset_class", sa.String(length=16), nullable=False),
        sa.Column("resolution", sa.String(length=8), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=False), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 6), nullable=False),
        sa.UniqueConstraint("ticker", "asset_class", "resolution", "ts"),
    )
    op.create_index(
        "ix_ohlcv_bars_lookup",
        "ohlcv_bars",
        ["ticker", "asset_class", "resolution", "ts"],
    )


def downgrade() -> None:
    op.drop_index("ix_ohlcv_bars_lookup", table_name="ohlcv_bars")
    op.drop_table("ohlcv_bars")
