import unittest
from datetime import date

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.usuario import EstadoPersonal, RolUsuario, Usuario
from app.schemas.usuario import ActualizarUsuarioRequest, CrearUsuarioRequest

PASSWORD = "clave-segura-123"


class EsquemaEstadosPersonalTest(unittest.TestCase):
    def test_crear_usuario_usa_valores_operativos_por_defecto(self):
        payload = CrearUsuarioRequest(
            codigo_empleado="MAN100",
            nombre="Persona Nueva",
            password=PASSWORD,
        )

        self.assertEqual(payload.rol, RolUsuario.GASFITERO)
        self.assertEqual(payload.cargo, "GASFITERO")
        self.assertEqual(payload.area, "MANTENIMIENTO")

    def test_crear_usuario_rechaza_cargo_chofer(self):
        for cargo in ("CHOFER_CAMIONETA", "CHOFER", "chofer_camioneta"):
            with self.subTest(cargo=cargo), self.assertRaises(ValidationError):
                CrearUsuarioRequest(
                    codigo_empleado="MAN101",
                    nombre="Persona Chofer",
                    password=PASSWORD,
                    cargo=cargo,
                )

    def test_actualizar_usuario_rechaza_cargo_chofer(self):
        with self.assertRaises(ValidationError):
            ActualizarUsuarioRequest(cargo="CHOFER_CAMIONETA")

    def test_actualizar_usuario_acepta_fecha_de_retorno_iso_con_hora(self):
        payload = ActualizarUsuarioRequest(
            estado=EstadoPersonal.AUSENTE,
            motivo_ausencia="Vacaciones",
            fecha_retorno="2026-12-01T00:00:00",
        )

        self.assertEqual(payload.fecha_retorno, date(2026, 12, 1))

    def test_modelo_sincroniza_activo_con_estado(self):
        usuario = Usuario(
            codigo_empleado="GAS900",
            nombre="Persona",
            password_hash="hash",
            rol=RolUsuario.GASFITERO,
            estado=EstadoPersonal.AUSENTE,
        )
        self.assertFalse(usuario.activo)

        usuario.estado = EstadoPersonal.ACTIVO
        self.assertTrue(usuario.activo)

        usuario.estado = EstadoPersonal.RETIRADO
        self.assertFalse(usuario.activo)


async def _crear_usuario(
    db: AsyncSession,
    *,
    codigo: str,
    estado: EstadoPersonal = EstadoPersonal.ACTIVO,
    dni: str | None = None,
    celular: str | None = None,
) -> Usuario:
    usuario = Usuario(
        codigo_empleado=codigo,
        nombre=f"Persona {codigo}",
        password_hash=hash_password(PASSWORD),
        rol=RolUsuario.GASFITERO,
        cargo="GASFITERO",
        area="MANTENIMIENTO",
        dni=dni,
        celular=celular,
        estado=estado,
    )
    db.add(usuario)
    await db.flush()
    return usuario


async def _asegurar_catalogos(db: AsyncSession) -> None:
    await db.execute(
        text(
            """
            INSERT INTO catalogo_opciones
                (grupo, codigo, etiqueta, orden, activo, predeterminado)
            VALUES
                ('CARGO_USUARIO', 'GASFITERO', 'Gasfitero', 1, true, true),
                ('AREA_USUARIO', 'MANTENIMIENTO', 'Mantenimiento', 1, true, true)
            ON CONFLICT (grupo, codigo) DO NOTHING
            """
        )
    )


