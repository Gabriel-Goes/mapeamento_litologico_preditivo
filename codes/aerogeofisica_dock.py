# -*- coding: utf-8 -*-
from qgis.PyQt import QtCore, QtWidgets
from qgis.core import (
    QgsProject,
    QgsDataSourceUri,
    QgsGeometry,
    QgsVectorLayer,
)
from qgis.utils import iface


def selecionar_pontos_postgis(
    schema="geof",
    tabela="ag_sample_gamma",
    geom_col="geom",
    pk_col="sample_id",
    host="localhost",
    port="5432",
    dbname="geologia",
    user="postgres",
    password="postgres",
    layer_name_suffix="_in_sel",
):
    """
    Backend simples: lê a geometria da seleção na camada ativa e cria
    uma camada PostGIS com pontos que intersectam essa geometria.

    Todos os parâmetros são configuráveis para permitir reutilização
    futura com outras tabelas/camadas.
    """

    camada = iface.activeLayer()
    if camada is None:
        QtWidgets.QMessageBox.warning(
            iface.mainWindow(),
            "Aerogeofísica",
            "Nenhuma camada ativa. Selecione uma camada de polígonos."
        )
        return

    if camada.selectedFeatureCount() == 0:
        QtWidgets.QMessageBox.warning(
            iface.mainWindow(),
            "Aerogeofísica",
            "Nenhuma feição selecionada na camada ativa."
        )
        return

    feats_sel = list(camada.selectedFeatures())
    geom_union = feats_sel[0].geometry()
    if len(feats_sel) > 1:
        geom_union = QgsGeometry.unaryUnion([f.geometry() for f in feats_sel])

    if geom_union is None or geom_union.isEmpty():
        QtWidgets.QMessageBox.warning(
            iface.mainWindow(),
            "Aerogeofísica",
            "Geometria selecionada está vazia ou inválida."
        )
        return

    crs = camada.crs()
    poly_srid = crs.postgisSrid()
    if poly_srid <= 0:
        QtWidgets.QMessageBox.warning(
            iface.mainWindow(),
            "Aerogeofísica",
            f"SRID da camada ativa é inválido ({poly_srid})."
        )
        return

    wkt = geom_union.asWkt()
    wkt_sql = wkt.replace("'", "''")

    where = (
        f"ST_Intersects("
        f"{geom_col}, "
        f"ST_Transform("
        f"ST_GeomFromText('{wkt_sql}', {poly_srid}), "
        f"Find_SRID('{schema}','{tabela}','{geom_col}')"
        f")"
        f")"
    )

    uri = QgsDataSourceUri()
    uri.setConnection(host, port, dbname, user, password)
    uri.setDataSource(schema, tabela, geom_col, where, pk_col)

    nome_camada = f"{tabela}{layer_name_suffix}"

    vlayer = QgsVectorLayer(uri.uri(False), nome_camada, "postgres")
    if not vlayer.isValid():
        QtWidgets.QMessageBox.critical(
            iface.mainWindow(),
            "Aerogeofísica",
            "Falha ao criar camada PostGIS com os pontos filtrados.\n"
            "Verifique host, porta, credenciais, schema, tabela e nomes de colunas."
        )
        return

    QgsProject.instance().addMapLayer(vlayer)
    iface.setActiveLayer(vlayer)

    n_pts = vlayer.featureCount()
    iface.messageBar().pushInfo(
        "Aerogeofísica",
        f"{n_pts} ponto(s) aerogeofísico(s) intersectando a seleção."
    )


