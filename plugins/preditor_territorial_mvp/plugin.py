# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from qgis.PyQt import QtCore
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis

from .dock import PreditorTerritorialMvpDock


class PreditorTerritorialMvpPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.menu_name = "Preditor Territorial MVP"
        self._dock = None
        self._plugin_dir = Path(__file__).resolve().parent

    def initGui(self):
        icon = QIcon(str(self._plugin_dir / "icon.png"))
        self.action = QAction(icon, "Abrir Preditor Territorial MVP", self.iface.mainWindow())
        self.action.setObjectName("PreditorTerritorialMvpAction")
        self.action.triggered.connect(self._open_dock)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu_name, self.action)

    def unload(self):
        if self._dock is not None:
            try:
                self.iface.removeDockWidget(self._dock)
            except Exception:
                pass
            self._dock.deleteLater()
            self._dock = None

        if self.action is not None:
            self.iface.removePluginMenu(self.menu_name, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def _open_dock(self):
        if self._dock is None:
            self._dock = PreditorTerritorialMvpDock(self.iface, self._plugin_dir)
            self.iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._dock)
        self._dock.show()
        self._dock.raise_()


def log_info(msg: str) -> None:
    QgsMessageLog.logMessage(str(msg), "Preditor Territorial MVP", Qgis.Info)
