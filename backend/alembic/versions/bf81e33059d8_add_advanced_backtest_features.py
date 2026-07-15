"""add advanced backtest features

Revision ID: bf81e33059d8
Revises: 39c62e08ef95
Create Date: 2026-07-06 09:28:45.538516

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'bf81e33059d8'
down_revision = '39c62e08ef95'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('backtest_runs', sa.Column('leverage', sa.Numeric(8, 2), nullable=True, server_default='1.0'))
    op.add_column('backtest_runs', sa.Column('dynamic_stop_column', sa.String(64), nullable=True))
    op.add_column('backtest_runs', sa.Column('dynamic_tp_pct_column', sa.String(64), nullable=True))
    op.add_column('backtest_runs', sa.Column('enable_counter_trades', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('backtest_runs', sa.Column('counter_tp_multiplier', sa.Numeric(8, 4), nullable=True, server_default='1.5'))
    op.add_column('backtest_runs', sa.Column('exit_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('backtest_runs', 'exit_rules')
    op.drop_column('backtest_runs', 'counter_tp_multiplier')
    op.drop_column('backtest_runs', 'enable_counter_trades')
    op.drop_column('backtest_runs', 'dynamic_tp_pct_column')
    op.drop_column('backtest_runs', 'dynamic_stop_column')
    op.drop_column('backtest_runs', 'leverage')
