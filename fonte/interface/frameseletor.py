# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# source/interface/FrameSeletor.py
# # ------------------------------ IMPORTS ------------------------------------
from tkinter import ttk
import tkinter as tk

from interface.seletorfolhas import SeletorFolhas
from utils.utils import reverse_meta_cartas
# --------------------------------------------------------------------------- #


# ------------------------------- CLASSES ------------------------------------
class FrameSeletor():
    '''
    Esta classe é responsável por criar o Frame que contêm as ferramentas de
    seleção e geração de folhas de cartas.
    '''

    # Construtor da classe Seletor de Folhas
    def __init__(self, admin_folhas, main_frame, style):
        print('-> Inicializando Frame de Seletor')
        self.admin_folhas = admin_folhas
        self.main_frame = main_frame
        self.style = style
        self.setup_frame_seletor()
        self.seletor_folhas = self.setup_seletor_folhas()
        self.combobox_carta.bind('<<ComboboxSelected>>',
                                 self.seletor_folhas.evento_combobox_cartas)
        self.combobox_folha.bind('<KeyRelease>',
                                 self.seletor_folhas.filtrar_ids_folhas)
        self.setupt_botão_selecionar()

    # Configuração do seletor de folhas
    def setup_seletor_folhas(self):
        '''
        Método responsável por configurar a classe SeletorFolhas, que é a
        classe responsável por mediar a interação entre FrameSeletor e
        AbrirFolhas. Sendo assim, SeletorFolhas é a classe responsável por
        gerenciar a seleção de folhas de cartas.
        '''
        seletor_folhas = SeletorFolhas(self.combobox_carta,
                                       self.combobox_folha,
                                       self.admin_folhas)
        return seletor_folhas

    # Método para criar o seletor de folhas de cartas
    def setup_frame_seletor(self):
        '''
        Configura o frame responsável pelos widgets de seleção de escala e
        ids de folhas.
        '''
        # ------------------- Frame - Seletor de Folhas de Cartas -------------
        # Cria Frame para o Seletor
        self.seletor_frame = ttk.Frame(self.main_frame,
                                       relief=tk.GROOVE,
                                       width=1200, height=900,
                                       style="Custom.TFrame")
        self.seletor_frame.grid(row=0, column=0, padx=5, pady=5)

        # ------------------- Label do Seletor de Folhas ----------------------
        label_seletor = tk.Label(self.seletor_frame,
                                 text='Seletor de Folhas',
                                 font=('SourceCodePro', 12, 'bold'),
                                 relief=tk.GROOVE, bd=2,
                                 bg='black', fg='white')
        label_seletor.grid(row=0, column=0, padx=5, pady=5)

        # ------------------- Frame - Folha de Estudo -------------------------
        self.folha_estudo_frame = ttk.Frame(self.seletor_frame,
                                            relief=tk.GROOVE,
                                            width=900, height=600,
                                            style="Custom.TFrame")
        self.folha_estudo_frame.grid(row=1, column=0, padx=5, pady=5)

        # ------------------- Label do Folhas de Estudo  ----------------------
        label_estudo_frame = tk.Label(self.folha_estudo_frame,
                                      text='Folha de Estudo',
                                      font=('SourceCodePro', 9, 'bold'),
                                      relief=tk.GROOVE, bd=2,
                                      bg='black', fg='white')
        # Centraliza label no CENTRO DO TOPO DO FRAME
        label_estudo_frame.grid(row=0, column=0, padx=5, pady=5, sticky='EW')

        # ------------------- Combobox - Carta --------------------------------
        self.combobox_carta = ttk.Combobox(self.folha_estudo_frame,
                                           values=list(
                                               reverse_meta_cartas.keys()),
                                           width=15,
                                           height=6,
                                           style="Custom.TCombobox")
        self.combobox_carta.grid(row=1, column=0, padx=5, pady=5)
        self.combobox_carta.set('1:1.000.000')

        # ------------------- Combobox - Folha --------------------------------
        self.folha_var = tk.StringVar()
        self.folha_var.trace('w', lambda name, index, mode,
                             sv=self.folha_var: self.on_text_change(sv))
        self.combobox_folha = ttk.Combobox(self.folha_estudo_frame,
                                           textvariable=self.folha_var,
                                           values=[],
                                           width=15,
                                           height=6,
                                           style="Custom.TCombobox")
        self.combobox_folha.grid(row=2, column=0, padx=5, pady=5, sticky='W')

    # ------------------- Botão - Adicionar Folha à Área de Estudo --------
    def setupt_botão_selecionar(self):
        # UTF-8 SIMBOLOS
        # Simbolo de mais
        # plus_sign = u"\u2795"
        # Simbolo de correto
        check_sign = u"\u2713"
        comando = self.seletor_folhas.define_area_de_estudo
        self.botao_adicionar_folha = ttk.Button(self.folha_estudo_frame,
                                                text=check_sign,
                                                width=3,
                                                style="Custom.TButton",
                                                command=comando)
        self.botao_adicionar_folha.grid(row=2, column=1, padx=5, pady=5)

    # Transforma texto em maiúsculo
    def on_text_change(self, sv):
        '''
        Método para transformar texto em maiúsculo.
        '''
        current_text = sv.get().upper()
        sv.set(current_text)


# ------------------------------ MAINLOOP ------------------------------------
if __name__ == '__main__':
    pass
