"""Sprint 17 Data Connectivity & Data Quality Schema

Revision ID: 003_s17_data_quality_schema
Revises: 002_s15_workflow_schema
Create Date: 2026-09-14 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_s17_data_quality_schema'
down_revision: Union[str, None] = '002_s15_workflow_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ingestion_jobs
    op.create_table(
        'ingestion_jobs',
        sa.Column('ingestion_id', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), server_default='tenant_default', nullable=False),
        sa.Column('dataset_type', sa.String(length=64), server_default='INVOICES', nullable=False),
        sa.Column('started_at', sa.String(length=64), nullable=False),
        sa.Column('completed_at', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('total_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('accepted_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('rejected_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duplicate_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('warning_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('quality_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('error_summary_json', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=128), server_default='SYSTEM', nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('ingestion_id')
    )
    op.create_index('idx_ingestion_jobs_tenant_id', 'ingestion_jobs', ['tenant_id'])
    op.create_index('idx_ingestion_jobs_status', 'ingestion_jobs', ['status'])
    op.create_index('idx_ingestion_jobs_source_id', 'ingestion_jobs', ['source_id'])

    # 2. ingestion_records
    op.create_table(
        'ingestion_records',
        sa.Column('record_id', sa.String(length=64), nullable=False),
        sa.Column('ingestion_id', sa.String(length=64), nullable=False),
        sa.Column('record_index', sa.Integer(), nullable=False),
        sa.Column('source_record_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), server_default='tenant_default', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='ACCEPTED', nullable=False),
        sa.Column('raw_data_json', sa.Text(), nullable=True),
        sa.Column('normalized_data_json', sa.Text(), nullable=True),
        sa.Column('quality_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('duplicate_status', sa.String(length=32), server_default='UNIQUE', nullable=False),
        sa.Column('fingerprint', sa.String(length=128), nullable=True),
        sa.Column('validation_errors_json', sa.Text(), nullable=True),
        sa.Column('validation_warnings_json', sa.Text(), nullable=True),
        sa.Column('transformation_log_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['ingestion_id'], ['ingestion_jobs.ingestion_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('record_id')
    )
    op.create_index('idx_ingestion_records_ingestion_id', 'ingestion_records', ['ingestion_id'])
    op.create_index('idx_ingestion_records_fingerprint', 'ingestion_records', ['fingerprint'])
    op.create_index('idx_ingestion_records_status', 'ingestion_records', ['status'])

    # 3. data_quality_reports
    op.create_table(
        'data_quality_reports',
        sa.Column('report_id', sa.String(length=64), nullable=False),
        sa.Column('ingestion_id', sa.String(length=64), nullable=False),
        sa.Column('overall_quality_score', sa.Float(), nullable=False),
        sa.Column('quality_status', sa.String(length=32), nullable=False),
        sa.Column('dimension_scores_json', sa.Text(), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('accepted_records', sa.Integer(), nullable=False),
        sa.Column('rejected_records', sa.Integer(), nullable=False),
        sa.Column('duplicate_records', sa.Integer(), nullable=False),
        sa.Column('warning_records', sa.Integer(), nullable=False),
        sa.Column('issues_json', sa.Text(), nullable=True),
        sa.Column('warnings_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['ingestion_id'], ['ingestion_jobs.ingestion_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index('idx_quality_reports_ingestion_id', 'data_quality_reports', ['ingestion_id'])

    # 4. data_lineage_records
    op.create_table(
        'data_lineage_records',
        sa.Column('lineage_id', sa.String(length=64), nullable=False),
        sa.Column('ingestion_id', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('source_record_id', sa.String(length=64), nullable=False),
        sa.Column('canonical_record_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), server_default='tenant_default', nullable=False),
        sa.Column('transformations_json', sa.Text(), nullable=True),
        sa.Column('downstream_evidence_ids_json', sa.Text(), nullable=True),
        sa.Column('downstream_finding_ids_json', sa.Text(), nullable=True),
        sa.Column('downstream_case_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('lineage_id')
    )
    op.create_index('idx_lineage_canonical_id', 'data_lineage_records', ['canonical_record_id'])
    op.create_index('idx_lineage_ingestion_id', 'data_lineage_records', ['ingestion_id'])
    op.create_index('idx_lineage_case_id', 'data_lineage_records', ['downstream_case_id'])


def downgrade() -> None:
    op.drop_index('idx_lineage_case_id', table_name='data_lineage_records')
    op.drop_index('idx_lineage_ingestion_id', table_name='data_lineage_records')
    op.drop_index('idx_lineage_canonical_id', table_name='data_lineage_records')
    op.drop_table('data_lineage_records')

    op.drop_index('idx_quality_reports_ingestion_id', table_name='data_quality_reports')
    op.drop_table('data_quality_reports')

    op.drop_index('idx_ingestion_records_status', table_name='ingestion_records')
    op.drop_index('idx_ingestion_records_fingerprint', table_name='ingestion_records')
    op.drop_index('idx_ingestion_records_ingestion_id', table_name='ingestion_records')
    op.drop_table('ingestion_records')

    op.drop_index('idx_ingestion_jobs_source_id', table_name='ingestion_jobs')
    op.drop_index('idx_ingestion_jobs_status', table_name='ingestion_jobs')
    op.drop_index('idx_ingestion_jobs_tenant_id', table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')
