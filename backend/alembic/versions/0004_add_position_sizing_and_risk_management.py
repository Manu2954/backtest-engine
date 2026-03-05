"""add position sizing and risk management

Revision ID: 0004_add_position_sizing_and_risk_management
Revises: 0003_add_periodic_contribution
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_add_position_sizing_and_risk_management"
down_revision = "0003_add_periodic_contribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add position sizing columns to backtest_runs
    op.add_column(
        "backtest_runs",
        sa.Column("position_size_type", sa.String(32), nullable=True, server_default="full_capital"),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("position_size_value", sa.Numeric(18, 2), nullable=True, server_default="100.0"),
    )

    # Add risk management columns to backtest_runs
    op.add_column(
        "backtest_runs",
        sa.Column("stop_loss_pct", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("take_profit_pct", sa.Numeric(8, 4), nullable=True),
    )

    # Add exit_reason column to trade_logs
    op.add_column(
        "trade_logs",
        sa.Column("exit_reason", sa.String(32), nullable=True, server_default="signal"),
    )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column("trade_logs", "exit_reason")
    op.drop_column("backtest_runs", "take_profit_pct")
    op.drop_column("backtest_runs", "stop_loss_pct")
    op.drop_column("backtest_runs", "position_size_value")
    op.drop_column("backtest_runs", "position_size_type")
