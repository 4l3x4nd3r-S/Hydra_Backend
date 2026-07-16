"""Promover a Alfredo Vargas Peralta como supervisor.

Revision ID: f2b3c4d5e6a7
Revises: a2b3c4d5e6f7
Create Date: 2026-07-16 04:35:00.000000

Retira a Alfredo del personal operativo, transfiere las referencias del
supervisor provisional y elimina el usuario Supervisor1.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2b3c4d5e6a7"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            alfredo_id INTEGER;
            supervisor_anterior_id INTEGER;
        BEGIN
            SELECT id INTO alfredo_id
            FROM usuarios
            WHERE UPPER(TRIM(nombre)) = 'ALFREDO VARGAS PERALTA'
               OR codigo_empleado = 'MAN002'
               OR UPPER(TRIM(nombre)) = 'ALBERTO VARGAS PERALTA'
            ORDER BY
                CASE
                    WHEN UPPER(TRIM(nombre)) = 'ALFREDO VARGAS PERALTA' THEN 0
                    WHEN codigo_empleado = 'MAN002' THEN 1
                    ELSE 2
                END
            LIMIT 1;

            IF alfredo_id IS NULL THEN
                RAISE NOTICE 'No se encontró el usuario de Alfredo; no se modificaron usuarios.';
                RETURN;
            END IF;

            SELECT id INTO supervisor_anterior_id
            FROM usuarios
            WHERE id <> alfredo_id
              AND (
                  UPPER(TRIM(nombre)) = 'SUPERVISOR1'
                  OR codigo_empleado = 'SUP001'
              )
            LIMIT 1;

            DELETE FROM cuadrillas_personal WHERE usuario_id = alfredo_id;
            UPDATE ordenes_servicio
            SET responsable_id = NULL
            WHERE responsable_id = alfredo_id;

            UPDATE usuarios
            SET nombre = 'ALFREDO VARGAS PERALTA',
                rol = 'SUPERVISOR'::rol_usuario,
                cargo = NULL,
                area = 'MANTENIMIENTO'::area_usuario,
                activo = TRUE
            WHERE id = alfredo_id;

            IF supervisor_anterior_id IS NOT NULL THEN
                UPDATE ordenes_servicio
                SET supervisor_id = alfredo_id
                WHERE supervisor_id = supervisor_anterior_id;

                UPDATE ordenes_servicio
                SET responsable_id = NULL
                WHERE responsable_id = supervisor_anterior_id;

                UPDATE reclamos
                SET usuario_id = alfredo_id
                WHERE usuario_id = supervisor_anterior_id;

                DELETE FROM cuadrillas_personal
                WHERE usuario_id = supervisor_anterior_id;

                DELETE FROM usuarios WHERE id = supervisor_anterior_id;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE usuarios
        SET rol = 'GASFITERO'::rol_usuario,
            cargo = 'GASFITERO'::cargo_usuario,
            area = 'MANTENIMIENTO'::area_usuario
        WHERE UPPER(TRIM(nombre)) = 'ALFREDO VARGAS PERALTA';
        """
    )