@pytest.mark.asyncio
async def test_login_de_ausente_devuelve_403_con_fecha_de_retorno(
    client: AsyncClient, db_session: AsyncSession
):
    usuario = await _crear_usuario(
        db_session, codigo="GAS-AUS-01", estado=EstadoPersonal.AUSENTE
    )
    usuario.motivo_ausencia = "Vacaciones"
    usuario.fecha_retorno = date(2026, 12, 1)
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"codigo_empleado": "GAS-AUS-01", "password": PASSWORD},
    )

    assert response.status_code == 403
    assert "ausencia hasta el 01/12" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_de_retirado_devuelve_403(
    client: AsyncClient, db_session: AsyncSession
):
    await _crear_usuario(
        db_session, codigo="GAS-RET-01", estado=EstadoPersonal.RETIRADO
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"codigo_empleado": "GAS-RET-01", "password": PASSWORD},
    )

    assert response.status_code == 403
    assert "dada de baja" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_de_ausente_con_password_incorrecta_sigue_siendo_401(
    client: AsyncClient, db_session: AsyncSession
):
    await _crear_usuario(
        db_session, codigo="GAS-AUS-02", estado=EstadoPersonal.AUSENTE
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"codigo_empleado": "GAS-AUS-02", "password": "incorrecta-123"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_existente_deja_de_funcionar_al_marcar_ausente(
    client: AsyncClient, db_session: AsyncSession
):
    usuario = await _crear_usuario(db_session, codigo="GAS-TOK-01")

    login = await client.post(
        "/api/v1/auth/login",
        json={"codigo_empleado": "GAS-TOK-01", "password": PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    usuario.estado = EstadoPersonal.AUSENTE
    await db_session.flush()

    perfil = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert perfil.status_code == 401


@pytest.mark.asyncio
async def test_no_puede_pasar_a_retirado_si_esta_en_cuadrilla_activa(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    usuario = await _crear_usuario(db_session, codigo="GAS-CUA-01")
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas (id, codigo_grupo, especialidad, activo)
            VALUES (901, 'Cuadrilla 901', 'Agua', true)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas_personal (cuadrilla_id, usuario_id, rol_en_cuadrilla)
            VALUES (901, :usuario_id, 'GASFITERO_APOYO')
            ON CONFLICT (cuadrilla_id, usuario_id) DO NOTHING
            """
        ),
        {"usuario_id": usuario.id},
    )
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/usuarios/{usuario.id}",
        json={"estado": "RETIRADO"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert "Cuadrilla 901" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reincorporar_limpia_motivo_y_fecha(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    usuario = await _crear_usuario(
        db_session, codigo="GAS-REI-01", estado=EstadoPersonal.AUSENTE
    )
    usuario.motivo_ausencia = "Viaje"
    usuario.fecha_retorno = date(2026, 12, 1)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/usuarios/{usuario.id}",
        json={"estado": "ACTIVO"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "ACTIVO"
    assert data["activo"] is True
    assert data["motivo_ausencia"] is None
    assert data["fecha_retorno"] is None


@pytest.mark.asyncio
async def test_ampliar_ausencia_sin_cambiar_de_estado(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    usuario = await _crear_usuario(
        db_session, codigo="GAS-AMP-01", estado=EstadoPersonal.AUSENTE
    )
    usuario.motivo_ausencia = "Viaje"
    usuario.fecha_retorno = date(2026, 12, 1)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/usuarios/{usuario.id}",
        json={"estado": "AUSENTE", "fecha_retorno": "2026-12-15"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "AUSENTE"
    assert data["motivo_ausencia"] == "Viaje"
    assert data["fecha_retorno"] == "2026-12-15"


@pytest.mark.asyncio
async def test_activo_legacy_se_traduce_a_estado(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    usuario = await _crear_usuario(db_session, codigo="GAS-LEG-01")

    response = await client.patch(
        f"/api/v1/usuarios/{usuario.id}",
        json={"activo": False},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "RETIRADO"
    assert response.json()["activo"] is False


@pytest.mark.asyncio
async def test_fecha_de_retorno_anterior_a_hoy_devuelve_422(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    usuario = await _crear_usuario(db_session, codigo="GAS-FEC-01")

    response = await client.patch(
        f"/api/v1/usuarios/{usuario.id}",
        json={"estado": "AUSENTE", "fecha_retorno": "2020-01-01"},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "anterior a hoy" in response.json()["detail"]


@pytest.mark.asyncio
async def test_supervisor_no_puede_cambiar_su_propio_estado(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    response = await client.patch(
        "/api/v1/usuarios/1",
        json={"estado": "RETIRADO"},
        headers=auth_headers,
    )

    assert response.status_code == 403
    assert "tu propio estado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dni_duplicado_devuelve_409_y_se_puede_vaciar(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    primero = await _crear_usuario(
        db_session, codigo="GAS-DNI-01", dni="12345678"
    )
    segundo = await _crear_usuario(
        db_session, codigo="GAS-DNI-02", dni="87654321"
    )
    await db_session.flush()

    duplicado = await client.patch(
        f"/api/v1/usuarios/{segundo.id}",
        json={"dni": primero.dni},
        headers=auth_headers,
    )
    assert duplicado.status_code == 409
    assert "El DNI 12345678 ya está registrado." in duplicado.json()["detail"]

    vaciado = await client.patch(
        f"/api/v1/usuarios/{segundo.id}",
        json={"dni": None},
        headers=auth_headers,
    )
    assert vaciado.status_code == 200
    assert vaciado.json()["dni"] is None


@pytest.mark.asyncio
async def test_crear_usuario_aplica_defaults_y_estado_activo(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    await _asegurar_catalogos(db_session)

    response = await client.post(
        "/api/v1/usuarios",
        json={
            "codigo_empleado": "GAS-NEW-01",
            "nombre": "Persona Nueva",
            "password": PASSWORD,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["rol"] == "GASFITERO"
    assert data["cargo"] == "GASFITERO"
    assert data["area"] == "MANTENIMIENTO"
    assert data["estado"] == "ACTIVO"
    assert data["activo"] is True


@pytest.mark.asyncio
async def test_crear_usuario_con_cargo_chofer_devuelve_422(
    client: AsyncClient, auth_headers
):
    response = await client.post(
        "/api/v1/usuarios",
        json={
            "codigo_empleado": "GAS-NEW-02",
            "nombre": "Persona Chofer",
            "password": PASSWORD,
            "cargo": "CHOFER_CAMIONETA",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
