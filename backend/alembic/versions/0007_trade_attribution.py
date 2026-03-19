"""add trade attribution fields

Revision ID: 0007_trade_attribution
Revises: 6151cbef3598
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0007_trade_attribution'
down_revision = '6151cbef3598'
branch_labels = None
depends_on = None


def upgrade():
    # Add enable_attribution to backtest_runs
    op.add_column('backtest_runs', sa.Column('enable_attribution', sa.Boolean(), nullable=False, server_default='true'))

    # Add attribution fields to trade_logs
    op.add_column('trade_logs', sa.Column('entry_conditions_met', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('trade_logs', sa.Column('exit_conditions_met', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('trade_logs', sa.Column('entry_signal_strength', sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column('trade_logs', sa.Column('market_return_during_trade', sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column('trade_logs', sa.Column('alpha', sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column('trade_logs', sa.Column('indicator_snapshot_entry', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('trade_logs', sa.Column('indicator_snapshot_exit', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove attribution fields from trade_logs
    op.drop_column('trade_logs', 'indicator_snapshot_exit')
    op.drop_column('trade_logs', 'indicator_snapshot_entry')
    op.drop_column('trade_logs', 'alpha')
    op.drop_column('trade_logs', 'market_return_during_trade')
    op.drop_column('trade_logs', 'entry_signal_strength')
    op.drop_column('trade_logs', 'exit_conditions_met')
    op.drop_column('trade_logs', 'entry_conditions_met')

    # Remove enable_attribution from backtest_runs
    op.drop_column('backtest_runs', 'enable_attribution')
