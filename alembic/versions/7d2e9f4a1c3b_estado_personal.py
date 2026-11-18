"""Agregar estado del personal (activo, ausente, retirado).

Revision ID: 7d2e9f4a1c3b
Revises: 6c91240d80e1
Create Date: 2026-11-18 00:05:00.000000

- Enum ``estado_personal``: ``ACTIVO``, ``AUSENTE``, ``RETIRADO``.
- Columnas nuevas en ``usuarios``: ``estado``, ``motivo_ausencia`` y
  ``fecha_retorno``.
- Relleno: ``activo = true`` -> ``ACTIVO``, ``activo = false`` -> ``RETIRADO``.

La columna ``activo`` se conserva y se mantiene sincronizada desde el modelo
(``activo = (estado == ACTIVO)``), de modo que las consultas existentes
(login, refresh, supervisor y app móvil) sigan funcionando sin cambios.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7d2e9f4a1c3b"
down_revision: Union[str, None] = "6c91240d80e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

estado_personal = postgresql.ENUM(
    "ACTIVO",
    "AUSENTE",
    "RETIRADO",
    name="estado_personal",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE estado_personal AS ENUM ('ACTIVO', 'AUSENTE', 'RETIRADO')"
    )

    op.add_column(
        "usuarios",
        sa.Column(
            "estado",
            estado_personal,
            nullable=False,
            server_default="ACTIVO",
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("motivo_ausencia", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "usuarios",
        sa.Column("fecha_retorno", sa.Date(), nullable=True),
    )

    op.execute(
        """
        UPDATE usuarios
        SET estado = CASE
            WHEN COALESCE(activo, true) THEN 'ACTIVO'::estado_personal
            ELSE 'RETIRADO'::estado_personal
        END
        """
    )


def downgrade() -> None:
    op.drop_column("usuarios", "fecha_retorno")
    op.drop_column("usuarios", "motivo_ausencia")
    op.drop_column("usuarios", "estado")
    op.execute("DROP TYPE estado_personal")
