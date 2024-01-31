
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Interface.py
# # ------------------------------ IMPORTS ------------------------------------
from geologist.source.DicionarioFolhas import DicionarioFolhas

from geologist.interface.SeletorFolhas import SeletorFolhas
from geologist.interface.PlotFrame import PlotFrame

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
        self.dicionario_folhas = DicionarioFolhas()
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
        self.folha_estudo = None
        self.setup_ui()

    # método para executar as funções de configuração da interface
    def setup_ui(self):
        self.root.title('Preditor Terra')
        self.root.geometry('1440x900')

        # ------------------- Main Frame
        main_frame = ttk.Frame(self.root, width=1420, height=880,
                               relief=tk.GROOVE, style="Custom.TFrame")
        main_frame.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        # ------------------- Seletor de Folhas - Frame
        self.seletor_folhas = SeletorFolhas(main_frame, self.style)
        # ------------------- Plot Frame
        self.plot_frame = PlotFrame(main_frame,
                                    self.seletor_folhas, self.folha_estudo,
                                    self.style)


# ----------------------------- MAINLOOP
# Inicialização do aplicativo
if __name__ == "__main__":
    root = tk.Tk(className='Preditor_Terra')
    app = PreditorTerraUI(root)
    root.mainloop()
else:
    pass
