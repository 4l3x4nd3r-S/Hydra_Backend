"""Actualizar las credenciales de Alfredo como supervisor.

Revision ID: f3c4d5e6a7b8
Revises: f2b3c4d5e6a7
Create Date: 2026-07-16 05:20:00.000000
"""
from typing import Sequence, Union
import os

import sqlalchemy as sa
from alembic import op

from app.core.security import hash_password


revision: str = "f3c4d5e6a7b8"
down_revision: Union[str, None] = "f2b3c4d5e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _actualizar_credenciales(codigo: str, password: str) -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE usuarios
            SET codigo_empleado = :codigo,
                password_hash = :password_hash
            WHERE UPPER(TRIM(nombre)) = 'ALFREDO VARGAS PERALTA'
               OR codigo_empleado IN ('MAN002', 'SUP001')
            """
        ),
        {
            "codigo": codigo,
            "password_hash": hash_password(password),
        },
    )


def upgrade() -> None:
    codigo = os.environ.get("HYDRA_INITIAL_SUPERVISOR_CODE")
    password = os.environ.get("HYDRA_INITIAL_SUPERVISOR_PASSWORD")
    if not codigo or not password:
        raise RuntimeError(
            "HYDRA_INITIAL_SUPERVISOR_CODE y "
            "HYDRA_INITIAL_SUPERVISOR_PASSWORD son obligatorios para esta migración."
        )
    _actualizar_credenciales(codigo, password)


def downgrade() -> None:
    # Un downgrade no debe restaurar una contraseña conocida ni recuperar
    # secretos que no están almacenados en texto plano.
    return None
