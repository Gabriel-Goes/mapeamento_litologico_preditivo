# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
#
# Canvas Para Visualização de Fohlas
# ------------------------------ IMPORTS ------------------------------------
from geologist.utils.utils import plotar_inicial
from geologist.source.DicionarioFolhas import DicionarioFolhas as DictFolhas
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from tkinter import ttk
import tkinter as tk
# ---------------------------------------------------------------------------


# ------------------------- Frame - Plot Frame
def plot_frame(main_frame):
    df = DictFolhas()
    plot_frame = ttk.Frame(main_frame, width=1200, height=800,
                           relief=tk.GROOVE, borderwidth=5)
    # Plot Frame é fixado na centro esquerda do Main Frame
    plot_frame.grid(row=0, column=0, padx=5, pady=5)
    plot_frame.grid_propagate(False)

    # ------------------- Canvas - Plot Frame
    canvas = tk.Canvas(plot_frame, width=1200, height=800, bg='white')
    canvas.grid(row=0, column=0, padx=0, pady=0)
    # ------------------- Plot Carta 1:1.000.000
    # Plotar Carta 1:1.000.000
    map = plotar_inicial(df.carta_1kk)
    # plotar mapa no canvas
    canvas = FigureCanvasTkAgg(map, master=canvas)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0, padx=0, pady=0)
    # ------------------- Toolbar - Plot Frame
    toolbar = NavigationToolbar2Tk(canvas, plot_frame)
    toolbar.update()
    toolbar.grid(row=1, column=0, padx=0, pady=0)
    canvas.get_tk_widget().grid(row=0, column=0, padx=0, pady=0)
