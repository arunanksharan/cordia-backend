"""recreate deleted

Revision ID: 5b5ff7275c09
Revises: 16712157a5c7
Create Date: 2025-10-06 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b5ff7275c09'
down_revision: Union[str, None] = '16712157a5c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
