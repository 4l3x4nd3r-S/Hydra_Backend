"""Crear catálogos operativos administrables.

Revision ID: d7e8f9a0b1c2
Revises: c7d8e9f0a1b2
Create Date: 2026-07-20 02:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalogo_opciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grupo", sa.String(length=50), nullable=False),
        sa.Column("codigo", sa.String(length=120), nullable=False),
        sa.Column("etiqueta", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("padre_codigo", sa.String(length=120), nullable=True),
        sa.Column("relacionado_codigo", sa.String(length=120), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("predeterminado", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grupo", "codigo", name="uq_catalogo_grupo_codigo"),
    )
    op.create_index(
        "ix_catalogo_opciones_grupo",
        "catalogo_opciones",
        ["grupo"],
        unique=False,
    )
    op.create_index(
        "ix_catalogo_opciones_id",
        "catalogo_opciones",
        ["id"],
        unique=False,
    )

    tabla = sa.table(
        "catalogo_opciones",
        sa.column("grupo", sa.String()),
        sa.column("codigo", sa.String()),
        sa.column("etiqueta", sa.String()),
        sa.column("descripcion", sa.Text()),
        sa.column("padre_codigo", sa.String()),
        sa.column("relacionado_codigo", sa.String()),
        sa.column("orden", sa.Integer()),
        sa.column("activo", sa.Boolean()),
        sa.column("predeterminado", sa.Boolean()),
    )

    def fila(
        grupo: str,
        codigo: str,
        etiqueta: str,
        orden: int,
        *,
        descripcion: str | None = None,
        padre: str | None = None,
        relacionado: str | None = None,
        predeterminado: bool = False,
    ) -> dict:
        return {
            "grupo": grupo,
            "codigo": codigo,
            "etiqueta": etiqueta,
            "descripcion": descripcion,
            "padre_codigo": padre,
            "relacionado_codigo": relacionado,
            "orden": orden,
            "activo": True,
            "predeterminado": predeterminado,
        }

    opciones = [
        fila("ESPECIALIDAD_CUADRILLA", "Agua", "Agua", 1, predeterminado=True),
        fila("ESPECIALIDAD_CUADRILLA", "Alcantarillado", "Alcantarillado", 2),
        fila("FORMATO_RECLAMO", "Anexo 6", "Anexo 6", 1, relacionado="Alcantarillado", predeterminado=True),
        fila("FORMATO_RECLAMO", "Formato 1", "Formato 1", 2, relacionado="Agua"),
        fila("CANAL_RECLAMO", "Presencial", "Presencial", 1, predeterminado=True),
        fila("CANAL_RECLAMO", "Call Center", "Call Center", 2),
        fila("CANAL_RECLAMO", "Llamada Directa", "Llamada Directa", 3),
        fila("ESTADO_RECLAMO", "PENDIENTE", "Pendiente", 1, predeterminado=True),
        fila("ESTADO_RECLAMO", "ASIGNADO", "Asignado", 2),
        fila("ESTADO_RECLAMO", "EN PROCESO", "En proceso", 3),
        fila("ESTADO_RECLAMO", "ATENDIDO", "Atendido", 4),
        fila("ESTADO_RECLAMO", "RECHAZADO", "Rechazado", 5),
        fila("ESTADO_RECLAMO", "CERRADO", "Cerrado", 6),
        fila("ESTADO_ORDEN", "ASIGNADO", "Asignada", 1, predeterminado=True),
        fila("ESTADO_ORDEN", "EN_PROCESO", "En proceso", 2),
        fila("ESTADO_ORDEN", "COMPLETADO", "Completada", 3),
        fila("ESTADO_ORDEN", "ARCHIVADO", "Archivada", 4),
        fila("FUNCION_CUADRILLA", "GASFITERO", "Gasfitero", 1),
        fila("FUNCION_CUADRILLA", "LIDER", "Gasfitero principal", 2),
        fila("FUNCION_CUADRILLA", "APOYO", "Gasfitero de apoyo", 3),
        fila("FUNCION_CUADRILLA", "CHOFER", "Chofer", 4),
        fila("AREA_USUARIO", "MANTENIMIENTO", "Mantenimiento", 1),
        fila("CARGO_USUARIO", "GASFITERO", "Gasfitero", 1),
        fila("CARGO_USUARIO", "GASFITERO_PRINCIPAL", "Gasfitero principal", 2),
        fila("CARGO_USUARIO", "GASFITERO_APOYO", "Gasfitero de apoyo", 3),
        fila("CARGO_USUARIO", "CHOFER_CAMIONETA", "Chofer", 4),
    ]

    anexo = {
        "OP-1": "Obras inconclusas (vereda pendiente, calzada pendiente)",
        "OP-2": "Fugas en la red de agua potable e inundaciones (roturas de tuberías en redes matriz y secundaria, fuga de agua en vereda o en calzada)",
        "OP-3": "Desbordes en la red de alcantarillado (rotura de tubería)",
        "OP-4": "Atoro en conexión de alcantarillado e inundaciones (taponamiento de conexiones en una zona, taponamiento con desborde en la calle)",
        "OP-5": "Cortes del servicio no programados o incumplimiento del horario de abastecimiento",
        "OP-6": "Falta de accesorios de seguridad en instalaciones y trabajos en ejecución",
        "OP-7": "Seguridad: emanaciones del sistema de alcantarillado",
    }
    for orden, (codigo, descripcion) in enumerate(anexo.items(), start=1):
        opciones.append(
            fila(
                "TIPO_PROBLEMA",
                codigo,
                codigo,
                orden,
                descripcion=descripcion,
                padre="Anexo 6",
                predeterminado=orden == 1,
            )
        )

    formato_1 = [
        ("B1", "Agua potable · Fugas en conexión domiciliaria"),
        ("B5", "Agua potable · Fugas en red matriz"),
        ("B8", "Agua potable · Falta de agua"),
        ("B9", "Agua potable · Limpieza de llave de toma"),
        ("B10", "Agua potable · Fuga de agua en caja de medidor"),
        ("B11", "Agua potable · Mantenimiento de medidor"),
        ("B13", "Agua potable · Calidad de agua"),
        ("B14", "Agua potable · Instalación de medidor"),
        ("FALTA DE PRESIÓN DE AGUA", "Agua potable · Presión insuficiente en el predio"),
        ("REPOSICIÓN DE CAJA DE MEDIDOR", "Agua potable · Caja de medidor rota o deteriorada"),
        ("REPOSICIÓN DE MEDIDOR POR HURTO", "Agua potable · Robo del medidor"),
        ("CAMBIO DE LLAVE DE PASO", "Agua potable · Válvula de control malograda"),
        ("REUBICACIÓN DE CONEXION", "Agua potable · Mover la toma de agua a otro punto"),
        ("REPOSICIÓN DE MARCO Y TAPA DE AGUA", "Agua potable · Cambio de la cubierta protectora"),
        ("NIVELACIÓN DE CAJA DE REGISTRO DE AGUA", "Agua potable · Ajustar la caja a la altura de la vereda"),
        ("B6", "Alcantarillado · Atoro en conexión domiciliaria"),
        ("B7", "Alcantarillado · Atoro en red matriz"),
        ("B12", "Alcantarillado · Buzón sin tapa"),
        ("REPOSICIÓN DE MARCO Y TAPA DE ALCANTARILLADO", "Alcantarillado · Tapa de registro domiciliario dañada"),
        ("NIVELACIÓN DE CAJA DE REGISTRO DE ALCANTARILLADO", "Alcantarillado · Alinear la caja de registro a la vereda"),
        ("REPOSICIÓN DE TUBERIA DE CONCRETO A PVC - ALCANTARILLADO", "Alcantarillado · Modernización de redes antiguas"),
        ("A1", "Otros · Filtración de agua externa hacia el predio"),
        ("TRABAJOS COLATERAS", "Otros · Daños incidentales a veredas o pistas tras reparaciones"),
        ("OTROS", "Otros · Reclamos generales sin categoría definida"),
    ]
    for orden, (codigo, descripcion) in enumerate(formato_1, start=1):
        opciones.append(
            fila(
                "TIPO_PROBLEMA",
                codigo,
                codigo,
                orden,
                descripcion=descripcion,
                padre="Formato 1",
                predeterminado=orden == 1,
            )
        )

    op.bulk_insert(tabla, opciones)


def downgrade() -> None:
    op.drop_index("ix_catalogo_opciones_id", table_name="catalogo_opciones")
    op.drop_index("ix_catalogo_opciones_grupo", table_name="catalogo_opciones")
    op.drop_table("catalogo_opciones")
