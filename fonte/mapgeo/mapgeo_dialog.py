import logging
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsGeometry, QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant
from .databaseengine import DatabaseEngine

log_file = os.path.expanduser('~/MAPGEO.LOG')
logger = logging.getLogger('mapgeo')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)

if not logger.hasHandlers():
    logger.addHandler(file_handler)

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'mapgeo_dialog_base.ui'))

meta_cartas = {
    '1kk': {'escala': '1:1.000.000',
            'incrementos': (4, 6),
            'codigos': ['A', 'B', 'C', 'D', 'E', 'F', 'G',
                        'H', 'I', 'J', 'K', 'L', 'M', 'N',
                        'O', 'P', 'Q', 'R', 'S', 'T']},
    '500k': {'escala': '1:500.000',
             'incrementos': (2, 3),
             'codigos': [['V', 'Y'], ['X', 'Z']]},
    '250k': {'escala': '1:250.000',
             'incrementos': (1, 1.5),
             'codigos': [['A', 'C'], ['B', 'D']]},
    '100k': {'escala': '1:100.000',
             'incrementos': (0.5, 0.5),
             'codigos': [['I', 'IV'], ['II', 'V'], ['III', 'VI']]},
    '50k': {'escala': '1:50.000',
            'incrementos': (0.25, 0.25),
            'codigos': [['1', '3'], ['2', '4']]},
    '25k': {'escala': '1:25.000',
            'incrementos': (0.125, 0.125),
            'codigos': [['NW', 'SW'], ['NE', 'SE']]}
}

reverse_meta_cartas = {meta_cartas[k]['escala']: k for k in meta_cartas}




class mapgeoDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(mapgeoDialog, self).__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.selectGeometryButton.clicked.connect(self.select_geometry)
        self.runButton.clicked.connect(self.find_intersecting_maps)
        self.db_session = None
        self.selected_geometry = None
        logger.info("Inicializando o plugin MAPGEO.")

        try:
            # Adicionar escalas ao combobox
            self.scaleComboBox.addItems(['1:1.000.000', '1:500.000', '1:250.000', '1:100.000', '1:50.000', '1:25.000'])

            # Tentar conectar ao banco de dados
            self.db_session = DatabaseEngine.get_session()
            logger.info("Conexão ao banco de dados estabelecida com sucesso.")
        except Exception as e:
            # Logar o erro e exibir mensagem de erro
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
            #scale_key = '25k'

            query = f"""
                SELECT codigo, escala, epsg, ST_AsText(wkb_geometry) AS wkt_geometry
                FROM folha_cartografica
                WHERE escala = '{scale_key}'
                AND ST_Intersects(
                    wkb_geometry,
                    ST_GeomFromText('{wkt_geometry}', 4326)
                );
            """
            logger.debug(f"Consulta SQL: {query}")
            result = self.db_session.execute(query).fetchall()

            if not result:
                QMessageBox.information(self, "Nenhuma Interseção", "Nenhuma folha cartográfica foi encontrada.")
                return

            logger.debug(f"Resultado:\n{result}")
            layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Folhas Intersectadas", "memory")
            pr = layer.dataProvider()
            pr.addAttributes([QgsField("codigo", QVariant.String), QgsField("escala", QVariant.String), QgsField("epsg", QVariant.Int), QgsField("wkt_geometry")])
            layer.updateFields()

            for row in result:
                try:
                    wkt_geometry = row['wkt_geometry']
                    wkt_geometry = QgsGeometry.fromWkt(wkt_geometry)
                    feat = QgsFeature()
                    feat.setGeometry(wkt_geometry)
                    feat.setAttributes([row['codigo'], row['escala'], row['epsg'], row['wkt_geometry']])
                    pr.addFeature(feat)

                except Exception as e:
                    logger.error(f"Erro: {str(e)}")
                    continue

            QgsProject.instance().addMapLayer(layer)
            QMessageBox.information(self, "Sucesso", f"{len(result)} folhas foram encontradas e adicionadas ao QGIS.")
        except Exception as e:
            logger.error(f"Erro ao processar os resultados: {str(e)}")
            QMessageBox.critical(self, "Erro na Consulta", f"Erro ao processar os resultados: {str(e)}")
