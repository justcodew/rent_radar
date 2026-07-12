"""add ai_insights column to listing_scores

Revision ID: cff1453cfb84
Revises: 0001
Create Date: 2026-07-06 23:49:26.084599
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'cff1453cfb84'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('listing_scores', sa.Column('ai_insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('listing_scores', 'ai_insights')
