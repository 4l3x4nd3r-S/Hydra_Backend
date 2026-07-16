import unittest

from pydantic import ValidationError

from app.schemas.reclamo import ActualizarReclamoRequest, CrearReclamoRequest


DATOS_BASE = {
    "codigo_solicitud": "12345",
    "canal_entrada": "Presencial",
    "descripcion": "Descripción de prueba",
    "nombre_solicitante": "Usuario Prueba",
    "direccion": "Dirección de prueba",
    "telefono": "987654321",
    "email": "usuario@prueba.com",
    "numero_medidor": "1234567",
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

    def test_numero_medidor_requiere_siete_digitos_no_nulos(self):
        for numero in ("123456", "12345678", "123A567", "0000000"):
            with self.subTest(numero=numero), self.assertRaises(ValidationError):
                CrearReclamoRequest(
                    **{**DATOS_BASE, "numero_medidor": numero},
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

    def test_anexo_6_admite_op_y_rechaza_formato_1(self):
        payload = CrearReclamoRequest(
            **DATOS_BASE, formato="Anexo 6", tipo_problema="OP-1"
        )
        self.assertEqual(payload.tipo_problema, "OP-1")

        with self.assertRaisesRegex(ValidationError, "no corresponde"):
            CrearReclamoRequest(
                **DATOS_BASE, formato="Anexo 6", tipo_problema="B1"
            )

    def test_formato_1_admite_catalogo_nuevo_y_rechaza_op(self):
        payload = CrearReclamoRequest(
            **DATOS_BASE,
            formato="Formato 1",
            tipo_problema="REPOSICIÓN DE TUBERIA DE CONCRETO A PVC - DESAGÜE",
        )
        self.assertIn("DESAGÜE", payload.tipo_problema)

        with self.assertRaisesRegex(ValidationError, "no corresponde"):
            CrearReclamoRequest(
                **DATOS_BASE, formato="Formato 1", tipo_problema="OP-1"
            )


if __name__ == "__main__":
    unittest.main()
