"""add space templates

Revision ID: 0005_add_space_templates
Revises: 0004_add_activity_template_fields
Create Date: 2025-08-23 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_add_space_templates'
down_revision = '0004_add_activity_template_fields'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # create space_templates table if missing
    if 'space_templates' not in tables:
        op.create_table(
            'space_templates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
        )

    # create space_template_fields table if missing
    if 'space_template_fields' not in tables:
        op.create_table(
            'space_template_fields',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('space_template_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('field_type', sa.String(), nullable=False),
            sa.Column('options', sa.Text(), nullable=True),
        )
        # add FK only if templates table exists
        if 'space_templates' in tables:
            op.create_foreign_key(
                'fk_space_template_fields_space_template_id',
                'space_template_fields', 'space_templates', ['space_template_id'], ['id']
            )

    # add column to spaces if not present
    if 'spaces' in tables:
        cols = [c['name'] for c in inspector.get_columns('spaces')]
        if 'space_template_id' not in cols:
            # Use batch_alter_table for SQLite compatibility when adding constraints
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('spaces') as batch_op:
                    batch_op.add_column(sa.Column('space_template_id', sa.Integer(), nullable=True))
                    if 'space_templates' in tables:
                        batch_op.create_foreign_key('fk_spaces_space_template_id', 'space_templates', ['space_template_id'], ['id'])
            else:
                op.add_column('spaces', sa.Column('space_template_id', sa.Integer(), nullable=True))
                if 'space_templates' in tables:
                    op.create_foreign_key('fk_spaces_space_template_id', 'spaces', 'space_templates', ['space_template_id'], ['id'])


def downgrade():
    # drop foreign key and column from spaces
    try:
        op.drop_constraint('fk_spaces_space_template_id', 'spaces', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('spaces', 'space_template_id')
    except Exception:
        pass

    # drop space_template_fields table
    try:
        op.drop_table('space_template_fields')
    except Exception:
        pass

    # drop space_templates table
    try:
        op.drop_table('space_templates')
    except Exception:
        pass
