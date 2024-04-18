import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtCore import QSettings, QTranslator
from .preditor_terra_dialog import PreditorTerraDialog


class PreditorTerra:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = None

        # Internacionalização
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', f'PreditorTerra_{locale}.qm')
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        # Cria uma ação que iniciará a configuração do plugin
        icon = QIcon(':/plugins/preditor_terra/icon.png')
        self.action = QAction(icon, "Preditor Terra", self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        # Adiciona a ação ao menu e à barra de ferramentas
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Preditor Terra", self.action)

    def unload(self):
        # Remove o ícone e o menu do plugin no QGIS
        self.iface.removePluginMenu("&Preditor Terra", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        # Cria o diálogo (se não estiver criado) e exibe
        if not self.dlg:
            self.dlg = PreditorTerraDialog()

        # Exibe o diálogo
        self.dlg.show()

        # Executa o diálogo e verifica se o usuário clicou em OK
        result = self.dlg.exec_()
        if result:
            # Implemente aqui a lógica para fazer algo com a entrada do usuário
            pass
