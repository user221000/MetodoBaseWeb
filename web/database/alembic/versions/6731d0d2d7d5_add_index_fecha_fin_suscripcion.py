"""add_index_fecha_fin_suscripcion

Revision ID: 6731d0d2d7d5
Revises: a19a0ae3ac49
Create Date: 2026-03-26 10:33:20.057019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6731d0d2d7d5'
down_revision: Union[str, Sequence[str], None] = 'a19a0ae3ac49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Historic repair: the index preceded its column's f8 migration.
    if "fecha_fin_suscripcion" not in {item["name"] for item in sa.inspect(op.get_bind()).get_columns("clientes")}:
        op.add_column("clientes", sa.Column("fecha_fin_suscripcion", sa.DateTime(), nullable=True))
    op.create_index(
        op.f('ix_clientes_fecha_fin_suscripcion'),
        'clientes',
        ['fecha_fin_suscripcion'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_clientes_fecha_fin_suscripcion'), table_name='clientes')
