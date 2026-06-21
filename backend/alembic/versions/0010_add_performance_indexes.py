"""add performance indexes and fix missing provider column

Revision ID: 0010_perf_indexes
Revises: 0009_add_fetched_at
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0010_perf_indexes'
down_revision = '0009_add_fetched_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix: add provider column that was missing from migration 6151cbef3598
    op.add_column(
        'backtest_runs',
        sa.Column('provider', sa.String(16), nullable=True)
    )

    # Indexes for backtest_runs table
    op.create_index('ix_backtest_runs_strategy_id', 'backtest_runs', ['strategy_id'])
    op.create_index('ix_backtest_runs_status', 'backtest_runs', ['status'])
    op.create_index(
        'ix_backtest_runs_strategy_created',
        'backtest_runs',
        ['strategy_id', 'created_at'],
        postgresql_using='btree',
        postgresql_ops={'created_at': 'DESC'}
    )

    # Index for trade_logs table
    op.create_index('ix_trade_logs_run_id', 'trade_logs', ['run_id'])

    # Indexes for indicators table
    op.create_index('ix_indicators_strategy_id', 'indicators', ['strategy_id'])

    # Indexes for condition_groups table
    op.create_index('ix_condition_groups_strategy_id', 'condition_groups', ['strategy_id'])

    # Indexes for conditions table
    op.create_index('ix_conditions_group_id', 'conditions', ['group_id'])


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('ix_conditions_group_id', table_name='conditions')
    op.drop_index('ix_condition_groups_strategy_id', table_name='condition_groups')
    op.drop_index('ix_indicators_strategy_id', table_name='indicators')
    op.drop_index('ix_trade_logs_run_id', table_name='trade_logs')
    op.drop_index('ix_backtest_runs_strategy_created', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_status', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_strategy_id', table_name='backtest_runs')

    # Remove provider column
    op.drop_column('backtest_runs', 'provider')
