"""add risk_free_rate to backtest_runs

Revision ID: 91b8ee5657c5
Revises: 0008_robustness_analysis
Create Date: 2026-04-15 17:09:47.916041

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91b8ee5657c5'
down_revision = '0008_robustness_analysis'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'backtest_runs',
        sa.Column('risk_free_rate', sa.Numeric(8, 4), nullable=True, server_default='0.0')
    )


def downgrade() -> None:
    op.drop_column('backtest_runs', 'risk_free_rate')
