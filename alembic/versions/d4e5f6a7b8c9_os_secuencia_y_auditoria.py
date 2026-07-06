"""os_secuencia_y_auditoria

Revision ID: d4e5f6a7b8c9
Revises: c76ece5b8293
Create Date: 2026-07-03 10:00:00.000000

Agrega tabla os_secuencia (correlativo diario para numero_orden)
y auditoria_eventos (trazabilidad para fiscalización).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "os_secuencia",
        sa.Column("fecha", sa.Date, primary_key=True),
        sa.Column("contador", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_index("ix_os_secuencia_fecha", "os_secuencia", ["fecha"])

    op.create_table(
        "auditoria_eventos",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "timestamp",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Integer, nullable=True),
        sa.Column("usuario_nombre", sa.String(200), nullable=True),
        sa.Column("rol", sa.String(50), nullable=True),
        sa.Column("accion", sa.String(100), nullable=False),
        sa.Column("entidad", sa.String(100), nullable=False),
        sa.Column("entidad_id", sa.Integer, nullable=True),
        sa.Column("detalles", postgresql.JSONB, nullable=True),
    )

    op.create_index(
        "ix_auditoria_accion_entidad",
        "auditoria_eventos",
        ["accion", "entidad"],
    )
    op.create_index(
        "ix_auditoria_timestamp", "auditoria_eventos", ["timestamp"]
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auditoria_eventos CASCADE")
    op.execute("DROP TABLE IF EXISTS os_secuencia CASCADE")
