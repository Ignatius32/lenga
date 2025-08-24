"""
Phase 2 migration: add movement log details and agent assignments handling

Revision ID: 0002_phase2
Revises: 
Create Date: 2025-08-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_phase2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Note: Autogenerate locally with alembic revision --autogenerate
    op.create_table('ticket_movement_log',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ticket_id', sa.Integer, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('action_user_id', sa.Integer, nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('ticket_movement_log')
