# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# Descrição: Classe para plotar as folhas de estudo no canvas.
# source/interface/PlotFolhas.py

# ---------- imports
import pygmt
from shapely.wkb import loads
import logging

# -----------------------------------------------------------------------------
# Esta classe será responsável por atualizar o canvas com as folhas disponí
# veis no self.seletorFolhas.dicionario e self.seletorFolhas.folhaEstudo.
# Utilizando a biblioteca pygmt para plotar as folhas.
logger = logging.getLogger(__name__)


# ------------------------------- CLASSES ------------------------------------
class PlotFolhas:

    def __init__(self, folhas_estudo):
        self.folhas_estudo = folhas_estudo

    def plot_basemap(self):
        fig = pygmt.Figure()
        fig.basemap(region=[-85, -30, -55, 20], projection='M6i', frame=True)
        fig.show()

    def plot_folha_estudo(self):
        logger.debug(f' folhas_estudo: {self.folhas_estudo}')
        fig = pygmt.Figure()
        fig.basemap(region=[-45, -40, -23, -20], projection='M6i', frame=True)
        fe = self.folhas_estudo

        if isinstance(fe, dict):
            logger.debug(f'folhas_estudo contém {len(fe)} itens')
            for key, value in fe.items():
                try:
                    logger.debug(f'key: {key} value: {value}')
                    poly = loads(value['geometry'].desc)
                    fig.plot(data=poly, style='p', color='black')
                    logger.debug(f'folha: {key} plotada')
                except Exception as e:
                    logger.error(f'Erro ao plotar folha: {key} - {e}')
        else:
            logger.error('folhas_estudo não é um dicionário')

        logger.debug('Mostrando o plot')
        fig.show()
