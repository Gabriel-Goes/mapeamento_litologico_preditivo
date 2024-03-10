# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# Descrição: Classe para plotar as folhas de estudo no canvas.
# source/interface/PlotFolhas.py
# ---------- imports
from utils import plotar, plotarInicial
# -----------------------------------------------------------------------------


# ------------------------------- CLASSES ------------------------------------
class PlotFolhas:
    '''
    Esta classe será responsável por atualizar o canvas com as folhas disponí
    veis no self.seletorFolhas.dicionario e self.seletorFolhas.folhaEstudo.
    '''

    def __init__(self, seletorFolhas, framePlot):
        self.seletorFolhas = seletorFolhas
        self.framePlot = framePlot

    def plot_folha_estudo(self):
        '''
        Método para plotar a folha de estudo no canvas.
        '''
        id_folha_estudo = self.seletorFolhas.folhaEstudo.folha_id
        folhas = self.seletorFolhas.dicionario
        # Limpa o canvas
        self.seletorFolhas.ax.clear()
        # Usa o utils.plotar para plotar a folha de estudo
        if id_folha_estudo in folhas:
            print(f' --> Plotando folha de estudo {id_folha_estudo}')
            plotar({id_folha_estudo:
                    folhas[id_folha_estudo]}, self.seletorFolhas.carta)

    def redesenhar_canvas(self):
        '''
        Método para redesenhar o canvas.
        '''
        carta_1kk = self.seletorFolhas.dicionario['carta_1kk']
        plotarInicial(carta_1kk)
