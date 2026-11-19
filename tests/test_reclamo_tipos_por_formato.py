import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pydantic import ValidationError

from app.schemas.reclamo import ActualizarReclamoRequest, CrearReclamoRequest
from app.services.catalogo_service import validar_reclamo_catalogo


DATOS_BASE = {
    "codigo_solicitud": "12345",
    "canal_entrada": "Presencial",
    "descripcion": "Descripción de prueba",
    "nombre_solicitante": "Usuario Prueba",
    "direccion": "Dirección de prueba",
    "telefono": "987654321",
    "email": "usuario@prueba.com",
    "numero_suministro": "1234567",
}


class ReclamoTiposPorFormatoTest(unittest.TestCase):
    def test_codigo_solicitud_requiere_cinco_digitos_no_nulos(self):
        for codigo in ("1234", "123456", "12A45", "00000"):
            with self.subTest(codigo=codigo), self.assertRaises(ValidationError):
                CrearReclamoRequest(
                    **{**DATOS_BASE, "codigo_solicitud": codigo},
                    formato="Anexo 6",
                    tipo_problema="OP-1",
                )

    def test_descripcion_es_opcional(self):
        sin_descripcion = {k: v for k, v in DATOS_BASE.items() if k != "descripcion"}
        for extra in ({}, {"descripcion": None}, {"descripcion": ""}, {"descripcion": "   "}):
            with self.subTest(extra=extra):
                reclamo = CrearReclamoRequest(
                    **sin_descripcion, **extra, formato="Anexo 6", tipo_problema="OP-1"
                )
                self.assertIsNone(reclamo.descripcion)

    def test_descripcion_se_recorta_y_vaciarla_en_actualizacion_la_deja_nula(self):
        reclamo = CrearReclamoRequest(
            **{**DATOS_BASE, "descripcion": "  Fuga en vereda  "},
            formato="Anexo 6",
            tipo_problema="OP-1",
        )
        self.assertEqual(reclamo.descripcion, "Fuga en vereda")
        cambio = ActualizarReclamoRequest(descripcion="")
        self.assertIsNone(cambio.descripcion)
        self.assertIn("descripcion", cambio.model_dump(exclude_unset=True))

    def test_numero_suministro_requiere_siete_digitos_no_nulos(self):
        for numero in ("123456", "12345678", "123A567", "0000000"):
            with self.subTest(numero=numero), self.assertRaises(ValidationError):
                CrearReclamoRequest(
                    **{**DATOS_BASE, "numero_suministro": numero},
                    formato="Anexo 6",
                    tipo_problema="OP-1",
                )

    def test_telefono_requiere_nueve_digitos_y_empezar_con_nueve(self):
        for telefono in ("876543210", "98765432", "9876543210", "9A7654321"):
            with self.subTest(telefono=telefono), self.assertRaises(ValidationError):
                CrearReclamoRequest(
                    **{**DATOS_BASE, "telefono": telefono},
                    formato="Anexo 6",
                    tipo_problema="OP-1",
                )

        payload = CrearReclamoRequest(
            **DATOS_BASE,
            formato="Anexo 6",
            tipo_problema="OP-1",
        )
        self.assertEqual(payload.telefono, "987654321")

    def test_actualizacion_de_telefono_tambien_debe_empezar_con_nueve(self):
        with self.assertRaises(ValidationError):
            ActualizarReclamoRequest(telefono="876543210")

        payload = ActualizarReclamoRequest(telefono="912345678")
        self.assertEqual(payload.telefono, "912345678")



class ReclamoCatalogoTest(unittest.IsolatedAsyncioTestCase):
    async def test_tipo_de_problema_debe_corresponder_al_formato(self):
        opciones = [
            SimpleNamespace(grupo="FORMATO_RECLAMO", codigo="Anexo 6"),
            SimpleNamespace(grupo="CANAL_RECLAMO", codigo="Presencial"),
            SimpleNamespace(
                grupo="TIPO_PROBLEMA",
                codigo="B1",
                padre_codigo="Formato 1",
            ),
            SimpleNamespace(grupo="ESTADO_RECLAMO", codigo="PENDIENTE"),
        ]
        resultado = MagicMock()
        resultado.scalars.return_value.all.return_value = opciones
        db = MagicMock()
        db.execute = AsyncMock(return_value=resultado)

        with self.assertRaisesRegex(ValueError, "no corresponde"):
            await validar_reclamo_catalogo(
                db,
                formato="Anexo 6",
                canal="Presencial",
                tipo_problema="B1",
                estado="PENDIENTE",
            )


if __name__ == "__main__":
    unittest.main()
