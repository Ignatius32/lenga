"""add activity template fields

Revision ID: 0004_add_activity_template_fields
Revises: e944015c1998
Create Date: 2025-08-23 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_activity_template_fields'
down_revision = 'e944015c1998'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'activity_type_fields',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('activity_type_id', sa.Integer(), sa.ForeignKey('activity_types.id')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('field_type', sa.String(), nullable=False),
        sa.Column('options', sa.Text(), nullable=True),
    )
    op.create_table(
        'activity_field_values',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('activity_id', sa.Integer(), sa.ForeignKey('activities.id')),
        sa.Column('field_id', sa.Integer(), sa.ForeignKey('activity_type_fields.id')),
        sa.Column('value', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('activity_field_values')
    op.drop_table('activity_type_fields')
