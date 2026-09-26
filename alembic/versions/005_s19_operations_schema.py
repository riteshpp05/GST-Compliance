"""Sprint 19 Enterprise Operations, Observability & Performance Schema

Revision ID: 005_s19_operations_schema
Revises: 004_s18_investigation_intelligence
Create Date: 2026-09-14 15:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_s19_operations_schema'
down_revision: Union[str, None] = '004_s18_investigation_intelligence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. operations_alerts
    op.create_table(
        'operations_alerts',
        sa.Column('alert_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), server_default='tenant_default', nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('action_required', sa.Text(), server_default='', nullable=False),
        sa.Column('acknowledged', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('alert_id')
    )
    op.create_index('idx_op_alerts_tenant_id', 'operations_alerts', ['tenant_id'])
    op.create_index('idx_op_alerts_category', 'operations_alerts', ['category'])
    op.create_index('idx_op_alerts_severity', 'operations_alerts', ['severity'])

    # 2. performance_benchmarks
    op.create_table(
        'performance_benchmarks',
        sa.Column('benchmark_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.Column('overall_status', sa.String(length=32), nullable=False),
        sa.Column('scenarios_json', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('benchmark_id')
    )
    op.create_index('idx_perf_benchmarks_timestamp', 'performance_benchmarks', ['timestamp'])

    # 3. application_metrics
    op.create_table(
        'application_metrics',
        sa.Column('metric_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), server_default='tenant_default', nullable=False),
        sa.Column('metric_type', sa.String(length=64), nullable=False),
        sa.Column('metric_data_json', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('metric_id')
    )
    op.create_index('idx_app_metrics_tenant_id', 'application_metrics', ['tenant_id'])
    op.create_index('idx_app_metrics_timestamp', 'application_metrics', ['timestamp'])


def downgrade() -> None:
    op.drop_table('application_metrics')
    op.drop_table('performance_benchmarks')
    op.drop_table('operations_alerts')
