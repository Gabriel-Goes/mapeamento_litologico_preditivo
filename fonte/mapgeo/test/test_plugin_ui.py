import sys
import types
import unittest
from unittest.mock import MagicMock

# Create minimal qgis stubs so mapgeo can be imported without QGIS
qgis_module = types.ModuleType('qgis')
pyqt_module = types.ModuleType('qgis.PyQt')
qtcore_module = types.ModuleType('qgis.PyQt.QtCore')
qtcore_module.QSettings = MagicMock()
qtcore_module.QTranslator = MagicMock()
qtcore_module.QCoreApplication = MagicMock()
qtgui_module = types.ModuleType('qgis.PyQt.QtGui')
qtgui_module.QIcon = MagicMock()
qtwidgets_module = types.ModuleType('qgis.PyQt.QtWidgets')
qtwidgets_module.QAction = MagicMock()

sys.modules.setdefault('qgis', qgis_module)
sys.modules.setdefault('qgis.PyQt', pyqt_module)
sys.modules.setdefault('qgis.PyQt.QtCore', qtcore_module)
sys.modules.setdefault('qgis.PyQt.QtGui', qtgui_module)
sys.modules.setdefault('qgis.PyQt.QtWidgets', qtwidgets_module)

# Stub the dialog used by the plugin
dialog_module = types.ModuleType('mapgeo.mapgeo_dialog')
class DummyDialog:
    def __init__(self, iface):
        self.iface = iface
        self.show = MagicMock()

dialog_module.mapgeoDialog = DummyDialog
sys.modules['mapgeo.mapgeo_dialog'] = dialog_module

from mapgeo.mapgeo import mapgeo

class DummyIface:
    def addToolBarIcon(self, action):
        pass
    def removeToolBarIcon(self, action):
        pass
    def addPluginToDatabaseMenu(self, menu, action):
        pass
    def removePluginDatabaseMenu(self, menu, action):
        pass
    def mainWindow(self):
        return None

class PluginRunTest(unittest.TestCase):
    def test_run_initializes_dialog_and_shows_it(self):
        iface = DummyIface()
        plugin = mapgeo(iface)
        plugin.first_start = True
        plugin.dlg = None
        plugin.run()
        self.assertIsNotNone(plugin.dlg)
        plugin.dlg.show.assert_called_once()
        # running again should reuse same dialog
        plugin.dlg.show.reset_mock()
        plugin.run()
        plugin.dlg.show.assert_called_once()

if __name__ == '__main__':
    unittest.main()
