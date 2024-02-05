
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Interface.py
# # ------------------------------ IMPORTS ------------------------------------
from DicionarioFolhas import DicionarioFolhas

from FrameSeletor import FrameSeletor
from FramePlot import FramePlot

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
        self.folhaEstudo = None
        self.dicionarioFolhas = DicionarioFolhas()
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
        self.setup_ui()

    # método para executar as funções de configuração da interface
    def setup_ui(self):
        self.root.title('Preditor Terra')
        self.root.geometry('1440x900')

        # ------------------- Main Frame
        mainFrame = ttk.Frame(self.root, width=1420, height=880,
                              relief=tk.GROOVE, style="Custom.TFrame")
        mainFrame.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        # ------------------- Seletor de Folhas - Frame
        self.frameSeletor = FrameSeletor(mainFrame, self.style)
        # ------------------- Plot Frame
        self.framePlot = FramePlot(mainFrame, self.frameSeletor,
                                   self.folhaEstudo, self.style)


# ----------------------------- MAINLOOP
def main():
    '''
    Função principal para executar a interface do Preditor Terra.
    '''
    self = PreditorTerraUI
    self.root = tk.Tk(className='Preditor_Terra')
    self._app = PreditorTerraUI(self.root)
    self.root.mainloop()
    print(' Interface do Preditor Terra encerrada.')
    return self._app


# Inicialização do aplicativo
if __name__ == "__main__":
    main()
else:
    pass
