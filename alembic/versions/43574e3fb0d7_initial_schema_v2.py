"""initial_schema_v2

Revision ID: 43574e3fb0d7
Revises:
Create Date: 2026-06-30 01:42:07.755463

Migración drop-and-recreate: elimina todo el esquema anterior y crea
las 9 tablas del nuevo modelo entidad-relación Hydra v2.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '43574e3fb0d7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── DROPS (orden inverso de dependencias) ────────────────────────────────
    op.execute("DROP TABLE IF EXISTS alertas CASCADE")
    op.execute("DROP TABLE IF EXISTS lecturas_presion CASCADE")
    op.execute("DROP TABLE IF EXISTS sensores CASCADE")
    op.execute("DROP TABLE IF EXISTS ordenes_trabajo CASCADE")
    op.execute("DROP TABLE IF EXISTS reclamos CASCADE")
    op.execute("DROP TABLE IF EXISTS sectores CASCADE")
    op.execute("DROP TABLE IF EXISTS usuarios CASCADE")
    op.execute("DROP TABLE IF EXISTS cuadrillas_gasfiteros CASCADE")
    op.execute("DROP TABLE IF EXISTS cuadrillas CASCADE")
    op.execute("DROP TABLE IF EXISTS elementos_red CASCADE")
    op.execute("DROP TABLE IF EXISTS registros_presion CASCADE")
    op.execute("DROP TABLE IF EXISTS puntos_presion CASCADE")
    op.execute("DROP TABLE IF EXISTS ordenes_servicio CASCADE")

    op.execute("DROP TYPE IF EXISTS rol_usuario CASCADE")
    op.execute("DROP TYPE IF EXISTS estadoot CASCADE")
    op.execute("DROP TYPE IF EXISTS prioridadot CASCADE")
    op.execute("DROP TYPE IF EXISTS tipoalerta CASCADE")
    op.execute("DROP TYPE IF EXISTS nivelalerta CASCADE")
    op.execute("DROP TYPE IF EXISTS estadoalerta CASCADE")

    # ── TABLAS ───────────────────────────────────────────────────────────────

    op.create_table(
        "sectores",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("reservorio_asociado", sa.String(100), nullable=True),
        sa.Column("geometria_geojson", sa.Text, nullable=True),
    )

    op.create_table(
        "puntos_presion",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("codigo_punto", sa.String(50), unique=True, nullable=False),
        sa.Column("latitud", sa.Float, nullable=True),
        sa.Column("longitud", sa.Float, nullable=True),
        sa.Column("sector_id", sa.Integer, sa.ForeignKey("sectores.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "elementos_red",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("codigo_plano", sa.String(50), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=True),
        sa.Column("latitud", sa.Float, nullable=True),
        sa.Column("longitud", sa.Float, nullable=True),
        sa.Column("sector_id", sa.Integer, sa.ForeignKey("sectores.id"), nullable=True),
        sa.Column("estado_operativo", sa.String(50), nullable=True),
        sa.Column("estado_valvula", sa.String(50), nullable=True),
        sa.Column("fecha_modificacion", sa.DateTime, nullable=True),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("codigo_empleado", sa.String(50), unique=True, nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("SUPERVISOR", "GASFITERO", name="rol_usuario"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "cuadrillas",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("codigo_grupo", sa.String(50), nullable=False),
        sa.Column("especialidad", sa.String(50), nullable=True),
    )

    op.create_table(
        "cuadrillas_gasfiteros",
        sa.Column("cuadrilla_id", sa.Integer, sa.ForeignKey("cuadrillas.id"), primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), primary_key=True),
    )

    op.create_table(
        "reclamos",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("codigo_ticket_cisco", sa.String(50), nullable=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("canal_entrada", sa.String(50), nullable=True),
        sa.Column("tipo_problema", sa.String(50), nullable=True),
        sa.Column("formato", sa.String(50), nullable=True),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("direccion", sa.String(255), nullable=True),
        sa.Column("latitud", sa.Float, nullable=True),
        sa.Column("longitud", sa.Float, nullable=True),
        sa.Column("estado", sa.String(50), nullable=True),
        sa.Column("fecha_registro", sa.DateTime, nullable=False),
    )

    op.create_table(
        "registros_presion",
        sa.Column("id", sa.BigInteger, primary_key=True, index=True),
        sa.Column("punto_presion_id", sa.Integer, sa.ForeignKey("puntos_presion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.Column("presion_mca", sa.Float, nullable=False),
        sa.Column("temperatura_c", sa.Float, nullable=True),
        sa.Column("dispositivo_serie", sa.String(50), nullable=True),
        sa.UniqueConstraint("punto_presion_id", "fecha_hora", name="uq_punto_timestamp"),
    )

    op.create_table(
        "ordenes_servicio",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("numero_orden", sa.String(50), nullable=True),
        sa.Column("reclamo_id", sa.Integer, sa.ForeignKey("reclamos.id"), nullable=True),
        sa.Column("supervisor_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("cuadrilla_id", sa.Integer, sa.ForeignKey("cuadrillas.id"), nullable=True),
        sa.Column("sector_id", sa.Integer, sa.ForeignKey("sectores.id"), nullable=True),
        sa.Column("fecha_programacion", sa.DateTime, nullable=True),
        sa.Column("fecha_ejecucion_inicio", sa.DateTime, nullable=True),
        sa.Column("fecha_ejecucion_fin", sa.DateTime, nullable=True),
        sa.Column("estado_orden", sa.String(50), nullable=True),
        sa.Column("insumos_utilizados", sa.Text, nullable=True),
        sa.Column("observaciones_gasfitero", sa.Text, nullable=True),
        sa.Column("ruta_carpeta_evidencias", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ordenes_servicio CASCADE")
    op.execute("DROP TABLE IF EXISTS registros_presion CASCADE")
    op.execute("DROP TABLE IF EXISTS puntos_presion CASCADE")
    op.execute("DROP TABLE IF EXISTS reclamos CASCADE")
    op.execute("DROP TABLE IF EXISTS cuadrillas_gasfiteros CASCADE")
    op.execute("DROP TABLE IF EXISTS cuadrillas CASCADE")
    op.execute("DROP TABLE IF EXISTS usuarios CASCADE")
    op.execute("DROP TABLE IF EXISTS elementos_red CASCADE")
    op.execute("DROP TABLE IF EXISTS sectores CASCADE")
    op.execute("DROP TYPE IF EXISTS rol_usuario CASCADE")
