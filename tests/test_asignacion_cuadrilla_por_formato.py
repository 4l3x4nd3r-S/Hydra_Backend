import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.orden_servicio_service import (
    ESPECIALIDAD_POR_FORMATO_RECLAMO,
    OrdenServicioService,
)


class AsignacionCuadrillaPorFormatoTest(unittest.TestCase):
    def test_anexo_6_requiere_desague(self):
        self.assertEqual(
            ESPECIALIDAD_POR_FORMATO_RECLAMO["Anexo 6"],
            "Desagüe",
        )

    def test_formato_1_requiere_agua(self):
        self.assertEqual(
            ESPECIALIDAD_POR_FORMATO_RECLAMO["Formato 1"],
            "Agua",
        )


class ValidacionCuadrillaPorFormatoTest(unittest.IsolatedAsyncioTestCase):
    async def test_rechaza_cuadrilla_de_agua_para_anexo_6(self):
        resultado = MagicMock()
        resultado.scalars.return_value.first.return_value = SimpleNamespace(
            especialidad="Agua"
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=resultado)

        servicio = OrdenServicioService(db)

        with self.assertRaisesRegex(ValueError, "solo pueden.*Desagüe"):
            await servicio._validar_cuadrilla_compatible(1, "Anexo 6")

    async def test_admite_cuadrilla_de_agua_para_formato_1(self):
        resultado = MagicMock()
        resultado.scalars.return_value.first.return_value = SimpleNamespace(
            especialidad="Agua"
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=resultado)

        servicio = OrdenServicioService(db)

        await servicio._validar_cuadrilla_compatible(1, "Formato 1")


if __name__ == "__main__":
    unittest.main()
