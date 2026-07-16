import unittest

from pydantic import ValidationError

from app.models.cuadrilla import formatear_codigo_cuadrilla
from app.models.usuario import AreaUsuario
from app.schemas.cuadrilla import CrearCuadrillaRequest, PersonalRequest


class CuadrillasMantenimientoTest(unittest.TestCase):
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
        for especialidad in ("Agua", "Desagüe"):
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

    def test_cuadrilla_rechaza_especialidad_fuera_de_agua_desague(self):
        with self.assertRaises(ValidationError):
            CrearCuadrillaRequest(
                especialidad="Distribución",
                personal={"lider_id": 1, "apoyos_ids": [2]},
            )

    def test_cuadrilla_rechaza_roles_de_otro_tipo(self):
        with self.assertRaisesRegex(ValidationError, "Agua no admiten el rol Chofer"):
            CrearCuadrillaRequest(
                especialidad="Agua",
                personal={"lider_id": 1, "apoyos_ids": [2], "chofer_id": 3},
            )

        with self.assertRaisesRegex(ValidationError, "Desagüe no admiten el rol Operador"):
            CrearCuadrillaRequest(
                especialidad="Desagüe",
                personal={"lider_id": 1, "apoyos_ids": [2], "operador_id": 3},
            )


if __name__ == "__main__":
    unittest.main()
