import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsGeometry, QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant

from .databaseengine import DatabaseEngine
from .resources import reverse_meta_cartas

import logging
logger = logging.getLogger('mapgeo')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logger.propagate = False
logger.debug("Logger inicializado.")

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'mapgeo_dialog_base.ui'))


class mapgeoDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(mapgeoDialog, self).__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.selectGeometryButton.clicked.connect(self.select_geometry)
        self.runButton.clicked.connect(self.find_intersecting_maps)
        self.db_session = None
        self.selected_geometry = None

        try:
            self.scaleComboBox.addItems(['1:1.000.000', '1:500.000', '1:250.000', '1:100.000', '1:50.000', '1:25.000'])
            self.db_session = DatabaseEngine.get_session()
            logger.info("Conexão ao banco de dados estabelecida com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
            QMessageBox.critical(self, "Erro de Conexão", f"Falha ao conectar ao banco de dados: {str(e)}")

    def select_geometry(self):
        try:
            layer = self.iface.activeLayer()
            if layer is None or not isinstance(layer, QgsVectorLayer):
                raise ValueError("Nenhuma camada ativa válida selecionada no QGIS.")

            selected_features = layer.selectedFeatures()
            if not selected_features:
                raise ValueError("Nenhuma feição selecionada. Por favor, selecione uma feição primeiro.")

            self.selected_geometry = selected_features[0].geometry()
            wkt_geometry = self.selected_geometry.asWkt()

            logger.info(f"Geometria selecionada: {wkt_geometry}")
            QMessageBox.information(self, "Geometria Selecionada", f"Geometria selecionada:\n{wkt_geometry}")
        except Exception as e:
            logger.error(f"Erro na seleção de geometria: {str(e)}")
            QMessageBox.critical(self, "Erro na Seleção", f"Erro ao selecionar geometria: {str(e)}")

    def find_intersecting_maps(self):
        if self.selected_geometry is None:
            QMessageBox.warning(self, "Geometria Não Selecionada", "Por favor, selecione uma geometria antes de continuar.")
            return

        try:
            selected_scale = self.scaleComboBox.currentText()
            logger.info(f"Escala selecionada: {selected_scale}")
            wkt_geometry = self.selected_geometry.asWkt()
            scale_key = reverse_meta_cartas.get(selected_scale)
            if not scale_key:
                raise ValueError(f"Escala inválida selecionada: {selected_scale}")

            query = f"""
                SELECT codigo, escala, ST_AsEWKB(wkb_geometry) AS wkb_geometry
                FROM folhas_cartograficas
                WHERE escala = '{scale_key}'
                AND ST_Intersects(
                    wkb_geometry,
                    ST_GeomFromText('{wkt_geometry}', 4326)
                );
            """
            logger.debug(f"Consulta SQL: {query}")
            result = self.db_session.execute(query).fetchall()
            logger.info(f"{len(result)} resultados encontrados na consulta.")

            if result:
                layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Folhas Intersectadas", "memory")
                pr = layer.dataProvider()
                pr.addAttributes([QgsField("codigo", QVariant.String), QgsField("escala", QVariant.String)])
                layer.updateFields()

                for row in result:
                    wkb_geometry = row['wkb_geometry']
                    if isinstance(wkb_geometry, memoryview):
                        wkb_geometry = wkb_geometry.tobytes()
                    geom = QgsGeometry().fromWkb(wkb_geometry)

                    if geom.isEmpty():
                        logger.warning(f"Geometria vazia para o código {row['codigo']}")
                        continue

                    feat = QgsFeature()
                    feat.setGeometry(geom)
                    feat.setAttributes([row['codigo'], row['escala']])
                    pr.addFeature(feat)

                QgsProject.instance().addMapLayer(layer)
                QMessageBox.information(self, "Sucesso", f"{len(result)} folhas foram encontradas e adicionadas ao QGIS.")
                logger.info(f"{len(result)} folhas cartográficas adicionadas ao QGIS.")
            else:
                QMessageBox.information(self, "Nenhuma Interseção", "Nenhuma folha cartográfica foi encontrada.")
                logger.info("Nenhuma folha cartográfica foi encontrada.")
        except Exception as e:
            logger.error(f"Erro ao executar a consulta SQL: {str(e)}")
            QMessageBox.critical(self, "Erro na Consulta", f"Erro ao executar a consulta SQL: {str(e)}")
