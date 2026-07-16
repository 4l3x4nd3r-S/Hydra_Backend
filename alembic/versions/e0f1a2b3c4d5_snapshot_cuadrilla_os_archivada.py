"""Guardar la cuadrilla historica de las ordenes de servicio archivadas.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-15 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e0f1a2b3c4d5"
down_revision: Union[str, None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ordenes_servicio",
        sa.Column("cuadrilla_snapshot", postgresql.JSONB(), nullable=True),
    )

    # Las O.S. ya terminadas quedan congeladas con la composición disponible
    # al aplicar esta migración. Desde aquí, cada finalización crea su snapshot.
    op.execute(
        """
        UPDATE ordenes_servicio AS os
        SET cuadrilla_snapshot = jsonb_build_object(
            'id', c.id,
            'codigo_grupo', c.codigo_grupo,
            'especialidad', c.especialidad,
            'lider', (
                SELECT jsonb_build_object(
                    'id', u.id,
                    'nombre', u.nombre,
                    'codigo_empleado', u.codigo_empleado,
                    'rol_en_cuadrilla', cp.rol_en_cuadrilla::text
                )
                FROM cuadrillas_personal cp
                JOIN usuarios u ON u.id = cp.usuario_id
                WHERE cp.cuadrilla_id = c.id
                  AND cp.rol_en_cuadrilla::text = 'LIDER'
                LIMIT 1
            ),
            'apoyos', COALESCE((
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'id', u.id,
                        'nombre', u.nombre,
                        'codigo_empleado', u.codigo_empleado,
                        'rol_en_cuadrilla', cp.rol_en_cuadrilla::text
                    ) ORDER BY u.nombre
                )
                FROM cuadrillas_personal cp
                JOIN usuarios u ON u.id = cp.usuario_id
                WHERE cp.cuadrilla_id = c.id
                  AND cp.rol_en_cuadrilla::text = 'APOYO'
            ), '[]'::jsonb),
            'chofer', (
                SELECT jsonb_build_object(
                    'id', u.id,
                    'nombre', u.nombre,
                    'codigo_empleado', u.codigo_empleado,
                    'rol_en_cuadrilla', cp.rol_en_cuadrilla::text
                )
                FROM cuadrillas_personal cp
                JOIN usuarios u ON u.id = cp.usuario_id
                WHERE cp.cuadrilla_id = c.id
                  AND cp.rol_en_cuadrilla::text = 'CHOFER'
                LIMIT 1
            ),
            'operador', (
                SELECT jsonb_build_object(
                    'id', u.id,
                    'nombre', u.nombre,
                    'codigo_empleado', u.codigo_empleado,
                    'rol_en_cuadrilla', cp.rol_en_cuadrilla::text
                )
                FROM cuadrillas_personal cp
                JOIN usuarios u ON u.id = cp.usuario_id
                WHERE cp.cuadrilla_id = c.id
                  AND cp.rol_en_cuadrilla::text = 'OPERADOR'
                LIMIT 1
            )
        )
        FROM cuadrillas c
        WHERE os.cuadrilla_id = c.id
          AND UPPER(COALESCE(os.estado_orden, '')) IN ('COMPLETADO', 'ARCHIVADO')
        """
    )


def downgrade() -> None:
    op.drop_column("ordenes_servicio", "cuadrilla_snapshot")
