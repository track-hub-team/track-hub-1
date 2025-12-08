"""add_files_fingerprint_to_ds_meta_data

Revision ID: 6d2c27b643d8
Revises: f1a05f68a5b8
Create Date: 2025-12-08 18:27:42.542102

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d2c27b643d8'
down_revision = 'f1a05f68a5b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ds_meta_data', sa.Column('files_fingerprint', sa.String(64), nullable=True))


def downgrade():
    op.drop_column('ds_meta_data', 'files_fingerprint')
