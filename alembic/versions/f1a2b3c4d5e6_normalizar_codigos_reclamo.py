"""Normalizar códigos de solicitud y números de medidor.

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-07-15 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE reclamos
        SET codigo_solicitud = CASE
            WHEN COALESCE(substring(codigo_solicitud FROM '([0-9]+)$'), '') ~ '[1-9]'
                THEN LPAD(
                    RIGHT(substring(codigo_solicitud FROM '([0-9]+)$'), 5),
                    5,
                    '0'
                )
            ELSE LPAD(((MOD(id - 1, 99999)) + 1)::text, 5, '0')
        END
        WHERE codigo_solicitud IS NULL
           OR codigo_solicitud !~ '^[0-9]{5}$'
           OR codigo_solicitud = '00000'
        """
    )
    op.execute(
        """
        UPDATE reclamos
        SET numero_medidor = CASE
            WHEN COALESCE(regexp_replace(numero_medidor, '[^0-9]', '', 'g'), '') ~ '[1-9]'
                THEN LPAD(
                    RIGHT(regexp_replace(numero_medidor, '[^0-9]', '', 'g'), 7),
                    7,
                    '0'
                )
            ELSE LPAD(((MOD(id - 1, 9999999)) + 1)::text, 7, '0')
        END
        WHERE numero_medidor IS NULL
           OR numero_medidor !~ '^[0-9]{7}$'
           OR numero_medidor = '0000000'
        """
    )

    op.alter_column(
        "reclamos",
        "codigo_solicitud",
        existing_type=sa.String(length=50),
        type_=sa.String(length=5),
        existing_nullable=True,
    )
    op.alter_column(
        "reclamos",
        "numero_medidor",
        existing_type=sa.String(length=50),
        type_=sa.String(length=7),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_reclamos_codigo_solicitud_5_digitos",
        "reclamos",
        "codigo_solicitud IS NULL OR "
        "(codigo_solicitud ~ '^[0-9]{5}$' AND codigo_solicitud <> '00000')",
    )
    op.create_check_constraint(
        "ck_reclamos_numero_medidor_7_digitos",
        "reclamos",
        "numero_medidor IS NULL OR "
        "(numero_medidor ~ '^[0-9]{7}$' AND numero_medidor <> '0000000')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_reclamos_numero_medidor_7_digitos",
        "reclamos",
        type_="check",
    )
    op.drop_constraint(
        "ck_reclamos_codigo_solicitud_5_digitos",
        "reclamos",
        type_="check",
    )
    op.alter_column(
        "reclamos",
        "numero_medidor",
        existing_type=sa.String(length=7),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
    op.alter_column(
        "reclamos",
        "codigo_solicitud",
        existing_type=sa.String(length=5),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