class AerogeofisicaDock(QtWidgets.QDockWidget):
    """
    Dock minimalista, mas já estruturado com QTabWidget, para ser
    estendido com novas abas (interpolação, STAC, SOM/CNN, etc.).

    Aba atual: 'Pontos PostGIS'
        - Exibe informação da camada ativa.
        - Permite configurar conexão PostGIS e nomes de schema/tabela.
        - Botão 'Executar' chama o backend selecionar_pontos_postgis().
    """

    def __init__(self, iface):
        super().__init__("Geologia — Workflow")
        self.iface = iface
        self.setObjectName("AerogeofisicaDock")
        self.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QWidget(self)
        self.setWidget(root)

        layout = QtWidgets.QVBoxLayout(root)

        # TabWidget para modularidade futura
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # ------------------ TAB 1: Pontos PostGIS ------------------
        tab_pts = QtWidgets.QWidget()
        self.tabs.addTab(tab_pts, "Pontos PostGIS")

        lay_tab = QtWidgets.QVBoxLayout(tab_pts)

        # Grupo: Camada de seleção
        gb_sel = QtWidgets.QGroupBox("Camada de seleção (QGIS)")
        lay_sel = QtWidgets.QGridLayout(gb_sel)

        self.labLayerName = QtWidgets.QLabel("<i>Nenhuma camada ativa</i>")
        self.labLayerCrs = QtWidgets.QLabel("CRS: —")
        self.btnRefreshLayer = QtWidgets.QPushButton("Atualizar camada ativa")

        lay_sel.addWidget(QtWidgets.QLabel("Camada ativa:"), 0, 0)
        lay_sel.addWidget(self.labLayerName, 0, 1, 1, 2)
        lay_sel.addWidget(QtWidgets.QLabel("CRS:"), 1, 0)
        lay_sel.addWidget(self.labLayerCrs, 1, 1, 1, 2)
        lay_sel.addWidget(self.btnRefreshLayer, 2, 2)

        lay_tab.addWidget(gb_sel)

        # Grupo: Conexão PostGIS
        gb_pg = QtWidgets.QGroupBox("Conexão PostGIS / Tabela de pontos")
        lay_pg = QtWidgets.QGridLayout(gb_pg)

        self.leHost = QtWidgets.QLineEdit("localhost")
        self.lePort = QtWidgets.QLineEdit("5432")
        self.leDb   = QtWidgets.QLineEdit("geologia")
        self.leUser = QtWidgets.QLineEdit("postgres")
        self.lePass = QtWidgets.QLineEdit("postgres")
        self.lePass.setEchoMode(QtWidgets.QLineEdit.Password)

        self.leSchema   = QtWidgets.QLineEdit("geof")
        self.leTabela   = QtWidgets.QLineEdit("ag_sample_gamma")
        self.leGeomCol  = QtWidgets.QLineEdit("geom")
        self.lePkCol    = QtWidgets.QLineEdit("sample_id")
        self.leSufixo   = QtWidgets.QLineEdit("_in_sel")

        row = 0
        lay_pg.addWidget(QtWidgets.QLabel("Host"), row, 0)
        lay_pg.addWidget(self.leHost, row, 1)
        lay_pg.addWidget(QtWidgets.QLabel("Porta"), row, 2)
        lay_pg.addWidget(self.lePort, row, 3)
        row += 1

        lay_pg.addWidget(QtWidgets.QLabel("Banco"), row, 0)
        lay_pg.addWidget(self.leDb, row, 1)
        lay_pg.addWidget(QtWidgets.QLabel("Usuário"), row, 2)
        lay_pg.addWidget(self.leUser, row, 3)
        row += 1

        lay_pg.addWidget(QtWidgets.QLabel("Senha"), row, 0)
        lay_pg.addWidget(self.lePass, row, 1)
        row += 1

        lay_pg.addWidget(QtWidgets.QLabel("Schema"), row, 0)
        lay_pg.addWidget(self.leSchema, row, 1)
        lay_pg.addWidget(QtWidgets.QLabel("Tabela"), row, 2)
        lay_pg.addWidget(self.leTabela, row, 3)
        row += 1

        lay_pg.addWidget(QtWidgets.QLabel("Coluna geom"), row, 0)
        lay_pg.addWidget(self.leGeomCol, row, 1)
        lay_pg.addWidget(QtWidgets.QLabel("PK"), row, 2)
        lay_pg.addWidget(self.lePkCol, row, 3)
        row += 1

        lay_pg.addWidget(QtWidgets.QLabel("Sufixo nome camada"), row, 0)
        lay_pg.addWidget(self.leSufixo, row, 1)
        row += 1

        self.btnRun = QtWidgets.QPushButton("Selecionar pontos")
        self.btnRun.setStyleSheet("font-weight: 600;")
        lay_pg.addWidget(self.btnRun, row, 3)

        lay_tab.addWidget(gb_pg)

        # Log simples
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setPlaceholderText("Mensagens do workflow…")
        lay_tab.addWidget(self.log)

        # Conexões de sinais
        self.btnRefreshLayer.clicked.connect(self._update_active_layer_info)
        self.btnRun.clicked.connect(self._on_run)

        # Atualiza info inicial
        self._update_active_layer_info()

    # ----------------------- Helpers UI -----------------------

    def _log(self, msg):
        self.log.appendPlainText(str(msg))

    def _update_active_layer_info(self):
        camada = self.iface.activeLayer()
        if camada is None:
            self.labLayerName.setText("<i>Nenhuma camada ativa</i>")
            self.labLayerCrs.setText("CRS: —")
            self._log("Nenhuma camada ativa no canvas.")
            return

        self.labLayerName.setText(camada.name())
        try:
            crs_authid = camada.crs().authid()  # ex.: 'EPSG:4326'
        except Exception:
            crs_authid = "—"
        self.labLayerCrs.setText(f"CRS: {crs_authid}")
        self._log(f"Camada ativa: {camada.name()} | CRS: {crs_authid}")

    # ----------------------- Ação principal -----------------------

    def _on_run(self):
        self._log("Executando seleção de pontos PostGIS a partir da feição selecionada…")

        try:
            selecionar_pontos_postgis(
                schema=self.leSchema.text().strip(),
                tabela=self.leTabela.text().strip(),
                geom_col=self.leGeomCol.text().strip(),
                pk_col=self.lePkCol.text().strip(),
                host=self.leHost.text().strip(),
                port=self.lePort.text().strip(),
                dbname=self.leDb.text().strip(),
                user=self.leUser.text().strip(),
                password=self.lePass.text(),
                layer_name_suffix=self.leSufixo.text().strip() or "_in_sel",
            )
            self._log("Operação concluída.")
        except Exception as e:
            self._log(f"Erro ao executar seleção: {e}")


# Helper para carregar o dock via console do QGIS
_aero_dock = None

def run_aerogeofisica_dock():
    global _aero_dock
    if _aero_dock is None:
        _aero_dock = AerogeofisicaDock(iface)
        iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, _aero_dock)
    _aero_dock.show()
    _aero_dock.raise_()
