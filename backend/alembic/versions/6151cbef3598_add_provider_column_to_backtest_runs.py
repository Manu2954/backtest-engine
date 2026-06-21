"""add provider column to backtest_runs

Revision ID: 6151cbef3598
Revises: 0006_boolean_expressions
Create Date: 2026-03-15 03:34:40.111786

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6151cbef3598'
down_revision = '0006_boolean_expr'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'backtest_runs',
        sa.Column('provider', sa.String(16), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('backtest_runs', 'provider')
