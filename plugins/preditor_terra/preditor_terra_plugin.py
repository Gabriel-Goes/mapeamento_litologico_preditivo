# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
from pathlib import Path

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis


class PreditorTerraPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.menu_name = "Preditor Terra"
        self._module = None
        self._plugin_dir = Path(__file__).resolve().parent

    def initGui(self):
        icon = QIcon(str(self._plugin_dir / "icon.png"))
        self.action = QAction(icon, "Abrir Preditor Terra", self.iface.mainWindow())
        self.action.setObjectName("PreditorTerraAction")
        self.action.triggered.connect(self._open_preditor_terra)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu_name, self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(self.menu_name, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
        self._close_preditor_terra()

    def _log(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(str(message), "Preditor Terra", level)

    def _resolve_code_file(self):
        env_path = os.environ.get("PREDITOR_TERRA_CODE_FILE", "").strip()
        candidates = []
        if env_path:
            candidates.append(Path(env_path).expanduser())

        candidates.append((self._plugin_dir / "PreditoTerra_QGIS.py").resolve())
        repo_candidate = (self._plugin_dir.parent.parent / "codes" / "PreditoTerra_QGIS.py").resolve()
        candidates.append(repo_candidate)

        for p in candidates:
            if p.is_file():
                return p
        return None

    def _load_runtime_module(self):
        if self._module is not None:
            return self._module

        code_file = self._resolve_code_file()
        if code_file is None:
            raise RuntimeError(
                "PreditoTerra_QGIS.py não encontrado. "
                "Defina PREDITOR_TERRA_CODE_FILE ou mantenha o repositório com a pasta codes/."
            )

        runtime_dir = str(code_file.parent)
        if runtime_dir not in sys.path:
            sys.path.insert(0, runtime_dir)

        spec = importlib.util.spec_from_file_location("preditor_terra_runtime", str(code_file))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Falha ao carregar módulo do arquivo: {code_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module = module
        self._log(f"Runtime carregado: {code_file}")
        return module

    def _open_preditor_terra(self):
        try:
            module = self._load_runtime_module()
            if hasattr(module, "open_preditor_terra_dock"):
                module.open_preditor_terra_dock(self.iface)
            elif hasattr(module, "_open_preditor_terra_dock"):
                module._open_preditor_terra_dock()
            else:
                raise RuntimeError("Módulo sem função para abrir o dock.")
        except Exception as e:
            self._log(f"Erro abrindo Preditor Terra: {e}", Qgis.Critical)
            self.iface.messageBar().pushCritical("Preditor Terra", str(e))

    def _close_preditor_terra(self):
        try:
            if self._module is not None and hasattr(self._module, "close_preditor_terra_dock"):
                self._module.close_preditor_terra_dock(self.iface)
        except Exception:
            pass
