# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# source/interface/FrameSeletor.py
# # ------------------------------ IMPORTS ------------------------------------
from tkinter import ttk
import tkinter as tk

from DicionarioFolhas import DicionarioFolhas
from utils import metaCartas
# --------------------------------------------------------------------------- #


# ------------------------------- CLASSES ------------------------------------
class FrameSeletor():
    '''
    Esta classe é responsável por criar o Frame que contêm as ferramentas de
    seleção e geração de folhas de cartas.
    '''

    # Construtor da classe Seletor de Folhas
    def __init__(self, dicionario, seletorFolhas, mainFrame, style):
        print(' --> Inicializando Frame de Seletor')
        self.seletorFolhas = seletorFolhas
        self.mainFrame = mainFrame
        self.style = style
        self.DicionarioFolhas = DicionarioFolhas()
        self.labelFolhaEstudo = None
        self.setupFrameSeletor(dicionario=dicionario)

    def atualizarfolhaEstudo(self, folhaEstudo):
        self.atualizarLabelFolhaEstudo(folhaEstudo)

    # Método para criar o seletor de folhas de cartas
    def setupFrameSeletor(self, dicionario):
        '''
        Cria o seletor de folhas de cartas.
        '''
        # Label do topo - PREDITOR TERRA --------------------------------------
        labelMain = tk.Label(self.mainFrame, text='Preditor Terra',
                             font=('SourceCodePro', 12, 'bold'),
                             relief=tk.GROOVE, bd=2)
        labelMain.grid(row=0, column=1, padx=0, pady=0)
        labelMain.config(bg='black', fg='white')
        # ------------------- Frame - Seletor de Folhas de Cartas -------------
        # Cria Frame para o Seletor
        self.seletorFrame = ttk.Frame(self.mainFrame,
                                      relief=tk.GROOVE,
                                      width=300, height=400,
                                      style="Custom.TFrame")
        self.seletorFrame.grid(row=0, column=1, padx=0, pady=0)
        # ------------------- Label do Seletor de Folhas ----------------------
        labelSeletor = tk.Label(self.seletorFrame,
                                text='Seletor de Folhas',
                                font=('SourceCodePro', 12, 'bold'),
                                relief=tk.GROOVE, bd=2,
                                bg='black', fg='white')
        labelSeletor.grid(row=0, column=0, padx=5, pady=5)
        # ------------------- Combobox - Carta --------------------------------
        self.comboboxCarta = ttk.Combobox(self.seletorFrame,
                                          values=[dados['escala'] for dados in
                                                  metaCartas.values()],
                                          width=10,
                                          style="Custom.TCombobox")
        self.comboboxCarta.grid(row=1, column=0, padx=5, pady=5)
        self.comboboxCarta.set('1:25.000')
        # ------------------- Combobox - Folha --------------------------------
        self.comboboxFolha = ttk.Combobox(self.seletorFrame, width=10,
                                          style="Custom.TCombobox")
        self.comboboxFolha.grid(row=2, column=0, padx=5, pady=5)
        self.comboboxFolha.set('SF23_YA_III4')
        # ------------------ Botão - Gerar Dicionário de folhas ---------------
        botao_gDicionario = ttk.Button(self.seletorFrame,
                                       text='Gerar Dicionário',
                                       command=lambda:
                                       self.seletorFolhas.gDicionario(
                                           dicionario),
                                       style="Custom.TButton")
        botao_gDicionario.grid(row=3, column=0, padx=5, pady=5)
        # ------------------ Frame - Folha de Estudo --------------------------
        self.frameFolhaEstudo = ttk.Frame(self.seletorFrame,
                                          relief=tk.GROOVE,
                                          width=300, height=400,
                                          style="Custom.TFrame")
        self.frameFolhaEstudo.grid(row=4, column=0, padx=0, pady=0)
        # ------------------ Label - Folha de Estuda --------------------------
        self.atualizarLabelFolhaEstudo()

    # ----------- Método para atualizar label de folha de estudo --------------
    def atualizarLabelFolhaEstudo(self, id_folha=None):
        ajuda = "Selecione uma área de estudo clicando"
        # Romva o label antigo se ele já existir
        if self.labelFolhaEstudo is not None:
            self.labelFolhaEstudo.destroy()
        text = f'Área de Estudo: {id_folha}' if id_folha else ajuda
        self.labelFolhaEstudo = tk.Label(
            self.frameFolhaEstudo,
            text=text,
            font=('SourceCodePro', 9, 'bold'),
            relief=tk.GROOVE, bd=2,
            bg='black', fg='white')
        self.labelFolhaEstudo.grid(row=4, column=0, padx=0, pady=0)


# ------------------------------ MAINLOOP ------------------------------------
if __name__ == '__main__':
    print(metaCartas)
    print(metaCartas.keys())
