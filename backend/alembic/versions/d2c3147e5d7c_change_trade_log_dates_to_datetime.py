"""change trade log dates to datetime

Revision ID: d2c3147e5d7c
Revises: 0359606ba02e
Create Date: 2026-06-22 21:04:05.389735

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2c3147e5d7c'
down_revision = '0359606ba02e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change entry_date and exit_date from Date to DateTime
    op.alter_column('trade_logs', 'entry_date',
                    type_=sa.DateTime(),
                    existing_type=sa.Date(),
                    existing_nullable=False)
    op.alter_column('trade_logs', 'exit_date',
                    type_=sa.DateTime(),
                    existing_type=sa.Date(),
                    existing_nullable=False)


def downgrade() -> None:
    # Revert to Date type (will lose time component)
    op.alter_column('trade_logs', 'entry_date',
                    type_=sa.Date(),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)
    op.alter_column('trade_logs', 'exit_date',
                    type_=sa.Date(),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)
