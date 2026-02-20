"""add share_token

Revision ID: c74f9128f670
Revises: 1ed6b9c78826
Create Date: 2026-02-17 08:24:51.180379

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c74f9128f670'
down_revision = '1ed6b9c78826'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipes',
        sa.Column('share_token', sa.String(64), nullable=True, unique=True)
    )
    op.create_index('ix_recipes_share_token', 'recipes', ['share_token'], unique=True)

def downgrade():
    op.drop_index('ix_recipes_share_token', table_name='recipes')
    op.drop_column('recipes', 'share_token')