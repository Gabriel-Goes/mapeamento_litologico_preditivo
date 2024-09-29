# source/interface/FramePlot.py
# ---------------------------------------------------------------------------
#
# Canvas Para Visualização de Folhas
# ------------------------------ IMPORTS ------------------------------------

from tkinter import ttk
import tkinter as tk

# ---------------------------------------------------------------------------


# ------------------------------- CLASSES ------------------------------------
# Classe para criar o Frame de Plotagem e métodos visuais
class FramePlot:
    '''
    Esta classe é responsável por criar o Frame de Plotagem e métodos visuais.

    '''

    def __init__(self, FrameSeletor, MainFrame, style=None):
        from nucleo.plotfolhas import PlotFolhas
        print(' --> Inicializando Frame de Plotagem')
        self.frame_seletor = FrameSeletor
        self.main_frame = MainFrame
        self.style = style
        self.seletor_folhas = self.frame_seletor.seletor_folhas
        self.plot_folhas = PlotFolhas(self.seletor_folhas.folhas_estudo)
        self.setupPlotFrame()

    # ------------------------- Frame - Plot Frame
    def setupPlotFrame(self):
        '''
        Cria o Frame para plotar as cartas.
        Implementar reconhecimento de click na tela para pegar coords.
        '''
        plot_frame = ttk.Frame(self.main_frame, width=1200, height=880,
                               relief=tk.GROOVE, borderwidth=5,
                               style="Custom.TFrame")
        # Plot Frame é fixado na centro esquerda do Main Frame
        plot_frame.grid(row=0, column=1, padx=0, pady=0)
        plot_frame.grid_propagate(False)
        # ------------------- Canvas - Plot Frame
        self.canvas = tk.Canvas(plot_frame,
                                width=1200, height=800, bg='lightgray')
        self.canvas.grid(row=0, column=0, padx=0, pady=0)
