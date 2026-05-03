"""add short selling support

Revision ID: 55da40c56956
Revises: 91b8ee5657c5
Create Date: 2026-05-03 15:34:59.693999

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '55da40c56956'
down_revision = '91b8ee5657c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategies', sa.Column('short_entry_expression', sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('short_exit_expression', sa.Text(), nullable=True))
    op.add_column('trade_logs', sa.Column('direction', sa.String(8), nullable=False, server_default='LONG'))


def downgrade() -> None:
    op.drop_column('trade_logs', 'direction')
    op.drop_column('strategies', 'short_exit_expression')
    op.drop_column('strategies', 'short_entry_expression')
