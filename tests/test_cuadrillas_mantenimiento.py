import unittest
from unittest.mock import AsyncMock, MagicMock

from pydantic import ValidationError

from app.models.cuadrilla import (
    Cuadrilla,
    CuadrillaPersonal,
    RolEnCuadrilla,
    formatear_codigo_cuadrilla,
)
from app.models.usuario import AreaUsuario, CargoUsuario, RolUsuario, Usuario
from app.routers.supervisor import _tecnico_response
from app.schemas.cuadrilla import CrearCuadrillaRequest, PersonalRequest
from app.services.catalogo_service import GRUPO_ESPECIALIDAD, validar_codigo_catalogo


class CuadrillasMantenimientoTest(unittest.TestCase):
    def test_respuesta_de_personal_incluye_funcion_y_cuadrilla(self):
        usuario = Usuario(
            id=10,
            codigo_empleado="GAS010",
            nombre="Gasfitero Apoyo",
            password_hash="hash",
            rol=RolUsuario.GASFITERO,
            cargo=CargoUsuario.GASFITERO,
            area=AreaUsuario.MANTENIMIENTO,
            dni="71234567",
            celular="912345678",
        )
        cuadrilla = Cuadrilla(
            id=3,
            codigo_grupo="Cuadrilla 003",
            especialidad="Agua",
        )
        pertenencia = CuadrillaPersonal(
            usuario=usuario,
            cuadrilla=cuadrilla,
            rol_en_cuadrilla=RolEnCuadrilla.GASFITERO_APOYO,
        )
        usuario.cuadrillas = [pertenencia]

        response = _tecnico_response(
            usuario,
            {"GASFITERO_APOYO": "Gasfitero de apoyo"},
            {"MANTENIMIENTO": "Mantenimiento"},
            {"GASFITERO": "Gasfitero"},
        )

        self.assertEqual(response.funcion_visible, "Gasfitero de apoyo")
        self.assertEqual(response.dni, "71234567")
        self.assertEqual(response.celular, "912345678")
        self.assertFalse(response.es_principal)
        self.assertEqual(response.rol_en_cuadrilla, "GASFITERO_APOYO")
        self.assertEqual(response.cuadrilla_id, 3)
        self.assertEqual(response.codigo_cuadrilla, "Cuadrilla 003")
        self.assertTrue(response.puede_ser_gasfitero)
        self.assertFalse(response.puede_ser_chofer)

    def test_chofer_sin_cuadrilla_conserva_su_unica_funcion(self):
        usuario = Usuario(
            id=20,
            codigo_empleado="CHO020",
            nombre="Personal Chofer",
            password_hash="hash",
            rol=RolUsuario.GASFITERO,
            cargo=CargoUsuario.CHOFER_CAMIONETA,
            area=AreaUsuario.MANTENIMIENTO,
        )
        usuario.cuadrillas = []

        response = _tecnico_response(
            usuario,
            {"CHOFER": "Chofer"},
            {"MANTENIMIENTO": "Mantenimiento"},
            {"CHOFER_CAMIONETA": "Chofer"},
        )

        self.assertEqual(response.funcion_visible, "Chofer")
        self.assertTrue(response.puede_ser_chofer)
        self.assertFalse(response.puede_ser_gasfitero)
        self.assertIsNone(response.cuadrilla_id)

    def test_identificador_de_cuadrilla_es_automatico_y_uniforme(self):
        self.assertEqual(formatear_codigo_cuadrilla(1), "Cuadrilla 001")
        self.assertEqual(formatear_codigo_cuadrilla(27), "Cuadrilla 027")
        self.assertEqual(formatear_codigo_cuadrilla(1000), "Cuadrilla 1000")

    def test_area_usuario_solo_mantenimiento(self):
        self.assertEqual(list(AreaUsuario), [AreaUsuario.MANTENIMIENTO])

    def test_personal_requiere_dos_integrantes_distintos(self):
        with self.assertRaisesRegex(ValidationError, "al menos 2 integrantes"):
            PersonalRequest(lider_id=1, apoyos_ids=[1])

    def test_cuadrilla_admite_solo_especialidades_operativas(self):
        for especialidad in ("Agua", "Alcantarillado"):
            with self.subTest(especialidad=especialidad):
                payload = CrearCuadrillaRequest(
                    especialidad=especialidad,
                    personal={"lider_id": 1, "apoyos_ids": [2]},
                )

                self.assertEqual(payload.especialidad, especialidad)
                self.assertEqual(
                    len({payload.personal.lider_id, *payload.personal.apoyos_ids}),
                    2,
                )

    def test_cuadrilla_rechaza_el_rol_operador(self):
        with self.assertRaisesRegex(ValidationError, "Extra inputs are not permitted"):
            CrearCuadrillaRequest(
                especialidad="Alcantarillado",
                personal={"lider_id": 1, "apoyos_ids": [2], "operador_id": 3},
            )


class CuadrillaCatalogoTest(unittest.IsolatedAsyncioTestCase):
    async def test_rechaza_especialidad_ausente_del_catalogo(self):
        resultado = MagicMock()
        resultado.scalar_one_or_none.return_value = None
        db = MagicMock()
        db.execute = AsyncMock(return_value=resultado)

        with self.assertRaisesRegex(ValueError, "Opción no válida"):
            await validar_codigo_catalogo(db, GRUPO_ESPECIALIDAD, "Distribución")


if __name__ == "__main__":
    unittest.main()
