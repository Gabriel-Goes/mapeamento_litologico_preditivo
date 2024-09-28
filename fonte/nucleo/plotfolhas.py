# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# Descrição: Classe para plotar as folhas de estudo no canvas.
# source/interface/PlotFolhas.py
# ---------- imports
import pygmt
from shapely.wkb import loads

# -----------------------------------------------------------------------------
# Esta classe será responsável por atualizar o canvas com as folhas disponí
# veis no self.seletorFolhas.dicionario e self.seletorFolhas.folhaEstudo.
# Utilizando a biblioteca pygmt para plotar as folhas.


# ------------------------------- CLASSES ------------------------------------
class PlotFolhas:

    def __init__(self, folhas_estudo):
        self.folhas_estudo = folhas_estudo

    def plot_basemap(self):
        fig = pygmt.Figure()
        fig.basemap(region=[-85, -30, -55, 20], projection='M6i', frame=True)
        fig.show()

    def plot_folha_estudo(self):
        fig = pygmt.Figure()
        fig.basemap(region=[-45, -40, -23, -20], projection='M6i', frame=True)
        fe = self.folhas_estudo
        for key, value in fe:
            poly = loads(value['geometry'].desc)
            fig.plot(data=poly, style='p', color='black')
        fig.show()
