# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# sourcuce/interface/Interface.py
# # ------------------------------ IMPORTS ------------------------------------
from FrameSeletor import FrameSeletor
from FramePlot import FramePlot
from SeletorFolhas import SeletorFolhas
from PlotFolhas import PlotFolhas
from DicionarioFolhas import DicionarioFolhas

import tkinter as tk
from tkinter import ttk
# ---------------------------------------------------------------------------
"""
===========================
Interface do Preditor Terra
===========================

Este script é responsável por criar a interface do Preditor Terra.

"""


# ------------------------------ INTERFACE ------------------------------------
class PreditorTerraUI:
    '''
    Esta Classe é responsável por criar a interface do Preditor Terra.
    '''
    # Construtor da classe PreditorTerra

    def __init__(self, root):
        print('')
        print('======================================================')
        print('              Interface do Preditor Terra             ')
        print('======================================================')
        self.root = root
        # ---------------- Configuração do estilo da interface
        self.root.configure(bg='black')
        self.style = ttk.Style()
        self.style.configure("Custom.TFrame", background="black",
                             foreground="white")
        self.style.configure("Custom.TButton", background="black",
                             foreground="white")
        self.style.configure("Custom.TCombobox",
                             background="gray", foreground="black",
                             selectbackground="lightgray",
                             selectforeground="black", box="lightgray", font=(
                                 'SourceCodePro', 12, 'bold'))
        self.ax = None

        self.dicionarioFolhas = DicionarioFolhas()
        self.setup_ui()

    # método para executar as funções de configuração da interface
    def setup_ui(self):
        self.root.title('Preditor Terra')
        self.root.geometry('1440x900')
        dicionario = {}
        # ------------------- Seletor de Folhas
        self.seletorFolhas = SeletorFolhas(self.ax,
                                           self.dicionarioFolhas,
                                           dicionario,
                                           interface=None)
        self.seletorFolhas.interface = self
        # ------------------- Main Frame
        self.mainFrame = ttk.Frame(self.root, width=1420, height=880,
                                   relief=tk.GROOVE, style="Custom.TFrame")
        self.mainFrame.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        # ------------------- Seletor de Folhas - Frame
        self.frameSeletor = FrameSeletor(dicionario,
                                         self.seletorFolhas,
                                         self.mainFrame,
                                         self.style)
        # ------------------- Plot Frame
        self.framePlot = FramePlot(self.seletorFolhas,
                                   self.mainFrame,
                                   self.frameSeletor,
                                   self.style)
        self.seletorFolhas.frameSeletor = self.frameSeletor
        # ------------------- Plot Folhas
        self.plotFolhas = PlotFolhas(self.seletorFolhas, self.framePlot)


# ----------------------------- MAINLOOP
def start():
    '''
    Função principal para executar a interface do Preditor Terra.
    '''
    root = tk.Tk(className='Preditor_Terra')
    app = PreditorTerraUI(root)
    root.mainloop()
    print(' Interface do Preditor Terra encerrada.')
    return app


# Inicialização do aplicativo
if __name__ == "__main__":
    start()
