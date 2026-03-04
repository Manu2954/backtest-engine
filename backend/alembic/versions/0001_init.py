"""init tables

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.String(length=64), nullable=False),
        sa.Column("indicator_type", sa.String(length=64), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "condition_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_type", sa.String(length=16), nullable=False),
        sa.Column("logic", sa.String(length=8), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("left_operand_type", sa.String(length=16), nullable=False),
        sa.Column("left_operand_value", sa.String(length=128), nullable=False),
        sa.Column("operator", sa.String(length=32), nullable=False),
        sa.Column("right_operand_type", sa.String(length=16), nullable=False),
        sa.Column("right_operand_value", sa.String(length=128), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["group_id"], ["condition_groups.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("asset_class", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("bar_resolution", sa.String(length=8), nullable=False),
        sa.Column("initial_capital", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("report", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "trade_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("exit_date", sa.Date(), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("shares", sa.Numeric(18, 6), nullable=False),
        sa.Column("pnl", sa.Numeric(18, 6), nullable=False),
        sa.Column("pnl_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("trade_duration_days", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["backtest_runs.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("trade_logs")
    op.drop_table("backtest_runs")
    op.drop_table("conditions")
    op.drop_table("condition_groups")
    op.drop_table("indicators")
    op.drop_table("strategies")
    op.drop_table("users")
