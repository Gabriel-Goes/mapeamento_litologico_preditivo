# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
#
# Canvas Para Visualização de Folhas
# ------------------------------ IMPORTS ------------------------------------
from geologist.utils.utils import plotar_inicial
from geologist.source.DicionarioFolhas import DicionarioFolhas as DictFolhas
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from tkinter import ttk
import tkinter as tk
import shapely.geometry
# ---------------------------------------------------------------------------


# ------------------------------- CLASSES ------------------------------------
# Classe para criar o Frame de Plotagem e métodos visuais
class PlotFrame:
    '''
    Esta classe é responsável por criar o Frame de Plotagem e métodos visuais.

    Exemplo:
        plot_frame = PlotFrame(main_frame)
    '''

    def __init__(self, main_frame, seletor_folhas, folha_estudo, style=None):
        self.main_frame = main_frame
        self.dic_f = DictFolhas()
        self.ax = None
        self.folha_estudo = folha_estudo
        self.seletor_folhas = seletor_folhas
        self.style = style
        self.plot_frame()

    # Método para ver click no canvas
    def on_canvas_click(self, event):
        '''
        Evento de click no canvas.
        '''
        # geographic coordinates from the click of mouse button
        x, y = self.ax.transData.inverted().transform((event.x, event.y))
        print('')
        print('########### Evento de Click no Canvas ###########')
        print(f' --> Coords: {x, y}')
        self.folha_estudo = self.determine_folha_clicada(x, y)
        print(f' --> Folha clicada: {self.folha_estudo.id_folha}')
        print('----------------------------------------------------')
        print('')
        if self.folha_estudo is not None:
            self.seletor_folhas.atualizar_folha_estudo(self.folha_estudo)

    # Método para determinar qual folha foi clicada por contains x, y
    def determine_folha_clicada(self, ax_x, ax_y):
        click = shapely.geometry.Point(ax_x, ax_y)
        for id, poly in self.dic_f.carta_1kk.iterrows():
            if poly.geometry.contains(click):
                break
        folha_estudo = self.dic_f.carta_1kk.loc[id]

        return folha_estudo

    # ------------------------- Frame - Plot Frame
    def plot_frame(self):
        '''
        Cria o Frame para plotar as cartas.
        Implementar reconhecimento de click na tela para pegar coords.
        '''
        plot_frame = ttk.Frame(self.main_frame, width=1200, height=880,
                               relief=tk.GROOVE, borderwidth=5,
                               style="Custom.TFrame")
        # Plot Frame é fixado na centro esquerda do Main Frame
        plot_frame.grid(row=0, column=0, padx=0, pady=0)
        plot_frame.grid_propagate(False)
        # ------------------- Canvas - Plot Frame
        canvas = tk.Canvas(plot_frame, width=1200, height=800, bg='lightgray')
        canvas.grid(row=0, column=0, padx=0, pady=0)
        # ------------------- Plot Carta 1:1.000.000
        # Plotar Carta 1:1.000.000
        map, ax = plotar_inicial(self.dic_f.carta_1kk)
        self.ax = ax
        # plotar mapa no canvas
        canvas = FigureCanvasTkAgg(map, master=canvas)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, padx=0, pady=0)
        # ------------------- Toolbar - Plot Frame
        toolbar = NavigationToolbar2Tk(canvas, plot_frame)
        toolbar.update()
        toolbar.grid(row=1, column=0, padx=0, pady=0)
        canvas.get_tk_widget().grid(row=0, column=0, padx=0, pady=0)
        # ------------------- Evento de Click no Canvas
        map.canvas.mpl_connect('button_press_event', self.on_canvas_click)
