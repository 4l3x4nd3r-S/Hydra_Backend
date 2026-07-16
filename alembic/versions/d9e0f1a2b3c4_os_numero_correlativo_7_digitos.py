"""Usar un correlativo global de siete digitos para las ordenes de servicio.

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-15 19:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Conserva todas las O.S. y les asigna un correlativo estable según su ID.
    op.execute(
        """
        WITH ordenes_numeradas AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS correlativo
            FROM ordenes_servicio
        )
        UPDATE ordenes_servicio AS os
        SET numero_orden = LPAD(ordenes_numeradas.correlativo::text, 7, '0')
        FROM ordenes_numeradas
        WHERE os.id = ordenes_numeradas.id
        """
    )

    op.alter_column(
        "ordenes_servicio",
        "numero_orden",
        existing_type=sa.String(length=50),
        type_=sa.String(length=7),
        existing_nullable=True,
    )
    op.create_unique_constraint(
        "uq_ordenes_servicio_numero_orden",
        "ordenes_servicio",
        ["numero_orden"],
    )
    op.create_check_constraint(
        "ck_ordenes_servicio_numero_orden_7_digitos",
        "ordenes_servicio",
        "numero_orden IS NULL OR numero_orden ~ '^[0-9]{7}$'",
    )

    op.execute(
        "CREATE SEQUENCE orden_servicio_numero_seq "
        "MINVALUE 1 MAXVALUE 9999999 START WITH 1"
    )
    op.execute(
        """
        DO $$
        DECLARE
            ultimo_numero bigint;
        BEGIN
            SELECT MAX(numero_orden::bigint)
            INTO ultimo_numero
            FROM ordenes_servicio;

            IF ultimo_numero IS NULL THEN
                PERFORM setval('orden_servicio_numero_seq', 1, false);
            ELSE
                PERFORM setval('orden_servicio_numero_seq', ultimo_numero, true);
            END IF;
        END $$
        """
    )

    op.drop_table("os_secuencia")


def downgrade() -> None:
    op.create_table(
        "os_secuencia",
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("contador", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("fecha", name="os_secuencia_pkey"),
    )
    op.create_index(
        "ix_os_secuencia_fecha", "os_secuencia", ["fecha"], unique=False
    )

    op.execute("DROP SEQUENCE orden_servicio_numero_seq")
    op.drop_constraint(
        "ck_ordenes_servicio_numero_orden_7_digitos",
        "ordenes_servicio",
        type_="check",
    )
    op.drop_constraint(
        "uq_ordenes_servicio_numero_orden",
        "ordenes_servicio",
        type_="unique",
    )
    op.alter_column(
        "ordenes_servicio",
        "numero_orden",
        existing_type=sa.String(length=7),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
