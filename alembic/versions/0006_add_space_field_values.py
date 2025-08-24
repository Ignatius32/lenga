"""add space field values

Revision ID: 0006_add_space_field_values
Revises: 0005_add_space_templates
Create Date: 2025-08-23 12:55:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0006_add_space_field_values'
down_revision = '0005_add_space_templates'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'space_field_values' not in tables:
        op.create_table(
            'space_field_values',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('field_name', sa.String(), nullable=False),
            sa.Column('value', sa.Text(), nullable=True),
        )
        if 'spaces' in tables:
            op.create_foreign_key('fk_space_field_values_space_id', 'space_field_values', 'spaces', ['space_id'], ['id'])


def downgrade():
    try:
        op.drop_table('space_field_values')
    except Exception:
        pass
