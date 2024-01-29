# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# SeletorFolhas.py
# # ------------------------------ IMPORTS ------------------------------------
from tkinter import ttk
import tkinter as tk

from geologist.source.DicionarioFolhas import DicionarioFolhas
from geologist.utils.utils import cartas
# --------------------------------------------------------------------------- #


# ------------------------------- CLASSES ------------------------------------
class SeletorFolhas:
    '''
    Esta classe é responsável por criar o seletor de folhas de cartas.
    '''
    # Construtor da classe Seletor de Folhas

    def __init__(self, main_frame):
        self.main_frame = main_frame
        self.dicionario_folhas = DicionarioFolhas()
        self.criar_seletor_folhas()

# Função para criar o seletor de folhas de cartas
    def criar_seletor_folhas(self):
        '''
        Cria o seletor de folhas de cartas.
        '''
        # ------------------- Frame - Seletor de Folhas
        # Cria Frame para o Seletor
        seletor_folhas_frame = ttk.Frame(self.main_frame, relief=tk.GROOVE,
                                         width=200, height=400)
        seletor_folhas_frame.grid(row=0, column=1, padx=5, pady=5)
        # ------------------- Label do topo - Seletor de Folhas
        label_seletor_folhas = tk.Label(seletor_folhas_frame,
                                        text='Seletor de Folhas',
                                        font=('SourceCodePro', 12, 'bold'),
                                        relief=tk.GROOVE, bd=2)
        label_seletor_folhas.grid(row=0, column=0, padx=5, pady=5)
        # ------------------- Combobox - Carta
        self.combobox_carta = ttk.Combobox(seletor_folhas_frame,
                                           values=[dados['escala'] for dados in
                                                   cartas.values()], width=10)
        self.combobox_carta.grid(row=1, column=0, padx=5, pady=5)
        self.combobox_carta.bind('<<ComboboxSelected>>',
                                 self.atualizar_valores_folhas)

        # ------------------- Combobox - Folha
        self.combobox_folha = ttk.Combobox(seletor_folhas_frame, width=10)
        self.combobox_folha.grid(row=2, column=0, padx=5, pady=5)

    # Método para atualizar valores de folhas
    def atualizar_valores_folhas(self, event):
        '''
        Atualiza os valores das folhas de acordo com a carta selecionada.
        '''
        chave_carta = self.combobox_carta.get()
        valores_folhas = []

        # Encontra a carta correspondente no dicionário
        for carta, dados in cartas.items():
            # print(f'string: {carta}, dados: {dados}') pra entender oq ta
            # acontecendo
            print(f' --> Carta: {carta}')
            print('')
            print(f' --> Dados: {dados}')
            if dados['escala'] == chave_carta:
                valores_folhas = dados['codigos']
                break
        # Atualizar os valores do Combobox_folha
        self.combobox_folha['values'] = sum(valores_folhas, []) if isinstance(
            valores_folhas[0], list) else valores_folhas
        # Selecionar o primeiro valor do Combobox_folha
        self.combobox_folha.current(0)

    # Gerar Dicionário de Folhas
    def gerar_dicionario_folhas(self):
        carta_selecionada = self.combobox_carta.get()
        folha_selecionada = self.combobox_folha.get()
        dicionario = self.dicionario_folhas(carta_selecionada,
                                            folha_selecionada)
        # Agora podemos usar o dicionário para plotar e filtrar informaçoes etc
        return dicionario


if __name__ == '__main__':
    print(cartas)
    print(cartas.keys())
