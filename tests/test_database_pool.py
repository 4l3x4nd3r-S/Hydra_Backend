import unittest

from app.core.database import engine


class DatabasePoolTest(unittest.TestCase):
    def test_pool_valida_conexiones_antes_de_reutilizarlas(self):
        self.assertTrue(engine.pool._pre_ping)

    def test_pool_recicla_conexiones_inactivas(self):
        self.assertEqual(engine.pool._recycle, 300)


if __name__ == "__main__":
    unittest.main()
