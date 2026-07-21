import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.orden_servicio_service import OrdenServicioService


class ValidacionCuadrillaPorFormatoTest(unittest.IsolatedAsyncioTestCase):
    async def test_rechaza_cuadrilla_de_agua_para_anexo_6(self):
        resultado = MagicMock()
        resultado.scalars.return_value.first.return_value = SimpleNamespace(
            especialidad="Agua"
        )
        db = MagicMock()
        catalogo = MagicMock()
        catalogo.scalar_one_or_none.return_value = "Alcantarillado"
        db.execute = AsyncMock(side_effect=[resultado, catalogo])

        servicio = OrdenServicioService(db)

        with self.assertRaisesRegex(ValueError, "solo pueden.*Alcantarillado"):
            await servicio._validar_cuadrilla_compatible(1, "Anexo 6")

    async def test_admite_cuadrilla_de_agua_para_formato_1(self):
        resultado = MagicMock()
        resultado.scalars.return_value.first.return_value = SimpleNamespace(
            especialidad="Agua"
        )
        db = MagicMock()
        catalogo = MagicMock()
        catalogo.scalar_one_or_none.return_value = "Agua"
        db.execute = AsyncMock(side_effect=[resultado, catalogo])

        servicio = OrdenServicioService(db)

        await servicio._validar_cuadrilla_compatible(1, "Formato 1")


if __name__ == "__main__":
    unittest.main()
