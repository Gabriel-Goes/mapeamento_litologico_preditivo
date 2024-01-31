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

    def __init__(self, main_frame, style):
        self.main_frame = main_frame
        self.dicionario_folhas = DicionarioFolhas()
        self.style = style
        self.criar_seletor_folhas()

# Função para criar o seletor de folhas de cartas
    def criar_seletor_folhas(self):
        '''
        Cria o seletor de folhas de cartas.
        '''
        # Label do topo - PREDITOR TERRA
        label_main = tk.Label(self.main_frame, text='Preditor Terra',
                              font=('SourceCodePro', 12, 'bold'),
                              relief=tk.GROOVE, bd=2)
        label_main.grid(row=0, column=1, padx=0, pady=0)
        label_main.config(bg='black', fg='white')
        # ------------------- Frame - Seletor de Folhas
        # Cria Frame para o Seletor
        seletor_folhas_frame = ttk.Frame(self.main_frame, relief=tk.GROOVE,
                                         width=300, height=400,
                                         style="Custom.TFrame")
        seletor_folhas_frame.grid(row=0, column=1, padx=0, pady=0)
        # ------------------- Label do Seletor de Folhas
        label_seletor_folhas = tk.Label(seletor_folhas_frame,
                                        text='Seletor de Folhas',
                                        font=('SourceCodePro', 12, 'bold'),
                                        relief=tk.GROOVE, bd=2,
                                        bg='black', fg='white')
        label_seletor_folhas.grid(row=0, column=0, padx=5, pady=5)
        # ------------------- Combobox - Carta
        self.combobox_carta = ttk.Combobox(seletor_folhas_frame,
                                           values=[dados['escala'] for dados in
                                                   cartas.values()], width=10,
                                           style="Custom.TCombobox")
        self.combobox_carta.grid(row=1, column=0, padx=5, pady=5)
        self.combobox_carta.bind('<<ComboboxSelected>>',
                                 self.atualizar_valores_folhas)
        # ------------------- Combobox - Folha
        self.combobox_folha = ttk.Combobox(seletor_folhas_frame, width=10,
                                           style="Custom.TCombobox")
        self.combobox_folha.grid(row=2, column=0, padx=5, pady=5)
        # ------------------ Botão - Gerar Dicionário de folhas
        botao_g_dicionario = ttk.Button(seletor_folhas_frame,
                                        text='Gerar Dicionário',
                                        command=self.e_gerar_dicionario_folhas,
                                        style="Custom.TButton")
        botao_g_dicionario.grid(row=3, column=0, padx=5, pady=5)

    # Método para atualizar valores de folhas
    def atualizar_valores_folhas(self, event):
        '''
        Atualiza os valores das folhas de acordo com a carta selecionada.
        '''
        escala_carta = self.combobox_carta.get()

        # Encontra a carta correspondente no dicionário
        for carta, dados in cartas.items():
            if dados['escala'] == escala_carta:
                print('======================================================')
                print(f'Carta: {carta}')
                print(f'Valores: {dados}')
                print('======================================================')
                # Atualizar a carta_selecionada
                self.carta_selecionada = carta
                # Atualizar os valores do Combobox_folha
                self.combobox_folha['values'] = dados['codigos']
                # Selecionar o primeiro valor do Combobox_folha
                self.combobox_folha.current(0)
                break

    # Gerar Dicionário de Folhas
    def e_gerar_dicionario_folhas(self):
        dic_f = self.dicionario_folhas
        folha_selecionada = self.combobox_folha.get()
        print('======================================================')
        print(f'Carta: {self.carta_selecionada}')
        print(f'Folha(s): {folha_selecionada}')
        print('======================================================')
        print('')
        dicionario = dic_f.gera_dicionario_de_folhas(self.carta_selecionada,
                                                     folha_selecionada)
        # Agora podemos usar o dicionário para plotar e filtrar informaçoes etc
        print('Dicionário de Folhas:', dicionario)
        return dicionario

    # Método para atualizar folha de estudo
    def atualizar_folha_estudo(self, folha_estudo):
        '''
        Atualiza a folha de estudo.
        '''
        self.folha_estudo = folha_estudo
        print(f' --> Folha de estudo atualizada: {self.folha_estudo}')
        print('======================================================')


# ------------------------------ MAINLOOP ------------------------------------
if __name__ == '__main__':
    print(cartas)
    print(cartas.keys())
