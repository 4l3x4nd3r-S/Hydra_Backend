"""Asignar identificadores automáticos e irrepetibles a las cuadrillas.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-15 22:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH cuadrillas_numeradas AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS numero
            FROM cuadrillas
        )
        UPDATE cuadrillas AS c
        SET codigo_grupo = 'Cuadrilla ' ||
            LPAD(cuadrillas_numeradas.numero::text, 3, '0')
        FROM cuadrillas_numeradas
        WHERE c.id = cuadrillas_numeradas.id
        """
    )

    op.create_unique_constraint(
        "uq_cuadrillas_codigo_grupo",
        "cuadrillas",
        ["codigo_grupo"],
    )
    op.execute(
        "CREATE SEQUENCE cuadrilla_numero_seq "
        "MINVALUE 1 MAXVALUE 999999 START WITH 1"
    )
    op.execute(
        """
        DO $$
        DECLARE
            cantidad_cuadrillas bigint;
        BEGIN
            SELECT COUNT(*) INTO cantidad_cuadrillas FROM cuadrillas;
            IF cantidad_cuadrillas = 0 THEN
                PERFORM setval('cuadrilla_numero_seq', 1, false);
            ELSE
                PERFORM setval(
                    'cuadrilla_numero_seq',
                    cantidad_cuadrillas,
                    true
                );
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE cuadrilla_numero_seq")
    op.drop_constraint(
        "uq_cuadrillas_codigo_grupo",
        "cuadrillas",
        type_="unique",
    )
