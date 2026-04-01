# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
from qgis.PyQt import QtCore, QtWidgets
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsColorRampShader,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
    QgsTask,
)

from .mcda_engine import McdaResult, list_available_folhas, run_mcda_from_gpkg


class PreditorTerritorialMvpDock(QtWidgets.QDockWidget):
    def __init__(self, iface, plugin_dir: Path):
        super().__init__("Preditor Territorial MVP")
        self.iface = iface
        self._plugin_dir = Path(plugin_dir)
        self._gpkg_path = self._plugin_dir / "data" / "gamba_mvp.gpkg"
        self._task = None

        self.setObjectName("PreditorTerritorialMvpDock")
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        self._build_ui()
        self._load_folhas()

    def _build_ui(self):
        root = QtWidgets.QWidget(self)
        self.setWidget(root)
        layout = QtWidgets.QVBoxLayout(root)

        self.lbl_data = QtWidgets.QLabel(f"GPKG interno: {self._gpkg_path}")
        self.lbl_data.setWordWrap(True)
        layout.addWidget(self.lbl_data)

        form = QtWidgets.QFormLayout()

        self.cb_folha = QtWidgets.QComboBox()
        form.addRow("Folha", self.cb_folha)

        self.sb_pixel = QtWidgets.QSpinBox()
        self.sb_pixel.setRange(50, 1000)
        self.sb_pixel.setSingleStep(50)
        self.sb_pixel.setValue(200)
        form.addRow("Pixel (m)", self.sb_pixel)

        self.dsb_low = QtWidgets.QDoubleSpinBox()
        self.dsb_low.setRange(0.0, 1.0)
        self.dsb_low.setDecimals(2)
        self.dsb_low.setSingleStep(0.05)
        self.dsb_low.setValue(0.40)
        form.addRow("Limiar medio", self.dsb_low)

        self.dsb_high = QtWidgets.QDoubleSpinBox()
        self.dsb_high.setRange(0.0, 1.0)
        self.dsb_high.setDecimals(2)
        self.dsb_high.setSingleStep(0.05)
        self.dsb_high.setValue(0.70)
        form.addRow("Limiar alto", self.dsb_high)

        layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("Gerar mapas territoriais")
        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.setEnabled(False)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log_box = QtWidgets.QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(180)
        layout.addWidget(self.log_box)

        self.btn_run.clicked.connect(self._run_mcda)
        self.btn_cancel.clicked.connect(self._cancel_task)

    def _log(self, msg: str):
        stamp = datetime.utcnow().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{stamp}] {msg}")

    def _warn(self, msg: str):
        self._log(f"WARN: {msg}")
        self.iface.messageBar().pushWarning("Preditor Territorial MVP", str(msg))

    def _info(self, msg: str):
        self._log(msg)
        self.iface.messageBar().pushInfo("Preditor Territorial MVP", str(msg))

    def _load_folhas(self):
        self.cb_folha.clear()
        if not self._gpkg_path.is_file():
            self._warn(f"Arquivo de dados nao encontrado: {self._gpkg_path}")
            self.btn_run.setEnabled(False)
            return

        try:
            folhas = list_available_folhas(self._gpkg_path)
        except Exception as exc:
            self._warn(f"Falha ao carregar folhas: {exc}")
            self.btn_run.setEnabled(False)
            return

        if not folhas:
            self._warn("Nenhuma folha encontrada em mc_100k.")
            self.btn_run.setEnabled(False)
            return

        self.cb_folha.addItems(folhas)
        default_idx = self.cb_folha.findText("SB21_ZA_II")
        if default_idx >= 0:
            self.cb_folha.setCurrentIndex(default_idx)

        self.btn_run.setEnabled(True)
        self._log(f"Folhas disponiveis: {len(folhas)}")

    def _set_running(self, running: bool):
        self.btn_run.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        if not running:
            self.progress.setValue(0)

    def _run_mcda(self):
        if self._task is not None:
            self._warn("Ja existe uma operacao em andamento.")
            return

        folha = self.cb_folha.currentText().strip()
        if not folha:
            self._warn("Selecione uma folha valida.")
            return

        low = float(self.dsb_low.value())
        high = float(self.dsb_high.value())
        if high <= low:
            self._warn("Limiar alto deve ser maior que limiar medio.")
            return

        pixel = int(self.sb_pixel.value())
        self._set_running(True)
        self._log(
            f"Iniciando MCDA | folha={folha} pixel={pixel}m low={low:.2f} high={high:.2f}"
        )

        def _worker(task):
            return run_mcda_from_gpkg(
                gpkg_path=self._gpkg_path,
                folha_codigo=folha,
                pixel_size_m=pixel,
                low_threshold=low,
                high_threshold=high,
                progress_cb=lambda p, _m: task.setProgress(float(p)),
            )

        def _finished(exception, result):
            self._task = None
            self._set_running(False)
            try:
                self.iface.statusBarIface().clearMessage()
            except Exception:
                pass

            if exception is not None:
                msg = str(exception)
                if "cancel" in msg.lower():
                    self._warn("Operacao cancelada pelo usuario.")
                else:
                    self._warn(f"Falha no processamento: {msg}")
                return

            try:
                paths = self._write_outputs(result)
                self._add_layers(paths)
                self._info("MCDA concluido com sucesso.")
                self._log("Arquivos gerados:")
                for key, path in paths.items():
                    self._log(f"  - {key}: {path}")
            except Exception as exc:
                self._warn(f"Falha ao materializar saidas: {exc}")

        self._task = QgsTask.fromFunction(
            "Preditor Territorial MVP - MCDA",
            _worker,
            on_finished=_finished,
            flags=QgsTask.CanCancel,
        )
        self._task.progressChanged.connect(self._on_progress)
        QgsApplication.taskManager().addTask(self._task)

    def _on_progress(self, value: float):
        pct = int(max(0, min(100, round(float(value)))))
        self.progress.setValue(pct)
        try:
            self.iface.statusBarIface().showMessage(f"Preditor Territorial MVP: {pct}%")
        except Exception:
            pass

    def _cancel_task(self):
        if self._task is None:
            return
        self._task.cancel()
        self._warn("Pedido de cancelamento enviado.")

    def _write_outputs(self, result: McdaResult) -> dict[str, str]:
        out_dir = Path(tempfile.gettempdir()) / "preditor_territorial_mvp"
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        folha = result.folha_codigo

        pot_path = out_dir / f"PT_POTENCIAL_{folha}_{ts}.tif"
        res_path = out_dir / f"PT_RESTRICOES_{folha}_{ts}.tif"
        pri_path = out_dir / f"PT_PRIORIDADE_{folha}_{ts}.tif"
        rep_path = out_dir / f"PT_RELATORIO_{folha}_{ts}.json"

        self._write_raster(
            pot_path,
            result.potential,
            result.epsg,
            result.geotransform,
            nodata=-9999.0,
            gdal_type=gdal.GDT_Float32,
        )
        self._write_raster(
            res_path,
            result.restriction,
            result.epsg,
            result.geotransform,
            nodata=0,
            gdal_type=gdal.GDT_Byte,
        )
        self._write_raster(
            pri_path,
            result.priority,
            result.epsg,
            result.geotransform,
            nodata=0,
            gdal_type=gdal.GDT_Byte,
        )

        with rep_path.open("w", encoding="utf-8") as f:
            json.dump(result.metadata, f, ensure_ascii=False, indent=2)

        return {
            "potencial": str(pot_path),
            "restricoes": str(res_path),
            "prioridade": str(pri_path),
            "relatorio": str(rep_path),
        }

    def _write_raster(
        self,
        path: Path,
        arr: np.ndarray,
        epsg: int,
        geotransform: tuple[float, float, float, float, float, float],
        nodata: float | int,
        gdal_type,
    ):
        data = np.asarray(arr)
        ny, nx = data.shape

        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(
            str(path),
            int(nx),
            int(ny),
            1,
            gdal_type,
            options=["COMPRESS=LZW", "PREDICTOR=2"],
        )
        if ds is None:
            raise RuntimeError(f"Falha ao criar raster: {path}")

        ds.SetGeoTransform(tuple(float(v) for v in geotransform))

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg))
        ds.SetProjection(srs.ExportToWkt())

        band = ds.GetRasterBand(1)
        band.SetNoDataValue(float(nodata))

        to_write = data.copy()
        if np.issubdtype(to_write.dtype, np.floating):
            to_write = np.where(np.isfinite(to_write), to_write, float(nodata))

        band.WriteArray(to_write)
        band.FlushCache()
        ds = None

    def _add_layers(self, paths: dict[str, str]):
        group = self._ensure_group("Preditor Territorial MVP/Planejamento Territorial")

        lyr_pot = self._add_raster(paths["potencial"], "PT_POTENCIAL", group)
        self._style_potential(lyr_pot)

        lyr_res = self._add_raster(paths["restricoes"], "PT_RESTRICOES", group)
        self._style_restriction(lyr_res)

        lyr_pri = self._add_raster(paths["prioridade"], "PT_PRIORIDADE", group)
        self._style_priority(lyr_pri)

    def _ensure_group(self, group_path: str):
        root = QgsProject.instance().layerTreeRoot()
        node = root
        for part in [p for p in str(group_path).split("/") if p]:
            found = node.findGroup(part)
            node = found if found is not None else node.addGroup(part)
        return node

    def _add_raster(self, path: str, name: str, group_node):
        layer = QgsRasterLayer(str(path), str(name))
        if not layer.isValid():
            raise RuntimeError(f"Camada raster invalida: {path}")
        QgsProject.instance().addMapLayer(layer, False)
        group_node.addLayer(layer)
        return layer

    def _apply_shader(self, layer: QgsRasterLayer, items, discrete: bool = False):
        shader = QgsColorRampShader()
        shader.setColorRampType(
            QgsColorRampShader.Discrete if discrete else QgsColorRampShader.Interpolated
        )
        shader.setColorRampItemList(items)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(shader)

        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, raster_shader)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def _style_potential(self, layer: QgsRasterLayer):
        items = [
            QgsColorRampShader.ColorRampItem(0.00, QColor("#440154"), "0.00"),
            QgsColorRampShader.ColorRampItem(0.40, QColor("#3b528b"), "0.40"),
            QgsColorRampShader.ColorRampItem(0.70, QColor("#5ec962"), "0.70"),
            QgsColorRampShader.ColorRampItem(1.00, QColor("#fde725"), "1.00"),
        ]
        self._apply_shader(layer, items, discrete=False)

    def _style_restriction(self, layer: QgsRasterLayer):
        items = [
            QgsColorRampShader.ColorRampItem(0, QColor(220, 220, 220, 20), "Sem restricao"),
            QgsColorRampShader.ColorRampItem(1, QColor("#d73027"), "Restricao"),
        ]
        self._apply_shader(layer, items, discrete=True)

    def _style_priority(self, layer: QgsRasterLayer):
        items = [
            QgsColorRampShader.ColorRampItem(1, QColor("#7f7f7f"), "Restrita"),
            QgsColorRampShader.ColorRampItem(2, QColor("#fee08b"), "Baixa"),
            QgsColorRampShader.ColorRampItem(3, QColor("#fdae61"), "Media"),
            QgsColorRampShader.ColorRampItem(4, QColor("#1a9850"), "Alta"),
        ]
        self._apply_shader(layer, items, discrete=True)
