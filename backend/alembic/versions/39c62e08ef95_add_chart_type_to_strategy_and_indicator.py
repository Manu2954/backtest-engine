"""add chart_type to strategy and indicator

Revision ID: 39c62e08ef95
Revises: d2c3147e5d7c
Create Date: 2026-06-26 03:21:34.005664

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39c62e08ef95'
down_revision = 'd2c3147e5d7c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add chart_type to strategies table (default 'ohlcv')
    op.add_column('strategies', sa.Column('chart_type', sa.String(32), nullable=False, server_default='ohlcv'))

    # Add chart_type to indicators table (nullable - inherits from strategy if None)
    op.add_column('indicators', sa.Column('chart_type', sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column('indicators', 'chart_type')
    op.drop_column('strategies', 'chart_type')
