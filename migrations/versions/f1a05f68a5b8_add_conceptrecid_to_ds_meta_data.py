"""add_conceptrecid_to_ds_meta_data

Revision ID: f1a05f68a5b8
Revises: c83a25ec9445
Create Date: 2025-12-08 18:17:58.588106

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a05f68a5b8'
down_revision = 'c83a25ec9445'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ds_meta_data', sa.Column('conceptrecid', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('ds_meta_data', 'conceptrecid')
