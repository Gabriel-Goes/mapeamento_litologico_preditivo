import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from .resources import *
from .mapgeo_dialog import mapgeoDialog

import logging
logger = logging.getLogger('mapgeo')
# file log
logging.basicConfig(filename='~/mapgeo.log', level=logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
file_handler = logging.FileHandler('mapgeo.log')


class mapgeo:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&Mapeamento Geológico')
        self.first_start = None
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'mapgeo_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        logger.info("mapgeo plugin initialized")

    def tr(self, message):
        """Tradução."""
        return QCoreApplication.translate('mapgeo', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ) -> QAction:
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(self.menu, action)

        self.actions.append(action)
        logger.debug(f"Action '{text}' added to the menu and toolbar.")
        return action

    def initGui(self):
        """Inicializa a interface gráfica do plugin."""
        icon_path = ':/plugins/mapgeo/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Mapeamento Geológico'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        self.first_start = True
        logger.info("mapgeo plugin GUI initialized.")

    def unload(self):
        """Remove o plugin do QGIS."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu(self.tr(u'&Mapeamento Geológico'), action)
            self.iface.removeToolBarIcon(action)
        logger.info("mapgeo plugin unloaded.")

    def run(self):
        """Executa o diálogo do plugin."""
        if self.first_start:
            self.first_start = False
            self.dlg = mapgeoDialog(self.iface)
            logger.info("Dialog initialized.")

        # Verifica se o diálogo foi carregado corretamente
        if self.dlg is not None:
            logger.debug("Displaying the dialog.")
            self.dlg.show()
        else:
            logger.error("Failed to load the dialog.")

        # Executa o loop de eventos do diálogo
        result = self.dlg.exec_()

        if result:
            logger.info("Dialog executed successfully.")
        else:
            logger.warning("Dialog execution was canceled or failed.")
