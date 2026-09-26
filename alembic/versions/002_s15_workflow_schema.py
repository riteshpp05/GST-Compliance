"""Sprint 15 Enterprise Workflow & Case Lifecycle Schema

Revision ID: 002_s15_workflow_schema
Revises: 001_s14_initial_schema
Create Date: 2026-09-13 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_s15_workflow_schema'
down_revision: Union[str, None] = '001_s14_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to investigation_cases
    with op.batch_alter_table('investigation_cases') as batch_op:
        batch_op.add_column(sa.Column('case_type', sa.String(length=64), server_default='GST_COMPLIANCE_INVESTIGATION', nullable=False))
        batch_op.add_column(sa.Column('source', sa.String(length=64), server_default='AUTOMATED_SCAN', nullable=False))
        batch_op.add_column(sa.Column('created_by', sa.String(length=128), server_default='SYSTEM', nullable=False))

    # 2. investigation_plans
    op.create_table(
        'investigation_plans',
        sa.Column('plan_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('questions_json', sa.Text(), nullable=True),
        sa.Column('required_data_json', sa.Text(), nullable=True),
        sa.Column('expected_evidence_json', sa.Text(), nullable=True),
        sa.Column('analysis_tasks_json', sa.Text(), nullable=True),
        sa.Column('risk_areas_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PLANNED'),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('updated_at', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('plan_id')
    )
    op.create_index('idx_plans_case_id', 'investigation_plans', ['case_id'])

    # 3. case_evidence_records
    op.create_table(
        'case_evidence_records',
        sa.Column('evidence_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('evidence_type', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('data_json', sa.Text(), nullable=True),
        sa.Column('reliability', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('collected_at', sa.String(length=64), nullable=False),
        sa.Column('collected_by', sa.String(length=128), nullable=False, server_default='SYSTEM'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('evidence_id')
    )
    op.create_index('idx_evd_records_case_id', 'case_evidence_records', ['case_id'])
    op.create_index('idx_evd_records_type', 'case_evidence_records', ['evidence_type'])

    # 4. case_findings
    op.create_table(
        'case_findings',
        sa.Column('finding_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='COMPLIANCE_MISMATCH'),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default='HIGH'),
        sa.Column('evidence_ids_json', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='VERIFIED'),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False, server_default='SYSTEM'),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('finding_id')
    )
    op.create_index('idx_findings_case_id', 'case_findings', ['case_id'])
    op.create_index('idx_findings_severity', 'case_findings', ['severity'])

    # 5. case_risk_assessments
    op.create_table(
        'case_risk_assessments',
        sa.Column('assessment_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('risk_level', sa.String(length=32), nullable=False, server_default='LOW'),
        sa.Column('contributing_factors_json', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=False, server_default=''),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('assessed_at', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False, server_default='1.0'),
        sa.Column('rules_evaluated_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assessment_id')
    )
    op.create_index('idx_risk_assess_case_id', 'case_risk_assessments', ['case_id'])

    # 6. case_recommendations
    op.create_table(
        'case_recommendations',
        sa.Column('recommendation_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('recommended_action', sa.String(length=64), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('supporting_finding_ids_json', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('generated_by', sa.String(length=128), nullable=False, server_default='AI_AGENT'),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('recommendation_id')
    )
    op.create_index('idx_recommendations_case_id', 'case_recommendations', ['case_id'])
    op.create_index('idx_recommendations_action', 'case_recommendations', ['recommended_action'])


def downgrade() -> None:
    op.drop_table('case_recommendations')
    op.drop_table('case_risk_assessments')
    op.drop_table('case_findings')
    op.drop_table('case_evidence_records')
    op.drop_table('investigation_plans')
    with op.batch_alter_table('investigation_cases') as batch_op:
        batch_op.drop_column('created_by')
        batch_op.drop_column('source')
        batch_op.drop_column('case_type')
