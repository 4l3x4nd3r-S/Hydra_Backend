import unittest
from types import SimpleNamespace

from app.models.cuadrilla import RolEnCuadrilla
from app.services.orden_servicio_snapshot import cuadrilla_para_respuesta


def _cuadrilla(nombre_grupo: str, lider_id: int, lider_nombre: str):
    usuario = SimpleNamespace(
        id=lider_id,
        nombre=lider_nombre,
        codigo_empleado=f"EMP-{lider_id}",
    )
    integrante = SimpleNamespace(
        usuario=usuario,
        rol_en_cuadrilla=RolEnCuadrilla.GASFITERO_PRINCIPAL,
    )
    return SimpleNamespace(
        id=1,
        codigo_grupo=nombre_grupo,
        especialidad="Agua",
        personal=[integrante],
    )


class OrdenServicioSnapshotTest(unittest.TestCase):
    def test_os_activa_refleja_los_datos_actuales_de_la_cuadrilla(self):
        orden = SimpleNamespace(
            estado_orden="EN_PROCESO",
            cuadrilla_snapshot=None,
            cuadrilla=_cuadrilla("Grupo actualizado", 2, "Líder nuevo"),
        )

        cuadrilla = cuadrilla_para_respuesta(orden)

        self.assertEqual(cuadrilla["codigo_grupo"], "Grupo actualizado")
        self.assertEqual(cuadrilla["lider"]["nombre"], "Líder nuevo")

    def test_os_archivada_conserva_nombre_y_lider_historicos(self):
        historica = {
            "id": 1,
            "codigo_grupo": "Grupo original",
            "especialidad": "Agua",
            "lider": {
                "id": 1,
                "nombre": "Líder original",
                "codigo_empleado": "EMP-1",
                "rol_en_cuadrilla": "LIDER",
            },
            "apoyos": [],
            "chofer": None,
        }
        orden = SimpleNamespace(
            estado_orden="COMPLETADO",
            cuadrilla_snapshot=historica,
            cuadrilla=_cuadrilla("Grupo actualizado", 2, "Líder nuevo"),
        )

        cuadrilla = cuadrilla_para_respuesta(orden)

        self.assertEqual(cuadrilla["codigo_grupo"], "Grupo original")
        self.assertEqual(cuadrilla["lider"]["nombre"], "Líder original")


if __name__ == "__main__":
    unittest.main()
