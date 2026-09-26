"""Sprint 18 Investigation Intelligence, Evidence & AI Evaluation Schema

Revision ID: 004_s18_investigation_intelligence
Revises: 003_s17_data_quality_schema
Create Date: 2026-09-14 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_s18_investigation_intelligence'
down_revision: Union[str, None] = '003_s17_data_quality_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Sprint 18 orchestration columns to existing investigation_plans table
    with op.batch_alter_table('investigation_plans') as batch_op:
        batch_op.add_column(sa.Column('subject_invoice_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=64), server_default='tenant_default', nullable=False))
        batch_op.add_column(sa.Column('priority', sa.String(length=16), server_default='P3', nullable=False))
        batch_op.add_column(sa.Column('budget_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('limit_reached_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('created_by', sa.String(length=128), server_default='SYSTEM', nullable=False))

    op.create_index('idx_investigation_plans_tenant_id', 'investigation_plans', ['tenant_id'])

    # 2. investigation_steps
    op.create_table(
        'investigation_steps',
        sa.Column('step_id', sa.String(length=64), nullable=False),
        sa.Column('plan_id', sa.String(length=64), nullable=False),
        sa.Column('tool_name', sa.String(length=64), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('input_params_json', sa.Text(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('execution_time_seconds', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['investigation_plans.plan_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('step_id')
    )
    op.create_index('idx_investigation_steps_plan_id', 'investigation_steps', ['plan_id'])
    op.create_index('idx_investigation_steps_status', 'investigation_steps', ['status'])

    # 3. investigation_traces
    op.create_table(
        'investigation_traces',
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('investigation_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('step_id', sa.String(length=64), nullable=False),
        sa.Column('tool_name', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='SUCCESS', nullable=False),
        sa.Column('duration_seconds', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('trace_id')
    )
    op.create_index('idx_traces_investigation_id', 'investigation_traces', ['investigation_id'])
    op.create_index('idx_traces_case_id', 'investigation_traces', ['case_id'])

    # 4. evaluation_runs
    op.create_table(
        'evaluation_runs',
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.Column('total_cases', sa.Integer(), nullable=False),
        sa.Column('passed_cases', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('metric_averages_json', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index('idx_eval_runs_timestamp', 'evaluation_runs', ['timestamp'])

    # 5. evaluation_results
    op.create_table(
        'evaluation_results',
        sa.Column('result_id', sa.String(length=64), nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('test_case_id', sa.String(length=64), nullable=False),
        sa.Column('test_case_name', sa.String(length=128), nullable=False),
        sa.Column('passed', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('metric_scores_json', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['evaluation_runs.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('result_id')
    )
    op.create_index('idx_eval_results_run_id', 'evaluation_results', ['run_id'])
    op.create_index('idx_eval_results_test_case_id', 'evaluation_results', ['test_case_id'])


def downgrade() -> None:
    op.drop_table('evaluation_results')
    op.drop_table('evaluation_runs')
    op.drop_table('investigation_traces')
    op.drop_table('investigation_steps')
    op.drop_index('idx_investigation_plans_tenant_id', table_name='investigation_plans')

    with op.batch_alter_table('investigation_plans') as batch_op:
        batch_op.drop_column('created_by')
        batch_op.drop_column('limit_reached_reason')
        batch_op.drop_column('budget_json')
        batch_op.drop_column('priority')
        batch_op.drop_column('tenant_id')
        batch_op.drop_column('subject_invoice_id')
