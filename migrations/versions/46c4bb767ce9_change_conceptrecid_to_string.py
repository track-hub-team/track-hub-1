"""change_conceptrecid_to_string

Revision ID: 46c4bb767ce9
Revises: 6d2c27b643d8
Create Date: 2025-12-08 18:48:57.966754

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46c4bb767ce9'
down_revision = '6d2c27b643d8'
branch_labels = None
depends_on = None


def upgrade():
    # Cambiar tipo de columna de Integer a String(120)
    op.alter_column('ds_meta_data', 'conceptrecid',
                    existing_type=sa.Integer(),
                    type_=sa.String(120),
                    existing_nullable=True)


def downgrade():
    # Revertir a Integer
    op.alter_column('ds_meta_data', 'conceptrecid',
                    existing_type=sa.String(120),
                    type_=sa.Integer(),
                    existing_nullable=True)
