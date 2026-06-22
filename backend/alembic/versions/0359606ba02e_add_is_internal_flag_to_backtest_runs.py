"""add is_internal flag to backtest_runs

Revision ID: 0359606ba02e
Revises: 0010_perf_indexes
Create Date: 2026-06-22 12:01:29.004886

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0359606ba02e'
down_revision = '0010_perf_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_internal column with default False
    op.add_column(
        'backtest_runs',
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('backtest_runs', 'is_internal')
