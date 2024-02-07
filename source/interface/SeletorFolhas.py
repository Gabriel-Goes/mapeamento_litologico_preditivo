# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# source/interface/SeletorFolhas.py
# Descrição: Classe para implementar métodos de seleção de folhas.
# -----------------------------------------------------------------------------
import shapely
from utils import reverse_meta_cartas


# ------------------------------ CLASSES ------------------------------------
class SeletorFolhas:
    '''
    Classe para implementar métodos de seleção de folhas.
        Será importado por FrameSeletor e utilizado para atualizar valores
        de folhas, atualizar folha de estudo e gerar dicionário de folhas.
    '''
    def __init__(self,
                 combobox_cartas, combobox_folha,
                 gerenciador_folhas):
        '''
        Construtor da classe SeletorFolhas.
        '''
        self.combobox_folha = combobox_folha
        self.combobox_cartas = combobox_cartas
        self.gerenciadorFolhas = gerenciador_folhas

    # ---------------------------- Métodos ------------------------------------
    # Visualiza valor de Combobox Cartas
    def get_combobox_cartas(self):
        '''
        Método para visualizar valor de Combobox Cartas.
        '''
        print(f' --> Escala escolhida: {self.combobox_cartas.get()}')
        self.escala = self.combobox_cartas.get()

    # Evento de Combobox Cartas atualizado
    def evento_combobox_cartas(self, event):
        '''
        Evento de Combobox Cartas atualizado.
        '''
        self.get_combobox_cartas()
        self.selecionar_carta(self.escala)

    # Atualiza valores de Combobox Folhas
    def atualizar_combobox_folha(self):
        '''
        Método para atualizar valores de Combobox Folhas.
        '''
        id_folhas = self.cartas['id_folha'].tolist()
        self.combobox_folha['values'] = id_folhas
        if id_folhas:
            self.combobox_folha.set(id_folhas[0])

    # Seleciona Folhas a partir das esclas disponíveis em meta_cartas
    def selecionar_carta(self, escala):
        '''
        Método para selecionar folhas a partir das escalas disponíveis em
        meta_cartas.
        '''
        try:
            carta = reverse_meta_cartas[escala]
            self.cartas = self.gerenciadorFolhas.seleciona_escala(carta)
            print(f' --> Folhas selecionadas: {len(self.cartas)}')
            print(f' --> {self.cartas.head()}')
            self.atualizar_combobox_folha()
            print(' --> Combobox Folhas atualizado!')
        except Exception as e:
            print(f' --> Erro ao selecionar folhas! {e}')

        return self.cartas

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
