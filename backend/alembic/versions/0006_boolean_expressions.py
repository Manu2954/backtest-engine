"""add boolean expression support to strategies

Revision ID: 0006_boolean_expressions
Revises: 0005_add_transaction_costs
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_boolean_expressions'
down_revision = '0005_add_transaction_costs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add expression columns to strategies table
    op.add_column('strategies', sa.Column('entry_expression', sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('exit_expression', sa.Text(), nullable=True))

    # Add group_name column to condition_groups table
    op.add_column('condition_groups', sa.Column('group_name', sa.String(length=64), nullable=True))


def downgrade() -> None:
    # Remove group_name from condition_groups
    op.drop_column('condition_groups', 'group_name')

    # Remove expression columns from strategies
    op.drop_column('strategies', 'exit_expression')
    op.drop_column('strategies', 'entry_expression')
