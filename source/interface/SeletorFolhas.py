# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# Descrição: Classe para implementar métodos de seleção de folhas.
# -----------------------------------------------------------------------------
from utils import metaCartas


class SeletorFolhas:
    '''
    Classe para implementar métodos de seleção de folhas.
        Será importado por FrameSeletor e utilizado para atualizar valores
        de folhas, atualizar folha de estudo e gerar dicionário de folhas.
    '''
    def __init__(self, frameSeletor, dicionarioFolhas):
        self.dicionarioFolhas = dicionarioFolhas
        self.frameSeletor = frameSeletor

    # Método para atualizar valores de folhas
    def atualizarID(self, event):
        '''
        Atualiza os IDs das folhas de acordo com a carta selecionada.
        '''
        escalaCarta = self.comboboxCarta.get()
        # Encontra a carta correspondente no dicionário
        for carta, dados in metaCartas.items():
            if dados['escala'] == escalaCarta:
                print(f'Carta: {carta}')
                print(f'Valores: {dados}')
                print('======================================================')
                print('')
                # Atualizar a carta_selecionada
                self.cartaSelec = carta
                # Atualizar os valores do Combobox_folha
                self.comboboxFolha['values'] = dados['codigos']
                # Selecionar o primeiro valor do Combobox_folha
                self.comboboxFolha.current(0)
                break

    # Método para atualizar folha de estudo
    def atualizarFolhaEstudo(self, folhaEstudo):
        '''
        Atualiza a folha de estudo.
        '''
        self.folhaEstudo = folhaEstudo
        print(f' --> Folha de estudo atualizada:\n {self.folhaEstudo}')
        print('======================================================')
        print('')

    # Gerar Dicionário de Folhas
    def gDicionario(self):
        idFolhaSelecionada = self.folhaEstudo['id_folha']
        folhas = self.combobox_folha.get()
        print(' ------> Gerando Dicionário de Folhas')
        print(f'ID da Folha Selecionada: {idFolhaSelecionada}')
        print(f'Carta: {self.cartaSelec}')
        print(f'Folha(s): {folhas}')
        print('======================================================')
        print('')
        self.dicionario = self.dicionarioFolhas.gera_dicionario(
            idFolhaSelecionada,
            self.carta_selec,
            folhas)
        # Agora podemos usar o dicionário para plotar e filtrar informaçoes etc
        print('Dicionário de Folhas:', self.dicionario.keys())
        print('======================================================')
        print('')

        return self.dicionario
