"""Sprint 14 Initial Relational Schema

Revision ID: 001_s14_initial_schema
Revises: 
Create Date: 2026-09-13 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_s14_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. investigation_sessions
    op.create_table(
        'investigation_sessions',
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('entity_focus_json', sa.Text(), nullable=True),
        sa.Column('accumulated_findings_json', sa.Text(), nullable=True),
        sa.Column('accumulated_regulatory_evidence_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('updated_at', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index('idx_sessions_status', 'investigation_sessions', ['status'])
    op.create_index('idx_sessions_created_at', 'investigation_sessions', ['created_at'])

    # 2. investigation_turns
    op.create_table(
        'investigation_turns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('resolved_query', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(length=64), nullable=False),
        sa.Column('tools_used_json', sa.Text(), nullable=True),
        sa.Column('findings_json', sa.Text(), nullable=True),
        sa.Column('regulatory_knowledge_json', sa.Text(), nullable=True),
        sa.Column('synthesized_answer', sa.Text(), nullable=False),
        sa.Column('confidence', sa.String(length=32), server_default='HIGH'),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['investigation_sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'turn_index', name='uq_session_turn_index')
    )
    op.create_index('idx_turns_session_id', 'investigation_turns', ['session_id'])

    # 3. investigation_cases
    op.create_table(
        'investigation_cases',
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False, server_default='P3'),
        sa.Column('risk_level', sa.String(length=32), nullable=False, server_default='LOW'),
        sa.Column('source_session_id', sa.String(length=64), nullable=True),
        sa.Column('source_dossier_id', sa.String(length=64), nullable=True),
        sa.Column('invoice_id', sa.String(length=64), nullable=True),
        sa.Column('counterparty_gstin', sa.String(length=32), nullable=True),
        sa.Column('counterparty_name', sa.String(length=256), nullable=True),
        sa.Column('assigned_to', sa.String(length=128), nullable=True),
        sa.Column('assigned_role', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('updated_at', sa.String(length=64), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False, server_default=''),
        sa.Column('financial_exposure', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('root_cause', sa.String(length=128), nullable=False, server_default='UNDETERMINED'),
        sa.Column('blast_radius_json', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('case_id')
    )
    op.create_index('idx_cases_status', 'investigation_cases', ['status'])
    op.create_index('idx_cases_priority', 'investigation_cases', ['priority'])
    op.create_index('idx_cases_risk_level', 'investigation_cases', ['risk_level'])
    op.create_index('idx_cases_assigned_to', 'investigation_cases', ['assigned_to'])
    op.create_index('idx_cases_invoice_id', 'investigation_cases', ['invoice_id'])
    op.create_index('idx_cases_source_session_id', 'investigation_cases', ['source_session_id'])

    # 4. case_decisions
    op.create_table(
        'case_decisions',
        sa.Column('decision_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=False),
        sa.Column('reviewer_role', sa.String(length=128), nullable=True),
        sa.Column('decision', sa.String(length=64), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('requested_evidence', sa.Text(), nullable=True),
        sa.Column('evidence_reviewed_json', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('decision_id')
    )
    op.create_index('idx_decisions_case_id', 'case_decisions', ['case_id'])
    op.create_index('idx_decisions_reviewer', 'case_decisions', ['reviewer'])

    # 5. case_events
    op.create_table(
        'case_events',
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('actor', sa.String(length=128), nullable=False),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.Column('previous_status', sa.String(length=64), nullable=True),
        sa.Column('new_status', sa.String(length=64), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('idx_events_case_id', 'case_events', ['case_id'])
    op.create_index('idx_events_event_type', 'case_events', ['event_type'])

    # 6. case_evidence_references
    op.create_table(
        'case_evidence_references',
        sa.Column('reference_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('source_identifier', sa.String(length=128), nullable=False),
        sa.Column('invoice_id', sa.String(length=64), nullable=True),
        sa.Column('gate_id', sa.Integer(), nullable=True),
        sa.Column('dossier_id', sa.String(length=64), nullable=True),
        sa.Column('session_id', sa.String(length=64), nullable=True),
        sa.Column('document_id', sa.String(length=128), nullable=True),
        sa.Column('section', sa.String(length=128), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False, server_default=''),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('reference_id')
    )
    op.create_index('idx_evidence_case_id', 'case_evidence_references', ['case_id'])
    op.create_index('idx_evidence_invoice_id', 'case_evidence_references', ['invoice_id'])
    op.create_index('idx_evidence_source_type', 'case_evidence_references', ['source_type'])


def downgrade() -> None:
    op.drop_table('case_evidence_references')
    op.drop_table('case_events')
    op.drop_table('case_decisions')
    op.drop_table('investigation_cases')
    op.drop_table('investigation_turns')
    op.drop_table('investigation_sessions')
