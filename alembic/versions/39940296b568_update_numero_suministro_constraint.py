"""Update numero_suministro constraint

Revision ID: 39940296b568
Revises: cb239f099008
Create Date: 2026-08-09 17:26:20.294203

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

revision: str = '39940296b568'
down_revision: Union[str, None] = 'cb239f099008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old constraint
    op.drop_constraint('ck_reclamos_numero_suministro_7_digitos', 'reclamos', type_='check')
    # Create the new constraint
    op.create_check_constraint(
        'ck_reclamos_numero_suministro_7_digitos',
        'reclamos',
        "numero_suministro IS NULL OR (numero_suministro ~ '^[0-9]{6,7}$' AND numero_suministro NOT IN ('0000000', '000000'))"
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint('ck_reclamos_numero_suministro_7_digitos', 'reclamos', type_='check')
    # Recreate the old constraint
    op.create_check_constraint(
        'ck_reclamos_numero_suministro_7_digitos',
        'reclamos',
        "numero_suministro IS NULL OR (numero_suministro ~ '^[0-9]{7}$' AND numero_suministro <> '0000000')"
    )
