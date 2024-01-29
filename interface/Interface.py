# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Interface.py
# # ------------------------------ IMPORTS ------------------------------------
from geologist.source.DicionarioFolhas import DicionarioFolhas

from geologist.interface.SeletorFolhas import SeletorFolhas as sf
from geologist.interface.PlotFrame import plot_frame as pf

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
        print('======================================================')
        print('              Interface do Preditor Terra             ')
        print('======================================================')
        self.root = root
        self.dicionario_folhas = DicionarioFolhas()
        self.setup_ui()

    def setup_ui(self):
        self.root.title('Preditor Terra')
        self.root.geometry('1440x900')

        # Label do topo - PREDITOR TERRA
        label_root = tk.Label(self.root, text='Preditor Terra',
                              font=('SourceCodePro', 12, 'bold'),
                              relief=tk.GROOVE, bd=2)
        label_root.grid(row=0, column=0, padx=1, pady=1)

        # ------------------- Main Frame
        main_frame = ttk.Frame(self.root, width=1400, height=860,
                               relief=tk.GROOVE)
        main_frame.grid(row=1, column=0, padx=5, pady=1, sticky='nsew')

        # ------------------- Seletor de Folhas - Frame
        self.seletor_folhas = sf(main_frame)

        # ------------------- Plot Frame
        self.plot_frame = pf(main_frame)


# ----------------------------- MAINLOOP
# Inicialização do aplicativo
if __name__ == "__main__":
    root = tk.Tk(className='Preditor_Terra')
    app = PreditorTerraUI(root)
    root.mainloop()
else:
    pass
