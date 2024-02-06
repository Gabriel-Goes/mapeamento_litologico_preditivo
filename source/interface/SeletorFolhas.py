# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# source/interface/SeletorFolhas.py
# Descrição: Classe para implementar métodos de seleção de folhas.
# -----------------------------------------------------------------------------
from typing import Any, Dict
import shapely
from DicionarioFolhas import DicionarioFolhas
from utils import metaCartas, reverseMetaCartas


class SeletorFolhas:
    '''
    Classe para implementar métodos de seleção de folhas.
        Será importado por FrameSeletor e utilizado para atualizar valores
        de folhas, atualizar folha de estudo e gerar dicionário de folhas.
    '''
    def __init__(self,
                 ax: Any,
                 dicionarioFolhas: DicionarioFolhas,
                 dicionario: Dict[str, Any],
                 interface = None) -> None:
        self.ax = ax
        self.dicionarioFolhas = dicionarioFolhas
        dicionario = dicionario
        self.folhaEstudo = None
        self.frameSeletor = None
        self.interface = interface
    def atualizarFolhaEstudo(self, folhaEstudo):
        '''
        Atualiza a folha de estudo.
        '''
        if folhaEstudo is None:
            print(f'self.folhaEstudo: {self.folhaEstudo}')
            print(' --> Selecione uma folha de estudo.')
            print('======================================================')
            print('')
            return
        self.folhaEstudo = folhaEstudo
        print(f' --> Folha de estudo atualizada:\n {self.folhaEstudo}')
        print('======================================================')
        print('')

    # Método para determinar folha clicada
    def determine_folha_clicada(self, ax_x, ax_y):
        '''
        Define qual folha foi clicada no canvas a partir das coordenadas ax_x e
        ax_y pelo método contains.
        '''
        click = shapely.geometry.Point(ax_x, ax_y)
        for id, poly in self.dicionarioFolhas.carta_1kk.iterrows():
            if poly.geometry.contains(click):
                break
        folhaEstudo = self.dicionarioFolhas.carta_1kk.loc[id]

        return folhaEstudo

    # Método para ver click no canvas
    def on_canvas_click(self, click_event):
        '''
        Evento de click no canvas.
        '''
        # geographic coordinates from the click of mouse button
        x, y = self.ax.transData.inverted().transform((click_event.x,
                                                       click_event.y))
        print('')
        print('########### Evento de Click no Canvas ###########')
        print(f' --> Coords: {x, y}')
        self.folhaEstudo = self.determine_folha_clicada(x, y)
        print(f' --> Folha clicada: {self.folhaEstudo.id_folha}')
        print('======================================================')
        print('')
        if self.folhaEstudo is not None:
            self.atualizarFolhaEstudo(self.folhaEstudo)
            # Atualizar Label Folha de Estudo
            self.frameSeletor.atualizarLabelFolhaEstudo(
                self.folhaEstudo.id_folha)
            self.interface.plotFolhas.plot_folha_estudo()

    # Gerar Dicionário de Folhas
    def gDicionario(self, dicionario) -> Dict[str, Any]:
        '''
        Gera o dicionário de folhas.
        '''
        folhaEstudo = self.folhaEstudo
        if folhaEstudo is None:
            print(f' folhaEstadoAtual: {self.folhaEstudo}')
            print(' --> Selecione uma folha de estudo.')
            print('======================================================')
            print('')
            return
        id_folhaEstudo= folhaEstudo['id_folha']
        folhas = self.frameSeletor.comboboxFolha.get()
        escalaCarta = self.frameSeletor.comboboxCarta.get()
        self.carta = reverseMetaCartas.get(escalaCarta)
        print(' ------> Gerando Dicionário de Folhas')
        print(f'ID da Folha Selecionada: {id_folhaEstudo}')
        print(f'Carta: {self.carta}')
        print(f'Folha(s): {folhas}')
        print('======================================================')
        print('')
        dicionario = self.dicionarioFolhas.gera_dicionario(id_folhaEstudo,
                                                           self.carta,
                                                           folhas,
                                                           dicionario)
        # Agora podemos usar o dicionário para plotar e filtrar informaçoes etc
        print('Dicionário de Folhas:', dicionario.keys())
        print('======================================================')
        print('')

        return dicionario
