"""
Stamp current models - empty migration

Revision ID: 0003_stamp_current
Revises: 0002_phase2
Create Date: 2025-08-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_stamp_current'
down_revision = '0002_phase2'
branch_labels = None
depends_on = None


def upgrade():
    # Empty migration: current schema assumed to match models in this repo snapshot.
    pass


def downgrade():
    pass
