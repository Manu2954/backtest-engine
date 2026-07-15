"""add market_type to backtest_runs

Revision ID: c1a2b3d4e5f6
Revises: bf81e33059d8
Create Date: 2026-07-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = 'bf81e33059d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('backtest_runs', sa.Column('market_type', sa.String(16), nullable=True, server_default='SPOT'))


def downgrade() -> None:
    op.drop_column('backtest_runs', 'market_type')
