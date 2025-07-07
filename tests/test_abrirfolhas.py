import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fonte", "mapgeo"))
sys.modules.setdefault("pygmt", types.ModuleType("pygmt"))
import geopandas as gpd

gpd.read_file = lambda *args, **kwargs: types.SimpleNamespace(unary_union=None)
from nucleo.abrirfolhas import AbrirFolhas, AttribDict


class AbrirFolhasInvalidDBURLTest(unittest.TestCase):
    def test_invalid_db_url(self):
        abrir = AbrirFolhas(gdb_url="invalid://url")
        self.assertIsNone(abrir.engine)
        self.assertIsNone(abrir.session)
        self.assertIsInstance(abrir.dic_folhas, AttribDict)


if __name__ == "__main__":
    unittest.main()
