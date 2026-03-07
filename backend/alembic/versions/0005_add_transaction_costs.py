"""add transaction costs

Revision ID: 0005_add_transaction_costs
Revises: 0004_add_position_sizing_and_risk_management
Create Date: 2026-03-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_add_transaction_costs"
down_revision = "0004_add_position_sizing_and_risk_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add transaction cost columns to backtest_runs
    op.add_column(
        "backtest_runs",
        sa.Column("commission_per_trade", sa.Numeric(18, 2), nullable=True, server_default="0.0"),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("commission_pct", sa.Numeric(8, 4), nullable=True, server_default="0.0"),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("slippage_pct", sa.Numeric(8, 4), nullable=True, server_default="0.0"),
    )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column("backtest_runs", "slippage_pct")
    op.drop_column("backtest_runs", "commission_pct")
    op.drop_column("backtest_runs", "commission_per_trade")
