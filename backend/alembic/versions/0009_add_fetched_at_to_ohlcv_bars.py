"""add fetched_at to ohlcv_bars for cache invalidation

Revision ID: 0009_add_fetched_at
Revises: 55da40c56956
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009_add_fetched_at'
down_revision = '55da40c56956'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add fetched_at column with server default for existing rows
    op.add_column(
        'ohlcv_bars',
        sa.Column(
            'fetched_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.func.now()
        )
    )


def downgrade() -> None:
    op.drop_column('ohlcv_bars', 'fetched_at')
