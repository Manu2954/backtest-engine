"""add robustness analysis tables

Revision ID: 0008_robustness_analysis
Revises: 0007_trade_attribution
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0008_robustness_analysis'
down_revision = '0007_trade_attribution'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create robustness_analyses table
    op.create_table(
        'robustness_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('params', postgresql.JSONB, nullable=False),
        sa.Column('report', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
    )

    # Create indexes
    op.create_index('idx_robustness_strategy', 'robustness_analyses', ['strategy_id'])
    op.create_index('idx_robustness_type', 'robustness_analyses', ['analysis_type'])
    op.create_index('idx_robustness_status', 'robustness_analyses', ['status'])

    # Create robustness_variant_backtests table
    op.create_table(
        'robustness_variant_backtests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('robustness_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('backtest_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant_label', sa.String(255), nullable=False),
        sa.Column('variant_params', postgresql.JSONB, nullable=False),
    )

    # Create index
    op.create_index('idx_variant_analysis', 'robustness_variant_backtests', ['analysis_id'])


def downgrade() -> None:
    op.drop_table('robustness_variant_backtests')
    op.drop_table('robustness_analyses')
